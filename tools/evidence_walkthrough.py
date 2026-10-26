"""Exercise the fictional V14-00 vertical slice through the installed offline CLI."""

import argparse
import hashlib
import json
import os
import subprocess
import sysconfig
from pathlib import Path
from typing import Any

from tools.capture_workloads import write_pcap

ROOT = Path(__file__).resolve().parents[1]


def walkthrough(output: Path) -> dict[str, Any]:
    output.mkdir(exist_ok=False)
    console = Path(sysconfig.get_path("scripts")) / (
        "otarchguard.exe" if os.name == "nt" else "otarchguard"
    )
    commands: list[list[str]] = []

    def run(*args: str) -> dict[str, Any]:
        commands.append(list(args))
        child = subprocess.run([str(console), *args], capture_output=True, timeout=120)
        if child.returncode or child.stderr:
            raise RuntimeError("Installed evidence walkthrough command failed")
        result: dict[str, Any] = json.loads(child.stdout)
        return result

    industrial = ROOT / "tests/fixtures/protocol-corpus/synthetic-industrial.pcap"
    plant = output / "fictional-second.pcap"
    write_pcap(plant)
    inputs = [industrial, plant]
    before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    workspace = output / "workspace"
    run("evidence", "init", str(workspace))
    snapshots = []
    for number, capture in enumerate(inputs, 1):
        site = output / f"capture-{number}"
        run("capture", "analyze", str(capture), "--output", str(site))
        enrichment = run(
            "capture", "enrich", str(capture), "--output", str(output / f"enrichment-{number}.json")
        )
        receipt = run(
            "evidence",
            "add",
            str(workspace),
            str(site / "observations.json"),
            "--label",
            f"Fictional collection {number}",
        )
        if receipt["status"] != "ADDED":
            raise AssertionError("Snapshot import did not add independent evidence")
        snapshot_id = receipt["snapshot"]["snapshot_id"]
        snapshot = run("evidence", "show", str(workspace), snapshot_id)
        if snapshot["observations_sha256"] != receipt["snapshot"]["observations_sha256"]:
            raise AssertionError("Snapshot observation identity mismatch")
        if number == 1:
            positives = [r for r in enrichment["records"] if r["status"] == "STRUCTURALLY_VALID"]
            if [(r["packet"]["index"], r["protocol"]) for r in positives] != [
                (1, "modbus_tcp"),
                (2, "modbus_tcp"),
                (3, "profinet_dcp"),
            ]:
                raise AssertionError("Independent industrial fixture oracle mismatch")
            if any(
                r["status"] == "STRUCTURALLY_VALID"
                for r in enrichment["records"]
                if r["packet"]["index"] == 4
            ):
                raise AssertionError("Unrelated PROFINET frame became a positive DCP record")
        snapshots.append(receipt["snapshot"])
    duplicate = run(
        "evidence",
        "add",
        str(workspace),
        str(output / "capture-1/observations.json"),
        "--label",
        "A renamed review label",
    )
    if duplicate["status"] != "DUPLICATE_CAPTURE" or not duplicate["observations_match"]:
        raise AssertionError("Repeated capture did not preserve duplicate identity")
    listed = run("evidence", "list", str(workspace))
    verified = run("evidence", "verify", str(workspace))
    if len(listed["snapshots"]) != 2 or verified["snapshots"] != 2:
        raise AssertionError("Duplicate ingestion inflated apparent evidence")
    if before != {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}:
        raise AssertionError("Original fictional inputs changed")
    if list((workspace / "snapshots").glob("*.pcap*")):
        raise AssertionError("Workspace copied raw capture bytes")
    record = {
        "status": "passed",
        "fictional_only": True,
        "external_capture_validation": "pending",
        "snapshot_count": 2,
        "snapshots": snapshots,
        "duplicate_status": duplicate["status"],
        "verification": verified,
        "commands": commands,
        "limitations": [
            "Metadata ingestion only; drift and baseline approval are pending.",
            "Fictional collections do not establish monitoring continuity or comparable coverage.",
        ],
    }
    (output / "walkthrough.json").write_text(
        json.dumps(record, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = walkthrough(args.output)
    print(json.dumps({"status": result["status"], "snapshot_count": result["snapshot_count"]}))


if __name__ == "__main__":
    main()
