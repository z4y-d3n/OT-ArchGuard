"""Independent writer/specimen acceptance; no Wireshark installation needed.

The reference decoder receipt is produced offline by TShark, not by the product.
See fixtures/capture-interoperability/README.md for provenance and limitations.
"""

import calendar
import hashlib
import json
import socket
import struct
from dataclasses import replace
from datetime import datetime
from fractions import Fraction
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from otarchguard.capture.contract import CAPTURE_LIMITS, Packet, Timestamp
from otarchguard.capture.observations import _decode, analyze_capture
from otarchguard.capture.parser import scan_capture
from otarchguard.cli import app
from otarchguard.diagnostics import ModelError

CORPUS = Path(__file__).parent / "fixtures" / "capture-interoperability"
MANIFEST = json.loads((CORPUS / "manifest.json").read_text(encoding="utf-8"))
SPECIMENS = MANIFEST["specimens"]
REFERENCE = json.loads((CORPUS / "reference-decoder.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("specimen", SPECIMENS, ids=[s["file"] for s in SPECIMENS])
def test_independent_specimen_integrity_and_container_acceptance(specimen: dict[str, Any]) -> None:
    path = CORPUS / specimen["file"]
    before = path.read_bytes()
    assert hashlib.sha256(before).hexdigest() == specimen["sha256"]
    assert len(before) == specimen["bytes"]
    if specimen["error"]:
        with pytest.raises(ModelError) as raised:
            scan_capture(path)
        assert raised.value.diagnostics[0].code == specimen["error"]
    else:
        packets: list[Packet] = []
        result = scan_capture(path, packets.append)
        assert result["packets"] == specimen["packets"]
        assert result["sha256"] == specimen["sha256"]
        assert result == scan_capture(path)
        reference = REFERENCE["containers"][specimen["file"]]
        assert reference["sha256"] == specimen["sha256"]
        assert len(packets) == len(reference["packets"])
        for packet, ref in zip(packets, reference["packets"], strict=True):
            assert packet.index == int(ref["frame.number"])
            assert packet.captured_length == int(ref["frame.cap_len"])
            assert packet.original_length == int(ref["frame.len"])
            if ref["frame.interface_id"] is not None:
                assert packet.interface == int(ref["frame.interface_id"])
            stamp = ref["frame.time_epoch"]
            if stamp is None:
                assert packet.timestamp is None
            else:
                # ISO output avoids TShark's signed-decimal pre-epoch rendering.
                assert stamp.endswith("Z")
                seconds = calendar.timegm(datetime.fromisoformat(stamp[:19]).timetuple())
                expected = Fraction(seconds) + Fraction("0." + stamp[20:-1])
                assert packet.timestamp is not None
                actual = Fraction(packet.timestamp.ticks, packet.timestamp.denominator)
                actual += packet.timestamp.offset_seconds
                assert actual == expected
    assert path.read_bytes() == before


@pytest.mark.parametrize("index", range(12))
def test_external_decoder_packet_metadata_and_supported_protocol_fields(index: int) -> None:
    path = CORPUS / "text2pcap-pcapng.data"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == REFERENCE["input_sha256"]
    packets: list[Packet] = []
    scan_capture(path, packets.append)
    assert len(packets) == len(REFERENCE["rows"]) == 12
    packet, reference = packets[index], REFERENCE["rows"][index]
    assert packet.index == int(reference["frame.number"])
    assert packet.interface == int(reference["frame.interface_id"])
    assert packet.captured_length == int(reference["frame.cap_len"])
    assert packet.original_length == int(reference["frame.len"])
    assert packet.timestamp is not None
    assert Fraction(packet.timestamp.ticks, packet.timestamp.denominator) == Fraction(
        reference["frame.time_epoch"]
    )
    observed = _decode(packet, CAPTURE_LIMITS)
    assert (
        observed.status
        == [
            "decoded",
            "decoded",
            "decoded",
            "decoded",
            "decoded",
            "decoded",
            "fragmented",
            "truncated",
            "malformed",
            "truncated",
            "decoded",
            "decoded",
        ][index]
    )
    if observed.status != "decoded":
        # TShark may display partial ports even when the product deliberately
        # withholds them. A reference decoder does not override conservative policy.
        assert observed.source_port is None and observed.destination_port is None
        assert not observed.initiation
        return
    assert observed.source_mac == reference["eth.src"]
    assert observed.destination_mac == reference["eth.dst"]
    if observed.transport == "arp":
        htype, ptype, hlen, plen, opcode = struct.unpack_from("!HHBBH", packet.data, 14)
        assert (htype, ptype, hlen, plen, opcode) == (1, 0x0800, 6, 4, 1)
        assert reference["arp.hw.type"] == "1" and reference["arp.proto.type"] == "0x0800"
        assert reference["arp.hw.size"] == "6" and reference["arp.proto.size"] == "4"
        assert reference["arp.opcode"] == "1"
        assert observed.source_ip == reference["arp.src.proto_ipv4"]
        assert observed.destination_ip == reference["arp.dst.proto_ipv4"]
        assert reference["arp.src.hw_mac"] == "02:00:00:00:00:10"
        assert reference["arp.dst.hw_mac"] == "00:00:00:00:00:00"
        return
    assert observed.source_ip == (reference["ip.src"] or reference["ipv6.src"])
    assert observed.destination_ip == (reference["ip.dst"] or reference["ipv6.dst"])
    assert observed.vlans == ((int(reference["vlan.id"]),) if reference["vlan.id"] else ())
    protocol = reference["ip.proto"] or reference["ipv6.nxt"]
    assert observed.transport == {"6": "tcp", "17": "udp", "1": "icmp", "58": "icmpv6"}[protocol]
    if observed.transport in {"tcp", "udp"}:
        assert observed.source_port == int(reference[observed.transport + ".srcport"])
        assert observed.destination_port == int(reference[observed.transport + ".dstport"])


def test_spec_sections_interface_reset_exact_times_and_unsupported_accounting() -> None:
    path = CORPUS / "spec-sections.data"
    packets: list[Packet] = []
    metadata = scan_capture(path, packets.append)
    assert metadata["unknown_blocks"] == 1
    assert [(p.section, p.interface, p.linktype) for p in packets] == [
        (0, 0, 1),
        (0, 1, 147),
        (0, 0, 1),
        (1, 0, 1),
    ]
    assert [p.timestamp for p in packets] == [
        Timestamp(7, 4, -3),
        Timestamp(1, 1_000_000),
        None,
        Timestamp(7, 1000, 4),
    ]
    result = analyze_capture(path)
    assert result["coverage"]["packets"] == 4
    assert result["coverage"]["decoded"] == 3
    assert result["coverage"]["unsupported"] == 1
    assert "PACKETS_WITHOUT_TIMESTAMPS" in metadata["limitations"]


@pytest.mark.parametrize(
    "specimen",
    [s for s in SPECIMENS if s["error"]],
    ids=[s["file"] for s in SPECIMENS if s["error"]],
)
def test_independent_fatal_captures_publish_no_success_or_output(
    tmp_path: Path, specimen: dict[str, Any]
) -> None:
    output = tmp_path / "must-not-exist"
    result = CliRunner().invoke(
        app, ["capture", "analyze", str(CORPUS / specimen["file"]), "--output", str(output)]
    )
    assert result.exit_code == 2 and not result.stdout and not output.exists()
    assert json.loads(result.stderr)["code"] == specimen["error"]
    assert not list(tmp_path.glob(".otarchguard-capture-*"))


def test_external_writer_capture_is_offline_deterministic_and_resource_bounded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def deny(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("Independent capture analysis attempted networking")

    monkeypatch.setattr(socket, "socket", deny)
    monkeypatch.setattr(socket, "getaddrinfo", deny)
    path = CORPUS / "text2pcap-pcapng.data"
    before = path.read_bytes()
    report = analyze_capture(path)
    assert report == analyze_capture(path)
    assert report["coverage"]["packets"] == 12
    assert report["coverage"]["fragmented"] == 1
    assert report["coverage"]["truncated"] == 2
    assert report["coverage"]["malformed"] == 1
    assert path.read_bytes() == before
    for limits in (
        replace(CAPTURE_LIMITS, packets=11),
        replace(CAPTURE_LIMITS, packet_bytes=53),
        replace(CAPTURE_LIMITS, file_bytes=len(before) - 1),
    ):
        with pytest.raises(ModelError) as raised:
            analyze_capture(path, limits=limits)
        assert raised.value.diagnostics[0].code == "LIMIT_EXCEEDED"
