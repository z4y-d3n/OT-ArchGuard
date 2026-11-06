"""Stable manifest claims must match independently reopened source and assets."""

import hashlib
import json
import os
import py_compile
import shutil
import subprocess
import sys
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


def test_assembly_entry_requires_isolated_source_execution(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, release.__file__, "--help"],
        cwd=tmp_path,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode != 0 and b"Use python -I" in result.stderr


def test_backend_argv_mutation_cannot_redirect_the_sdist(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Independent tiny backend emulates setuptools' documented argv side effect.
    # Archive parsing is exercised separately with real wheel/sdist mutations.
    (tmp_path / "setuptools.py").write_text(
        "import sys\nfrom pathlib import Path\n"
        "class Backend:\n"
        " def build_wheel(self, destination):\n"
        "  Path(destination, 'otarchguard-1.5.0-py3-none-any.whl').write_bytes(b'wheel')\n"
        "  sys.argv = ['setup', 'bdist_wheel']\n"
        " def build_sdist(self, destination):\n"
        "  Path(destination, 'otarchguard-1.5.0.tar.gz').write_bytes(b'sdist')\n"
        "build_meta = Backend()\n"
    )
    source = {"tested_commit": "a" * 40, "tree": "b" * 40, "files": {}}
    monkeypatch.setattr(release, "_authorized_source", lambda root: source)
    monkeypatch.setattr(release, "audit", lambda wheel, sdist, root: {"status": "passed"})
    output = tmp_path / "assets"
    release.prepare(output, tmp_path)
    assert {p.name for p in output.iterdir()} == set(NAMES)
    assert (output / NAMES[0]).read_bytes() == b"wheel"
    assert (output / NAMES[1]).read_bytes() == b"sdist"


@pytest.mark.parametrize("unsafe_import_mutation", [False, True])
@pytest.mark.parametrize("helper", ["audit_release", "verify_v15_06_transition"])
def test_mutable_predecessor_helper_cache_never_executes(
    tmp_path: Path, unsafe_import_mutation: bool, helper: str
) -> None:
    root = Path(release.__file__).resolve().parents[1]
    candidate = tmp_path / "candidate"
    for name in (root / "tools/public-files.txt").read_text(encoding="utf-8").splitlines():
        target = candidate / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / name, target)
    if unsafe_import_mutation:
        # Negative control: reintroduce the dangerous preauthorization import.
        tool = candidate / "tools/prepare_v15_release.py"
        raw = tool.read_text(encoding="utf-8")
        tool.write_text(
            raw.replace("import argparse\n", f"import tools.{helper}\nimport argparse\n", 1)
        )
    marker = tmp_path / "untrusted-cache-executed"
    evil = tmp_path / "evil.py"
    evil.write_text(f"from pathlib import Path\nPath({str(marker)!r}).write_text('executed')\n")
    cached = candidate / "tools/__pycache__" / f"{helper}.{sys.implementation.cache_tag}.pyc"
    cached.parent.mkdir()
    py_compile.compile(
        str(evil),
        cfile=str(cached),
        invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH,
    )
    git_dir = subprocess.check_output(
        ["git", "rev-parse", "--absolute-git-dir"], cwd=root, text=True
    ).strip()
    script = (
        f"import runpy,sys;sys.path.insert(0,{str(candidate)!r});"
        "sys.argv=['prepare_v15_release','--verify','--output','missing-assets'];"
        "runpy.run_module('tools.prepare_v15_release',run_name='__main__')"
    )
    result = subprocess.run(
        [sys.executable, "-I", "-c", script],
        cwd=candidate,
        env={**os.environ, "GIT_DIR": git_dir},
        capture_output=True,
        timeout=60,
    )
    assert result.returncode != 0
    assert marker.exists() is unsafe_import_mutation


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
