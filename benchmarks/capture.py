"""Measured synthetic capture workloads; no active networking or real plant data."""

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
import tracemalloc
from dataclasses import asdict
from pathlib import Path
from typing import Any

from otarchguard.capture.explorer import generate_site
from otarchguard.capture.observations import analyze_capture
from otarchguard.diagnostics import ModelError
from tools.capture_workloads import write_pcap


def measure(root: Path, name: str, count: int, cardinality: int, skew: bool) -> dict[str, Any]:
    capture = root / (name + ".pcap")
    write_pcap(capture, count, cardinality=cardinality, skew=skew)
    tracemalloc.start()
    started = time.perf_counter()
    result: dict[str, Any]
    try:
        observations = analyze_capture(capture)
        site = generate_site(observations, root / (name + "-site"))
        result = {
            "status": "complete",
            "flows": len(observations["flows"]),
            "hosts": len(observations["hosts"]),
            "output_bytes": site["output_bytes"],
            "observations_sha256": observations["observations_sha256"],
        }
    except ModelError as error:
        result = {
            "status": "rejected",
            "diagnostic_codes": [d.code for d in error.diagnostics],
            "diagnostics": [asdict(d) for d in error.diagnostics],
        }
    elapsed = time.perf_counter() - started
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    with capture.open("rb") as stream:
        input_sha256 = hashlib.file_digest(stream, "sha256").hexdigest()
    result.update(
        name=name,
        packets=count,
        distinct_source_budget=cardinality,
        skew=skew,
        elapsed_seconds=elapsed,
        traced_peak_bytes=peak,
        input_bytes=capture.stat().st_size,
        input_sha256=input_sha256,
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--worker",
        choices=[
            "repeated-1k",
            "repeated-10k",
            "repeated-100k",
            "repeated-250k",
            "cardinality-1k",
            "skew-10k",
            "cardinality-rejection",
        ],
    )
    args = parser.parse_args()
    workloads = {
        "repeated-1k": (1000, 0, False),
        "repeated-10k": (10000, 0, False),
        "repeated-100k": (100000, 0, False),
        "repeated-250k": (250000, 0, False),
        "cardinality-1k": (1000, 1000, False),
        "skew-10k": (10000, 10000, True),
        "cardinality-rejection": (10000, 10000, False),
    }
    if args.worker:
        print(
            json.dumps(measure(args.output, args.worker, *workloads[args.worker]), sort_keys=True)
        )
        return
    args.output.mkdir(exist_ok=False)
    measured = []
    for name in workloads:
        child = subprocess.run(
            [
                sys.executable,
                "-m",
                "benchmarks.capture",
                "--output",
                str(args.output),
                "--worker",
                name,
            ],
            capture_output=True,
            timeout=600,
        )
        if child.returncode:
            raise RuntimeError(child.stderr.decode(errors="replace"))
        row = json.loads(child.stdout)
        expected = "rejected" if name == "cardinality-rejection" else "complete"
        if row["status"] != expected:
            raise RuntimeError(f"Unexpected benchmark outcome: {row}")
        if expected == "rejected" and not all(
            d["category"] == "resource_limit" for d in row["diagnostics"]
        ):
            raise RuntimeError(f"Expected resource rejection, received: {row}")
        measured.append(row)
        print(json.dumps(row, sort_keys=True), flush=True)
    report = {
        "synthetic_only": True,
        "python": platform.python_version(),
        "python_build": sys.version,
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "processor": platform.processor(),
        "logical_cpus": os.cpu_count(),
        "workloads": measured,
        "memory_metric": "tracemalloc peak Python allocations; not whole-process RSS",
        "timing_scope": "Analysis, JSON/HTML generation and link audit; excludes fixture writing.",
        "conditions": "One run per isolated worker with tracing enabled; no throughput guarantee.",
    }
    (args.output / "benchmark.json").write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
