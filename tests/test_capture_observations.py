"""Independent byte fixtures for capture metadata, without packet-library oracles."""

import hashlib
import ipaddress
import json
import random
import struct
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from otarchguard.capture.contract import CAPTURE_LIMITS, Packet, Timestamp
from otarchguard.capture.observations import _decode, analyze_capture
from otarchguard.diagnostics import ModelError


def tcp(source: int = 40000, destination: int = 502, flags: int = 2) -> bytes:
    return struct.pack("!HHIIBBHHH", source, destination, 1, 0, 0x50, flags, 1024, 0, 0)


def udp(source: int = 40000, destination: int = 47808) -> bytes:
    return struct.pack("!HHHH", source, destination, 8, 0)


def ipv4(
    value: bytes,
    protocol: int = 6,
    source: str = "192.0.2.10",
    destination: str = "192.0.2.20",
    fragments: int = 0,
) -> bytes:
    return (
        struct.pack("!BBHHHBBH", 0x45, 0, len(value) + 20, 1, fragments, 64, protocol, 0)
        + ipaddress.IPv4Address(source).packed
        + ipaddress.IPv4Address(destination).packed
        + value
    )


def ipv6(value: bytes, protocol: int = 6) -> bytes:
    return (
        struct.pack("!IHBB", 0x60000000, len(value), protocol, 64)
        + ipaddress.IPv6Address("2001:db8::10").packed
        + ipaddress.IPv6Address("2001:db8::20").packed
        + value
    )


def ethernet(value: bytes, ethertype: int = 0x0800, tags: tuple[int, ...] = ()) -> bytes:
    header = bytes.fromhex("001122334455aabbccddeeff")
    for index, tag in enumerate(tags):
        header += struct.pack("!HH", 0x88A8 if index == 0 and len(tags) > 1 else 0x8100, tag)
    return header + struct.pack("!H", ethertype) + value


def pcap(path: Path, frames: list[bytes], linktype: int = 1) -> Path:
    result = struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 262144, linktype)
    for index, frame in enumerate(frames):
        result += struct.pack("<IIII", 100 + index, index * 1000, len(frame), len(frame)) + frame
    path.write_bytes(result)
    return path


def packet(value: bytes, linktype: int = 1, original: int | None = None) -> Packet:
    return Packet(
        1,
        24,
        0,
        0,
        linktype,
        Timestamp(1000001, 1000000),
        len(value),
        original if original is not None else len(value),
        value,
    )


def analyze(path: Path, frames: list[bytes], linktype: int = 1) -> dict[str, Any]:
    return analyze_capture(pcap(path, frames, linktype))


def test_counters_direction_and_exact_timestamp_oracle(tmp_path: Path) -> None:
    forward = ethernet(ipv4(tcp()))
    reverse = ethernet(ipv4(tcp(502, 40000, 0x12), source="192.0.2.20", destination="192.0.2.10"))
    report = analyze(tmp_path / "capture with spaces.pcap", [forward, reverse, forward])
    assert report["coverage"]["decoded"] == 3
    assert report["coverage"]["packets"] == 3
    assert len(report["flows"]) == 2 and len(report["conversations"]) == 1
    conversation = report["conversations"][0]
    assert conversation["packets"] == 3
    assert conversation["captured_bytes"] == 3 * 54
    assert conversation["original_bytes"] == 3 * 54
    assert conversation["first_timestamp"] == "100/1"
    assert conversation["last_timestamp"] == "51001/500"
    assert conversation["initiation_direction"] == "observed_syn"
    assert sorted(h["packets"] for h in report["hosts"]) == [3, 3]
    flow = next(f for f in report["flows"] if f["source_ip"] == "192.0.2.10")
    assert flow["id"] == conversation["initiator_flow_id"]
    assert flow["packets"] == 2 and flow["tcp_flags"] == ["SYN"]
    assert flow["samples"][0]["index"] == 1 and flow["samples"][0]["offset"] == 24
    assert flow["samples"][1]["index"] == 3 and flow["samples"][1]["offset"] == 164
    assert flow["samples"][0]["timestamp"] == {
        "ticks": 100000000,
        "denominator": 1000000,
        "offset_seconds": 0,
    }
    assert flow["source_macs"] == ["aa:bb:cc:dd:ee:ff"]
    assert flow["destination_macs"] == ["00:11:22:33:44:55"]
    assert flow["protocol_hints"] == [{"protocol": "Modbus/TCP", "level": "PORT_HINT", "port": 502}]
    assert not any("payload" in key for key in flow)
    assert report == analyze_capture(tmp_path / "capture with spaces.pcap")
    identity = report.pop("observations_sha256")
    assert (
        identity
        == hashlib.sha256(
            json.dumps(report, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode()
        ).hexdigest()
    )


@pytest.mark.parametrize("flags", [0, 1, 4, 0x10, 0x12, 3, 6, 0x13])
def test_no_initiation_from_midstream_response_reset_or_conflicting_flags(flags: int) -> None:
    observed = _decode(packet(ethernet(ipv4(tcp(flags=flags)))), CAPTURE_LIMITS)
    assert observed.status == "decoded" and not observed.initiation


def test_opposite_syn_is_uncertain_without_inventing_sessions(tmp_path: Path) -> None:
    report = analyze(
        tmp_path / "opposite.pcap",
        [
            ethernet(ipv4(tcp())),
            ethernet(ipv4(tcp(502, 40000), source="192.0.2.20", destination="192.0.2.10")),
        ],
    )
    assert len(report["conversations"]) == 1
    assert report["conversations"][0]["initiation_direction"] == "conflicting_syn"
    assert report["conversations"][0]["initiator_flow_id"] is None


def test_udp_arp_icmp_ipv6_and_unknown_are_observations(tmp_path: Path) -> None:
    arp = bytes.fromhex("0001080006040001aabbccddeeffc000020a000000000000c0000214")
    report = analyze(
        tmp_path / "protocols.pcap",
        [
            ethernet(ipv4(udp(), 17)),
            ethernet(arp, 0x0806),
            ethernet(ipv4(b"\x08\x00\x00\x00", 1)),
            ethernet(ipv6(tcp()), 0x86DD),
            ethernet(ipv6(b"\x80\x00\x00\x00", 58), 0x86DD),
            ethernet(b"fictional-data", 0x88B5),
        ],
    )
    assert report["coverage"]["decoded"] == 5 and report["coverage"]["unsupported"] == 1
    assert {f["transport"] for f in report["flows"]} == {
        "udp",
        "arp",
        "icmp",
        "tcp",
        "icmpv6",
        "unknown",
    }
    udp_flow = next(f for f in report["flows"] if f["transport"] == "udp")
    assert not udp_flow["initiation_evidence"]
    assert udp_flow["protocol_hints"] == [
        {"protocol": "BACnet/IP", "level": "PORT_HINT", "port": 47808}
    ]
    assert any(h["ip"] == "2001:db8::10" for h in report["hosts"])
    assert all(
        c["initiation_direction"] == "uncertain"
        for c in report["conversations"]
        if c["transport"] != "tcp"
    )


@pytest.mark.parametrize("tags", [(), (100,), (100, 200)])
def test_vlan_and_raw_ip(tags: tuple[int, ...]) -> None:
    observed = _decode(packet(ethernet(ipv4(tcp()), tags=tags)), CAPTURE_LIMITS)
    assert observed.vlans == tags and observed.status == "decoded"
    assert observed.destination_port == 502
    raw = _decode(packet(ipv4(udp(), 17), 101), CAPTURE_LIMITS)
    assert raw.source_mac is None and raw.transport == "udp" and raw.status == "decoded"
    assert (
        _decode(packet(ethernet(ipv4(tcp()), tags=(1, 2, 3))), CAPTURE_LIMITS).status
        == "unsupported"
    )


@pytest.mark.parametrize("fragment", [1, 0x2000, 0x2001])
def test_ipv4_fragments_never_expose_ports_or_initiation(fragment: int) -> None:
    observed = _decode(packet(ethernet(ipv4(tcp(), fragments=fragment))), CAPTURE_LIMITS)
    assert observed.status == "fragmented"
    assert observed.source_ip == "192.0.2.10"
    assert observed.source_port is None and observed.destination_port is None
    assert not observed.initiation


def test_ipv6_extension_and_fragment_handling() -> None:
    extension = b"\x06\x00" + bytes(6)
    observed = _decode(packet(ethernet(ipv6(extension + tcp(), 0), 0x86DD)), CAPTURE_LIMITS)
    assert observed.transport == "tcp" and observed.destination_port == 502
    fragment = b"\x06\x00\x00\x01" + bytes(4)
    observed = _decode(packet(ethernet(ipv6(fragment + tcp(), 44), 0x86DD)), CAPTURE_LIMITS)
    assert observed.status == "fragmented" and observed.source_port is None
    chain = (b"\x3c\x00" + bytes(6)) * 9 + tcp()
    observed = _decode(packet(ethernet(ipv6(chain, 60), 0x86DD)), CAPTURE_LIMITS)
    assert observed.status == "unsupported" and observed.reason == "IPV6_EXTENSION_DEPTH_EXCEEDED"
    assert (
        _decode(packet(ethernet(ipv6(b"\x06\xff" + bytes(6), 0), 0x86DD)), CAPTURE_LIMITS).status
        == "truncated"
    )


def test_malformed_and_truncated_never_have_unsafe_ports() -> None:
    frame = ethernet(ipv4(tcp()))
    for length in range(len(frame)):
        observed = _decode(packet(frame[:length]), CAPTURE_LIMITS)
        assert observed.status in {"truncated", "unsupported"}
        assert observed.source_port is None and observed.destination_port is None
        assert not observed.initiation
    observed = _decode(packet(frame, original=len(frame) + 20), CAPTURE_LIMITS)
    assert observed.status == "truncated" and observed.source_port is None
    malformed_ip = bytearray(ipv4(tcp()))
    malformed_ip[0] = 0x44
    malformed_tcp = bytearray(tcp())
    malformed_tcp[12] = 0x40
    malformed_udp = bytearray(udp())
    malformed_udp[4:6] = b"\x00\x07"
    for value in (bytes(malformed_ip), ipv4(bytes(malformed_tcp)), ipv4(bytes(malformed_udp), 17)):
        observed = _decode(packet(ethernet(value)), CAPTURE_LIMITS)
        assert observed.status == "malformed" and observed.source_port is None


def test_unknown_linktype_preserves_raw_statistics(tmp_path: Path) -> None:
    report = analyze(tmp_path / "unknown.pcap", [bytes(12), bytes(17)], 147)
    assert not report["hosts"]
    assert report["coverage"]["unsupported"] == 2
    assert len(report["flows"]) == 1
    assert report["flows"][0]["captured_bytes"] == 29
    assert report["flows"][0]["limitations"] == ["LINKTYPE_UNSUPPORTED"]


@pytest.mark.parametrize("budget", ["hosts", "flows", "conversations", "aggregation_bytes"])
def test_aggregation_limits_fail_closed(tmp_path: Path, budget: str) -> None:
    path = pcap(tmp_path / "limited.pcap", [ethernet(ipv4(tcp()))])
    with pytest.raises(ModelError) as error:
        analyze_capture(path, replace(CAPTURE_LIMITS, **{budget: 0}))
    assert error.value.diagnostics[0].category == "resource_limit", error.value.diagnostics


def test_samples_are_bounded_without_losing_counters_or_syn_conflict(tmp_path: Path) -> None:
    frames = [ethernet(ipv4(tcp()))] * 20
    frames += [ethernet(ipv4(tcp(502, 40000), source="192.0.2.20", destination="192.0.2.10"))]
    report = analyze(tmp_path / "bounded.pcap", frames)
    flow = next(f for f in report["flows"] if f["packets"] == 20)
    assert len(flow["samples"]) == 8 and flow["samples_omitted"] == 12
    assert len(flow["initiation_evidence"]) == 8 and flow["initiation_evidence_omitted"] == 12
    assert flow["initiation_packets"] == 20
    assert report["conversations"][0]["initiation_direction"] == "conflicting_syn"


def test_bounded_packet_mutations_do_not_escape_decoder() -> None:
    generator = random.Random(1302)
    fixture = ethernet(ipv6(b"\x06\x00" + bytes(6) + tcp(), 0), 0x86DD, (10, 20))
    for _ in range(500):
        value = bytearray(fixture)
        for _ in range(generator.randrange(1, 5)):
            value[generator.randrange(len(value))] = generator.randrange(256)
        result = _decode(packet(bytes(value)), CAPTURE_LIMITS)
        assert result.status in {"decoded", "truncated", "malformed", "fragmented", "unsupported"}
        if result.status != "decoded":
            assert result.source_port is None and not result.initiation


def test_ipv4_options_are_bounded_and_source_routes_unevaluated() -> None:
    for options, expected in (
        (b"\x01\x01\x00\x00", "decoded"),
        (b"\x44\x01\x00\x00", "malformed"),
        (b"\x44\x08\x00\x00", "malformed"),
        (b"\x83\x03\x04\x00", "unsupported"),
        (b"\x89\x03\x04\x00", "unsupported"),
    ):
        header = bytearray(ipv4(tcp())[:20])
        header[0] = 0x46
        header[2:4] = struct.pack("!H", 44)
        result = _decode(packet(ethernet(bytes(header) + options + tcp())), CAPTURE_LIMITS)
        assert result.status == expected
        if expected != "decoded":
            assert result.source_port is None and not result.initiation


def test_multi_interface_records_are_not_sessions_and_spb_has_no_timestamp(tmp_path: Path) -> None:
    def block(kind: int, body: bytes) -> bytes:
        size = len(body) + 12
        return struct.pack("<II", kind, size) + body + struct.pack("<I", size)

    frame = ethernet(ipv4(tcp()))
    padded = frame + bytes((-len(frame)) % 4)
    source = block(0x0A0D0D0A, struct.pack("<IHHq", 0x1A2B3C4D, 1, 0, -1))
    source += block(1, struct.pack("<HHI", 1, 0, 65535)) * 2
    source += block(6, struct.pack("<IIIII", 0, 0, 2000000, len(frame), len(frame)) + padded)
    source += block(6, struct.pack("<IIIII", 1, 0, 1000000, len(frame), len(frame)) + padded)
    source += block(3, struct.pack("<I", len(frame)) + padded)
    path = tmp_path / "interfaces.pcapng"
    path.write_bytes(source)
    report = analyze_capture(path)
    assert len(report["flows"]) == len(report["conversations"]) == 1
    flow = report["flows"][0]
    assert flow["packets"] == 3 and flow["interfaces"] == ["0:0", "0:1"]
    assert flow["missing_timestamps"] == 1
    assert flow["first_timestamp"] == "1/1" and flow["last_timestamp"] == "2/1"
    assert flow["samples"][2]["timestamp"] is None
    assert flow["initiation_packets"] == 3


def test_metadata_sets_are_explicitly_bounded(tmp_path: Path) -> None:
    frames = []
    for index in range(257):
        value = bytearray(ethernet(ipv4(tcp())))
        value[6:12] = index.to_bytes(6, "big")
        frames.append(bytes(value))
    path = pcap(tmp_path / "many-macs.pcap", frames)
    with pytest.raises(ModelError) as error:
        analyze_capture(path)
    assert error.value.diagnostics[0].code == "LIMIT_EXCEEDED"
    assert "capture_metadata_values" in error.value.diagnostics[0].message


def test_exact_host_and_sample_boundaries_and_independent_results(tmp_path: Path) -> None:
    path = pcap(tmp_path / "boundary.pcap", [ethernet(ipv4(tcp()))] * 2)
    with pytest.raises(ModelError):
        analyze_capture(path, replace(CAPTURE_LIMITS, hosts=1))
    report = analyze_capture(path, replace(CAPTURE_LIMITS, hosts=2, packet_samples=1))
    flow = report["flows"][0]
    assert len(flow["samples"]) == 1 and flow["samples_omitted"] == 1
    assert len(flow["initiation_evidence"]) == 1 and flow["initiation_evidence_omitted"] == 1
    report["limitations"].clear()
    assert analyze_capture(path)["limitations"]


@pytest.mark.parametrize(
    ("flags", "status", "reason"),
    [
        (1 << 24, "malformed", "CAPTURE_LINK_ERRORS_REPORTED"),
        (1 << 11, "unsupported", "CAPTURE_SEGMENTATION_OFFLOAD_UNSUPPORTED"),
        (2 | (1 << 9), "decoded", None),
    ],
)
def test_pcapng_capture_error_and_offload_flags_prevent_native_initiation(
    tmp_path: Path, flags: int, status: str, reason: str | None
) -> None:
    def block(kind: int, body: bytes) -> bytes:
        size = len(body) + 12
        return struct.pack("<II", kind, size) + body + struct.pack("<I", size)

    frame = ethernet(ipv4(tcp()))
    padded = frame + bytes((-len(frame)) % 4)
    source = block(0x0A0D0D0A, struct.pack("<IHHq", 0x1A2B3C4D, 1, 0, -1))
    source += block(1, struct.pack("<HHI", 1, 0, 65535))
    source += block(
        6,
        struct.pack("<IIIII", 0, 0, 1000000, len(frame), len(frame))
        + padded
        + struct.pack("<HHIHH", 2, 4, flags, 0, 0),
    )
    path = tmp_path / "flags.pcapng"
    path.write_bytes(source)
    flow = analyze_capture(path)["flows"][0]
    assert flow["status"] == status
    if reason is not None:
        assert flow["source_port"] is None and not flow["initiation_evidence"]
        assert reason in flow["limitations"]
    else:
        assert flow["source_port"] == 40000 and flow["initiation_evidence"]


@pytest.mark.parametrize(
    ("options", "status"),
    [
        (b"\x02\x04\x05\xb4", "decoded"),
        (b"\x01\x01\x00\x00", "decoded"),
        (b"\xfe\x04\x00\x00", "decoded"),
        (b"\x02\x00\x00\x00", "malformed"),
        (b"\x02\x08\x00\x00", "malformed"),
        (b"\x02\x03\x00\x00", "malformed"),
        (b"\x00\x00\x01\x00", "malformed"),
        (b"\x01\x01\x01\x02", "malformed"),
        (b"\x05\x04\x00\x00", "malformed"),
    ],
)
def test_tcp_option_framing_cannot_supply_invalid_initiation(options: bytes, status: str) -> None:
    segment = bytearray(tcp())
    segment[12] = 0x60
    result = _decode(packet(ethernet(ipv4(bytes(segment) + options))), CAPTURE_LIMITS)
    assert result.status == status
    assert result.initiation == (status == "decoded")
    if status != "decoded":
        assert result.source_port is None and result.destination_port is None


def test_tcp_reserved_bits_are_explicitly_malformed() -> None:
    segment = bytearray(tcp())
    segment[12] |= 2
    result = _decode(packet(ethernet(ipv4(bytes(segment)))), CAPTURE_LIMITS)
    assert result.status == "malformed" and result.reason == "TCP_RESERVED_BITS_SET"
    assert not result.initiation and result.source_port is None
