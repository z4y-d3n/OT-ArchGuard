"""Measured synthetic capture workloads; no active networking or real plant data."""

import argparse
import hashlib
import importlib
import json
import os
import platform
import struct
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


def process_peak_rss_bytes() -> int | None:
    """OS-reported lifetime resident high-water mark, including interpreter startup."""
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        class Counters(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                *[
                    (name, ctypes.c_size_t)
                    for name in (
                        "PeakWorkingSetSize",
                        "WorkingSetSize",
                        "QuotaPeakPagedPoolUsage",
                        "QuotaPagedPoolUsage",
                        "QuotaPeakNonPagedPoolUsage",
                        "QuotaNonPagedPoolUsage",
                        "PagefileUsage",
                        "PeakPagefileUsage",
                    )
                ],
            ]

        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD]
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        if not psapi.GetProcessMemoryInfo(
            kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb
        ):
            raise ctypes.WinError(ctypes.get_last_error())
        return int(counters.PeakWorkingSetSize)
    if sys.platform in {"linux", "darwin"}:
        resource = importlib.import_module("resource")
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return int(peak) * (1 if sys.platform == "darwin" else 1024)
    return None


def write_boundary_workload(path: Path, name: str, count: int) -> None:
    """Exercise maximum captured frames or many sections with bounded option metadata."""
    with path.open("xb") as stream:
        if name == "maxframe-64":
            size = 262_144
            stream.write(struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, size, 1))
            frame = bytes(size)  # Unsupported Ethernet type; never fabricated transport.
            for index in range(count):
                stream.write(struct.pack("<IIII", index, 0, size, size))
                stream.write(frame)
        else:

            def block(kind: int, body: bytes) -> bytes:
                size = 12 + len(body)
                return struct.pack("<II", kind, size) + body + struct.pack("<I", size)

            # One framed unknown option plus end marker occupies exactly 64 KiB.
            options = struct.pack("<HH", 2988, 65528) + bytes(65528) + bytes(4)
            for _ in range(count):
                stream.write(block(0x0A0D0D0A, struct.pack("<IHHq", 0x1A2B3C4D, 1, 0, -1)))
                stream.write(block(1, struct.pack("<HHI", 1, 0, 65535) + options))


def measure(root: Path, name: str, count: int, cardinality: int, skew: bool) -> dict[str, Any]:
    capture = root / (name + ".pcap")
    if name in {"maxframe-64", "metadata-sections-256"}:
        write_boundary_workload(capture, name, count)
    else:
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
            "parsed_records": observations["capture"]["packets"],
            "parsed_interfaces": len(observations["capture"]["interfaces"]),
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
        supplied_packet_records=0 if name == "metadata-sections-256" else count,
        supplied_sections=count if name == "metadata-sections-256" else 1,
        distinct_source_budget=cardinality,
        skew=skew,
        elapsed_seconds=elapsed,
        traced_peak_bytes=peak,
        process_peak_rss_bytes=process_peak_rss_bytes(),
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
            "maxframe-64",
            "metadata-sections-256",
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
        "maxframe-64": (64, 0, False),
        "metadata-sections-256": (256, 0, False),
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
        "memory_metric": "tracemalloc allocations and OS lifetime peak resident bytes, separately",
        "rss_scope": "Whole worker lifetime including startup, fixture writing and tracing; "
        "Windows PeakWorkingSetSize / POSIX ru_maxrss. Not a workload delta or enforced RSS cap.",
        "timing_scope": "Analysis, JSON/HTML generation and link audit; excludes fixture writing.",
        "conditions": "One run per isolated worker with tracing enabled; no throughput guarantee.",
    }
    (args.output / "benchmark.json").write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
