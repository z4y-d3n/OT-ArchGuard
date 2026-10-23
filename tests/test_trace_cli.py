"""Native installed trace completion, structured failures and atomic reports."""

import json
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml
from typer.testing import CliRunner

from otarchguard.cli import app


@pytest.mark.parametrize("mode", ["reachable", "blocked", "absent", "mixed"])
@pytest.mark.parametrize("format", [None, "json", "html"])
def test_native_trace_completion(
    installed_console: Path, minimal: dict[str, Any], tmp_path: Path, mode: str, format: str | None
) -> None:
    if mode == "blocked":
        minimal["rules"] = []
    elif mode == "absent":
        minimal["rules"] = []
        minimal["transport_edges"] = []
    elif mode == "mixed":
        minimal["services"][0]["destination_ports"] = [{"start": 501, "end": 503}]
    source = tmp_path / "modelo válido.yaml"
    source.write_text(yaml.safe_dump(minimal), encoding="utf-8")
    output = tmp_path / f"evidencia ü.{format}"
    args = [str(installed_console), "trace", str(source), "--source", "eng", "--service", "svc_plc"]
    if format:
        args += ["--report", str(output), "--report-format", format]
        output.write_bytes(b"\x00previous\xff")
    first = subprocess.run(args, capture_output=True, timeout=30)
    second = subprocess.run(args, capture_output=True, timeout=30)
    assert first.returncode == second.returncode == 0
    assert first.stderr == second.stderr == b""
    assert first.stdout == second.stdout
    assert b"\r\n" not in first.stdout
    payload = json.loads(first.stdout)
    outcomes = [i["reachable"] for i in payload["intervals"]]
    assert (
        outcomes
        == {
            "reachable": [True],
            "blocked": [False],
            "absent": [False],
            "mixed": [False, True, False],
        }[mode]
    )
    assert not payload["intents_assessed"] and "passed" not in payload
    if format == "json":
        assert output.read_bytes() == first.stdout
    elif format == "html":
        html = output.read_text(encoding="utf-8")
        assert "Content-Security-Policy" in html and "<script" not in html
        assert 'id="scope"' in html and 'id="evidence"' in html
        assert "trace_version" in html and "Frontier" in html
    assert not list(tmp_path.glob(".otarchguard-*"))


@pytest.mark.parametrize(
    "extra",
    [
        ["--source", "unknown", "--service", "svc_plc"],
        ["--source", "plc", "--service", "svc_plc"],
        ["--source", "eng", "--service", "unknown"],
        ["--source", "bad id", "--service", "svc_plc"],
        ["--source", "eng", "--service", "svc_plc", "--destination", "eng"],
        ["--source", "eng", "--service", "svc_plc", "--destination", "unknown"],
        ["--source", "eng"],
        ["--source", "eng", "--service", "svc_plc", "--unknown"],
        ["--source", "eng", "--service", "svc_plc", "--report-format", "svg"],
    ],
)
def test_native_failure_preserves_sentinel(
    installed_console: Path, tmp_path: Path, extra: list[str]
) -> None:
    report = tmp_path / "sentinel.html"
    sentinel = b"\x00\xffexisting binary\x80"
    report.write_bytes(sentinel)
    args = [
        str(installed_console),
        "trace",
        "tests/fixtures/minimal-valid.yaml",
        *extra,
        "--report",
        str(report),
    ]
    process = subprocess.run(args, capture_output=True, timeout=30)
    assert process.returncode == 2 and process.stdout == b""
    diagnostic = json.loads(process.stderr)
    assert diagnostic["category"] in ("invalid_input", "unsupported_model")
    assert report.read_bytes() == sentinel
    assert not list(tmp_path.glob(".otarchguard-*"))


@pytest.mark.parametrize(
    "failure", ["input", "malformed", "unsupported", "same", "directory", "missing_parent"]
)
def test_native_io_and_model_failures(
    installed_console: Path, minimal: dict[str, Any], tmp_path: Path, failure: str
) -> None:
    source = tmp_path / "input.yaml"
    if failure == "unsupported":
        minimal["unsupported"] = True
    if failure != "input":
        source.write_text(
            "[" if failure == "malformed" else yaml.safe_dump(minimal), encoding="utf-8"
        )
    target = tmp_path / "report.html"
    target.write_bytes(b"\x00\xffold")
    if failure == "same":
        target = source
    elif failure == "directory":
        target = tmp_path
    elif failure == "missing_parent":
        target = tmp_path / "missing" / "report.html"
    before = source.read_bytes() if source.exists() else None
    proc = subprocess.run(
        [
            str(installed_console),
            "trace",
            str(source),
            "--source",
            "eng",
            "--service",
            "svc_plc",
            "--report",
            str(target),
        ],
        capture_output=True,
        timeout=30,
    )
    assert proc.returncode == 2 and not proc.stdout
    assert json.loads(proc.stderr)["code"]
    if source.exists():
        assert source.read_bytes() == before
    assert (tmp_path / "report.html").read_bytes() == b"\x00\xffold"
    assert not list(tmp_path.glob(".otarchguard-*"))


def test_format_requires_report() -> None:
    result = CliRunner().invoke(
        app,
        [
            "trace",
            "tests/fixtures/minimal-valid.yaml",
            "--source",
            "eng",
            "--service",
            "svc_plc",
            "--report-format",
            "json",
        ],
    )
    assert result.exit_code == 2 and not result.stdout
    assert json.loads(result.stderr)["code"] == "INVALID_VALUE"


def test_execution_and_atomic_write_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def broken(*args: Any, **kwargs: Any) -> Any:
        raise OSError("injected failure")

    target = tmp_path / "report.html"
    target.write_bytes(b"\xfforiginal")
    args = [
        "trace",
        "tests/fixtures/minimal-valid.yaml",
        "--source",
        "eng",
        "--service",
        "svc_plc",
        "--report",
        str(target),
    ]
    monkeypatch.setattr(os, "replace", broken)
    result = CliRunner().invoke(app, args)
    assert result.exit_code == 2 and not result.stdout
    assert json.loads(result.stderr)["code"] == "REPORT_IO_ERROR"
    assert target.read_bytes() == b"\xfforiginal" and not list(tmp_path.glob(".otarchguard-*"))
    monkeypatch.setattr("otarchguard.cli.trace_file", broken)
    result = CliRunner().invoke(app, args)
    assert result.exit_code == 2 and not result.stdout
    assert json.loads(result.stderr)["category"] == "execution_error"


def test_native_policy_evidence(installed_console: Path, tmp_path: Path) -> None:
    report = tmp_path / "policy.json"
    proc = subprocess.run(
        [
            str(installed_console),
            "trace",
            "tests/fixtures/minimal-valid.yaml",
            "--source",
            "eng",
            "--service",
            "svc_plc",
            "--destination",
            "plc",
            "--policy-evidence",
            "--report",
            str(report),
            "--report-format",
            "json",
        ],
        capture_output=True,
        timeout=30,
    )
    assert proc.returncode == 0 and not proc.stderr
    evidence = json.loads(proc.stdout)["policy_evidence"]
    assert evidence["status"] == "complete"
    assert evidence["scope"]["examined_edge_ids"] == ["t_eng_plc"]
    assert evidence["work"]["edge_rule_atom_checks"] == 1


def test_resource_failure_preserves_report(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from dataclasses import replace

    from otarchguard.contract import RESOURCE_LIMITS
    from otarchguard.trace import trace_file

    def limited(path: Path, source: str, service: str, **kwargs: Any) -> Any:
        return trace_file(
            path, source, service, replace(RESOURCE_LIMITS, edge_rule_atom_checks=1), **kwargs
        )

    monkeypatch.setattr("otarchguard.cli.trace_file", limited)
    target = tmp_path / "prior.html"
    target.write_bytes(b"\x00\xffprior")
    result = CliRunner().invoke(
        app,
        [
            "trace",
            "tests/fixtures/minimal-valid.yaml",
            "--source",
            "eng",
            "--service",
            "svc_plc",
            "--policy-evidence",
            "--report",
            str(target),
        ],
    )
    assert result.exit_code == 2 and not result.stdout
    assert json.loads(result.stderr)["category"] == "resource_limit"
    assert target.read_bytes() == b"\x00\xffprior" and not list(tmp_path.glob(".otarchguard-*"))
