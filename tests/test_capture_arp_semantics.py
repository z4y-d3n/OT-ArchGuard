"""ARP claim/delivery oracles authored directly from RFC 826 field positions."""

import hashlib
import ipaddress
import json
import struct
from pathlib import Path
from typing import Any

import pytest
import yaml

from otarchguard.api import validate_bytes
from otarchguard.capture.observations import analyze_capture
from otarchguard.capture.reconciliation import compare_capture, mapping_template
from otarchguard.diagnostics import ModelError


def arp_frame(
    *,
    opcode: int = 1,
    sender_ip: str = "192.0.2.10",
    target_ip: str = "192.0.2.20",
    sender_mac: str = "020000000010",
    target_mac: str = "000000000000",
    ethernet_source: str = "020000000010",
    ethernet_destination: str = "ffffffffffff",
    hardware_type: int = 1,
    protocol_type: int = 0x0800,
    hardware_length: int = 6,
    protocol_length: int = 4,
) -> bytes:
    return (
        bytes.fromhex(ethernet_destination + ethernet_source + "0806")
        + struct.pack(
            "!HHBBH", hardware_type, protocol_type, hardware_length, protocol_length, opcode
        )
        + bytes.fromhex(sender_mac)
        + ipaddress.IPv4Address(sender_ip).packed
        + bytes.fromhex(target_mac)
        + ipaddress.IPv4Address(target_ip).packed
    )


def observe(tmp_path: Path, frames: list[bytes]) -> dict[str, Any]:
    path = tmp_path / "arp-reference.pcap"
    data = struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1)
    for index, frame in enumerate(frames):
        data += struct.pack("<IIII", 100, index, len(frame), len(frame)) + frame
    path.write_bytes(data)
    result = analyze_capture(path)
    assert path.read_bytes() == data
    assert result == analyze_capture(path)
    return result


def test_broadcast_request_preserves_claim_and_delivery_without_target_host(
    tmp_path: Path, minimal: dict[str, Any]
) -> None:
    result = observe(tmp_path, [arp_frame()])
    assert result["observation_version"] == 2
    flow = result["flows"][0]
    assert flow["source_ip"] == "192.0.2.10"  # Historical ARP SPA alias.
    assert flow["destination_ip"] == "192.0.2.20"  # Historical ARP TPA alias.
    assert flow["arp"] == {
        "metadata_version": 1,
        "opcode": 1,
        "operation": "request",
        "sender_protocol_address": "192.0.2.10",
        "target_protocol_address": "192.0.2.20",
        "sender_hardware_address": "02:00:00:00:00:10",
        "target_hardware_address": "00:00:00:00:00:00",
        "ethernet_source_mac": "02:00:00:00:00:10",
        "ethernet_destination_mac": "ff:ff:ff:ff:ff:ff",
        "ethernet_delivery": "broadcast",
    }
    assert flow["transport_evidence"] == "UNKNOWN"
    assert flow["initiation_evidence"] == []
    assert [(h["ip"], h["observation_roles"]) for h in result["hosts"]] == [
        ("192.0.2.10", ["arp_request_sender"])
    ]
    model = validate_bytes(yaml.safe_dump(minimal).encode())
    review = mapping_template(result, model)
    assert [p["observed_ip"] for p in review["proposals"]] == ["192.0.2.10"]
    assert all(p["decision"] == "PENDING" for p in review["proposals"])
    comparison = compare_capture(result, model, review)
    assert comparison["findings"][0]["classification"] == "OBSERVED_MODEL_UNSUPPORTED"
    assert comparison["work"]["native_query_pairs"] == 0


@pytest.mark.parametrize("opcode,role", [(1, "arp_request_sender"), (2, "arp_reply_sender")])
@pytest.mark.parametrize(
    "destination,delivery",
    [
        ("ffffffffffff", "broadcast"),
        ("020000000020", "unicast"),
        ("01005e000001", "multicast"),
    ],
)
def test_operation_and_wire_delivery_are_independent(
    tmp_path: Path, opcode: int, role: str, destination: str, delivery: str
) -> None:
    result = observe(tmp_path, [arp_frame(opcode=opcode, ethernet_destination=destination)])
    assert result["flows"][0]["arp"]["ethernet_delivery"] == delivery
    assert result["flows"][0]["arp"]["opcode"] == opcode
    assert result["hosts"][0]["observation_roles"] == [role]
    assert result["hosts"][0]["destination_macs"] == []


def test_gratuitous_arp_is_one_sender_claim_not_two_host_observations(tmp_path: Path) -> None:
    result = observe(tmp_path, [arp_frame(target_ip="192.0.2.10")])
    assert len(result["hosts"]) == 1
    assert result["hosts"][0]["packets"] == 1
    assert result["hosts"][0]["destination_macs"] == []
    assert result["conversations"][0]["initiation_direction"] == "uncertain"


def test_probe_promotes_neither_unspecified_sender_nor_referenced_target(
    tmp_path: Path, minimal: dict[str, Any]
) -> None:
    result = observe(tmp_path, [arp_frame(sender_ip="0.0.0.0")])
    assert result["coverage"]["decoded"] == 1
    assert result["hosts"] == []
    assert result["flows"][0]["arp"]["target_protocol_address"] == "192.0.2.20"
    model = validate_bytes(yaml.safe_dump(minimal).encode())
    assert mapping_template(result, model)["proposals"] == []


def test_reply_sender_is_observed_without_ownership_or_target_confirmation(tmp_path: Path) -> None:
    result = observe(
        tmp_path,
        [
            arp_frame(),
            arp_frame(
                opcode=2,
                sender_ip="192.0.2.20",
                target_ip="192.0.2.10",
                sender_mac="020000000020",
                target_mac="020000000010",
                ethernet_source="020000000020",
                ethernet_destination="020000000010",
            ),
        ],
    )
    assert {h["ip"]: h["observation_roles"] for h in result["hosts"]} == {
        "192.0.2.10": ["arp_request_sender"],
        "192.0.2.20": ["arp_reply_sender"],
    }
    assert all(h["packets"] == 1 for h in result["hosts"])
    assert len(result["flows"]) == len(result["conversations"]) == 2


def test_arp_reference_does_not_add_packets_or_frame_macs_to_later_ip_sender(
    tmp_path: Path,
) -> None:
    # Independent IPv4/ICMP header: the referenced address actually occurs as an
    # IP source only in record two; Ethernet addresses remain frame observations.
    ip_frame = (
        bytes.fromhex("0200000000100200000000200800")
        + struct.pack("!BBHHHBBH", 0x45, 0, 24, 1, 0, 64, 1, 0)
        + ipaddress.IPv4Address("192.0.2.20").packed
        + ipaddress.IPv4Address("192.0.2.10").packed
        + bytes.fromhex("00000000")
    )
    result = observe(tmp_path, [arp_frame(), ip_frame])
    hosts = {h["ip"]: h for h in result["hosts"]}
    assert hosts["192.0.2.20"]["packets"] == 1
    assert hosts["192.0.2.20"]["observation_roles"] == ["packet_source"]
    assert hosts["192.0.2.20"]["source_macs"] == ["02:00:00:00:00:20"]
    assert hosts["192.0.2.20"]["destination_macs"] == []
    assert hosts["192.0.2.10"]["observation_roles"] == ["arp_request_sender", "packet_destination"]


def test_spoofed_claims_and_ethernet_addresses_remain_distinct_evidence(tmp_path: Path) -> None:
    result = observe(
        tmp_path,
        [
            arp_frame(),
            arp_frame(sender_mac="020000000099"),
            arp_frame(target_mac="020000000098"),
            arp_frame(ethernet_source="020000000097"),
            arp_frame(ethernet_destination="020000000096"),
            arp_frame(opcode=2),
        ],
    )
    assert len(result["flows"]) == len(result["conversations"]) == 6
    assert len(result["hosts"]) == 1
    host = result["hosts"][0]
    assert host["source_macs"] == ["02:00:00:00:00:10", "02:00:00:00:00:97"]
    assert host["observation_roles"] == ["arp_reply_sender", "arp_request_sender"]
    assert {f["arp"]["sender_hardware_address"] for f in result["flows"]} == {
        "02:00:00:00:00:10",
        "02:00:00:00:00:99",
    }


@pytest.mark.parametrize("length", range(42))
def test_every_truncated_arp_prefix_creates_no_host(tmp_path: Path, length: int) -> None:
    result = observe(tmp_path, [arp_frame()[:length]])
    assert result["hosts"] == []
    assert result["coverage"]["decoded"] == 0
    assert result["flows"][0]["arp"] is None


@pytest.mark.parametrize(
    "changes",
    [
        {"hardware_type": 2},
        {"protocol_type": 0x86DD},
        {"hardware_length": 5},
        {"protocol_length": 16},
    ],
)
def test_unsupported_arp_formats_do_not_supply_identity_evidence(
    tmp_path: Path, changes: dict[str, Any]
) -> None:
    result = observe(tmp_path, [arp_frame(**changes)])
    assert result["hosts"] == []
    assert result["flows"][0]["arp"] is None
    assert result["flows"][0]["limitations"] == ["ARP_ADDRESS_FORMAT_UNSUPPORTED"]


@pytest.mark.parametrize("opcode", [0, 3, 65535])
def test_unsupported_opcode_preserves_fields_without_promoting_host(
    tmp_path: Path, opcode: int
) -> None:
    result = observe(tmp_path, [arp_frame(opcode=opcode)])
    assert result["hosts"] == []
    assert result["flows"][0]["arp"]["opcode"] == opcode
    assert result["flows"][0]["arp"]["operation"] == "unsupported"
    assert result["flows"][0]["limitations"] == ["ARP_OPCODE_UNSUPPORTED"]


def test_legacy_observations_are_rejected_even_with_valid_digest(
    tmp_path: Path, minimal: dict[str, Any]
) -> None:
    result = observe(tmp_path, [arp_frame()])
    result.pop("observations_sha256")
    result["observation_version"] = 1
    result["observations_sha256"] = hashlib.sha256(
        json.dumps(result, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode()
    ).hexdigest()
    model = validate_bytes(yaml.safe_dump(minimal).encode())
    with pytest.raises(ModelError) as caught:
        mapping_template(result, model)
    assert "regenerate" in caught.value.diagnostics[0].message
