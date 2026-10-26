"""Independent byte corpus for the V13-08 parser/decoder audit.

Fixtures intentionally do not import the implementation's capture generators.
RFC 791 section 3.1 and RFC 8200 section 4.2 provide the option oracles.
"""

import ipaddress
import struct
from pathlib import Path
from typing import Any

import pytest
import yaml

from otarchguard.api import validate_bytes
from otarchguard.capture.observations import analyze_capture
from otarchguard.capture.parser import scan_capture
from otarchguard.capture.reconciliation import compare_capture, mapping_template


def _syn() -> bytes:
    return bytes.fromhex("9c4001f600000001000000005002100000000000")


def _write_pcap(path: Path, frame: bytes) -> Path:
    path.write_bytes(
        struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 101)
        + struct.pack("<IIII", 1, 0, len(frame), len(frame))
        + frame
    )
    return path


def _ipv4(options: bytes) -> bytes:
    size = 20 + len(options)
    return (
        struct.pack("!BBHHHBBH", 0x40 | (size // 4), 0, size + 20, 1, 0, 64, 6, 0)
        + ipaddress.IPv4Address("192.0.2.10").packed
        + ipaddress.IPv4Address("192.0.2.20").packed
        + options
        + _syn()
    )


def _ipv6(extension: bytes, protocol: int) -> bytes:
    return (
        struct.pack("!IHBB", 0x60000000, len(extension) + 20, protocol, 64)
        + ipaddress.IPv6Address("2001:db8::10").packed
        + ipaddress.IPv6Address("2001:db8::20").packed
        + extension
        + _syn()
    )


@pytest.mark.parametrize(
    "options",
    [
        b"\x00\x01\x00\x00",  # End-of-list followed by nonzero padding.
        b"\x07\x02\x00\x00",  # Record-route lacks its mandatory pointer.
        b"\x44\x02\x00\x00",  # Timestamp lacks pointer and overflow/flag.
        b"\x88\x02\x00\x00",  # Stream identifier must occupy four octets.
    ],
)
def test_invalid_ipv4_options_cannot_supply_initiation(tmp_path: Path, options: bytes) -> None:
    flow = analyze_capture(_write_pcap(tmp_path / "options.pcap", _ipv4(options)))["flows"][0]
    assert flow["status"] != "decoded"
    assert flow["source_port"] is None and flow["destination_port"] is None
    assert not flow["initiation_evidence"] and flow["initiation_packets"] == 0


@pytest.mark.parametrize(
    "options",
    [b"\x01\x01\x00\x00", b"\x07\x03\x04\x00", b"\x44\x04\x05\x00", b"\x88\x04\x00\x01"],
)
def test_valid_ipv4_option_controls(tmp_path: Path, options: bytes) -> None:
    flow = analyze_capture(_write_pcap(tmp_path / "valid.pcap", _ipv4(options)))["flows"][0]
    assert flow["status"] == "decoded"
    assert flow["destination_port"] == 502 and flow["initiation_packets"] == 1


def test_unimplemented_ipv4_option_is_conservative(tmp_path: Path) -> None:
    flow = analyze_capture(_write_pcap(tmp_path / "unknown.pcap", _ipv4(b"\x9e\x04\x00\x00")))[
        "flows"
    ][0]
    assert flow["status"] == "unsupported"
    assert flow["source_port"] is None and not flow["initiation_evidence"]


@pytest.mark.parametrize("options", [b"\x00\x01\x00\x00", b"\x07\x02\x00\x00"])
def test_malformed_ipv4_syn_never_reaches_native_engine(
    tmp_path: Path, minimal: dict[str, Any], options: bytes
) -> None:
    observations = analyze_capture(_write_pcap(tmp_path / "malformed.pcap", _ipv4(options)))
    model = validate_bytes(yaml.safe_dump(minimal).encode())
    review = mapping_template(observations, model)
    for proposal in review["proposals"]:
        candidate = proposal["candidates"][0]
        proposal.update(
            decision="ACCEPT",
            selected_asset_id=candidate["asset_id"],
            selected_interface_id=candidate["interface_id"],
            reviewer="Independent synthetic reviewer",
            rationale="Exact fictional endpoint correspondence reviewed for this capture.",
        )
    result = compare_capture(observations, model, review)
    assert result["work"]["native_query_pairs"] == 0
    assert result["findings"][0]["classification"] == "OBSERVED_MODEL_UNSUPPORTED"
    assert result["findings"][0]["native_result"] is None
    assert result["absence_assessment"]["status"] == "suppressed"


@pytest.mark.parametrize("protocol", [0, 60])
@pytest.mark.parametrize(
    "options",
    [
        b"\x01\xff\x00\x00\x00\x00",  # PadN claims bytes outside this header.
        b"\x00\x00\x00\x00\x00\x01",  # Last option lacks a length field.
        b"\x01\x04\x00\x01\x00\x00",  # PadN has nonzero option data.
    ],
)
def test_invalid_ipv6_option_tlv_cannot_supply_initiation(
    tmp_path: Path, protocol: int, options: bytes
) -> None:
    raw = _ipv6(b"\x06\x00" + options, protocol)
    flow = analyze_capture(_write_pcap(tmp_path / "options.pcap", raw))["flows"][0]
    assert flow["status"] != "decoded"
    assert flow["source_port"] is None and flow["destination_port"] is None
    assert not flow["initiation_evidence"] and flow["initiation_packets"] == 0


@pytest.mark.parametrize("protocol", [0, 60])
def test_valid_ipv6_padding_preserves_transport(tmp_path: Path, protocol: int) -> None:
    raw = _ipv6(b"\x06\x00\x01\x04\x00\x00\x00\x00", protocol)
    flow = analyze_capture(_write_pcap(tmp_path / "padding.pcap", raw))["flows"][0]
    assert flow["status"] == "decoded" and flow["destination_port"] == 502
    assert flow["initiation_packets"] == 1


@pytest.mark.parametrize("protocol", [0, 60])
def test_unimplemented_ipv6_option_is_conservative(tmp_path: Path, protocol: int) -> None:
    # Unknown option with discard action. Its framing is otherwise valid.
    raw = _ipv6(b"\x06\x00\x80\x02\x00\x00\x00\x00", protocol)
    flow = analyze_capture(_write_pcap(tmp_path / "unknown.pcap", raw))["flows"][0]
    assert flow["status"] == "unsupported"
    assert flow["source_port"] is None and not flow["initiation_evidence"]


def test_ipv6_routing_header_requires_supported_destination_semantics(tmp_path: Path) -> None:
    raw = _ipv6(b"\x06\x00\xff\x01\x00\x00\x00\x00", 43)
    flow = analyze_capture(_write_pcap(tmp_path / "routed.pcap", raw))["flows"][0]
    assert flow["status"] == "unsupported"
    assert flow["destination_port"] is None and not flow["initiation_evidence"]


def test_independent_pcapng_section_and_timestamp_oracle(tmp_path: Path) -> None:
    def block(endian: str, kind: int, body: bytes) -> bytes:
        size = len(body) + 12
        return struct.pack(endian + "II", kind, size) + body + struct.pack(endian + "I", size)

    capture = b""
    for endian, resolution, offset in (("<", 0x82, -3), (">", 3, 4)):
        capture += block(endian, 0x0A0D0D0A, struct.pack(endian + "IHHq", 0x1A2B3C4D, 1, 0, -1))
        options = struct.pack(endian + "HHB3xHHqHH", 9, 1, resolution, 14, 8, offset, 0, 0)
        capture += block(endian, 1, struct.pack(endian + "HHI", 101, 0, 0) + options)
        capture += block(endian, 6, struct.pack(endian + "IIIII", 0, 0, 7, 0, 0))
    path = tmp_path / "mixed.pcapng"
    path.write_bytes(capture)
    result = scan_capture(path)
    assert result["packets"] == 2 and result["blocks"] == 6
    assert [i["timestamp_denominator"] for i in result["interfaces"]] == [4, 1000]
    assert [i["timestamp_offset_seconds"] for i in result["interfaces"]] == [-3, 4]
    flows = analyze_capture(path)["flows"]
    assert len(flows) == 1
    assert flows[0]["first_timestamp"] == "-5/4"
    assert flows[0]["last_timestamp"] == "4007/1000"
    assert flows[0]["interfaces"] == ["0:0", "1:0"]
