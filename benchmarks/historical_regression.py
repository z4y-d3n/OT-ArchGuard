"""Run unchanged historical/native/capture operations with either installed checkpoint."""

import argparse
import hashlib
import json
import platform
import statistics
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import otarchguard
from otarchguard.architecture_comparison import compare_architecture_versions
from otarchguard.capture.observations import analyze_capture
from otarchguard.capture.protocols import enrich_capture
from otarchguard.drift.engine import compare
from otarchguard.drift.reports import verify_report
from otarchguard.evidence import lifecycle
from tools.drift_walkthrough import canonical, comparison_context


def measure(root: Path, output: Path, trials: int = 5) -> dict[str, Any]:
    selection = json.loads((root / "selection.json").read_bytes())
    workspace = Path(selection["workspace"])
    reference = selection["periods"]["reference"]["analysis_id"]
    candidate = selection["periods"]["candidate"]["analysis_id"]
    context = comparison_context(reference, candidate, selection["scope"])
    operations: dict[str, Callable[[], Any]] = {
        "workspace_verification": lambda: lifecycle.verify_lifecycle(workspace),
        "revision_inspection": lambda: lifecycle.list_revisions(workspace),
        "drift_comparison": lambda: compare(
            workspace, selection["baseline_id"], [candidate], context
        ),
        "report_reproduction": lambda: verify_report(workspace, root / "report.json"),
        "native_comparison": lambda: compare_architecture_versions(
            root / "reference-model.yaml", root / "candidate-model.yaml"
        ),
        "capture_observations": lambda: analyze_capture(root / "candidate.pcap"),
        "protocol_enrichment": lambda: enrich_capture(root / "candidate.pcap"),
    }
    result: dict[str, Any] = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "module": str(Path(otarchguard.__file__).resolve()),
        "trials": trials,
        "operations": {},
        "source_sha256": {
            p.relative_to(Path(otarchguard.__file__).parent).as_posix(): hashlib.sha256(
                p.read_bytes()
            ).hexdigest()
            for p in Path(otarchguard.__file__).parent.rglob("*.py")
        },
    }
    for name, operation in operations.items():
        expected = canonical(operation())
        times = []
        for _ in range(trials):
            start = time.perf_counter()
            actual = operation()
            times.append(time.perf_counter() - start)
            if canonical(actual) != expected:
                raise AssertionError("Measured result changed")
        result["operations"][name] = {
            "raw_seconds": times,
            "median_seconds": statistics.median(times),
            "output_sha256": hashlib.sha256(expected).hexdigest(),
        }
    output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    measure(args.input.absolute(), args.output.absolute())
    print("Historical/native/capture regression measurements completed")


if __name__ == "__main__":
    main()
