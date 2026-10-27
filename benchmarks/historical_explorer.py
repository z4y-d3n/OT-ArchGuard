"""Finite historical Explorer timing and separate allocation trials, without network."""

import argparse
import hashlib
import json
import platform
import statistics
import time
import tracemalloc
from collections.abc import Callable
from functools import partial
from pathlib import Path
from typing import Any

import otarchguard
from benchmarks.capture import process_peak_rss_bytes
from otarchguard.drift.engine import compare
from otarchguard.drift.explorer import generate_explorer
from otarchguard.drift.explorer_bundle import audit_files
from otarchguard.drift.explorer_render import render
from otarchguard.drift.reports import inspect_report
from tools.drift_walkthrough import canonical, comparison_context, prepare


def _timed(operation: Callable[[], Any], trials: int) -> dict[str, Any]:
    values = []
    for _ in range(trials):
        start = time.perf_counter()
        operation()
        values.append(time.perf_counter() - start)
    return {"raw_seconds": values, "median_seconds": statistics.median(values)}


def benchmark(
    output: Path, scales: tuple[int, ...] = (1, 64, 512), trials: int = 3
) -> dict[str, Any]:
    if not 1 <= trials <= 7 or any(not 1 <= n <= 512 for n in scales):
        raise ValueError("Use 1..7 trials and producer scales 1..512")
    output.mkdir(exist_ok=False)
    receipt: dict[str, Any] = {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "module": str(Path(otarchguard.__file__).resolve()),
        "fictional_only": True,
        "method": "Untraced timings; separate tracemalloc trial; RSS lifetime high water. "
        "Largest case reaches fictional packet producer ceiling, not engine maximum. "
        "OS cache and scheduling uncontrolled; no industrial-scale extrapolation.",
        "workloads": [],
    }
    for scale in scales:
        root = output / str(scale)
        selected = prepare(root, scale=scale, variations=False)
        workspace = Path(selected["workspace"])
        ref = selected["periods"]["reference"]["analysis_id"]
        cand = selected["periods"]["candidate"]["analysis_id"]
        report = compare(
            workspace,
            selected["baseline_id"],
            [cand],
            comparison_context(ref, cand, selected["scope"]),
        )
        report_path = root / "report.json"
        report_path.write_bytes(canonical(report) + b"\n")
        verified = inspect_report(workspace, report_path)["verification"]
        files = render(report, verified)
        # Audit the complete site, including the portable source metadata members.
        files["report.json"] = report_path.read_bytes()
        files["verification.json"] = canonical(verified) + b"\n"
        sequence = 0
        last: dict[str, Any] = {}

        def generation(work: Path = workspace, path: Path = report_path, dest: Path = root) -> None:
            nonlocal sequence, last
            sequence += 1
            last = generate_explorer(work, path, dest / ("site-" + str(sequence)))

        generation()  # warmup excluded
        generated = _timed(generation, trials)
        replayed = _timed(partial(inspect_report, workspace, report_path), trials)
        rendered = _timed(partial(render, report, verified), trials)
        audited = _timed(partial(audit_files, files), trials)
        tracemalloc.start()
        try:
            generation()
            _, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        receipt["workloads"].append(
            {
                "scale": scale,
                "full_generation": generated,
                "source_replay": replayed,
                "pure_render": rendered,
                "link_audit": audited,
                "separate_peak_python_bytes": peak,
                "process_lifetime_peak_rss_bytes": process_peak_rss_bytes(),
                "publication": last,
                "report_sha256": hashlib.sha256(report_path.read_bytes()).hexdigest(),
                "summary": report["summary"],
            }
        )
        (output / "benchmark.json").write_text(
            json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8"
        )
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--scales", default="1,64,512")
    parser.add_argument("--trials", type=int, default=3)
    args = parser.parse_args()
    benchmark(args.output.absolute(), tuple(int(n) for n in args.scales.split(",")), args.trials)
    print("Historical Explorer benchmark completed")


if __name__ == "__main__":
    main()
