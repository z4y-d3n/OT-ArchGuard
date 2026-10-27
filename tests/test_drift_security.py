"""Independent hostile report mutation and current-authority acceptance tests."""

import hashlib
import json
import os
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from otarchguard.diagnostics import ModelError
from otarchguard.drift import reports
from otarchguard.drift.contract import DRIFT_LIMITS, Budget
from otarchguard.drift.engine import compare
from otarchguard.evidence import history, lifecycle
from otarchguard.evidence.history import _check_image
from otarchguard.evidence.workspace import serialize

FIXTURES = Path(__file__).parent / "fixtures/capture-contract-v2"


def _seal(report: dict[str, Any]) -> dict[str, Any]:
    body = {k: v for k, v in report.items() if k != "drift_id"}
    encoded = json.dumps(
        {"domain": "otarchguard.drift.v1", "value": body},
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("ascii")
    report["drift_id"] = "drift-" + hashlib.sha256(encoded).hexdigest()
    return report


@pytest.fixture
def evidence(tmp_path: Path) -> tuple[Path, str, str, dict[str, Any], dict[str, Any]]:
    workspace = tmp_path / "fictional-history"
    history.initialize_history(workspace)
    sid = history.add_collection(workspace, FIXTURES / "supported/observations.json")["snapshot_id"]
    aid = lifecycle.create_revision(workspace, sid)["analysis"]["analysis_id"]
    scope = {
        "environment": "Fictional security fixture",
        "purpose": "Independent adversarial acceptance",
        "coverage": "Finite source data; loss and visibility remain unknown",
        "uncertainties": ["No continuous monitoring asserted"],
        "vantage_points": ["Fictional sensor assertion"],
        "protocols": ["tcp"],
    }
    scope_path = tmp_path / "scope.json"
    scope_path.write_bytes(serialize(scope))
    bid = lifecycle.propose_baseline(workspace, scope_path, [aid])["baseline"]["baseline_id"]
    approval = lifecycle.record_review(
        workspace, bid, "approve", "Fictional reviewer", "Independent fictional acceptance"
    )["review"]
    context = {
        "context_version": 1,
        "pairs": [
            {
                "reference_analysis_id": aid,
                "candidate_analysis_id": aid,
                "candidate_scope": scope,
                "alignment": "asserted",
                "rationale": "Explicit fictional same-collection comparison",
                "native_queries": [],
            }
        ],
    }
    return workspace, bid, aid, context, approval


def _report(evidence: tuple[Path, str, str, dict[str, Any], dict[str, Any]]) -> dict[str, Any]:
    workspace, bid, aid, context, _ = evidence
    return compare(workspace, bid, [aid], context)


@pytest.mark.parametrize(
    "mutation", ["count", "finding", "approval", "source", "engine", "options", "context"]
)
def test_recomputed_hash_never_grants_fabricated_analytical_authority(
    evidence: tuple[Path, str, str, dict[str, Any], dict[str, Any]],
    tmp_path: Path,
    mutation: str,
) -> None:
    workspace, _, _, _, _ = evidence
    report = _report(evidence)
    if mutation == "count":
        report["summary"]["findings"] += 1
    elif mutation == "finding":
        report["comparisons"][0]["findings"][0]["explanation"] = "Fabricated claim"
    elif mutation == "approval":
        report["inputs"]["approval"]["reviewer"] = "Fabricated authenticated administrator"
    elif mutation == "source":
        report["inputs"]["candidate_sources"][0]["capture_sha256"] = "a" * 64
    elif mutation == "engine":
        report["implementation_sha256"]["drift/engine.py"] = "f" * 64
    elif mutation == "options":
        report["options"]["force_comparable"] = True
    else:
        report["options"]["context"]["pairs"][0]["candidate_scope"]["vantage_points"] = [
            "Different fictional sensor"
        ]
    path = tmp_path / "forged.json"
    path.write_bytes(serialize(_seal(report)))
    # Strict structural integrity does not confer evidence authority.
    assert reports.read_report(path)["drift_id"] == report["drift_id"]
    with pytest.raises(ModelError):
        reports.verify_report(workspace, path)


def test_current_revocation_is_checked_after_previous_success_and_history_survives(
    evidence: tuple[Path, str, str, dict[str, Any], dict[str, Any]], tmp_path: Path
) -> None:
    workspace, bid, aid, context, approval = evidence
    report = _report(evidence)
    path = tmp_path / "historical.json"
    reports.publish(report, path, workspace)
    before = path.read_bytes()
    assert reports.verify_report(workspace, path)["currently_approved_reference"] is True
    lifecycle.record_review(
        workspace,
        bid,
        "revoke",
        "Fictional reviewer",
        "Withdraw fictional acceptance",
        approval["review_id"],
    )
    verified = reports.verify_report(workspace, path)
    assert verified["canonical_reproduction"] is True
    assert verified["current_baseline_status"] == "REVOKED"
    assert verified["currently_approved_reference"] is False
    assert verified["review_graph_changed"] is True
    assert path.read_bytes() == before
    with pytest.raises(ModelError):
        compare(workspace, bid, [aid], context)
    with pytest.raises(ModelError):
        reports.publish(report, tmp_path / "new-publication.json", workspace)


def test_superseded_baseline_retains_exact_historical_report_but_loses_current_authority(
    evidence: tuple[Path, str, str, dict[str, Any], dict[str, Any]], tmp_path: Path
) -> None:
    workspace, bid, aid, context, approval = evidence
    path = tmp_path / "historical.json"
    reports.publish(_report(evidence), path, workspace)
    sid = history.add_collection(workspace, FIXTURES / "limited/observations.json")["snapshot_id"]
    candidate = lifecycle.create_revision(workspace, sid)["analysis"]["analysis_id"]
    successor = lifecycle.propose_baseline(workspace, tmp_path / "scope.json", [candidate])[
        "baseline"
    ]
    lifecycle.record_review(
        workspace,
        successor["baseline_id"],
        "supersede",
        "Fictional reviewer",
        "Exact alternate fictional collection",
        approval["review_id"],
    )
    assert reports.verify_report(workspace, path)["current_baseline_status"] == "SUPERSEDED"
    with pytest.raises(ModelError):
        compare(workspace, bid, [aid], context)


def test_publication_owns_a_copy_before_checking_untrusted_caller_report(
    evidence: tuple[Path, str, str, dict[str, Any], dict[str, Any]],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace, _, _, _, _ = evidence
    report = _report(evidence)
    expected = deepcopy(report)
    original = _check_image

    def caller_mutation(selected: Path, image: Any) -> None:
        original(selected, image)
        report["summary"]["findings"] = 999999
        _seal(report)

    monkeypatch.setattr(reports, "_check_image", caller_mutation)
    output = tmp_path / "owned-report.json"
    reports.publish(report, output, workspace)
    assert reports.read_report(output) == expected
    assert reports.verify_report(workspace, output)["canonical_reproduction"] is True


def test_no_overwrite_and_interrupted_publication_preserve_existing_sources(
    evidence: tuple[Path, str, str, dict[str, Any], dict[str, Any]],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace, _, _, _, _ = evidence
    report = _report(evidence)
    output = tmp_path / "existing.json"
    output.write_bytes(b"original owner bytes")
    with pytest.raises(ModelError):
        reports.publish(report, output, workspace)
    assert output.read_bytes() == b"original owner bytes"

    def interruption(descriptor: int) -> None:
        raise OSError("Fictional disk interruption")

    monkeypatch.setattr(os, "fsync", interruption)
    fresh = tmp_path / "interrupted.json"
    with pytest.raises(ModelError) as error:
        reports.publish(report, fresh, workspace)
    assert error.value.diagnostics[0].code == "EVIDENCE_WRITE"
    assert not fresh.exists()
    assert lifecycle.verify_lifecycle(workspace)["status"] == "VERIFIED_METADATA"


@pytest.mark.parametrize("name", ["../outside.json", "report.json:stream", "CON.json", "bad.json "])
def test_unsafe_output_path_is_rejected_before_publication(
    evidence: tuple[Path, str, str, dict[str, Any], dict[str, Any]],
    tmp_path: Path,
    name: str,
) -> None:
    workspace, _, _, _, _ = evidence
    with pytest.raises(ModelError) as error:
        reports.publish(_report(evidence), tmp_path / name, workspace)
    assert error.value.diagnostics[0].code in {"EVIDENCE_PATH", "DRIFT_PATH"}


def test_workspace_cannot_receive_an_unsupported_drift_member(
    evidence: tuple[Path, str, str, dict[str, Any], dict[str, Any]],
) -> None:
    workspace, _, _, _, _ = evidence
    with pytest.raises(ModelError) as error:
        reports.publish(_report(evidence), workspace / "drift.json", workspace)
    assert error.value.diagnostics[0].code == "DRIFT_PATH"
    assert not (workspace / "drift.json").exists()


def test_link_or_junction_path_signal_is_never_ignored(
    evidence: tuple[Path, str, str, dict[str, Any], dict[str, Any]],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace, _, _, _, _ = evidence
    report = _report(evidence)
    link = tmp_path / "fictional-junction"
    link.mkdir()
    original = Path.is_junction

    def junction(path: Path) -> bool:
        return path == link or original(path)

    monkeypatch.setattr(Path, "is_junction", junction)
    with pytest.raises(ModelError) as error:
        reports.publish(report, link / "report.json", workspace)
    assert error.value.diagnostics[0].code == "EVIDENCE_PATH"


def test_missing_source_after_valid_report_does_not_use_a_cached_approval(
    evidence: tuple[Path, str, str, dict[str, Any], dict[str, Any]], tmp_path: Path
) -> None:
    workspace, _, aid, _, _ = evidence
    path = tmp_path / "historical.json"
    reports.publish(_report(evidence), path, workspace)
    assert reports.verify_report(workspace, path)["canonical_reproduction"] is True
    (workspace / "analyses" / (aid + ".json")).unlink()
    with pytest.raises(ModelError):
        reports.verify_report(workspace, path)


@pytest.mark.parametrize("value", [True, 0, -1, DRIFT_LIMITS.work_units + 1])
def test_untrusted_resource_limits_cannot_broaden_or_disable_work(value: int) -> None:
    with pytest.raises(ModelError) as error:
        Budget(replace(DRIFT_LIMITS, work_units=value))
    assert error.value.diagnostics[0].code == "DRIFT_LIMIT"


def test_narrowed_limits_are_reproduced_and_must_cover_actual_findings(
    evidence: tuple[Path, str, str, dict[str, Any], dict[str, Any]], tmp_path: Path
) -> None:
    workspace, bid, aid, context, _ = evidence
    report = compare(workspace, bid, [aid], context, limits=replace(DRIFT_LIMITS, findings=100))
    path = tmp_path / "narrow.json"
    reports.publish(report, path, workspace)
    assert reports.verify_report(workspace, path)["canonical_reproduction"] is True
    report["limits"]["findings"] = 1
    path.write_bytes(serialize(_seal(report)))
    with pytest.raises(ModelError):
        reports.verify_report(workspace, path)


@pytest.mark.parametrize("mutation", ["version", "unknown", "nan", "duplicate"])
def test_unknown_report_contract_and_noncanonical_json_fail_closed(
    evidence: tuple[Path, str, str, dict[str, Any], dict[str, Any]],
    tmp_path: Path,
    mutation: str,
) -> None:
    report = _report(evidence)
    if mutation == "version":
        report["drift_version"] = True
    elif mutation == "unknown":
        report["future_field"] = {}
    path = tmp_path / "malformed.json"
    data = serialize(_seal(report))
    if mutation == "nan":
        data = b'{"drift_version":NaN}'
    elif mutation == "duplicate":
        data = b'{"drift_version":1,"drift_version":1}'
    path.write_bytes(data)
    with pytest.raises(ModelError):
        reports.read_report(path)
