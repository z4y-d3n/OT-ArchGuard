"""Public offline command workflow and one-acquisition comparison boundary."""

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from otarchguard.cli import app
from otarchguard.drift.engine import compare
from otarchguard.evidence import lifecycle
from tools.drift_walkthrough import comparison_context, prepare


@pytest.fixture
def selected(tmp_path: Path) -> dict[str, Any]:
    return prepare(tmp_path / "fictional", variations=False)


def test_complete_cli_workflow_and_human_summary(selected: dict[str, Any]) -> None:
    root = Path(selected["workspace"]).parent
    reference = selected["periods"]["reference"]["analysis_id"]
    candidate = selected["periods"]["candidate"]["analysis_id"]
    context = root / "comparison-context.json"
    context.write_text(json.dumps(comparison_context(reference, candidate, selected["scope"])))
    output = root / "result.json"
    runner = CliRunner()
    arguments = [
        "evidence",
        "drift",
        "compare",
        selected["workspace"],
        selected["baseline_id"],
        "--candidate",
        candidate,
        "--context",
        str(context),
        "--output",
        str(output),
    ]
    result = runner.invoke(app, arguments)
    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    assert json.loads(output.read_bytes()) == report
    for command in ("verify", "inspect", "summarize"):
        checked = runner.invoke(
            app, ["evidence", "drift", command, selected["workspace"], str(output)]
        )
        assert checked.exit_code == 0, checked.output
        if command == "verify":
            assert json.loads(checked.stdout)["canonical_reproduction"] is True
        elif command == "summarize":
            assert "Current baseline status: APPROVED" in checked.stdout
            assert "No incident" in checked.stdout
    before = output.read_bytes()
    rejected = runner.invoke(app, arguments)
    assert rejected.exit_code == 2
    assert json.loads(rejected.stderr)["code"] == "EVIDENCE_EXISTS"
    assert output.read_bytes() == before


@pytest.mark.parametrize(
    "arguments",
    [
        ["evidence", "drift", "compare", "--force-comparable"],
        ["evidence", "drift", "invented"],
        ["evidence", "drift", "verify"],
        ["evidence", "drift", "summarize", "--unknown"],
    ],
)
def test_command_usage_errors_are_structured(arguments: list[str]) -> None:
    result = CliRunner().invoke(app, arguments)
    assert result.exit_code == 2
    assert json.loads(result.stderr)["code"] == "INVALID_VALUE"


def test_compare_acquires_trusted_lifecycle_once(
    selected: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = lifecycle._operation
    acquisitions = 0

    def counted(path: Path) -> Any:
        nonlocal acquisitions
        acquisitions += 1
        return original(path)

    monkeypatch.setattr(lifecycle, "_operation", counted)
    reference = selected["periods"]["reference"]["analysis_id"]
    candidate = selected["periods"]["candidate"]["analysis_id"]
    compare(
        Path(selected["workspace"]),
        selected["baseline_id"],
        [candidate],
        comparison_context(reference, candidate, selected["scope"]),
    )
    assert acquisitions == 1
