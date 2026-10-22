"""Regress Windows venv and base-runner layouts using a genuine installed launcher."""

import json
import os
import runpy
import shutil
import subprocess
import sys
import sysconfig
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("layout", ["venv", "windows_runner"])
@pytest.mark.parametrize("caller", ["fixture", "walkthrough"])
def test_installed_launcher_uses_scripts_scheme_in_both_windows_layouts(
    layout: str,
    caller: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
) -> None:
    name = "otarchguard.exe" if os.name == "nt" else "otarchguard"
    installed = Path(sysconfig.get_path("scripts")) / name
    assert installed.is_file(), f"Real installed launcher required: {installed}"
    scripts = tmp_path / "Python installation with spaces" / "Scripts"
    scripts.mkdir(parents=True)
    interpreter = (scripts if layout == "venv" else scripts.parent) / "python.exe"
    interpreter.write_bytes(b"Layout placeholder; never executed")
    launcher = scripts / name
    # Preserve pip's real launcher and its embedded interpreter, not a test command stub.
    shutil.copy2(installed, launcher)
    if layout == "windows_runner":
        interpreter.with_name(name).write_bytes(b"Wrong sibling launcher; never execute")
    monkeypatch.setattr(sys, "executable", str(interpreter))
    monkeypatch.setattr(sysconfig, "get_path", lambda name: str(scripts))
    monkeypatch.setenv("PATH", str(tmp_path / "unrelated PATH"))

    if caller == "fixture":
        resolved = request.getfixturevalue("installed_console")
        assert resolved == launcher
        result = subprocess.run(
            [str(resolved), "validate", str(ROOT / "tests/fixtures/minimal-valid.yaml")],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
            timeout=20,
        )
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout)["status"] == "valid" and not result.stderr
    else:
        namespace = runpy.run_path(str(ROOT / "examples/run_examples.py"))
        run = cast(Callable[[list[str], int], dict[str, object]], namespace["run"])
        assert (
            run(["validate", str(ROOT / "tests/fixtures/minimal-valid.yaml")], 0)["status"]
            == "valid"
        )


@pytest.mark.parametrize("caller", ["fixture", "walkthrough"])
def test_missing_installed_launcher_fails_without_path_or_module_fallback(
    caller: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest
) -> None:
    # The real launcher remains available elsewhere; an absent scheme launcher must fail.
    monkeypatch.setattr(sysconfig, "get_path", lambda name: str(tmp_path))
    if caller == "fixture":
        with pytest.raises(AssertionError, match="Installed console launcher missing"):
            request.getfixturevalue("installed_console")
    else:
        namespace = runpy.run_path(str(ROOT / "examples/run_examples.py"))
        run = cast(Callable[[list[str], int], dict[str, object]], namespace["run"])
        with pytest.raises(FileNotFoundError, match="Installed console launcher missing"):
            run(["--help"], 0)
