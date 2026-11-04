"""V15-04 generation-only installed-runtime latency and separate memory trials.

Prepare once, reuse exact inputs with both installations, and choose fresh output
directories. Receipts describe observations; they do not authorize source.
"""

import argparse
import gc
import hashlib
import importlib.metadata as metadata
import json
import os
import platform
import statistics
import subprocess
import sys
import time
import tracemalloc
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import otarchguard
from benchmarks.capture import process_peak_rss_bytes
from benchmarks.foundation import memory
from otarchguard.explorer import generate_explorer
from tools.synthetic_explorer import explorer_workload

ROOT = Path(__file__).resolve().parents[1]
CASES = {
    "small": (20, 30, 40, 3),
    "medium": (150, 200, 250, 5),
    "larger": (500, 600, 750, 6),
    "adversarial": (150, 200, 250, 5),
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def inventory(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): sha(p.read_bytes())
        for p in sorted(root.rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--runtime-receipt", type=Path, required=True)
    parser.add_argument("--cases", nargs="+", choices=CASES, default=list(CASES)[:3])
    parser.add_argument("--mode", choices=("wall", "allocation", "rss"), default="wall")
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--prepare", action="store_true")
    args = parser.parse_args()
    if sys.flags.optimize or not 1 <= args.runs <= 20:
        parser.error("Use unoptimized Python and 1..20 trials.")
    if args.mode == "rss" and len(args.cases) != 1:
        parser.error("RSS requires one case per fresh process.")
    package = Path(otarchguard.__file__).resolve().parent
    installed = {n: h for n, h in inventory(package).items() if n.endswith(".py")}
    expected = json.loads(args.runtime_receipt.read_bytes())["installed_module_sha256"]
    direct = json.loads(metadata.distribution("otarchguard").read_text("direct_url.json") or "{}")
    if (
        package.is_relative_to(ROOT / "src")
        or direct.get("dir_info", {}).get("editable", False)
        or installed != expected
    ):
        raise ValueError("Regular installed modules must match the supplied runtime receipt.")
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    receipt: dict[str, Any] = {
        "completed": False,
        "started_utc": datetime.now(UTC).isoformat(),
        "command": [sys.executable, "-m", "benchmarks.explorer_performance", *sys.argv[1:]],
        "driver_sha256": sha(Path(__file__).read_bytes()),
        "constructor_sha256": sha((ROOT / "tools/synthetic_explorer.py").read_bytes()),
        "git_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "git_tree": subprocess.check_output(
            ["git", "rev-parse", "HEAD^{tree}"], cwd=ROOT, text=True
        ).strip(),
        "git_status": subprocess.check_output(
            ["git", "status", "--porcelain=v1"], cwd=ROOT, text=True
        ),
        "runtime_receipt_sha256": sha(args.runtime_receipt.read_bytes()),
        "installed_module_sha256": installed,
        "distribution": metadata.version("otarchguard"),
        "native_engine": otarchguard.NATIVE_ENGINE_VERSION,
        "schema": 1,
        "python": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "logical_cpus": os.cpu_count(),
        "memory_at_start": memory(),
        "packages": {d.metadata["Name"]: d.version for d in metadata.distributions()},
        "mode": args.mode,
        "method": (
            "Wall: one excluded warmup per case/block, GC outside each perf_counter trial; "
            "preconstructed inputs; hashes outside timing. Allocation: separate single "
            "tracemalloc generation, no wall-latency claim. RSS: separate single generation, "
            "OS process-lifetime peak working set/RSS includes imports/setup, not isolated "
            "allocation. No measured children. No concurrent heavy campaigns. OS cache, "
            "antivirus, thermals and scheduling uncontrolled. Receipt is not authorization."
        ),
        "workloads": [],
    }

    def save() -> None:
        (out / "receipt.json").write_text(
            json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8"
        )

    save()
    for case in args.cases:
        work = args.inputs.resolve() / case
        if args.prepare:
            model, provenance = explorer_workload(work, *CASES[case], hostile=case == "adversarial")
        else:
            model = work / "accepted/architecture.yaml"
            provenance = work / "accepted/architecture.provenance.json"
        inputs = inventory(work)
        record: dict[str, Any] = {
            "case": case,
            "constructor": "tools.synthetic_explorer.explorer_workload",
            "parameters": list(CASES[case]),
            "hostile": case == "adversarial",
            "input_inventory": inputs,
            "input_sha256": {
                "model": sha(model.read_bytes()),
                "provenance": sha(provenance.read_bytes()),
            },
            "trials": [],
        }
        receipt["workloads"].append(record)
        (out / case).mkdir()
        expected_output = None
        count = args.runs + 1 if args.mode == "wall" else 1
        for number in range(count):
            gc.collect()
            site = out / case / f"trial-{number}"
            if args.mode == "allocation":
                tracemalloc.start()
            started = time.perf_counter()
            result = generate_explorer(model, site, provenance=provenance)
            elapsed = time.perf_counter() - started
            if args.mode == "allocation":
                _, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                record["peak_python_allocation_bytes"] = peak
            if args.mode == "rss":
                record["process_lifetime_peak_rss_bytes"] = process_peak_rss_bytes()
            output = inventory(site)
            if expected_output is None:
                expected_output = output
                record["output_inventory"] = output
                record["output_stats"] = result["site"]
            elif output != expected_output:
                raise ValueError("Repeated generation changed output bytes.")
            if args.mode == "wall":
                trial = {"seconds": elapsed, "phases": result["timings_seconds"]}
                if number == 0:
                    record["warmup"] = trial
                else:
                    record["trials"].append(trial)
            save()
        if inventory(work) != inputs:
            raise ValueError("Generation modified its immutable inputs.")
        if args.mode == "wall":
            timings = [t["seconds"] for t in record["trials"]]
            median = statistics.median(timings)
            record["summary"] = {
                "median": median,
                "mad": statistics.median(abs(v - median) for v in timings),
                "minimum": min(timings),
                "maximum": max(timings),
            }
        save()
        print(case, record.get("summary", args.mode), flush=True)
    receipt["completed"] = True
    receipt["finished_utc"] = datetime.now(UTC).isoformat()
    save()


if __name__ == "__main__":
    main()
