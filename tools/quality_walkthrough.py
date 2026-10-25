"""Installed-console tutorial using fictional declarations and documentary-only changes."""

import argparse
import copy
import hashlib
import json
import os
import subprocess
import sysconfig
from pathlib import Path
from typing import Any

import yaml

from otarchguard.explorer_data import load_model
from otarchguard.ingestion.project import create_project
from otarchguard.ingestion.project_review import emit_project
from tools.synthetic_projects import synthetic_project, tutorial_decisions, write_json

ROOT = Path(__file__).resolve().parents[1]


def walkthrough(output: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=False)
    console = Path(sysconfig.get_path("scripts")) / (
        "otarchguard.exe" if os.name == "nt" else "otarchguard"
    )
    commands = []

    def run(*args: object) -> None:
        command = [str(console), *map(str, args)]
        result = subprocess.run(command, capture_output=True, text=True, timeout=120)
        commands.append(
            {
                "argv": command[1:],
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        )
        if result.returncode:
            raise RuntimeError("Installed quality/comparison console failed: " + result.stderr)

    before = yaml.safe_load(
        (ROOT / "tests/fixtures/minimal-valid.yaml").read_text(encoding="utf-8")
    )
    retired = {**before["assets"][0], "id": "retired", "name": "Retired declaration"}
    before["assets"].append(retired)
    after = copy.deepcopy(before)
    after["assets"] = [a for a in after["assets"] if a["id"] != "retired"]
    after["assets"].append({**retired, "id": "sensor", "name": "New declared sensor"})
    after["zones"].append({**after["zones"][0], "id": "engineering", "name": "Engineering"})
    after["assets"][0]["zone_id"] = "engineering"
    after["interfaces"][0].update(placement_zone_id="engineering", ipv4="192.0.2.30/24")
    after["conduits"] = [
        {
            "id": "engineering-control",
            "name": "Declared crossing",
            "purpose": "Fictional crossing",
            "common_security_needs": "Owner context",
            "zone_ids": ["engineering", "control"],
        }
    ]
    after["transport_edges"][0]["conduit_id"] = "engineering-control"
    after["rules"] = []
    for name, data in (("baseline", before), ("proposed", after)):
        (output / (name + ".yaml")).write_text(yaml.safe_dump(data), encoding="utf-8")
    baseline, proposed = output / "baseline.yaml", output / "proposed.yaml"
    write_json(
        output / "profile.json",
        {
            "profile_version": 1,
            "model_sha256": load_model(baseline).sha256,
            "context": "Fictional documentary requirement",
            "requirements": [
                {
                    "id": "asset-documentation",
                    "expectation": "ENTITY_PROVENANCE",
                    "entity_kind": "assets",
                    "entity_ids": ["*"],
                    "rationale": "Owner requests source support; missing support "
                    "is not a vulnerability.",
                }
            ],
        },
    )
    run("quality", baseline, "--profile", output / "profile.json", "--output", output / "quality")
    run("quality", baseline)  # JSON-only, no Explorer required.
    run(
        "compare-architecture",
        baseline,
        proposed,
        "--trace",
        "eng:svc_plc",
        "--output",
        output / "comparison",
    )
    report = json.loads((output / "comparison/review.json").read_text(encoding="utf-8"))
    assert (
        report["analytical_results"][0]["intervals"][0]["classification"]
        == "NO_LONGER_ALLOWED_FOR_EVALUATED_QUERY"
    )
    assert {c["action"] for c in report["changes"] if c["entity_kind"] == "assets"} == {
        "ADDED",
        "REMOVED",
        "MODIFIED",
    }
    # A revised drawing alone changes documentary evidence and its acknowledgment.
    manifest = synthetic_project(output / "documents", count=4, contradictory=False)
    paths = []
    for version in ("before", "after"):
        if version == "after":
            graph = output / "documents/topology.drawio"
            graph.write_text(
                graph.read_text(encoding="utf-8").replace(
                    "</root>",
                    '<mxCell id="extra-arrow" edge="1" parent="1" source="n0" target="n1"/></root>',
                ),
                encoding="utf-8",
            )
        draft = create_project(manifest)
        accepted = output / ("documentary-" + version)
        accepted.mkdir()
        for name, data in emit_project(draft, tutorial_decisions(draft), manifest).items():
            (accepted / name).write_bytes(data)
        paths.append(accepted)
    run(
        "compare-architecture",
        paths[0] / "architecture.yaml",
        paths[1] / "architecture.yaml",
        "--baseline-provenance",
        paths[0] / "architecture.provenance.json",
        "--proposed-provenance",
        paths[1] / "architecture.provenance.json",
        "--output",
        output / "documentary-comparison",
    )
    documentary = json.loads(
        (output / "documentary-comparison/review.json").read_text(encoding="utf-8")
    )
    assert documentary["baseline_model_sha256"] == documentary["proposed_model_sha256"]
    assert not any(c["layer"] == "NATIVE" for c in documentary["changes"])
    assert any(c["entity_kind"] == "documentary_connectors" for c in documentary["changes"])
    assert documentary["analytical_status"] == "NOT_EVALUATED"
    inventories = {
        name: {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (output / name).iterdir()
        }
        for name in ("quality", "comparison", "documentary-comparison")
    }
    receipt = {
        "status": "passed",
        "synthetic_only": True,
        "commands": commands,
        "baseline_model_sha256": report["baseline_model_sha256"],
        "proposed_model_sha256": report["proposed_model_sha256"],
        "site_hashes": inventories,
    }
    write_json(output / "walkthrough.json", receipt)
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    walkthrough(args.output)
    print("Installed quality, comparison, exact trace and documentary-only walkthroughs passed.")


if __name__ == "__main__":
    main()
