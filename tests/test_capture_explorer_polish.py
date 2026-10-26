"""Acceptance checks for conservative ARP presentation and readable findings."""

import re
from html import unescape
from pathlib import Path

import pytest

from otarchguard.capture.explorer import CLASSIFICATION_LABELS, _diagram, generate_site
from otarchguard.capture.observations import analyze_capture
from otarchguard.capture.reconciliation import CLASSIFICATIONS
from otarchguard.explorer_html import audit_site
from tools.capture_workloads import write_pcapng


@pytest.mark.parametrize("packets, expected", [(1, "1 packet ·"), (2, "2 packets ·")])
def test_arp_panel_never_draws_target_as_observed_destination(
    tmp_path: Path, packets: int, expected: str
) -> None:
    source = tmp_path / "fixture.pcapng"
    write_pcapng(source, extended=True)
    observations = analyze_capture(source)
    flows = [f for f in observations["flows"] if f["arp"] is not None]
    for flow in flows:
        flow["packets"] = packets
    diagram = _diagram(flows, None)
    visible = unescape(re.sub("<[^>]+>", " ", diagram))
    assert "ARP request" in visible and "ARP reply" in visible
    assert "Sender IP:" in visible and "Target IP:" in visible
    assert "Ethernet destination: Broadcast" in visible
    assert "Ethernet destination: Unicast" in visible
    assert "no target presence, response or IP ownership" in visible
    assert "Observed destination" not in visible
    assert '<path class="diagram-line' not in diagram
    assert expected in visible and "packet records" not in visible


def test_human_labels_cover_exact_codes_without_replacing_json() -> None:
    assert set(CLASSIFICATION_LABELS) == set(CLASSIFICATIONS)
    assert all(label != code for code, label in CLASSIFICATION_LABELS.items())


def test_final_explorer_has_complete_links_privacy_and_dense_fallback(tmp_path: Path) -> None:
    source = tmp_path / "fixture.pcapng"
    write_pcapng(source, extended=True)
    observations = analyze_capture(source)
    output = tmp_path / "site"
    generate_site(observations, output)
    assert audit_site(output)["html_pages"] > 0
    for path in output.glob("*.html"):
        html = path.read_text(encoding="utf-8")
        assert "Sensitive network metadata" in html
        assert 'href="#main"' in html
        assert str(tmp_path) not in html
        assert "file://" not in html and "https://" not in html
        assert "fictional unsupported metadata" not in html
    hosts = (output / "hosts.html").read_text(encoding="utf-8")
    assert "ARP target-only references" in hosts
    flows = observations["flows"] * 3
    fallback = _diagram(flows, None)
    assert "Diagram omitted" in fallback and "complete paginated tables and JSON" in fallback
