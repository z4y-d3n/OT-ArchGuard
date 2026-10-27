"""Workspace-v2 migration and storage tested against independent v1 fixtures."""

import errno
import hashlib
import json
import os
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from otarchguard.diagnostics import ModelError, fail
from otarchguard.evidence import history
from otarchguard.evidence.observations import digest
from otarchguard.evidence.workspace import (
    _publish,
    add_snapshot,
    build_snapshot,
    initialize_workspace,
    serialize,
    verify_workspace,
)

FIXTURES = Path(__file__).parent / "fixtures/capture-contract-v2"


def _legacy(tmp_path: Path, variants: tuple[str, ...] = ("supported", "limited")) -> Path:
    source = tmp_path / "legacy"
    initialize_workspace(source)
    for variant in variants:
        add_snapshot(source, FIXTURES / variant / "observations.json", "label " + variant)
    return source


def _bytes(path: Path) -> dict[str, bytes]:
    return {
        str(item.relative_to(path)): item.read_bytes() for item in path.rglob("*") if item.is_file()
    }


def _object(kind: str = "attachment", **fields: Any) -> dict[str, Any]:
    body = {kind + "_version": 1, **fields}
    identity = (
        kind
        + "-"
        + hashlib.sha256(
            json.dumps(
                {"domain": "otarchguard." + kind, "value": body},
                sort_keys=True,
                ensure_ascii=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
    )
    return {**body, kind + "_id": identity}


@pytest.mark.parametrize("variants", [(), ("supported",), ("limited", "supported")])
def test_migration_preserves_source_snapshot_bytes_ids_and_labels(
    tmp_path: Path, variants: tuple[str, ...]
) -> None:
    source = _legacy(tmp_path, variants)
    # Deliberately use a valid noncanonical representation to detect reserialization.
    for path in (source / "snapshots").iterdir():
        path.write_bytes(b" \n" + path.read_bytes().replace(b"\n", b"\r\n") + b"\t")
    original = _bytes(source)
    target = tmp_path / "history"
    result = history.migrate_workspace(source, target)
    assert result["status"] == "MIGRATED_METADATA"
    assert result["physical_collections"] == len(variants)
    assert _bytes(source) == original
    assert verify_workspace(source)["snapshots"] == len(variants)
    state = history.read_history(target)
    assert len(state["snapshots"]) == len(variants)
    assert all(not state[kind] for kind in ("attachments", "analyses", "reviews", "baselines"))
    for entry in result["migration"]["snapshots"]:
        name = "snapshots/" + entry["snapshot_id"] + ".json"
        assert (target / name).read_bytes() == original[str(Path(name))]
        assert entry["snapshot_sha256"] == hashlib.sha256(original[str(Path(name))]).hexdigest()
        assert state["snapshots"][entry["snapshot_id"]]["label"].startswith("label ")
    with pytest.raises(ModelError):
        verify_workspace(target)


def test_repeated_migration_and_existing_destination_never_overwrite(tmp_path: Path) -> None:
    source = _legacy(tmp_path)
    target = tmp_path / "history"
    history.migrate_workspace(source, target)
    before = _bytes(target)
    with pytest.raises(ModelError) as error:
        history.migrate_workspace(source, target)
    assert error.value.diagnostics[0].code == "EVIDENCE_EXISTS"
    assert _bytes(target) == before


@pytest.mark.parametrize("location", ["same", "inside", "parent"])
def test_migration_requires_separate_source_destination_trees(
    tmp_path: Path, location: str
) -> None:
    source = _legacy(tmp_path)
    target = {"same": source, "inside": source / "new", "parent": tmp_path}[location]
    before = _bytes(source)
    with pytest.raises(ModelError):
        history.migrate_workspace(source, target)
    assert _bytes(source) == before


@pytest.mark.parametrize(
    "mutation", ["manifest", "truncated", "missing", "version", "duplicate", "extra"]
)
def test_corrupt_source_never_reserves_destination(tmp_path: Path, mutation: str) -> None:
    source = _legacy(tmp_path, ("supported",))
    snapshot_path = next((source / "snapshots").iterdir())
    if mutation == "manifest":
        (source / "workspace.json").write_bytes(b'{"workspace_version":true,"snapshot_version":1}')
    elif mutation == "truncated":
        snapshot_path.write_bytes(b'{"snapshot_version":1,')
    elif mutation == "missing":
        # Migration cannot recover an absent object from an unindexed legacy workspace.
        # An invalid dangling entry does have to be rejected.
        snapshot_path.rename(snapshot_path.with_name("snapshot-" + "0" * 64 + ".json"))
    elif mutation == "version":
        value = json.loads(snapshot_path.read_bytes())
        value["snapshot_version"] = 2
        snapshot_path.write_bytes(serialize(value))
    elif mutation == "duplicate":
        value = json.loads(snapshot_path.read_bytes())
        second = build_snapshot(value["observations"], "different label")
        (source / "snapshots" / (second["snapshot_id"] + ".json")).write_bytes(serialize(second))
    else:
        (source / "unexpected.json").write_bytes(b"{}")
    before = _bytes(source)
    target = tmp_path / "history"
    with pytest.raises(ModelError):
        history.migrate_workspace(source, target)
    assert not target.exists()
    assert _bytes(source) == before


def test_migrated_snapshot_reserialization_is_detected_even_when_semantically_identical(
    tmp_path: Path,
) -> None:
    source = _legacy(tmp_path, ("supported",))
    target = tmp_path / "history"
    history.migrate_workspace(source, target)
    snapshot = next((target / "snapshots").iterdir())
    snapshot.write_bytes(snapshot.read_bytes() + b" ")
    with pytest.raises(ModelError) as error:
        history.read_history(target)
    assert error.value.diagnostics[0].code == "EVIDENCE_MIGRATION"


def test_missing_declared_migration_member_is_detected(tmp_path: Path) -> None:
    source = _legacy(tmp_path, ("supported",))
    target = tmp_path / "history"
    history.migrate_workspace(source, target)
    next((target / "snapshots").iterdir()).unlink()
    with pytest.raises(ModelError):
        history.read_history(target)


def test_input_change_between_validation_and_commit_leaves_uncommitted_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = _legacy(tmp_path, ("supported",))
    target = tmp_path / "history"
    original_publish = _publish

    def changed(path: Path, data: bytes) -> None:
        original_publish(path, data)
        if path.parent.name == "snapshots":
            manifest = source / "workspace.json"
            manifest.write_bytes(manifest.read_bytes() + b" ")

    monkeypatch.setattr(history, "_publish", changed)
    with pytest.raises(ModelError) as error:
        history.migrate_workspace(source, target)
    assert error.value.diagnostics[0].code == "EVIDENCE_CHANGED"
    assert not (target / "workspace.json").exists()
    assert (target / ".pending-migration.json").is_file()
    with pytest.raises(ModelError):
        history.read_history(target)
    with pytest.raises(ModelError):
        history.migrate_workspace(source, target)


def test_disk_failure_is_controlled_and_source_remains_untouched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = _legacy(tmp_path, ("supported",))
    original = _bytes(source)
    target = tmp_path / "history"

    def no_space(descriptor: int) -> None:
        raise OSError(errno.ENOSPC, "fictional disk full")

    monkeypatch.setattr(os, "fsync", no_space)
    with pytest.raises(ModelError) as error:
        history.migrate_workspace(source, target)
    assert error.value.diagnostics[0].code == "EVIDENCE_WRITE"
    assert _bytes(source) == original
    assert not (target / "workspace.json").exists()
    with pytest.raises(ModelError):
        history.read_history(target)


@pytest.mark.parametrize(
    "field,limit",
    [("snapshots", 0), ("workspace_bytes", 64), ("object_bytes", 64), ("depth", 2), ("nodes", 10)],
)
def test_migration_resource_bounds_precede_destination_creation(
    tmp_path: Path, field: str, limit: int
) -> None:
    source = _legacy(tmp_path)
    target = tmp_path / "history"
    limits = replace(history.HISTORY_LIMITS, **{field: limit})
    with pytest.raises(ModelError):
        history.migrate_workspace(source, target, limits)
    assert not target.exists()


def test_initialize_new_workspace_has_explicit_version_and_no_authority(tmp_path: Path) -> None:
    root = tmp_path / "history"
    history.initialize_history(root)
    state = history.read_history(root)
    assert state["manifest"]["workspace_version"] == 2
    assert state["manifest"]["migration"] is None
    result = history.verify_history(root)
    assert result["physical_collections"] == 0
    assert result["reviews"] == result["baselines"] == 0
    assert history.workspace_version(root) == 2
    with pytest.raises(ModelError):
        history.initialize_history(root)


def test_generic_content_store_requires_callback_for_semantic_validation(tmp_path: Path) -> None:
    root = tmp_path / "history"
    history.initialize_history(root)
    value = _object(payload="local metadata only")
    prospective_sizes = []

    def validator(state: dict[str, Any]) -> None:
        prospective_sizes.append(len(state["attachments"]))
        assert state["attachments"][value["attachment_id"]] == value

    added = history.publish_object(root, "attachments", value, validator)
    assert added == {"status": "ADDED", "object_id": value["attachment_id"]}
    before = _bytes(root)
    assert (
        history.publish_object(root, "attachments", value, validator)["status"] == "ALREADY_PRESENT"
    )
    assert _bytes(root) == before
    assert prospective_sizes == [1, 1]
    with pytest.raises(ModelError):
        history.publish_object(root, "attachments", {**value, "payload": "changed"})
    assert _bytes(root) == before


def test_semantic_callback_rejection_publishes_no_object(tmp_path: Path) -> None:
    root = tmp_path / "history"
    history.initialize_history(root)
    before = _bytes(root)

    def reject(state: dict[str, Any]) -> None:
        fail("EVIDENCE_JOIN", "$", "Fictional invalid cross-artifact join")

    with pytest.raises(ModelError):
        history.publish_object(root, "analyses", _object("analysis"), reject)
    assert _bytes(root) == before


def test_new_collection_can_be_added_after_migration_without_changing_provenance(
    tmp_path: Path,
) -> None:
    source = _legacy(tmp_path, ("supported",))
    root = tmp_path / "history"
    history.migrate_workspace(source, root)
    manifest = (root / "workspace.json").read_bytes()
    history.add_collection(root, FIXTURES / "limited/observations.json", "another")
    assert history.verify_history(root)["physical_collections"] == 2
    assert (root / "workspace.json").read_bytes() == manifest
    before = _bytes(root)
    duplicate = history.add_collection(root, FIXTURES / "limited/observations.json", "different")
    assert duplicate["status"] == "DUPLICATE_CAPTURE"
    assert duplicate["label_match"] is False
    assert _bytes(root) == before


def test_direct_duplicate_physical_collection_publication_fails(tmp_path: Path) -> None:
    root = tmp_path / "history"
    history.initialize_history(root)
    observation = json.loads((FIXTURES / "supported/observations.json").read_bytes())
    history.publish_object(root, "snapshots", build_snapshot(observation, "first"))
    with pytest.raises(ModelError):
        history.publish_object(root, "snapshots", build_snapshot(observation, "other"))
    assert history.verify_history(root)["physical_collections"] == 1


@pytest.mark.parametrize("location", ["root", "folder", "pending", "directory", "renamed"])
def test_strict_workspace_inventory_rejects_unexpected_members(
    tmp_path: Path, location: str
) -> None:
    root = tmp_path / "history"
    history.initialize_history(root)
    if location == "root":
        (root / "extra.json").write_bytes(b"{}")
    elif location == "folder":
        (root / "reviews" / "anything.json").write_bytes(b"{}")
    elif location == "pending":
        (root / "analyses" / ".pending-interrupted.tmp").write_bytes(b"{}")
    elif location == "directory":
        (root / "baselines" / ("baseline-" + "0" * 64 + ".json")).mkdir()
    else:
        value = _object()
        (root / "attachments" / ("attachment-" + "0" * 64 + ".json")).write_bytes(serialize(value))
    with pytest.raises(ModelError):
        history.read_history(root)


@pytest.mark.parametrize("document", [b"[]", b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1.5}', b"\xff"])
def test_lifecycle_document_reader_is_strict(tmp_path: Path, document: bytes) -> None:
    path = tmp_path / "input.json"
    path.write_bytes(document)
    with pytest.raises(ModelError):
        history.read_document(path)


def test_manifest_type_confusion_unknown_version_and_rehashed_invalid_object(
    tmp_path: Path,
) -> None:
    root = tmp_path / "history"
    history.initialize_history(root)
    manifest = json.loads((root / "workspace.json").read_bytes())
    manifest["snapshot_version"] = True
    (root / "workspace.json").write_bytes(serialize(manifest))
    with pytest.raises(ModelError):
        history.read_history(root)
    manifest["snapshot_version"] = 1
    (root / "workspace.json").write_bytes(serialize(manifest))
    bad: dict[str, Any] = {"attachment_version": 2}
    bad["attachment_id"] = "attachment-" + digest(
        {"domain": "otarchguard.attachment", "value": bad}
    )
    with pytest.raises(ModelError):
        history.publish_object(root, "attachments", bad)


def test_workspace_count_limit_checks_before_publication(tmp_path: Path) -> None:
    root = tmp_path / "history"
    history.initialize_history(root)
    with pytest.raises(ModelError):
        history.publish_object(
            root, "attachments", _object(), limits=replace(history.HISTORY_LIMITS, attachments=0)
        )
    assert list((root / "attachments").iterdir()) == []


def test_simulated_reparse_source_is_rejected_without_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = _legacy(tmp_path)
    original = Path.is_junction

    def reparse(path: Path) -> bool:
        return path == source or original(path)

    monkeypatch.setattr(Path, "is_junction", reparse)
    with pytest.raises(ModelError):
        history.migrate_workspace(source, tmp_path / "history")
    assert not (tmp_path / "history").exists()
