"""Snapshot lifetime and deterministic work-conservation regression safeguards."""

import json
import tracemalloc
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
import yaml
from typer.testing import CliRunner

from benchmarks import profile
from otarchguard import api, cli, loading
from otarchguard.api import ValidatedArchitecture
from otarchguard.comparison import compare_architectures
from otarchguard.contract import RESOURCE_LIMITS, ResourceLimits
from otarchguard.exposure import exposure_architecture
from otarchguard.intents import check_architecture


@pytest.mark.parametrize("command", ["check", "exposure", "compare"])
@pytest.mark.parametrize("format", ["html", "json"])
@pytest.mark.parametrize("replace_input", [False, True])
def test_report_reuses_exact_evaluated_snapshots(
    minimal: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    command: str,
    format: str,
    replace_input: bool,
) -> None:
    left, right = tmp_path / "left.yaml", tmp_path / "right.yaml"
    left.write_text(yaml.safe_dump(minimal), encoding="utf-8")
    minimal["revision"] = "different"
    right.write_text(yaml.safe_dump(minimal), encoding="utf-8")
    output = tmp_path / f"report.{format}"
    snapshots: list[ValidatedArchitecture] = []
    validate_input = api._validate

    def validate(value: loading.YamlValue, limits: ResourceLimits) -> ValidatedArchitecture:
        result = validate_input(value, limits)
        snapshots.append(result)
        if replace_input:
            (left, right)[len(snapshots) - 1].write_bytes(b"\xff")
        return result

    monkeypatch.setattr(api, "_validate", validate)
    arguments = [command, str(left)]
    if command == "compare":
        arguments.append(str(right))
    if command != "check":
        arguments += ["--scenario", "engineering_scope"]
    result = CliRunner().invoke(
        cli.app, [*arguments, "--report", str(output), "--report-format", format]
    )
    assert result.exit_code == 0 and result.stderr == ""
    assert len(snapshots) == (2 if command == "compare" else 1)
    payload = json.loads(result.stdout)
    if command == "compare":
        assert snapshots[0].sha256 != snapshots[1].sha256
        assert payload["baseline"]["snapshot_sha256"] == snapshots[0].sha256
        assert payload["proposed"]["snapshot_sha256"] == snapshots[1].sha256
    else:
        assert payload["snapshot_sha256"] == snapshots[0].sha256
    if format == "json":
        report = json.loads(output.read_bytes())
        assert [s["model_sha256"] for s in report["snapshots"]] == [s.sha256 for s in snapshots]
        assert report["result"] == {
            k: v for k, v in payload.items() if k not in {"engine_version", "schema_version"}
        }
    else:
        assert all(s.sha256.encode() in output.read_bytes() for s in snapshots)


@pytest.mark.parametrize("command", ["check", "exposure", "compare"])
def test_consecutive_report_invocations_do_not_reuse_prior_model(
    minimal: dict[str, Any],
    tmp_path: Path,
    command: str,
) -> None:
    path, output = tmp_path / "same.yaml", tmp_path / "report.json"
    args = [command, str(path)] + ([str(path)] if command == "compare" else [])
    if command != "check":
        args += ["--scenario", "engineering_scope"]
    args += ["--report", str(output), "--report-format", "json"]
    runner = CliRunner()
    identities = []
    for valid, permit in [(True, True), (False, False), (True, False), (True, True)]:
        data = {**minimal, "rules": minimal["rules"] if permit else []}
        path.write_bytes(yaml.safe_dump(data).encode() if valid else b"\xff")
        before = output.read_bytes() if output.exists() else b""
        result = runner.invoke(cli.app, args)
        if not valid:
            assert result.exit_code == 2 and not result.stdout
            assert output.read_bytes() == before
            continue
        assert result.exit_code == (0 if permit else 1) and not result.stderr
        report = json.loads(output.read_bytes())
        identities.append(report["snapshots"][0]["model_sha256"])
        assert report["result"]["passed"] is permit
    assert identities[0] == identities[2] != identities[1]
    assert not list(tmp_path.glob(".otarchguard-*"))


def test_measurement_separates_timing_batches_from_traced_allocation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    traced = False
    calls = []
    wall, cpu = (
        iter(range(0, 100_000_000_000, 4_000_000_000)),
        iter(range(0, 100_000_000_000, 2_000_000_000)),
    )

    def start() -> None:
        nonlocal traced
        traced = True

    def stop() -> None:
        nonlocal traced
        traced = False

    monkeypatch.setattr(profile, "perf_counter_ns", lambda: next(wall))
    monkeypatch.setattr(profile, "process_time_ns", lambda: next(cpu))
    monkeypatch.setattr(tracemalloc, "start", start)
    monkeypatch.setattr(tracemalloc, "stop", stop)
    monkeypatch.setattr(tracemalloc, "get_traced_memory", lambda: (7, 11))
    result = profile.measure(lambda: calls.append(traced), runs=3, batch=2)
    assert calls == [False] * 7 + [True]  # warm-up + six timed calls + separate peak
    assert result["wall_seconds"] == [2.0] * 3
    assert result["cpu_seconds"] == [1.0] * 3
    assert result["peak_traced_python_bytes"] == 11 and not traced


@pytest.mark.parametrize("command", ["check", "exposure", "compare"])
def test_report_path_preserves_resource_failure_and_old_artifact(
    minimal: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    command: str,
) -> None:
    path, output = tmp_path / "valid.yaml", tmp_path / "old.html"
    path.write_text(yaml.safe_dump(minimal), encoding="utf-8")
    output.write_bytes(b"old artifact")
    limits = replace(RESOURCE_LIMITS, state_edge_visits=1)

    def restricted(*args: Any, **kwargs: Any) -> Any:
        if command == "check":
            return check_architecture(args[0], limits)
        if command == "exposure":
            return exposure_architecture(args[0], args[1], limits)
        return compare_architectures(args[0], args[1], args[2], limits=limits)

    monkeypatch.setattr(
        cli,
        {
            "check": "check_architecture",
            "exposure": "exposure_architecture",
            "compare": "compare_architectures",
        }[command],
        restricted,
    )
    arguments = [command, str(path)] + ([str(path)] if command == "compare" else [])
    if command != "check":
        arguments += ["--scenario", "engineering_scope"]
    result = CliRunner().invoke(cli.app, [*arguments, "--report", str(output)])
    assert result.exit_code == 2 and not result.stdout
    assert json.loads(result.stderr)["category"] == "resource_limit"
    assert output.read_bytes() == b"old artifact"
    assert not list(tmp_path.glob(".otarchguard-*"))
    monkeypatch.undo()
    completed = CliRunner().invoke(cli.app, [*arguments, "--report", str(output)])
    assert completed.exit_code == 0 and not completed.stderr
    assert output.read_bytes() != b"old artifact"
    assert not list(tmp_path.glob(".otarchguard-*"))
