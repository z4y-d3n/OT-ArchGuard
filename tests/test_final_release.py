"""Final-gate regressions for release evidence that previously escaped the audit."""

import stat
import zipfile
from pathlib import Path

import pytest

from tools.audit_release import check_member, read_wheel
from tools.review_bundle import REVIEW_FILES


@pytest.mark.parametrize(
    "name,mode",
    [
        ("private/", stat.S_IFDIR),
        ("../ignored/", stat.S_IFDIR),
        ("otarchguard/loading.py", stat.S_IFLNK),
        ("otarchguard/loading.py", stat.S_IFIFO),
    ],
)
def test_wheel_audit_checks_previously_ignored_entry_metadata(
    tmp_path: Path, name: str, mode: int
) -> None:
    wheel = tmp_path / "hostile.whl"
    entry = zipfile.ZipInfo(name)
    entry.create_system = 3
    entry.external_attr = (mode | 0o644) << 16
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(entry, b"payload")
    with pytest.raises(ValueError):
        read_wheel(wheel)


def test_wheel_audit_accepts_windows_unspecified_file_type(tmp_path: Path) -> None:
    wheel = tmp_path / "windows.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("otarchguard/loading.py", b"approved")
    assert read_wheel(wheel) == {"otarchguard/loading.py": b"approved"}


@pytest.mark.parametrize("name", ["src//otarchguard/loading.py", "src/./otarchguard/loading.py"])
def test_release_paths_require_canonical_spelling(name: str) -> None:
    with pytest.raises(ValueError):
        check_member(name, wheel=False)


def test_final_review_includes_release_contract_and_exact_gate_regressions() -> None:
    assert {
        "pyproject.toml",
        ".gitattributes",
        ".github/workflows/ci.yml",
        "tools/audit_release.py",
        "tests/test_final_release.py",
        "docs/release-notes-1.2.0.md",
        "docs/release-publication-1.2.0.md",
    } <= REVIEW_FILES
