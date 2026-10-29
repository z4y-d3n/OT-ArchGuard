"""Independent wire fixtures and negative oracles for enrichment contract 1.

Frames below are original test data written from field layouts, without using
the production decoders or third-party packet construction libraries.
"""

import copy
import hashlib
import json
import random
import struct
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from otarchguard.capture.contract import CAPTURE_LIMITS, Packet
from otarchguard.capture.observations import analyze_capture
from otarchguard.capture.protocols import (
    ENRICHMENT_LIMITS,
    EnrichmentLimits,
    ProtocolView,
    Status,
    decode,
    enrich_capture,
    validate_enrichment,
)
from otarchguard.capture.protocols.packet import packet_view
from otarchguard.diagnostics import ModelError

READ = bytes.fromhex("000100000006010300000001")
WRITE = bytes.fromhex("000200000006010600000001")
DCP_IDENTIFY = bytes.fromhex("fefe05000000000100000004ffff0000")


def _view(data: bytes, *, source: int = 40000, destination: int = 502) -> ProtocolView:
    return ProtocolView(data, "tcp", source, destination)


def _ethernet(data: bytes, ethertype: int, tags: tuple[int, ...] = ()) -> bytes:
    result = bytes.fromhex("001122334455aabbccddeeff")
    for tag in tags:
        result += struct.pack("!HH", 0x8100, tag)
    return result + struct.pack("!H", ethertype) + data


def _tcp(data: bytes, *, source: int = 40000, destination: int = 502) -> bytes:
    return struct.pack("!HHIIBBHHH", source, destination, 1, 0, 0x50, 0x18, 1024, 0, 0) + data


def _ipv4(data: bytes, *, fragments: int = 0) -> bytes:
    return (
        struct.pack(
            "!BBHHHBBH4s4s",
            0x45,
            0,
            len(data) + 20,
            1,
            fragments,
            64,
            6,
            0,
            bytes([192, 0, 2, 10]),
            bytes([192, 0, 2, 20]),
        )
        + data
    )


def _capture(path: Path, frames: list[bytes], linktype: int = 1) -> Path:
    data = struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 262144, linktype)
    for i, frame in enumerate(frames):
        data += struct.pack("<IIII", 100 + i, 0, len(frame), len(frame)) + frame
    path.write_bytes(data)
    return path


def _report(tmp_path: Path) -> dict[str, Any]:
    return enrich_capture(
        _capture(
            tmp_path / "original.pcap",
            [
                _ethernet(_ipv4(_tcp(READ)), 0x0800),
                _ethernet(DCP_IDENTIFY, 0x8892),
            ],
        )
    )


def _rehash(value: dict[str, Any]) -> None:
    canonical = json.dumps(
        {k: v for k, v in value.items() if k != "enrichment_sha256"},
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
    )
    value["enrichment_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()


def test_modbus_header_and_direction_are_separate() -> None:
    (first,) = decode(_view(READ))
    assert first.status == Status.STRUCTURALLY_VALID
    assert first.message_category == "read_type"
    assert dict(first.fields) == {
        "transaction_id": 1,
        "protocol_id": 0,
        "unit_id": 1,
        "function_code": 3,
        "exception_response": False,
        "adu_length": 12,
    }
    (forward,) = decode(_view(WRITE))
    (reverse,) = decode(_view(WRITE, source=502, destination=40000))
    assert forward == reverse
    assert forward.message_category == "write_type"
    assert any("direction is unassessed" in text for text in forward.limitations)
    assert not any("request" in (forward.message_category or "") for _ in [0])


@pytest.mark.parametrize(
    ("payload", "category"),
    [
        (bytes.fromhex("0001000000050103020000"), "read_type"),
        (bytes.fromhex("000100000003018302"), "exception_response"),
        (bytes.fromhex("000100000006010800000000"), "diagnostic_type"),
        (bytes.fromhex("000100000009011000000001020000"), "write_type"),
        (bytes.fromhex("00010000000801160000ffff0000"), "write_type"),
        (bytes.fromhex("00010000000d01170000000100000001020000"), "read_write_type"),
    ],
)
def test_supported_modbus_message_shapes(payload: bytes, category: str) -> None:
    (result,) = decode(_view(payload))
    assert result.status == Status.STRUCTURALLY_VALID
    assert result.message_category == category


@pytest.mark.parametrize(
    ("payload", "status", "reason"),
    [
        (b"", Status.PORT_HINT, "NO_APPLICATION_BYTES"),
        (READ[:6], Status.TRUNCATED, "MBAP_HEADER_INCOMPLETE_OR_SEGMENTED"),
        (READ[:-1], Status.TRUNCATED, "ADU_INCOMPLETE_OR_SEGMENTED"),
        (b"HTTP/1.1 200 OK", Status.PORT_HINT, "MBAP_PROTOCOL_NOT_RECOGNIZED"),
        (
            bytes.fromhex("000100010006010300000001"),
            Status.PORT_HINT,
            "MBAP_PROTOCOL_NOT_RECOGNIZED",
        ),
        (bytes.fromhex("00010000000101"), Status.MALFORMED, "MBAP_LENGTH_INVALID"),
        (bytes.fromhex("0001000000ff0103"), Status.MALFORMED, "MBAP_LENGTH_INVALID"),
        (bytes.fromhex("0001000000020103"), Status.MALFORMED, "PDU_SHAPE_INVALID"),
        (bytes.fromhex("0001000000050103030000"), Status.MALFORMED, "PDU_SHAPE_INVALID"),
        (bytes.fromhex("000100000002017f"), Status.UNSUPPORTED_VARIANT, "FUNCTION_NOT_SUPPORTED"),
        (bytes.fromhex("00010000000401830200"), Status.MALFORMED, "PDU_SHAPE_INVALID"),
    ],
)
def test_modbus_abstention_has_no_positive_fields(
    payload: bytes, status: Status, reason: str
) -> None:
    (result,) = decode(_view(payload))
    assert (result.status, result.reason, result.fields) == (status, reason, ())
    assert result.message_category is None


def test_modbus_nonstandard_port_requires_explicit_selection() -> None:
    assert decode(_view(READ, destination=12345)) == ()
    explicit = replace(_view(READ, destination=12345), inspect_modbus=True)
    assert decode(explicit)[0].status == Status.STRUCTURALLY_VALID
    assert decode(ProtocolView(READ, "ethernet", ethertype=0x0800)) == ()


def test_coalesced_and_segmented_modbus_never_resynchronize() -> None:
    records = decode(_view(READ + WRITE))
    assert [r.record_offset for r in records] == [0, 12]
    assert all(r.status == Status.STRUCTURALLY_VALID for r in records)
    broken = decode(_view(READ + b"broken" + WRITE))
    assert len(broken) == 2 and broken[-1].status == Status.PORT_HINT
    assert not any(r.record_offset > 12 for r in broken)
    assert decode(_view(READ[6:]))[0].status != Status.STRUCTURALLY_VALID
    assert decode(_view(READ[:7]))[0].status == Status.TRUNCATED


@pytest.mark.parametrize("maximum", [1, 2, 8])
def test_record_work_is_bounded(maximum: int) -> None:
    limit = replace(ENRICHMENT_LIMITS, records_per_packet=maximum)
    assert len(decode(_view(READ * maximum), limit)) == maximum
    records = decode(_view(READ * (maximum + 1)), limit)
    assert len(records) == maximum
    assert records[-1].reason == "RECORD_ITERATION_LIMIT"
    assert records[-1].status == Status.UNSUPPORTED_VARIANT


def test_protocol_view_ceiling_and_no_zero_budget() -> None:
    assert (
        decode(_view(READ), replace(ENRICHMENT_LIMITS, view_bytes=11))[0].reason
        == "VIEW_BYTE_LIMIT"
    )
    with pytest.raises(ValueError):
        EnrichmentLimits(records_per_packet=0)
    with pytest.raises(ValueError):
        EnrichmentLimits(records=True)


def test_dcp_layer_two_identify_get_set_and_padding() -> None:
    (identify,) = decode(ProtocolView(DCP_IDENTIFY + bytes(30), "ethernet", ethertype=0x8892))
    assert identify.status == Status.STRUCTURALLY_VALID
    assert identify.message_category == "identify"
    assert dict(identify.fields) == {
        "frame_id": 0xFEFE,
        "service_id": 5,
        "service_type": 0,
        "data_length": 4,
        "blocks": 1,
    }
    for payload, category in [
        (bytes.fromhex("fefd030000000001000000020202"), "get"),
        (bytes.fromhex("fefd04000000000100000006020200020000"), "set"),
        (bytes.fromhex("feff05010000000100000006020200020000"), "identify"),
    ]:
        (result,) = decode(ProtocolView(payload, "ethernet", ethertype=0x8892))
        assert result.status == Status.STRUCTURALLY_VALID and result.message_category == category
    assert decode(_view(DCP_IDENTIFY, destination=34962)) == ()
    assert decode(ProtocolView(DCP_IDENTIFY, "ethernet", ethertype=0x0800)) == ()


@pytest.mark.parametrize(
    ("payload", "status", "reason"),
    [
        (bytes.fromhex("fefc"), Status.UNSUPPORTED_VARIANT, "DCP_HELLO_NOT_SUPPORTED"),
        (DCP_IDENTIFY[:11], Status.TRUNCATED, "DCP_HEADER_TRUNCATED"),
        (DCP_IDENTIFY[:-1], Status.TRUNCATED, "DCP_DATA_TRUNCATED"),
        (
            bytes.fromhex("fefe05000000000100000003ffff0000"),
            Status.MALFORMED,
            "DCP_DATA_ALIGNMENT_INVALID",
        ),
        (
            bytes.fromhex("fefe05000000000100000004ffff0002"),
            Status.MALFORMED,
            "DCP_BLOCK_LENGTH_INVALID",
        ),
        (
            bytes.fromhex("fefe04000000000100000004ffff0000"),
            Status.MALFORMED,
            "DCP_FRAME_SERVICE_MISMATCH",
        ),
        (
            bytes.fromhex("fefe05020000000100000004ffff0000"),
            Status.UNSUPPORTED_VARIANT,
            "DCP_SERVICE_NOT_SUPPORTED",
        ),
        (
            bytes.fromhex("fefd04000000000100000004ffff0000"),
            Status.MALFORMED,
            "DCP_BLOCK_INFO_MISSING",
        ),
        (
            bytes.fromhex("fefd030000000001000100020202"),
            Status.MALFORMED,
            "DCP_RESERVED_FIELD_NONZERO",
        ),
        (
            DCP_IDENTIFY + bytes(31),
            Status.UNSUPPORTED_VARIANT,
            "DCP_TRAILING_BYTES_OUTSIDE_PADDING",
        ),
    ],
)
def test_dcp_abstention(payload: bytes, status: Status, reason: str) -> None:
    (result,) = decode(ProtocolView(payload, "ethernet", ethertype=0x8892))
    assert (result.status, result.reason, result.fields) == (status, reason, ())


@pytest.mark.parametrize(
    "payload",
    [b"", b"\xfe", bytes.fromhex("8000") + DCP_IDENTIFY[2:], bytes.fromhex("8000") + bytes(16384)],
    ids=["missing", "partial", "unrelated", "unrelated_large"],
)
def test_unidentified_profinet_traffic_is_never_labeled_dcp(payload: bytes) -> None:
    assert decode(ProtocolView(payload, "ethernet", ethertype=0x8892)) == ()


def test_capture_accounts_for_non_dcp_profinet_without_protocol_claims(tmp_path: Path) -> None:
    frames = [_ethernet(b"", 0x8892), _ethernet(bytes.fromhex("8000"), 0x8892)]
    report = enrich_capture(_capture(tmp_path / "non-dcp.pcap", frames))
    validate_enrichment(report)
    assert not report["records"]
    assert report["skipped_packets"] == {
        "PROFINET_FRAME_ID_MISSING": 1,
        "NON_DCP_PROFINET_FRAME_ID": 1,
    }


def test_dcp_nested_work_and_sensitive_body_are_not_exported(tmp_path: Path) -> None:
    # Identify reply with a structurally framed name block, deliberately private.
    secret = b"SECRET-PLANT-NAME"
    body = bytes.fromhex("0202") + struct.pack("!H", len(secret) + 2) + bytes(2) + secret
    body += bytes(len(body) % 2)
    data = bytes.fromhex("feff0501000000010000") + struct.pack("!H", len(body)) + body
    report = enrich_capture(_capture(tmp_path / "private.pcap", [_ethernet(data, 0x8892)]))
    validate_enrichment(report)
    assert report["records"][0]["status"] == "STRUCTURALLY_VALID"
    assert "SECRET" not in json.dumps(report)
    nested = bytes.fromhex("fefd03000000000100000004") + bytes.fromhex("02020202")
    (result,) = decode(
        ProtocolView(nested, "ethernet", ethertype=0x8892), replace(ENRICHMENT_LIMITS, dcp_blocks=1)
    )
    assert result.reason == "DCP_BLOCK_ITERATION_LIMIT"


def test_capture_binding_determinism_and_frozen_observations(tmp_path: Path) -> None:
    path = _capture(
        tmp_path / "a.pcap", [_ethernet(_ipv4(_tcp(READ)), 0x0800), _ethernet(DCP_IDENTIFY, 0x8892)]
    )
    before = analyze_capture(path)
    first = enrich_capture(path)
    validate_enrichment(first)
    assert first["capture_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert first["capture"] == before["capture"]
    assert first["records"][0]["packet"]["offset"] == 24
    assert first["records"][1]["packet"]["index"] == 2
    assert first["packets_with_records"] == 2
    renamed = tmp_path / "renamed.pcap"
    renamed.write_bytes(path.read_bytes())
    assert enrich_capture(renamed) == first
    assert analyze_capture(path) == before
    assert before["observation_version"] == 2


def test_vlan_raw_ip_and_ipv6_supported_subset(tmp_path: Path) -> None:
    tagged = _ethernet(DCP_IDENTIFY, 0x8892, (9, 12))
    report = enrich_capture(_capture(tmp_path / "vlan.pcap", [tagged]))
    assert report["records"][0]["vlans"] == [9, 12]
    validate_enrichment(report)
    raw = _ipv4(_tcp(READ))
    assert (
        enrich_capture(_capture(tmp_path / "raw.pcap", [raw], 101))["records"][0]["status"]
        == "STRUCTURALLY_VALID"
    )
    tcp = _tcp(READ)
    ipv6 = (
        struct.pack(
            "!IHBB16s16s",
            0x60000000,
            len(tcp),
            6,
            64,
            bytes.fromhex("20010db8000000000000000000000001"),
            bytes.fromhex("20010db8000000000000000000000002"),
        )
        + tcp
    )
    assert (
        enrich_capture(_capture(tmp_path / "v6.pcap", [ipv6], 101))["records"][0]["status"]
        == "STRUCTURALLY_VALID"
    )


def test_unsupported_outer_evidence_cannot_yield_application_metadata(tmp_path: Path) -> None:
    frames = [
        _ethernet(_ipv4(_tcp(READ), fragments=0x2000), 0x0800),
        _ethernet(_ipv4(_tcp(READ)), 0x0800, (1, 2, 3)),
        b"bad",
    ]
    report = enrich_capture(_capture(tmp_path / "bad.pcap", frames))
    validate_enrichment(report)
    assert not report["records"] and sum(report["skipped_packets"].values()) == 3
    frame = _ethernet(DCP_IDENTIFY, 0x8892)
    pkt = Packet(1, 24, 0, 0, 1, None, len(frame), len(frame), frame)
    for bad in [
        replace(pkt, link_errors=True),
        replace(pkt, offloaded=True),
        replace(pkt, original_length=len(frame) + 1),
    ]:
        assert packet_view(bad, CAPTURE_LIMITS).view is None


def test_enrichment_limits_fail_without_publishing_a_partial_result(tmp_path: Path) -> None:
    path = _capture(tmp_path / "capture.pcap", [_ethernet(_ipv4(_tcp(READ + WRITE)), 0x0800)])
    with pytest.raises(ModelError):
        enrich_capture(path, limits=replace(ENRICHMENT_LIMITS, records=1))
    report = enrich_capture(path)
    compact_size = len(json.dumps(report, sort_keys=True, separators=(",", ":")).encode())
    pretty_size = len((json.dumps(report, sort_keys=True, indent=2) + "\n").encode())
    assert pretty_size > compact_size
    with pytest.raises(ModelError):
        enrich_capture(path, limits=replace(ENRICHMENT_LIMITS, output_bytes=compact_size + 1))


@pytest.mark.parametrize(
    "mutation",
    [
        "version",
        "digest",
        "count",
        "reference",
        "privacy",
        "status",
        "boolean",
        "category",
    ],
)
def test_rehashed_artifact_tampering_is_rejected(tmp_path: Path, mutation: str) -> None:
    value = copy.deepcopy(_report(tmp_path))
    if mutation == "version":
        value["enrichment_version"] = 2
    elif mutation == "digest":
        value["capture_sha256"] = "0" * 64
    elif mutation == "count":
        value["counts"]["modbus_tcp:STRUCTURALLY_VALID"] += 1
    elif mutation == "reference":
        value["records"][0]["packet"]["interface"] = 99
    elif mutation == "privacy":
        value["records"][0]["fields"]["process_value"] = "SECRET"
    elif mutation == "status":
        value["records"][0]["status"] = "FUTURE_CONFIRMED"
    elif mutation == "boolean":
        value["records"][0]["fields"]["unit_id"] = True
    else:
        value["records"][0]["message_category"] = "executed_write"
    _rehash(value)
    with pytest.raises(ValueError):
        validate_enrichment(value)


def test_random_bytes_and_mutations_are_bounded_and_deterministic() -> None:
    rng = random.Random(14)
    for size in range(256):
        data = rng.randbytes(size)
        for view in [_view(data), ProtocolView(data, "ethernet", ethertype=0x8892)]:
            records = decode(view)
            assert len(records) <= ENRICHMENT_LIMITS.records_per_packet
            assert decode(view) == records
    for original, transport in [(READ, "tcp"), (DCP_IDENTIFY, "ethernet")]:
        for index in range(len(original)):
            for value in (0, 127, 255):
                data = original[:index] + bytes([value]) + original[index + 1 :]
                view = (
                    _view(data)
                    if transport == "tcp"
                    else ProtocolView(data, "ethernet", ethertype=0x8892)
                )
                assert len(decode(view)) <= ENRICHMENT_LIMITS.records_per_packet


def test_independently_authored_capture_matches_reference_receipt() -> None:
    directory = Path(__file__).parent / "fixtures" / "protocol-corpus"
    path = directory / "synthetic-industrial.pcap"
    receipt = json.loads((directory / "tshark-receipt.json").read_text(encoding="utf-8"))
    assert hashlib.sha256(path.read_bytes()).hexdigest() == receipt["input_sha256"]
    report = enrich_capture(path)
    validate_enrichment(report)
    assert [r["packet"]["index"] for r in report["records"]] == [1, 2, 3]
    assert [r["status"] for r in report["records"]] == [
        "STRUCTURALLY_VALID",
        "STRUCTURALLY_VALID",
        "STRUCTURALLY_VALID",
    ]
    assert report["skipped_packets"] == {"NON_DCP_PROFINET_FRAME_ID": 1}
    for actual, expected in zip(report["records"][:2], receipt["packets"][:2], strict=True):
        for our_key, reference_key in [
            ("transaction_id", "mbtcp.trans_id"),
            ("protocol_id", "mbtcp.prot_id"),
            ("unit_id", "mbtcp.unit_id"),
            ("function_code", "modbus.func_code"),
        ]:
            assert actual["fields"][our_key] == int(expected[reference_key])
        assert actual["fields"]["adu_length"] == int(expected["mbtcp.len"]) + 6
    dcp = report["records"][2]
    for our_key, reference_key in [
        ("frame_id", "pn_rt.frame_id"),
        ("service_id", "pn_dcp.service_id"),
        ("service_type", "pn_dcp.service_type"),
        ("data_length", "pn_dcp.data_length"),
    ]:
        assert dcp["fields"][our_key] == int(receipt["packets"][2][reference_key])


def test_pcapng_extreme_resolution_is_preserved_without_float_conversion(tmp_path: Path) -> None:
    def block(kind: int, body: bytes) -> bytes:
        size = 12 + len(body)
        assert size % 4 == 0
        return struct.pack("<II", kind, size) + body + struct.pack("<I", size)

    frame = _ethernet(_ipv4(_tcp(READ)), 0x0800)
    section = block(0x0A0D0D0A, struct.pack("<IHHq", 0x1A2B3C4D, 1, 0, -1))
    resolution = struct.pack("<HH", 9, 1) + bytes([127, 0, 0, 0]) + bytes(4)
    interface = block(1, struct.pack("<HHI", 1, 0, 65535) + resolution)
    body = struct.pack("<IIIII", 0, 0, 17, len(frame), len(frame)) + frame
    body += bytes((-len(body)) % 4)
    path = tmp_path / "extreme.pcapng"
    path.write_bytes(section + interface + block(6, body))
    report = enrich_capture(path)
    validate_enrichment(report)
    assert report["records"][0]["packet"]["timestamp"]["denominator"] == 10**127
    assert report["records"][0]["packet"]["timestamp"]["ticks"] == 17
