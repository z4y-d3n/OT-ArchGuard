"""Run fixed workloads with separate untraced timing and traced Python memory."""

import argparse
import gc
import hashlib
import importlib.metadata
import json
import os
import platform
import statistics
import tracemalloc
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from time import perf_counter
from typing import Any

from benchmarks.workloads import source_bytes
from otarchguard.api import validate_bytes
from otarchguard.comparison import compare_bytes
from otarchguard.contract import RESOURCE_LIMITS
from otarchguard.diagnostics import ModelError
from otarchguard.exposure import ExposureResult, exposure_bytes
from otarchguard.intervals import partition
from otarchguard.reporting import build_report, html_report


def measure(operation: Callable[[], Any], runs: int) -> tuple[dict[str, Any], Any]:
    operation()  # Unrecorded warm-up; each run creates a fresh analysis engine.
    elapsed = []
    result: Any = None
    for _ in range(runs):
        gc.collect()
        start = perf_counter()
        result = operation()
        elapsed.append(perf_counter() - start)
    result = None
    gc.collect()
    tracemalloc.start()
    try:
        result = operation()
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return {
        "elapsed_seconds": elapsed,
        "median_seconds": statistics.median(elapsed),
        "maximum_seconds": max(elapsed),
        "peak_traced_python_bytes": peak,
        "memory_method": "Separate fresh operation with tracemalloc; not process RSS",
    }, result


def run(profile: str, runs: int) -> dict[str, Any]:
    source = source_bytes(profile)
    validated = validate_bytes(source)
    model = validated.model
    atoms = partition(model, frozenset(s.id for s in model.services), RESOURCE_LIMITS)
    record: dict[str, Any] = {
        "profile": profile,
        "input_sha256": hashlib.sha256(source).hexdigest(),
        "model_sha256": validated.sha256,
        "input_bytes": len(source),
        "counts": {
            "assets": len(model.assets),
            "interfaces": len(model.interfaces),
            "edges": len(model.transport_edges) + len(model.forwarding_edges),
            "transport_edges": len(model.transport_edges),
            "forwarding_edges": len(model.forwarding_edges),
            "rules": len(model.rules),
            "services": len(model.services),
            "origins": 10,
            "states": 2 * len(model.interfaces),
            "edge_rule_associations": sum(len(r.edge_ids) for r in model.rules),
        },
        "default_limits": asdict(RESOURCE_LIMITS),
        "protocol_port_atoms": {protocol: len(values) for protocol, values in atoms.items()},
    }
    start = perf_counter()
    try:
        exposure, result = measure(lambda: exposure_bytes(source, "scope"), runs)
    except ModelError as error:
        record.update(
            status="rejected",
            rejection_seconds=perf_counter() - start,
            diagnostics=[asdict(d) for d in error.diagnostics],
        )
        return record
    assert isinstance(result, ExposureResult)
    record.update(
        status="completed",
        exposure=exposure,
        analysis_passed=result.passed,
        observations=len(result.observations),
        destination_assets=len(result.destination_assets),
        atom_queries=result.atom_queries,
        state_edge_visits=result.state_edge_visits,
        edge_rule_atom_checks=result.edge_rule_atom_checks,
    )
    record["target"] = {
        "time_seconds": 30,
        "peak_traced_python_bytes": 512 * 1024 * 1024,
        "time_passed": exposure["maximum_seconds"] <= 30,
        "memory_passed": exposure["peak_traced_python_bytes"] <= 512 * 1024 * 1024,
        "applies_to": "routine exposure pipeline only; no comparison/report target asserted",
    }
    if profile == "routine":
        comparison, compared = measure(lambda: compare_bytes(source, source, "scope"), runs)
        comparison["identity_deltas_empty"] = not (
            compared.newly_reachable or compared.no_longer_reachable or compared.inventory_changes
        )
        record["comparison"] = comparison
        reporting, rendered = measure(
            lambda: html_report(build_report("exposure", (validated,), result), (validated,)), runs
        )
        reporting["html_bytes"] = len(rendered)
        record["reporting"] = reporting
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--runs", type=int, default=5)
    args = parser.parse_args()
    if args.runs < 5:
        parser.error("At least five measured runs are required")
    records = [
        run(profile, args.runs)
        for profile in ("routine", "sparse", "deny-heavy", "dense-policy", "interval-heavy")
    ]
    evidence = {
        "environment": {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "logical_cpus": os.cpu_count(),
            "dependencies": {
                name: importlib.metadata.version(name) for name in ("pydantic", "PyYAML", "typer")
            },
        },
        "method": "Full in-memory YAML bytes -> validation/hash -> exposure/all intents; "
        "source generation excluded; no tracemalloc during timing; one warm-up then GC "
        "before each run. Comparison includes both validated inputs; reporting uses "
        "precomputed evidence and excludes file I/O.",
        "workloads": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    first = records[0]
    return (
        0
        if (
            first["status"] == "completed"
            and first["target"]["time_passed"]
            and first["target"]["memory_passed"]
        )
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
