"""Independent mutations of exact V15 source authorization and installed identity."""

import importlib.metadata as metadata
import importlib.util
import shutil
import sys
import types
from pathlib import Path
from typing import Any

import pytest

import otarchguard
from tools import verify_v15_transition as policy


@pytest.fixture(scope="module")
def predecessor() -> dict[str, bytes]:
    assert policy.PREDECESSOR == "b3adcc9de21dfff6ad58946028a241844ff88294"
    assert policy.REVIEWED == "867516be2c274a12d251c89bc0310a441b91da45"
    return policy.reference()


@pytest.fixture(scope="module")
def candidate(tmp_path_factory: pytest.TempPathFactory, predecessor: dict[str, bytes]) -> Path:
    root = tmp_path_factory.mktemp("reviewed-v15")
    for name in [*predecessor, "pyproject.toml"]:
        source = policy.ROOT / name
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    policy.check_source(root, predecessor)
    return root


def test_positive_policy_binds_exact_97_modules_and_installed_runtime(
    predecessor: dict[str, bytes],
) -> None:
    receipt = policy.check_source(policy.ROOT, predecessor)
    assert len(receipt["changed"]) == 4
    assert len(receipt["unchanged"]) == 93
    assert receipt["additions"] == receipt["removals"] == []
    assert policy.check_installation(policy.expected_modules(predecessor))["distribution"] == (
        "1.5.0.dev1"
    )


@pytest.mark.parametrize(
    "name",
    [
        "src/otarchguard/api.py",
        "src/otarchguard/contract.py",
        "src/otarchguard/__init__.py",
        "src/otarchguard/reporting.py",
        "src/otarchguard/drift/explorer_render.py",
        "src/otarchguard/drift/explorer_bundle.py",
        "tests/test_reachability_oracle.py",
        "docs/yaml-schema-v1.md",
        "tools/verify_legacy_candidate.py",
        "tools/capture_contract.py",
        "tests/fixtures/capture-contract-v2/supported/observations.json",
        "tests/fixtures/capture-contract-v2/manifest.json",
        "pyproject.toml",
    ],
)
def test_rejects_unauthorized_bytes_even_inside_reviewed_change_surface(
    candidate: Path,
    predecessor: dict[str, bytes],
    tmp_path: Path,
    name: str,
) -> None:
    shutil.copytree(candidate, tmp_path / "candidate")
    root = tmp_path / "candidate"
    target = root / name
    target.write_bytes(target.read_bytes() + b"\n ")
    with pytest.raises(ValueError):
        policy.check_source(root, predecessor)


@pytest.mark.parametrize("mutation", ["missing", "extra", "resource", "rehashed-fixture"])
def test_complete_inventory_and_independent_fixture_oracle(
    candidate: Path,
    predecessor: dict[str, bytes],
    tmp_path: Path,
    mutation: str,
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


@pytest.mark.parametrize(
    "field,value",
    [
        ("DISTRIBUTION_VERSION", "1.4.0"),
        ("NATIVE_ENGINE_VERSION", "1.5.0.dev1"),
        ("__version__", "1.5.0.dev1"),
        ("__file__", str(policy.ROOT / "src/otarchguard/__init__.py")),
    ],
)
def test_rejects_incorrect_installed_identity(
    predecessor: dict[str, bytes],
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: str,
) -> None:
    monkeypatch.setattr(otarchguard, field, value)
    with pytest.raises(ValueError, match="Installed candidate"):
        policy.check_installation(policy.expected_modules(predecessor))


def test_rejects_installed_payload_different_from_reviewed_source(
    predecessor: dict[str, bytes],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = policy.expected_modules(predecessor)
    monkeypatch.setattr(policy, "module_hashes", lambda _: {**expected, "api.py": "0" * 64})
    with pytest.raises(ValueError, match="Installed candidate"):
        policy.check_installation(expected)


@pytest.mark.parametrize("field", ["RENDERER_VERSION", "_renderer_identity"])
def test_rejects_unreviewed_installed_renderer(
    predecessor: dict[str, bytes],
    monkeypatch: pytest.MonkeyPatch,
    field: str,
) -> None:
    from otarchguard.drift import explorer

    monkeypatch.setattr(
        explorer, field, "unknown" if field == "RENDERER_VERSION" else lambda: "0" * 64
    )
    with pytest.raises(ValueError, match="Installed candidate"):
        policy.check_installation(policy.expected_modules(predecessor))


def test_rejects_forged_distribution_metadata(
    predecessor: dict[str, bytes],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real = metadata.distribution("otarchguard")

    class Forged:
        version = "1.4.0"

        def __getattr__(self, name: str) -> Any:
            return getattr(real, name)

    monkeypatch.setattr(metadata, "distribution", lambda _: Forged())
    with pytest.raises(ValueError, match="Installed candidate"):
        policy.check_installation(policy.expected_modules(predecessor))


def test_reference_bootstrap_does_not_trust_mutable_oracle_imports(
    predecessor: dict[str, bytes],
    candidate: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Regression for the independent auditor's demonstrated parser bypass.
    # A forged legacy helper offers a self-consistent unauthorized api.py.
    forged = dict(predecessor)
    forged["src/otarchguard/api.py"] += b"\n# unauthorized\n"
    helper = types.ModuleType("tools.verify_legacy_candidate")
    helper_api: Any = helper
    helper_api._archive_files = lambda _: forged
    helper_api._module_hashes = policy._module_hashes
    monkeypatch.setitem(sys.modules, "tools.verify_legacy_candidate", helper)
    spec = importlib.util.spec_from_file_location("independent_v15_policy", policy.__file__)
    assert spec and spec.loader
    isolated = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(isolated)
    actual = isolated.reference()
    assert actual == predecessor
    root = tmp_path / "forged-candidate"
    shutil.copytree(candidate, root)
    (root / "src/otarchguard/api.py").write_bytes(forged["src/otarchguard/api.py"])
    with pytest.raises(ValueError, match="exact reviewed"):
        isolated.check_source(root, actual)
