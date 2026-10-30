"""V14-05 trust-transition tests over independently specified fictional wire data.

These tests exercise packet-to-artifact joins, rather than claiming full protocol
semantics. Expected metadata follows the documented V14-01 framing subsets.
CRC-16/DNP uses the normal polynomial, independently of the reflected decoder.
No test invokes a network, TShark, or a third-party capture.
"""

import hashlib
import json
import struct
from dataclasses import asdict, replace
from pathlib import Path

import pytest
from typer.testing import CliRunner

from otarchguard.capture.cli import app as capture_app
from otarchguard.capture.contract import CAPTURE_LIMITS
from otarchguard.capture.protocols import (
    EnrichmentLimits,
    ProtocolView,
    Status,
    decode,
    enrich_capture,
    validate_enrichment,
)
from otarchguard.diagnostics import ModelError


def _crc(data: bytes) -> bytes:
    register = 0
    for octet in data:
        register ^= int(f"{octet:08b}"[::-1], 2) << 8
        for _ in range(8):
            register = ((register << 1) ^ (0x3D65 if register & 0x8000 else 0)) & 65535
    value = int(f"{register:016b}"[::-1], 2) ^ 65535
    return struct.pack("<H", value)


def _dnp(opaque: bytes) -> bytes:
    user = b"\xc0\xc0\x81\x00\x00" + opaque
    header = b"\x05\x64" + bytes([5 + len(user), 0x44]) + b"\x01\x00\x02\x00"
    return header + _crc(header) + user + _crc(user)


# Each pair differs only in information the public metadata contract excludes.
# Eight-byte strings have identical length so the retained envelope stays equal.
_PRIVATE_A = b"<script>"
_PRIVATE_B = b"SECRET!!"
_S7_HEADER = bytes.fromhex("0300002402f080320100000001000e0005")
_S7_PARAMETER = bytes.fromhex("0501120a10020001000184000000")
_UA_PREFIX = b"HELF" + struct.pack("<IIIIIIi", 40, 0, 8192, 8192, 0, 0, 8)
CASES = (
    (
        "modbus_tcp",
        502,
        bytes.fromhex("000100000006010600001234"),
        bytes.fromhex("0001000000060106ffffabcd"),
        "write_type",
    ),
    (
        "profinet_dcp",
        None,
        bytes.fromhex("fefd0400000000010000000e0202000a0000") + _PRIVATE_A,
        bytes.fromhex("fefd0400000000010000000e0202000a0000") + _PRIVATE_B,
        "set",
    ),
    (
        "ethernet_ip",
        44818,
        bytes.fromhex("650004000100000000000000") + _PRIVATE_A + b"\0" * 4 + b"\1\0\0\0",
        bytes.fromhex("65000400ffffffff00000000") + _PRIVATE_B + b"\0" * 4 + b"\1\0\0\0",
        "register_session",
    ),
    (
        "s7comm",
        102,
        _S7_HEADER + _S7_PARAMETER + bytes.fromhex("00040008aa"),
        _S7_HEADER[:11]
        + b"\xff\xff"
        + _S7_HEADER[13:]
        + _S7_PARAMETER[:8]
        + bytes.fromhex("ffff84ffffff")
        + bytes.fromhex("00040008bb"),
        "write_type",
    ),
    (
        "iec104",
        2404,
        bytes.fromhex("680e0000000001010300010000000001"),
        bytes.fromhex("680e00000000010103000100ffffff00"),
        "information_transfer",
    ),
    (
        "opcua_binary",
        4840,
        _UA_PREFIX + _PRIVATE_A,
        _UA_PREFIX + _PRIVATE_B,
        "connection_handshake",
    ),
    ("dnp3", 20000, _dnp(_PRIVATE_A), _dnp(_PRIVATE_B), "user_data"),
)


def _view(data: bytes, port: int | None) -> ProtocolView:
    if port is None:
        return ProtocolView(data, "ethernet", ethertype=0x8892)
    return ProtocolView(data, "tcp", 42000, port)


def _ethernet(data: bytes, port: int | None) -> bytes:
    macs = bytes.fromhex("020000000002020000000001")
    if port is None:
        return macs + b"\x88\x92" + data
    tcp = struct.pack("!HHIIBBHHH", 42000, port, 1, 0, 0x50, 0x18, 4096, 0, 0) + data
    ipv4 = struct.pack(
        "!BBHHHBBH4s4s",
        0x45,
        0,
        20 + len(tcp),
        1,
        0,
        64,
        6,
        0,
        bytes([192, 0, 2, 1]),
        bytes([192, 0, 2, 2]),
    )
    return macs + b"\x08\x00" + ipv4 + tcp


def _pcap(
    frames: list[bytes], *, endian: str = "<", nano: bool = False, linktype: int = 1
) -> bytes:
    magic = 0xA1B23C4D if nano else 0xA1B2C3D4
    output = struct.pack(endian + "IHHIIII", magic, 2, 4, 0, 0, 65535, linktype)
    for index, frame in enumerate(frames):
        output += struct.pack(endian + "IIII", 100 + index, 17, len(frame), len(frame)) + frame
    return output


@pytest.mark.parametrize("protocol,port,before,after,category", CASES, ids=[c[0] for c in CASES])
def test_private_value_substitution_preserves_only_allowed_header_evidence(
    protocol: str,
    port: int | None,
    before: bytes,
    after: bytes,
    category: str,
    tmp_path: Path,
) -> None:
    assert before != after and len(before) == len(after)
    first, second = (decode(_view(data, port)) for data in (before, after))
    assert len(first) == len(second) == 1
    assert first == second
    assert first[0].status == Status.STRUCTURALLY_VALID
    assert first[0].protocol == protocol and first[0].message_category == category
    reports = []
    for label, payload in (("before", before), ("after", after)):
        capture = tmp_path / (label + ".pcap")
        capture.write_bytes(_pcap([_ethernet(payload, port)]))
        report = enrich_capture(capture)
        validate_enrichment(report)
        reports.append(report)
        encoded = json.dumps(report)
        assert _PRIVATE_A.decode() not in encoded and _PRIVATE_B.decode() not in encoded
        assert report["counts"] == {protocol + ":STRUCTURALLY_VALID": 1}
        assert report["records"][0]["fields"] == dict(first[0].fields)
    assert reports[0]["capture_sha256"] != reports[1]["capture_sha256"]
    assert reports[0]["enrichment_sha256"] != reports[1]["enrichment_sha256"]
    assert reports[0]["records"] == reports[1]["records"]


_TCP = tuple(case for case in CASES if case[1] is not None)


@pytest.mark.parametrize("protocol,port,payload,other,category", _TCP, ids=[c[0] for c in _TCP])
def test_bad_middle_record_stops_packet_without_resynchronizing_later_valid_bytes(
    protocol: str,
    port: int,
    payload: bytes,
    other: bytes,
    category: str,
) -> None:
    # Each contradiction is at a documented mandatory framing field. No random fuzzing.
    bad = bytearray(payload)
    if protocol == "modbus_tcp":
        bad[4:6] = b"\0\1"  # MBAP length cannot contain unit plus function.
    elif protocol == "ethernet_ip":
        bad[0:2] = b"\xff\xff"  # No recognized encapsulation command.
    elif protocol == "s7comm":
        bad[1] = 1  # TPKT reserved byte.
    elif protocol == "iec104":
        bad[2] = 1  # S format cannot carry this I-format ASDU length.
    elif protocol == "opcua_binary":
        bad[4:8] = b"\7\0\0\0"  # Declared total below fixed eight-byte header.
    else:
        bad[8] ^= 1  # Mandatory link-header CRC.
    results = decode(_view(payload + bytes(bad) + other, port))
    assert len(results) == 2
    assert results[0].status == Status.STRUCTURALLY_VALID
    assert results[0].message_category == category
    expected_reason = {
        "modbus_tcp": "MBAP_LENGTH_INVALID",
        "ethernet_ip": "ENCAPSULATION_COMMAND_UNSUPPORTED",
        "s7comm": "TPKT_HEADER_INVALID",
        "iec104": "S_CONTROL_OR_LENGTH_INVALID",
        "opcua_binary": "MESSAGE_SIZE_INVALID",
        "dnp3": "LINK_HEADER_CRC_INVALID",
    }
    expected_status = Status.UNSUPPORTED_VARIANT if protocol == "ethernet_ip" else Status.MALFORMED
    assert results[1].status == expected_status and results[1].reason == expected_reason[protocol]
    assert [r.record_offset for r in results] == [0, len(payload)]
    assert results[1].fields == () and results[1].message_category is None
    assert all(r.protocol == protocol for r in results)


@pytest.mark.parametrize("protocol,port,payload,other,category", _TCP, ids=[c[0] for c in _TCP])
def test_exact_packet_record_and_view_bounds_account_for_unexamined_tail(
    protocol: str,
    port: int,
    payload: bytes,
    other: bytes,
    category: str,
) -> None:
    exact = decode(_view(payload * 2, port), EnrichmentLimits(records_per_packet=2))
    assert len(exact) == 2 and all(r.status == Status.STRUCTURALLY_VALID for r in exact)
    exceeded = decode(_view(payload * 3, port), EnrichmentLimits(records_per_packet=2))
    assert [r.status for r in exceeded] == [Status.STRUCTURALLY_VALID, Status.UNSUPPORTED_VARIANT]
    assert exceeded[-1].reason == "RECORD_ITERATION_LIMIT"
    assert exceeded[-1].record_offset == len(payload) and exceeded[-1].fields == ()
    assert decode(_view(payload, port), EnrichmentLimits(view_bytes=len(payload))) == exact[:1]
    (over_view,) = decode(_view(payload + b"\0", port), EnrichmentLimits(view_bytes=len(payload)))
    assert over_view.status == Status.UNSUPPORTED_VARIANT
    assert over_view.reason == "VIEW_BYTE_LIMIT" and over_view.fields == ()


@pytest.mark.parametrize("endian,nano", [("<", False), (">", False), ("<", True), (">", True)])
def test_seven_family_capture_joins_survive_container_precision_and_exact_global_budget(
    endian: str,
    nano: bool,
    tmp_path: Path,
) -> None:
    frames = [_ethernet(case[2], case[1]) for case in CASES]
    source = _pcap(frames, endian=endian, nano=nano)
    capture = tmp_path / "mixed.pcap"
    capture.write_bytes(source)
    limits = EnrichmentLimits(records=7)
    report = enrich_capture(capture, limits=limits)
    validate_enrichment(report)
    assert report["capture_sha256"] == hashlib.sha256(source).hexdigest()
    assert report["packets_with_records"] == 7 and report["skipped_packets"] == {}
    assert report["counts"] == {case[0] + ":STRUCTURALLY_VALID": 1 for case in CASES}
    offset = 24
    denominator = 1_000_000_000 if nano else 1_000_000
    for index, (record, case, frame) in enumerate(
        zip(report["records"], CASES, frames, strict=True)
    ):
        assert record["protocol"] == case[0] and record["record_offset"] == 0
        packet = record["packet"]
        assert packet["index"] == index + 1 and packet["offset"] == offset
        assert packet["captured_length"] == packet["original_length"] == len(frame)
        assert packet["timestamp"] == {
            "ticks": (100 + index) * denominator + 17,
            "denominator": denominator,
            "offset_seconds": 0,
        }
        offset += 16 + len(frame)
    with pytest.raises(ModelError) as raised:
        enrich_capture(capture, limits=replace(limits, records=6))
    assert raised.value.diagnostics[0].code == "LIMIT_EXCEEDED"
    assert "enrichment_records" in raised.value.diagnostics[0].message
    assert capture.read_bytes() == source
    assert list(tmp_path.iterdir()) == [capture]


@pytest.mark.parametrize("linktype,prefix", [(0, b"\x02\0\0\0"), (113, b"\0" * 14 + b"\x08\0")])
def test_recognizable_inner_payload_cannot_override_unsupported_null_or_sll(
    linktype: int,
    prefix: bytes,
    tmp_path: Path,
) -> None:
    # Preserve actual link framing: no conversion to raw IP/Ethernet for a positive.
    ip = _ethernet(CASES[0][2], 502)[14:]
    capture = tmp_path / "unsupported.pcap"
    capture.write_bytes(_pcap([prefix + ip], linktype=linktype))
    report = enrich_capture(capture)
    validate_enrichment(report)
    assert report["records"] == [] and report["counts"] == {}
    assert report["packets_with_records"] == 0
    assert report["skipped_packets"] == {"LINKTYPE_UNSUPPORTED": 1}


def test_known_conflicting_ports_select_one_family_without_payload_based_fallback() -> None:
    # Source 502 wins the documented inventory order even for recognizable UA bytes.
    payload = CASES[5][2]
    (selected,) = decode(ProtocolView(payload, "tcp", 502, 4840))
    assert selected.protocol == "modbus_tcp" and selected.status == Status.PORT_HINT
    assert selected.reason == "MBAP_PROTOCOL_NOT_RECOGNIZED" and selected.fields == ()
    assert decode(ProtocolView(payload, "tcp", 42000, 12345)) == ()
    # Explicit nonstandard Modbus selection is the sole documented API exception.
    (explicit,) = decode(ProtocolView(CASES[0][2], "tcp", 42000, 12345, inspect_modbus=True))
    assert explicit.protocol == "modbus_tcp" and explicit.status == Status.STRUCTURALLY_VALID


def test_dcp_selector_iteration_and_outer_capture_ceiling_are_exact(tmp_path: Path) -> None:
    selectors = bytes.fromhex("01020203")
    data = bytes.fromhex("fefd03000000000100000004") + selectors
    (at_limit,) = decode(_view(data, None), EnrichmentLimits(dcp_blocks=2))
    assert at_limit.status == Status.STRUCTURALLY_VALID
    assert dict(at_limit.fields)["blocks"] == 2
    (over_limit,) = decode(_view(data, None), EnrichmentLimits(dcp_blocks=1))
    assert over_limit.status == Status.UNSUPPORTED_VARIANT
    assert over_limit.reason == "DCP_BLOCK_ITERATION_LIMIT" and over_limit.fields == ()
    frame = _ethernet(data, None)
    capture = tmp_path / "selectors.pcap"
    capture.write_bytes(_pcap([frame]))
    assert enrich_capture(capture, capture_limits=replace(CAPTURE_LIMITS, packet_bytes=len(frame)))
    with pytest.raises(ModelError) as raised:
        enrich_capture(capture, capture_limits=replace(CAPTURE_LIMITS, packet_bytes=len(frame) - 1))
    assert raised.value.diagnostics[0].code == "LIMIT_EXCEEDED"
    assert "capture_packet_bytes" in raised.value.diagnostics[0].message
    assert set(p.name for p in tmp_path.iterdir()) == {"selectors.pcap"}


def test_crc_oracle_and_all_abstention_records_exclude_payload_types() -> None:
    assert _crc(b"123456789") == bytes.fromhex("82ea")
    for _, port, payload, _, _ in CASES:
        records = decode(_view(payload, port), EnrichmentLimits(view_bytes=len(payload) - 1))
        assert len(records) == 1 and records[0].status == Status.UNSUPPORTED_VARIANT
        assert records[0].fields == () and records[0].message_category is None
        assert isinstance(json.dumps(asdict(records[0])), str)


@pytest.mark.parametrize("bad_tail", [b"\0" * 15, struct.pack("<IIII", 101, 0, 2, 1) + b"xx"])
def test_fatal_later_container_record_prevents_cli_publication_after_valid_protocol(
    bad_tail: bytes,
    tmp_path: Path,
) -> None:
    capture = tmp_path / "late-failure.pcap"
    original = _pcap([_ethernet(CASES[0][2], 502)]) + bad_tail
    capture.write_bytes(original)
    output = tmp_path / "enrichment.json"
    result = CliRunner().invoke(capture_app, ["enrich", str(capture), "--output", str(output)])
    assert result.exit_code == 2
    assert result.stdout == "" and not output.exists()
    diagnostic = json.loads(result.stderr)
    assert diagnostic["code"] in {"CAPTURE_TRUNCATED", "CAPTURE_INVALID"}
    assert capture.read_bytes() == original
