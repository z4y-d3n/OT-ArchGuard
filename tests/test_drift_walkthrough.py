"""Independent literal longitudinal fixture and installed API walkthrough oracles."""

import json
from pathlib import Path

from otarchguard.capture.observations import analyze_capture
from otarchguard.capture.protocols import enrich_capture
from tools.drift_walkthrough import scenario, write_fictional_capture


def test_independent_packet_fixture_has_exact_directional_relationships(tmp_path: Path) -> None:
    reference, candidate = tmp_path / "reference.pcap", tmp_path / "candidate.pcap"
    write_fictional_capture(reference)
    write_fictional_capture(candidate, candidate=True)
    expected_reference = {
        ("192.0.2.11", 41000, "192.0.2.20", 502),
        ("192.0.2.10", 42000, "192.0.2.20", 502),
    }
    expected_candidate = {
        ("192.0.2.11", 41000, "192.0.2.20", 502),
        ("192.0.2.99", 43000, "192.0.2.20", 502),
    }
    for path, expected in ((reference, expected_reference), (candidate, expected_candidate)):
        observations = analyze_capture(path)
        actual = {
            (f["source_ip"], f["source_port"], f["destination_ip"], f["destination_port"])
            for f in observations["flows"]
        }
        assert actual == expected
        assert all(f["packets"] == 1 for f in observations["flows"])
    assert {r["message_category"] for r in enrich_capture(reference)["records"]} == {"read_type"}
    assert {r["message_category"] for r in enrich_capture(candidate)["records"]} == {
        "read_type",
        "write_type",
    }


def test_complete_installed_drift_walkthrough_preserves_sources_and_revokes(tmp_path: Path) -> None:
    output = tmp_path / "fictional-walkthrough"
    receipt = scenario(output)
    assert receipt["status"] == "passed"
    assert receipt["independent_identity_oracle"] is True
    assert receipt["byte_identical_reproduction"] is True
    assert receipt["workspace_unchanged_by_comparison"] is True
    assert receipt["revoked_reference_rejected"] is True
    report = json.loads((output / "drift.json").read_bytes())
    findings = report["comparisons"][0]["findings"]
    categories = {(finding["category"], finding["subtype"]) for finding in findings}
    assert ("OBSERVED_COMMUNICATION_DIFFERENCE", "REFERENCE_ONLY_OBSERVATION") in categories
    assert ("OBSERVED_COMMUNICATION_DIFFERENCE", "CANDIDATE_ONLY_OBSERVATION") in categories
    assert ("OBSERVED_COMMUNICATION_DIFFERENCE", "OBSERVED_IN_BOTH") in categories
    assert any(category == "PROTOCOL_METADATA_DIFFERENCE" for category, _ in categories)
    assert report["comparisons"][0]["comparability"]["asset_continuity"] == "INDETERMINATE"
    incomplete = json.loads((output / "incomplete-drift.json").read_bytes())
    dimensions = incomplete["comparisons"][0]["comparability"]["dimensions"]
    assert any(d["result"] != "COMPARABLE" and "packet" in d["dimension"] for d in dimensions)
    analytical = json.loads((output / "decoder_one-drift.json").read_bytes())
    assert analytical["comparisons"][0]["comparability"]["independent_collections"] is False
    assert any(
        f["category"] == "ANALYTICAL_INTERPRETATION_DIFFERENCE"
        and f["subtype"] == "PROTOCOL_SEMANTICS_CHANGED"
        for f in analytical["comparisons"][0]["findings"]
    )
