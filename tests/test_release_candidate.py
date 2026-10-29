"""Exact candidate identity and sensitivity of the narrow compatibility allowlist."""

import hashlib
import importlib.metadata
import json
import os
import subprocess
import tomllib
from pathlib import Path
from typing import Any

import pytest
import yaml

from otarchguard import __version__
from otarchguard.api import validate_file
from otarchguard.reporting import build_report
from otarchguard.trace import trace_file
from tools.compare_versioned_contract import compare_artifact, compare_captures

ROOT = Path(__file__).resolve().parents[1]
RELEASE_VERSION = "1.4.0"
ENGINE_VERSION = "1.3.0"


def test_exact_candidate_identity_and_frozen_contracts(installed_console: Path) -> None:
    assert __version__ == ENGINE_VERSION
    assert importlib.metadata.version("otarchguard") == RELEASE_VERSION
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert project["version"] == RELEASE_VERSION
    result = subprocess.run([str(installed_console), "--version"], capture_output=True, timeout=30)
    assert result.returncode == 0 and not result.stderr
    assert result.stdout.splitlines() == [RELEASE_VERSION.encode()]
    source = ROOT / "tests/fixtures/minimal-valid.yaml"
    snapshot = validate_file(source)
    assert snapshot.model.schema_version == 1
    legacy = build_report("validation", (snapshot,))
    assert legacy["engine_version"] == ENGINE_VERSION
    assert legacy["report_version"] == legacy["schema_version"] == 1
    trace = trace_file(source, "eng", "svc_plc", policy_evidence=True)
    assert trace.engine_version == ENGINE_VERSION
    assert trace.trace_version == trace.schema_version == 1


@pytest.mark.parametrize("command", ["validate", "check", "exposure", "compare", "trace"])
def test_installed_candidate_report_versions(
    command: str, installed_console: Path, tmp_path: Path
) -> None:
    source = ROOT / "tests/fixtures/minimal-valid.yaml"
    args = [command, str(source)]
    if command == "compare":
        args += [str(source)]
    if command in {"compare", "exposure"}:
        args += ["--scenario", "engineering_scope"]
    if command == "trace":
        args += ["--source", "eng", "--service", "svc_plc"]
    output = tmp_path / "candidate evidence ñ.json"
    result = subprocess.run(
        [str(installed_console), *args, "--report", str(output), "--report-format", "json"],
        env={**os.environ, "NO_COLOR": "1", "TERM": "dumb"},
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0 and not result.stderr
    for payload in (json.loads(result.stdout), json.loads(output.read_bytes())):
        assert payload["engine_version"] == ENGINE_VERSION
        assert payload["schema_version"] == 1
    report = json.loads(output.read_bytes())
    assert report["trace_version" if command == "trace" else "report_version"] == 1


def test_intent_failure_exit_remains_one(
    minimal: dict[str, Any], installed_console: Path, tmp_path: Path
) -> None:
    minimal["rules"] = []
    source = tmp_path / "failed requirement.yaml"
    source.write_text(yaml.safe_dump(minimal), encoding="utf-8")
    result = subprocess.run(
        [str(installed_console), "check", str(source)], capture_output=True, timeout=30
    )
    assert result.returncode == 1 and not result.stderr
    assert json.loads(result.stdout)["passed"] is False


def test_only_exact_root_engine_transition_is_allowed() -> None:
    before = (
        b'{"engine_version": "1.0.1", "schema_version": 1, '
        b'"result": {"engine_version": "fixture"}}\n'
    )
    after = before.replace(b'"1.0.1"', b'"1.1.0"')
    assert compare_artifact(before, after) == "ENGINE_VERSION_JSON"
    for changed in (
        after.replace(b'"fixture"', b'"1.1.0"'),
        after.replace(b'"schema_version": 1', b'"schema_version": 2'),
        after.replace(b'"schema_version": 1', b'"schema_version": true'),
        after.replace(b'"1.1.0"', b'"1.1.0rc1"'),
        after + b"\n",
    ):
        with pytest.raises(ValueError):
            compare_artifact(before, changed)


@pytest.mark.parametrize(
    "before,after", [(b"<svg>1.0.1</svg>", b"<svg>1.1.0</svg>"), (b"1.0.1\n", b"1.1.0\n")]
)
def test_arbitrary_text_and_svg_version_substitution_is_forbidden(
    before: bytes, after: bytes
) -> None:
    with pytest.raises(ValueError):
        compare_artifact(before, after)


def test_html_allowlist_is_confined_to_appendix_and_exact_trace_header() -> None:
    before = (
        b"<!doctype html><p>fixture 1.0.1</p>"
        b"<p>Status: complete; trace version 1; engine 1.0.1; schema 1.</p>"
        b'<section id="json"><pre>{&quot;engine_version&quot;: &quot;1.0.1&quot;, '
        b"&quot;trace_version&quot;: 1}</pre></details></section></main>"
    )
    after = before.replace(b"engine 1.0.1;", b"engine 1.1.0;").replace(
        b"&quot;engine_version&quot;: &quot;1.0.1&quot;",
        b"&quot;engine_version&quot;: &quot;1.1.0&quot;",
    )
    assert compare_artifact(before, after) == "ENGINE_VERSION_HTML"
    for changed in (
        after.replace(b"fixture 1.0.1", b"fixture 1.1.0"),
        after.replace(b"&quot;trace_version&quot;: 1", b"&quot;trace_version&quot;: 2"),
    ):
        with pytest.raises(ValueError):
            compare_artifact(before, changed)


@pytest.mark.parametrize("wrong_exit", [False, 0.0])
def test_capture_exit_code_types_are_not_normalized(tmp_path: Path, wrong_exit: object) -> None:
    before, after = tmp_path / "baseline", tmp_path / "candidate"
    for folder, version in ((before, "1.0.1"), (after, "1.1.0")):
        folder.mkdir()
        artifact = json.dumps({"engine_version": version, "schema_version": 1}).encode()
        (folder / "validate.stdout").write_bytes(artifact)
        record = {
            "python": "3.12",
            "platform": "test",
            "production_sha256": {"__init__.py": version, "cli.py": "same"},
            "inputs": {"minimal": {"input_sha256": "same", "model_sha256": "same"}},
            "exits": {"validate": 0},
            "artifacts": {"validate.stdout": hashlib.sha256(artifact).hexdigest()},
        }
        (folder / "manifest.json").write_text(json.dumps(record), encoding="utf-8")
    assert compare_captures(before, after)["status"] == "PASS"
    manifest = after / "manifest.json"
    changed = json.loads(manifest.read_bytes())
    changed["exits"]["validate"] = wrong_exit
    manifest.write_text(json.dumps(changed), encoding="utf-8")
    with pytest.raises(ValueError, match="Changed capture exits"):
        compare_captures(before, after)
