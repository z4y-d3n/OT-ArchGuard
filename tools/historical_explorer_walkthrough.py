"""Fictional offline historical Explorer scenarios, using the existing packet producer."""

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from otarchguard.drift.engine import compare
from otarchguard.drift.explorer import generate_explorer, verify_explorer
from otarchguard.evidence import lifecycle
from tools.drift_walkthrough import canonical, comparison_context, prepare


def _inventory(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in root.rglob("*")
        if p.is_file()
    }


def scenario(output: Path) -> dict[str, Any]:
    output.mkdir(exist_ok=False)
    selected = prepare(output / "sources")
    workspace = Path(selected["workspace"])
    reference = selected["periods"]["reference"]["analysis_id"]
    before = _inventory(workspace)
    results: dict[str, Any] = {}

    def present(name: str, selection: dict[str, Any], candidate: str) -> None:
        work = Path(selection["workspace"])
        ref = selection["periods"]["reference"]["analysis_id"]
        report = compare(
            work,
            selection["baseline_id"],
            [candidate],
            comparison_context(ref, candidate, selection["scope"]),
        )
        path = output / (name + "-report.json")
        path.write_bytes(canonical(report) + b"\n")
        result = generate_explorer(work, path, output / name, page_size=10)
        fresh = verify_explorer(output / name, workspace=work)
        if not fresh["analytical_reproduction"]:
            raise AssertionError("Published site failed exact source replay")
        results[name] = {
            "publication": result,
            "summary": report["summary"],
            "comparability": [p["comparability"] for p in report["comparisons"]],
        }

    present("normal", selected, selected["periods"]["candidate"]["analysis_id"])
    present("incomplete", selected, selected["periods"]["incomplete"]["analysis_id"])
    present("decoder", selected, selected["periods"]["decoder_one"]["analysis_id"])
    present("unchanged", selected, reference)
    if results["unchanged"]["summary"]["difference_records"] != 0:
        raise AssertionError("Identical selected revision acquired drift")
    if results["decoder"]["comparability"][0]["independent_collections"]:
        raise AssertionError("Decoder reinterpretation acquired an independent capture")
    original = output / "normal-report.json"
    repeated = generate_explorer(workspace, original, output / "normal-repeat", page_size=10)
    if repeated["bundle_id"] != results["normal"]["publication"]["bundle_id"]:
        raise AssertionError("Repeated generation changed canonical bundle identity")
    if _inventory(output / "normal") != _inventory(output / "normal-repeat"):
        raise AssertionError("Repeated bundle bytes differ")
    if _inventory(workspace) != before:
        raise AssertionError("Explorer generation modified its historical workspace")
    lifecycle.record_review(
        workspace,
        selected["baseline_id"],
        "revoke",
        "Fictional owner",
        "Retire teaching reference",
        predecessor=selected["approval_id"],
    )
    fresh = verify_explorer(output / "normal", workspace=workspace)
    revoked = generate_explorer(workspace, original, output / "revoked", page_size=10)
    if fresh["source_reproduction"]["current_baseline_status"] != "REVOKED":
        raise AssertionError("Revocation did not change current authority")
    dense = prepare(output / "dense-sources", scale=80, variations=False)
    present("dense", dense, dense["periods"]["candidate"]["analysis_id"])
    receipt = {
        "status": "passed",
        "fictional_only": True,
        "scenarios": results,
        "revoked": revoked,
        "fresh_verification_after_revocation": fresh,
        "byte_identical_repetition": True,
        "source_unchanged_by_explorer": True,
        "architecture_and_native_scenario": "normal",
        "human_visual_acceptance": "PENDING",
    }
    (output / "walkthrough.json").write_text(
        json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = scenario(args.output.absolute())
    print(json.dumps({"status": result["status"], "scenarios": sorted(result["scenarios"])}))


if __name__ == "__main__":
    main()
