"""Installed check CLI exits, complete output and controlled fatal errors."""

import json
import subprocess
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

import pytest
import yaml
from typer.testing import CliRunner

from otarchguard import cli
from otarchguard.api import validate_bytes
from otarchguard.contract import RESOURCE_LIMITS
from otarchguard.policy import Work
from otarchguard.reachability import ReachabilityEngine

FIXTURES = Path(__file__).parent / "fixtures"
runner = CliRunner(env={"NO_COLOR": "1", "TERM": "dumb"})


def test_boundary_check_passes_and_is_reproducible() -> None:
    args = ["check", str(FIXTURES / "boundary-device.yaml")]
    first, second = runner.invoke(cli.app, args), runner.invoke(cli.app, args)
    assert first.exit_code == second.exit_code == 0
    assert first.stdout == second.stdout and first.stderr == second.stderr == ""
    result = json.loads(first.stdout)
    assert result["passed"] and len(result["intents"]) == 8
    assert "not sessions, compromise, risk or compliance" in result["scope"]


@pytest.mark.parametrize("kind", ["required", "prohibited"])
def test_failed_intents_exit_one(minimal: dict[str, Any], tmp_path: Path, kind: str) -> None:
    minimal["intents"][0]["kind"] = kind
    if kind == "required":
        minimal["rules"] = []
    path = tmp_path / "model with spaces.yaml"
    path.write_text(yaml.safe_dump(minimal), encoding="utf-8")
    result = runner.invoke(cli.app, ["check", str(path)])
    assert result.exit_code == 1 and result.stderr == ""
    payload = json.loads(result.stdout)
    assert not payload["passed"] and payload["failed_intent_count"] == 1
    interval = payload["intents"][0]["queries"][0]["intervals"][0]
    assert (interval["witness"] is not None) == (kind == "prohibited")


@pytest.mark.parametrize(
    ("name", "code"),
    [
        ("invalid-missing-reference.yaml", "MISSING_REFERENCE"),
        ("invalid-interface-placement.yaml", "INVALID_PLACEMENT"),
        ("unsupported-model.yaml", "UNSUPPORTED_CONDUIT"),
    ],
)
def test_invalid_input_is_never_a_policy_result(name: str, code: str) -> None:
    result = runner.invoke(cli.app, ["check", str(FIXTURES / name)])
    assert result.exit_code == 2 and result.stdout == ""
    assert json.loads(result.stderr)["code"] == code


def test_resource_failure_after_partial_search_emits_no_partial_result(
    minimal: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    minimal["services"][0]["destination_ports"] = [{"start": 501, "end": 502}]
    engine = ReachabilityEngine(validate_bytes(yaml.safe_dump(minimal).encode()))
    # Inject a smaller runtime counter than the preflight limit to exercise the
    # second line of defense; no fabricated successful partial answer is allowed.
    engine.work = Work(replace(RESOURCE_LIMITS, state_edge_visits=3))

    def fail_during_work(path: Path) -> object:
        return engine.evaluate("eng", "svc_plc")

    monkeypatch.setattr(cli, "check_file", fail_during_work)
    result = runner.invoke(cli.app, ["check", "unused.yaml"])
    assert result.exit_code == 2 and result.stdout == ""
    assert json.loads(result.stderr)["category"] == "resource_limit"


def test_unexpected_failure_is_controlled(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(path: Path) -> None:
        raise RuntimeError("private exception detail")

    monkeypatch.setattr(cli, "check_file", broken)
    result = runner.invoke(cli.app, ["check", "unused.yaml"])
    assert result.exit_code == 2 and result.stdout == ""
    assert json.loads(result.stderr)["code"] == "INTERNAL_ERROR"
    assert "private exception detail" not in result.output and "Traceback" not in result.output


def test_result_serialization_failure_has_no_success_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = asdict

    def serialize(value: Any) -> dict[str, Any]:
        if hasattr(value, "intents"):
            raise MemoryError("serialization failed")
        return original(value)

    monkeypatch.setattr(cli, "asdict", serialize)
    result = runner.invoke(cli.app, ["check", str(FIXTURES / "minimal-valid.yaml")])
    assert result.exit_code == 2 and result.stdout == ""
    assert json.loads(result.stderr)["code"] == "INTERNAL_ERROR"


@pytest.mark.parametrize("expected", [0, 1, 2])
def test_installed_console_exit_codes(
    minimal: dict[str, Any], tmp_path: Path, expected: int, installed_console: Path
) -> None:
    if expected == 1:
        minimal["rules"] = []
    if expected == 2:
        minimal["schema_version"] = 2
    path = tmp_path / "path with spaces.yaml"
    path.write_text(yaml.safe_dump(minimal), encoding="utf-8")
    executable = installed_console
    result = subprocess.run(
        [str(executable), "check", str(path)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == expected, result.stderr
    assert bool(result.stdout) == (expected != 2)
    assert bool(result.stderr) == (expected == 2)
