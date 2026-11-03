"""Paired installed-runtime workloads; run separately for each producer."""

import argparse
import hashlib
import json
import platform
import statistics
import subprocess
import sys
import sysconfig
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import otarchguard
from otarchguard.drift.engine import compare
from otarchguard.drift.explorer import generate_explorer, verify_explorer
from otarchguard.drift.reports import inspect_report
from otarchguard.reporting import write_report
from tools.drift_walkthrough import canonical, comparison_context, prepare


def benchmark(output: Path, *, scale: int = 512, trials: int = 3) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=False)
    selected = prepare(output / "sources", scale=scale, variations=False)
    workspace = Path(selected["workspace"])
    ref = selected["periods"]["reference"]["analysis_id"]
    candidate = selected["periods"]["candidate"]["analysis_id"]
    report = compare(
        workspace,
        selected["baseline_id"],
        [candidate],
        comparison_context(ref, candidate, selected["scope"]),
    )
    report_path = output / "report.json"
    report_path.write_bytes(canonical(report) + b"\n")
    receipt: dict[str, Any] = {
        "python": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "distribution": otarchguard.DISTRIBUTION_VERSION,
        "native_engine": otarchguard.NATIVE_ENGINE_VERSION,
        "module": otarchguard.__file__,
        "scale": scale,
        "trials": trials,
        "driver_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "method": "One warmup then untraced wall-clock trials; preparation excluded. "
        "No memory comparison; filesystem cache and scheduling uncontrolled.",
        "capture_sha256": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.rglob("*.pcap")
        },
        "producer_sha256": report["inputs"]["reference_sources"][0]["producer_semantics_sha256"],
        "workloads": {},
    }
    sequence = 0
    published: dict[str, Any] = {}

    def generation() -> None:
        nonlocal sequence, published
        sequence += 1
        published = generate_explorer(workspace, report_path, output / f"site-{sequence}")

    def measure(name: str, operation: Callable[[], Any]) -> None:
        operation()
        values = []
        for _ in range(trials):
            start = time.perf_counter()
            operation()
            values.append(time.perf_counter() - start)
        receipt["workloads"][name] = {"seconds": values, "median": statistics.median(values)}
        (output / "benchmark.json").write_text(json.dumps(receipt, indent=2) + "\n")

    measure("generation", generation)
    measure("replay", lambda: inspect_report(workspace, report_path))
    measure("report_write_1MiB", lambda: write_report(output / "atomic-report", b"x" * 1048576, ()))
    console = Path(sysconfig.get_path("scripts")) / (
        "otarchguard.exe" if sys.platform == "win32" else "otarchguard"
    )

    def startup() -> None:
        result = subprocess.run(
            [str(console), "--version"], cwd=output, capture_output=True, check=True, timeout=30
        )
        if result.stdout.strip().decode() != otarchguard.DISTRIBUTION_VERSION or result.stderr:
            raise AssertionError("Installed console identity mismatch")

    measure("cli_startup", startup)
    if (output / "atomic-report").read_bytes() != b"x" * 1048576:
        raise AssertionError("Report output loss")
    receipt["publication"] = published
    receipt["source_replay"] = verify_explorer(output / f"site-{sequence}", workspace=workspace)
    (output / "benchmark.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--scale", type=int, default=512)
    parser.add_argument("--trials", type=int, default=3)
    args = parser.parse_args()
    if not 1 <= args.scale <= 512 or not 1 <= args.trials <= 7:
        parser.error("Use scale 1..512 and trials 1..7")
    benchmark(args.output.resolve(), scale=args.scale, trials=args.trials)


if __name__ == "__main__":
    main()
