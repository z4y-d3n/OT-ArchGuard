"""T01 and applicable T20: bounded syntax, scalar semantics and safe rejection."""

from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
import yaml

from otarchguard.api import validate_bytes
from otarchguard.contract import RESOURCE_LIMITS, DiagnosticCategory
from otarchguard.diagnostics import ModelError
from otarchguard.loading import load_bytes, load_file


@pytest.mark.parametrize(
    ("source", "code"),
    [
        (b"", "YAML_SYNTAX"),
        (b"\xff", "YAML_SYNTAX"),
        (b"a: [", "YAML_SYNTAX"),
        (b"a: 1\na: 2", "DUPLICATE_KEY"),
        (b"a: {b: 1, b: 2}", "DUPLICATE_KEY"),
        (b"---\na: 1\n---\nb: 2", "MULTIPLE_DOCUMENTS"),
        (b"a: &x [1]\nb: *x", "YAML_FEATURE"),
        (b"a: *x", "YAML_FEATURE"),
        (b"a: !!str value", "YAML_FEATURE"),
        (b"!!python/object/apply:os.system ['never execute']", "YAML_FEATURE"),
        (b"%YAML 1.1\n---\na: 1", "YAML_FEATURE"),
        (b"%YAML 1.3\n---\na: 1", "YAML_FEATURE"),
        (b"%IGNORED argument\n---\na: 1", "YAML_FEATURE"),
        (b"%TAG !e! tag:example.com,2000:\n---\na: 1", "YAML_FEATURE"),
        (b"a: {<<: {b: 1}}", "YAML_FEATURE"),
        (b"1: value", "TYPE_MISMATCH"),
        (b"[a, b]: value", "TYPE_MISMATCH"),
        (b"a: .NaN", "TYPE_MISMATCH"),
        (b"a: 2e3", "TYPE_MISMATCH"),
        (b"a: -.5", "TYPE_MISMATCH"),
    ],
)
def test_reject_yaml_features(source: bytes, code: str) -> None:
    with pytest.raises(ModelError) as caught:
        load_bytes(source)
    assert caught.value.diagnostics[0].code == code


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (b"true", True),
        (b"false", False),
        (b"null", None),
        (b"~", None),
        (b"-12", -12),
        (b"yes", "yes"),
        (b"off", "off"),
        (b"2026-10-21", "2026-10-21"),
        (b"0x20", "0x20"),
        (b"012", "012"),
        (b"1_000", "1_000"),
        (b"True", "True"),
        (b"'2.0'", "2.0"),
        (b"'true'", "true"),
    ],
)
def test_explicit_scalar_resolution(source: bytes, expected: object) -> None:
    actual = load_bytes(source)
    assert type(actual) is type(expected)
    assert actual == expected


def test_block_text_and_markers() -> None:
    assert load_bytes(b"---\na: |\n  on\n  %literal\n...\n") == {"a": "on\n%literal\n"}


@pytest.mark.parametrize("source", [b"[]", b"null", b"42", b"zones: []"])
def test_root_requires_complete_mapping(source: bytes) -> None:
    with pytest.raises(ModelError):
        validate_bytes(source)


def test_syntax_location_is_safe() -> None:
    with pytest.raises(ModelError) as caught:
        load_bytes(b"secret_label: [\n")
    diagnostic = caught.value.diagnostics[0]
    assert diagnostic.line is not None and diagnostic.column is not None
    assert "secret_label" not in diagnostic.message


def test_depth_budget_before_construction() -> None:
    at_limit = b"[" * 32 + b"0" + b"]" * 32
    assert isinstance(load_bytes(at_limit), list)
    with pytest.raises(ModelError, match="Architecture processing failed") as caught:
        load_bytes(b"[" + at_limit + b"]")
    assert "nesting_depth" in caught.value.diagnostics[0].message


def test_event_budget_exact_boundary() -> None:
    source = b"a: [1, 2]"
    count = len(list(yaml.parse(source)))
    assert load_bytes(source, replace(RESOURCE_LIMITS, parser_events=count)) == {"a": [1, 2]}
    with pytest.raises(ModelError) as caught:
        load_bytes(source, replace(RESOURCE_LIMITS, parser_events=count - 1))
    assert "parser_events" in caught.value.diagnostics[0].message


def test_byte_budget_and_bounded_file_read(tmp_path: Path) -> None:
    source = b"a: text"
    limits = replace(RESOURCE_LIMITS, input_bytes=len(source))
    assert load_bytes(source, limits) == {"a": "text"}
    file = tmp_path / "architecture.yaml"
    file.write_bytes(source + b" " * 100)
    with pytest.raises(ModelError) as caught:
        load_file(file, limits)
    assert caught.value.diagnostics[0].category == DiagnosticCategory.RESOURCE_LIMIT
    assert f"observed/planned {len(source) + 1}" in caught.value.diagnostics[0].message


def test_default_byte_limit() -> None:
    with pytest.raises(ModelError) as caught:
        load_bytes(b" " * (RESOURCE_LIMITS.input_bytes + 1))
    assert "input_bytes" in caught.value.diagnostics[0].message


def test_read_failure(tmp_path: Path) -> None:
    with pytest.raises(ModelError) as caught:
        load_file(tmp_path / "missing")
    assert caught.value.diagnostics[0].category == DiagnosticCategory.IO_ERROR
    assert caught.value.diagnostics[0].code == "READ_ERROR"


def test_duplicate_keys_at_nested_valid_location(minimal: dict[str, Any]) -> None:
    source = yaml.safe_dump(minimal)
    source += "\nduplicate: {nested: {port: 1, port: 2}}"
    with pytest.raises(ModelError) as caught:
        validate_bytes(source.encode())
    assert caught.value.diagnostics[0].code == "DUPLICATE_KEY"
