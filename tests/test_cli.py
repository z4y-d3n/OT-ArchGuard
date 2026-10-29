"""Installed CLI foundation behavior; no analysis is expected."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from otarchguard import DISTRIBUTION_VERSION as __version__
from otarchguard.cli import app

runner = CliRunner(env={"NO_COLOR": "1", "TERM": "dumb"})


def test_help_and_version() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "check initiation intents" in result.stdout
    for command in ("validate", "check", "exposure", "compare"):
        assert command in result.stdout
    version = runner.invoke(app, ["--version"])
    assert version.exit_code == 0
    assert version.stdout.strip() == __version__


@pytest.mark.parametrize("command", ["validate", "check", "exposure", "compare"])
def test_command_help(command: str) -> None:
    result = runner.invoke(app, [command, "--help"])
    assert result.exit_code == 0
    assert "not implemented" not in result.stdout


@pytest.mark.parametrize(
    "arguments",
    [
        ["exposure", "missing file.yaml", "--scenario", "scope"],
        ["compare", "before.yaml", "after.yaml", "--scenario", "scope"],
    ],
)
def test_scenario_commands_control_unreadable_inputs(arguments: list[str]) -> None:
    result = runner.invoke(app, arguments)
    assert result.exit_code == 2
    assert result.stdout == ""
    assert json.loads(result.stderr)["code"] == "READ_ERROR"
    assert "Traceback" not in result.output


@pytest.mark.parametrize(
    "arguments",
    [[], ["unknown"], ["validate"], ["exposure", "x.yaml"], ["compare", "a", "b"]],
)
def test_usage_errors(arguments: list[str]) -> None:
    result = runner.invoke(app, arguments)
    assert result.exit_code == 2
    assert "Traceback" not in result.output


def test_module_entry_point_from_path_with_spaces(tmp_path: Path) -> None:
    working_directory = tmp_path / "path with spaces"
    working_directory.mkdir()
    environment = {**os.environ, "NO_COLOR": "1", "TERM": "dumb"}
    result = subprocess.run(
        [sys.executable, "-m", "otarchguard", "--help"],
        cwd=working_directory,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    assert "validate" in result.stdout
    assert list(working_directory.iterdir()) == []
