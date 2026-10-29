"""Bounded, append-only workspace-v2 storage and byte-preserving v1 migration.

The manifest is the publication point for a fresh workspace. New workspaces are
reserved with exclusive mkdir; until workspace.json is published they cannot be
read as committed workspaces. Failed operations deliberately retain their files
for human inspection. This is a local single-writer contract, not an OS sandbox.
"""

import hashlib
import os
import re
import stat
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from otarchguard.diagnostics import check_limit, fail
from otarchguard.evidence.observations import digest
from otarchguard.evidence.paths import _check_read_path
from otarchguard.evidence.workspace import (
    EVIDENCE_LIMITS,
    EvidenceLimits,
    _decode,
    _file_identity,
    _local,
    _publish,
    build_snapshot,
    serialize,
    validate_snapshot,
)


@dataclass(frozen=True, slots=True)
class HistoryLimits:
    """Finite work bounds; these are ceilings, not performance promises."""

    workspace_bytes: int = 256 * 1024 * 1024
    object_bytes: int = 64 * 1024 * 1024
    snapshots: int = 256
    attachments: int = 1024
    analyses: int = 1024
    reviews: int = 1024
    baselines: int = 256
    depth: int = 64
    nodes: int = 2_000_000


HISTORY_LIMITS = HistoryLimits()
_KINDS = {
    "snapshots": "snapshot",
    "attachments": "attachment",
    "analyses": "analysis",
    "reviews": "review",
    "baselines": "baseline",
}
_VERSIONS = {
    "workspace_version": 2,
    "snapshot_version": 1,
    "attachment_version": 1,
    "analysis_version": 1,
    "review_version": 1,
    "baseline_version": 1,
}
_SHA = re.compile(r"[0-9a-f]{64}$")
HistoryState = dict[str, Any]
StateValidator = Callable[[HistoryState], None]


@dataclass(frozen=True, slots=True)
class _HistoryImage:
    """One operation's bounded, verified acquisition, never a persistent cache.

    Only private lifecycle orchestration retains this image. Returned public
    states carry no reusable filesystem authority. Raw buffers are released as
    each file is decoded; receipts retain only exact byte length and SHA-256.
    """

    path: Path
    limits: HistoryLimits
    state: HistoryState
    inventories: dict[str, tuple[str, ...]]
    files: dict[str, tuple[int, str]]
    total_bytes: int


def _evidence_limits(limits: HistoryLimits) -> EvidenceLimits:
    return replace(
        EVIDENCE_LIMITS,
        workspace_bytes=limits.workspace_bytes,
        snapshot_bytes=limits.object_bytes,
        snapshots=limits.snapshots,
        depth=limits.depth,
        nodes=limits.nodes,
    )


def _read_bytes(path: Path, limits: HistoryLimits) -> bytes:
    """Read exact regular-file bytes while detecting replacement or modification."""
    _check_read_path(path)
    try:
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode):
            fail("EVIDENCE_FILE", "$", "Evidence input must be a regular local file.")
        check_limit("history_object_bytes", before.st_size, limits.object_bytes)
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        with os.fdopen(os.open(path, flags), "rb") as stream:
            opened = os.fstat(stream.fileno())
            if _file_identity(opened) != _file_identity(before):
                fail("EVIDENCE_CHANGED", "$", "Evidence changed while opening.")
            # A read(size) can allocate the entire requested buffer even when
            # the regular file is tiny. One byte past the verified open size
            # detects growth without reserving the configured maximum.
            data = stream.read(min(opened.st_size, limits.object_bytes) + 1)
            after = os.fstat(stream.fileno())
        _check_read_path(path)
        named = path.lstat()
        if (
            _file_identity(opened) != _file_identity(after)
            or opened.st_ctime_ns != after.st_ctime_ns
            or _file_identity(after) != _file_identity(named)
            # Windows lstat/fstat may expose different ctime meanings; compare
            # ctime only between observations made through the same API.
            or before.st_ctime_ns != named.st_ctime_ns
            or len(data) != opened.st_size
        ):
            fail("EVIDENCE_CHANGED", "$", "Evidence changed during reading.")
    except OSError:
        fail("EVIDENCE_READ", "$", "Cannot read local historical evidence.")
    check_limit("history_object_bytes", len(data), limits.object_bytes)
    return data


def read_document(path: Path, limits: HistoryLimits = HISTORY_LIMITS) -> dict[str, Any]:
    """Bounded strict JSON input for lifecycle operations and scope documents."""
    return _decode(_read_bytes(path, limits), _evidence_limits(limits))


def workspace_version(path: Path, limits: HistoryLimits = HISTORY_LIMITS) -> int:
    """Dispatch only an explicitly supported manifest version, without migration."""
    manifest = read_document(path / "workspace.json", limits)
    version = manifest.get("workspace_version")
    if type(version) is not int or version not in {1, 2}:
        fail("EVIDENCE_WORKSPACE", "$", "Unsupported workspace version.")
    return version


def _directory(path: Path) -> None:
    _local(path)
    try:
        if not stat.S_ISDIR(path.lstat().st_mode):
            fail("EVIDENCE_WORKSPACE", "$", "Workspace member must be a real directory.")
    except OSError:
        fail("EVIDENCE_WORKSPACE", "$", "Workspace directory is unavailable.")


def _members(path: Path, maximum: int) -> list[Path]:
    _directory(path)
    members: list[Path] = []
    try:
        # Path.iterdir materializes scandir on Python 3.14 before yielding. Use
        # scandir directly so an oversized directory stops at maximum + 1.
        with os.scandir(path) as entries:
            for member in entries:
                check_limit("history_directory_members", len(members) + 1, maximum)
                members.append(Path(member.path))
    except OSError:
        fail("EVIDENCE_READ", "$", "Cannot inspect workspace members.")
    return sorted(members)


def _id(kind: str, value: dict[str, Any]) -> str:
    singular = _KINDS[kind]
    identity = value.get(singular + "_id")
    if not isinstance(identity, str) or re.fullmatch(singular + r"-[0-9a-f]{64}", identity) is None:
        fail("EVIDENCE_ID", "$", "Object requires an exact content identity.")
    return identity


def _object(kind: str, value: dict[str, Any], limits: HistoryLimits) -> None:
    identity = _id(kind, value)
    if kind == "snapshots":
        validate_snapshot(value, _evidence_limits(limits))
        return
    singular = _KINDS[kind]
    version = value.get(singular + "_version")
    if type(version) is not int or version != 1:
        fail("EVIDENCE_VERSION", "$", "Unsupported immutable historical object version.")
    body = {k: v for k, v in value.items() if k != singular + "_id"}
    expected = singular + "-" + digest({"domain": "otarchguard." + singular, "value": body})
    if identity != expected:
        fail("EVIDENCE_INTEGRITY", "$", "Historical object content identity mismatch.")


def _manifest(value: dict[str, Any], limits: HistoryLimits) -> None:
    if set(value) != {*_VERSIONS, "migration"} or any(
        type(value[key]) is not int or value[key] != version for key, version in _VERSIONS.items()
    ):
        fail("EVIDENCE_WORKSPACE", "$", "Unsupported or malformed workspace-v2 manifest.")
    provenance = value["migration"]
    if provenance is None:
        return
    if not isinstance(provenance, dict) or set(provenance) != {
        "source_workspace_version",
        "source_manifest_sha256",
        "snapshots",
    }:
        fail("EVIDENCE_MIGRATION", "$", "Invalid migration provenance.")
    if (
        type(provenance["source_workspace_version"]) is not int
        or provenance["source_workspace_version"] != 1
        or not isinstance(provenance["source_manifest_sha256"], str)
        or not _SHA.fullmatch(provenance["source_manifest_sha256"])
        or not isinstance(provenance["snapshots"], list)
    ):
        fail("EVIDENCE_MIGRATION", "$", "Invalid migration source identity.")
    check_limit("history_migration_members", len(provenance["snapshots"]), limits.snapshots)
    previous = ""
    captures: set[str] = set()
    for entry in provenance["snapshots"]:
        if not isinstance(entry, dict) or set(entry) != {
            "snapshot_id",
            "snapshot_sha256",
            "capture_sha256",
            "observations_sha256",
        }:
            fail("EVIDENCE_MIGRATION", "$", "Invalid migration snapshot provenance.")
        sid = entry["snapshot_id"]
        if (
            not isinstance(sid, str)
            or re.fullmatch(r"snapshot-[0-9a-f]{64}", sid) is None
            or sid <= previous
            or any(
                not isinstance(entry[key], str) or not _SHA.fullmatch(entry[key])
                for key in ("snapshot_sha256", "capture_sha256", "observations_sha256")
            )
            or entry["capture_sha256"] in captures
        ):
            fail("EVIDENCE_MIGRATION", "$", "Invalid or duplicate migration membership.")
        previous = sid
        captures.add(entry["capture_sha256"])


def _read_image(path: Path, limits: HistoryLimits = HISTORY_LIMITS) -> _HistoryImage:
    """Validate bounded inventory and content IDs; lifecycle validates semantic joins.

    This API does not confer analytical meaning on an attachment merely because
    its generic content hash matches. Use lifecycle verification before trust.
    """
    members = _members(path, len(_KINDS) + 2)
    names = {member.name for member in members}
    if "workspace.json" not in names or any(name.startswith(".pending-") for name in names):
        fail("EVIDENCE_INTERRUPTED", "$", "Uncommitted workspace requires manual inspection.")
    if names != {"workspace.json", *_KINDS}:
        fail("EVIDENCE_WORKSPACE", "$", "Unexpected workspace-v2 root members.")
    inventories = {"": tuple(member.name for member in members)}
    manifest_bytes = _read_bytes(path / "workspace.json", limits)
    manifest = _decode(manifest_bytes, _evidence_limits(limits))
    _manifest(manifest, limits)
    state: HistoryState = {"manifest": manifest}
    files = {"workspace.json": (len(manifest_bytes), hashlib.sha256(manifest_bytes).hexdigest())}
    byte_hashes: dict[str, str] = {}
    total_bytes = len(manifest_bytes)
    captures: set[str] = set()
    for kind, singular in _KINDS.items():
        objects: dict[str, dict[str, Any]] = {}
        state[kind] = objects
        entries = _members(path / kind, getattr(limits, kind))
        inventories[kind] = tuple(entry.name for entry in entries)
        check_limit("history_" + kind, len(entries), getattr(limits, kind))
        for entry in entries:
            if entry.name.startswith(".pending-"):
                fail("EVIDENCE_INTERRUPTED", "$", "Uncommitted object requires manual inspection.")
            if re.fullmatch(singular + r"-[0-9a-f]{64}\.json", entry.name) is None:
                fail("EVIDENCE_WORKSPACE", "$", "Unexpected historical object filename.")
            raw = _read_bytes(entry, limits)
            files[kind + "/" + entry.name] = (len(raw), hashlib.sha256(raw).hexdigest())
            total_bytes += len(raw)
            check_limit("history_workspace_bytes", total_bytes, limits.workspace_bytes)
            value = _decode(raw, _evidence_limits(limits))
            _object(kind, value, limits)
            identity = _id(kind, value)
            if entry.stem != identity:
                fail("EVIDENCE_WORKSPACE", "$", "Historical object filename mismatch.")
            if kind == "snapshots":
                if value["capture_sha256"] in captures:
                    fail("EVIDENCE_WORKSPACE", "$", "Duplicate physical collection identity.")
                captures.add(value["capture_sha256"])
                byte_hashes[identity] = files[kind + "/" + entry.name][1]
            elif raw != serialize(value):
                fail(
                    "EVIDENCE_INTEGRITY",
                    "$",
                    "New historical objects require canonical storage bytes.",
                )
            objects[identity] = value
    check_limit("history_workspace_bytes", total_bytes, limits.workspace_bytes)
    provenance = manifest["migration"]
    if provenance is not None:
        check_limit("history_migration_members", len(provenance["snapshots"]), limits.snapshots)
        for entry in provenance["snapshots"]:
            snapshot = state["snapshots"].get(entry["snapshot_id"])
            if (
                snapshot is None
                or byte_hashes[entry["snapshot_id"]] != entry["snapshot_sha256"]
                or any(
                    snapshot[key] != entry[key] for key in ("capture_sha256", "observations_sha256")
                )
            ):
                fail("EVIDENCE_MIGRATION", "$", "Preserved migration member is missing or changed.")
    return _HistoryImage(path.absolute(), limits, state, inventories, files, total_bytes)


def read_history(path: Path, limits: HistoryLimits = HISTORY_LIMITS) -> HistoryState:
    """Acquire and validate a fresh complete inventory for each public operation.

    Content identity is not analytical authority; lifecycle checks the complete
    semantic graph before using this state. No image survives this public read.
    """
    return _read_image(path, limits).state


def _check_image(workspace: Path, image: _HistoryImage) -> None:
    """Reacquire exact bytes before publication; metadata alone never grants reuse."""
    if workspace.absolute() != image.path:
        fail("EVIDENCE_PATH", "$", "A historical acquisition belongs to one workspace.")
    for folder, previous in image.inventories.items():
        maximum = len(_KINDS) + 2 if not folder else getattr(image.limits, folder)
        current = tuple(member.name for member in _members(workspace / folder, maximum))
        if current != previous:
            fail("EVIDENCE_CHANGED", "$", "Workspace inventory changed before publication.")
    total_bytes = 0
    for name, (size, sha256) in image.files.items():
        raw = _read_bytes(workspace / name, image.limits)
        total_bytes += len(raw)
        check_limit("history_workspace_bytes", total_bytes, image.limits.workspace_bytes)
        if len(raw) != size or hashlib.sha256(raw).hexdigest() != sha256:
            fail("EVIDENCE_CHANGED", "$", "Workspace content changed before publication.")


def _reserve(path: Path) -> None:
    _local(path)
    try:
        path.mkdir()
        for kind in _KINDS:
            (path / kind).mkdir()
    except FileExistsError:
        fail("EVIDENCE_EXISTS", "$", "Historical workspace destination must be new.")
    except OSError:
        fail(
            "EVIDENCE_WRITE",
            "$",
            "Cannot reserve the historical workspace; inspect partial destination.",
        )


def initialize_history(path: Path, limits: HistoryLimits = HISTORY_LIMITS) -> dict[str, Any]:
    manifest = {**_VERSIONS, "migration": None}
    raw = serialize(manifest)
    _decode(raw, _evidence_limits(limits))
    check_limit("history_workspace_bytes", len(raw), limits.workspace_bytes)
    _reserve(path)
    _publish(path / "workspace.json", raw)
    return {"status": "INITIALIZED", "workspace_version": 2}


def _migration_source(source: Path, limits: HistoryLimits) -> tuple[bytes, dict[str, bytes]]:
    members = _members(source, 3)
    if {member.name for member in members} != {"workspace.json", "snapshots"}:
        fail("EVIDENCE_MIGRATION", "$", "Source v1 workspace has unexpected root members.")
    manifest = _read_bytes(source / "workspace.json", limits)
    decoded = _decode(manifest, _evidence_limits(limits))
    if serialize(decoded) != serialize({"workspace_version": 1, "snapshot_version": 1}):
        fail("EVIDENCE_WORKSPACE", "$", "Migration requires a valid workspace-v1 manifest.")
    result: dict[str, bytes] = {}
    captures: set[str] = set()
    total_bytes = len(manifest)
    entries = _members(source / "snapshots", limits.snapshots)
    check_limit("history_snapshots", len(entries), limits.snapshots)
    for entry in entries:
        if re.fullmatch(r"snapshot-[0-9a-f]{64}\.json", entry.name) is None:
            fail("EVIDENCE_MIGRATION", "$", "Unexpected or interrupted source snapshot entry.")
        raw = _read_bytes(entry, limits)
        total_bytes += len(raw)
        check_limit("history_workspace_bytes", total_bytes, limits.workspace_bytes)
        snapshot = _decode(raw, _evidence_limits(limits))
        validate_snapshot(snapshot, _evidence_limits(limits))
        if entry.stem != snapshot["snapshot_id"] or snapshot["capture_sha256"] in captures:
            fail(
                "EVIDENCE_WORKSPACE",
                "$",
                "Source snapshot identity or physical uniqueness mismatch.",
            )
        captures.add(snapshot["capture_sha256"])
        result[entry.name] = raw
    return manifest, result


def migrate_workspace(
    source: Path, destination: Path, limits: HistoryLimits = HISTORY_LIMITS
) -> dict[str, Any]:
    """Copy a completely validated v1 workspace without altering any source byte.

    A failed destination is not reusable. Inspect and rename it out of the way
    before retrying to a fresh name. No automatic deletion or repair is attempted.
    """
    _local(source)
    _local(destination)
    # Reject equal/nested paths even when the eventual destination does not exist.
    src, dst = source.absolute(), destination.absolute()
    if src == dst or src in dst.parents or dst in src.parents:
        fail("EVIDENCE_PATH", "$", "Migration source and destination must be separate trees.")
    if destination.exists():
        fail("EVIDENCE_EXISTS", "$", "Migration destination must be new.")
    source_manifest, files = _migration_source(source, limits)
    provenance = []
    for raw in files.values():
        snapshot = _decode(raw, _evidence_limits(limits))
        provenance.append(
            {
                "snapshot_id": snapshot["snapshot_id"],
                "snapshot_sha256": hashlib.sha256(raw).hexdigest(),
                "capture_sha256": snapshot["capture_sha256"],
                "observations_sha256": snapshot["observations_sha256"],
            }
        )
    manifest = {
        **_VERSIONS,
        "migration": {
            "source_workspace_version": 1,
            "source_manifest_sha256": hashlib.sha256(source_manifest).hexdigest(),
            "snapshots": provenance,
        },
    }
    manifest_bytes = serialize(manifest)
    _decode(manifest_bytes, _evidence_limits(limits))
    planned = len(manifest_bytes) + sum(map(len, files.values()))
    check_limit("history_workspace_bytes", planned, limits.workspace_bytes)
    _reserve(destination)
    marker = destination / ".pending-migration.json"
    _publish(marker, serialize({"status": "UNCOMMITTED_MIGRATION"}))
    for name, raw in files.items():
        _publish(destination / "snapshots" / name, raw)
    # Re-open every source file and compare exact bytes, not merely self-reported IDs.
    if _migration_source(source, limits) != (source_manifest, files):
        fail("EVIDENCE_CHANGED", "$", "Source workspace changed during migration.")
    for name, raw in files.items():
        if _read_bytes(destination / "snapshots" / name, limits) != raw:
            fail("EVIDENCE_CHANGED", "$", "Destination snapshot changed before publication.")
    try:
        marker.unlink()
    except OSError:
        fail("EVIDENCE_WRITE", "$", "Cannot finish migration; destination remains uncommitted.")
    _publish(destination / "workspace.json", manifest_bytes)
    read_history(destination, limits)
    return {
        "status": "MIGRATED_METADATA",
        "workspace_version": 2,
        "physical_collections": len(files),
        "snapshots": len(files),
        "source_unchanged": True,
        "migration": manifest["migration"],
        "limitations": [
            "Original capture bytes were not reopened; source authenticity is unverified.",
            "Preserved labels are not approval records.",
        ],
    }


def _prepare_object(
    kind: str,
    value: dict[str, Any],
    limits: HistoryLimits,
) -> tuple[bytes, dict[str, Any], str]:
    if kind not in _KINDS:
        fail("EVIDENCE_OBJECT", "$", "Unsupported historical object kind.")
    # Roundtrip prevents alias mutation and bounds direct Python API inputs.
    try:
        raw = serialize(value)
        value = _decode(raw, _evidence_limits(limits))
    except (ValueError, TypeError, RecursionError):
        fail("EVIDENCE_OBJECT", "$", "Invalid historical object values.")
    check_limit("history_object_bytes", len(raw), limits.object_bytes)
    _object(kind, value, limits)
    identity = _id(kind, value)
    return raw, value, identity


def _publish_prepared(
    workspace: Path,
    kind: str,
    prepared: tuple[bytes, dict[str, Any], str],
    image: _HistoryImage,
    validate: StateValidator | None,
) -> dict[str, Any]:
    raw, value, identity = prepared
    if workspace.absolute() != image.path:
        fail("EVIDENCE_PATH", "$", "A historical acquisition belongs to one workspace.")
    limits = image.limits
    state = image.state
    existing = state[kind].get(identity)
    if existing is not None:
        if serialize(existing) != raw:
            fail("EVIDENCE_EXISTS", "$", "Existing evidence cannot be overwritten.")
        if validate is not None:
            validate(state)
        # An idempotent no-op is a validated read, not a publication boundary.
        # Like public inspection it uses this operation's freshly acquired bytes.
        return {"status": "ALREADY_PRESENT", "object_id": identity}
    if kind == "snapshots" and any(
        old["capture_sha256"] == value["capture_sha256"] for old in state[kind].values()
    ):
        fail(
            "EVIDENCE_DUPLICATE_CAPTURE",
            "$",
            "Physical collection already exists; create a revision.",
        )
    check_limit("history_" + kind, len(state[kind]) + 1, getattr(limits, kind))
    state = {**state, kind: {**state[kind], identity: value}}
    if validate is not None:
        validate(state)
    check_limit("history_workspace_bytes", image.total_bytes + len(raw), limits.workspace_bytes)
    # Keep a second physical acquisition at the write boundary. Reuse avoids
    # re-decoding/re-validating unchanged objects, never checking only size/mtime.
    _check_image(workspace, image)
    _publish(workspace / kind / (identity + ".json"), raw)
    return {"status": "ADDED", "object_id": identity}


def _publish_from_image(
    workspace: Path,
    kind: str,
    value: dict[str, Any],
    image: _HistoryImage,
    validate: StateValidator | None = None,
) -> dict[str, Any]:
    """Append within one private lifecycle operation using its original acquisition."""
    return _publish_prepared(
        workspace, kind, _prepare_object(kind, value, image.limits), image, validate
    )


def publish_object(
    workspace: Path,
    kind: str,
    value: dict[str, Any],
    validate: StateValidator | None = None,
    limits: HistoryLimits = HISTORY_LIMITS,
) -> dict[str, Any]:
    """Validate a fresh prospective complete state and append one canonical object."""
    # Preserve invalid-object diagnostics before inspecting the workspace.
    prepared = _prepare_object(kind, value, limits)
    return _publish_prepared(workspace, kind, prepared, _read_image(workspace, limits), validate)


def add_collection(
    workspace: Path,
    observations_path: Path,
    label: str = "",
    validate: StateValidator | None = None,
    limits: HistoryLimits = HISTORY_LIMITS,
) -> dict[str, Any]:
    snapshot = build_snapshot(
        read_document(observations_path, limits), label, _evidence_limits(limits)
    )
    image = _read_image(workspace, limits)
    state = image.state
    for previous in state["snapshots"].values():
        if previous["capture_sha256"] == snapshot["capture_sha256"]:
            return {
                "status": "DUPLICATE_CAPTURE",
                "existing": previous["snapshot_id"],
                "observations_match": previous["observations_sha256"]
                == snapshot["observations_sha256"],
                "label_match": previous["label"] == label,
            }
    result = _publish_from_image(workspace, "snapshots", snapshot, image, validate)
    return {**result, "snapshot_id": snapshot["snapshot_id"]}


def verify_history(
    workspace: Path, validate: StateValidator | None = None, limits: HistoryLimits = HISTORY_LIMITS
) -> dict[str, Any]:
    state = read_history(workspace, limits)
    if validate is not None:
        validate(state)
    return {
        "status": "VERIFIED_OBJECT_INTEGRITY",
        "workspace_version": 2,
        "physical_collections": len(state["snapshots"]),
        **{kind: len(state[kind]) for kind in _KINDS},
        "limitations": [
            "Content hashes establish integrity; source and reviewer authenticity are unverified.",
            "Original capture bytes were not reopened.",
            "Generic storage requires lifecycle semantic verification before analytical use.",
        ],
    }
