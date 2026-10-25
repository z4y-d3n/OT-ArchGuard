"""Boundary acceptance and fail-closed resource tests, independent of RSS internals."""

from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
import yaml
from typer.testing import CliRunner

from benchmarks.capture import write_boundary_workload
from otarchguard.api import validate_bytes
from otarchguard.capture import cli as capture_cli
from otarchguard.capture.contract import CAPTURE_LIMITS
from otarchguard.capture.explorer import generate_site
from otarchguard.capture.observations import analyze_capture
from otarchguard.capture.reconciliation import compare_capture, mapping_template
from otarchguard.cli import app
from otarchguard.diagnostics import ModelError
from otarchguard.domain import PortInterval
from otarchguard.reachability import IntervalResult, ReachabilityEngine


@pytest.mark.parametrize("workload", ["maxframe-64", "metadata-sections-256"])
def test_boundary_workload_bytes_and_observations_are_deterministic(
    tmp_path: Path, workload: str
) -> None:
    first, second = tmp_path / "first.pcap", tmp_path / "second.pcap"
    write_boundary_workload(first, workload, 2)
    write_boundary_workload(second, workload, 2)
    assert first.read_bytes() == second.read_bytes()
    observed = analyze_capture(first)
    assert observed == analyze_capture(second)
    if workload == "maxframe-64":
        assert observed["capture"]["packets"] == 2
        assert observed["capture"]["captured_bytes"] == 2 * CAPTURE_LIMITS.packet_bytes
        assert observed["coverage"]["unsupported"] == 2
        assert observed["flows"][0]["destination_port"] is None
        assert observed["flows"][0]["initiation_evidence"] == []
    else:
        assert observed["capture"]["packets"] == 0
        assert len(observed["capture"]["interfaces"]) == 2
        assert [i["section"] for i in observed["capture"]["interfaces"]] == [0, 1]
        assert observed["hosts"] == observed["flows"] == []
    site = generate_site(observed, tmp_path / "accepted-site")
    assert site["audit"]["broken_links"] == 0
    assert not list((tmp_path / "accepted-site").rglob("*.pcap*"))


@pytest.mark.parametrize(
    "workload,field,maximum,diagnostic",
    [
        ("maxframe-64", "packet_bytes", 16, "capture_packet_bytes"),
        ("maxframe-64", "packets", 1, "capture_packets"),
        ("metadata-sections-256", "interfaces", 1, "capture_interfaces"),
        ("metadata-sections-256", "metadata_bytes", 32, "capture_metadata_bytes"),
        ("metadata-sections-256", "block_bytes", 32, "capture_block_bytes"),
    ],
)
def test_boundary_resource_rejection_publishes_no_partial_site(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    workload: str,
    field: str,
    maximum: int,
    diagnostic: str,
) -> None:
    capture, output = tmp_path / "boundary.pcap", tmp_path / "rejected-site"
    write_boundary_workload(capture, workload, 2)
    before = capture.read_bytes()
    sentinel = tmp_path / "existing-output.txt"
    sentinel.write_text("Retain existing user data", encoding="utf-8")
    limits = replace(CAPTURE_LIMITS, **{field: maximum})

    def limited(path: Path) -> dict[str, Any]:
        return analyze_capture(path, limits)

    monkeypatch.setattr(capture_cli, "analyze_capture", limited)
    result = CliRunner().invoke(app, ["capture", "analyze", str(capture), "--output", str(output)])
    assert result.exit_code == 2
    assert "resource_limit" in result.output and diagnostic in result.output
    assert not output.exists()
    assert not list(tmp_path.glob(".otarchguard-capture-*"))
    assert capture.read_bytes() == before
    assert sentinel.read_text(encoding="utf-8") == "Retain existing user data"


def test_capture_native_budget_stops_before_retaining_all_intervals(
    tmp_path: Path, minimal: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    # Three intervals fit native work limits, but the first interval exceeds the
    # deliberately tiny capture evidence budget. Only one atom may be evaluated.
    # This fails against the earlier full-QueryResult-before-budget behavior.
    from tools.capture_workloads import write_pcap

    capture = tmp_path / "native.pcap"
    write_pcap(capture, count=1)
    observations = analyze_capture(capture)
    minimal["services"][0]["destination_ports"] = [{"start": 501, "end": 503}]
    model = validate_bytes(yaml.safe_dump(minimal).encode())
    review = mapping_template(observations, model)
    for proposal in review["proposals"]:
        candidate = proposal["candidates"][0]
        proposal.update(
            decision="ACCEPT",
            selected_asset_id=candidate["asset_id"],
            selected_interface_id=candidate["interface_id"],
            reviewer="Reviewer B",
            rationale="Synthetic allocation boundary test.",
        )
    original, calls = ReachabilityEngine._atom, []

    def count_atom(
        self: ReachabilityEngine, source: str, service: str, atom: PortInterval
    ) -> IntervalResult:
        calls.append((atom.start, atom.end))
        return original(self, source, service, atom)

    monkeypatch.setattr(ReachabilityEngine, "_atom", count_atom)
    with pytest.raises(ModelError) as caught:
        compare_capture(
            observations, model, review, replace(CAPTURE_LIMITS, aggregation_bytes=2048)
        )
    assert caught.value.diagnostics[0].category == "resource_limit"
    assert "capture_native_evidence_bytes" in caught.value.diagnostics[0].message
    assert len(calls) == 1
