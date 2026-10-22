"""Native installed console failure matrix: safe errors and atomic report preservation."""

import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("escape", "code", "location", "column"),
    [
        (b"\\uD800", "INVALID_TEXT", "$.revision", 11),
        (b"\\uDBFF", "INVALID_TEXT", "$.revision", 11),
        (b"\\uDC00", "INVALID_TEXT", "$.revision", 11),
        (b"\\uDFFF", "INVALID_TEXT", "$.revision", 11),
        (b"\\U00110000", "YAML_SYNTAX", "$", 14),
        (b"\\UFFFFFFFF", "YAML_SYNTAX", "$", 14),
    ],
)
@pytest.mark.parametrize("case", ["validate", "check", "exposure", "compare_left", "compare_right"])
@pytest.mark.parametrize("report_format", [None, "json", "html"])
def test_native_unicode_failure_is_deterministic_and_preserves_reports(
    escape: bytes,
    code: str,
    location: str,
    column: int,
    case: str,
    report_format: str | None,
    tmp_path: Path,
    installed_console: Path,
) -> None:
    directory = tmp_path / "working directory with spaces"
    directory.mkdir()
    valid = ROOT / "tests/fixtures/minimal-valid.yaml"
    bad = directory / "invalid.yaml"
    bad.write_bytes(
        valid.read_bytes().replace(b"revision: initial", b'revision: "' + escape + b'"')
    )
    command = case.split("_")[0]
    arguments = [command, str(valid if case == "compare_right" else bad)]
    if command == "compare":
        arguments += [str(bad if case == "compare_right" else valid)]
    if command in {"compare", "exposure"}:
        arguments += ["--scenario", "engineering_scope"]
    output = directory / f"report.{report_format}"
    sentinel = b"previous report\x00\xff\n"
    if report_format:
        arguments += ["--report", str(output), "--report-format", report_format]
    environment = {
        **os.environ,
        "PYTHONPATH": str(ROOT / "tools/offline"),
        "OTARCHGUARD_OFFLINE_CHECK": "1",
        "PYTHONIOENCODING": "ascii:strict",
        "NO_COLOR": "1",
        "TERM": "dumb",
    }
    previous_stderr = None
    # Exercise an absent report, then an existing binary sentinel. Directory
    # snapshots include hidden files and catch unintended temporary residue.
    for existing in (False, True):
        if report_format and existing:
            output.write_bytes(sentinel)
        before = {p.name: p.read_bytes() for p in directory.iterdir()}
        result = subprocess.run(
            [str(installed_console), *arguments],
            cwd=directory,
            env=environment,
            capture_output=True,
            check=False,
            timeout=30,
        )
        assert result.returncode == 2
        assert result.stdout == b""
        assert b"Traceback" not in result.stderr
        assert b"INTERNAL_ERROR" not in result.stderr
        result.stderr.decode("ascii")
        assert json.loads(result.stderr) == {
            "category": "invalid_input",
            "code": code,
            "location": location,
            "message": (
                "Text must contain only Unicode scalar values; surrogate code points are forbidden."
                if code == "INVALID_TEXT"
                else "Malformed YAML; check syntax at the reported location."
            ),
            "line": 3,
            "column": column,
        }
        assert {p.name: p.read_bytes() for p in directory.iterdir()} == before
        if previous_stderr is not None:
            assert result.stderr == previous_stderr
        previous_stderr = result.stderr
