"""Independent framing and rehashed metadata adversaries for the V14-00 slice.

Wire constants come from Modbus MBAP/PDU layout and official Wireshark DCP
constants, not product fixture generators. A valid outer digest is not enough.
"""

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from otarchguard.capture.protocols import (
    ProtocolView,
    Status,
    decode,
    enrich_capture,
    validate_enrichment,
)
from otarchguard.diagnostics import ModelError
from otarchguard.evidence.workspace import build_snapshot

FIXTURES = Path(__file__).parent / "fixtures"


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode()
    ).hexdigest()


def _rehash(value: dict[str, Any], field: str) -> None:
    value[field] = _digest({key: item for key, item in value.items() if key != field})


@pytest.mark.parametrize(
    "service,category,body",
    [
        (3, "get", "0102"),
        (4, "set", "0202000400000000"),
    ],
)
def test_dcp_get_set_wire_ids_are_three_and_four(service: int, category: str, body: str) -> None:
    payload = bytes.fromhex("fefd") + bytes([service, 0])
    blocks = bytes.fromhex(body)
    payload += bytes.fromhex("000000010000") + len(blocks).to_bytes(2, "big") + blocks
    records = decode(ProtocolView(payload, "ethernet", ethertype=0x8892))
    assert len(records) == 1
    assert records[0].status == Status.STRUCTURALLY_VALID
    assert records[0].message_category == category
    assert dict(records[0].fields)["service_id"] == service


@pytest.mark.parametrize("service", [1, 2])
def test_unassigned_dcp_ids_cannot_become_get_or_set(service: int) -> None:
    payload = bytes.fromhex("fefd") + bytes([service, 0]) + bytes.fromhex("00000001000000020102")
    records = decode(ProtocolView(payload, "ethernet", ethertype=0x8892))
    assert all(record.status != Status.STRUCTURALLY_VALID for record in records)
    assert all(record.message_category is None for record in records)


@pytest.mark.parametrize("function", [3, 4, 23])
def test_incomplete_register_shape_is_not_a_valid_modbus_response(function: int) -> None:
    # One byte cannot encode a 16-bit register. PDU length3 cannot be a read request.
    payload = bytes.fromhex("00010000000401") + bytes([function, 1, 0])
    records = decode(ProtocolView(payload, "tcp", source_port=502, destination_port=40000))
    assert len(records) == 1
    assert records[0].status == Status.MALFORMED


def test_independent_tshark_receipt_matches_only_supported_product_metadata() -> None:
    directory = FIXTURES / "protocol-corpus"
    receipt = json.loads((directory / "tshark-receipt.json").read_text(encoding="utf-8"))
    report = enrich_capture(directory / "synthetic-industrial.pcap")
    validate_enrichment(report)
    assert report["capture_sha256"] == receipt["input_sha256"]
    assert len(receipt["packets"]) == 4
    assert len(report["records"]) == report["packets_with_records"] == 3
    assert report["skipped_packets"] == {"NON_DCP_PROFINET_FRAME_ID": 1}
    assert receipt["packets"][3]["pn_rt.frame_id"] == "32768"
    assert receipt["packets"][3]["pn_dcp.service_id"] == ""
    assert all(record["packet"]["index"] != 4 for record in report["records"])
    for record, reference in zip(report["records"], receipt["packets"][:3], strict=True):
        assert record["packet"]["index"] == int(reference["frame.number"])
        if reference["modbus.func_code"]:
            assert record["status"] == "STRUCTURALLY_VALID"
            assert record["fields"]["function_code"] == int(reference["modbus.func_code"])
            assert record["fields"]["transaction_id"] == int(reference["mbtcp.trans_id"])
        elif reference["pn_dcp.service_id"]:
            assert record["status"] == "STRUCTURALLY_VALID"
            assert record["fields"]["service_id"] == int(reference["pn_dcp.service_id"])


@pytest.mark.parametrize("payload", [b"", b"\xfe", b"\x80\x00", b"\x00\x00"])
def test_unrelated_or_missing_profinet_frame_id_has_no_dcp_label(payload: bytes) -> None:
    assert decode(ProtocolView(payload, "ethernet", ethertype=0x8892)) == ()


@pytest.mark.parametrize("location", ["root", "record", "packet", "capture", "interface"])
def test_enrichment_rejects_unknown_payload_extensions(location: str) -> None:
    report = enrich_capture(FIXTURES / "protocol-corpus" / "synthetic-industrial.pcap")
    targets = {
        "root": report,
        "record": report["records"][0],
        "packet": report["records"][0]["packet"],
        "capture": report["capture"],
        "interface": report["capture"]["interfaces"][0],
    }
    targets[location]["raw_application_payload"] = "SENSITIVE_UNSUPPORTED_EXTENSION"
    _rehash(report, "enrichment_sha256")
    with pytest.raises(ValueError):
        validate_enrichment(report)


@pytest.mark.parametrize("mutation", ["record_outside_frame", "packet_outside_file"])
def test_enrichment_rejects_impossible_rehashed_packet_boundaries(mutation: str) -> None:
    report = enrich_capture(FIXTURES / "protocol-corpus" / "synthetic-industrial.pcap")
    packet = report["records"][0]["packet"]
    if mutation == "record_outside_frame":
        packet["captured_length"] = packet["original_length"] = 1
        report["records"][0]["record_offset"] = 16_384
    else:
        packet["offset"] = report["capture"]["size_bytes"] - 1
    _rehash(report, "enrichment_sha256")
    with pytest.raises(ValueError):
        validate_enrichment(report)


@pytest.mark.parametrize("mutation", ["denominator", "offset", "unsupported_resolution", "budget"])
def test_enrichment_metadata_joins_and_reported_budget_are_enforced(mutation: str) -> None:
    report = enrich_capture(FIXTURES / "protocol-corpus" / "synthetic-industrial.pcap")
    interface = report["capture"]["interfaces"][0]
    if mutation == "denominator":
        interface["timestamp_denominator"] = 2
    elif mutation == "offset":
        interface["timestamp_offset_seconds"] = 1
    elif mutation == "unsupported_resolution":
        interface["timestamp_denominator"] = 3
        for record in report["records"]:
            record["packet"]["timestamp"]["denominator"] = 3
    else:
        report["limits"]["records"] = 1
    _rehash(report, "enrichment_sha256")
    with pytest.raises(ValueError):
        validate_enrichment(report)


@pytest.mark.parametrize("mutation", ["interface_denominator", "group_timestamp", "flow_bytes"])
def test_snapshot_rejects_inconsistent_rehashed_observation_metadata(mutation: str) -> None:
    source = FIXTURES / "capture-contract-v2" / "supported" / "observations.json"
    observations = copy.deepcopy(json.loads(source.read_text(encoding="utf-8")))
    if mutation == "interface_denominator":
        observations["capture"]["interfaces"][0]["timestamp_denominator"] = 0
    elif mutation == "group_timestamp":
        observations["conversations"][0]["first_timestamp"] = "invalid"
    else:
        observations["flows"][0]["captured_bytes"] = 1
    _rehash(observations, "observations_sha256")
    with pytest.raises(ModelError):
        build_snapshot(observations)
