"""Finite metadata enrichment measurements; synthetic traffic, no active network."""

import argparse
import hashlib
import json
import platform
import time
import tracemalloc
from dataclasses import asdict
from pathlib import Path
from typing import Any

from benchmarks.capture import process_peak_rss_bytes
from otarchguard.capture.protocols import enrich_capture, validate_enrichment
from otarchguard.diagnostics import ModelError
from tools.protocol_workloads import TCP_MESSAGES, capture, ethernet, seven_frames, tcp_frame


def measure(root: Path, name: str, frames: list[bytes]) -> dict[str, Any]:
    path = capture(root / (name + ".pcap"), frames)
    tracemalloc.start()
    started = time.perf_counter()
    result: dict[str, Any]
    try:
        artifact = enrich_capture(path)
        encoded = json.dumps(artifact, sort_keys=True, ensure_ascii=True, indent=2) + "\n"
        result = {
            "status": "complete",
            "records": len(artifact["records"]),
            "counts": artifact["counts"],
            "output_bytes": len(encoded.encode()),
            "skipped_packets": artifact["skipped_packets"],
            "enrichment_sha256": artifact["enrichment_sha256"],
        }
    except ModelError as error:
        artifact = None
        result = {"status": "rejected", "diagnostics": [asdict(d) for d in error.diagnostics]}
    elapsed = time.perf_counter() - started
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    if artifact is not None:
        validate_enrichment(artifact)
    result.update(
        name=name,
        supplied_packets=len(frames),
        input_bytes=path.stat().st_size,
        input_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        elapsed_seconds=elapsed,
        traced_peak_bytes=peak,
        process_peak_rss_bytes=process_peak_rss_bytes(),
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    workloads = [
        (name + "-1k", [tcp_frame(payload, port)] * 1000) for name, port, payload in TCP_MESSAGES
    ]
    workloads += [
        ("dcp-1k", [seven_frames()[-1]] * 1000),
        ("mixed-7", seven_frames()),
        ("mixed-700", seven_frames() * 100),
        ("mixed-7000", seven_frames() * 1000),
        ("mixed-record-rejection", seven_frames() * 3000),
        ("malformed-1000", [tcp_frame(bytes.fromhex("056405c0010000040000"), 20000)] * 1000),
        ("view-ceiling", [tcp_frame(b"x" * 16385, 44818)]),
        ("unsupported-outer", [ethernet(b"x" * 32, 0x1234)] * 1000),
    ]
    result = {
        "measurement_version": 1,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "results": [measure(args.output, name, frames) for name, frames in workloads],
        "limitations": [
            "Single finite traced runs, not throughput or capacity guarantees.",
            "RSS is process lifetime high-water mark; workloads share one interpreter.",
            "Traced Python allocation peak differs from RSS; output includes packet provenance.",
            "Timing includes capture scanning and pretty serialization, excludes validation.",
        ],
    }
    (args.output / "benchmark.json").write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
