"""Installed CLI pipelines, local artifacts and enforced-offline subprocess checks."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from benchmarks.workloads import source_bytes

ROOT = Path(__file__).resolve().parents[1]


def offline_environment() -> dict[str, str]:
    return {
        **os.environ,
        "PYTHONPATH": str(ROOT / "tools/offline"),
        "OTARCHGUARD_OFFLINE_CHECK": "1",
        "NO_COLOR": "1",
        "TERM": "dumb",
    }


@pytest.mark.parametrize("probe", ["socket.socket()", "socket.getaddrinfo('denied.invalid', 443)"])
def test_network_guard_rejects_operations_before_network(probe: str, tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-c", f"import socket; {probe}"],
        cwd=tmp_path,
        env=offline_environment(),
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    assert result.returncode != 0
    assert "OFFLINE_GUARD: network operation denied" in result.stderr


@pytest.mark.parametrize(
    "family,scenario",
    [
        ("flat-plant", "plant_scope"),
        ("segmented-plant", "plant_scope"),
        ("remote-support", "support_scope"),
    ],
)
@pytest.mark.parametrize("command", ["validate", "check", "exposure", "compare"])
@pytest.mark.parametrize("format", ["html", "json"])
def test_offline_installed_cli_and_report_determinism(
    family: str, scenario: str, command: str, format: str, tmp_path: Path, installed_console: Path
) -> None:
    directory = tmp_path / "working directory with spaces"
    directory.mkdir()
    baseline = ROOT / "examples" / family / "baseline.yaml"
    proposed = baseline.with_name("proposed.yaml")
    args = [command, str(baseline)] + ([str(proposed)] if command == "compare" else [])
    if command in {"exposure", "compare"}:
        args += ["--scenario", scenario]
    output = directory / f"local report.{format}"
    executable = installed_console
    expected = 1 if command == "compare" else 0
    previous_stdout = None
    previous_report = None
    for _ in range(2):
        result = subprocess.run(
            [str(executable), *args, "--report", str(output), "--report-format", format],
            cwd=directory,
            env=offline_environment(),
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        assert result.returncode == expected, result.stderr
        assert result.stderr == "" and json.loads(result.stdout)
        report = output.read_bytes()
        if previous_stdout is not None:
            assert result.stdout == previous_stdout and report == previous_report
        if format == "html":
            assert b"<svg" in report and b"data-zone-id=" in report
        else:
            payload = json.loads(report)
            assert payload["report_version"] == 1
            assert payload["status"] == (
                "failed_intents" if expected else "valid" if command == "validate" else "passed"
            )
        previous_stdout, previous_report = result.stdout, report


@pytest.mark.parametrize("command", ["validate", "check", "exposure", "compare"])
def test_default_byte_ceiling_never_writes_partial_report(command: str, tmp_path: Path) -> None:
    path = tmp_path / "too large.yaml"
    path.write_bytes(b" " * (5 * 1024 * 1024 + 1))
    output = tmp_path / "report.html"
    output.write_bytes(b"previous artifact")
    args = [command, str(path)] + ([str(path)] if command == "compare" else [])
    if command in {"exposure", "compare"}:
        args += ["--scenario", "scope"]
    result = subprocess.run(
        [sys.executable, "-m", "otarchguard", *args, "--report", str(output)],
        cwd=tmp_path,
        env=offline_environment(),
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    assert result.returncode == 2 and result.stdout == ""
    diagnostic = json.loads(result.stderr)
    assert diagnostic["category"] == "resource_limit" and "input_bytes" in diagnostic["message"]
    assert output.read_bytes() == b"previous artifact"


@pytest.mark.parametrize(
    "profile,limit",
    [
        ("dense-policy", "edge_rule_atom_checks"),
        ("interval-heavy", "state_edge_visits"),
    ],
)
@pytest.mark.parametrize("command", ["exposure", "compare"])
def test_default_work_ceiling_leaves_no_success_after_rejection(
    profile: str, limit: str, command: str, tmp_path: Path
) -> None:
    path = tmp_path / "bounded model.yaml"
    path.write_bytes(source_bytes(profile))
    output = tmp_path / "report.json"
    output.write_bytes(b"previous artifact")
    args = [command, str(path)] + ([str(path)] if command == "compare" else [])
    # Dense-policy compare validates two ~1.4 MiB YAML inputs before work preflight.
    # Allow hosted-runner variability with a bounded hang guard for this case only;
    # NFR-05's 30 s warm routine-exposure target and production limits are unchanged.
    timeout = 90 if command == "compare" and profile == "dense-policy" else 30
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "otarchguard",
            *args,
            "--scenario",
            "scope",
            "--report",
            str(output),
            "--report-format",
            "json",
        ],
        cwd=tmp_path,
        env=offline_environment(),
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )
    assert result.returncode == 2 and result.stdout == ""
    diagnostic = json.loads(result.stderr)
    assert diagnostic["code"] == "LIMIT_EXCEEDED"
    assert diagnostic["category"] == "resource_limit" and limit in diagnostic["message"]
    assert output.read_bytes() == b"previous artifact"
