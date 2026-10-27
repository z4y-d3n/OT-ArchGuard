"""Scriptable lifecycle CLI acceptance and structured failure boundaries."""

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from otarchguard.evidence.cli import app
from otarchguard.evidence.history import publish_object
from otarchguard.evidence.lifecycle import load_state
from otarchguard.evidence.workspace import serialize

ROOT = Path(__file__).resolve().parents[1]
RUNNER = CliRunner()


def command(*args: str) -> dict[str, Any]:
    result = RUNNER.invoke(app, list(args))
    assert result.exit_code == 0, result.output
    return json.loads(result.stdout)  # type: ignore[no-any-return]


def initialized(tmp_path: Path) -> tuple[Path, str, str]:
    workspace = tmp_path / "fictional-history"
    command("init", str(workspace), "--version", "2")
    command(
        "add",
        str(workspace),
        str(ROOT / "tests/fixtures/capture-contract-v2/supported/observations.json"),
    )
    sid = command("list", str(workspace))["snapshots"][0]["snapshot_id"]
    aid = command("revision", "create", str(workspace), sid)["analysis"]["analysis_id"]
    return workspace, sid, aid


def proposed(tmp_path: Path) -> tuple[Path, str]:
    workspace, _, aid = initialized(tmp_path)
    scope = tmp_path / "scope.json"
    scope.write_bytes(
        serialize(
            {
                "environment": "Fictional CLI site",
                "purpose": "Synthetic acceptance",
                "coverage": "Unknown; no completeness assertion",
                "uncertainties": [],
                "vantage_points": [],
                "protocols": [],
            }
        )
    )
    bid = command("baseline", "propose", str(workspace), str(scope), "--revision", aid)["baseline"][
        "baseline_id"
    ]
    return workspace, bid


def test_explicit_cli_proposal_approval_revocation_and_human_inspection(tmp_path: Path) -> None:
    workspace, bid = proposed(tmp_path)
    assert command("baseline", "show", str(workspace), bid)["status"] == "PROPOSED"
    missing = RUNNER.invoke(app, ["baseline", "approve", str(workspace), bid])
    assert missing.exit_code == 2
    assert json.loads(missing.stderr)["code"] == "INVALID_VALUE"
    assert load_state(workspace)["reviews"] == {}
    approved = command(
        "baseline",
        "approve",
        str(workspace),
        bid,
        "--reviewer",
        "Fictional reviewer",
        "--rationale",
        "Fictional acceptance",
    )
    assert approved["baseline_status"] == "APPROVED"
    original = (workspace / "reviews" / (approved["review"]["review_id"] + ".json")).read_bytes()
    readable = RUNNER.invoke(app, ["baseline", "review", str(workspace), bid, "--text"])
    assert readable.exit_code == 0
    assert "Fictional CLI site" in readable.stdout and "APPROVED" in readable.stdout
    assert "unauthenticated" in readable.stdout
    revoked = command(
        "baseline",
        "revoke",
        str(workspace),
        bid,
        "--predecessor",
        approved["review"]["review_id"],
        "--reviewer",
        "Fictional reviewer",
        "--rationale",
        "Withdraw fictional acceptance",
    )
    assert revoked["baseline_status"] == "REVOKED"
    assert (
        workspace / "reviews" / (approved["review"]["review_id"] + ".json")
    ).read_bytes() == original
    result = command("verify", str(workspace))
    assert result["physical_collections"] == result["analyses"] == 1
    assert result["approved_baselines"] == 0 and result["revoked_baselines"] == 1
    assert result["source_authenticity"] == "UNVERIFIED"


def test_duplicate_analytical_revision_is_idempotent_and_v1_default_retained(
    tmp_path: Path,
) -> None:
    legacy = tmp_path / "legacy"
    assert command("init", str(legacy))["workspace_version"] == 1
    workspace, sid, aid = initialized(tmp_path)
    result = command("revision", "create", str(workspace), sid)
    assert result["status"] == "ALREADY_PRESENT" and result["object_id"] == aid
    assert len(command("revision", "list", str(workspace))["analyses"]) == 1
    assert command("show", str(workspace), sid)["snapshot_id"] == sid


@pytest.mark.parametrize(
    "kind,body",
    [
        ("attachments", {"attachment_version": 1, "capture_sha256": [], "dependencies": []}),
        ("analyses", {"analysis_version": 1, "capture_sha256": "a" * 64, "components": []}),
        ("baselines", {"baseline_version": True}),
        ("reviews", {"review_version": 1, "subject_id": []}),
    ],
)
def test_rehashed_malformed_storage_never_escapes_structured_public_verification(
    tmp_path: Path,
    kind: str,
    body: dict[str, Any],
) -> None:
    # Deliberately bypass semantic callback to simulate attacker-written bytes.
    from otarchguard.evidence.attachments import object_digest

    workspace, _, _ = initialized(tmp_path)
    singular = {
        "attachments": "attachment",
        "analyses": "analysis",
        "baselines": "baseline",
        "reviews": "review",
    }[kind]
    body[singular + "_id"] = singular + "-" + object_digest("otarchguard." + singular, body)
    if body.get("baseline_version") is True:
        # Raw hostile bytes bypass the storage version guard as well.
        (workspace / kind / (body[singular + "_id"] + ".json")).write_bytes(serialize(body))
    else:
        publish_object(workspace, kind, body)
    result = RUNNER.invoke(app, ["verify", str(workspace)])
    assert result.exit_code == 2
    diagnostic = json.loads(result.stderr)
    assert diagnostic["code"] != "EVIDENCE_INTERNAL"
    assert result.stdout == ""


def test_unknown_workspace_version_and_analysis_filter_use_structured_diagnostics(
    tmp_path: Path,
) -> None:
    workspace, _, _ = initialized(tmp_path)
    result = RUNNER.invoke(app, ["revision", "list", str(workspace), "--capture", "f" * 64])
    assert result.exit_code == 2 and json.loads(result.stderr)["code"] == "EVIDENCE_NOT_FOUND"
    bad = RUNNER.invoke(app, ["init", str(tmp_path / "bad"), "--version", "3"])
    assert bad.exit_code == 2 and json.loads(bad.stderr)["code"] == "EVIDENCE_WORKSPACE"
    assert not (tmp_path / "bad").exists()
