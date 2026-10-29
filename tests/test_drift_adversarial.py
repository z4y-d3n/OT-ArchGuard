"""Independent hostile rehashing, authority and publication boundary challenges."""

import copy
import hashlib
import json
import os
import shutil
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from otarchguard.diagnostics import ModelError
from otarchguard.drift.contract import DRIFT_LIMITS
from otarchguard.drift.engine import compare
from otarchguard.drift.reports import publish, read_report, verify_report
from otarchguard.evidence import lifecycle
from tools.drift_walkthrough import canonical, comparison_context, prepare


@pytest.fixture(scope="module")
def drift_case(tmp_path_factory: pytest.TempPathFactory) -> tuple[dict[str, Any], dict[str, Any]]:
    selection = prepare(tmp_path_factory.mktemp("independent-drift") / "source")
    reference = selection["periods"]["reference"]["analysis_id"]
    candidate = selection["periods"]["candidate"]["analysis_id"]
    context = comparison_context(reference, candidate, selection["scope"])
    report = compare(Path(selection["workspace"]), selection["baseline_id"], [candidate], context)
    return selection, report


def _reseal(report: dict[str, Any]) -> None:
    # This attacker knows the complete canonical hash algorithm. Rehashing must
    # still confer no authority over independently replayed analytical findings.
    body = {k: v for k, v in report.items() if k != "drift_id"}
    report["drift_id"] = (
        "drift-"
        + hashlib.sha256(canonical({"domain": "otarchguard.drift.v1", "value": body})).hexdigest()
    )


@pytest.mark.parametrize(
    "attack",
    [
        "finding",
        "aggregate",
        "comparability",
        "source",
        "approval",
        "implementation",
        "limit",
        "mode",
        "context",
        "limitations",
        "frontier",
        "extra",
    ],
)
def test_self_consistent_report_hash_does_not_authorize_fabricated_meaning(
    tmp_path: Path,
    drift_case: tuple[dict[str, Any], dict[str, Any]],
    attack: str,
) -> None:
    selection, original = drift_case
    report = copy.deepcopy(original)
    if attack == "finding":
        report["comparisons"][0]["findings"][0]["explanation"] = "Attacker fabricated evidence"
    elif attack == "aggregate":
        report["summary"]["findings"] += 1
    elif attack == "comparability":
        report["comparisons"][0]["comparability"]["asset_continuity"] = "COMPARABLE"
    elif attack == "source":
        report["inputs"]["candidate_sources"][0]["capture_sha256"] = "0" * 64
    elif attack == "approval":
        report["inputs"]["approval"]["reviewer"] = "Attacker organization root"
    elif attack == "implementation":
        report["implementation_sha256"]["drift/engine.py"] = "1" * 64
    elif attack == "limit":
        report["limits"]["work_units"] = True
    elif attack == "mode":
        report["options"]["mode"] = "force-comparable"
    elif attack == "context":
        report["options"]["context"]["pairs"][0]["alignment"] = "authenticated"
    elif attack == "limitations":
        report["limitations"] = []
    elif attack == "frontier":
        report["inputs"]["review_frontier"] = []
    else:
        report["trusted"] = True
    _reseal(report)
    path = tmp_path / "forged.json"
    path.write_bytes(canonical(report))
    with pytest.raises(ModelError):
        verify_report(Path(selection["workspace"]), path)
    output = tmp_path / "forged-publication.json"
    with pytest.raises(ModelError):
        publish(report, output, Path(selection["workspace"]))
    assert not output.exists()
    assert original == drift_case[1]


@pytest.mark.parametrize(
    "payload",
    [
        b'{"drift_version":1,"drift_version":1}',
        b'{"drift_version":NaN}',
        b'{"drift_version":1.0}',
        b'{"drift_version":true}',
        b'{"drift_version":2}',
        b'{"drift_version":1,"value":"\\ud800"}',
        b'{"drift_version":1,',
        b"\xff",
        b"[]",
        b"[" * 70 + b"]" * 70,
    ],
)
def test_hostile_report_documents_fail_with_controlled_diagnostics(
    tmp_path: Path, payload: bytes
) -> None:
    source = tmp_path / "hostile.json"
    source.write_bytes(payload)
    with pytest.raises(ModelError):
        read_report(source)


@pytest.mark.parametrize("target", ["existing", "traversal", "ads", "suffix", "workspace"])
def test_report_output_policy_never_overwrites_or_expands_workspace(
    tmp_path: Path,
    drift_case: tuple[dict[str, Any], dict[str, Any]],
    target: str,
) -> None:
    selection, report = drift_case
    workspace = Path(selection["workspace"])
    if target == "existing":
        destination = tmp_path / "existing.json"
        destination.write_bytes(b"preserved sentinel")
    elif target == "traversal":
        destination = tmp_path / ".." / "escaped.json"
    elif target == "ads":
        destination = tmp_path / "report.json:hidden"
    elif target == "suffix":
        destination = tmp_path / "report.txt"
    else:
        destination = workspace / "drift.json"
    before = {p.relative_to(workspace): p.read_bytes() for p in workspace.rglob("*") if p.is_file()}
    with pytest.raises(ModelError):
        publish(report, destination, workspace)
    after = {p.relative_to(workspace): p.read_bytes() for p in workspace.rglob("*") if p.is_file()}
    assert before == after
    if target == "existing":
        assert destination.read_bytes() == b"preserved sentinel"
    else:
        assert not destination.exists()


@pytest.mark.parametrize(
    "field", ["findings", "keys", "references", "protocol_records", "work_units", "report_bytes"]
)
def test_narrowed_resource_limits_abort_entire_comparison(
    drift_case: tuple[dict[str, Any], dict[str, Any]],
    field: str,
) -> None:
    selection, _ = drift_case
    reference = selection["periods"]["reference"]["analysis_id"]
    candidate = selection["periods"]["candidate"]["analysis_id"]
    with pytest.raises(ModelError):
        compare(
            Path(selection["workspace"]),
            selection["baseline_id"],
            [candidate],
            comparison_context(reference, candidate, selection["scope"]),
            limits=replace(DRIFT_LIMITS, **{field: 1}),
        )


def test_revocation_is_freshly_checked_but_old_report_remains_reproducible(
    tmp_path: Path,
    drift_case: tuple[dict[str, Any], dict[str, Any]],
) -> None:
    selection, report = drift_case
    workspace = tmp_path / "history"
    shutil.copytree(Path(selection["workspace"]), workspace)
    source = tmp_path / "before-revocation.json"
    publish(report, source, workspace)
    original = source.read_bytes()
    assert verify_report(workspace, source)["currently_approved_reference"] is True
    lifecycle.record_review(
        workspace,
        selection["baseline_id"],
        "revoke",
        "Fictional owner",
        "Independent revocation challenge",
        predecessor=selection["approval_id"],
    )
    reference = selection["periods"]["reference"]["analysis_id"]
    candidate = selection["periods"]["candidate"]["analysis_id"]
    with pytest.raises(ModelError):
        compare(
            workspace,
            selection["baseline_id"],
            [candidate],
            comparison_context(reference, candidate, selection["scope"]),
        )
    verified = verify_report(workspace, source)
    assert verified["current_baseline_status"] == "REVOKED"
    assert verified["currently_approved_reference"] is False
    assert verified["canonical_reproduction"] is True
    assert source.read_bytes() == original
    with pytest.raises(ModelError):
        publish(report, tmp_path / "new-after-revocation.json", workspace)


def test_rehashed_cross_capture_revision_is_rejected_by_lifecycle_consumer(
    tmp_path: Path,
    drift_case: tuple[dict[str, Any], dict[str, Any]],
) -> None:
    selection, _ = drift_case
    workspace = tmp_path / "history"
    shutil.copytree(Path(selection["workspace"]), workspace)
    candidate = selection["periods"]["candidate"]["analysis_id"]
    path = workspace / "analyses" / (candidate + ".json")
    value = json.loads(path.read_bytes())
    original_state = lifecycle.load_state(workspace)
    reference = selection["periods"]["reference"]["analysis_id"]
    value["capture_sha256"] = original_state["analyses"][reference]["capture_sha256"]
    body = {k: v for k, v in value.items() if k != "analysis_id"}
    value["analysis_id"] = (
        "analysis-"
        + hashlib.sha256(canonical({"domain": "otarchguard.analysis", "value": body})).hexdigest()
    )
    path.unlink()
    (path.parent / (value["analysis_id"] + ".json")).write_bytes(canonical(value))
    with pytest.raises(ModelError):
        compare(
            workspace,
            selection["baseline_id"],
            [value["analysis_id"]],
            comparison_context(reference, value["analysis_id"], selection["scope"]),
        )


def test_interrupted_atomic_report_publication_leaves_no_destination(
    tmp_path: Path,
    drift_case: tuple[dict[str, Any], dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selection, report = drift_case
    destination = tmp_path / "interrupted.json"

    def interrupted(descriptor: int) -> None:
        raise OSError("Fictional interrupted flush")

    monkeypatch.setattr(os, "fsync", interrupted)
    with pytest.raises(ModelError):
        publish(report, destination, Path(selection["workspace"]))
    assert not destination.exists()
    assert list(tmp_path.iterdir()) == []
