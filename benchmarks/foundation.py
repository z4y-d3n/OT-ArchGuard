"""Measure the Gate V15-01 foundation using existing fictional workload constructors.

Run from a reviewed checkout with a regular installed matching package:
python -m benchmarks.foundation --output output/NEW_EMPTY_DIRECTORY

This typed reproduction harness preserves the operations of the local raw
measurement driver; earlier receipts identify that original driver by hash.
"""

import argparse
import ctypes
import dataclasses
import gc
import hashlib
import importlib.metadata
import json
import os
import platform
import statistics
import subprocess
import sys
import sysconfig
import time
import tracemalloc
from collections.abc import Callable
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from typing import Any

import otarchguard
from benchmarks.capture import process_peak_rss_bytes
from benchmarks.workloads import source_bytes
from otarchguard.api import validate_bytes
from otarchguard.capture.observations import analyze_capture
from otarchguard.capture.protocols import enrich_capture
from otarchguard.drift.engine import compare
from otarchguard.drift.explorer import generate_explorer as historical_explorer
from otarchguard.drift.explorer_bundle import verify_bundle
from otarchguard.drift.reports import inspect_report
from otarchguard.evidence.lifecycle import verify_lifecycle
from otarchguard.explorer import generate_explorer
from otarchguard.trace import trace_bytes
from tools.capture_workloads import write_pcap
from tools.drift_walkthrough import canonical, comparison_context, prepare
from tools.protocol_workloads import capture, seven_frames
from tools.synthetic_explorer import explorer_workload

ROOT = Path(__file__).resolve().parents[1]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def inventory(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): sha(p.read_bytes())
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def memory() -> dict[str, int] | None:
    if sys.platform != "win32":
        return None

    class Status(ctypes.Structure):
        total_physical: int
        available_physical: int
        _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [
            (n, ctypes.c_ulonglong)
            for n in (
                "total_physical",
                "available_physical",
                "total_page",
                "available_page",
                "total_virtual",
                "available_virtual",
                "available_extended",
            )
        ]

    status = Status()
    status.length = ctypes.sizeof(status)
    if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        return {
            "total_physical_bytes": status.total_physical,
            "available_physical_bytes": status.available_physical,
        }
    return None


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--skip-allocation",
        action="append",
        default=[],
        metavar="WORKLOAD",
        help="Exact workload name: retain five timings and record allocation trial as skipped.",
    )
    args = parser.parse_args()
    if sys.flags.optimize:
        parser.error("Run without -O; benchmark identity assertions must be active.")
    known_workloads = (
        {
            "native-validation-routine",
            "native-trace-routine",
            "capture-parsing-index-repeated-10k",
            "bounded-industrial-mixed-700",
            "installed-cli-startup-version",
            "installed-cli-first-validation",
        }
        | {"architecture-explorer-" + name for name in ("small", "medium", "larger")}
        | {
            operation + "-" + str(scale)
            for operation in (
                "historical-lifecycle-validation",
                "historical-drift",
                "historical-source-replay",
                "historical-explorer-generation",
                "historical-portable-verification",
            )
            for scale in (1, 64, 512)
        }
    )
    if not set(args.skip_allocation) <= known_workloads:
        parser.error("Use an exact supported workload name for --skip-allocation.")
    out = args.output.absolute()
    out.mkdir(parents=True, exist_ok=False)
    package = Path(otarchguard.__file__).resolve().parent
    installed = inventory(package)
    module_hashes = {n: d for n, d in installed.items() if n.endswith(".py")}
    source = {n: d for n, d in inventory(ROOT / "src/otarchguard").items() if n.endswith(".py")}
    assert module_hashes == source and not package.is_relative_to(ROOT / "src")
    direct = json.loads(
        importlib.metadata.distribution("otarchguard").read_text("direct_url.json") or "{}"
    )
    assert not direct.get("dir_info", {}).get("editable", False)
    receipt: dict[str, Any] = {
        "completed": False,
        "source_commit": git("rev-parse", "HEAD"),
        "source_tree": git("rev-parse", "HEAD^{tree}"),
        "working_tree_at_start": git("status", "--porcelain=v1"),
        "started_utc": datetime.now(UTC).isoformat(),
        "command_argv": [sys.executable, "-m", "benchmarks.foundation", *sys.argv[1:]],
        "command": subprocess.list2cmdline(
            [sys.executable, "-m", "benchmarks.foundation", *sys.argv[1:]]
        ),
        "script_sha256": sha(Path(__file__).read_bytes()),
        "environment": {
            "python": sys.version,
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "logical_processors": os.cpu_count(),
            "memory_at_start": memory(),
            "installed_package": str(package),
            "distribution": otarchguard.DISTRIBUTION_VERSION,
            "native_engine": otarchguard.NATIVE_ENGINE_VERSION,
            "installed_module_sha256": module_hashes,
            "source_module_match": True,
            "packages": {d.metadata["Name"]: d.version for d in importlib.metadata.distributions()},
            "offline_guard": os.environ.get("OTARCHGUARD_OFFLINE_CHECK"),
        },
        "method": (
            "Each operation: one untimed warmup; five wall-clock trials with GC before each; "
            "separate sixth traced-allocation operation. Hash/output checks happen after timed "
            "intervals. Fixture preparation excluded. Shared interpreter OS lifetime high-water "
            "RSS includes earlier workloads and tracing, not per-workload RSS. File cache and "
            "scheduler uncontrolled. Five startup/first-run subprocess trials likewise follow "
            "an untimed warmup; parent traced allocation does not measure child memory."
        ),
        "comparison": (
            "Baseline characterization only. No optimization or paired performance change claim; "
            "candidate production source is required to remain byte-identical."
        ),
        "workloads": [],
    }

    def save() -> None:
        (out / "receipt.json").write_text(
            json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8"
        )

    def measure(
        name: str,
        operation: Callable[[], Any],
        identity: Callable[[Any], Any],
        fixtures: dict[str, Any],
        scope: str,
        *,
        trace: bool = True,
    ) -> dict[str, Any]:
        receipt["active_workload"] = name
        save()
        print("START", name, flush=True)
        try:
            expected = identity(operation())
        except BaseException as error:
            receipt["active_error"] = {"phase": "warmup", "type": type(error).__name__}
            save()
            raise
        elapsed: list[float] = []
        row: dict[str, Any] = {
            "name": name,
            "status": "TIMING_IN_PROGRESS",
            "timing_scope": scope,
            "fixture_identity": fixtures,
            "warmup_runs": 1,
            "measured_runs": 0,
            "wall_seconds": elapsed,
            "separate_traced_python_peak_bytes": None,
            "allocation_status": "PENDING",
            "output_identity": expected,
            "timed_output_identity_match": None,
        }
        receipt["workloads"].append(row)
        save()
        for _ in range(5):
            gc.collect()
            started = time.perf_counter()
            try:
                result = operation()
                elapsed.append(time.perf_counter() - started)
                row["timed_output_identity_match"] = identity(result) == expected
                assert row["timed_output_identity_match"], (name, "nondeterministic output")
            except BaseException as error:
                row.update(status="ERROR", error_type=type(error).__name__)
                save()
                raise
            median = statistics.median(elapsed)
            row.update(
                measured_runs=len(elapsed),
                median_seconds=median,
                min_seconds=min(elapsed),
                max_seconds=max(elapsed),
                median_absolute_deviation_seconds=statistics.median(
                    abs(x - median) for x in elapsed
                ),
            )
            # Receipt writes and identity checks are outside the timed interval.
            save()
        row["timed_output_identity_match"] = True
        row["status"] = "TIMING_COMPLETE_ALLOCATION_PENDING"
        save()
        result = None
        peak: int | None = None
        requested_skip = name in args.skip_allocation
        if trace and not requested_skip:
            gc.collect()
            tracemalloc.start()
            try:
                result = operation()
                _, peak = tracemalloc.get_traced_memory()
                assert identity(result) == expected
            except BaseException as error:
                row.update(
                    status="ERROR", allocation_status="ERROR", error_type=type(error).__name__
                )
                save()
                raise
            finally:
                tracemalloc.stop()
        row.update(
            status="PASS",
            separate_traced_python_peak_bytes=peak,
            allocation_status="PASS" if trace and not requested_skip else "SKIP",
            memory_method=(
                "Separate tracemalloc operation; Python allocations, not RSS"
                if trace and not requested_skip
                else "Explicit --skip-allocation request; timing retained, allocation trial omitted"
                if requested_skip
                else "Child memory not measured; no parent allocation claim"
            ),
            shared_process_lifetime_peak_rss_bytes=process_peak_rss_bytes(),
            rss_scope=(
                "Shared interpreter lifetime OS high-water mark; includes previous workloads, "
                "fixture preparation and traced trials; not per-operation RSS or delta; "
                "excludes console child memory"
            ),
        )
        save()
        print("DONE", name, row["median_seconds"], flush=True)
        return row

    routine = source_bytes("routine")
    (out / "native-routine.yaml").write_bytes(routine)
    fixture = {
        "constructor": "benchmarks.workloads.source_bytes(routine)",
        "sha256": sha(routine),
        "bytes": len(routine),
    }
    measure(
        "native-validation-routine",
        lambda: validate_bytes(routine),
        lambda v: v.sha256,
        fixture,
        "In-memory YAML decode, validation, normalization and model hash",
    )
    measure(
        "native-trace-routine",
        lambda: trace_bytes(routine, "a000", "svc00"),
        lambda v: sha(canonical(dataclasses.asdict(v))),
        fixture,
        "In-memory validation plus one exact source/service trace",
    )

    for name, assets, interfaces, connectors, sources in [
        ("small", 20, 30, 40, 3),
        ("medium", 150, 200, 250, 5),
        ("larger", 500, 600, 750, 6),
    ]:
        work = out / ("architecture-" + name)
        model, sidecar = explorer_workload(work, assets, interfaces, connectors, sources)
        sequence = 0

        def generation(work: Path = work, model: Path = model, sidecar: Path = sidecar) -> Path:
            nonlocal sequence
            sequence += 1
            dest = work / ("site-" + str(sequence))
            generate_explorer(model, dest, provenance=sidecar)
            return dest

        measure(
            "architecture-explorer-" + name,
            generation,
            lambda p: sha(canonical(inventory(p))),
            {
                "constructor": "tools.synthetic_explorer.explorer_workload",
                "assets": assets,
                "interfaces": interfaces,
                "connectors": connectors,
                "sources": sources,
                "model_sha256": sha(model.read_bytes()),
                "provenance_sha256": sha(sidecar.read_bytes()),
            },
            "Installed generation, validation, rendering, file publication and internal "
            "link audit; fixture preparation excluded",
        )

    pcap = out / "repeated-10k.pcap"
    write_pcap(pcap, 10000, cardinality=0, skew=False)
    measure(
        "capture-parsing-index-repeated-10k",
        lambda: analyze_capture(pcap),
        lambda v: v["observations_sha256"],
        {
            "constructor": (
                "tools.capture_workloads.write_pcap(count=10000,cardinality=0,skew=False)"
            ),
            "sha256": sha(pcap.read_bytes()),
            "bytes": pcap.stat().st_size,
        },
        "Capture reading, parsing, bounded host/conversation indexing and canonical observation "
        "identity; no HTML generation",
    )
    proto = capture(out / "mixed-700.pcap", seven_frames() * 100)
    measure(
        "bounded-industrial-mixed-700",
        lambda: enrich_capture(proto),
        lambda v: v["enrichment_sha256"],
        {
            "constructor": "tools.protocol_workloads.seven_frames()*100",
            "sha256": sha(proto.read_bytes()),
            "bytes": proto.stat().st_size,
        },
        "Seven existing bounded protocol families, capture scan and metadata extraction; "
        "no deep decoding or serialization",
    )

    for scale in (1, 64, 512):
        work = out / ("history-" + str(scale))
        selected = prepare(work, scale=scale, variations=False)
        workspace = Path(selected["workspace"])
        before = inventory(workspace)
        fixtures = {
            "constructor": "tools.drift_walkthrough.prepare(scale="
            + str(scale)
            + ",variations=False)",
            "scale": scale,
            "workspace_manifest_sha256": sha(canonical(before)),
            "workspace_files": len(before),
            "workspace_bytes": sum(p.stat().st_size for p in workspace.rglob("*") if p.is_file()),
            "input_files": {
                p.name: sha(p.read_bytes()) for p in sorted(work.iterdir()) if p.is_file()
            },
            "baseline_id": selected["baseline_id"],
        }
        measure(
            "historical-lifecycle-validation-" + str(scale),
            partial(verify_lifecycle, workspace),
            lambda v: sha(canonical(v)),
            fixtures,
            "Read-only full collection/attachment/revision/baseline/review semantic "
            "and dependency validation",
        )
        ref = selected["periods"]["reference"]["analysis_id"]
        cand = selected["periods"]["candidate"]["analysis_id"]
        context = comparison_context(ref, cand, selected["scope"])

        def operation(
            workspace: Path = workspace,
            baseline_id: str = selected["baseline_id"],
            candidate: str = cand,
            context: dict[str, Any] = context,
        ) -> dict[str, Any]:
            return compare(workspace, baseline_id, [candidate], context)

        measure(
            "historical-drift-" + str(scale),
            operation,
            lambda v: v["drift_id"],
            fixtures,
            "Complete source-bound drift comparison including full historical validation "
            "and requested native trace",
        )
        report = operation()
        report_path = work / "report.json"
        report_path.write_bytes(canonical(report) + b"\n")
        measure(
            "historical-source-replay-" + str(scale),
            partial(inspect_report, workspace, report_path),
            lambda v: sha(canonical(v)),
            {**fixtures, "report_sha256": sha(report_path.read_bytes())},
            "Read-only report source validation and reproducible source-dependent replay",
        )
        sequence = 0

        def history_generation(
            work: Path = work, workspace: Path = workspace, report_path: Path = report_path
        ) -> Path:
            nonlocal sequence
            sequence += 1
            dest = work / ("site-" + str(sequence))
            historical_explorer(workspace, report_path, dest)
            return dest

        measure(
            "historical-explorer-generation-" + str(scale),
            history_generation,
            lambda p: sha(canonical(inventory(p))),
            {**fixtures, "report_sha256": sha(report_path.read_bytes())},
            "Full Explorer source replay, semantic HTML/CSS/SVG render, link audit "
            "and portable bundle publication",
        )
        measure(
            "historical-portable-verification-" + str(scale),
            partial(verify_bundle, work / "site-1"),
            lambda v: sha(canonical(v)),
            {**fixtures, "bundle_manifest_sha256": sha(canonical(inventory(work / "site-1")))},
            "Read-only exact portable bundle inventory, SHA-256 and link/presentation audit; "
            "no source replay",
        )
        assert before == inventory(workspace), "Historical source workspace mutated"

    console = Path(sysconfig.get_path("scripts")) / (
        "otarchguard.exe" if os.name == "nt" else "otarchguard"
    )

    def child(arguments: list[str]) -> dict[str, Any]:
        completed = subprocess.run(
            [str(console), *arguments], cwd=out, capture_output=True, check=False, timeout=60
        )
        assert completed.returncode == 0, (arguments, completed.returncode, completed.stderr)
        return {
            "exit": completed.returncode,
            "stdout_sha256": sha(completed.stdout),
            "stderr_sha256": sha(completed.stderr),
            "stdout": completed.stdout.decode() if arguments == ["--version"] else None,
        }

    measure(
        "installed-cli-startup-version",
        lambda: child(["--version"]),
        lambda v: v,
        {"console": str(console), "arguments": ["--version"], "working_directory": str(out)},
        "Fresh native console process creation, Python and all CLI imports, version output "
        "and process exit; no child memory measurement",
        trace=False,
    )
    minimal = (ROOT / "tests/fixtures/minimal-valid.yaml").resolve()
    measure(
        "installed-cli-first-validation",
        lambda: child(["validate", str(minimal)]),
        lambda v: v,
        {
            "console": str(console),
            "arguments": ["validate", str(minimal)],
            "sha256": sha(minimal.read_bytes()),
            "working_directory": str(out),
        },
        "Fresh native console process plus first fictional model validation; "
        "no child memory measurement",
        trace=False,
    )
    receipt["finished_utc"] = datetime.now(UTC).isoformat()
    receipt["working_tree_at_end"] = git("status", "--porcelain=v1")
    receipt["pass_count"] = len(receipt["workloads"])
    receipt["failure_count"] = 0
    receipt["allocation_pass_count"] = sum(
        r["allocation_status"] == "PASS" for r in receipt["workloads"]
    )
    receipt["allocation_skip_count"] = sum(
        r["allocation_status"] == "SKIP" for r in receipt["workloads"]
    )
    receipt["completed"] = True
    receipt.pop("active_workload", None)
    receipt["installed_module_sha256_at_end"] = {
        n: d for n, d in inventory(package).items() if n.endswith(".py")
    }
    assert receipt["installed_module_sha256_at_end"] == module_hashes
    save()


if __name__ == "__main__":
    main()
