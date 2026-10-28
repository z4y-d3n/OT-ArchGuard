"""Presentation contracts: local navigation, independent evidence and CLI options."""

import json
import re
import subprocess
import xml.etree.ElementTree as ET
from copy import deepcopy
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import pytest
import yaml
from typer.testing import CliRunner

from otarchguard import cli
from otarchguard.api import validate_bytes, validate_file
from otarchguard.comparison import compare_architectures
from otarchguard.diagnostics import ModelError
from otarchguard.diagrams import INTERPRETATION
from otarchguard.reporting import architecture_svg, build_report, html_report, json_report

ROOT = Path(__file__).resolve().parents[1]
runner = CliRunner()


class Navigation(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.targets: list[str] = []
        self.tables = self.captions = self.heads = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for key, value in attrs:
            if key == "id":
                assert value and value not in self.ids
                self.ids.add(value)
            if key == "href":
                assert value and re.fullmatch(r"#[a-z][a-z0-9_-]*", value)
                self.targets.append(value[1:])
            if key in {"marker-end", "clip-path"}:
                assert value and value.startswith("url(#") and value.endswith(")")
                self.targets.append(value[5:-1])
            if tag == "th":
                assert ("scope", "col") in attrs or ("scope", "row") in attrs
        self.tables += tag == "table"
        self.captions += tag == "caption"
        self.heads += tag == "thead"


@pytest.mark.parametrize(
    "family,scenario",
    [
        ("flat-plant", "plant_scope"),
        ("segmented-plant", "plant_scope"),
        ("remote-support", "support_scope"),
    ],
)
def test_unique_comparison_ids_and_local_navigation(family: str, scenario: str) -> None:
    snapshots = tuple(
        validate_file(ROOT / f"examples/{family}/{side}.yaml") for side in ("baseline", "proposed")
    )
    result = compare_architectures(snapshots[0], snapshots[1], scenario)
    report = build_report("comparison", snapshots, result)
    before = json_report(report)
    preference = (snapshots[0].model.zones[-1].id,)
    html = html_report(report, snapshots, zone_order=preference)
    assert html == html_report(report, snapshots, zone_order=preference)
    assert json_report(report) == before  # rendering cannot mutate its evidence envelope
    parser = Navigation()
    parser.feed(html.decode())
    assert set(parser.targets) <= parser.ids
    assert parser.tables == parser.captions == parser.heads > 0
    text = html.decode()
    assert INTERPRETATION in text and "@media print" in text and ":focus-visible" in text
    assert "@media(max-width:640px)" in text
    assert 'id="snapshot-0"' in text and 'id="snapshot-1"' in text
    assert "Device-to-interface attachment map" in text
    critical = text[: text.index("<svg")]
    assert f"{len(result.introduced_prohibited_violations)} interval records" in critical
    if result.introduced_prohibited_violations:
        assert "INTRODUCED prohibited violation" in critical
        assert result.introduced_prohibited_violations[0].intent_id in critical
    if result.broken_required_communications:
        assert "req_hmi_plc — FAILED" in critical
    reverse = compare_architectures(snapshots[1], snapshots[0], scenario)
    reverse_html = html_report(
        build_report("comparison", snapshots[::-1], reverse), snapshots[::-1]
    ).decode()
    assert (
        f"{len(reverse.resolved_prohibited_violations)} interval records"
        in reverse_html[: reverse_html.index("<svg")]
    )


def arguments(command: str, path: Path) -> list[str]:
    args = [command, str(path)] + ([str(path)] if command == "compare" else [])
    if command in {"compare", "exposure"}:
        args += ["--scenario", "engineering_scope"]
    return args


def test_native_ci_matrix_preserves_verification_safeguards() -> None:
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))
    assert workflow["permissions"] == {"contents": "read"}
    job = workflow["jobs"]["verify"]
    assert job["runs-on"] == "${{ matrix.os }}"
    assert job["strategy"]["fail-fast"] is False
    assert job["strategy"]["matrix"] == {
        "os": ["windows-latest", "ubuntu-latest", "macos-latest"],
        "python": ["3.12", "3.14"],
    }
    assert job["defaults"]["run"]["shell"] == "pwsh"
    steps = job["steps"]
    checkout = steps[0]
    assert checkout["with"] == {"persist-credentials": False, "fetch-depth": 0}
    runs = "\n".join(s.get("run", "") for s in steps)
    for required in (
        "EXPECTED_ROOT_SHA",
        "--max-parents=0",
        '--force-reinstall --no-index --no-deps --no-build-isolation "output/artifacts/',
        "verify_environment.py",
        "ruff check",
        "ruff format --check",
        "-m mypy",
        "pip check",
        "-m pytest",
        "examples/run_examples.py",
        "audit_release.py",
        "verify_source_checkout.py",
        "-m benchmarks.run",
    ):
        assert required in runs
    for step in steps:
        assert "continue-on-error" not in step
        if step.get("env", {}).get("OTARCHGUARD_OFFLINE_CHECK") == "1":
            assert step["env"]["PYTHONPATH"] == "${{ github.workspace }}/tools/offline"
        if "upload-artifact@" in step.get("uses", ""):
            assert "${{ matrix.os }}" in step["with"]["name"]
            assert "${{ matrix.python }}" in step["with"]["name"]
            required = step["name"] == "Retain candidate integrity evidence"
            assert step["with"]["retention-days"] == (30 if required else 7)
            if required:
                assert step["with"]["if-no-files-found"] == "error"
                assert "output/source-checkout.json" in step["with"]["path"]
    assert "-m pytest tests --basetemp=output/sdist-tmp" in runs


@pytest.mark.parametrize("command", ["validate", "check", "exposure", "compare"])
@pytest.mark.parametrize("mode", ["valid", "unknown", "duplicate", "no-report", "json"])
def test_zone_order_cli_is_presentation_only(command: str, mode: str, tmp_path: Path) -> None:
    path = ROOT / "tests/fixtures/minimal-valid.yaml"
    args = arguments(command, path)
    normal = runner.invoke(cli.app, args)
    output = tmp_path / "existing report.html"
    sentinel = b"prior artifact\x00\xff"
    output.write_bytes(sentinel)
    options = ["--zone-order", "unknown" if mode == "unknown" else "control"]
    if mode == "duplicate":
        options += ["--zone-order", "control"]
    if mode != "no-report":
        options += ["--report", str(output)]
    if mode == "json":
        options += ["--report-format", "json"]
    result = runner.invoke(cli.app, [*args, *options])
    if mode == "valid":
        assert result.exit_code == normal.exit_code == 0
        assert result.stdout == normal.stdout and not result.stderr
        assert "Effective zone order" in output.read_text(encoding="utf-8")
    else:
        assert result.exit_code == 2 and not result.stdout
        diagnostic = json.loads(result.stderr)
        assert diagnostic["category"] == "invalid_input"
        assert diagnostic["code"] == ("INVALID_REFERENCE" if mode == "unknown" else "INVALID_VALUE")
        assert output.read_bytes() == sentinel
        assert list(tmp_path.iterdir()) == [output]


def test_comparison_union_preferences_do_not_invent_zones(
    minimal: dict[str, Any], tmp_path: Path
) -> None:
    first = validate_bytes(yaml.safe_dump(minimal).encode())
    proposed = deepcopy(minimal)
    proposed["zones"].append({**proposed["zones"][0], "id": "new_zone"})
    second = validate_bytes(yaml.safe_dump(proposed).encode())
    result = compare_architectures(first, second, "engineering_scope")
    report = build_report("comparison", (first, second), result)
    html = html_report(report, (first, second), zone_order=("new_zone", "control")).decode()
    svgs = re.findall(r"<svg.*?</svg>", html)
    ns = "{http://www.w3.org/2000/svg}"
    assert [
        g.attrib["data-zone-id"] for g in ET.fromstring(svgs[0]).findall(f"{ns}g[@data-zone-id]")
    ] == ["control"]
    assert [
        g.attrib["data-zone-id"] for g in ET.fromstring(svgs[1]).findall(f"{ns}g[@data-zone-id]")
    ] == ["new_zone", "control"]
    with pytest.raises(ModelError):
        architecture_svg(first, zone_order=("new_zone",))
    with pytest.raises(ModelError):
        html_report(report, (first, second), zone_order=("control", "control"))
    for name, value in (("baseline", minimal), ("proposed", proposed)):
        (tmp_path / f"{name}.yaml").write_text(yaml.safe_dump(value), encoding="utf-8")
    run = runner.invoke(
        cli.app,
        [
            "compare",
            str(tmp_path / "baseline.yaml"),
            str(tmp_path / "proposed.yaml"),
            "--scenario",
            "engineering_scope",
            "--zone-order",
            "new_zone",
            "--report",
            str(tmp_path / "comparison.html"),
        ],
    )
    assert run.exit_code == 0 and not run.stderr


@pytest.mark.parametrize("command", ["validate", "check", "exposure", "compare"])
def test_native_installed_presentation_preserves_json_stdout(
    command: str, installed_console: Path, tmp_path: Path
) -> None:
    args = arguments(command, ROOT / "tests/fixtures/minimal-valid.yaml")
    before = subprocess.run(
        [str(installed_console), *args], capture_output=True, check=False, timeout=30
    )
    output = tmp_path / "report with spaces.html"
    after = subprocess.run(
        [str(installed_console), *args, "--zone-order", "control", "--report", str(output)],
        capture_output=True,
        check=False,
        timeout=30,
    )
    assert before.returncode == after.returncode == 0
    assert before.stdout == after.stdout and not after.stderr
    assert INTERPRETATION in output.read_text(encoding="utf-8")
