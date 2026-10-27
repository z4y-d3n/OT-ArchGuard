"""Repeat an entirely fictional workspace-v2 lifecycle through the offline CLI.

No operational evidence is approved. All reviewer labels and mappings are
invented for this reproducible acceptance demonstration.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sysconfig
from pathlib import Path
from typing import Any

import yaml

from otarchguard.evidence.history import read_history
from otarchguard.evidence.revisions import build_semantics
from tools.capture_workloads import plant_model, write_pcap

ROOT = Path(__file__).resolve().parents[1]


def _bytes(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def _canonical_id(kind: str, value: dict[str, Any]) -> str:
    body = {k: v for k, v in value.items() if k != kind + "_id"}
    encoded = json.dumps(
        {"domain": "otarchguard." + kind, "value": body},
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("ascii")
    return kind + "-" + hashlib.sha256(encoded).hexdigest()


def scenario(output: Path) -> dict[str, Any]:
    output.mkdir(exist_ok=False)
    console = Path(sysconfig.get_path("scripts")) / (
        "otarchguard.exe" if os.name == "nt" else "otarchguard"
    )
    commands: list[dict[str, Any]] = []

    def run(*args: str, rejected: bool = False) -> dict[str, Any]:
        child = subprocess.run([str(console), *args], capture_output=True, timeout=120)
        commands.append({"arguments": list(args), "exit_code": child.returncode})
        if rejected:
            if child.returncode != 2 or not child.stderr:
                raise AssertionError("A negative historical workflow was not rejected safely")
            return json.loads(child.stderr.splitlines()[0])  # type: ignore[no-any-return]
        if child.returncode or child.stderr:
            raise RuntimeError(
                "Installed history walkthrough command failed: "
                + " ".join(args)
                + ": "
                + child.stderr.decode(errors="replace")[:1024]
            )
        result: dict[str, Any] = json.loads(child.stdout)
        return result

    captures = [
        ROOT / "tests/fixtures/protocol-corpus/synthetic-industrial.pcap",
        output / "fictional-second.pcap",
    ]
    write_pcap(captures[1])
    input_before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in captures}
    source = output / "legacy"
    workspace = output / "history"
    run("evidence", "init", str(source))
    snapshots: list[str] = []
    for index, capture in enumerate(captures):
        site = output / f"observations-{index}"
        run("capture", "analyze", str(capture), "--output", str(site))
        imported = run(
            "evidence",
            "add",
            str(source),
            str(site / "observations.json"),
            "--label",
            f"Fictional collection {index + 1}; label is not approval",
        )
        snapshots.append(imported["snapshot"]["snapshot_id"])
    source_before = _bytes(source)
    migrated = run("evidence", "migrate", str(source), str(workspace))
    if migrated["physical_collections"] != 2 or source_before != _bytes(source):
        raise AssertionError("Migration changed source bytes or physical membership")
    if run("evidence", "verify", str(source))["snapshots"] != 2:
        raise AssertionError("Original v1 workspace no longer validates")
    for name, data in source_before.items():
        if name.startswith("snapshots/") and (workspace / name).read_bytes() != data:
            raise AssertionError("Migration reserialized an immutable original snapshot")

    enrichment_path = output / "enrichment-a.json"
    enrichment = run("capture", "enrich", str(captures[0]), "--output", str(enrichment_path))
    if enrichment["observations_sha256"] is not None:
        raise AssertionError("Demonstration expected the documented null enrichment join")
    imported = run(
        "evidence", "attach", str(workspace), snapshots[0], "enrichment", str(enrichment_path)
    )
    enrichment_id = imported["attachment"]["attachment_id"]
    mismatch = run(
        "evidence",
        "attach",
        str(workspace),
        snapshots[1],
        "enrichment",
        str(enrichment_path),
        rejected=True,
    )
    first = run(
        "evidence",
        "revision",
        "create",
        str(workspace),
        snapshots[0],
        "--enrichment",
        enrichment_id,
    )["analysis"]
    repeated = run(
        "evidence",
        "revision",
        "create",
        str(workspace),
        snapshots[0],
        "--enrichment",
        enrichment_id,
    )
    if repeated["status"] != "ALREADY_PRESENT" or repeated["analysis"] != first:
        raise AssertionError("Identical revisions are not idempotent")
    state = read_history(workspace)
    semantics = build_semantics(
        state["snapshots"][snapshots[0]],
        {"enrichment": state["attachments"][enrichment_id]},
        require_complete_scan=True,
    )
    semantics_path = output / "selected-semantics.json"
    semantics_path.write_text(
        json.dumps(semantics, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    second = run(
        "evidence",
        "revision",
        "create",
        str(workspace),
        snapshots[0],
        "--enrichment",
        enrichment_id,
        "--semantics",
        str(semantics_path),
    )["analysis"]
    if (
        first["analysis_id"] == second["analysis_id"]
        or first["capture_sha256"] != second["capture_sha256"]
    ):
        raise AssertionError("Different selected analysis requirements lost identity separation")
    b_revision = run("evidence", "revision", "create", str(workspace), snapshots[1])["analysis"]

    model_path = output / "fictional-model.yaml"
    model_path.write_text(yaml.safe_dump(plant_model(), sort_keys=False), encoding="utf-8")
    model_before = model_path.read_bytes()
    model_id = run("evidence", "attach", str(workspace), snapshots[0], "model", str(model_path))[
        "attachment"
    ]["attachment_id"]
    mapping_path = output / "fictional-reviewed-mapping.json"
    run(
        "capture",
        "map",
        str(captures[0]),
        "--model",
        str(model_path),
        "--output",
        str(mapping_path),
    )
    mapping = json.loads(mapping_path.read_bytes())
    for item in mapping["proposals"]:
        item["reviewer"] = "Fictional laboratory reviewer"
        item["rationale"] = "Invented teaching identities only; no operational assertion"
        if len(item["candidates"]) == 1:
            selected = item["candidates"][0]
            item.update(
                decision="ACCEPT",
                selected_asset_id=selected["asset_id"],
                selected_interface_id=selected["interface_id"],
            )
        else:
            item["decision"] = "REJECT"
    mapping_path.write_text(json.dumps(mapping, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    mapping_id = run(
        "evidence",
        "attach",
        str(workspace),
        snapshots[0],
        "mapping",
        str(mapping_path),
        "--model",
        model_id,
    )["attachment"]["attachment_id"]
    comparison_site = output / "fictional-native-comparison"
    run(
        "capture",
        "compare",
        str(captures[0]),
        "--model",
        str(model_path),
        "--mapping",
        str(mapping_path),
        "--output",
        str(comparison_site),
    )
    comparison_id = run(
        "evidence",
        "attach",
        str(workspace),
        snapshots[0],
        "comparison",
        str(comparison_site / "comparison.json"),
        "--model",
        model_id,
        "--mapping",
        mapping_id,
    )["attachment"]["attachment_id"]
    scope = {
        "environment": "Entirely fictional acceptance laboratory",
        "purpose": "Reference inputs for future finite historical comparisons",
        "coverage": "Only selected generated packets; no monitoring continuity asserted",
        "uncertainties": ["Packet loss unknown", "Source authenticity not established"],
        "vantage_points": [],
        "protocols": ["modbus_tcp", "profinet_dcp"],
    }
    scope_path = output / "fictional-scope.json"
    scope_path.write_text(json.dumps(scope, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    baseline = run(
        "evidence",
        "baseline",
        "propose",
        str(workspace),
        str(scope_path),
        "--revision",
        second["analysis_id"],
        "--revision",
        b_revision["analysis_id"],
    )["baseline"]
    if baseline["status"] != "PROPOSED":
        raise AssertionError("A proposal acquired implicit approval")
    approval = run(
        "evidence",
        "baseline",
        "approve",
        str(workspace),
        baseline["baseline_id"],
        "--reviewer",
        "Fictional owner",
        "--rationale",
        "Fictional finite reference only",
    )["review"]
    third = run(
        "evidence",
        "revision",
        "create",
        str(workspace),
        snapshots[0],
        "--enrichment",
        enrichment_id,
        "--model",
        model_id,
        "--mapping",
        mapping_id,
        "--comparison",
        comparison_id,
    )["analysis"]
    successor = run(
        "evidence",
        "baseline",
        "propose",
        str(workspace),
        str(scope_path),
        "--revision",
        third["analysis_id"],
        "--revision",
        b_revision["analysis_id"],
    )["baseline"]
    if successor["status"] != "PROPOSED":
        raise AssertionError("Old approval transferred to a new interpretation")
    stale_approval = run(
        "evidence",
        "baseline",
        "approve",
        str(workspace),
        successor["baseline_id"],
        "--reviewer",
        "Fictional owner",
        "--rationale",
        "Conflicting root must fail",
        rejected=True,
    )
    superseding = run(
        "evidence",
        "baseline",
        "supersede",
        str(workspace),
        successor["baseline_id"],
        "--predecessor",
        approval["review_id"],
        "--reviewer",
        "Fictional owner",
        "--rationale",
        "Explicit fictional selection of revised inputs",
    )["review"]
    run(
        "evidence",
        "baseline",
        "revoke",
        str(workspace),
        successor["baseline_id"],
        "--predecessor",
        superseding["review_id"],
        "--reviewer",
        "Fictional owner",
        "--rationale",
        "Fictional reference period retired",
    )
    architecture = run(
        "evidence",
        "baseline",
        "propose",
        str(workspace),
        str(scope_path),
        "--kind",
        "architecture",
        "--model",
        model_id,
    )["baseline"]
    if architecture["status"] != "PROPOSED" or architecture["model_sha256"] is None:
        raise AssertionError(
            "Architecture reference did not retain its distinct proposal semantics"
        )
    verified = run("evidence", "verify", str(workspace))
    if (
        verified["physical_collections"] != 2
        or verified["analyses"] != 4
        or verified["reviews"] != 3
        or verified["approved_baselines"] != 0
        or verified["revoked_baselines"] != 1
        or verified["superseded_baselines"] != 1
    ):
        raise AssertionError("Historical counts or effective decision states disagree")
    if source_before != _bytes(source) or model_before != model_path.read_bytes():
        raise AssertionError("Original workspace or selected model was modified")
    if input_before != {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in captures}:
        raise AssertionError("Original fictional packet bytes were modified")
    state = read_history(workspace)
    for plural, kind in (
        ("attachments", "attachment"),
        ("analyses", "analysis"),
        ("baselines", "baseline"),
        ("reviews", "review"),
    ):
        for identifier, value in state[plural].items():
            if identifier != _canonical_id(kind, value):
                raise AssertionError("Independent canonical identity oracle disagrees")
    receipt = {
        "status": "passed",
        "fictional_only": True,
        "source_v1_bytes_preserved": True,
        "model_bytes_preserved": True,
        "identities": {
            kind: sorted(state[kind])
            for kind in ("snapshots", "attachments", "analyses", "baselines", "reviews")
        },
        "verification": verified,
        "negative_cases": {"cross_capture_attachment": mismatch, "stale_approval": stale_approval},
        "commands": commands,
    }
    (output / "walkthrough.json").write_text(
        json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    return receipt


def walkthrough(output: Path) -> dict[str, Any]:
    output.mkdir(exist_ok=False)
    first = scenario(output / "first")
    replay = scenario(output / "replay")
    if first["identities"] != replay["identities"]:
        raise AssertionError("Equivalent independent runs did not reproduce canonical identities")
    result = {
        "status": "passed",
        "fictional_only": True,
        "independent_replay": "identical canonical object identities",
        "identities": first["identities"],
        "verification": first["verification"],
        "limitations": [
            "Metadata integrity and exact supported relationships only; "
            "originals remain unauthenticated.",
            "Fictional assertions are not approvals of real evidence or repository artifacts.",
            "Historical drift and a historical Explorer are outside this demonstration.",
        ],
    }
    (output / "walkthrough.json").write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = walkthrough(args.output)
    print(
        json.dumps(
            {"status": result["status"], "verification": result["verification"]}, sort_keys=True
        )
    )


if __name__ == "__main__":
    main()
