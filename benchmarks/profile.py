"""Opt-in phase attribution; measurements are observations, never CI timing assertions."""

import argparse
import cProfile
import gc
import hashlib
import json
import os
import platform
import pstats
import statistics
import subprocess
import sys
import sysconfig
import tracemalloc
from collections.abc import Callable
from dataclasses import asdict
from functools import partial
from pathlib import Path
from time import perf_counter_ns, process_time_ns
from typing import Any

import yaml
from typer.testing import CliRunner

from benchmarks.workloads import routine, source_bytes
from otarchguard.api import validate_bytes
from otarchguard.cli import app
from otarchguard.comparison import compare_architectures
from otarchguard.contract import RESOURCE_LIMITS
from otarchguard.diagnostics import ModelError
from otarchguard.exposure import exposure_architecture
from otarchguard.graph import build_graph
from otarchguard.intents import check_architecture
from otarchguard.intervals import partition
from otarchguard.loading import load_bytes
from otarchguard.normalization import canonical_bytes, normalize
from otarchguard.parsing import parse_model
from otarchguard.policy import compile_policy
from otarchguard.reachability import ReachabilityEngine
from otarchguard.reporting import (
    architecture_svg,
    build_report,
    html_report,
    json_report,
    write_report,
)
from otarchguard.trace import trace_architecture
from otarchguard.trace_reporting import trace_html, trace_json
from otarchguard.validation import validate_structure

ROOT = Path(__file__).resolve().parents[1]


def report_command(path: Path, output: Path) -> Any:
    """Complete in-process check/report invocation; excludes interpreter/import startup."""
    return CliRunner().invoke(
        app, ["check", str(path), "--report", str(output), "--report-format", "json"]
    )


def expect_rejection(operation: Callable[[], Any], diagnostics: list[dict[str, Any]]) -> None:
    """Measure controlled failures too; never turn a rejection into a partial result."""
    try:
        operation()
    except ModelError as error:
        assert [asdict(d) for d in error.diagnostics] == diagnostics
    else:
        raise AssertionError("Expected the same controlled rejection")


def measure(operation: Callable[[], Any], runs: int, batch: int = 1) -> dict[str, Any]:
    """One warm-up; untraced wall/CPU batches; independent single-operation peak."""
    operation()
    wall, cpu = [], []
    for _ in range(runs):
        gc.collect()
        w, c = perf_counter_ns(), process_time_ns()
        for _ in range(batch):
            operation()
        cpu.append((process_time_ns() - c) / batch / 1e9)
        wall.append((perf_counter_ns() - w) / batch / 1e9)
    gc.collect()
    tracemalloc.start()
    try:
        operation()
        retained, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    median = statistics.median(wall)
    return {
        "wall_seconds": wall,
        "cpu_seconds": cpu,
        "median_wall_seconds": median,
        "median_cpu_seconds": statistics.median(cpu),
        "wall_mad_seconds": statistics.median(abs(s - median) for s in wall),
        "wall_range_seconds": [min(wall), max(wall)],
        "peak_traced_python_bytes": peak,
        "post_operation_traced_bytes": retained,
        "batch": batch,
        "runs": runs,
    }


def attribution(operation: Callable[[], Any]) -> list[dict[str, Any]]:
    """Keep all production function self/cumulative costs; overlapping costs do not add."""
    profiler = cProfile.Profile()
    profiler.runcall(operation)
    stats: Any = pstats.Stats(profiler)
    return [
        {
            "module": Path(file).name,
            "line": line,
            "function": function,
            "primitive_calls": values[0],
            "calls": values[1],
            "self_seconds": values[2],
            "cumulative_seconds": values[3],
        }
        for (file, line, function), values in sorted(stats.stats.items())
        if "otarchguard" in file
    ]


def workload(name: str) -> bytes:
    if name in {"routine", "sparse", "dense-policy", "interval-heavy", "deny-heavy"}:
        return source_bytes(name)
    if name in {"mixed", "mixed-intervals"}:
        return (ROOT / "examples/trace/communication.yaml").read_bytes()
    if name == "comparison":
        return (ROOT / "examples/flat-plant/baseline.yaml").read_bytes()
    data: dict[str, Any] = yaml.safe_load((ROOT / "tests/fixtures/minimal-valid.yaml").read_bytes())
    if name == "tcp-udp":
        data["services"].append({**data["services"][0], "id": "svc_udp", "protocol": "udp"})
        data["rules"].append({**data["rules"][0], "id": "allow_udp", "protocol": "udp"})
        data["scenarios"][0]["destination_service_ids"].append("svc_udp")
    elif name == "blocked":
        data["rules"] = []
    elif name == "absent":
        data["rules"], data["transport_edges"] = [], []
    elif name == "boundary":
        return (ROOT / "tests/fixtures/boundary-device.yaml").read_bytes()
    elif name != "minimal":
        raise ValueError("Unknown profile")
    # Break shared nested references in derived declarations; YAML aliases are forbidden.
    return yaml.safe_dump(json.loads(json.dumps(data)), sort_keys=False).encode()


def report_workflow(name: str, out: Path, runs: int) -> dict[str, Any]:
    """Observe total Python allocation of the report workflow, separately from native timing."""
    data = workload(name)
    path, output = out / (name + ".yaml"), out / (name + ".json")
    path.write_bytes(data)
    operation = partial(report_command, path, output)
    result = operation()
    return {
        "name": name,
        "input_sha256": hashlib.sha256(data).hexdigest(),
        "measurements": measure(operation, runs),
        "exit": result.exit_code,
        "stdout_sha256": hashlib.sha256(result.stdout.encode()).hexdigest(),
        "report_sha256": hashlib.sha256(output.read_bytes()).hexdigest()
        if output.exists()
        else None,
        "method": "In-process complete check/JSON report, including input and writing; "
        "excludes interpreter/import startup; Python allocation, not child RSS.",
    }


def profile(name: str, out: Path, runs: int, confirmation: bool = False) -> dict[str, Any]:
    data = workload(name)
    path = out / (name + ".yaml")
    path.write_bytes(data)
    validated = validate_bytes(data)
    peer, peer_path = validated, path
    if name == "comparison":
        peer_data = (ROOT / "examples/flat-plant/proposed.yaml").read_bytes()
        peer = validate_bytes(peer_data)
        peer_path = out / "comparison-proposed.yaml"
        peer_path.write_bytes(peer_data)
    model = validated.model
    service = (
        next(s for s in model.services if s.id == "svc_plc")
        if name == "mixed-intervals"
        else model.services[0]
    )
    source = next(a.id for a in model.assets if a.id != service.asset_id)
    scope = frozenset({service.id})
    engine = ReachabilityEngine(validated, scope)
    raw = None if confirmation else load_bytes(data)
    parsed = model if confirmation else parse_model(raw, RESOURCE_LIMITS)
    normalized = model if confirmation else normalize(parsed)
    record: dict[str, Any] = {
        "name": name,
        "mode": "confirmation" if confirmation else "full_attribution",
        "input_sha256": hashlib.sha256(data).hexdigest(),
        "model_sha256": validated.sha256,
        "scope": {"source_asset_id": source, "service_id": service.id},
        "input_bytes": len(data),
        "dimensions": {
            "assets": len(model.assets),
            "interfaces": len(model.interfaces),
            "edges": len(engine.graph.edges),
            "rules": len(model.rules),
            "associations": engine.associations,
            "services": len(model.services),
            "selected_atoms": len(engine.service_atoms[service.id]),
            "protocols": sorted({s.protocol for s in model.services}),
        },
        "ceilings": asdict(RESOURCE_LIMITS),
        "phases": {},
    }
    operations: dict[str, Callable[[], Any]] = {
        "input_read": path.read_bytes,
        "yaml_parse": lambda: load_bytes(data),
        "typed_parse": lambda: parse_model(raw, RESOURCE_LIMITS),
        "structure_validation": lambda: validate_structure(parsed),
        "normalization": lambda: normalize(parsed),
        "canonical_serialization": lambda: canonical_bytes(normalized),
        "sha256": lambda: hashlib.sha256(validated.canonical_json).hexdigest(),
        "validation_complete": lambda: validate_bytes(data),
        "graph": lambda: build_graph(model, RESOURCE_LIMITS),
        "policy_compile_including_associations": lambda: compile_policy(model, RESOURCE_LIMITS),
        "partition": lambda: partition(model, scope, RESOURCE_LIMITS),
        "engine_prepare": lambda: ReachabilityEngine(validated, scope),
        "trace_plain": lambda: trace_architecture(validated, source, service.id),
        "trace_policy": lambda: trace_architecture(
            validated, source, service.id, policy_evidence=True
        ),
        "check_prevalidated": lambda: check_architecture(validated),
    }
    plain = trace_architecture(validated, source, service.id)
    policy = trace_architecture(validated, source, service.id, policy_evidence=True)
    assert plain.intervals == policy.intervals and plain.work == policy.work
    record["trace_work"] = asdict(plain.work)
    record["policy_work"] = asdict(policy.policy_evidence)["work"]
    record["evidence_sha256"] = hashlib.sha256(trace_json(policy)).hexdigest()
    operations.update(trace_json=lambda: trace_json(policy), trace_html=lambda: trace_html(policy))
    report = build_report("validation", (validated,))
    rendered = json_report(report)
    operations.update(
        report_build=lambda: build_report("validation", (validated,)),
        report_json=lambda: json_report(report),
        report_html=lambda: html_report(report, (validated,)),
        report_svg=lambda: architecture_svg(validated),
        report_write=lambda: write_report(out / (name + ".report.json"), rendered, (path,)),
    )
    if model.scenarios:
        operations["exposure_prevalidated"] = lambda: exposure_architecture(
            validated, model.scenarios[0].id
        )
        operations["comparison_prevalidated"] = lambda: compare_architectures(
            validated, peer, model.scenarios[0].id
        )
    if name == "tcp-udp":
        operations["trace_udp"] = lambda: trace_architecture(validated, source, "svc_udp")
    if confirmation:
        operations = {
            phase: operation
            for phase, operation in operations.items()
            if phase
            in {
                "trace_plain",
                "trace_policy",
                "trace_udp",
                "check_prevalidated",
                "exposure_prevalidated",
                "comparison_prevalidated",
            }
        }
    for phase, operation in operations.items():
        try:
            # Batch only predictably tiny non-I/O operations; preserve fresh engine lifetime.
            batch = 20 if phase in {"sha256", "input_read"} else 1
            record["phases"][phase] = {"status": "completed", **measure(operation, runs, batch)}
            if phase in {"check_prevalidated", "exposure_prevalidated", "comparison_prevalidated"}:
                result = asdict(operation())
                record["phases"][phase]["work"] = {
                    key: value
                    for key, value in result.items()
                    if key in {"atom_queries", "state_edge_visits", "edge_rule_atom_checks"}
                }
        except ModelError as error:
            diagnostics = [asdict(d) for d in error.diagnostics]
            record["phases"][phase] = {
                "status": "rejected",
                "diagnostics": diagnostics,
                **measure(partial(expect_rejection, operation, diagnostics), runs),
            }
    record["cprofile_trace_policy"] = attribution(operations["trace_policy"])
    if not confirmation:
        record["cprofile_validation"] = attribution(operations["validation_complete"])
    if not confirmation or name in {"minimal", "routine"}:
        record["cprofile_check_report"] = attribution(
            partial(
                CliRunner().invoke, app, ["check", str(path), "--report", str(out / "profile.html")]
            )
        )
    console = Path(sysconfig.get_path("scripts")) / (
        "otarchguard.exe" if os.name == "nt" else "otarchguard"
    )
    commands = {
        "startup": ["--version"],
        "validate": ["validate", str(path)],
        "check_json": [
            "check",
            str(path),
            "--report",
            str(out / (name + "-check.json")),
            "--report-format",
            "json",
        ],
        "trace_plain": ["trace", str(path), "--source", source, "--service", service.id],
        "trace_policy": [
            "trace",
            str(path),
            "--source",
            source,
            "--service",
            service.id,
            "--policy-evidence",
        ],
    }
    if name in {"minimal", "routine", "mixed", "comparison", "tcp-udp"} and model.scenarios:
        commands["exposure_html"] = [
            "exposure",
            str(path),
            "--scenario",
            model.scenarios[0].id,
            "--report",
            str(out / (name + "-exposure.html")),
        ]
        commands["compare_json"] = [
            "compare",
            str(path),
            str(peer_path),
            "--scenario",
            model.scenarios[0].id,
            "--report",
            str(out / (name + "-compare.json")),
            "--report-format",
            "json",
        ]
    record["native"] = {}
    if confirmation and name not in {"minimal", "routine", "mixed", "tcp-udp", "comparison"}:
        commands = {"check_json": commands["check_json"]}
    for label, args in commands.items():
        samples, outputs = [], []
        for i in range(runs + 1):
            start = perf_counter_ns()
            process = subprocess.run([str(console), *args], capture_output=True, timeout=120)
            elapsed = (perf_counter_ns() - start) / 1e9
            outputs.append(
                (
                    process.returncode,
                    hashlib.sha256(process.stdout).hexdigest(),
                    hashlib.sha256(process.stderr).hexdigest(),
                )
            )
            if i:
                samples.append(elapsed)
        assert len(set(outputs)) == 1
        record["native"][label] = {
            "wall_seconds": samples,
            "median_wall_seconds": statistics.median(samples),
            "exit": outputs[0][0],
            "stdout_sha256": outputs[0][1],
            "stderr_sha256": outputs[0][2],
            "cpu_seconds": None,
            "peak_traced_python_bytes": None,
        }
    return record


def capacity(runs: int) -> list[dict[str, Any]]:
    """Finite independent scope/association/atom/frontier sweeps; unchanged ceilings."""
    records: list[dict[str, Any]] = []
    for axis in (
        "inventory",
        "edges",
        "rules",
        "sources",
        "services",
        "associations",
        "atoms",
        "deny_density",
        "frontier",
    ):
        for size in (1, 20, 25) if axis == "frontier" else (1, 3, 8):
            data = routine("routine")
            if axis == "inventory":
                for i in range(size * 25):
                    data["assets"].append({**data["assets"][0], "id": f"extra{i}"})
                    data["interfaces"].append(
                        {
                            **data["interfaces"][0],
                            "id": f"extra{i}_net",
                            "asset_id": f"extra{i}",
                            "ipv4": f"203.0.113.{i + 1}/24",
                        }
                    )
            elif axis == "edges":
                data["transport_edges"] = data["transport_edges"][: size * 100]
                selected = {e["id"] for e in data["transport_edges"] + data["forwarding_edges"]}
                for rule in data["rules"]:
                    rule["edge_ids"] = [e for e in rule["edge_ids"] if e in selected]
                data["rules"] = [r for r in data["rules"] if r["edge_ids"]]
            elif axis == "rules":
                data["rules"] = data["rules"][: size * 20]
            elif axis == "deny_density":
                for i, rule in enumerate(data["rules"]):
                    rule["effect"] = "deny" if i % size == 0 else "allow"
            elif axis == "sources":
                data["scenarios"][0]["origin_asset_ids"] = [f"a{i:03}" for i in range(size)]
            elif axis == "services":
                data["scenarios"][0]["destination_service_ids"] = [
                    f"svc{i:02}" for i in range(size)
                ]
            elif axis == "associations":
                for rule in data["rules"]:
                    rule["edge_ids"] = rule["edge_ids"][:size]
            elif axis == "atoms":
                data = routine("interval-heavy")
                data["rules"] = data["rules"][:size]
            else:
                # Policy absence yields a bounded frontier; topology remains declared.
                data["rules"] = []
                data["forwarding_edges"] = []
                data["transport_edges"] = [
                    {
                        "id": f"frontier{i}",
                        "source_interface_id": "a000_b",
                        "destination_interface_id": "a175_a",
                    }
                    for i in range(size)
                ]
            encoded = yaml.safe_dump(data, sort_keys=False).encode()
            validated = validate_bytes(encoded)
            operation: Callable[[], Any] = partial(
                trace_architecture, validated, "a000", "svc00", policy_evidence=True
            )
            if axis in {"sources", "services"}:
                operation = partial(exposure_architecture, validated, "scope")
            try:
                result = operation()
                measurements = measure(operation, runs)
                records.append(
                    {
                        "axis": axis,
                        "size": size,
                        "status": "completed",
                        "input_sha256": hashlib.sha256(encoded).hexdigest(),
                        "dimensions": {
                            "assets": len(validated.model.assets),
                            "interfaces": len(validated.model.interfaces),
                            "edges": len(validated.model.transport_edges)
                            + len(validated.model.forwarding_edges),
                            "rules": len(validated.model.rules),
                            "associations": sum(len(r.edge_ids) for r in validated.model.rules),
                            "services": len(validated.model.services),
                        },
                        "measurements": measurements,
                        "work": {
                            k: v
                            for k, v in asdict(result).items()
                            if k
                            in {
                                "work",
                                "atom_queries",
                                "state_edge_visits",
                                "edge_rule_atom_checks",
                            }
                        },
                    }
                )
            except ModelError as error:
                records.append(
                    {
                        "axis": axis,
                        "size": size,
                        "status": "rejected",
                        "diagnostics": [asdict(d) for d in error.diagnostics],
                    }
                )
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument(
        "--profiles",
        nargs="+",
        default=[
            "minimal",
            "mixed",
            "mixed-intervals",
            "tcp-udp",
            "comparison",
            "boundary",
            "blocked",
            "absent",
            "routine",
            "sparse",
            "deny-heavy",
            "dense-policy",
            "interval-heavy",
        ],
    )
    parser.add_argument("--capacity", action="store_true")
    parser.add_argument("--report-workflow", action="store_true")
    parser.add_argument("--confirmation", action="store_true")
    args = parser.parse_args()
    if args.runs < 5:
        parser.error("At least five repetitions are required")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    evidence: dict[str, Any] = {
        "environment": {
            "python": sys.version,
            "executable": sys.executable,
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "logical_cpus": os.cpu_count(),
        },
        "method": (
            "One warm-up; GC outside each timing; perf_counter_ns wall/process_time_ns CPU; "
            "separate single-operation tracemalloc (not RSS). Native subprocess CPU/allocation "
            "unavailable; no parent CPU substituted. Phase microbenchmarks overlap and do not "
            "sum; cProfile self/cumulative costs include instrumentation overhead. "
            "No concurrent suites/builds."
        ),
        "workloads": [],
    }
    for name in args.profiles:
        evidence["workloads"].append(
            report_workflow(name, args.output.parent, args.runs)
            if args.report_workflow
            else profile(name, args.output.parent, args.runs, args.confirmation)
        )
        args.output.write_text(
            json.dumps(evidence, sort_keys=True, indent=2) + "\n", encoding="utf-8"
        )
        print("Profiled", name, flush=True)
    if args.capacity:
        evidence["capacity"] = capacity(args.runs)
        args.output.write_text(
            json.dumps(evidence, sort_keys=True, indent=2) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    main()
