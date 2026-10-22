"""Deterministic JSON, native exit codes and controlled failures for the new commands."""

import json
import subprocess
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
import yaml
from typer.testing import CliRunner

from otarchguard import cli
from otarchguard.comparison import compare_bytes
from otarchguard.contract import RESOURCE_LIMITS
from otarchguard.exposure import exposure_bytes

runner = CliRunner(env={"NO_COLOR": "1", "TERM": "dumb"})


def write(tmp_path: Path, name: str, data: dict[str, Any]) -> Path:
    path = tmp_path / name
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def test_exposure_json_is_deterministic(boundary: dict[str, Any], tmp_path: Path) -> None:
    path = write(tmp_path, "architecture with spaces.yaml", boundary)
    args = ["exposure", str(path), "--scenario", "support_scope"]
    first, second = runner.invoke(cli.app, args), runner.invoke(cli.app, args)
    assert first.exit_code == second.exit_code == 0
    assert first.stdout == second.stdout and first.stderr == second.stderr == ""
    result = json.loads(first.stdout)
    assert len(result["observations"]) == 4
    assert len(result["destination_assets"]) == 4
    assert "not compromise probability" in result["interpretation"]


def test_compare_reduction_and_regression_exit_one(minimal: dict[str, Any], tmp_path: Path) -> None:
    before = write(tmp_path, "baseline.yaml", minimal)
    minimal["rules"] = []
    after = write(tmp_path, "proposed.yaml", minimal)
    result = runner.invoke(
        cli.app, ["compare", str(before), str(after), "--scenario", "engineering_scope"]
    )
    assert result.exit_code == 1 and result.stderr == ""
    payload = json.loads(result.stdout)
    assert not payload["passed"] and payload["no_longer_reachable"]
    assert payload["broken_required_communications"]


def test_exposure_checks_intents_outside_selected_scenario(
    minimal: dict[str, Any], tmp_path: Path
) -> None:
    minimal["services"].append(
        {
            "id": "outside",
            "asset_id": "plc",
            "interface_id": "plc_net",
            "protocol": "tcp",
            "destination_ports": [{"start": 503, "end": 503}],
        }
    )
    minimal["intents"][0]["destination_service_ids"].append("outside")
    path = write(tmp_path, "model.yaml", minimal)
    result = runner.invoke(cli.app, ["exposure", str(path), "--scenario", "engineering_scope"])
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert not payload["intent_checks"]["passed"] and payload["observations"]
    assert payload["query_scope"]["destination_service_ids"] == ["svc_plc"]


def test_delta_alone_does_not_fail_and_explicit_scope_works(
    minimal: dict[str, Any], tmp_path: Path
) -> None:
    minimal["intents"] = []
    after = write(tmp_path, "after.yaml", minimal)
    minimal["rules"] = []
    before = write(tmp_path, "before.yaml", minimal)
    result = runner.invoke(
        cli.app, ["compare", str(before), str(after), "--origin", "eng", "--service", "svc_plc"]
    )
    assert result.exit_code == 0 and json.loads(result.stdout)["newly_reachable"]


@pytest.mark.parametrize("command", ["exposure", "compare"])
def test_unknown_scenario_and_scope_failure_are_controlled(
    minimal: dict[str, Any], tmp_path: Path, command: str
) -> None:
    path = write(tmp_path, "model.yaml", minimal)
    args = (
        [command, str(path)]
        + ([str(path)] if command == "compare" else [])
        + ["--scenario", "missing"]
    )
    result = runner.invoke(cli.app, args)
    assert result.exit_code == 2 and not result.stdout
    assert json.loads(result.stderr)["code"] == (
        "MISSING_REFERENCE" if command == "exposure" else "SCOPE_MISMATCH"
    )


@pytest.mark.parametrize(
    "arguments",
    [
        [],
        ["--origin", "eng"],
        ["--scenario", "engineering_scope", "--origin", "eng", "--service", "svc_plc"],
    ],
)
def test_comparison_scope_requires_exactly_one_mode(
    minimal: dict[str, Any], tmp_path: Path, arguments: list[str]
) -> None:
    path = write(tmp_path, "model.yaml", minimal)
    result = runner.invoke(cli.app, ["compare", str(path), str(path), *arguments])
    assert result.exit_code == 2 and not result.stdout
    assert json.loads(result.stderr)["category"] == "invalid_input"


@pytest.mark.parametrize("command", ["exposure", "compare"])
def test_resource_errors_emit_no_partial_success(
    minimal: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch, command: str
) -> None:
    data = yaml.safe_dump(minimal).encode()
    limits = replace(RESOURCE_LIMITS, state_edge_visits=1)
    path = write(tmp_path, "model.yaml", minimal)
    if command == "exposure":

        def restricted_exposure(*args: Any, **kwargs: Any) -> object:
            return exposure_bytes(data, "engineering_scope", limits)

        monkeypatch.setattr(cli, "exposure_file", restricted_exposure)
    else:

        def restricted_compare(*args: Any, **kwargs: Any) -> object:
            return compare_bytes(data, data, "engineering_scope", limits=limits)

        monkeypatch.setattr(cli, "compare_files", restricted_compare)
    args = (
        [command, str(path)]
        + ([str(path)] if command == "compare" else [])
        + ["--scenario", "engineering_scope"]
    )
    result = runner.invoke(cli.app, args)
    assert result.exit_code == 2 and not result.stdout
    assert json.loads(result.stderr)["category"] == "resource_limit"


@pytest.mark.parametrize("command", ["exposure", "compare"])
def test_serialization_failure_is_controlled(
    minimal: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch, command: str
) -> None:
    from dataclasses import asdict

    path = write(tmp_path, "model.yaml", minimal)

    def fail_result(value: Any) -> dict[str, Any]:
        if hasattr(value, "observations") or hasattr(value, "newly_reachable"):
            raise MemoryError("private serialization detail")
        return asdict(value)

    monkeypatch.setattr(cli, "asdict", fail_result)
    args = (
        [command, str(path)]
        + ([str(path)] if command == "compare" else [])
        + ["--scenario", "engineering_scope"]
    )
    result = runner.invoke(cli.app, args)
    assert result.exit_code == 2 and not result.stdout
    assert json.loads(result.stderr)["code"] == "INTERNAL_ERROR"
    assert "private serialization detail" not in result.output


@pytest.mark.parametrize("expected", [0, 1, 2])
@pytest.mark.parametrize("command", ["exposure", "compare"])
def test_installed_console_exits(
    minimal: dict[str, Any], tmp_path: Path, command: str, expected: int, installed_console: Path
) -> None:
    before = write(tmp_path, "baseline with spaces.yaml", minimal)
    after_data = deepcopy(minimal)
    if expected == 1:
        after_data["rules"] = []
    elif expected == 2:
        after_data["schema_version"] = 2
    after = write(tmp_path, "after with spaces.yaml", after_data)
    executable = installed_console
    args = [str(executable), command] + (
        [str(before), str(after)] if command == "compare" else [str(after)]
    )
    result = subprocess.run(
        [*args, "--scenario", "engineering_scope"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    assert result.returncode == expected, result.stderr
    assert bool(result.stdout) == (expected != 2)
    assert bool(result.stderr) == (expected == 2)
