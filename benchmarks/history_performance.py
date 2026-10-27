"""Differential, alternating installed-package history performance acceptance.

Run baseline fixture preparation and measured baseline/optimized workers with
explicit interpreters. Original benchmark code and receipts remain unchanged.
Normal latency, cold-console latency, allocations and profiling are separate.
"""

import argparse
import hashlib
import json
import os
import platform
import shutil
import statistics
import subprocess
from pathlib import Path
from typing import Any

from tools.history_performance_worker import canonical, file_manifest, identity

ROOT = Path(__file__).resolve().parents[1]
READ_OPERATIONS = {
    "verify",
    "list_collections",
    "list_revisions",
    "show_revision",
    "list_baselines",
    "review_state",
    "show_baseline_text",
    "invalid_reference",
    "corrupt_json",
    "tampered_object",
    "unsupported_version",
    "resource_exhaustion",
}
ALL_OPERATIONS = (
    "initialize",
    "migrate",
    "list_collections",
    "list_revisions",
    "show_revision",
    "import_attachment",
    "create_revision",
    "reuse_revision",
    "propose_baseline",
    "approve",
    "reject",
    "supersede",
    "revoke",
    "list_baselines",
    "review_state",
    "show_baseline_text",
    "verify",
    "invalid_reference",
    "corrupt_json",
    "tampered_object",
    "unsupported_version",
    "resource_exhaustion",
    "conflict_approval",
)
EXPECTED_REJECTIONS = {
    "invalid_reference": "EVIDENCE_REVIEW",
    "corrupt_json": "EVIDENCE_JSON",
    "tampered_object": "EVIDENCE_REVISION",
    "unsupported_version": "EVIDENCE_WORKSPACE",
    "resource_exhaustion": "LIMIT_EXCEEDED",
    "conflict_approval": "EVIDENCE_REVIEW",
}
SCALING_OPERATIONS = frozenset(
    {"verify", "list_collections", "list_revisions", "list_baselines", "review_state"}
)
# R=model-bound revisions, D=review-chain depth, B=baseline proposals,
# M=unreferenced models, P=packets, C=model catalog. Collections stay at one.
# Pure R varies selected revisions over an identical 128-model catalog.
AXIS_PARAMETERS = (
    (16, 0, 0, 0, 1, 128),
    (64, 0, 0, 0, 1, 128),
    (128, 0, 0, 0, 1, 128),
    (64, 16, 64, 0, 1, 64),
    (64, 32, 64, 0, 1, 64),
    (64, 64, 64, 0, 1, 64),
    (64, 0, 0, 0, 1, 64),
    (64, 0, 16, 0, 1, 64),
    (64, 0, 32, 0, 1, 64),
    (64, 0, 64, 0, 1, 64),
    (0, 0, 0, 16, 1, 0),
    (0, 0, 0, 64, 1, 0),
    (0, 0, 0, 128, 1, 0),
    (0, 0, 0, 0, 64, 0),
)


def workload_operations(
    name: str,
    operations: tuple[str, ...],
    axis_operations: tuple[str, ...] | None = None,
) -> tuple[str, ...]:
    if name in {"workflow", "original83", "dense-native-replay"}:
        return operations
    selected = (
        axis_operations if name.startswith("axis-") and axis_operations is not None else operations
    )
    return tuple(
        op
        for op in selected
        if op in SCALING_OPERATIONS and (name != "collections-0" or op != "review_state")
    )


def assert_expected_outcome(operation: str, measured: dict[str, Any]) -> None:
    """Equal failures cannot masquerade as a successful performance comparison."""
    if measured["mode"] == "console":
        exit_code = measured["exit_code"]
        diagnostics = [json.loads(line) for line in measured["stderr"].splitlines()]
    else:
        exit_code = measured["outcome"]["exit_code"]
        diagnostics = measured["outcome"].get("diagnostics", [])
    expected = EXPECTED_REJECTIONS.get(operation)
    if expected is None:
        if exit_code != 0 or diagnostics:
            raise ValueError("A valid benchmark workflow unexpectedly failed")
        if operation == "reuse_revision" and measured["mode"] != "console":
            if measured["outcome"]["result"]["status"] != "ALREADY_PRESENT":
                raise ValueError("The idempotent workload did not actually reuse a revision")
    elif exit_code != 2 or not diagnostics or diagnostics[0]["code"] != expected:
        raise ValueError("A malicious workload did not preserve its required rejection")


def resolve_commit(value: str) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "--verify", "--end-of-options", value + "^{commit}"],
        cwd=ROOT,
        text=True,
    ).strip()


def summarize(values: list[int | float]) -> dict[str, float]:
    if not values:
        raise ValueError("A comparison needs all trial samples")
    median = float(statistics.median(values))
    return {
        "median": median,
        "minimum": float(min(values)),
        "maximum": float(max(values)),
        "spread": float(max(values) - min(values)),
        "median_absolute_deviation": float(statistics.median(abs(v - median) for v in values)),
    }


def compare_samples(
    baseline: list[dict[str, Any]], optimized: list[dict[str, Any]]
) -> dict[str, Any]:
    if len(baseline) != len(optimized) or not baseline:
        raise ValueError("Baseline and optimized trials must have equal nonzero counts")
    field = "stdout_sha256" if baseline[0]["mode"] == "console" else "outcome_sha256"
    for old, new in zip(baseline, optimized, strict=True):
        if old["input_identity"] != new["input_identity"]:
            raise ValueError("A workload changed between compared implementations")
        if (
            old[field] != new[field]
            or old.get("stderr_sha256") != new.get("stderr_sha256")
            or old.get("exit_code") != new.get("exit_code")
        ):
            raise ValueError("Differential public outcome mismatch")
        if old["artifact_manifest_sha256"] != new["artifact_manifest_sha256"]:
            raise ValueError("Differential persistent artifact bytes mismatch")
    old_stats = summarize([r["elapsed_ns"] for r in baseline])
    new_stats = summarize([r["elapsed_ns"] for r in optimized])
    result: dict[str, Any] = {
        "baseline_elapsed_ns": old_stats,
        "optimized_elapsed_ns": new_stats,
        "speedup": old_stats["median"] / new_stats["median"] if new_stats["median"] else None,
        "integrity": "exact public outcomes and persistent artifact bytes",
        "trials_each": len(baseline),
    }
    for name in ("cpu_ns", "python_peak_bytes", "rss_bytes"):
        old_values = [r[name] for r in baseline if r.get(name) is not None]
        new_values = [r[name] for r in optimized if r.get(name) is not None]
        if old_values and new_values:
            result["baseline_" + name] = summarize(old_values)
            result["optimized_" + name] = summarize(new_values)
    return result


def _worker(python: Path, args: list[str], environment: dict[str, str]) -> None:
    child = subprocess.run(
        [str(python), "-m", "tools.history_performance_worker", *args],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        timeout=1800,
    )
    if child.returncode:
        raise RuntimeError(
            f"Worker {python} failed: {child.stderr.decode(errors='replace')[-4096:]}"
        )


def expected_package_sources(commit: str) -> dict[str, str]:
    names = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", commit, "src/otarchguard"], cwd=ROOT, text=True
    ).splitlines()
    names = [n for n in names if n.endswith(".py")]
    if not names:
        raise ValueError("Source commit contains no package Python inventory")
    data = subprocess.check_output(
        ["git", "cat-file", "--batch"],
        input="".join(commit + ":" + n + "\n" for n in names).encode(),
        cwd=ROOT,
    )
    result: dict[str, str] = {}
    position = 0
    for name in names:
        end = data.index(b"\n", position)
        header = data[position:end].split()
        if len(header) != 3 or header[1] != b"blob":
            raise ValueError("Expected exact committed Python source blob")
        size = int(header[2])
        raw = data[end + 1 : end + 1 + size]
        if len(raw) != size or data[end + 1 + size : end + 2 + size] != b"\n":
            raise ValueError("Malformed committed source response")
        result[name.removeprefix("src/otarchguard/")] = hashlib.sha256(raw).hexdigest()
        position = end + size + 2
    return result


def _relocate(value: Any, before: Path, after: Path) -> Any:
    if isinstance(value, dict):
        return {k: _relocate(v, before, after) for k, v in value.items()}
    if isinstance(value, list):
        return [_relocate(v, before, after) for v in value]
    if isinstance(value, str) and (
        value == str(before.absolute()) or value.startswith(str(before.absolute()) + os.sep)
    ):
        return str(after.absolute()) + value[len(str(before.absolute())) :]
    return value


def run_comparison(
    output: Path,
    baseline_python: Path,
    optimized_python: Path,
    baseline_commit: str,
    optimized_commit: str,
    *,
    trials: int = 3,
    reference_workspace: Path | None = None,
    dense_workspace: Path | None = None,
    operations: tuple[str, ...] = ALL_OPERATIONS,
    scales: tuple[int, ...] = (0, 1, 16, 64, 128, 256),
    modes: tuple[str, ...] = ("timing", "console", "memory", "profile"),
    axis_operations: tuple[str, ...] | None = None,
    fanout_scales: tuple[int, ...] = (),
) -> dict[str, Any]:
    if not 1 <= trials <= 9 or not all(0 <= n <= 256 for n in scales):
        raise ValueError("Bounded benchmark needs 1..9 trials and 0..256 collections")
    if not set(operations) <= set(ALL_OPERATIONS) or not set(modes) <= {
        "timing",
        "console",
        "memory",
        "profile",
    }:
        raise ValueError("Unknown benchmark operation or mode")
    if axis_operations is not None and not set(axis_operations) <= SCALING_OPERATIONS:
        raise ValueError("Axis operations must be supported read-only measurements")
    if any(type(n) is not int or not 1 <= n <= 256 for n in fanout_scales) or (
        fanout_scales and dense_workspace is None
    ):
        raise ValueError("Fan-out scales require a dense fictional template and 1..256 branches")
    output = output.absolute()
    baseline_commit = resolve_commit(baseline_commit)
    optimized_commit = resolve_commit(optimized_commit)
    baseline_python = baseline_python.absolute()
    optimized_python = optimized_python.absolute()
    output.mkdir(exist_ok=False)
    temporary = output / "temporary"
    temporary.mkdir()
    environment = {
        **os.environ,
        "OTARCHGUARD_OFFLINE_CHECK": "1",
        "PYTHONPATH": str(ROOT / "tools/offline"),
        "TEMP": str(temporary),
        "TMP": str(temporary),
        "PYTHONUTF8": "1",
    }
    packages: dict[str, Any] = {}
    for version, interpreter, commit in (
        ("baseline", baseline_python, baseline_commit),
        ("optimized", optimized_python, optimized_commit),
    ):
        package_file = output / (version + "-package.json")
        _worker(interpreter, ["--identify", "--output", str(package_file)], environment)
        packages[version] = json.loads(package_file.read_bytes())
        if packages[version]["source_sha256"] != expected_package_sources(commit):
            raise ValueError(
                "Installed package sources differ from the declared " + version + " commit"
            )
    if (
        packages["baseline"]["python"] != packages["optimized"]["python"]
        or packages["baseline"]["implementation"] != packages["optimized"]["implementation"]
    ):
        raise ValueError(
            "Primary before/after performance needs the same Python version and implementation"
        )
    fixtures = output / "fixtures"
    fixtures.mkdir()
    workloads: dict[str, Path] = {}
    if reference_workspace is not None:
        reference = fixtures / "original"
        reference.mkdir()
        shutil.copytree(reference_workspace, reference / "history", symlinks=True)
        _worker(
            baseline_python, ["--validate", "--output", str(reference / "history")], environment
        )
        workloads["original83"] = reference
    if dense_workspace is not None:
        dense = fixtures / "dense"
        dense.mkdir()
        shutil.copytree(dense_workspace, dense / "history", symlinks=True)
        _worker(baseline_python, ["--validate", "--output", str(dense / "history")], environment)
        workloads["dense-native-replay"] = dense
    for count in scales:
        destination = fixtures / ("collections-" + str(count))
        _worker(
            baseline_python,
            ["--prepare", "--output", str(destination), "--collections", str(count)],
            environment,
        )
        workloads[destination.name] = destination
    # Independent axes retain physical collection count at one.
    if reference_workspace is None and not any(n > 0 for n in scales):
        raise ValueError("At least one nonempty workload is needed for complete workflows")
    if len(scales) > 2:
        for revisions, depth, baselines, models, packets, catalog in AXIS_PARAMETERS:
            destination = (
                fixtures
                / f"axis-r{revisions}-d{depth}-b{baselines}-m{models}-p{packets}-c{catalog}"
            )
            _worker(
                baseline_python,
                [
                    "--prepare",
                    "--output",
                    str(destination),
                    "--collections",
                    "1",
                    "--revisions",
                    str(revisions),
                    "--review-depth",
                    str(depth),
                    "--packets",
                    str(packets),
                    "--baselines",
                    str(baselines),
                    "--unreferenced-models",
                    str(models),
                    "--model-catalog",
                    str(catalog),
                ],
                environment,
            )
            workloads[destination.name] = destination
    for branches in fanout_scales:
        destination = fixtures / f"axis-fanout-{branches}"
        assert dense_workspace is not None
        _worker(
            baseline_python,
            [
                "--prepare-fanout",
                str(dense_workspace.absolute()),
                "--fanout",
                str(branches),
                "--output",
                str(destination),
            ],
            environment,
        )
        workloads[destination.name] = destination
    # A small complete workflow fixture always permits all mutating operations.
    complete = fixtures / "workflow"
    _worker(
        baseline_python,
        ["--prepare", "--output", str(complete), "--collections", "2", "--revisions", "2"],
        environment,
    )
    workloads["workflow"] = complete
    public_source = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    record: dict[str, Any] = {
        "benchmark_version": 1,
        "baseline_commit": baseline_commit,
        "optimized_commit": optimized_commit,
        "harness_commit": public_source,
        "harness_sha256": {
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [
                ROOT / "benchmarks/history_performance.py",
                ROOT / "tools/history_performance_worker.py",
            ]
        },
        "environment": {
            "platform": platform.platform(),
            "processor": platform.processor(),
            "machine": platform.machine(),
            "logical_cpus": os.cpu_count(),
            "power_mode": "Not controlled by the harness; "
            "record the operator's power-plan receipt separately.",
            "python_harness": platform.python_version(),
            "baseline_python": str(baseline_python),
            "optimized_python": str(optimized_python),
            "offline_python": True,
            "timing_policy": "same-machine alternating installed workers; "
            "no tracemalloc/cProfile in primary timing; fresh-process console; "
            "filesystem cache not forcibly evicted",
        },
        "workloads": {},
        "packages": packages,
        "comparisons": [],
        "measurement_selection": {
            "collection_scales": scales,
            "operations": operations,
            "axis_operations": axis_operations,
            "axis_parameters_r_d_b_m_p_c": AXIS_PARAMETERS,
            "fanout_scales": fanout_scales,
        },
        "limitations": [
            "OS filesystem/antivirus/scheduling caches are uncontrolled confounders; "
            "preserve raw trials and spread.",
            "Fresh-process RSS includes interpreter and common harness imports; "
            "it is not traced operation allocation.",
            "CLI child CPU/RSS are not inferred from parent counters.",
            "Profiling/allocation timings never establish primary end-user speedups.",
        ],
    }
    cases = output / "cases"
    cases.mkdir()
    trial_root = output / "trials"
    trial_root.mkdir()
    case_number = trial_number = 0
    for workload_name, fixture in workloads.items():
        manifest = file_manifest(fixture / "history")
        record["workloads"][workload_name] = {
            "file_sha256": manifest,
            "identity": identity(manifest),
            "file_count": len(manifest),
            "bytes": sum(p.stat().st_size for p in (fixture / "history").rglob("*") if p.is_file()),
        }
        selected_operations = workload_operations(workload_name, operations, axis_operations)
        for operation in selected_operations:
            template = cases / f"c{case_number:04d}"
            case_number += 1
            _worker(
                baseline_python,
                ["--case", str(fixture), "--output", str(template), "--operation", operation],
                environment,
            )
            original_request = json.loads((template / "request.json").read_bytes())
            for mode in modes:
                if mode == "console" and operation in {"resource_exhaustion", "review_state"}:
                    continue
                versions: dict[str, list[dict[str, Any]]] = {"baseline": [], "optimized": []}
                count = 1 if mode == "profile" else trials
                for trial in range(count):
                    order = (
                        ("baseline", "optimized") if trial % 2 == 0 else ("optimized", "baseline")
                    )
                    for version in order:
                        destination = trial_root / f"t{trial_number:05d}-{version[0]}"
                        trial_number += 1
                        shutil.copytree(template, destination)
                        request = _relocate(original_request, template, destination)
                        request["warmups"] = (
                            1 if mode == "timing" and operation in READ_OPERATIONS else 0
                        )
                        request_file = destination / "request.json"
                        request_file.write_bytes(canonical(request))
                        result_file = destination / "measurement.json"
                        interpreter = baseline_python if version == "baseline" else optimized_python
                        _worker(
                            interpreter,
                            [
                                "--request",
                                str(request_file),
                                "--output",
                                str(result_file),
                                "--mode",
                                mode,
                            ],
                            environment,
                        )
                        measured = json.loads(result_file.read_bytes())
                        assert_expected_outcome(operation, measured)
                        if (
                            measured["environment"]["source_inventory_sha256"]
                            != packages[version]["source_inventory_sha256"]
                        ):
                            raise ValueError("Installed source changed during the benchmark")
                        target = Path(request["workspace"])
                        measured["artifact_manifest_sha256"] = (
                            identity(file_manifest(target)) if target.is_dir() else None
                        )
                        measured["version"] = version
                        measured["trial"] = trial
                        measured["trial_directory"] = str(destination.relative_to(output))
                        result_file.write_bytes(canonical(measured))
                        versions[version].append(measured)
                comparison = compare_samples(versions["baseline"], versions["optimized"])
                record["comparisons"].append(
                    {
                        "workload": workload_name,
                        "operation": operation,
                        "mode": mode,
                        "summary": comparison,
                        "raw": versions,
                    }
                )
                (output / "performance.json").write_bytes(canonical(record))
    record["status"] = "passed"
    (output / "performance.json").write_bytes(canonical(record))
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--baseline-python", type=Path, required=True)
    parser.add_argument("--optimized-python", type=Path, required=True)
    parser.add_argument("--baseline-commit", required=True)
    parser.add_argument("--optimized-commit", required=True)
    parser.add_argument("--reference-workspace", type=Path)
    parser.add_argument("--dense-workspace", type=Path)
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--operations", nargs="*", choices=ALL_OPERATIONS)
    parser.add_argument("--axis-operations", nargs="*", choices=sorted(SCALING_OPERATIONS))
    parser.add_argument("--fanout-scales", nargs="*", type=int, default=[])
    parser.add_argument("--scales", nargs="*", type=int, default=[0, 1, 16, 64, 128, 256])
    parser.add_argument(
        "--modes",
        nargs="*",
        choices=["timing", "console", "memory", "profile"],
        default=["timing", "console", "memory", "profile"],
    )
    args = parser.parse_args()
    result = run_comparison(
        args.output,
        args.baseline_python,
        args.optimized_python,
        args.baseline_commit,
        args.optimized_commit,
        trials=args.trials,
        reference_workspace=args.reference_workspace,
        dense_workspace=args.dense_workspace,
        operations=tuple(args.operations) if args.operations else ALL_OPERATIONS,
        scales=tuple(args.scales),
        modes=tuple(args.modes),
        axis_operations=tuple(args.axis_operations) if args.axis_operations is not None else None,
        fanout_scales=tuple(args.fanout_scales),
    )
    print(
        json.dumps(
            {"status": result["status"], "comparisons": len(result["comparisons"])}, sort_keys=True
        )
    )


if __name__ == "__main__":
    main()
