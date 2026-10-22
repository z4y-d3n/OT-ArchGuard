"""Independent regression tests for source distribution integrity."""

from pathlib import Path

import pytest

from tools.audit_release import check_member, normalize_requirement, verify_source_files


@pytest.mark.parametrize(
    "name",
    [
        "docs/internal-audit.md",
        "docs/research.md",
        "docs/unreviewed.md",
        "private/notes.md",
        "docs/source-map.json",
    ],
)
def test_unreviewed_source_files_are_rejected(name: str) -> None:
    with pytest.raises(ValueError, match="Unreviewed"):
        check_member(name, wheel=False)


@pytest.mark.parametrize("name", ["tests/test_integration.py", "README.md"])
def test_modified_test_or_document_bytes_are_rejected(tmp_path: Path, name: str) -> None:
    source = tmp_path / name
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b"current approved candidate\n")
    with pytest.raises(ValueError, match="Source bytes differ"):
        verify_source_files({name: b"outdated archived content\n"}, tmp_path, frozenset({name}))


def test_missing_public_source_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="missing"):
        verify_source_files({}, tmp_path, frozenset({"tests/test_integration.py"}))


def test_dependency_clause_order_does_not_change_required_bounds() -> None:
    assert normalize_requirement("PyYAML>=6,<7") == normalize_requirement("pyyaml<7,>=6")
    assert normalize_requirement("PyYAML>=6,<7") != normalize_requirement("pyyaml>=6")
    assert normalize_requirement("PyYAML>=6,<7") != normalize_requirement("pyyaml<8,>=6")
