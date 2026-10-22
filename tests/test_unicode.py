"""Unicode scalar validation, public API rejection and independent canonical oracles."""

import hashlib
import json
from collections.abc import Callable
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

import pytest
import yaml
from yaml.error import Mark
from yaml.scanner import Scanner

from otarchguard.api import validate_bytes, validate_file
from otarchguard.comparison import compare_bytes, compare_files
from otarchguard.contract import RESOURCE_LIMITS, DiagnosticCategory
from otarchguard.diagnostics import Diagnostic, ModelError
from otarchguard.exposure import exposure_bytes, exposure_file
from otarchguard.intents import check_bytes, check_file
from otarchguard.loading import load_bytes, load_file

SURROGATES = (0xD800, 0xD801, 0xD955, 0xDBFE, 0xDBFF, 0xDC00, 0xDC01, 0xDDAA, 0xDFFE, 0xDFFF)
MESSAGE = "Text must contain only Unicode scalar values; surrogate code points are forbidden."


@pytest.mark.parametrize("point", SURROGATES)
@pytest.mark.parametrize("escape", ["u", "U"])
@pytest.mark.parametrize(
    ("template", "location", "line", "column"),
    [
        ('"%s"', "$", 1, 1),
        ('revision: "%s"', "$.revision", 1, 11),
        ('"%s": value', "$", 1, 1),
        ('suc:\n  "%s": value', "$.suc", 2, 3),
        ('assets:\n  - name: "%s"', "$.assets[0].name", 2, 11),
        ('metadata:\n  nested: [safe, "%s"]', "$.metadata.nested[1]", 2, 18),
    ],
)
def test_escaped_surrogates_have_safe_exact_locations(
    point: int, escape: str, template: str, location: str, line: int, column: int
) -> None:
    escaped = f"\\u{point:04X}" if escape == "u" else f"\\U{point:08X}"
    source = (template % escaped).encode("ascii")
    with pytest.raises(ModelError) as caught:
        load_bytes(source)
    assert caught.value.diagnostics == (
        Diagnostic(
            DiagnosticCategory.INVALID_INPUT, "INVALID_TEXT", location, MESSAGE, line, column
        ),
    )
    assert str(caught.value) == "Architecture processing failed"
    # Both common machine-output modes remain safe; no malformed input is echoed.
    json.dumps(asdict(caught.value.diagnostics[0]), ensure_ascii=False).encode("utf-8")
    json.dumps(asdict(caught.value.diagnostics[0]), ensure_ascii=True).encode("ascii")


def test_entire_surrogate_range_is_rejected() -> None:
    for point in range(0xD800, 0xE000):
        with pytest.raises(ModelError) as caught:
            load_bytes(f'"\\u{point:04x}"'.encode("ascii"))
        assert caught.value.diagnostics[0].code == "INVALID_TEXT"


@pytest.mark.parametrize("escaped", [b"\\uD800\\uDC00", b"\\uDC00\\uD800"])
def test_surrogate_pairs_are_not_repaired(escaped: bytes) -> None:
    with pytest.raises(ModelError) as caught:
        load_bytes(b'"' + escaped + b'"')
    assert caught.value.diagnostics[0].code == "INVALID_TEXT"
    assert load_bytes(b'"\\U00010000"') == "\U00010000"


@pytest.mark.parametrize("point", [0xD7FF, 0xE000, 0xFFFF, 0x10000, 0x1F600, 0x10FFFF])
def test_adjacent_boundaries_and_supplementary_scalars_are_accepted(point: int) -> None:
    assert load_bytes(f'"\\U{point:08X}"'.encode("ascii")) == chr(point)


@pytest.mark.parametrize("source", [b'"\xed\xa0\x80"', b'"\xed\xbf\xbf"', b'"\x00"'])
def test_raw_invalid_utf8_or_yaml_character_retains_parser_diagnostic(source: bytes) -> None:
    with pytest.raises(ModelError) as caught:
        load_bytes(source)
    assert caught.value.diagnostics[0].code == "YAML_SYNTAX"
    assert caught.value.diagnostics[0].category == DiagnosticCategory.INVALID_INPUT


@pytest.mark.parametrize("field", ["revision", "name", "purpose", "id", "key"])
@pytest.mark.parametrize(
    "entry", ["load", "validate", "check", "exposure", "compare_left", "compare_right"]
)
@pytest.mark.parametrize("from_file", [False, True])
def test_shared_boundary_protects_public_entry_points(
    minimal: dict[str, Any], tmp_path: Path, field: str, entry: str, from_file: bool
) -> None:
    good = yaml.safe_dump(minimal).encode("utf-8")
    if field == "revision":
        minimal[field] = "unsafe\udbff"
        location = "$.revision"
    elif field == "key":
        minimal["suc"]["unsafe\udfff"] = "value"
        location = "$.suc"
    else:
        minimal["suc"][field] = "unsafe\udc00"
        location = f"$.suc.{field}"
    bad = yaml.safe_dump(minimal).encode("utf-8")
    good_file, bad_file = tmp_path / "good.yaml", tmp_path / "bad.yaml"
    good_file.write_bytes(good)
    bad_file.write_bytes(bad)
    with pytest.raises(ModelError) as caught:
        if from_file:
            if entry == "load":
                load_file(bad_file)
            elif entry == "validate":
                validate_file(bad_file)
            elif entry == "check":
                check_file(bad_file)
            elif entry == "exposure":
                exposure_file(bad_file, "engineering_scope")
            elif entry == "compare_left":
                compare_files(bad_file, good_file, "engineering_scope")
            else:
                compare_files(good_file, bad_file, "engineering_scope")
        elif entry == "load":
            load_bytes(bad)
        elif entry == "validate":
            validate_bytes(bad)
        elif entry == "check":
            check_bytes(bad)
        elif entry == "exposure":
            exposure_bytes(bad, "engineering_scope")
        elif entry == "compare_left":
            compare_bytes(bad, good, "engineering_scope")
        else:
            compare_bytes(good, bad, "engineering_scope")
    diagnostic = caught.value.diagnostics[0]
    assert diagnostic.category == DiagnosticCategory.INVALID_INPUT
    assert diagnostic.code == "INVALID_TEXT"
    assert diagnostic.location == location
    assert diagnostic.message == MESSAGE


@pytest.mark.parametrize(
    "text",
    [
        "Ordinary ASCII",
        "Espa\u00f1ol: acci\u00f3n",
        "\u03a9 \u4e2d\u6587 \u0627\u0644\u0639\u0631\u0628\u064a\u0629",
        "\U0001f600 \U00010000 \U0010ffff",
        "e\u0301",
        "\u00e9",
        "before\x00\x01\ufffe\uffffafter",
        "\ud7ff\ue000",
    ],
)
def test_valid_text_has_independent_exact_canonical_bytes(
    minimal: dict[str, Any], text: str
) -> None:
    minimal["revision"] = text
    minimal["assets"][0]["name"] = text
    # This fixture is already in canonical record/list order. The oracle uses the
    # declaration directly, without calling production normalization or hashing.
    expected = json.dumps(
        minimal, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode()
    source = yaml.safe_dump(minimal, allow_unicode=True).encode()
    result = validate_bytes(source)
    assert result.canonical_json == expected
    assert result.sha256 == hashlib.sha256(expected).hexdigest()
    assert check_bytes(source).passed


def test_combining_text_keeps_distinct_identity(minimal: dict[str, Any]) -> None:
    minimal["revision"] = "\u00e9"
    composed = validate_bytes(yaml.safe_dump(minimal).encode())
    minimal["revision"] = "e\u0301"
    combining = validate_bytes(yaml.safe_dump(minimal).encode())
    assert composed.canonical_json != combining.canonical_json
    assert composed.sha256 != combining.sha256


def test_valid_unicode_key_in_diagnostic_is_safely_serializable() -> None:
    with pytest.raises(ModelError) as caught:
        load_bytes(b'"\\U0001F600": {nested: "\\uD800"}')
    diagnostic = caught.value.diagnostics[0]
    assert diagnostic.location == "$.\U0001f600.nested"
    assert diagnostic.code == "INVALID_TEXT"
    json.dumps(asdict(diagnostic), ensure_ascii=True).encode("ascii")


@pytest.mark.parametrize(
    "escape", [b"00110000", b"00110001", b"7FFFFFFF", b"80000000", b"FFFFFFFF", b"ffffffff"]
)
@pytest.mark.parametrize(
    ("template", "line", "column"),
    [
        (b'"\\U%s"', 1, 4),
        (b'revision: "\\U%s"', 1, 14),
        (b'"\\U%s": value', 1, 4),
        (b'suc:\n  "\\U%s": value', 2, 6),
        (b'assets:\n  - name: "\\U%s"', 2, 14),
    ],
)
def test_out_of_range_escapes_are_exact_scanner_diagnostics(
    escape: bytes, template: bytes, line: int, column: int
) -> None:
    for _ in range(2):
        with pytest.raises(ModelError) as caught:
            load_bytes(template % escape)
        assert caught.value.diagnostics == (
            Diagnostic(
                DiagnosticCategory.INVALID_INPUT,
                "YAML_SYNTAX",
                "$",
                "Malformed YAML; check syntax at the reported location.",
                line,
                column,
            ),
        )
        json.dumps(asdict(caught.value.diagnostics[0]), ensure_ascii=False).encode("ascii")


@pytest.mark.parametrize("escape", [b"\\U00110000", b"\\UFFFFFFFF"])
@pytest.mark.parametrize(
    "entry",
    [
        "load_bytes",
        "load_file",
        "validate_bytes",
        "validate_file",
        "check_bytes",
        "check_file",
        "exposure_bytes",
        "exposure_file",
        "compare_bytes_left",
        "compare_bytes_right",
        "compare_files_left",
        "compare_files_right",
    ],
)
def test_out_of_range_escape_public_apis(escape: bytes, entry: str, tmp_path: Path) -> None:
    good_file = Path(__file__).parent / "fixtures/minimal-valid.yaml"
    good = good_file.read_bytes()
    bad = good.replace(b"revision: initial", b'revision: "' + escape + b'"')
    bad_file = tmp_path / "invalid.yaml"
    bad_file.write_bytes(bad)
    actions: dict[str, Callable[[], object]] = {
        "load_bytes": lambda: load_bytes(bad),
        "load_file": lambda: load_file(bad_file),
        "validate_bytes": lambda: validate_bytes(bad),
        "validate_file": lambda: validate_file(bad_file),
        "check_bytes": lambda: check_bytes(bad),
        "check_file": lambda: check_file(bad_file),
        "exposure_bytes": lambda: exposure_bytes(bad, "engineering_scope"),
        "exposure_file": lambda: exposure_file(bad_file, "engineering_scope"),
        "compare_bytes_left": lambda: compare_bytes(bad, good, "engineering_scope"),
        "compare_bytes_right": lambda: compare_bytes(good, bad, "engineering_scope"),
        "compare_files_left": lambda: compare_files(bad_file, good_file, "engineering_scope"),
        "compare_files_right": lambda: compare_files(good_file, bad_file, "engineering_scope"),
    }
    with pytest.raises(ModelError) as caught:
        actions[entry]()
    assert caught.value.diagnostics == (
        Diagnostic(
            DiagnosticCategory.INVALID_INPUT,
            "YAML_SYNTAX",
            "$",
            "Malformed YAML; check syntax at the reported location.",
            3,
            14,
        ),
    )


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (b"\\U00110000", r"\U00110000"),
        (b"'\\UFFFFFFFF'", r"\UFFFFFFFF"),
        (b'"\\\\U00110000"', r"\U00110000"),
        (b'"\\\\UFFFFFFFF"', r"\UFFFFFFFF"),
        (b"|\n  \\U00110000\n", "\\U00110000\n"),
        (b">\n  \\UFFFFFFFF\n", "\\UFFFFFFFF\n"),
        (b"safe # \\UFFFFFFFF", "safe"),
        (b'"\\U0010FFFF"', "\U0010ffff"),
        (b'"\\U0010ffff"', "\U0010ffff"),
        (b'"\\U0010FFFE"', "\U0010fffe"),
        (b'"\\U0010FFFFF"', "\U0010ffffF"),
        (b'"\\u00110000"', "\x110000"),
        (b'"\\uFFFF"', "\uffff"),
        (b'"\\xFF"', "\xff"),
    ],
)
def test_unicode_escape_context_and_valid_boundaries_are_preserved(
    source: bytes, expected: str
) -> None:
    assert load_bytes(source) == expected


@pytest.mark.parametrize("escape", [b"\\U0011000", b"\\U0011000G", b"\\uZZZZ", b"\\U+0110000"])
def test_incomplete_or_nonhex_escape_retains_yaml_syntax(escape: bytes) -> None:
    with pytest.raises(ModelError) as caught:
        load_bytes(b'"' + escape + b'"')
    assert caught.value.diagnostics == (
        Diagnostic(
            DiagnosticCategory.INVALID_INPUT,
            "YAML_SYNTAX",
            "$",
            "Malformed YAML; check syntax at the reported location.",
            1,
            4,
        ),
    )


def test_earlier_parser_error_survives_directive_rescan() -> None:
    with pytest.raises(ModelError) as caught:
        load_bytes(b'first: [}\nsecond: "\\UFFFFFFFF"')
    diagnostic = caught.value.diagnostics[0]
    assert diagnostic.code == "YAML_SYNTAX"
    assert (diagnostic.line, diagnostic.column) == (1, 9)


def test_directive_priority_and_byte_limit_remain_unchanged() -> None:
    source = b'%YAML 1.3\n---\nrevision: "\\UFFFFFFFF"'
    with pytest.raises(ModelError) as caught:
        load_bytes(source)
    assert caught.value.diagnostics[0].code == "YAML_FEATURE"
    with pytest.raises(ModelError) as caught:
        load_bytes(source, replace(RESOURCE_LIMITS, input_bytes=len(source) - 1))
    assert caught.value.diagnostics[0].category == DiagnosticCategory.RESOURCE_LIMIT


@pytest.mark.parametrize("error_type", [ValueError, OverflowError, RuntimeError])
@pytest.mark.parametrize("source", [b'"safe"', b'"\\U00110000"', b'"\\UFFFFFFFF"'])
def test_unrelated_scanner_failures_are_not_masked(
    monkeypatch: pytest.MonkeyPatch, error_type: type[Exception], source: bytes
) -> None:
    failure = error_type("unrelated scanner failure")

    def broken(self: Scanner, double: bool, start_mark: Mark) -> list[str]:
        raise failure

    monkeypatch.setattr(Scanner, "scan_flow_scalar_non_spaces", broken)
    with pytest.raises(error_type) as caught:
        load_bytes(source)
    assert caught.value is failure
