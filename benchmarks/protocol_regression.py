"""Fixed-input enrichment regression: repeated latency and separate allocation trials.

The older protocols benchmark intentionally measures single traced observations.
This companion retains its wire producers and serialization boundary while
separating latency from allocation tracing for a matched checkpoint comparison.
"""

import argparse
import hashlib
import json
import statistics
import time
import tracemalloc
from dataclasses import asdict
from pathlib import Path
from typing import Any

from benchmarks.capture import process_peak_rss_bytes
from otarchguard.capture.protocols import enrich_capture, validate_enrichment
from otarchguard.diagnostics import ModelError
from tools.history_performance_worker import canonical, file_manifest, package_identity
from tools.protocol_workloads import capture, ethernet, seven_frames, tcp_frame


def prepare(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=False)
    workloads = {
        "mixed-700": seven_frames() * 100,
        "mixed-7000": seven_frames() * 1000,
        "supported-unsupported-1400": (seven_frames() + [ethernet(b"x" * 32, 0x1234)] * 7) * 100,
        "malformed-1000": [tcp_frame(bytes.fromhex("056405c0010000040000"), 20000)] * 1000,
        "view-ceiling": [tcp_frame(b"x" * 16385, 44818)],
        "metadata-ceiling": seven_frames() * 3000,
    }
    for name, frames in workloads.items():
        capture(root / (name + ".pcap"), frames)
    (root / "inputs.json").write_bytes(canonical(file_manifest(root)) + b"\n")


def _run(path: Path) -> tuple[dict[str, Any], dict[str, Any] | None]:
    try:
        artifact = enrich_capture(path)
        encoded = json.dumps(artifact, sort_keys=True, ensure_ascii=True, indent=2) + "\n"
        return {
            "status": "complete",
            "records": len(artifact["records"]),
            "counts": artifact["counts"],
            "skipped_packets": artifact["skipped_packets"],
            "output_bytes": len(encoded.encode("ascii")),
            "output_sha256": hashlib.sha256(encoded.encode("ascii")).hexdigest(),
            "enrichment_sha256": artifact["enrichment_sha256"],
        }, artifact
    except ModelError as error:
        return {
            "status": "rejected",
            "diagnostics": [asdict(d) for d in error.diagnostics],
        }, None


def measure(root: Path, output: Path, trials: int = 3) -> dict[str, Any]:
    if not 3 <= trials <= 7:
        raise ValueError("Use 3..7 matched latency trials")
    expected_inputs = json.loads((root / "inputs.json").read_bytes())
    actual_inputs = file_manifest(root)
    del actual_inputs["inputs.json"]
    if actual_inputs != expected_inputs:
        raise ValueError("Fixed protocol workload inventory changed")
    receipt: dict[str, Any] = {
        "package": package_identity(),
        "trials": trials,
        "input_sha256": expected_inputs,
        "method": "One excluded warmup; repeated untraced scan+pretty serialization; "
        "validation outside measurement; separate traced trial. RSS is process lifetime "
        "high water, not an operation delta. No capacity or worst-case latency claim.",
        "workloads": {},
    }
    for name in sorted(expected_inputs):
        path = root / name
        expected, artifact = _run(path)
        if artifact is not None:
            validate_enrichment(artifact)
        if name == "metadata-ceiling.pcap":
            if expected["status"] != "rejected" or not any(
                d["code"] == "LIMIT_EXCEEDED" for d in expected["diagnostics"]
            ):
                raise AssertionError("Metadata workload must fail its declared resource ceiling")
        elif expected["status"] != "complete":
            raise AssertionError("Bounded nonfatal workload unexpectedly failed")
        values = []
        for _ in range(trials):
            started = time.perf_counter()
            actual, artifact = _run(path)
            values.append(time.perf_counter() - started)
            if actual != expected:
                raise AssertionError("Latency trial changed canonical output")
            if artifact is not None:
                validate_enrichment(artifact)
        tracemalloc.start()
        try:
            actual, artifact = _run(path)
            _, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        if actual != expected:
            raise AssertionError("Allocation trial changed canonical output")
        if artifact is not None:
            validate_enrichment(artifact)
        receipt["workloads"][name] = {
            "result": expected,
            "input_bytes": path.stat().st_size,
            "raw_seconds": values,
            "median_seconds": statistics.median(values),
            "min_seconds": min(values),
            "max_seconds": max(values),
            "separate_peak_python_bytes": peak,
            "process_lifetime_peak_rss_bytes": process_peak_rss_bytes(),
        }
    final_inputs = file_manifest(root)
    del final_inputs["inputs.json"]
    if final_inputs != expected_inputs:
        raise AssertionError("Measurement mutated its fixed inputs")
    output.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--trials", type=int, default=3)
    args = parser.parse_args()
    if args.prepare:
        prepare(args.input)
    else:
        if args.output is None:
            parser.error("--output is required for measurement")
        measure(args.input, args.output, args.trials)
    print("Fixed protocol regression completed")


if __name__ == "__main__":
    main()
