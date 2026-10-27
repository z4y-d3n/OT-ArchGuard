"""Independent fictional wire oracles for finite-capture historical differences."""

import copy
import json
import struct
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from otarchguard.capture.observations import analyze_capture
from otarchguard.capture.protocols import enrich_capture
from otarchguard.diagnostics import ModelError
from otarchguard.drift.communications import compare_communications
from otarchguard.drift.comparability import assess, compare_coverage
from otarchguard.drift.contract import DRIFT_LIMITS, Budget, Side
from otarchguard.drift.protocols import compare_protocols
from otarchguard.evidence.attachments import build_attachment
from otarchguard.evidence.observations import digest
from otarchguard.evidence.revisions import build_revision
from otarchguard.evidence.workspace import build_snapshot
from tools.capture_workloads import plant_model
from tools.protocol_workloads import ethernet, seven_frames

SCOPE = {
    "environment": "fictional training segment",
    "purpose": "selected capture relationship comparison",
    "coverage": "finite packet files; collection loss unknown",
    "uncertainties": [],
    "vantage_points": ["fictional span A"],
    "protocols": ["tcp"],
}


def _frame(source: int = 11, port: int = 41000, function: int = 3) -> bytes:
    # Ethernet, IPv4, TCP and Modbus layouts authored without the product decoder.
    payload = bytes.fromhex("00010000000601") + bytes([function]) + bytes.fromhex("00000001")
    tcp = struct.pack("!HHIIBBHHH", port, 502, 1, 0, 0x50, 0x18, 1024, 0, 0) + payload
    ip = struct.pack(
        "!BBHHHBBH4s4s",
        0x45,
        0,
        20 + len(tcp),
        1,
        0,
        64,
        6,
        0,
        bytes([192, 0, 2, source]),
        bytes([192, 0, 2, 20]),
    )
    return ethernet(ip + tcp)


def _capture(path: Path, frames: list[bytes], ticks: int = 0) -> None:
    header = struct.pack("<IHHIIII", 0xA1B23C4D, 2, 4, 0, 0, 65535, 1)
    path.write_bytes(
        header
        + b"".join(
            struct.pack("<IIII", 2000000000, ticks + i, len(frame), len(frame)) + frame
            for i, frame in enumerate(frames)
        )
    )


def _side(path: Path, frames: list[bytes], ticks: int = 0, legacy: bool = False) -> Side:
    _capture(path, frames, ticks)
    snapshot = build_snapshot(analyze_capture(path))
    enriched = enrich_capture(path)
    if legacy:
        enriched["decoder_version"] = 1
        enriched["supported_protocols"] = ["modbus_tcp", "profinet_dcp"]
        enriched["enrichment_sha256"] = digest(
            {k: v for k, v in enriched.items() if k != "enrichment_sha256"}
        )
    attachments = {"enrichment": build_attachment("enrichment", enriched, snapshot)}
    return Side(build_revision(snapshot, attachments), snapshot, attachments)


def _assessment(reference: Side, candidate: Side, **scope: Any) -> dict[str, Any]:
    return assess(reference, candidate, SCOPE, SCOPE | scope, "asserted", Budget())


def test_same_collection_is_not_independent_evidence(tmp_path: Path) -> None:
    side = _side(tmp_path / "same.pcap", [_frame()])
    assessment = _assessment(side, side)
    assert assessment["independent_collections"] is False
    assert assessment["temporal_order"] == "SAME_COLLECTION"
    assert assessment["communication_metadata"] == "COMPARABLE"
    assert assessment["asset_continuity"] == "INDETERMINATE"
    findings = compare_communications(side, side, assessment, Budget())
    assert [f["subtype"] for f in findings] == ["OBSERVED_IN_BOTH"]
    assert compare_protocols(side, side, assessment, Budget()) == []


def test_independent_directional_difference_oracle_and_protocol_category(tmp_path: Path) -> None:
    reference = _side(tmp_path / "reference.pcap", [_frame(), _frame(10, 42000)])
    candidate = _side(tmp_path / "candidate.pcap", [_frame(function=6), _frame(99, 43000)], 100)
    assessment = _assessment(reference, candidate)
    findings = compare_communications(reference, candidate, assessment, Budget())
    by_source = {f["key"]["source_ip"]: f for f in findings}
    assert {key: value["subtype"] for key, value in by_source.items()} == {
        "192.0.2.10": "REFERENCE_ONLY_OBSERVATION",
        "192.0.2.11": "OBSERVED_IN_BOTH",
        "192.0.2.99": "CANDIDATE_ONLY_OBSERVATION",
    }
    assert by_source["192.0.2.10"]["candidate"] is None
    assert by_source["192.0.2.99"]["reference"] is None
    retained = by_source["192.0.2.99"]["candidate"]
    assert retained["source"]["capture_sha256"] == candidate.analysis["capture_sha256"]
    assert retained["packet_references"][0]["packet"]["index"] == 2
    protocols = compare_protocols(reference, candidate, assessment, Budget())
    common = [f for f in protocols if f["key"]["source_ip"] == "192.0.2.11"]
    assert {(f["subtype"], f["key"]["message_category"]) for f in common} == {
        ("REFERENCE_ONLY_METADATA", "read_type"),
        ("CANDIDATE_ONLY_METADATA", "write_type"),
    }
    assert all(f["category"] == "PROTOCOL_METADATA_DIFFERENCE" for f in protocols)


def test_reversed_comparison_reverses_only_side_labels(tmp_path: Path) -> None:
    a = _side(tmp_path / "a.pcap", [_frame(10)])
    b = _side(tmp_path / "b.pcap", [_frame(99)], 10)
    forward = compare_communications(a, b, _assessment(a, b), Budget())
    reverse = compare_communications(b, a, _assessment(b, a), Budget())
    assert [f["key"] for f in forward] == [f["key"] for f in reverse]
    assert {f["subtype"] for f in forward} == {
        "REFERENCE_ONLY_OBSERVATION",
        "CANDIDATE_ONLY_OBSERVATION",
    }
    for first, second in zip(forward, reverse, strict=True):
        assert first["reference"] == second["candidate"]
        assert first["candidate"] == second["reference"]


def test_packet_counts_are_raw_and_references_are_bounded(tmp_path: Path) -> None:
    a = _side(tmp_path / "a.pcap", [_frame()] * 17)
    b = _side(tmp_path / "b.pcap", [_frame()] * 18)
    findings = compare_communications(a, b, _assessment(a, b), Budget())
    assert [f["subtype"] for f in findings] == ["OBSERVED_METADATA_CHANGED"]
    reference = findings[0]["reference"]
    assert reference["metadata"]["packets"] == 17
    assert len(reference["packet_references"]) == 8
    assert reference["packet_references_omitted"] == 9
    assert reference["metadata"]["initiation_packets"] == 0
    protocols = compare_protocols(a, b, _assessment(a, b), Budget())
    assert {f["subtype"] for f in protocols} == {
        "RECORD_COUNTS_CHANGED",
        "PROTOCOL_COUNTERS_CHANGED",
    }
    records = next(f for f in protocols if f["subtype"] == "RECORD_COUNTS_CHANGED")
    assert records["reference"]["record_count"] == 17
    assert records["reference"]["packet_references_omitted"] == 9
    assert "rate" not in reference["metadata"]


def test_nanosecond_bounds_are_compared_without_float_rounding(tmp_path: Path) -> None:
    a = _side(tmp_path / "a.pcap", [_frame()], 1)
    b = _side(tmp_path / "b.pcap", [_frame()], 2)
    assessment = _assessment(a, b)
    assert assessment["temporal_order"] == "CANDIDATE_WINDOW_AFTER_REFERENCE"
    assert a.snapshot["collection"]["first_timestamp"] == "2000000000000000001/1000000000"
    assert b.snapshot["collection"]["first_timestamp"] == "1000000000000000001/500000000"
    assert compare_communications(a, b, assessment, Budget())[0]["subtype"] == "OBSERVED_IN_BOTH"
    assert _assessment(b, a)["temporal_order"] == "CANDIDATE_WINDOW_BEFORE_REFERENCE"


def test_incomplete_evidence_retains_finite_differences_and_abstains(tmp_path: Path) -> None:
    a = _side(tmp_path / "a.pcap", [_frame(10), _frame()])
    b = _side(tmp_path / "b.pcap", [_frame(), ethernet(b"unknown", 0x88B5)])
    assessment = _assessment(a, b)
    assert assessment["communication_metadata"] == "PARTIALLY_COMPARABLE"
    matrix = {d["dimension"]: d["result"] for d in assessment["dimensions"]}
    assert matrix["packet_interpretation"] == "PARTIALLY_COMPARABLE"
    findings = compare_communications(a, b, assessment, Budget())
    reference_only = next(f for f in findings if f["subtype"] == "REFERENCE_ONLY_OBSERVATION")
    assert reference_only["comparability"] == "PARTIALLY_COMPARABLE"
    assert "not identified in the selected candidate capture" in reference_only["explanation"]
    assert any("do not establish" in text for text in reference_only["limitations"])
    opaque = next(f for f in findings if f["subtype"] == "UNASSESSED_OPAQUE_OBSERVATIONS")
    assert opaque["comparability"] == "INDETERMINATE"


@pytest.mark.parametrize(
    "field, value, expected",
    [
        ("vantage_points", ["different sensor"], "INCOMPARABLE"),
        ("vantage_points", [], "INDETERMINATE"),
        ("protocols", [], "INDETERMINATE"),
        ("protocols", ["udp"], "PARTIALLY_COMPARABLE"),
        ("environment", "another site", "INCOMPARABLE"),
        ("uncertainties", ["unknown sensor loss"], "PARTIALLY_COMPARABLE"),
    ],
)
def test_declared_visibility_and_uncertainty_gate_strict_comparison(
    tmp_path: Path, field: str, value: Any, expected: str
) -> None:
    side = _side(tmp_path / "a.pcap", [_frame()])
    assert _assessment(side, side, **{field: value})["communication_metadata"] == expected


def test_unresolved_collection_alignment_is_explicit(tmp_path: Path) -> None:
    side = _side(tmp_path / "a.pcap", [_frame()])
    result = assess(side, side, SCOPE, SCOPE, "unresolved", Budget())
    assert result["communication_metadata"] == "INDETERMINATE"
    assert (
        next(d for d in result["dimensions"] if d["dimension"] == "collection_alignment")["result"]
        == "INDETERMINATE"
    )


def test_decoder_revision_change_is_analytical_same_physical_collection(tmp_path: Path) -> None:
    a = _side(tmp_path / "legacy.pcap", [_frame()], legacy=True)
    b = _side(tmp_path / "current.pcap", [_frame()])
    assert a.analysis["capture_sha256"] == b.analysis["capture_sha256"]
    assert a.analysis["analysis_id"] != b.analysis["analysis_id"]
    assessment = _assessment(a, b)
    assert assessment["independent_collections"] is False
    assert assessment["protocol_metadata"] == "INDETERMINATE"
    assert assessment["communication_metadata"] == "COMPARABLE"
    findings = compare_protocols(a, b, assessment, Budget())
    assert [(f["category"], f["subtype"]) for f in findings] == [
        ("ANALYTICAL_INTERPRETATION_DIFFERENCE", "PROTOCOL_SEMANTICS_CHANGED"),
    ]
    assert compare_communications(a, b, assessment, Budget())[0]["subtype"] == "OBSERVED_IN_BOTH"


def test_all_seven_families_compare_bounded_record_counts(tmp_path: Path) -> None:
    a = _side(tmp_path / "a.pcap", seven_frames())
    b = _side(tmp_path / "b.pcap", seven_frames() * 2)
    findings = compare_protocols(a, b, _assessment(a, b), Budget())
    counters = next(f for f in findings if f["subtype"] == "PROTOCOL_COUNTERS_CHANGED")
    assert counters["reference"]["capture_packets"] == 7
    assert counters["candidate"]["capture_packets"] == 14
    findings = [f for f in findings if f["subtype"] != "PROTOCOL_COUNTERS_CHANGED"]
    assert {f["key"]["protocol"] for f in findings} == {
        "modbus_tcp",
        "profinet_dcp",
        "ethernet_ip",
        "s7comm",
        "iec104",
        "opcua_binary",
        "dnp3",
    }
    assert {f["subtype"] for f in findings} == {"RECORD_COUNTS_CHANGED"}
    assert all(
        f["reference"]["record_count"] == 1 and f["candidate"]["record_count"] == 2
        for f in findings
    )


def test_transient_transaction_ids_do_not_create_protocol_category_changes(tmp_path: Path) -> None:
    first = _frame()
    second = first[:-12] + bytes.fromhex("100100000006010300000001")
    a = _side(tmp_path / "a.pcap", [first])
    b = _side(tmp_path / "b.pcap", [second])
    assert a.analysis["capture_sha256"] != b.analysis["capture_sha256"]
    assert compare_protocols(a, b, _assessment(a, b), Budget()) == []


def test_missing_protocol_evidence_is_not_negative_evidence(tmp_path: Path) -> None:
    enriched = _side(tmp_path / "a.pcap", [_frame()])
    side = Side(build_revision(enriched.snapshot), enriched.snapshot, {})
    findings = compare_protocols(side, side, _assessment(side, side), Budget())
    assert [(f["category"], f["subtype"]) for f in findings] == [
        ("INDETERMINATE_COMPARISON", "PROTOCOL_EVIDENCE_UNAVAILABLE"),
    ]


def test_reviewed_model_relative_associations_do_not_join_pending_ownership() -> None:
    folder = Path(__file__).parent / "fixtures/capture-contract-v2/supported"
    observations = json.loads((folder / "observations.json").read_bytes())
    snapshot = build_snapshot(observations)
    model = build_attachment("model", plant_model(), snapshot)
    mapping = build_attachment(
        "mapping", json.loads((folder / "mapping.json").read_bytes()), snapshot, {"model": model}
    )
    attachments = {"model": model, "mapping": mapping}
    side = Side(build_revision(snapshot, attachments), snapshot, attachments)
    findings = compare_communications(side, side, _assessment(side, side), Budget())
    statuses = {f["reference"]["reviewed_asset_correspondence"]["status"] for f in findings}
    assert statuses == {"EQUIVALENT_REVIEWED_MODEL_ASSOCIATIONS", "INDETERMINATE"}
    unresolved = next(f for f in findings if f["key"]["source_ip"] == "192.0.2.99")
    assert unresolved["reference"]["reviewed_asset_correspondence"]["status"] == "INDETERMINATE"


def test_missing_timestamps_do_not_invent_capture_chronology(tmp_path: Path) -> None:
    def block(kind: int, data: bytes) -> bytes:
        data += bytes((-len(data)) % 4)
        return struct.pack("<II", kind, 12 + len(data)) + data + struct.pack("<I", 12 + len(data))

    path = tmp_path / "no-times.pcapng"
    frame = _frame()
    path.write_bytes(
        block(0x0A0D0D0A, struct.pack("<IHHq", 0x1A2B3C4D, 1, 0, -1))
        + block(1, struct.pack("<HHI", 1, 0, 65535))
        + block(3, struct.pack("<I", len(frame)) + frame)
    )
    snapshot = build_snapshot(analyze_capture(path))
    no_time = Side(build_revision(snapshot), snapshot, {})
    timed = _side(tmp_path / "timed.pcap", [_frame()])
    result = _assessment(no_time, timed)
    assert result["temporal_order"] == "INDETERMINATE"
    assert (
        next(d for d in result["dimensions"] if d["dimension"] == "timestamps")["result"]
        == "INDETERMINATE"
    )


def test_arp_operation_remains_part_of_comparison_identity(tmp_path: Path) -> None:
    def arp(opcode: int) -> bytes:
        return ethernet(
            struct.pack("!HHBBH", 1, 0x0800, 6, 4, opcode)
            + bytes.fromhex("020000000010c000020a020000000020c0000214"),
            0x0806,
        )

    a = _side(tmp_path / "a.pcap", [arp(1)])
    b = _side(tmp_path / "b.pcap", [arp(2)])
    findings = compare_communications(a, b, _assessment(a, b), Budget())
    assert {(f["key"]["arp_operation"]["opcode"], f["subtype"]) for f in findings} == {
        (1, "REFERENCE_ONLY_OBSERVATION"),
        (2, "CANDIDATE_ONLY_OBSERVATION"),
    }


def test_key_and_work_limits_fail_without_partial_results(tmp_path: Path) -> None:
    side = _side(tmp_path / "a.pcap", [_frame()])
    assessment = _assessment(side, side)
    with pytest.raises(ModelError) as error:
        compare_communications(side, side, assessment, Budget(replace(DRIFT_LIMITS, keys=1)))
    assert error.value.diagnostics[0].code == "LIMIT_EXCEEDED"
    before = copy.deepcopy(side.snapshot)
    with pytest.raises(ModelError):
        assess(side, side, SCOPE, SCOPE, "asserted", Budget(replace(DRIFT_LIMITS, work_units=1)))
    assert side.snapshot == before


def test_protocol_accounting_retains_skip_denominators_even_without_header_delta(
    tmp_path: Path,
) -> None:
    a = _side(tmp_path / "a.pcap", [_frame()])
    b = _side(tmp_path / "b.pcap", [_frame(), ethernet(b"unknown", 0x88B5)])
    assessment = _assessment(a, b)
    findings = compare_protocols(a, b, assessment, Budget())
    assert [f["subtype"] for f in findings] == ["PROTOCOL_COUNTERS_CHANGED"]
    changed = findings[0]
    assert changed["reference"]["capture_packets"] == 1
    assert changed["candidate"]["capture_packets"] == 2
    assert changed["candidate"]["enrichment"]["packets_with_records"] == 1
    assert sum(changed["candidate"]["enrichment"]["skipped_packets"].values()) == 1
    unchanged = _assessment(a, a)
    dimension = next(d for d in unchanged["dimensions"] if d["dimension"] == "protocol_decoder")
    accounting = dimension["source_evidence"]["values"][0]
    assert accounting["capture_packets"] == 1
    assert accounting["enrichment_accounting"]["counts"] == {"modbus_tcp:STRUCTURALLY_VALID": 1}
    assert accounting["enrichment_accounting"]["limits"]["records_per_packet"] == 8


def test_changed_coverage_is_source_bound_and_never_an_outage_claim(tmp_path: Path) -> None:
    a = _side(tmp_path / "a.pcap", [_frame()])
    b = _side(tmp_path / "b.pcap", [_frame(), ethernet(b"unknown", 0x88B5)])
    assert compare_coverage(a, a, Budget()) == []
    findings = compare_coverage(a, b, Budget())
    assert [(f["category"], f["subtype"]) for f in findings] == [
        ("COVERAGE_DIFFERENCE", "CAPTURE_COVERAGE_CHANGED"),
    ]
    assert findings[0]["candidate"]["coverage"]["uninterpreted_packets"] == 1
    assert findings[0]["candidate"]["source"]["analysis_id"] == b.analysis["analysis_id"]
    assert "operational absence assessment is withheld" in findings[0]["explanation"]
