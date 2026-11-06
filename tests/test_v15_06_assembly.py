"""Stable manifest claims must match independently reopened source and assets."""

import hashlib
import json
from pathlib import Path

import pytest

from tools import prepare_v15_release as release
from tools.prepare_release import _manifest

NAMES = (
    "otarchguard-1.5.0-py3-none-any.whl",
    "otarchguard-1.5.0.tar.gz",
    "release-manifest.json",
    "SHA256SUMS.txt",
)


@pytest.mark.parametrize("mutation", [None, "claim", "unknown", "boolean_version", "duplicate_key"])
def test_rehashed_manifest_cannot_invent_acceptance_or_change_types(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str | None
) -> None:
    # Isolate the manifest boundary from archive parsing; the archive oracle is
    # independently exercised with real distributions in packaging audit tests.
    source = {"tested_commit": "a" * 40, "tree": "b" * 40, "files": {}}
    audit = {"status": "passed", "version": "1.5.0"}
    monkeypatch.setattr(release, "_authorized_source", lambda root: source)
    monkeypatch.setattr(release, "audit", lambda wheel, sdist, root: audit)
    manifest = _manifest(source, audit, "1.5.0", "1.3.0")
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
        with pytest.raises(ValueError, match="acceptance claims"):
            release.verify_assets(tmp_path)
