"""Independent source-pinned adversarial checks for the final distribution transition."""

import hashlib
import subprocess
from pathlib import Path
from typing import Any

import pytest

from tools import verify_legacy_candidate as legacy

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def approved() -> dict[str, bytes]:
    assert legacy.BASELINE == "f52c792b683cb499dc7de765b65b5cc897a96854"
    assert legacy.PRESENTATION == "117318393ead604a023a24bad7d53eb429faa13f"
    return legacy._archive_files(
        subprocess.check_output(["git", "archive", legacy.PRESENTATION], cwd=ROOT)
    )


def test_transition_is_one_literal_in_one_of_all_97_approved_modules(
    approved: dict[str, bytes],
) -> None:
    original = legacy._module_hashes(approved)
    expected = dict(original)
    before = approved["src/otarchguard/__init__.py"]
    after = before.replace(b'"1.4.0.dev1"', b'"1.4.0"', 1)
    assert before.count(b'"1.4.0.dev1"') == 1
    assert b'NATIVE_ENGINE_VERSION = "1.3.0"' in after
    assert b"__version__ = NATIVE_ENGINE_VERSION" in after
    expected["__init__.py"] = hashlib.sha256(after).hexdigest()
    assert len(expected) == 97
    assert legacy._candidate_module_hashes(approved) == expected
    assert {n for n in expected if original[n] != expected[n]} == {"__init__.py"}


@pytest.mark.parametrize("count", [0, 2])
def test_transition_requires_one_exact_approved_literal(
    approved: dict[str, bytes], count: int
) -> None:
    name = "src/otarchguard/__init__.py"
    literal = b'DISTRIBUTION_VERSION = "1.4.0.dev1"\n'
    forged = {**approved, name: approved[name].replace(literal, literal * count)}
    with pytest.raises(ValueError, match="unexpected version literal"):
        legacy._candidate_module_hashes(forged)


@pytest.mark.parametrize("mutation", ["analysis", "html", "engine", "version", "extra", "missing"])
def test_checkout_rejects_every_change_beyond_the_pinned_distribution_literal(
    approved: dict[str, bytes], tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    expected = legacy._candidate_module_hashes(approved)
    source = tmp_path / "src/otarchguard"
    for name, data in approved.items():
        if name.startswith("src/otarchguard/") and name.endswith(".py"):
            target = tmp_path / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(
                data.replace(b'"1.4.0.dev1"', b'"1.4.0"', 1)
                if target.name == "__init__.py"
                else data
            )
    monkeypatch.setattr(legacy, "ROOT", tmp_path)
    legacy._check_candidate_source(expected)
    if mutation in {"analysis", "html"}:
        target = source / ("api.py" if mutation == "analysis" else "reporting.py")
        target.write_bytes(target.read_bytes() + b"\n# unauthorized source change\n")
    elif mutation in {"engine", "version"}:
        target = source / "__init__.py"
        target.write_bytes(
            target.read_bytes().replace(
                b'"1.3.0"' if mutation == "engine" else b'"1.4.0"', b'"1.4.1"'
            )
        )
    elif mutation == "extra":
        (source / "unreviewed.py").write_bytes(b"pass\n")
    else:
        (source / "api.py").unlink()
    with pytest.raises(ValueError, match="exact reviewed distribution transition"):
        legacy._check_candidate_source(expected)


@pytest.mark.parametrize(
    "mutation", [None, "hash", "version", "engine", "editable", "checkout", "metadata_path"]
)
def test_installed_package_is_bound_to_source_metadata_and_regular_location(
    approved: dict[str, bytes], tmp_path: Path, mutation: str | None
) -> None:
    expected = legacy._candidate_module_hashes(approved)
    installed: dict[str, Any] = {
        "version": "1.3.0",
        "distribution_version": "1.4.0",
        "hashes": expected,
        "module": str(tmp_path / "site-packages/otarchguard"),
        "distribution_module": str(tmp_path / "site-packages/otarchguard"),
        "editable": False,
    }
    if mutation is None:
        legacy._check_candidate_installation(installed, expected)
        return
    if mutation == "hash":
        installed["hashes"] = {**expected, "api.py": "0" * 64}
    elif mutation in {"version", "engine"}:
        installed["distribution_version" if mutation == "version" else "version"] = "1.4.1"
    elif mutation == "editable":
        installed["editable"] = True
    elif mutation == "checkout":
        installed["module"] = installed["distribution_module"] = str(ROOT / "src/otarchguard")
    else:
        installed["distribution_module"] = str(tmp_path / "other/otarchguard")
    with pytest.raises(ValueError, match="exact reviewed transition"):
        legacy._check_candidate_installation(installed, expected)
