"""Post-creation review ZIP verification, including actual bytecode path metadata."""

import io
import json
import marshal
import stat
import zipfile
from pathlib import Path

import pytest

from otarchguard.diagnostics import ModelError
from tools.review_bundle import _safe_member, audit_review, create_review

SELECTED = frozenset({"src/otarchguard/ingestion/numbers.py"})


def selected_source(tmp_path: Path) -> Path:
    root = tmp_path / "source"
    file = root / next(iter(SELECTED))
    file.parent.mkdir(parents=True)
    file.write_text("value = 1\n", encoding="utf-8")
    return root


def test_review_excludes_real_bytecode_and_its_build_path(tmp_path: Path) -> None:
    root = selected_source(tmp_path)
    cache = root / "src/otarchguard/ingestion/__pycache__"
    cache.mkdir()
    encoded = marshal.dumps(compile("value = 1", str(root / "origin.py"), "exec"))
    assert str(root).encode() in encoded
    (cache / "numbers.cpython-312.pyc").write_bytes(encoded)
    (root / ".venv").mkdir()
    (root / ".venv/secret.pyo").write_bytes(encoded)
    output = tmp_path / "review.zip"
    first = create_review(output, root, SELECTED)
    assert first["bytecode_members"] == first["personal_paths"] == 0
    assert audit_review(output, root, SELECTED) == first
    with zipfile.ZipFile(output) as archive:
        assert set(archive.namelist()) == set(SELECTED) | {"review-manifest.json"}
        assert all(str(root).encode() not in archive.read(p) for p in archive.namelist())
        manifest = json.loads(archive.read("review-manifest.json"))
        assert set(manifest["files"]) == set(SELECTED)
    second = tmp_path / "again.zip"
    create_review(second, root, SELECTED)
    assert output.read_bytes() == second.read_bytes()
    before = output.read_bytes()
    with pytest.raises(ModelError):
        create_review(output, root, SELECTED)
    assert output.read_bytes() == before


@pytest.mark.parametrize(
    "name",
    [
        "../private.py",
        "/private.py",
        "c:/private.py",
        "src\\private.py",
        "src/__pycache__/x.py",
        ".venv/x.py",
        ".env/key.py",
        "output/evidence.py",
        "build/x.py",
        "dist/x.py",
        "private/x.py",
        "x.pyc",
        "x.pyo",
        "src/./x.py",
        "src//x.py",
    ],
)
def test_unsafe_review_archive_names_are_refused(name: str) -> None:
    with pytest.raises(ValueError):
        _safe_member(name)


@pytest.mark.parametrize("kind", ["pyc", "source_mutation", "special_file", "bad_manifest"])
def test_actual_output_is_reopened_and_tampering_detected(tmp_path: Path, kind: str) -> None:
    root = selected_source(tmp_path)
    output = tmp_path / "review.zip"
    create_review(output, root, SELECTED)
    with zipfile.ZipFile(output) as archive:
        files = {p: archive.read(p) for p in archive.namelist()}
    if kind == "pyc":
        files["cache.pyc"] = b"bytecode"
    if kind == "source_mutation":
        files[next(iter(SELECTED))] = b"tampered = True\n"
    if kind == "bad_manifest":
        files["review-manifest.json"] = b"{}"
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        for name, data in files.items():
            info = zipfile.ZipInfo(name)
            info.create_system = 3
            info.external_attr = (
                (stat.S_IFLNK if kind == "special_file" else stat.S_IFREG) | 0o644
            ) << 16
            archive.writestr(info, data)
    output.write_bytes(stream.getvalue())
    with pytest.raises(ValueError):
        audit_review(output, root, SELECTED)


@pytest.mark.parametrize("escaped", [False, True])
def test_review_rejects_personal_paths_in_selected_content(tmp_path: Path, escaped: bool) -> None:
    root = selected_source(tmp_path)
    value = str(Path.home())
    (root / next(iter(SELECTED))).write_text(
        json.dumps(value) if escaped else value, encoding="utf-8"
    )
    with pytest.raises(ValueError):
        create_review(tmp_path / "review.zip", root, SELECTED)
    assert not (tmp_path / "review.zip").exists()


def test_review_selection_must_be_approved(tmp_path: Path) -> None:
    root = selected_source(tmp_path)
    with pytest.raises(ValueError):
        create_review(tmp_path / "review.zip", root, frozenset({"secret.py"}))
