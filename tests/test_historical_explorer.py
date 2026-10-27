"""Independent source-authority and publication integration oracles."""

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from otarchguard.cli import app
from otarchguard.diagnostics import ModelError
from otarchguard.drift import explorer, explorer_render
from otarchguard.drift.engine import compare
from otarchguard.drift.reports import read_report
from otarchguard.evidence import lifecycle
from tools.drift_walkthrough import canonical, comparison_context, prepare


@pytest.fixture
def case(tmp_path: Path) -> tuple[Path, Path, dict[str, Any]]:
    selected = prepare(tmp_path / "inputs", variations=False)
    workspace = Path(selected["workspace"])
    ref = selected["periods"]["reference"]["analysis_id"]
    candidate = selected["periods"]["candidate"]["analysis_id"]
    report = compare(
        workspace,
        selected["baseline_id"],
        [candidate],
        comparison_context(ref, candidate, selected["scope"]),
    )
    path = tmp_path / "report.json"
    path.write_bytes(canonical(report) + b"\n")
    return workspace, path, selected


def inventory(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in root.rglob("*")
        if p.is_file()
    }


def test_one_acquisition_read_only_determinism_and_cli(
    case: tuple[Path, Path, dict[str, Any]], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace, report, _ = case
    before = inventory(workspace)
    original = lifecycle._operation
    acquisitions: list[Path] = []

    def counted(path: Path) -> Any:
        acquisitions.append(path)
        return original(path)

    monkeypatch.setattr(lifecycle, "_operation", counted)
    first = explorer.generate_explorer(workspace, report, tmp_path / "one", page_size=5)
    assert acquisitions == [workspace]
    second = explorer.generate_explorer(workspace, report, tmp_path / "two", page_size=5)
    assert first["bundle_id"] == second["bundle_id"]
    assert inventory(tmp_path / "one") == inventory(tmp_path / "two")
    assert inventory(workspace) == before
    site_before = inventory(tmp_path / "one")
    portable = explorer.verify_explorer(tmp_path / "one")
    assert portable["analytical_reproduction"] is False
    fresh = explorer.verify_explorer(tmp_path / "one", workspace=workspace)
    assert fresh["analytical_reproduction"] is True
    assert fresh["source_reproduction"]["currently_approved_reference"] is True
    assert inventory(tmp_path / "one") == site_before
    runner = CliRunner()
    generated = runner.invoke(
        app, ["evidence", "drift", "explore", str(workspace), str(report), str(tmp_path / "cli")]
    )
    assert generated.exit_code == 0, generated.output
    assert json.loads(generated.stdout)["drift_id"] == read_report(report)["drift_id"]
    verified = runner.invoke(
        app,
        [
            "evidence",
            "drift",
            "explore-verify",
            str(tmp_path / "cli"),
            "--workspace",
            str(workspace),
        ],
    )
    assert verified.exit_code == 0, verified.output
    assert json.loads(verified.stdout)["analytical_reproduction"] is True
    assert str(workspace).encode() not in (tmp_path / "cli/index.html").read_bytes()


@pytest.mark.parametrize("mutation", ["finding", "baseline", "candidate", "source"])
def test_rehashed_forgery_is_structurally_valid_but_source_rejected(
    case: tuple[Path, Path, dict[str, Any]], tmp_path: Path, mutation: str
) -> None:
    workspace, report_path, _ = case
    fake = copy.deepcopy(read_report(report_path))
    if mutation == "finding":
        fake["comparisons"][0]["findings"][0]["explanation"] = "A valid-looking invented claim"
    elif mutation == "baseline":
        fake["inputs"]["baseline"]["baseline_id"] = "baseline-" + "0" * 64
    elif mutation == "candidate":
        fake["options"]["candidates"] = ["analysis-" + "0" * 64]
    else:
        fake["comparisons"][0]["findings"][0]["reference"] = {"source": "forged"}
    body = {k: v for k, v in fake.items() if k != "drift_id"}
    fake["drift_id"] = (
        "drift-"
        + hashlib.sha256(canonical({"domain": "otarchguard.drift.v1", "value": body})).hexdigest()
    )
    report_path.write_bytes(canonical(fake) + b"\n")
    assert read_report(report_path)["drift_id"] == fake["drift_id"]
    with pytest.raises(ModelError):
        explorer.generate_explorer(workspace, report_path, tmp_path / "rejected")
    assert not (tmp_path / "rejected").exists()


def test_revocation_updates_fresh_authority_without_rewriting_historical_site(
    case: tuple[Path, Path, dict[str, Any]], tmp_path: Path
) -> None:
    workspace, report, selected = case
    first = explorer.generate_explorer(workspace, report, tmp_path / "approved")
    before = inventory(tmp_path / "approved")
    lifecycle.record_review(
        workspace,
        selected["baseline_id"],
        "revoke",
        "Fictional owner",
        "Retire reference",
        predecessor=selected["approval_id"],
    )
    fresh = explorer.verify_explorer(tmp_path / "approved", workspace=workspace)
    assert fresh["approval_snapshot_changed"] is True
    assert fresh["source_reproduction"]["current_baseline_status"] == "REVOKED"
    assert inventory(tmp_path / "approved") == before
    revoked = explorer.generate_explorer(workspace, report, tmp_path / "revoked")
    assert revoked["bundle_id"] != first["bundle_id"]
    overview = (tmp_path / "revoked/index.html").read_text(encoding="utf-8")
    assert "REVOKED" in overview and "APPROVED" in overview
    assert report.read_bytes() == (tmp_path / "revoked/report.json").read_bytes()


@pytest.mark.parametrize("source", ["report", "workspace"])
def test_mutation_during_rendering_leaves_no_successful_publication(
    case: tuple[Path, Path, dict[str, Any]],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source: str,
) -> None:
    workspace, report, _ = case
    original = explorer_render.render

    def changed(*args: Any, **kwargs: Any) -> dict[str, bytes]:
        files = original(*args, **kwargs)
        target = report if source == "report" else workspace / "workspace.json"
        target.write_bytes(target.read_bytes() + b" ")
        return files

    monkeypatch.setattr(explorer_render, "render", changed)
    with pytest.raises(ModelError):
        explorer.generate_explorer(workspace, report, tmp_path / "changed")
    assert not (tmp_path / "changed/explorer-manifest.json").exists()


def test_missing_source_member_and_output_within_workspace_rejected(
    case: tuple[Path, Path, dict[str, Any]], tmp_path: Path
) -> None:
    workspace, report, _ = case
    with pytest.raises(ModelError):
        explorer.generate_explorer(workspace, report, workspace / "site")
    next((workspace / "analyses").iterdir()).unlink()
    result = CliRunner().invoke(
        app,
        ["evidence", "drift", "explore", str(workspace), str(report), str(tmp_path / "missing")],
    )
    assert result.exit_code == 2
    assert json.loads(result.stderr)["code"].startswith("EVIDENCE")
    assert not (tmp_path / "missing").exists()
