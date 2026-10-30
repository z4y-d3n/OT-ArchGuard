"""Checksum completeness and clean-source guards for owner-controlled release assembly."""

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from tools import prepare_release as release
from tools.prepare_release import _source, verify_checksums

NAMES = (
    "otarchguard-1.4.0-py3-none-any.whl",
    "otarchguard-1.4.0.tar.gz",
    "release-manifest.json",
    "SHA256SUMS.txt",
)


@pytest.mark.parametrize(
    "mutation", [None, "changed", "missing", "extra", "duplicate", "traversal", "self_hash"]
)
def test_release_checksums_cover_exactly_the_three_other_assets(
    tmp_path: Path, mutation: str | None
) -> None:
    for name in NAMES[:-1]:
        (tmp_path / name).write_bytes(name.encode())
    checksums = "".join(
        f"{hashlib.sha256(name.encode()).hexdigest()}  {name}\n" for name in NAMES[:-1]
    )
    (tmp_path / NAMES[-1]).write_bytes(checksums.encode())
    if mutation is None:
        verify_checksums(tmp_path, NAMES)
        return
    if mutation == "changed":
        (tmp_path / NAMES[0]).write_bytes(b"forged wheel")
    elif mutation == "missing":
        (tmp_path / NAMES[1]).unlink()
    elif mutation == "extra":
        (tmp_path / "unreviewed.pcap").write_bytes(b"private")
    else:
        changed = {
            "duplicate": checksums + checksums.splitlines()[0] + "\n",
            "traversal": checksums.replace(NAMES[0], "../" + NAMES[0]),
            "self_hash": checksums + "0" * 64 + "  SHA256SUMS.txt\n",
        }[mutation]
        (tmp_path / NAMES[-1]).write_bytes(changed.encode())
    with pytest.raises(ValueError):
        verify_checksums(tmp_path, NAMES)


def test_release_assembly_rejects_uncommitted_source_before_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def dirty(command: list[str], *, cwd: Path) -> bytes:
        assert command == ["git", "status", "--porcelain=v1"] and cwd == tmp_path
        return b" M src/otarchguard/api.py\n"

    monkeypatch.setattr(subprocess, "check_output", dirty)
    with pytest.raises(ValueError, match="clean committed"):
        _source(tmp_path)


@pytest.mark.parametrize("mutation", [None, "engine", "distribution", "duplicate"])
def test_assembly_does_not_mislabel_source_engine_identity(
    tmp_path: Path, mutation: str | None
) -> None:
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "1.4.0"\n')
    source = tmp_path / "src/otarchguard/__init__.py"
    source.parent.mkdir(parents=True)
    raw = 'DISTRIBUTION_VERSION = "1.4.0"\nNATIVE_ENGINE_VERSION = "1.3.0"\n'
    if mutation == "engine":
        raw = raw.replace('"1.3.0"', '"1.4.0"')
    elif mutation == "distribution":
        raw = raw.replace('"1.4.0"', '"1.4.1"')
    elif mutation == "duplicate":
        raw += 'NATIVE_ENGINE_VERSION = "1.3.0"\n'
    source.write_text(raw)
    if mutation is None:
        assert release._versions(tmp_path) == ("1.4.0", "1.3.0")
    else:
        with pytest.raises(ValueError, match="Source version literals"):
            release._versions(tmp_path)


@pytest.mark.parametrize("mutation", [None, "claim", "unknown", "boolean_version", "duplicate_key"])
def test_rehashed_manifest_cannot_invent_acceptance_or_change_types(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str | None
) -> None:
    # Isolate the manifest boundary from archive parsing; the archive oracle is
    # independently exercised with real distributions in packaging audit tests.
    source = {"tested_commit": "a" * 40, "tree": "b" * 40, "files": {}}
    audit = {"status": "passed", "version": "1.4.0"}
    monkeypatch.setattr(release, "_source", lambda root: source)
    monkeypatch.setattr(release, "_versions", lambda root: ("1.4.0", "1.3.0"))
    monkeypatch.setattr(release, "audit", lambda wheel, sdist, root: audit)
    manifest = release._manifest(source, audit, "1.4.0", "1.3.0")
    if mutation == "claim":
        manifest["acceptance"] = "Hosted CI and owner approval complete"
    elif mutation == "unknown":
        manifest["approved"] = True
    elif mutation == "boolean_version":
        manifest["manifest_version"] = True
    raw = json.dumps(manifest, sort_keys=True, indent=2) + "\n"
    if mutation == "duplicate_key":
        raw = raw.replace(
            '"manifest_version": 1,', '"manifest_version": 99, "manifest_version": 1,'
        )
    for name in NAMES[:2]:
        (tmp_path / name).write_bytes(b"Independently audited archive placeholder")
    (tmp_path / NAMES[2]).write_bytes(raw.encode())
    (tmp_path / NAMES[3]).write_bytes(
        "".join(
            f"{hashlib.sha256((tmp_path / name).read_bytes()).hexdigest()}  {name}\n"
            for name in NAMES[:-1]
        ).encode()
    )
    if mutation is None:
        release.verify_assets(tmp_path)
    else:
        with pytest.raises(ValueError, match="unreviewed fields or acceptance claims"):
            release.verify_assets(tmp_path)
