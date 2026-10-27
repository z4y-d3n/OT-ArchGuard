"""Independent hostile-input and historical-authority acceptance checks.

These tests compute their own canonical identity oracle. Fictional fixture
metadata establishes integrity relationships, never real owner approvals.
"""

import copy
import errno
import hashlib
import json
import os
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from otarchguard.capture.observations import analyze_capture
from otarchguard.capture.protocols import enrich_capture, validate_enrichment
from otarchguard.diagnostics import ModelError, fail
from otarchguard.evidence import history
from otarchguard.evidence.attachments import build_attachment
from otarchguard.evidence.lifecycle import verify_lifecycle
from otarchguard.evidence.reviews import (
    REVIEW_LIMITATIONS,
    build_baseline,
    build_review,
    validate_baseline,
    validate_reviews,
)
from otarchguard.evidence.workspace import (
    _publish,
    add_snapshot,
    build_snapshot,
    initialize_workspace,
    serialize,
    verify_workspace,
)

FIXTURES = Path(__file__).parent / "fixtures/capture-contract-v2"


def canonical_identity(domain: str, body: dict[str, Any]) -> str:
    """Independent specification, deliberately avoiding production hash helpers."""
    encoded = json.dumps(
        {"domain": "otarchguard." + domain, "value": body},
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("ascii")
    return domain + "-" + hashlib.sha256(encoded).hexdigest()


def tree_bytes(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def legacy_workspace(root: Path, count: int = 2) -> Path:
    root.mkdir()
    source = root / "legacy"
    initialize_workspace(source)
    for variant in ("supported", "limited")[:count]:
        add_snapshot(source, FIXTURES / variant / "observations.json", "Fictional " + variant)
    return source


@pytest.mark.parametrize("count", [0, 1, 2])
def test_migration_preserves_source_bytes_and_accepts_no_approval_from_labels(
    tmp_path: Path, count: int
) -> None:
    source = legacy_workspace(tmp_path / "input", count)
    # Noncanonical formatting is accepted by v1; its exact bytes must survive.
    for snapshot in (source / "snapshots").iterdir():
        value = json.loads(snapshot.read_bytes())
        snapshot.write_bytes((json.dumps(value, indent=4, sort_keys=False) + "\r\n").encode())
    before = tree_bytes(source)
    history.migrate_workspace(source, tmp_path / "history")
    state = history.read_history(tmp_path / "history")
    assert tree_bytes(source) == before
    assert verify_workspace(source)["snapshots"] == count
    assert len(state["snapshots"]) == count
    assert all(not state[k] for k in ("attachments", "analyses", "reviews", "baselines"))
    for name, data in before.items():
        if name.startswith("snapshots/"):
            assert (tmp_path / "history" / name).read_bytes() == data
    with pytest.raises(ModelError):
        verify_workspace(tmp_path / "history")


def test_separate_migrations_produce_identical_objects_without_source_paths(tmp_path: Path) -> None:
    source = legacy_workspace(tmp_path / "input")
    history.migrate_workspace(source, tmp_path / "first")
    history.migrate_workspace(source, tmp_path / "second")
    assert tree_bytes(tmp_path / "first") == tree_bytes(tmp_path / "second")
    assert str(source).encode() not in (tmp_path / "first/workspace.json").read_bytes()


@pytest.mark.parametrize("unexpected", ["raw.pcap", ".pending-migration.json", "extra.json"])
def test_migration_rejects_unexpected_source_root_members(tmp_path: Path, unexpected: str) -> None:
    source = legacy_workspace(tmp_path / "input")
    (source / unexpected).write_bytes(b"unreviewed input")
    before = tree_bytes(source)
    with pytest.raises(ModelError):
        history.migrate_workspace(source, tmp_path / "history")
    assert tree_bytes(source) == before
    assert not (tmp_path / "history/workspace.json").exists()


@pytest.mark.parametrize("bad", [True, 2, -1, "1"])
def test_migration_dispatch_rejects_ambiguous_and_unknown_versions(
    tmp_path: Path, bad: Any
) -> None:
    source = legacy_workspace(tmp_path / "input")
    (source / "workspace.json").write_bytes(
        serialize({"workspace_version": bad, "snapshot_version": 1})
    )
    with pytest.raises(ModelError):
        history.migrate_workspace(source, tmp_path / "history")
    assert not (tmp_path / "history/workspace.json").exists()


def test_rehashed_duplicate_capture_is_still_one_collection_and_migration_rejects_it(
    tmp_path: Path,
) -> None:
    source = legacy_workspace(tmp_path / "input", 1)
    original = next((source / "snapshots").iterdir())
    duplicate = json.loads(original.read_bytes())
    duplicate["label"] = "Fictional independent collection claim"
    body = {k: v for k, v in duplicate.items() if k != "snapshot_id"}
    duplicate["snapshot_id"] = (
        "snapshot-"
        + hashlib.sha256(
            json.dumps(body, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode()
        ).hexdigest()
    )
    (source / "snapshots" / (duplicate["snapshot_id"] + ".json")).write_bytes(serialize(duplicate))
    with pytest.raises(ModelError):
        history.migrate_workspace(source, tmp_path / "history")
    assert not (tmp_path / "history/workspace.json").exists()


def test_migration_rejects_nested_duplicate_json_keys_before_publication(tmp_path: Path) -> None:
    source = legacy_workspace(tmp_path / "input", 1)
    original = next((source / "snapshots").iterdir())
    data = original.read_text(encoding="utf-8")
    data = data.replace('"snapshot_version": 1', '"snapshot_version": 1,"snapshot_version": 1')
    original.write_text(data, encoding="utf-8")
    with pytest.raises(ModelError):
        history.migrate_workspace(source, tmp_path / "history")
    assert not (tmp_path / "history/workspace.json").exists()


def test_migration_never_replaces_existing_destination_even_if_empty(tmp_path: Path) -> None:
    source = legacy_workspace(tmp_path / "input")
    destination = tmp_path / "history"
    destination.mkdir()
    with pytest.raises(ModelError):
        history.migrate_workspace(source, destination)
    assert list(destination.iterdir()) == []


def test_new_history_rejects_unexpected_root_and_object_members(tmp_path: Path) -> None:
    source = legacy_workspace(tmp_path / "input")
    destination = tmp_path / "history"
    history.migrate_workspace(source, destination)
    for directory in (destination, destination / "reviews"):
        unexpected = directory / "unreviewed.json"
        unexpected.write_bytes(b"{}")
        with pytest.raises(ModelError):
            history.read_history(destination)
        unexpected.unlink()
    history.verify_history(destination)


def test_truncated_or_rehashed_snapshot_cannot_acquire_valid_historical_meaning(
    tmp_path: Path,
) -> None:
    source = legacy_workspace(tmp_path / "input", 1)
    destination = tmp_path / "history"
    history.migrate_workspace(source, destination)
    snapshot = next((destination / "snapshots").iterdir())
    previous = snapshot.read_bytes()
    value = json.loads(previous)
    forged = copy.deepcopy(value)
    forged["capture_sha256"] = "f" * 64
    body = {k: v for k, v in forged.items() if k != "snapshot_id"}
    forged["snapshot_id"] = (
        "snapshot-"
        + hashlib.sha256(
            json.dumps(body, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode()
        ).hexdigest()
    )
    snapshot.unlink()
    renamed = snapshot.parent / (forged["snapshot_id"] + ".json")
    renamed.write_bytes(serialize(forged))
    with pytest.raises(ModelError):
        history.verify_history(destination)
    renamed.write_bytes(previous[: len(previous) // 2])
    with pytest.raises(ModelError):
        history.verify_history(destination)


def review_state() -> dict[str, Any]:
    """Minimal already-validated-reference stand-ins isolate the decision graph."""
    return {
        "analyses": {
            "analysis-" + "a" * 64: {"capture_sha256": "1" * 64},
            "analysis-" + "b" * 64: {"capture_sha256": "1" * 64},
            "analysis-" + "c" * 64: {"capture_sha256": "2" * 64},
        },
        "attachments": {},
        "baselines": {},
        "reviews": {},
    }


def review_scope() -> dict[str, Any]:
    return {
        "environment": "Fictional laboratory",
        "purpose": "Future finite historical comparison",
        "coverage": "Unknown outside the selected fictional packets",
        "uncertainties": ["No packet loss measurement"],
        "vantage_points": [],
        "protocols": ["modbus_tcp"],
    }


def proposal(state: dict[str, Any], revision: str = "a") -> dict[str, Any]:
    baseline = build_baseline("evidence", ["analysis-" + revision * 64], review_scope(), state)
    state["baselines"][baseline["baseline_id"]] = baseline
    return baseline


def decision(
    state: dict[str, Any], baseline: dict[str, Any], action: str, previous: str | None = None
) -> dict[str, Any]:
    result = build_review(
        baseline["baseline_id"],
        action,
        "Fictional reviewer",
        "Fictional lifecycle demonstration only",
        state,
        predecessor=previous,
    )
    state["reviews"][result["review_id"]] = result
    return result


def test_baseline_contract_has_an_independent_complete_canonical_oracle() -> None:
    state = review_state()
    scope = review_scope()
    baseline = build_baseline("evidence", ["analysis-" + "a" * 64], scope, state)
    expected = {
        "baseline_version": 1,
        "kind": "evidence",
        "members": [{"analysis_id": "analysis-" + "a" * 64, "capture_sha256": "1" * 64}],
        "model_attachment_id": None,
        "model_sha256": None,
        "scope": scope,
        "scope_sha256": hashlib.sha256(
            json.dumps(scope, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "limitations": list(REVIEW_LIMITATIONS),
    }
    assert baseline == {**expected, "baseline_id": canonical_identity("baseline", expected)}
    assert state["baselines"] == state["reviews"] == {}


def test_review_decision_binds_scope_subject_and_asserted_human_text() -> None:
    state = review_state()
    baseline = proposal(state)
    review = build_review(
        baseline["baseline_id"], "approve", "Fictional reviewer", "Explicit test scope", state
    )
    expected = {
        "review_version": 1,
        "subject_type": "baseline",
        "subject_id": baseline["baseline_id"],
        "decision": "approve",
        "scope_sha256": baseline["scope_sha256"],
        "reviewer": "Fictional reviewer",
        "rationale": "Explicit test scope",
        "evidence_references": ["analysis-" + "a" * 64],
        "predecessor": None,
        "asserted_at": None,
        "limitations": list(REVIEW_LIMITATIONS),
    }
    assert review == {**expected, "review_id": canonical_identity("review", expected)}
    assert state["reviews"] == {}
    assert validate_reviews(state)[baseline["baseline_id"]] == "PROPOSED"


def test_literal_independent_golden_baseline_and_review_contracts() -> None:
    fixture_path = Path(__file__).parent / "fixtures/evidence-history-v1/identity.json"
    fixture = json.loads(fixture_path.read_bytes())
    state = review_state()
    baseline = build_baseline("evidence", [fixture["analysis_id"]], fixture["scope"], state)
    assert baseline == fixture["baseline"]
    assert (
        baseline["baseline_id"]
        == "baseline-"
        + hashlib.sha256(fixture["canonical_baseline_ascii"].encode("ascii")).hexdigest()
    )
    state["baselines"][baseline["baseline_id"]] = baseline
    review = build_review(
        baseline["baseline_id"], "approve", "Fictional reviewer", "Explicit test scope", state
    )
    assert review == fixture["review"]
    assert (
        review["review_id"]
        == "review-" + hashlib.sha256(fixture["canonical_review_ascii"].encode("ascii")).hexdigest()
    )
    changed = copy.deepcopy(fixture["scope"])
    changed["coverage"] = "A different explicit fictional coverage assertion"
    assert (
        build_baseline("evidence", [fixture["analysis_id"]], changed, state)["baseline_id"]
        != baseline["baseline_id"]
    )


def test_new_interpretation_never_inherits_old_approval_and_conflicting_roots_fail() -> None:
    state = review_state()
    first = proposal(state)
    decision(state, first, "approve")
    second = proposal(state, "b")
    assert validate_reviews(state) == {
        first["baseline_id"]: "APPROVED",
        second["baseline_id"]: "PROPOSED",
    }
    with pytest.raises(ModelError):
        decision(state, second, "approve")
    assert len(state["reviews"]) == 1


def test_review_chain_resolution_is_independent_of_dictionary_and_filesystem_order() -> None:
    state = review_state()
    first, second, third = (proposal(state, name) for name in ("a", "b", "c"))
    approval = decision(state, first, "approve")
    successor = decision(state, second, "supersede", approval["review_id"])
    decision(state, second, "revoke", successor["review_id"])
    decision(state, third, "approve")
    expected = {
        first["baseline_id"]: "SUPERSEDED",
        second["baseline_id"]: "REVOKED",
        third["baseline_id"]: "APPROVED",
    }
    assert validate_reviews(state) == expected
    permuted = copy.deepcopy(state)
    permuted["reviews"] = dict(reversed(list(state["reviews"].items())))
    permuted["baselines"] = dict(reversed(list(state["baselines"].items())))
    assert validate_reviews(permuted) == expected
    assert state["reviews"][approval["review_id"]] == approval


def test_one_approval_cannot_have_two_independently_rehashed_successors() -> None:
    state = review_state()
    first, second, third = (proposal(state, name) for name in ("a", "b", "c"))
    approval = decision(state, first, "approve")
    left = build_review(
        second["baseline_id"],
        "supersede",
        "Fictional A",
        "First successor",
        state,
        predecessor=approval["review_id"],
    )
    right = build_review(
        third["baseline_id"],
        "supersede",
        "Fictional B",
        "Second successor",
        state,
        predecessor=approval["review_id"],
    )
    state["reviews"].update({left["review_id"]: left, right["review_id"]: right})
    with pytest.raises(ModelError):
        validate_reviews(state)


@pytest.mark.parametrize("field", ["reviewer", "rationale", "subject_id", "scope_sha256"])
def test_rehashed_reviews_still_require_authoritative_cross_object_relationships(
    field: str,
) -> None:
    state = review_state()
    first = proposal(state)
    approval = decision(state, first, "approve")
    altered = copy.deepcopy(approval)
    altered[field] = "" if field in {"reviewer", "rationale"} else "f" * 64
    body = {k: v for k, v in altered.items() if k != "review_id"}
    altered["review_id"] = canonical_identity("review", body)
    state["reviews"] = {altered["review_id"]: altered}
    with pytest.raises(ModelError):
        validate_reviews(state)


def test_rehashed_baseline_cannot_change_capture_membership_without_exact_revision_join() -> None:
    state = review_state()
    baseline = proposal(state)
    altered = copy.deepcopy(baseline)
    altered["members"][0]["capture_sha256"] = "f" * 64
    altered["baseline_id"] = canonical_identity(
        "baseline", {k: v for k, v in altered.items() if k != "baseline_id"}
    )
    with pytest.raises(ModelError):
        validate_baseline(altered, state)


def test_successor_cannot_silently_expand_approved_scope_or_revoke_an_unrelated_baseline() -> None:
    state = review_state()
    first = proposal(state)
    approval = decision(state, first, "approve")
    second = proposal(state, "b")
    with pytest.raises(ModelError):
        decision(state, second, "revoke", approval["review_id"])
    scope = review_scope()
    scope["environment"] = "Another fictional site"
    expanded = build_baseline("evidence", ["analysis-" + "b" * 64], scope, state)
    state["baselines"][expanded["baseline_id"]] = expanded
    with pytest.raises(ModelError):
        decision(state, expanded, "supersede", approval["review_id"])


@pytest.mark.parametrize(
    "timestamp", ["2026-99-01T00:00:00Z", "2026-02-30T00:00:00Z", "2026-01-01T25:00:00Z"]
)
def test_contextual_timestamp_cannot_claim_an_impossible_calendar_value(timestamp: str) -> None:
    state = review_state()
    baseline = proposal(state)
    with pytest.raises(ModelError):
        build_review(
            baseline["baseline_id"],
            "approve",
            "Fictional reviewer",
            "Fictional assertion",
            state,
            timestamp=timestamp,
        )


def test_disk_full_before_manifest_leaves_source_intact_and_destination_uncommitted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = legacy_workspace(tmp_path / "input")
    before = tree_bytes(source)

    def disk_full(descriptor: int) -> None:
        raise OSError(errno.ENOSPC, "simulated finite destination capacity")

    monkeypatch.setattr(os, "fsync", disk_full)
    with pytest.raises(ModelError):
        history.migrate_workspace(source, tmp_path / "history")
    assert tree_bytes(source) == before
    assert not (tmp_path / "history/workspace.json").exists()
    with pytest.raises(ModelError):
        history.read_history(tmp_path / "history")


def test_interrupted_migration_requires_new_destination_and_keeps_prior_objects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = legacy_workspace(tmp_path / "input")
    before = tree_bytes(source)
    real_publish = _publish
    calls = 0

    def interrupt(path: Path, data: bytes) -> None:
        nonlocal calls
        calls += 1
        if calls == 3:
            fail("EVIDENCE_WRITE", "$", "Simulated interruption before final publication")
        real_publish(path, data)

    monkeypatch.setattr(history, "_publish", interrupt)
    with pytest.raises(ModelError):
        history.migrate_workspace(source, tmp_path / "history")
    partial = tree_bytes(tmp_path / "history")
    assert ".pending-migration.json" in partial
    assert len([name for name in partial if name.startswith("snapshots/")]) == 1
    assert "workspace.json" not in partial
    assert tree_bytes(source) == before
    with pytest.raises(ModelError):
        history.read_history(tmp_path / "history")
    with pytest.raises(ModelError):
        history.migrate_workspace(source, tmp_path / "history")
    assert tree_bytes(tmp_path / "history") == partial


def test_changed_source_after_validation_prevents_committed_migration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = legacy_workspace(tmp_path / "input")
    original = history._migration_source
    calls = 0

    def changed(path: Path, limits: history.HistoryLimits) -> tuple[bytes, dict[str, bytes]]:
        nonlocal calls
        calls += 1
        if calls == 2:
            manifest = source / "workspace.json"
            manifest.write_bytes(manifest.read_bytes() + b"\n")
        return original(path, limits)

    monkeypatch.setattr(history, "_migration_source", changed)
    with pytest.raises(ModelError) as error:
        history.migrate_workspace(source, tmp_path / "history")
    assert error.value.diagnostics[0].code == "EVIDENCE_CHANGED"
    assert not (tmp_path / "history/workspace.json").exists()


def test_resource_rejection_occurs_before_new_destination_is_reserved(tmp_path: Path) -> None:
    source = legacy_workspace(tmp_path / "input")
    before = tree_bytes(source)
    for limits in (
        replace(history.HISTORY_LIMITS, snapshots=1),
        replace(history.HISTORY_LIMITS, workspace_bytes=1),
        replace(history.HISTORY_LIMITS, nodes=1),
        replace(history.HISTORY_LIMITS, depth=1),
    ):
        with pytest.raises(ModelError):
            history.migrate_workspace(source, tmp_path / "history", limits)
        assert not (tmp_path / "history").exists()
        assert tree_bytes(source) == before


@pytest.mark.parametrize("mutation", ["packet_offset", "source_port", "container_counts"])
def test_self_consistent_producer_and_attachment_hashes_do_not_bypass_exact_evidence_joins(
    tmp_path: Path, mutation: str
) -> None:
    capture = Path(__file__).parent / "fixtures/protocol-corpus/synthetic-industrial.pcap"
    snapshot = build_snapshot(analyze_capture(capture))
    enrichment = enrich_capture(capture)
    attachment = build_attachment("enrichment", enrichment, snapshot)
    forged = copy.deepcopy(attachment)
    payload = forged["payload"]
    if mutation == "packet_offset":
        payload["records"][0]["packet"]["offset"] += 1
    elif mutation == "source_port":
        payload["records"][0]["source_port"] = 1234
    else:
        payload["capture"]["unknown_blocks"] += 1
    payload["enrichment_sha256"] = hashlib.sha256(
        json.dumps(
            {k: v for k, v in payload.items() if k != "enrichment_sha256"},
            sort_keys=True,
            ensure_ascii=True,
            separators=(",", ":"),
        ).encode("ascii")
    ).hexdigest()
    # The standalone producer contract is internally consistent. Its additional
    # exact relationship to preserved observations is the consumer's responsibility.
    validate_enrichment(payload)
    forged["component_sha256"] = payload["enrichment_sha256"]
    forged["attachment_id"] = canonical_identity(
        "attachment", {k: v for k, v in forged.items() if k != "attachment_id"}
    )
    workspace = tmp_path / "history"
    history.initialize_history(workspace)
    history.publish_object(workspace, "snapshots", snapshot)
    history.publish_object(workspace, "attachments", forged)
    # Generic object storage deliberately grants no analytical interpretation.
    assert history.verify_history(workspace)["status"] == "VERIFIED_OBJECT_INTEGRITY"
    with pytest.raises(ModelError):
        verify_lifecycle(workspace)
