"""Independent publication and finding-to-evidence acceptance checks."""

import re
from dataclasses import replace
from html import unescape
from pathlib import Path
from typing import Any

import pytest
import yaml

from otarchguard.api import validate_bytes
from otarchguard.capture import explorer
from otarchguard.capture.contract import CAPTURE_LIMITS
from otarchguard.capture.observations import analyze_capture
from otarchguard.capture.reconciliation import compare_capture, mapping_template
from otarchguard.diagnostics import ModelError
from otarchguard.explorer_html import PageAudit, audit_site
from tools.capture_workloads import plant_model, write_pcap


def _comparison(tmp_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    source = tmp_path / "fixture.pcap"
    write_pcap(source)
    observations = analyze_capture(source)
    model = validate_bytes(yaml.safe_dump(plant_model()).encode())
    review = mapping_template(observations, model)
    for proposal in review["proposals"]:
        if len(proposal["candidates"]) == 1:
            candidate = proposal["candidates"][0]
            proposal.update(
                decision="ACCEPT",
                selected_asset_id=candidate["asset_id"],
                selected_interface_id=candidate["interface_id"],
                reviewer="independent-fictional-fixture",
                rationale="Synthetic fixture only; not operational identity approval.",
            )
    return observations, compare_capture(observations, model, review)


@pytest.mark.parametrize("rows_per_page", [2, 100])
def test_finding_rows_link_to_exact_underlying_evidence(tmp_path: Path, rows_per_page: int) -> None:
    observations, comparison = _comparison(tmp_path)
    output = tmp_path / "report"
    explorer.generate_site(
        observations,
        output,
        comparison,
        limits=replace(CAPTURE_LIMITS, rows_per_page=rows_per_page),
    )
    targets: list[str] = []
    for page in output.glob("findings*.html"):
        audit = PageAudit()
        audit.feed(page.read_text(encoding="utf-8"))
        targets.extend(audit.links)
    # A reviewer investigating a finding must not have to search an opaque digest
    # in a separate table. Each finding needs a precise evidence destination.
    for finding in comparison["findings"]:
        assert any(target.endswith("#flow-" + finding["flow_id"]) for target in targets)


def test_diagram_separates_packet_directions_and_exposes_exact_flow_evidence(
    tmp_path: Path,
) -> None:
    observations, comparison = _comparison(tmp_path)
    output = tmp_path / "lanes"
    explorer.generate_site(observations, output, comparison)
    page = (output / "index.html").read_text(encoding="utf-8")
    audit = PageAudit()
    audit.feed(page)
    diagram = page.split("<svg", 1)[1].split("</svg>", 1)[0]
    visible = unescape(re.sub("<[^>]+>", " ", diagram))
    rendered = [
        flow for flow in observations["flows"] if flow["source_ip"] and flow["destination_ip"]
    ]
    for flow in rendered:
        assert flow["source_ip"] in visible and flow["destination_ip"] in visible
        assert flow["transport"] in visible
        assert any(target.endswith("#flow-" + flow["id"]) for target in audit.links)
        if flow["source_port"] is not None and flow["destination_port"] is not None:
            assert f"{flow['source_port']} → {flow['destination_port']}" in visible
    # A separate horizontal segment per aggregate prevents shared return corridors
    # from making direction or relationship multiplicity visually indistinguishable.
    directions = re.findall(
        r'<path class="diagram-line documentary" d="M (\d+) (\d+) H (\d+)"', diagram
    )
    assert len(directions) == len(rendered)
    assert len({y for _, y, _ in directions}) == len(rendered)
    assert all(int(end) > int(start) for start, _, end in directions)
    assert "Observed source" in visible and "Observed destination" in visible
    assert "viewBox=" in diagram
    assert "aria-labelledby=" in diagram
    assert "not authorization" in visible


def test_output_appearing_during_staging_is_preserved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    observations, comparison = _comparison(tmp_path)
    output = tmp_path / "appeared"
    marker = output / "external-owner.txt"
    original_audit = audit_site

    def competing_destination(stage: Path) -> dict[str, int]:
        result = original_audit(stage)
        output.mkdir()
        marker.write_bytes(b"independent concurrent writer")
        return result

    monkeypatch.setattr(explorer, "audit_site", competing_destination)
    with pytest.raises(ModelError):
        explorer.generate_site(observations, output, comparison)
    assert marker.read_bytes() == b"independent concurrent writer"
    assert list(output.iterdir()) == [marker]
    assert not list(tmp_path.glob(".otarchguard-capture-*"))


def test_audit_failure_never_publishes_partial_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    observations, comparison = _comparison(tmp_path)
    output = tmp_path / "audit-rejected"

    def reject(stage: Path) -> dict[str, int]:
        assert (stage / "observations.json").is_file()
        raise ValueError("independent audit refusal")

    monkeypatch.setattr(explorer, "audit_site", reject)
    with pytest.raises(ValueError, match="independent audit refusal"):
        explorer.generate_site(observations, output, comparison)
    assert not output.exists()
    assert not list(tmp_path.glob(".otarchguard-capture-*"))
