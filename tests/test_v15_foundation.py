"""First-run diagnostics and retained verification for v1.5 development."""

import fnmatch
import importlib
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
TUTORIALS = (
    "evidence_history_walkthrough",
    "drift_walkthrough",
    "historical_explorer_walkthrough",
)


@pytest.mark.parametrize("tutorial", TUTORIALS)
@pytest.mark.parametrize(
    "case", ["missing_parent", "existing_directory", "existing_file", "file_parent"]
)
def test_tutorial_cli_explains_destination_errors_without_writes(
    tmp_path: Path, tutorial: str, case: str
) -> None:
    retained = tmp_path / "retained"
    retained.mkdir()
    marker = retained / "owner.txt"
    marker.write_bytes(b"existing user data\n")
    output = {
        "missing_parent": tmp_path / "absent" / "new",
        "existing_directory": retained,
        "existing_file": marker,
        "file_parent": marker / "new",
    }[case]
    before = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    result = subprocess.run(
        [sys.executable, "-m", "tools." + tutorial, "--output", str(output)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 2
    assert result.stdout == ""
    assert "Traceback" not in result.stderr
    if case in {"existing_directory", "existing_file"}:
        assert "choose a fresh destination" in result.stderr
    else:
        assert "create the parent directory first" in result.stderr
    assert before == {
        p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()
    }
    assert sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*")) == [
        "retained",
        "retained/owner.txt",
    ]


@pytest.mark.parametrize("tutorial", TUTORIALS)
def test_tutorial_cli_accepts_relative_fresh_destination(
    tmp_path: Path,
    tutorial: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = importlib.import_module("tools." + tutorial)
    (tmp_path / "output").mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", [tutorial, "--output", "output/new"])
    selected: list[Path] = []

    def scenario(output: Path) -> dict[str, Any]:
        selected.append(output)
        output.mkdir(exist_ok=False)
        return {"status": "passed", "verification": {}, "drift_id": "fixture", "scenarios": {}}

    monkeypatch.setattr(module, "walkthrough" if tutorial == TUTORIALS[0] else "scenario", scenario)
    module.main()
    assert selected == [tmp_path / "output/new"]
    assert (tmp_path / "output/new").is_dir()
    assert capsys.readouterr().err == ""


def test_v15_branch_triggers_the_preserved_six_job_matrix() -> None:
    # BaseLoader avoids YAML 1.1 treating GitHub's literal `on` key as a boolean.
    workflow = yaml.load((ROOT / ".github/workflows/ci.yml").read_text(), Loader=yaml.BaseLoader)
    branches = workflow["on"]["push"]["branches"]
    assert any(
        fnmatch.fnmatchcase("codex/v15-01-product-consolidation-foundation", b) for b in branches
    )
    assert workflow["on"]["pull_request"]["branches"] == ["v1.2", "main"]
    matrix = workflow["jobs"]["verify"]["strategy"]["matrix"]
    assert matrix == {
        "os": ["windows-latest", "ubuntu-latest", "macos-latest"],
        "python": ["3.12", "3.14"],
    }
