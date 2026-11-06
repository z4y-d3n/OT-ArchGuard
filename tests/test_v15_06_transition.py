"""Adversarial authorization tests; immutable predecessor expectations stay unchanged."""

import hashlib
import importlib.metadata as metadata
import json
import os
import py_compile
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

import otarchguard
from tools import verify_v15_06_transition as policy


@pytest.fixture(scope="module")
def predecessor() -> dict[str, bytes]:
    assert policy.PREDECESSOR == "7c5d6cb5c0efd6ee5946943bf8b83e12e98a9057"
    assert policy.TREE == "e2c40a52a3f5d9370d2053474d9f2aab1d1463b4"
    return policy.reference()


@pytest.fixture(scope="module")
def candidate(tmp_path_factory: pytest.TempPathFactory, predecessor: dict[str, bytes]) -> Path:
    root = tmp_path_factory.mktemp("v15-06-reviewed")
    for name in predecessor:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(policy.ROOT / name, path)
    policy.check_source(root, predecessor)
    return root


def test_exact_version_only_module_and_unchanged_historical_renderer(
    predecessor: dict[str, bytes],
) -> None:
    result = policy.check_source(policy.ROOT, predecessor)
    assert set(result["changed"]) == {"__init__.py"}
    assert len(result["unchanged"]) == 96
    installed = policy.check_installation(predecessor)
    assert installed["distribution"] == "1.5.0"
    assert installed["native_engine"] == "1.3.0"
    assert installed["renderer"] == "1.5.0.dev1-historical-explorer.1"
    assert installed["renderer_sha256"] == (
        "442d13378cd61586664e19f51ea6834537b0155c07e48ff5a6173628c5d6ca6b"
    )


@pytest.mark.parametrize(
    "mutation", [None, "allowed-helper", "protected-module", "init", "missing", "extra", "artifact"]
)
def test_native_manifest_delta_requires_exact_authorized_source_and_output(
    predecessor: dict[str, bytes], tmp_path: Path, mutation: str | None
) -> None:
    original = {
        n.removeprefix("src/otarchguard/"): hashlib.sha256(data).hexdigest()
        for n, data in predecessor.items()
        if n.startswith("src/otarchguard/") and n.endswith(".py")
    }
    for name, modules in (("before", original), ("after", policy.expected_modules(predecessor))):
        directory = tmp_path / name
        directory.mkdir()
        raw = b'{"engine_version": "1.3.0", "value": 1}\n'
        if name == "after" and mutation == "artifact":
            raw = raw.replace(b'"value": 1', b'"value": 2')
        (directory / "result.json").write_bytes(raw)
        manifest: dict[str, Any] = {
            "python": "fictional-test",
            "platform": "fictional-test",
            "production_sha256": {n: h for n, h in modules.items() if "/" not in n},
            "inputs": {"input.yaml": "0" * 64},
            "exits": {"validate": 0},
            "artifacts": {"result.json": hashlib.sha256(raw).hexdigest()},
        }
        if name == "after" and mutation in {"allowed-helper", "protected-module"}:
            module = "explorer_data.py" if mutation == "allowed-helper" else "reachability.py"
            manifest["production_sha256"][module] = "f" * 64
        elif name == "after" and mutation == "init":
            manifest["production_sha256"]["__init__.py"] = "f" * 64
        elif name == "after" and mutation == "missing":
            del manifest["production_sha256"]["explorer_data.py"]
        elif name == "after" and mutation == "extra":
            manifest["production_sha256"]["unexpected.py"] = "f" * 64
        (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    if mutation is not None:
        with pytest.raises(ValueError):
            policy.compare_native(predecessor, tmp_path / "before", tmp_path / "after")
    else:
        result = policy.compare_native(predecessor, tmp_path / "before", tmp_path / "after")
        assert result["allowed_module_changes"] == []
        assert result["artifacts"]["result.json"] == "EXACT_BYTES"


@pytest.mark.parametrize(
    "name",
    [
        ".github/workflows/ci.yml",
        "src/otarchguard/api.py",
        "src/otarchguard/__init__.py",
        "src/otarchguard/explorer_data.py",
        "src/otarchguard/capture/explorer.py",
        "src/otarchguard/drift/explorer_render.py",
        "src/otarchguard/evidence/revisions.py",
        "tools/verify_v15_transition.py",
        "tools/verify_v15_03_transition.py",
        "tools/verify_v15_04_transition.py",
        "tests/test_v15_04_transition.py",
        "tools/compare_versioned_contract.py",
        "tests/test_v15_transition.py",
        "tests/test_v15_03_transition.py",
        "tests/test_capture_ux_integrity.py",
        "tests/test_reachability_oracle.py",
        "tests/fixtures/capture-contract-v2/supported/observations.json",
        "tests/fixtures/capture-contract-v2/manifest.json",
        "docs/yaml-schema-v1.md",
        "pyproject.toml",
    ],
)
def test_unauthorized_bytes_fail_closed(
    candidate: Path, predecessor: dict[str, bytes], tmp_path: Path, name: str
) -> None:
    root = tmp_path / "candidate"
    shutil.copytree(candidate, root)
    target = root / name
    target.write_bytes(target.read_bytes() + b"\n# unauthorized\n")
    with pytest.raises(ValueError):
        policy.check_source(root, predecessor)


@pytest.mark.parametrize("mutation", ["missing", "extra", "resource", "rehashed-fixture"])
def test_inventory_and_forged_self_consistent_fixture(
    candidate: Path, predecessor: dict[str, bytes], tmp_path: Path, mutation: str
) -> None:
    root = tmp_path / "candidate"
    shutil.copytree(candidate, root)
    if mutation == "missing":
        (root / "src/otarchguard/api.py").unlink()
    elif mutation in {"extra", "resource"}:
        (
            root / "src/otarchguard" / ("extra.py" if mutation == "extra" else "extra.json")
        ).write_text("{}")
    else:
        (root / "tests/fixtures/capture-contract-v2/supported/observations.json").write_text("{}")
        (root / "tests/fixtures/capture-contract-v2/manifest.json").write_text("{}")
    with pytest.raises(ValueError):
        policy.check_source(root, predecessor)


def test_forged_installed_metadata_rejected(
    predecessor: dict[str, bytes], monkeypatch: pytest.MonkeyPatch
) -> None:
    real = metadata.distribution("otarchguard")

    class Forged:
        version = "1.5.0.dev3"

        def __getattr__(self, name: str) -> Any:
            return getattr(real, name)

    monkeypatch.setattr(metadata, "distribution", lambda _: Forged())
    with pytest.raises(ValueError, match="Installed candidate differs|Invalid installed metadata"):
        policy.check_installation(predecessor)


@pytest.mark.parametrize("isolated", [False, True])
def test_cli_rejects_shadowing_and_unauthorized_source(
    candidate: Path, tmp_path: Path, isolated: bool
) -> None:
    root = tmp_path / "candidate"
    shutil.copytree(candidate, root)
    script = root / "tools/verify_v15_06_transition.py"
    shutil.copyfile(Path(policy.__file__), script)
    source = root / "src/otarchguard/api.py"
    source.write_bytes(source.read_bytes() + b"\n# unauthorized\n")
    (root / "hashlib.py").write_text("raise SystemExit('SHADOW_EXECUTED')")
    result = subprocess.run(
        [
            sys.executable,
            *(["-I"] if isolated else []),
            str(script),
            "--source-only",
            "--output",
            str(tmp_path / "receipt.json"),
        ],
        cwd=root,
        env={
            **os.environ,
            "GIT_DIR": policy.git_output("rev-parse", "--absolute-git-dir").decode().strip(),
        },
        capture_output=True,
        timeout=60,
    )
    assert result.returncode != 0 and b"SHADOW_EXECUTED" not in result.stderr
    assert (b"exact reviewed V15-06" if isolated else b"Use python -I") in result.stderr


@pytest.mark.parametrize("malicious_source", [True, False])
def test_preimport_bytes_and_fresh_bytecode_boundary(
    tmp_path: Path, malicious_source: bool
) -> None:
    site = tmp_path / "site-packages"
    package = site / "otarchguard"
    shutil.copytree(
        Path(otarchguard.__file__).parent, package, ignore=shutil.ignore_patterns("__pycache__")
    )
    marker = tmp_path / "untrusted-executed"
    payload = f"\nopen({str(marker)!r}, 'w').write('executed')\n".encode()
    init = package / "__init__.py"
    if malicious_source:
        init.write_bytes(init.read_bytes() + payload)
    else:
        evil = tmp_path / "evil.py"
        evil.write_bytes(payload)
        cache = package / "__pycache__" / f"__init__.{sys.implementation.cache_tag}.pyc"
        cache.parent.mkdir()
        py_compile.compile(
            str(evil),
            cfile=str(cache),
            invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH,
        )
    info = site / "otarchguard-1.5.0.dist-info"
    original_info = Path(
        str(metadata.distribution("otarchguard").locate_file("otarchguard-1.5.0.dist-info"))
    )
    shutil.copytree(original_info, info)
    receipt = tmp_path / "receipt.json"
    script = (
        f"import runpy,sys;sys.path.insert(0,{str(site)!r});"
        f"sys.argv=[{policy.__file__!r},'--source-only','--output',{str(receipt)!r}];"
        f"runpy.run_path({policy.__file__!r},run_name='__main__')"
    )
    result = subprocess.run([sys.executable, "-I", "-c", script], capture_output=True, timeout=60)
    assert not marker.exists(), "Untrusted installed source or cache executed"
    if malicious_source:
        assert result.returncode != 0 and b"Installed candidate differs" in result.stderr
    else:
        assert result.returncode == 0, result.stderr
        assert json.loads(receipt.read_bytes())["installed"]["distribution"] == "1.5.0"


@pytest.mark.parametrize("mutation", ["duplicate_version", "name", "entry", "requirements", "json"])
def test_forged_regular_installed_metadata_fails_before_import(
    tmp_path: Path, mutation: str
) -> None:
    site = tmp_path / "site-packages"
    site.mkdir()
    info = site / "otarchguard-1.5.0.dist-info"
    original = Path(str(metadata.distribution("otarchguard").locate_file(info.name)))
    shutil.copytree(original, info)
    package = site / "otarchguard"
    shutil.copytree(Path(otarchguard.__file__).parent, package)
    if mutation == "entry":
        (info / "entry_points.txt").write_text("[console_scripts]\notarchguard = evil:app\n")
    elif mutation == "json":
        (info / "direct_url.json").write_text("{broken")
    else:
        path = info / "METADATA"
        raw = path.read_text(encoding="utf-8")
        if mutation == "duplicate_version":
            raw = raw.replace("Version: 1.5.0\n", "Version: 1.5.0\nVersion: 1.5.0\n")
        elif mutation == "name":
            raw = raw.replace("Name: otarchguard\n", "Name: forged\n")
        else:
            raw = raw.replace("Requires-Dist: PyYAML<7,>=6\n", "")
        path.write_text(raw, encoding="utf-8")
    receipt = tmp_path / "receipt.json"
    script = (
        f"import runpy,sys;sys.path.insert(0,{str(site)!r});"
        f"sys.argv=[{policy.__file__!r},'--source-only','--output',{str(receipt)!r}];"
        f"runpy.run_path({policy.__file__!r},run_name='__main__')"
    )
    result = subprocess.run([sys.executable, "-I", "-c", script], capture_output=True, timeout=60)
    assert result.returncode != 0 and not receipt.exists()
