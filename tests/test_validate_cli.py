"""Installed validate command: controlled diagnostics, exits and reproducible hashes."""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from otarchguard import cli
from otarchguard.api import validate_file

FIXTURES = Path(__file__).parent / "fixtures"
runner = CliRunner(env={"NO_COLOR": "1", "TERM": "dumb"})


@pytest.mark.parametrize(
    ("name", "code", "category"),
    [
        ("invalid-missing-reference.yaml", "MISSING_REFERENCE", "invalid_input"),
        ("invalid-interface-placement.yaml", "INVALID_PLACEMENT", "invalid_input"),
        ("unsupported-model.yaml", "UNSUPPORTED_CONDUIT", "unsupported_model"),
    ],
)
def test_invalid_fixture_cli(name: str, code: str, category: str) -> None:
    result = runner.invoke(cli.app, ["validate", str(FIXTURES / name)])
    assert result.exit_code == 2
    assert result.stdout == ""
    diagnostic = json.loads(result.stderr)
    assert diagnostic["category"] == category
    assert diagnostic["code"] == code
    assert diagnostic["location"].startswith("$.")
    assert "Traceback" not in result.output


def test_missing_file_cli(tmp_path: Path) -> None:
    result = runner.invoke(cli.app, ["validate", str(tmp_path / "missing")])
    assert result.exit_code == 2
    assert json.loads(result.stderr)["code"] == "READ_ERROR"
    assert result.stdout == ""


def test_success_is_only_structural(tmp_path: Path) -> None:
    target = tmp_path / "local file.yaml"
    target.write_bytes((FIXTURES / "minimal-valid.yaml").read_bytes())
    result = runner.invoke(cli.app, ["validate", str(target)])
    assert result.exit_code == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "valid"
    assert "no path or compliance evaluation" in payload["scope"]
    assert payload["model_sha256"] == validate_file(target).sha256
    assert result.stderr == ""
    assert list(tmp_path.iterdir()) == [target]


def test_installed_validation_from_other_directory(tmp_path: Path) -> None:
    directory = tmp_path / "path with spaces"
    directory.mkdir()
    file = directory / "declared architecture.yaml"
    file.write_bytes((FIXTURES / "boundary-device.yaml").read_bytes())
    command = [sys.executable, "-m", "otarchguard", "validate", str(file)]
    environment = {**os.environ, "NO_COLOR": "1", "TERM": "dumb"}
    first = subprocess.run(
        command,
        cwd=directory,
        env=environment,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    second = subprocess.run(
        command,
        cwd=directory,
        env=environment,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert first.returncode == second.returncode == 0, first.stderr
    assert first.stdout == second.stdout
    assert len(json.loads(first.stdout)["model_sha256"]) == 64


def test_unexpected_failure_does_not_disclose_traceback(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr(cli, "validate_file", broken)
    result = runner.invoke(cli.app, ["validate", "irrelevant.yaml"])
    assert result.exit_code == 2
    assert json.loads(result.stderr)["code"] == "INTERNAL_ERROR"
    assert "secret internal detail" not in result.output
    assert "Traceback" not in result.output


@pytest.mark.parametrize(
    ("name", "code"),
    [
        ("invalid-missing-reference.yaml", "MISSING_REFERENCE"),
        ("invalid-interface-placement.yaml", "INVALID_PLACEMENT"),
        ("unsupported-model.yaml", "UNSUPPORTED_CONDUIT"),
    ],
)
def test_installed_console_process_exit_code(
    name: str, code: str, tmp_path: Path, installed_console: Path
) -> None:
    executable = installed_console
    result = subprocess.run(
        [str(executable), "validate", str((FIXTURES / name).resolve())],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 2, result.stderr
    assert result.stdout == ""
    assert json.loads(result.stderr)["code"] == code
