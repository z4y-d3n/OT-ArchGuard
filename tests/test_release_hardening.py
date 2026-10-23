"""Gate V11-5: bounded hostile input, transaction faults and native contracts."""

import json
import os
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
import yaml
from test_reporting import OfflineHTML
from typer.testing import CliRunner

from otarchguard import cli, reporting
from otarchguard.api import validate_bytes
from otarchguard.contract import RESOURCE_LIMITS
from otarchguard.diagnostics import ModelError
from otarchguard.loading import load_bytes, load_file

ROOT = Path(__file__).resolve().parents[1]
COMMANDS = ("validate", "check", "exposure", "compare", "trace")


def arguments(command: str, path: Path) -> list[str]:
    args = [command, str(path)]
    if command == "compare":
        args += [str(path)]
    if command in {"exposure", "compare"}:
        args += ["--scenario", "engineering_scope"]
    if command == "trace":
        args += ["--source", "eng", "--service", "svc_plc"]
    return args


@pytest.mark.parametrize(
    "data",
    [
        b" \t\n",
        b"[{}, []]",
        b"true",
        b"revision: {nested: value}",
        b"a: &recursive [*recursive]",
        b"a: !!binary AA==",
        b"{true: a}",
        b"{? [a, b]: value}",
        b"---\n{}\n---\n{}",
        b"a: '\x00'",
        b"\xc0\xaf",
        b"\xe2\x82",
        b"\xed\xa0\x80",
        b"\xf4\x90\x80\x80",
        b'a: "\\udfff"',
        b'a: "\\U00110000"',
        b"schema_version: 0x01",
        b"schema_version: 1.0",
        b"schema_version: true",
        b"a: " + b"9" * 5000,
    ],
)
def test_hostile_input_is_controlled_and_repeatable(data: bytes) -> None:
    diagnostics = []
    for _ in range(2):
        with pytest.raises(ModelError) as caught:
            validate_bytes(data)
        diagnostics.append(caught.value.diagnostics)
    assert diagnostics[0] == diagnostics[1]
    assert diagnostics[0][0].category in {"invalid_input", "unsupported_model"}


@pytest.mark.parametrize("dimension", ["input_bytes", "nesting_depth", "parser_events"])
@pytest.mark.parametrize("offset", [-1, 0, 1])
def test_small_parser_boundaries(dimension: str, offset: int) -> None:
    data = b"a: [[text]]"
    # Stream/doc/map/key/seq/seq/scalar/seq-end/seq-end/map-end/doc-end/stream-end.
    observed = {"input_bytes": len(data), "nesting_depth": 3, "parser_events": 12}[dimension]
    limits = replace(RESOURCE_LIMITS, **{dimension: observed + offset})
    if offset == -1:
        with pytest.raises(ModelError) as caught:
            load_bytes(data, limits)
        assert caught.value.diagnostics[0].category == "resource_limit"
        assert dimension in caught.value.diagnostics[0].message
    else:
        assert load_bytes(data, limits) == {"a": [["text"]]}


def test_permission_denied_read_is_sanitized(monkeypatch: pytest.MonkeyPatch) -> None:
    def denied(*args: Any, **kwargs: Any) -> Any:
        raise PermissionError("PRIVATE input details")

    monkeypatch.setattr(Path, "open", denied)
    with pytest.raises(ModelError) as caught:
        load_file(Path("private.yaml"))
    diagnostic = caught.value.diagnostics[0]
    assert (diagnostic.category, diagnostic.code) == ("io_error", "READ_ERROR")
    assert "PRIVATE" not in diagnostic.message


@pytest.mark.parametrize("command", COMMANDS)
@pytest.mark.parametrize("fault", ["render", "serialize", "create", "write", "replace"])
def test_every_report_transaction_preserves_inputs_and_destination(
    command: str, fault: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "declaración with spaces 😀.yaml"
    data = (ROOT / "tests/fixtures/minimal-valid.yaml").read_bytes()
    path.write_bytes(data)
    output = tmp_path / "informe 😀.html"
    sentinel = b"\x00\xffold report\r\n"
    output.write_bytes(sentinel)

    def broken(*args: Any, **kwargs: Any) -> Any:
        raise OSError("PRIVATE fault detail C:/secret/credential")

    if fault in {"render", "serialize"}:
        name = (
            ("trace_html" if command == "trace" else "html_report")
            if fault == "render"
            else ("trace_json" if command == "trace" else "json_report")
        )
        monkeypatch.setattr(cli, name, broken)
    elif fault == "create":
        monkeypatch.setattr(tempfile, "NamedTemporaryFile", broken)
    elif fault == "replace":
        monkeypatch.setattr(os, "replace", broken)
    else:
        original = tempfile.NamedTemporaryFile

        class PartialWrite:
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                self.stream = original(*args, **kwargs)
                self.name = self.stream.name

            def __enter__(self) -> "PartialWrite":
                return self

            def write(self, payload: bytes) -> None:
                self.stream.write(payload[:17])
                raise OSError("PRIVATE partial write")

            def __exit__(self, *args: Any) -> None:
                self.stream.close()

        monkeypatch.setattr(tempfile, "NamedTemporaryFile", PartialWrite)
    format = "json" if fault == "serialize" else "html"
    result = CliRunner().invoke(
        cli.app, [*arguments(command, path), "--report", str(output), "--report-format", format]
    )
    assert result.exit_code == 2 and not result.stdout
    diagnostic = json.loads(result.stderr)
    assert diagnostic["category"] == (
        "execution_error" if fault in {"render", "serialize"} else "io_error"
    )
    assert "PRIVATE" not in result.stderr and "Traceback" not in result.stderr
    assert path.read_bytes() == data and output.read_bytes() == sentinel
    assert not list(tmp_path.glob(".otarchguard-*"))


@pytest.mark.parametrize("command", COMMANDS)
@pytest.mark.parametrize("fault", ["unknown", "missing_value", "enum", "empty_id", "missing_file"])
def test_installed_native_negative_contract(
    command: str, fault: str, installed_console: Path, tmp_path: Path
) -> None:
    path = tmp_path / "árbol with spaces 😀.yaml"
    path.write_bytes((ROOT / "tests/fixtures/minimal-valid.yaml").read_bytes())
    args = arguments(command, path)
    if fault == "unknown":
        args += ["--unknown-gate5-option"]
    elif fault == "missing_value":
        args += ["--report"]
    elif fault == "enum":
        args += ["--report-format", "xml"]
    elif fault == "empty_id":
        if command == "trace":
            args += ["--source", ""]
        elif command in {"exposure", "compare"}:
            args += ["--scenario", ""]
        else:
            args += ["--report", str(tmp_path / "report.html"), "--zone-order", ""]
    else:
        args = arguments(command, tmp_path / "missing.yaml")
    result = subprocess.run([str(installed_console), *args], capture_output=True, timeout=30)
    assert result.returncode == 2 and not result.stdout
    assert result.stderr and b"Traceback" not in result.stderr
    if command == "trace" or fault in {"empty_id", "missing_file"}:
        assert json.loads(result.stderr)["category"] in {"invalid_input", "io_error"}
    assert not list(tmp_path.glob(".otarchguard-*"))


@pytest.mark.parametrize("command", COMMANDS)
def test_installed_help_and_repeated_scalar_option(
    command: str, installed_console: Path, tmp_path: Path
) -> None:
    help_result = subprocess.run(
        [str(installed_console), command, "--help"],
        env={**os.environ, "NO_COLOR": "1", "TERM": "dumb"},
        capture_output=True,
        timeout=30,
    )
    assert help_result.returncode == 0 and not help_result.stderr
    assert b"--report" in help_result.stdout
    output = tmp_path / "report.any"
    result = subprocess.run(
        [
            str(installed_console),
            *arguments(command, ROOT / "tests/fixtures/minimal-valid.yaml"),
            "--report",
            str(output),
            "--report-format",
            "html",
            "--report-format",
            "json",
        ],
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0 and not result.stderr
    payload = json.loads(output.read_bytes())
    assert payload.get("trace_version", payload.get("report_version")) == 1


@pytest.mark.parametrize("command", COMMANDS)
@pytest.mark.parametrize(
    "payload",
    [
        '<script src="https://invalid.example/payload">alert(1)</script>',
        '"><img src=x onerror="alert(1)"><a href="javascript:alert(1)">x</a>',
        "combining e\u0301 confusable а \u202e bidi \u2028 line \u2029 paragraph 😀 \uffff",
    ],
)
def test_hostile_display_text_is_inert_parsed_markup(
    command: str, payload: str, minimal: dict[str, Any], tmp_path: Path
) -> None:
    minimal["revision"] = payload
    minimal["zones"][0]["name"] = payload
    minimal["assets"][0]["name"] = payload
    minimal["suc"]["completeness_assertion"] = payload
    minimal["scenarios"][0]["description"] = payload
    path = tmp_path / "input.yaml"
    path.write_text(yaml.safe_dump(minimal, allow_unicode=True), encoding="utf-8")
    validated = validate_bytes(path.read_bytes())
    svg = ET.fromstring(reporting.architecture_svg(validated))
    ns = {"s": "http://www.w3.org/2000/svg"}
    assert {e.attrib["data-edge-id"] for e in svg.findall("s:g[@data-edge-id]", ns)} == {
        "t_eng_plc"
    }
    for element in svg.iter():
        assert not any(key.lower().startswith("on") for key in element.attrib)
    output = tmp_path / "report.html"
    result = CliRunner().invoke(cli.app, [*arguments(command, path), "--report", str(output)])
    assert result.exit_code == 0 and not result.stderr
    parser = OfflineHTML()
    parser.feed(output.read_text(encoding="utf-8"))
    assert parser.csp
    assert str(tmp_path) not in output.read_text(encoding="utf-8")
