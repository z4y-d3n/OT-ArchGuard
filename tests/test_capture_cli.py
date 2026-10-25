"""Capture command and report boundaries, including preservation and offline behavior."""

import json
import socket
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
import yaml
from typer.testing import CliRunner

from otarchguard.api import validate_bytes
from otarchguard.capture.contract import CAPTURE_LIMITS
from otarchguard.capture.explorer import generate_site
from otarchguard.capture.observations import analyze_capture
from otarchguard.capture.reconciliation import compare_capture, mapping_template
from otarchguard.cli import app
from otarchguard.diagnostics import ModelError
from otarchguard.explorer_html import audit_site
from tools.capture_workloads import plant_model, write_pcap, write_pcapng

runner = CliRunner()


def test_command_help_and_structured_option_failure() -> None:
    result = runner.invoke(app, ["capture", "--help"])
    assert result.exit_code == 0
    for command in ("inspect", "analyze", "map", "compare"):
        assert command in result.stdout
    bad = runner.invoke(app, ["capture", "compare", "missing.pcap"])
    assert bad.exit_code == 2 and not bad.stdout
    assert json.loads(bad.stderr)["code"] == "INVALID_VALUE"
    unknown = runner.invoke(app, ["capture", "unknown"])
    assert unknown.exit_code == 2 and not unknown.stdout
    assert json.loads(unknown.stderr)["code"] == "INVALID_VALUE"


def test_inspect_header_detection_and_canonical_json(tmp_path: Path) -> None:
    capture = tmp_path / "capture with spaces.bin"
    write_pcapng(capture)
    first = runner.invoke(app, ["capture", "inspect", str(capture)])
    second = runner.invoke(app, ["capture", "inspect", str(capture)])
    assert first.exit_code == 0 and not first.stderr
    assert first.stdout == second.stdout
    result = json.loads(first.stdout)
    assert result["capture"]["format"] == "pcapng"
    assert result["capture"]["packets"] == 10
    assert str(tmp_path) not in first.stdout


def test_corrupted_capture_never_publishes_report(tmp_path: Path) -> None:
    source = tmp_path / "bad.pcap"
    source.write_bytes(bytes.fromhex("d4c3b2a1"))
    output = tmp_path / "site"
    result = runner.invoke(app, ["capture", "analyze", str(source), "--output", str(output)])
    assert result.exit_code == 2 and not result.stdout and not output.exists()
    assert json.loads(result.stderr)["code"] == "CAPTURE_INVALID"
    assert not list(tmp_path.glob(".otarchguard-capture-*"))


def test_output_preservation_input_alias_and_parent_links(tmp_path: Path) -> None:
    capture = tmp_path / "plant.pcap"
    write_pcap(capture)
    original = capture.read_bytes()
    result = runner.invoke(app, ["capture", "analyze", str(capture), "--output", str(capture)])
    assert result.exit_code == 2 and capture.read_bytes() == original
    output = tmp_path / "existing"
    output.mkdir()
    marker = output / "previous.txt"
    marker.write_text("keep")
    result = runner.invoke(app, ["capture", "analyze", str(capture), "--output", str(output)])
    assert result.exit_code == 2 and marker.read_text() == "keep"


@pytest.mark.parametrize("destination", ["CON", "unsafe:stream", "bad.", "bad "])
def test_unsafe_output_names(tmp_path: Path, destination: str) -> None:
    capture = tmp_path / "plant.pcap"
    write_pcap(capture)
    result = runner.invoke(
        app, ["capture", "analyze", str(capture), "--output", str(tmp_path / destination)]
    )
    assert result.exit_code == 2 and json.loads(result.stderr)["code"] == "CAPTURE_PATH"


def test_offline_report_determinism_and_complete_links(tmp_path: Path, monkeypatch: Any) -> None:
    def denied(*args: object, **kwargs: object) -> Any:
        raise AssertionError("Capture attempted networking")

    monkeypatch.setattr(socket, "socket", denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)
    capture = tmp_path / "plant.pcapng"
    write_pcapng(capture)
    for name in ("first", "second"):
        result = runner.invoke(
            app, ["capture", "analyze", str(capture), "--output", str(tmp_path / name)]
        )
        assert result.exit_code == 0 and not result.stderr, result.stderr
        assert json.loads(result.stdout)["audit"]["broken_links"] == 0
    first, second = tmp_path / "first", tmp_path / "second"
    assert {p.name: p.read_bytes() for p in first.iterdir()} == {
        p.name: p.read_bytes() for p in second.iterdir()
    }
    assert audit_site(first)["html_pages"] >= 7
    assert not list(first.glob("*.pcap*"))
    html = (first / "index.html").read_text(encoding="utf-8")
    assert "Content-Security-Policy" in html and "Sensitive network metadata" in html
    assert "<script" not in html and "https://" not in html


def test_staging_failure_and_output_budget_preserve_previous_files(tmp_path: Path) -> None:
    capture = tmp_path / "plant.pcap"
    write_pcap(capture)
    observations = analyze_capture(capture)
    output = tmp_path / "failed"
    with pytest.raises(ModelError):
        generate_site(observations, output, limits=replace(CAPTURE_LIMITS, output_bytes=100))
    assert not output.exists() and not list(tmp_path.glob(".otarchguard-capture-*"))


def test_mapping_comparison_and_hostile_review_text(tmp_path: Path) -> None:
    capture = tmp_path / "plant.pcapng"
    write_pcapng(capture)
    model = tmp_path / "model.yaml"
    model.write_text(yaml.safe_dump(plant_model()), encoding="utf-8")
    original_model = model.read_bytes()
    mapping = tmp_path / "pending.json"
    result = runner.invoke(
        app, ["capture", "map", str(capture), "--model", str(model), "--output", str(mapping)]
    )
    assert result.exit_code == 0 and not result.stderr
    review = json.loads(mapping.read_bytes())
    assert all(p["decision"] == "PENDING" for p in review["proposals"])
    payload = '<script>alert("hostile")</script>'
    for p in review["proposals"]:
        if len(p["candidates"]) == 1:
            candidate = p["candidates"][0]
            p.update(
                decision="ACCEPT",
                selected_asset_id=candidate["asset_id"],
                selected_interface_id=candidate["interface_id"],
                reviewer=payload,
                rationale=payload,
            )
    reviewed = tmp_path / "reviewed.json"
    reviewed.write_text(json.dumps(review), encoding="utf-8")
    output = tmp_path / "compared"
    result = runner.invoke(
        app,
        [
            "capture",
            "compare",
            str(capture),
            "--model",
            str(model),
            "--mapping",
            str(reviewed),
            "--output",
            str(output),
        ],
    )
    assert result.exit_code == 0 and not result.stderr, result.stderr
    comparison = json.loads((output / "comparison.json").read_bytes())
    codes = {f["classification"] for f in comparison["findings"]}
    assert {"OBSERVED_MODEL_REACHABLE", "OBSERVED_MODEL_UNREACHABLE"} <= codes
    assert model.read_bytes() == original_model
    html = "".join(p.read_text(encoding="utf-8") for p in output.glob("*.html"))
    assert payload not in html and "&lt;script&gt;" in html
    assert audit_site(output)["broken_links"] == 0


def test_pending_mapping_is_unevaluated_and_stale_mapping_fails(tmp_path: Path) -> None:
    capture = tmp_path / "plant.pcap"
    write_pcap(capture)
    observations = analyze_capture(capture)
    validated = validate_bytes(yaml.safe_dump(plant_model()).encode())
    template = mapping_template(observations, validated)
    result = compare_capture(observations, validated, template)
    assert result["work"]["native_query_pairs"] == 0
    template["capture_sha256"] = "0" * 64
    with pytest.raises(ModelError):
        compare_capture(observations, validated, template)


def test_pagination_keeps_all_evidence(tmp_path: Path) -> None:
    capture = tmp_path / "plant.pcap"
    write_pcap(capture)
    observations = analyze_capture(capture)
    result = generate_site(
        observations, tmp_path / "pages", limits=replace(CAPTURE_LIMITS, rows_per_page=2)
    )
    assert result["audit"]["broken_links"] == 0
    assert len(list((tmp_path / "pages").glob("evidence-*.html"))) == 5
