"""Adversarial tests for operation-local byte acquisitions and sized read buffers."""

import hashlib
import json
import os
import tracemalloc
from dataclasses import replace
from pathlib import Path
from typing import Any, BinaryIO, cast

import pytest

from otarchguard.diagnostics import ModelError, fail
from otarchguard.evidence import history
from otarchguard.evidence.workspace import serialize


def content(marker: str) -> dict[str, Any]:
    body: dict[str, Any] = {"attachment_version": 1, "marker": marker}
    canonical = json.dumps(
        {"domain": "otarchguard.attachment", "value": body},
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("ascii")
    return {**body, "attachment_id": "attachment-" + hashlib.sha256(canonical).hexdigest()}


def workspace(tmp_path: Path) -> Path:
    path = tmp_path / "history"
    history.initialize_history(path)
    return path


class ReadProbe:
    def __init__(self, stream: BinaryIO, requests: list[int], mutate: Any = None) -> None:
        self.stream = stream
        self.requests = requests
        self.mutate = mutate

    def __enter__(self) -> "ReadProbe":
        self.stream.__enter__()
        return self

    def __exit__(self, *args: Any) -> None:
        self.stream.__exit__(*args)

    def fileno(self) -> int:
        return self.stream.fileno()

    def read(self, size: int) -> bytes:
        self.requests.append(size)
        if self.mutate is not None:
            self.mutate()
        return self.stream.read(size)


@pytest.mark.parametrize("size", [0, 1, 127, 4096, 65536])
def test_read_request_uses_open_file_size_plus_one_not_maximum_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, size: int
) -> None:
    path = tmp_path / "bytes.json"
    path.write_bytes(b"x" * size)
    original = os.fdopen
    requests: list[int] = []

    def observed(descriptor: int, mode: str) -> ReadProbe:
        return ReadProbe(cast(BinaryIO, original(descriptor, mode)), requests)

    monkeypatch.setattr(os, "fdopen", observed)
    assert history._read_bytes(path, history.HISTORY_LIMITS) == b"x" * size
    assert requests == [size + 1]


def test_small_input_does_not_allocate_the_configured_sixty_four_megabytes(tmp_path: Path) -> None:
    path = tmp_path / "small.json"
    path.write_bytes(b'{"bounded":true}')
    tracemalloc.start()
    try:
        history._read_bytes(path, history.HISTORY_LIMITS)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert peak < 2 * 1024 * 1024


@pytest.mark.parametrize("mutation", ["grow", "shrink", "replace"])
def test_changed_file_during_size_appropriate_read_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    path = tmp_path / "bytes.json"
    path.write_bytes(b"original")
    original = os.fdopen
    requests: list[int] = []
    replacement_blocked = False

    def mutate() -> None:
        nonlocal replacement_blocked
        if mutation == "grow":
            path.write_bytes(b"original and unexpected growth")
        elif mutation == "shrink":
            path.write_bytes(b"x")
        else:
            other = tmp_path / "replacement.json"
            other.write_bytes(b"original")
            try:
                os.replace(other, path)
            except PermissionError:
                # Windows may deny replacement while this descriptor is open.
                # That also fails safely, through the controlled read diagnostic.
                replacement_blocked = True
                raise

    def observed(descriptor: int, mode: str) -> ReadProbe:
        return ReadProbe(cast(BinaryIO, original(descriptor, mode)), requests, mutate)

    monkeypatch.setattr(os, "fdopen", observed)
    with pytest.raises(ModelError) as error:
        history._read_bytes(path, history.HISTORY_LIMITS)
    assert error.value.diagnostics[0].code == (
        "EVIDENCE_READ" if replacement_blocked else "EVIDENCE_CHANGED"
    )
    if replacement_blocked:
        assert path.read_bytes() == b"original"
    assert requests == [len(b"original") + 1]


def test_size_ceiling_rejects_before_opening_and_exact_limit_is_readable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "bytes.json"
    path.write_bytes(b"123456")
    limits = replace(history.HISTORY_LIMITS, object_bytes=5)
    original = os.open
    opened: list[Path] = []

    def observed(file: Path, flags: int) -> int:
        opened.append(file)
        return original(file, flags)

    monkeypatch.setattr(os, "open", observed)
    with pytest.raises(ModelError) as error:
        history._read_bytes(path, limits)
    assert error.value.diagnostics[0].code == "LIMIT_EXCEEDED"
    assert opened == []
    path.write_bytes(b"12345")
    assert history._read_bytes(path, limits) == b"12345"
    assert opened == [path]


@pytest.mark.parametrize("raw", [b"", b'{"missing":', b'{"duplicate":1,"duplicate":2}'])
def test_empty_truncated_and_duplicate_key_json_keep_controlled_failure(
    tmp_path: Path, raw: bytes
) -> None:
    path = tmp_path / "invalid.json"
    path.write_bytes(raw)
    with pytest.raises(ModelError) as error:
        history.read_document(path)
    assert error.value.diagnostics[0].code == "EVIDENCE_JSON"


def test_image_keeps_exact_byte_receipts_and_public_state_shape(tmp_path: Path) -> None:
    path = workspace(tmp_path)
    # Whitespace in the manifest remains an allowed representation, counted exactly.
    manifest = path / "workspace.json"
    manifest.write_bytes(manifest.read_bytes() + b" \n\t")
    obj = content("first")
    history.publish_object(path, "attachments", obj)
    image = history._read_image(path)
    assert image.state == history.read_history(path)
    assert set(image.state) == {
        "manifest",
        "snapshots",
        "attachments",
        "analyses",
        "reviews",
        "baselines",
    }
    assert image.total_bytes == sum(size for size, _ in image.files.values())
    for name, (size, digest) in image.files.items():
        raw = (path / name).read_bytes()
        assert size == len(raw) and digest == hashlib.sha256(raw).hexdigest()
    assert set(image.inventories) == {
        "",
        "snapshots",
        "attachments",
        "analyses",
        "reviews",
        "baselines",
    }


def test_one_operation_publish_does_not_mutate_original_acquired_state(tmp_path: Path) -> None:
    path = workspace(tmp_path)
    image = history._read_image(path)
    obj = content("new")
    calls: list[dict[str, Any]] = []
    result = history._publish_from_image(path, "attachments", obj, image, calls.append)
    assert result == {"status": "ADDED", "object_id": obj["attachment_id"]}
    assert image.state["attachments"] == {}
    assert len(calls) == 1
    assert calls[0]["attachments"] == {obj["attachment_id"]: obj}
    assert history.read_history(path)["attachments"] == {obj["attachment_id"]: obj}


@pytest.mark.parametrize("mutation", ["bytes", "same_size_mtime", "remove", "extra", "manifest"])
def test_publication_rechecks_exact_content_and_inventory_after_callback(
    tmp_path: Path, mutation: str
) -> None:
    path = workspace(tmp_path)
    previous = content("old")
    history.publish_object(path, "attachments", previous)
    original_path = path / "attachments" / (previous["attachment_id"] + ".json")
    image = history._read_image(path)
    new = content("new")

    def mutate(_: dict[str, Any]) -> None:
        if mutation == "remove":
            original_path.unlink()
        elif mutation == "extra":
            (path / "attachments/stray.json").write_bytes(b"{}")
        elif mutation == "manifest":
            (path / "workspace.json").write_bytes(b"{}")
        else:
            info = original_path.stat()
            raw = original_path.read_bytes().replace(b'"old"', b'"bad"')
            original_path.write_bytes(raw)
            if mutation == "same_size_mtime":
                os.utime(original_path, ns=(info.st_atime_ns, info.st_mtime_ns))
                assert original_path.stat().st_size == info.st_size
                assert original_path.stat().st_mtime_ns == info.st_mtime_ns

    with pytest.raises(ModelError) as error:
        history._publish_from_image(path, "attachments", new, image, mutate)
    assert error.value.diagnostics[0].code == "EVIDENCE_CHANGED"
    assert not (path / "attachments" / (new["attachment_id"] + ".json")).exists()


def test_an_image_from_another_workspace_cannot_authorize_publication(tmp_path: Path) -> None:
    first = workspace(tmp_path)
    other = tmp_path / "other"
    history.initialize_history(other)
    image = history._read_image(first)
    with pytest.raises(ModelError) as error:
        history._publish_from_image(other, "attachments", content("new"), image)
    assert error.value.diagnostics[0].code == "EVIDENCE_PATH"
    assert history.read_history(other)["attachments"] == {}


def test_public_read_after_prior_success_revalidates_changed_bytes(tmp_path: Path) -> None:
    path = workspace(tmp_path)
    obj = content("one")
    history.publish_object(path, "attachments", obj)
    assert history.read_history(path)["attachments"][obj["attachment_id"]] == obj
    target = path / "attachments" / (obj["attachment_id"] + ".json")
    info = target.stat()
    target.write_bytes(target.read_bytes().replace(b'"one"', b'"two"'))
    os.utime(target, ns=(info.st_atime_ns, info.st_mtime_ns))
    with pytest.raises(ModelError) as error:
        history.read_history(path)
    assert error.value.diagnostics[0].code == "EVIDENCE_INTEGRITY"


def test_capacity_uses_original_raw_bytes_and_rejects_before_publish(tmp_path: Path) -> None:
    path = workspace(tmp_path)
    manifest = path / "workspace.json"
    manifest.write_bytes(manifest.read_bytes() + b" " * 4096)
    obj = content("new")
    exact = manifest.stat().st_size + len(serialize(obj))
    limits = replace(history.HISTORY_LIMITS, workspace_bytes=exact - 1)
    image = history._read_image(path, limits)
    with pytest.raises(ModelError) as error:
        history._publish_from_image(path, "attachments", obj, image)
    assert error.value.diagnostics[0].code == "LIMIT_EXCEEDED"
    assert history.read_history(path)["attachments"] == {}


def test_callback_rejection_and_publication_failure_keep_acquired_state_and_disk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = workspace(tmp_path)
    image = history._read_image(path)
    obj = content("new")

    def reject(_: dict[str, Any]) -> None:
        fail("EVIDENCE_REVIEW", "$", "Synthetic rejected prospective state")

    with pytest.raises(ModelError):
        history._publish_from_image(path, "attachments", obj, image, reject)
    assert image.state["attachments"] == {}
    assert history.read_history(path)["attachments"] == {}

    def disk_full(destination: Path, raw: bytes) -> None:
        fail("EVIDENCE_WRITE", "$", "Synthetic failure before atomic publication")

    monkeypatch.setattr(history, "_publish", disk_full)
    with pytest.raises(ModelError) as error:
        history._publish_from_image(path, "attachments", obj, image)
    assert error.value.diagnostics[0].code == "EVIDENCE_WRITE"
    assert image.state["attachments"] == {}
    assert history.read_history(path)["attachments"] == {}


def test_idempotent_publication_keeps_one_callback_and_existing_bytes(tmp_path: Path) -> None:
    path = workspace(tmp_path)
    obj = content("same")
    history.publish_object(path, "attachments", obj)
    target = path / "attachments" / (obj["attachment_id"] + ".json")
    before = target.read_bytes()
    calls: list[dict[str, Any]] = []
    result = history.publish_object(path, "attachments", obj, calls.append)
    assert result == {"status": "ALREADY_PRESENT", "object_id": obj["attachment_id"]}
    assert len(calls) == 1 and target.read_bytes() == before


@pytest.mark.parametrize("name", ["missing", "directory"])
def test_regular_file_boundary_is_preserved(tmp_path: Path, name: str) -> None:
    target = tmp_path / name
    if name == "directory":
        target.mkdir()
    with pytest.raises(ModelError) as error:
        history._read_bytes(target, history.HISTORY_LIMITS)
    assert error.value.diagnostics[0].code in {"EVIDENCE_FILE", "EVIDENCE_READ"}
