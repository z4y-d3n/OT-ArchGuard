"""Installed-distribution import workflow and controlled failures."""

import json
import os
import subprocess
from pathlib import Path
from typing import Any, cast

import pytest
from typer.testing import CliRunner

from otarchguard.cli import app
from otarchguard.ingestion.records import ImportDraft, MappingProfile
from otarchguard.ingestion.workflow import create_draft, load_record, serialize

EXAMPLES = Path(__file__).resolve().parents[1] / "examples/import-studio"
runner = CliRunner(env={"NO_COLOR": "1", "TERM": "dumb"})


@pytest.mark.parametrize("command", ["inspect", "preview", "map", "review", "emit"])
def test_import_help(command: str) -> None:
    result = runner.invoke(app, ["import", command, "--help"])
    assert result.exit_code == 0 and "Usage:" in result.stdout


def test_installed_end_to_end_owner_review(tmp_path: Path, installed_console: Path) -> None:
    def invoke(*args: str, expected: int = 0) -> dict[str, Any]:
        result = subprocess.run(
            [str(installed_console), *args],
            cwd=tmp_path,
            capture_output=True,
            env={**os.environ, "NO_COLOR": "1", "TERM": "dumb"},
            timeout=30,
        )
        assert result.returncode == expected, result.stderr.decode()
        assert not result.stderr if expected == 0 else not result.stdout
        return cast(dict[str, Any], json.loads(result.stdout if expected == 0 else result.stderr))

    source = tmp_path / "inventário con espacios.csv"
    source.write_bytes((EXAMPLES / "assets.csv").read_bytes())
    source_before = source.read_bytes()
    profile = str(EXAMPLES / "assets-profile.yaml")
    inspected = invoke("import", "inspect", str(source))
    assert inspected["collections"][0]["rows"] == 2
    previewed = invoke("import", "preview", str(source), "--profile", profile)
    assert previewed["state"] == "UNRESOLVED" and not previewed["conflicts"]
    draft = tmp_path / "draft.json"
    invoke("import", "map", str(source), "--profile", profile, "--output", str(draft))
    saved_draft = draft.read_bytes()
    error = invoke(
        "import", "map", str(source), "--profile", profile, "--output", str(draft), expected=2
    )
    assert error["code"] == "IMPORT_OUTPUT" and draft.read_bytes() == saved_draft
    decisions = tmp_path / "decisions.json"
    review = invoke(
        "import",
        "review",
        str(draft),
        "--decisions",
        str(decisions),
        "--context",
        str(EXAMPLES / "model-context.yaml"),
    )
    assert review["draft_sha256"] == previewed["draft_sha256"]
    output = tmp_path / "accepted architecture"
    error = invoke(
        "import",
        "emit",
        str(draft),
        "--source",
        str(source),
        "--decisions",
        str(decisions),
        "--output",
        str(output),
        expected=2,
    )
    assert error["code"] == "IMPORT_REVIEW" and not output.exists()
    # A synthetic owner acts only inside this test; production never auto-confirms.
    value = json.loads(decisions.read_bytes())
    value.update(
        reviewer="Synthetic owner",
        model_confirmed=True,
        model_rationale="Reviewed finite synthetic inventory and its omissions.",
    )
    for resolution in value["resolutions"]:
        resolution.update(decision="OWNER_CONFIRMED", rationale="Reviewed this synthetic row.")
    decisions.write_text(json.dumps(value), encoding="utf-8")
    emitted = invoke(
        "import",
        "emit",
        str(draft),
        "--source",
        str(source),
        "--decisions",
        str(decisions),
        "--output",
        str(output),
    )
    validated = invoke("validate", str(output / "architecture.yaml"))
    assert emitted["model_sha256"] == validated["model_sha256"]
    assert invoke("check", str(output / "architecture.yaml"))["passed"] is True
    # No intents were declared; this success does not establish connectivity.
    assert source.read_bytes() == source_before and draft.read_bytes() == saved_draft
    before = {p.name: p.read_bytes() for p in output.iterdir()}
    invoke(
        "import",
        "emit",
        str(draft),
        "--source",
        str(source),
        "--decisions",
        str(decisions),
        "--output",
        str(output),
        expected=2,
    )
    assert before == {p.name: p.read_bytes() for p in output.iterdir()}


@pytest.mark.parametrize("suffix", [".csv", ".tsv"])
def test_actual_cli_csv_and_tsv(tmp_path: Path, suffix: str) -> None:
    source = tmp_path / ("source" + suffix)
    delimiter = "\t" if suffix == ".tsv" else ","
    source.write_text(f"id{delimiter}name\na{delimiter}Controller\n", encoding="utf-8-sig")
    profile = tmp_path / "profile.json"
    profile.write_bytes(
        serialize(
            MappingProfile(
                profile_version=1,
                entity="asset",
                fields={"id": "id", "name": "name"},
            )
        )
    )
    result = runner.invoke(app, ["import", "preview", str(source), "--profile", str(profile)])
    assert result.exit_code == 0
    assert len(json.loads(result.stdout)["candidates"]) == 1


def test_cli_bad_input_leaves_existing_output_and_no_traceback(tmp_path: Path) -> None:
    source = tmp_path / "bad.csv"
    source.write_bytes(b"id,id\na,b\n")
    output = tmp_path / "draft.json"
    output.write_bytes(b"keep")
    result = runner.invoke(
        app,
        [
            "import",
            "map",
            str(source),
            "--profile",
            str(EXAMPLES / "assets-profile.yaml"),
            "--output",
            str(output),
        ],
    )
    assert result.exit_code == 2 and not result.stdout
    assert json.loads(result.stderr)["code"] == "IMPORT_HEADER"
    assert "Traceback" not in result.output and output.read_bytes() == b"keep"


def test_review_without_output_does_not_write(tmp_path: Path) -> None:
    profile = load_record(EXAMPLES / "assets-profile.yaml", MappingProfile)
    draft = create_draft(EXAMPLES / "assets.csv", profile)
    path = tmp_path / "draft.json"
    path.write_bytes(serialize(draft))
    result = runner.invoke(app, ["import", "review", str(path)])
    assert result.exit_code == 0 and list(tmp_path.iterdir()) == [path]
    assert load_record(path, ImportDraft) == draft


def test_hostile_label_is_serialized_as_inert_text(tmp_path: Path) -> None:
    path = tmp_path / "labels.csv"
    path.write_text("id,name\na,<svg onload=alert(1)>\n", encoding="utf-8")
    profile = tmp_path / "profile.json"
    profile.write_bytes(
        serialize(
            MappingProfile(
                profile_version=1,
                entity="asset",
                fields={"id": "id", "name": "name"},
            )
        )
    )
    result = runner.invoke(app, ["import", "preview", str(path), "--profile", str(profile)])
    assert result.exit_code == 0 and json.loads(result.stdout)["state"] == "UNRESOLVED"
    assert result.stdout.startswith("{")  # JSON evidence; no HTML/SVG renderer involved.
