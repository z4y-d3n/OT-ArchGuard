"""Public-operation freshness, full trust coverage and bounded reuse regressions."""

from pathlib import Path
from typing import Any

import pytest

import otarchguard.evidence.history as history
import otarchguard.evidence.lifecycle as lifecycle
import otarchguard.evidence.reviews as reviews
import otarchguard.evidence.validation as validation
from otarchguard.diagnostics import ModelError, fail
from otarchguard.evidence.workspace import serialize

FIXTURE = Path(__file__).parent / "fixtures/capture-contract-v2/supported/observations.json"


def prepare(tmp_path: Path, proposals: int = 1) -> tuple[Path, str, str, list[str]]:
    workspace = tmp_path / "history"
    history.initialize_history(workspace)
    history.add_collection(workspace, FIXTURE)
    sid = next(iter(history.read_history(workspace)["snapshots"]))
    aid = lifecycle.create_revision(workspace, sid)["analysis"]["analysis_id"]
    bids = []
    for index in range(proposals):
        scope = tmp_path / f"scope-{index}.json"
        scope.write_bytes(
            serialize(
                {
                    "environment": "Fictional operation test",
                    "purpose": f"Independent fictional scope {index}",
                    "coverage": "Unknown outside selected packets",
                    "uncertainties": [],
                    "protocols": [],
                    "vantage_points": [],
                }
            )
        )
        bids.append(lifecycle.propose_baseline(workspace, scope, [aid])["baseline"]["baseline_id"])
    return workspace, sid, aid, bids


def captured_bytes(path: Path) -> dict[str, bytes]:
    return {p.relative_to(path).as_posix(): p.read_bytes() for p in path.rglob("*") if p.is_file()}


@pytest.mark.parametrize("operation", ["verify", "list", "revisions", "baselines", "show"])
def test_read_operations_acquire_each_workspace_file_once_and_resolve_reviews_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
) -> None:
    workspace, _, aid, _ = prepare(tmp_path, proposals=5)
    original_read = history._read_bytes
    original_resolve = reviews.validate_reviews
    acquisitions: list[Path] = []
    resolutions = []

    def read(path: Path, limits: history.HistoryLimits) -> bytes:
        acquisitions.append(path)
        return original_read(path, limits)

    def resolve(state: dict[str, Any]) -> dict[str, str]:
        resolutions.append(len(state["reviews"]))
        return original_resolve(state)

    monkeypatch.setattr(history, "_read_bytes", read)
    monkeypatch.setattr(validation, "validate_reviews", resolve)
    monkeypatch.setattr(reviews, "validate_reviews", resolve)
    if operation == "verify":
        assert lifecycle.verify_lifecycle(workspace)["baselines"] == 5
    elif operation == "list":
        assert len(lifecycle.list_history(workspace)["baselines"]) == 5
    elif operation == "revisions":
        assert len(lifecycle.list_revisions(workspace)["analyses"]) == 1
    elif operation == "baselines":
        assert len(lifecycle.list_baselines(workspace)["baselines"]) == 5
    else:
        assert lifecycle.show_object(workspace, "analyses", aid)["analysis_id"] == aid
    assert len(acquisitions) == len(captured_bytes(workspace))
    assert len(set(acquisitions)) == len(acquisitions)
    assert resolutions == [0]


def test_approval_resolves_exact_prospective_graph_without_postpublication_rescan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace, _, _, bids = prepare(tmp_path)
    before = captured_bytes(workspace)
    acquired: list[Path] = []
    original = history._read_bytes

    def read(path: Path, limits: history.HistoryLimits) -> bytes:
        acquired.append(path)
        return original(path, limits)

    monkeypatch.setattr(history, "_read_bytes", read)
    approved = lifecycle.record_review(
        workspace, bids[0], "approve", "Fictional reviewer", "Fictional test only"
    )
    assert approved["status"] == "ADDED" and approved["baseline_status"] == "APPROVED"
    assert len(acquired) == len(before) * 2  # Acquisition plus exact-byte publication recheck.
    after = captured_bytes(workspace)
    assert all(after[name] == raw for name, raw in before.items())
    assert len(after) == len(before) + 1


def test_failed_publication_never_returns_or_records_prospective_approval(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace, _, _, bids = prepare(tmp_path)
    before = captured_bytes(workspace)

    def interrupted(*args: Any) -> None:
        fail("EVIDENCE_CHANGED", "$", "Injected change at publication boundary.")

    with monkeypatch.context() as patch:
        patch.setattr(history, "_check_image", interrupted)
        with pytest.raises(ModelError):
            lifecycle.record_review(
                workspace, bids[0], "approve", "Fictional reviewer", "Fictional test only"
            )
    assert captured_bytes(workspace) == before
    assert lifecycle.show_object(workspace, "baselines", bids[0])["status"] == "PROPOSED"


def test_returned_public_state_cannot_seed_authority_in_a_later_operation(tmp_path: Path) -> None:
    workspace, _, _, bids = prepare(tmp_path)
    first = lifecycle.load_state(workspace)
    first["baselines"][bids[0]]["scope"]["coverage"] = "Forged complete monitoring"
    first["reviews"]["review-" + "f" * 64] = {"decision": "approve", "subject_id": bids[0]}
    second = lifecycle.load_state(workspace)
    assert second["reviews"] == {}
    assert second["baselines"][bids[0]]["scope"]["coverage"] == "Unknown outside selected packets"
    assert lifecycle.show_object(workspace, "baselines", bids[0])["status"] == "PROPOSED"


def test_idempotent_approval_after_revocation_keeps_current_revoked_state(tmp_path: Path) -> None:
    workspace, _, _, bids = prepare(tmp_path)
    approval = lifecycle.record_review(
        workspace, bids[0], "approve", "Fictional reviewer", "Exact fictional assertion"
    )
    lifecycle.record_review(
        workspace,
        bids[0],
        "revoke",
        "Fictional reviewer",
        "Withdraw fictional assertion",
        approval["review"]["review_id"],
    )
    result = lifecycle.record_review(
        workspace, bids[0], "approve", "Fictional reviewer", "Exact fictional assertion"
    )
    assert result["status"] == "ALREADY_PRESENT"
    assert result["baseline_status"] == "REVOKED"
    assert lifecycle.verify_lifecycle(workspace)["reviews"] == 2


def test_input_selection_failures_keep_legacy_diagnostic_order(tmp_path: Path) -> None:
    workspace, sid, _, _ = prepare(tmp_path)
    missing = tmp_path / "absent.json"
    with pytest.raises(ModelError) as absent_snapshot:
        lifecycle.import_attachment(workspace, "snapshot-" + "f" * 64, "model", missing)
    assert absent_snapshot.value.diagnostics[0].code == "EVIDENCE_NOT_FOUND"
    with pytest.raises(ModelError) as absent_attachment:
        lifecycle.create_revision(workspace, sid, model="attachment-" + "f" * 64, semantics=missing)
    assert absent_attachment.value.diagnostics[0].code == "EVIDENCE_NOT_FOUND"
