"""Fictional deterministic capture writers. Never open sockets or capture live traffic."""

import ipaddress
import struct
from pathlib import Path


def tcp_frame(source: str, destination: str, sport: int, dport: int, flags: int = 2) -> bytes:
    tcp = struct.pack("!HHIIBBHHH", sport, dport, 1, 0, 5 << 4, flags, 8192, 0, 0)
    return ipv4_frame(source, destination, 6, tcp)


def ipv4_frame(source: str, destination: str, protocol: int, body: bytes) -> bytes:
    header = struct.pack(
        "!BBHHHBBH4s4s",
        0x45,
        0,
        20 + len(body),
        1,
        0,
        64,
        protocol,
        0,
        ipaddress.IPv4Address(source).packed,
        ipaddress.IPv4Address(destination).packed,
    )
    words = struct.unpack("!10H", header)
    checksum = sum(words)
    checksum = (checksum & 65535) + (checksum >> 16)
    checksum = (checksum & 65535) + (checksum >> 16)
    header = header[:10] + struct.pack("!H", (~checksum) & 65535) + header[12:]
    return bytes.fromhex("0200000000200200000000100800") + header + body


def demo_frames(*, extended: bool = False) -> list[bytes]:
    frames = [
        tcp_frame("192.0.2.10", "192.0.2.20", 40000, 502),
        tcp_frame("192.0.2.20", "192.0.2.10", 502, 40000, 0x12),
        tcp_frame("192.0.2.11", "192.0.2.20", 40001, 502),
        tcp_frame("192.0.2.10", "192.0.2.20", 40002, 102),
        tcp_frame("192.0.2.20", "192.0.2.10", 502, 49000, 0x10),
        ipv4_frame("192.0.2.11", "192.0.2.20", 17, struct.pack("!HHHH", 41000, 47808, 8, 0)),
        tcp_frame("192.0.2.99", "192.0.2.20", 40003, 502),
        tcp_frame("192.0.2.10", "192.0.2.98", 40004, 502),
    ]
    # ARP request claims sender protocol address; no owner or adjacency inference.
    frames.append(
        bytes.fromhex("ffffffffffff0200000000100806")
        + struct.pack("!HHBBH", 1, 0x0800, 6, 4, 1)
        + bytes.fromhex("020000000010c000020a000000000000c0000214")
    )
    ipv6 = struct.pack(
        "!IHBB16s16s",
        6 << 28,
        8,
        58,
        64,
        ipaddress.IPv6Address("2001:db8::10").packed,
        ipaddress.IPv6Address("2001:db8::20").packed,
    )
    frames.append(
        bytes.fromhex("02000000002002000000001086dd") + ipv6 + bytes.fromhex("8000000000010001")
    )
    if extended:
        frames.extend(
            [
                bytes.fromhex("0200000000100200000000200806")
                + struct.pack("!HHBBH", 1, 0x0800, 6, 4, 2)
                + bytes.fromhex("020000000020c0000214020000000010c000020a"),
                bytes.fromhex("02000000002002000000001088b5") + b"fictional unsupported metadata",
            ]
        )
    return frames


def write_pcap(path: Path, count: int = 10, *, cardinality: int = 0, skew: bool = False) -> None:
    frames = demo_frames()
    with path.open("xb") as stream:
        stream.write(struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1))
        for index in range(count):
            if cardinality and (not skew or index % 10 == 0):
                ip = str(
                    ipaddress.IPv4Address(
                        int(ipaddress.IPv4Address("198.18.0.1")) + index % cardinality
                    )
                )
                frame = tcp_frame(ip, "192.0.2.20", 40000, 502)
            else:
                frame = frames[index % len(frames)]
            stream.write(
                struct.pack(
                    "<IIII",
                    1_700_000_000 + index // 1_000_000,
                    index % 1_000_000,
                    len(frame),
                    len(frame),
                )
            )
            stream.write(frame)


def _block(kind: int, body: bytes) -> bytes:
    size = 12 + len(body)
    return struct.pack("<II", kind, size) + body + struct.pack("<I", size)


def write_pcapng(path: Path, *, extended: bool = False) -> None:
    with path.open("xb") as stream:
        stream.write(_block(0x0A0D0D0A, struct.pack("<IHHq", 0x1A2B3C4D, 1, 0, -1)))
        stream.write(_block(1, struct.pack("<HHI", 1, 0, 65535)))
        for index, frame in enumerate(demo_frames(extended=extended)):
            ticks = 1_700_000_000_000_000 + index
            padding = b"\x00" * ((-len(frame)) % 4)
            stream.write(
                _block(
                    6,
                    struct.pack(
                        "<IIIII", 0, ticks >> 32, ticks & 0xFFFFFFFF, len(frame), len(frame)
                    )
                    + frame
                    + padding,
                )
            )


def plant_model() -> dict[str, object]:
    names = {
        "eng": "Engineering workstation",
        "hmi": "HMI",
        "plc": "Simulated PLC",
        "historian": "Historian",
        "fw": "Declared boundary device",
    }
    addresses = {"eng": 10, "hmi": 11, "plc": 20, "historian": 30, "fw": 1}
    edges = [
        {
            "id": f"t_{src}_plc",
            "source_interface_id": f"{src}_net",
            "destination_interface_id": "plc_net",
        }
        for src in ("eng", "hmi")
    ]
    return {
        "schema_version": 1,
        "architecture_id": "fictional_capture_plant",
        "revision": "demo_1",
        "suc": {
            "id": "fictional_plant",
            "name": "Fictional capture demonstration",
            "purpose": "Offline evidence tutorial.",
            "controlled_process": "No real process.",
            "boundary_description": "Finite single-zone teaching plant; boundary is declared only.",
            "completeness_assertion": "Synthetic inventory only; no operational completeness claim",
            "access_points": [],
            "external_dependencies": [],
        },
        "zones": [
            {
                "id": "control",
                "name": "Control",
                "purpose": "Fictional supervision.",
                "scope": "internal",
                "grouping_rationale": "Teaching example only.",
                "safety_designation": "non_safety",
            }
        ],
        "assets": [
            {
                "id": key,
                "name": name,
                "role": name,
                "zone_id": "control",
                "kind": "boundary_device" if key == "fw" else "endpoint",
                "scope": "internal",
                "domain_classification": "iacs",
                "safety_classification": "non_safety",
                "criticality": "medium",
            }
            for key, name in names.items()
        ],
        "interfaces": [
            {
                "id": f"{key}_net",
                "asset_id": key,
                "placement_zone_id": "control",
                "ipv4": f"192.0.2.{addresses[key]}/24",
            }
            for key in names
        ],
        "conduits": [],
        "transport_edges": edges,
        "forwarding_edges": [],
        "services": [
            {
                "id": "svc_plc",
                "asset_id": "plc",
                "interface_id": "plc_net",
                "protocol": "tcp",
                "destination_ports": [{"start": 502, "end": 502}],
            },
            {
                "id": "svc_history",
                "asset_id": "historian",
                "interface_id": "historian_net",
                "protocol": "tcp",
                "destination_ports": [{"start": 4840, "end": 4840}],
            },
        ],
        "rules": [
            {
                "id": "allow_eng_plc",
                "edge_ids": ["t_eng_plc"],
                "source": {"asset_ids": ["eng"]},
                "destination": {"asset_ids": ["plc"]},
                "protocol": "tcp",
                "destination_ports": [{"start": 502, "end": 502}],
                "effect": "allow",
            }
        ],
        "intents": [],
        "scenarios": [],
    }
