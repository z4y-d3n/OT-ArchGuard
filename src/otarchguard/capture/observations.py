"""Bounded packet metadata and aggregates, without session or payload reconstruction.

MAC addresses describe frame observations, never ownership of an IP. IPv4 checksums
are not validated because capture offload can leave incomplete checksums. The
aggregation budget is conservative allocation accounting, not a measured RSS cap.
"""

import hashlib
import ipaddress
import json
import struct
from collections import Counter
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path
from typing import Any

from otarchguard.capture.contract import CAPTURE_LIMITS, CaptureLimits, Packet
from otarchguard.capture.parser import scan_capture
from otarchguard.diagnostics import check_limit

_PORTS: tuple[tuple[str, int, str], ...] = (
    ("tcp", 502, "Modbus/TCP"),
    ("tcp", 44818, "EtherNet/IP"),
    ("udp", 44818, "EtherNet/IP"),
    ("udp", 2222, "EtherNet/IP"),
    ("tcp", 20000, "DNP3"),
    ("udp", 20000, "DNP3"),
    ("tcp", 102, "S7comm"),
    ("tcp", 4840, "OPC UA"),
    ("udp", 47808, "BACnet/IP"),
)
_LIMITATIONS = [
    "Raw capture records are counted; duplicates and multi-interface copies are not deduplicated.",
    "Conversations group endpoint tuples, not sessions or successful communications.",
    "MAC addresses are frame observations and may belong to transit equipment.",
    "Port associations are PORT_HINT only, never confirmed application protocols.",
    "No payloads, DNS resolution, reassembly, checksum validation or live networking.",
    "Initial SYN evidence suggests an initiator; it does not establish a complete session.",
    "Missing traffic establishes neither blocking nor the absence of a device or service.",
    "ARP sender fields are claims; target fields only reference an address and do not "
    "establish a destination device, ownership or a response.",
]


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode()
    ).hexdigest()


@dataclass(slots=True)
class _Decoded:
    source_ip: str | None = None
    destination_ip: str | None = None
    source_mac: str | None = None
    destination_mac: str | None = None
    source_port: int | None = None
    destination_port: int | None = None
    transport: str = "unknown"
    ip_version: int | None = None
    vlans: tuple[int, ...] = ()
    status: str = "decoded"
    reason: str | None = None
    incidents: list[str] = field(default_factory=list)
    tcp_flags: tuple[str, ...] = ()
    initiation: bool = False
    arp: dict[str, Any] | None = None

    def stop(self, status: str, reason: str) -> None:
        self.status, self.reason = status, reason
        if reason not in self.incidents:
            self.incidents.append(reason)
        self.source_port = self.destination_port = None
        self.initiation = False


def _mac(value: bytes) -> str:
    return ":".join(f"{byte:02x}" for byte in value)


def _transport(value: bytes, protocol: int, result: _Decoded) -> None:
    names = {6: "tcp", 17: "udp", 1: "icmp", 58: "icmpv6"}
    result.transport = names.get(protocol, "unknown")
    if protocol == 6:
        if len(value) < 20:
            result.stop("truncated", "TCP_HEADER_TRUNCATED")
            return
        header = (value[12] >> 4) * 4
        if header < 20:
            result.stop("malformed", "TCP_DATA_OFFSET_INVALID")
            return
        if header > len(value):
            result.stop("truncated", "TCP_OPTIONS_TRUNCATED")
            return
        if value[12] & 0x0E:
            result.stop("malformed", "TCP_RESERVED_BITS_SET")
            return
        offset = 20
        while offset < header:
            kind = value[offset]
            if kind == 0:
                if any(value[offset + 1 : header]):
                    result.stop("malformed", "TCP_OPTION_PADDING_INVALID")
                    return
                break
            if kind == 1:
                offset += 1
                continue
            if offset + 2 > header:
                result.stop("malformed", "TCP_OPTION_LENGTH_INVALID")
                return
            size = value[offset + 1]
            expected = {2: 4, 3: 3, 4: 2, 8: 10}.get(kind)
            if (
                size < 2
                or offset + size > header
                or (expected is not None and size != expected)
                or (kind == 5 and (size < 10 or (size - 2) % 8))
            ):
                result.stop("malformed", "TCP_OPTION_LENGTH_INVALID")
                return
            offset += size
        flags = value[13] | ((value[12] & 1) << 8)
        result.tcp_flags = tuple(
            name
            for bit, name in enumerate(
                ("FIN", "SYN", "RST", "PSH", "ACK", "URG", "ECE", "CWR", "NS")
            )
            if flags & (1 << bit)
        )
        result.source_port, result.destination_port = struct.unpack_from("!HH", value)
        result.initiation = bool(flags & 2) and not bool(flags & (1 | 4 | 16))
    elif protocol == 17:
        if len(value) < 8:
            result.stop("truncated", "UDP_HEADER_TRUNCATED")
            return
        source, destination, length = struct.unpack_from("!HHH", value)
        if length < 8:
            result.stop("malformed", "UDP_LENGTH_INVALID")
        elif length > len(value):
            result.stop("truncated", "UDP_DATAGRAM_TRUNCATED")
        else:
            result.source_port, result.destination_port = source, destination
    elif protocol in {1, 58}:
        if len(value) < 4:
            result.stop("truncated", "ICMP_HEADER_TRUNCATED")
        elif (protocol == 1 and result.ip_version != 4) or (
            protocol == 58 and result.ip_version != 6
        ):
            result.stop("malformed", "ICMP_ADDRESS_FAMILY_MISMATCH")
    else:
        result.stop("unsupported", "IP_TRANSPORT_UNSUPPORTED")


def _ipv4(value: bytes, result: _Decoded) -> None:
    result.ip_version = 4
    if len(value) < 20:
        result.stop("truncated", "IPV4_HEADER_TRUNCATED")
        return
    result.source_ip = str(ipaddress.IPv4Address(value[12:16]))
    result.destination_ip = str(ipaddress.IPv4Address(value[16:20]))
    header, length = (value[0] & 15) * 4, int.from_bytes(value[2:4], "big")
    if value[0] >> 4 != 4 or header < 20 or length < header or value[6] & 0x80:
        result.stop("malformed", "IPV4_HEADER_INVALID")
        return
    result.transport = {6: "tcp", 17: "udp", 1: "icmp"}.get(value[9], "unknown")
    fragmented = bool(int.from_bytes(value[6:8], "big") & 0x3FFF)
    if fragmented:
        result.stop("fragmented", "IPV4_FRAGMENT_NOT_REASSEMBLED")
    if header > len(value) or length > len(value):
        result.stop("truncated", "IPV4_PACKET_TRUNCATED")
    elif fragmented:
        return
    else:
        offset = 20
        while offset < header:
            option = value[offset]
            if option == 0:
                if any(value[offset + 1 : header]):
                    result.stop("malformed", "IPV4_OPTION_PADDING_INVALID")
                    return
                break
            if option == 1:
                offset += 1
                continue
            if offset + 2 > header:
                result.stop("malformed", "IPV4_OPTION_LENGTH_INVALID")
                return
            size = value[offset + 1]
            if size < 2 or offset + size > header:
                result.stop("malformed", "IPV4_OPTION_LENGTH_INVALID")
                return
            if option in {131, 137}:
                result.stop("unsupported", "IPV4_SOURCE_ROUTE_UNSUPPORTED")
                return
            # RFC 791's known options have mandatory fields beyond the TLV
            # prefix. A framed but semantically unimplemented option must not
            # supply transport or initiation evidence.
            if option == 7:  # Record Route: type, length, pointer, IPv4 slots.
                valid = size >= 3 and (size - 3) % 4 == 0 and value[offset + 2] >= 4
            elif option == 68:  # Timestamp: pointer and overflow/flag are mandatory.
                valid = size >= 4 and value[offset + 2] >= 5
                if valid:
                    flag = value[offset + 3] & 15
                    valid = flag in {0, 1, 3} and (size - 4) % (4 if flag == 0 else 8) == 0
            elif option == 136:  # Stream identifier.
                valid = size == 4
            else:
                result.stop("unsupported", "IPV4_OPTION_UNSUPPORTED")
                return
            if not valid:
                result.stop("malformed", "IPV4_OPTION_FIELDS_INVALID")
                return
            offset += size
        _transport(value[header:length], value[9], result)


def _ipv6(value: bytes, result: _Decoded, limits: CaptureLimits) -> None:
    result.ip_version = 6
    if len(value) < 40:
        result.stop("truncated", "IPV6_HEADER_TRUNCATED")
        return
    result.source_ip = str(ipaddress.IPv6Address(value[8:24]))
    result.destination_ip = str(ipaddress.IPv6Address(value[24:40]))
    if value[0] >> 4 != 6:
        result.stop("malformed", "IPV6_VERSION_INVALID")
        return
    length, protocol = int.from_bytes(value[4:6], "big"), value[6]
    result.transport = {6: "tcp", 17: "udp", 58: "icmpv6"}.get(protocol, "unknown")
    if length == 0 and len(value) > 40:
        result.stop("unsupported", "IPV6_JUMBOGRAM_UNSUPPORTED")
        return
    if length + 40 > len(value):
        result.stop("truncated", "IPV6_PACKET_TRUNCATED")
        return
    end, offset, extensions = length + 40, 40, 0
    while protocol in {0, 43, 44, 51, 60}:
        extensions += 1
        if extensions > limits.ipv6_extensions:
            result.stop("unsupported", "IPV6_EXTENSION_DEPTH_EXCEEDED")
            return
        if offset + 8 > end:
            result.stop("truncated", "IPV6_EXTENSION_TRUNCATED")
            return
        if protocol == 44:
            result.stop("fragmented", "IPV6_FRAGMENT_NOT_REASSEMBLED")
            return
        if protocol == 0 and offset != 40:
            result.stop("malformed", "IPV6_HOP_BY_HOP_POSITION_INVALID")
            return
        size = (value[offset + 1] + 2) * 4 if protocol == 51 else (value[offset + 1] + 1) * 8
        if protocol == 51 and size < 12:
            result.stop("malformed", "IPV6_AH_LENGTH_INVALID")
            return
        if offset + size > end:
            result.stop("truncated", "IPV6_EXTENSION_TRUNCATED")
            return
        if protocol == 43:
            result.stop("unsupported", "IPV6_ROUTING_HEADER_UNSUPPORTED")
            return
        if protocol in {0, 60}:
            cursor, option_end = offset + 2, offset + size
            unknown_option = False
            while cursor < option_end:
                kind = value[cursor]
                if kind == 0:  # Pad1 has no length byte.
                    cursor += 1
                    continue
                if cursor + 2 > option_end:
                    result.stop("malformed", "IPV6_OPTION_LENGTH_INVALID")
                    return
                option_size = value[cursor + 1] + 2
                if cursor + option_size > option_end:
                    result.stop("malformed", "IPV6_OPTION_LENGTH_INVALID")
                    return
                if kind == 1:
                    if any(value[cursor + 2 : cursor + option_size]):
                        result.stop("malformed", "IPV6_OPTION_PADDING_INVALID")
                        return
                else:
                    unknown_option = True
                cursor += option_size
            if unknown_option:
                result.stop("unsupported", "IPV6_OPTION_UNSUPPORTED")
                return
        protocol, offset = value[offset], offset + size
    _transport(value[offset:end], protocol, result)


def _decode(packet: Packet, limits: CaptureLimits) -> _Decoded:
    value, result = packet.data, _Decoded()
    ethertype: int | None = None
    if packet.linktype == 1:
        if len(value) < 14:
            result.stop("truncated", "ETHERNET_HEADER_TRUNCATED")
            return result
        result.destination_mac, result.source_mac = _mac(value[:6]), _mac(value[6:12])
        ethertype, offset = int.from_bytes(value[12:14], "big"), 14
        tags: list[int] = []
        while ethertype in {0x8100, 0x88A8}:
            if len(tags) >= 2:
                result.vlans = tuple(tags)
                result.stop("unsupported", "VLAN_DEPTH_EXCEEDED")
                return result
            if len(value) < offset + 4:
                result.vlans = tuple(tags)
                result.stop("truncated", "VLAN_HEADER_TRUNCATED")
                return result
            tags.append(int.from_bytes(value[offset : offset + 2], "big") & 0xFFF)
            ethertype, offset = int.from_bytes(value[offset + 2 : offset + 4], "big"), offset + 4
        result.vlans, value = tuple(tags), value[offset:]
    elif packet.linktype == 101:
        if not value:
            result.stop("truncated", "RAW_IP_HEADER_TRUNCATED")
            return result
        ethertype = {4: 0x0800, 6: 0x86DD}.get(value[0] >> 4)
    else:
        result.stop("unsupported", "LINKTYPE_UNSUPPORTED")
        return result
    if ethertype == 0x0800:
        _ipv4(value, result)
    elif ethertype == 0x86DD:
        _ipv6(value, result, limits)
    elif ethertype == 0x0806:
        result.transport = "arp"
        if len(value) < 8:
            result.stop("truncated", "ARP_HEADER_TRUNCATED")
        elif value[:6] != b"\x00\x01\x08\x00\x06\x04":
            result.stop("unsupported", "ARP_ADDRESS_FORMAT_UNSUPPORTED")
        elif len(value) < 28:
            result.stop("truncated", "ARP_ADDRESSES_TRUNCATED")
        else:
            result.ip_version = 4
            result.source_ip = str(ipaddress.IPv4Address(value[14:18]))
            result.destination_ip = str(ipaddress.IPv4Address(value[24:28]))
            opcode = int.from_bytes(value[6:8], "big")
            result.arp = {
                "metadata_version": 1,
                "opcode": opcode,
                "operation": {1: "request", 2: "reply"}.get(opcode, "unsupported"),
                "sender_protocol_address": result.source_ip,
                "target_protocol_address": result.destination_ip,
                "sender_hardware_address": _mac(value[8:14]),
                "target_hardware_address": _mac(value[18:24]),
                "ethernet_source_mac": result.source_mac,
                "ethernet_destination_mac": result.destination_mac,
                "ethernet_delivery": "broadcast"
                if result.destination_mac == "ff:ff:ff:ff:ff:ff"
                else "multicast"
                if result.destination_mac is not None and int(result.destination_mac[:2], 16) & 1
                else "unicast",
            }
            if opcode not in {1, 2}:
                result.stop("unsupported", "ARP_OPCODE_UNSUPPORTED")
    else:
        result.stop("unsupported", "NETWORK_PROTOCOL_UNSUPPORTED")
    if packet.link_errors:
        result.stop("malformed", "CAPTURE_LINK_ERRORS_REPORTED")
    elif packet.offloaded:
        result.stop("unsupported", "CAPTURE_SEGMENTATION_OFFLOAD_UNSUPPORTED")
    if packet.captured_length < packet.original_length:
        if result.status == "decoded":
            result.stop("truncated", "CAPTURE_RECORD_TRUNCATED")
        elif "CAPTURE_RECORD_TRUNCATED" not in result.incidents:
            result.incidents.append("CAPTURE_RECORD_TRUNCATED")
    return result


@dataclass(slots=True)
class _Budget:
    limits: CaptureLimits
    allocated: int = 0

    def reserve(self, amount: int) -> None:
        check_limit(
            "capture_aggregation_bytes", self.allocated + amount, self.limits.aggregation_bytes
        )
        self.allocated += amount

    def add(self, values: set[str], value: str | None) -> None:
        if value is not None and value not in values:
            check_limit("capture_metadata_values", len(values) + 1, 256)
            self.reserve(256 + len(value) * 4)
            values.add(value)


def _timestamp(packet: Packet) -> Fraction | None:
    if packet.timestamp is None:
        return None
    stamp = packet.timestamp
    return Fraction(stamp.ticks, stamp.denominator) + stamp.offset_seconds


def _stamp(value: Fraction | None) -> str | None:
    return f"{value.numerator}/{value.denominator}" if value is not None else None


def _reference(packet: Packet) -> dict[str, Any]:
    stamp = packet.timestamp
    return {
        "index": packet.index,
        "offset": packet.offset,
        "section": packet.section,
        "interface": packet.interface,
        "captured_length": packet.captured_length,
        "original_length": packet.original_length,
        "timestamp": None
        if stamp is None
        else {
            "ticks": stamp.ticks,
            "denominator": stamp.denominator,
            "offset_seconds": stamp.offset_seconds,
        },
    }


@dataclass(slots=True)
class _Flow:
    identity: str
    conversation: str
    observed: _Decoded
    linktype: int
    packets: int = 0
    captured_bytes: int = 0
    original_bytes: int = 0
    first: Fraction | None = None
    last: Fraction | None = None
    missing_timestamps: int = 0
    source_macs: set[str] = field(default_factory=set)
    destination_macs: set[str] = field(default_factory=set)
    interfaces: set[str] = field(default_factory=set)
    flags: set[str] = field(default_factory=set)
    reasons: set[str] = field(default_factory=set)
    samples: list[dict[str, Any]] = field(default_factory=list)
    initiations: list[dict[str, Any]] = field(default_factory=list)
    initiation_packets: int = 0

    def update(self, packet: Packet, observed: _Decoded, budget: _Budget) -> None:
        self.packets += 1
        self.captured_bytes += packet.captured_length
        self.original_bytes += packet.original_length
        timestamp = _timestamp(packet)
        if timestamp is not None:
            self.first = timestamp if self.first is None else min(self.first, timestamp)
            self.last = timestamp if self.last is None else max(self.last, timestamp)
        else:
            self.missing_timestamps += 1
        budget.add(self.source_macs, observed.source_mac)
        budget.add(self.destination_macs, observed.destination_mac)
        budget.add(self.interfaces, f"{packet.section}:{packet.interface}")
        for incident in observed.incidents:
            budget.add(self.reasons, incident)
        for flag in observed.tcp_flags:
            budget.add(self.flags, flag)
        if len(self.samples) < budget.limits.packet_samples:
            budget.reserve(1024)
            self.samples.append(_reference(packet))
        if observed.initiation and observed.status == "decoded":
            self.initiation_packets += 1
            if len(self.initiations) < budget.limits.packet_samples:
                budget.reserve(1024)
                self.initiations.append(_reference(packet))

    def output(self) -> dict[str, Any]:
        o = self.observed
        hints = [
            {"protocol": name, "level": "PORT_HINT", "port": port}
            for transport, port, name in _PORTS
            if o.transport == transport and port in {o.source_port, o.destination_port}
        ]
        return {
            "id": self.identity,
            "conversation_id": self.conversation,
            "source_ip": o.source_ip,
            "destination_ip": o.destination_ip,
            "source_port": o.source_port,
            "destination_port": o.destination_port,
            "transport": o.transport,
            "arp": o.arp,
            "transport_evidence": "TRANSPORT_OBSERVED"
            if o.status == "decoded" and o.transport in {"tcp", "udp", "icmp", "icmpv6"}
            else "UNKNOWN",
            "ip_version": o.ip_version,
            "vlans": list(o.vlans),
            "linktype": self.linktype,
            "status": o.status,
            "packets": self.packets,
            "captured_bytes": self.captured_bytes,
            "original_bytes": self.original_bytes,
            "first_timestamp": _stamp(self.first),
            "last_timestamp": _stamp(self.last),
            "missing_timestamps": self.missing_timestamps,
            "interfaces": sorted(self.interfaces),
            "source_macs": sorted(self.source_macs),
            "destination_macs": sorted(self.destination_macs),
            "samples": self.samples,
            "samples_omitted": self.packets - len(self.samples),
            "tcp_flags": sorted(self.flags),
            "initiation_evidence": self.initiations,
            "initiation_packets": self.initiation_packets,
            "initiation_evidence_omitted": self.initiation_packets - len(self.initiations),
            "protocol_hints": hints,
            "limitations": sorted(self.reasons),
        }


@dataclass(slots=True)
class _Host:
    ip: str
    version: int
    packets: int = 0
    source_macs: set[str] = field(default_factory=set)
    destination_macs: set[str] = field(default_factory=set)
    observation_roles: set[str] = field(default_factory=set)


def analyze_capture(path: Path, limits: CaptureLimits = CAPTURE_LIMITS) -> dict[str, Any]:
    """Decode a streaming capture into bounded, deterministic metadata aggregates."""
    budget = _Budget(limits)
    flows: dict[str, _Flow] = {}
    hosts: dict[str, _Host] = {}
    conversations: dict[str, list[str]] = {}
    coverage: Counter[str] = Counter()

    def consume(packet: Packet) -> None:
        o = _decode(packet, limits)
        coverage[o.status] += 1
        coverage["capture_records_truncated"] += int(
            packet.captured_length < packet.original_length
        )
        endpoints = [
            (o.source_ip or "", o.source_port if o.source_port is not None else -1),
            (o.destination_ip or "", o.destination_port if o.destination_port is not None else -1),
        ]
        group: list[object] = [sorted(endpoints), o.transport, o.ip_version, o.vlans]
        # ARP protocol fields describe message claims, not an IP conversation.
        # Keep distinct opcodes, claims and Ethernet delivery in separate groups.
        if o.arp is not None:
            group.append(o.arp)
        if o.source_ip is None and o.destination_ip is None:
            group.append(packet.linktype)
        conversation_id = "conversation-" + _digest(group)
        identity_fields: list[object] = [
            endpoints,
            o.transport,
            o.ip_version,
            o.vlans,
            o.status,
            packet.linktype,
        ]
        if o.arp is not None:
            identity_fields.append(o.arp)
        identity = "flow-" + _digest(identity_fields)
        if identity not in flows:
            check_limit("capture_flows", len(flows) + 1, limits.flows)
            if conversation_id not in conversations:
                check_limit("capture_conversations", len(conversations) + 1, limits.conversations)
                budget.reserve(2048)
                conversations[conversation_id] = []
            budget.reserve(8192)
            flows[identity] = _Flow(identity, conversation_id, o, packet.linktype)
            conversations[conversation_id].append(identity)
        flows[identity].update(packet, o, budget)
        host_evidence = [
            (o.source_ip, o.source_mac, "source", "packet_source"),
            (o.destination_ip, o.destination_mac, "destination", "packet_destination"),
        ]
        if o.transport == "arp":
            # A target may never have transmitted or existed. Zero SPA is the
            # unspecified address used by probes, not an observed host identity.
            host_evidence = (
                [
                    (
                        o.source_ip,
                        o.source_mac,
                        "source",
                        "arp_" + o.arp["operation"] + "_sender",
                    )
                ]
                if o.status == "decoded" and o.arp is not None and o.source_ip != "0.0.0.0"
                else []
            )
        for ip, mac, direction, role in host_evidence:
            if ip is None:
                continue
            if ip not in hosts:
                check_limit("capture_hosts", len(hosts) + 1, limits.hosts)
                budget.reserve(2048)
                hosts[ip] = _Host(ip, o.ip_version or 4)
            host = hosts[ip]
            host.packets += 1
            budget.add(host.source_macs if direction == "source" else host.destination_macs, mac)
            budget.add(host.observation_roles, role)

    metadata = scan_capture(path, consume=consume, limits=limits)
    grouped: list[dict[str, Any]] = []
    for identity, members in sorted(conversations.items()):
        values = [flows[key] for key in sorted(members)]
        initiating = {
            (
                f.observed.source_ip,
                f.observed.source_port,
                f.observed.destination_ip,
                f.observed.destination_port,
            )
            for f in values
            if f.initiation_packets
        }
        initiators = [f.identity for f in values if f.initiation_packets]
        first = [f.first for f in values if f.first is not None]
        last = [f.last for f in values if f.last is not None]
        observed = values[0].observed
        grouped.append(
            {
                "id": identity,
                "flow_ids": [f.identity for f in values],
                "transport": observed.transport,
                "ip_version": observed.ip_version,
                "vlans": list(observed.vlans),
                "linktypes": sorted({f.linktype for f in values}),
                "packets": sum(f.packets for f in values),
                "captured_bytes": sum(f.captured_bytes for f in values),
                "original_bytes": sum(f.original_bytes for f in values),
                "first_timestamp": _stamp(min(first)) if first else None,
                "last_timestamp": _stamp(max(last)) if last else None,
                "initiation_direction": "conflicting_syn"
                if len(initiating) > 1
                else "observed_syn"
                if initiating
                else "uncertain",
                "initiator_flow_id": min(initiators) if len(initiating) == 1 else None,
                "limitations": [
                    "Grouped observations; no deduplication or complete sessions inferred."
                ],
            }
        )
    report: dict[str, Any] = {
        "observation_version": 2,
        "catalog_version": 1,
        "capture": metadata,
        "hosts": [
            {
                "id": "host-" + _digest([h.version, h.ip]),
                "ip": h.ip,
                "ip_version": h.version,
                "packets": h.packets,
                "source_macs": sorted(h.source_macs),
                "destination_macs": sorted(h.destination_macs),
                "observation_roles": sorted(h.observation_roles),
            }
            for _, h in sorted(hosts.items())
        ],
        "flows": [flow.output() for _, flow in sorted(flows.items())],
        "conversations": grouped,
        "coverage": {
            "packets": metadata["packets"],
            **{
                name: coverage[name]
                for name in ("decoded", "truncated", "malformed", "fragmented", "unsupported")
            },
            "interpreted_packets": coverage["decoded"],
            "uninterpreted_packets": metadata["packets"] - coverage["decoded"],
            "complete_file_scan": True,
            "capture_records_truncated": coverage["capture_records_truncated"],
        },
        "aggregation_accounted_bytes": budget.allocated,
        "limitations": list(_LIMITATIONS),
    }
    report["observations_sha256"] = _digest(report)
    return report
