"""Finite installed-package drift scaling with separate timing and allocation trials."""

import argparse
import copy
import hashlib
import importlib.metadata
import json
import platform
import statistics
import time
import tracemalloc
from pathlib import Path
from typing import Any
from unittest.mock import patch

import otarchguard
from benchmarks.capture import process_peak_rss_bytes
from otarchguard.evidence import history, lifecycle
from otarchguard.reachability import ReachabilityEngine
from tools.drift_walkthrough import canonical, comparison_context, prepare


def measure_case(
    name: str,
    selection: dict[str, Any],
    candidates: list[str],
    context: dict[str, Any],
    trials: int,
) -> dict[str, Any]:
    from otarchguard.drift.engine import compare

    workspace = Path(selection["workspace"])
    expected = compare(workspace, selection["baseline_id"], candidates, context)
    findings = [f for pair in expected["comparisons"] for f in pair["findings"]]
    if name == "identical-selected-revision":
        if expected["summary"]["distinct_physical_collections"] != 1 or any(
            f["category"] in {"PROTOCOL_METADATA_DIFFERENCE", "DECLARED_ARCHITECTURE_CHANGE"}
            for f in findings
        ):
            raise AssertionError("Identical fixture acquired an independent collection or change")
    elif name == "same-capture-decoder-reinterpretation":
        if expected["comparisons"][0]["comparability"]["independent_collections"] or not any(
            f["subtype"] == "PROTOCOL_SEMANTICS_CHANGED" for f in findings
        ):
            raise AssertionError("Same-capture decoder fixture lost analytical separation")
    elif name == "repeated-equivalent-packets":
        observed = [f for f in findings if f["category"] == "OBSERVED_COMMUNICATION_DIFFERENCE"]
        if len(observed) != 3 or any(
            side["metadata"]["packets"] != 128
            for f in observed
            for side in (f["reference"], f["candidate"])
            if side is not None
        ):
            raise AssertionError("Repeated packet fixture lost bounded tuple aggregation")
    elif name == "explicit-multiple-collection-alignment":
        if len(expected["comparisons"]) != 2 or expected["unaligned_findings"]:
            raise AssertionError("Explicit two-pair fixture lost collection correspondence")
    encoded = canonical(expected)
    before = {
        p.relative_to(workspace).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in workspace.rglob("*")
        if p.is_file()
    }
    raw: list[dict[str, Any]] = []
    for _ in range(trials):
        started = time.perf_counter()
        cpu_started = time.process_time()
        result = compare(workspace, selection["baseline_id"], candidates, context)
        cpu_seconds = time.process_time() - cpu_started
        wall_seconds = time.perf_counter() - started
        if canonical(result) != encoded:
            raise AssertionError("Measured comparison changed canonical results")
        raw.append({"wall_seconds": wall_seconds, "cpu_seconds": cpu_seconds})
    tracemalloc.start()
    try:
        allocated = compare(workspace, selection["baseline_id"], candidates, context)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    if canonical(allocated) != encoded:
        raise AssertionError("Allocation measurement changed canonical results")
    with (
        patch.object(history, "_read_bytes", wraps=history._read_bytes) as reads,
        patch.object(json, "loads", wraps=json.loads) as parses,
        patch.object(lifecycle, "_operation", wraps=lifecycle._operation) as acquisitions,
        patch.object(
            ReachabilityEngine, "evaluate", autospec=True, side_effect=ReachabilityEngine.evaluate
        ) as native,
    ):
        instrumented = compare(workspace, selection["baseline_id"], candidates, context)
        counts = {
            "workspace_byte_reads": sum(
                Path(call.args[0]).absolute().is_relative_to(workspace.absolute())
                for call in reads.call_args_list
            ),
            "all_history_byte_reads": reads.call_count,
            "json_loads_calls": parses.call_count,
            "lifecycle_acquisitions": acquisitions.call_count,
            "native_evaluate_calls": native.call_count,
        }
    if canonical(instrumented) != encoded:
        raise AssertionError("Separately instrumented trial changed canonical results")
    if counts["lifecycle_acquisitions"] != 1:
        raise AssertionError("Drift operation did not retain operation-scoped acquisition")
    started = time.perf_counter()
    historical = lifecycle.verify_lifecycle(workspace)
    historical_seconds = time.perf_counter() - started
    after = {
        p.relative_to(workspace).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in workspace.rglob("*")
        if p.is_file()
    }
    if before != after:
        raise AssertionError("Read-only benchmark mutated source evidence")
    return {
        "name": name,
        "drift_id": expected["drift_id"],
        "selected_pairs": len(context["pairs"]),
        "distinct_physical_collections": expected["summary"]["distinct_physical_collections"],
        "report_canonical_bytes": len(encoded),
        "workspace_files": len(before),
        "workspace_bytes": sum(p.stat().st_size for p in workspace.rglob("*") if p.is_file()),
        "input_manifest_sha256": hashlib.sha256(canonical(before)).hexdigest(),
        "raw_timing_trials": raw,
        "median_wall_seconds": statistics.median(x["wall_seconds"] for x in raw),
        "min_wall_seconds": min(x["wall_seconds"] for x in raw),
        "max_wall_seconds": max(x["wall_seconds"] for x in raw),
        "median_cpu_seconds": statistics.median(x["cpu_seconds"] for x in raw),
        "separate_traced_peak_bytes": peak,
        "process_lifetime_peak_rss_bytes": process_peak_rss_bytes(),
        "separate_instrumented_trial": counts,
        "historical_verify_seconds": historical_seconds,
        "historical_verification": historical,
        "resource_usage": expected["resource_usage"],
        "summary": expected["summary"],
    }


def benchmark(
    output: Path, scales: tuple[int, ...] = (1, 16, 64), trials: int = 3
) -> dict[str, Any]:
    if (
        not scales
        or len(scales) > 8
        or len(set(scales)) != len(scales)
        or any(type(n) is not int or not 1 <= n <= 512 for n in scales)
        or type(trials) is not int
        or not 1 <= trials <= 7
    ):
        raise ValueError("Use 1..8 unique scales in 1..512 and 1..7 trials")
    package = Path(otarchguard.__file__).resolve().parent
    root = Path(__file__).resolve().parents[1]
    direct = json.loads(
        importlib.metadata.distribution("otarchguard").read_text("direct_url.json") or "{}"
    )
    if package.is_relative_to(root / "src") or direct.get("dir_info", {}).get("editable", False):
        raise ValueError("Drift measurements require a regular installed package")
    output.mkdir(exist_ok=False)
    inventory = {
        p.relative_to(package).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(package.rglob("*.py"))
    }
    receipt: dict[str, Any] = {
        "benchmark_version": 1,
        "fictional_only": True,
        "platform": platform.platform(),
        "python": platform.python_version(),
        "installed_module": str(package),
        "distribution": otarchguard.DISTRIBUTION_VERSION,
        "native_engine": otarchguard.NATIVE_ENGINE_VERSION,
        "installed_source_sha256": inventory,
        "source_inventory_sha256": hashlib.sha256(canonical(inventory)).hexdigest(),
        "method": "Preparation and warmup excluded; timing untraced; "
        "allocations and counters separate; "
        "RSS is lifetime process high-water including preparation/imports; "
        "OS caches and scheduling uncontrolled; finite cardinality only",
        "workloads": [],
    }

    def retain(value: dict[str, Any]) -> None:
        receipt["workloads"].append(value)
        (output / "benchmark.json").write_text(
            json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8"
        )

    for scale in scales:
        selected = prepare(output / ("scale-" + str(scale)), scale=scale, variations=False)
        reference = selected["periods"]["reference"]["analysis_id"]
        candidate = selected["periods"]["candidate"]["analysis_id"]
        context = comparison_context(reference, candidate, selected["scope"])
        measured = measure_case("cardinality-" + str(scale), selected, [candidate], context, trials)
        retain({**measured, "scale": scale, "flow_relationships_per_capture": scale + 1})
    semantic = prepare(output / "semantic-cases")
    reference = semantic["periods"]["reference"]["analysis_id"]
    for name, candidate in (
        ("identical-selected-revision", reference),
        ("opaque-candidate-coverage", semantic["periods"]["incomplete"]["analysis_id"]),
        (
            "same-capture-decoder-reinterpretation",
            semantic["periods"]["decoder_one"]["analysis_id"],
        ),
    ):
        context = comparison_context(reference, candidate, semantic["scope"])
        retain(measure_case(name, semantic, [candidate], context, trials))
    repeated = prepare(output / "repeated-packets", variations=False, repetitions=128)
    reference = repeated["periods"]["reference"]["analysis_id"]
    candidate = repeated["periods"]["candidate"]["analysis_id"]
    retain(
        {
            **measure_case(
                "repeated-equivalent-packets",
                repeated,
                [candidate],
                comparison_context(reference, candidate, repeated["scope"]),
                trials,
            ),
            "packet_repetitions_per_relationship": 128,
            "flow_relationships_per_capture": 2,
        }
    )
    workspace = Path(semantic["workspace"])
    multi_scope = copy.deepcopy(semantic["scope"])
    multi_scope["purpose"] = "Explicit fictional multiple-collection alignment"
    scope_path = output / "multi-scope.json"
    scope_path.write_bytes(canonical(multi_scope))
    references = [semantic["periods"][key]["analysis_id"] for key in ("reference", "incomplete")]
    candidates = [semantic["periods"][key]["analysis_id"] for key in ("decoder_one", "candidate")]
    baseline = lifecycle.propose_baseline(workspace, scope_path, references)["baseline"]
    lifecycle.record_review(
        workspace,
        baseline["baseline_id"],
        "approve",
        "Fictional benchmark owner",
        "Exact fictional multi-collection inputs only",
    )
    context = {"context_version": 1, "pairs": []}
    for reference, candidate in zip(references, candidates, strict=True):
        context["pairs"].extend(comparison_context(reference, candidate, multi_scope)["pairs"])
    multi = {**semantic, "baseline_id": baseline["baseline_id"]}
    retain(
        measure_case("explicit-multiple-collection-alignment", multi, candidates, context, trials)
    )
    receipt["status"] = "passed"
    (output / "benchmark.json").write_text(
        json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--scales", nargs="+", type=int, default=[1, 16, 64])
    parser.add_argument("--trials", type=int, default=3)
    args = parser.parse_args()
    result = benchmark(args.output.absolute(), tuple(args.scales), args.trials)
    print(
        json.dumps(
            {"status": result["status"], "workloads": len(result["workloads"])}, sort_keys=True
        )
    )


if __name__ == "__main__":
    main()
