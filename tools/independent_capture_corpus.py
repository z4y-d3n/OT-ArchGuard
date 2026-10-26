"""Rebuild fictional V13-14 specimens without the product's fixture generators.

Requires optional, already installed Wireshark tools only when rebuilding. Tests
consume checked-in specimens and reference receipts without external software.
No sockets, interface enumeration, capture drivers, or live capture are used.
"""

import argparse
import hashlib
import json
import shutil
import struct
import subprocess
from pathlib import Path
from typing import Any


def _block(kind: int, body: bytes, endian: str = "<") -> bytes:
    length = 12 + len(body)
    return struct.pack(endian + "II", kind, length) + body + struct.pack(endian + "I", length)


def _option(code: int, value: bytes, endian: str = "<") -> bytes:
    return struct.pack(endian + "HH", code, len(value)) + value + bytes(-len(value) % 4)


def _section(endian: str = "<", major: int = 1) -> bytes:
    return _block(0x0A0D0D0A, struct.pack(endian + "IHHq", 0x1A2B3C4D, major, 0, -1), endian)


def _interface(link: int = 1, endian: str = "<", options: bytes = b"") -> bytes:
    return _block(1, struct.pack(endian + "HHI", link, 0, 65535) + options, endian)


def _enhanced(frame: bytes, interface: int = 0, ticks: int = 1, endian: str = "<") -> bytes:
    body = struct.pack(endian + "IIIII", interface, 0, ticks, len(frame), len(frame))
    return _block(6, body + frame + bytes(-len(frame) % 4), endian)


def _classic(frames: list[bytes], endian: str = "<", nano: bool = False, link: int = 1) -> bytes:
    magic = 0xA1B23C4D if nano else 0xA1B2C3D4
    result = struct.pack(endian + "IHHIIII", magic, 2, 4, 0, 0, 65535, link)
    for index, frame in enumerate(frames):
        result += struct.pack(endian + "IIII", 100 + index, 123456, len(frame), len(frame))
        result += frame
    return result


def reference_frames() -> list[bytes]:
    """Hand-authored RFC 791/8200/826 headers, independent of capture_workloads."""
    ethernet = "020000000020020000000010"
    ip4 = "450000280001000040060000c000020ac0000214"
    tcp = "9c4001f600000001000000005002100000000000"
    ip6 = "6000000000083a40" + "20010db8000000000000000000000010"
    ip6 += "20010db8000000000000000000000020"
    return [
        bytes.fromhex(ethernet + "0800" + ip4 + tcp),
        bytes.fromhex(ethernet + "08004500001c0002000040110000c000020ac0000214a028bac000080000"),
        bytes.fromhex(ethernet + "08004500001c0003000040010000c000020ac00002140800000000010001"),
        bytes.fromhex(ethernet + "86dd" + ip6 + "8000000000010001"),
        bytes.fromhex(
            "ffffffffffff02000000001008060001080006040001020000000010c000020a000000000000c0000214"
        ),
        bytes.fromhex(ethernet + "810000640800" + ip4 + tcp),
        bytes.fromhex(ethernet + "0800450000280001200040060000c000020ac0000214" + tcp),
        bytes.fromhex(ethernet + "0800450000140004000040060000c000020ac0000214"),
        bytes.fromhex(ethernet + "0800" + ip4 + tcp[:24] + "4002" + tcp[28:]),
        bytes.fromhex(ethernet[:16]),
        bytes.fromhex(ethernet + "86dd" + ip6.replace("00083a40", "00140640") + tcp),
        bytes.fromhex(ethernet + "86dd" + ip6.replace("00083a40", "00081140") + "a028bac000080000"),
    ]


def _run(command: list[str], cwd: Path) -> str:
    return subprocess.run(
        command, cwd=cwd, check=True, capture_output=True, text=True, encoding="utf-8"
    ).stdout


def _tool(name: str, directory: Path | None) -> str:
    found = str(directory / (name + ".exe")) if directory else shutil.which(name)
    if not found or not Path(found).is_file():
        raise RuntimeError(f"Optional corpus rebuild tool unavailable: {name}")
    return found


FIELDS = (
    "frame.number",
    "frame.interface_id",
    "frame.time_epoch",
    "frame.cap_len",
    "frame.len",
    "eth.src",
    "eth.dst",
    "ip.src",
    "ip.dst",
    "ipv6.src",
    "ipv6.dst",
    "ip.proto",
    "ipv6.nxt",
    "tcp.srcport",
    "tcp.dstport",
    "udp.srcport",
    "udp.dstport",
    "vlan.id",
    "arp.hw.type",
    "arp.proto.type",
    "arp.hw.size",
    "arp.proto.size",
    "arp.opcode",
    "arp.src.hw_mac",
    "arp.dst.hw_mac",
    "arp.src.proto_ipv4",
    "arp.dst.proto_ipv4",
)


def build(directory: Path, wireshark: Path | None) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    text2pcap = _tool("text2pcap", wireshark)
    tshark = _tool("tshark", wireshark)
    frames = reference_frames()
    specimens: list[dict[str, Any]] = []

    def put(
        name: str,
        data: bytes,
        packets: int | None,
        features: list[str],
        error: str | None = None,
        origin: str = "spec-authored-v1",
    ) -> None:
        (directory / name).write_bytes(data)
        specimens.append(
            {
                "file": name,
                "sha256": hashlib.sha256(data).hexdigest(),
                "bytes": len(data),
                "packets": packets,
                "error": error,
                "features": features,
                "origin": origin,
            }
        )

    for endian, label in (("<", "le"), (">", "be")):
        for nano, precision in ((False, "us"), (True, "ns")):
            put(
                f"spec-{label}-{precision}.data",
                _classic(frames[:2], endian, nano),
                2,
                ["pcap", label, precision, "multiple-packets", "extension-independent"],
            )
    put("spec-empty.data", _classic([]), 0, ["pcap", "empty"])
    put(
        "spec-unsupported-link.data",
        _classic([b"fictional"], link=147),
        1,
        ["pcap", "unsupported-linktype"],
    )
    put(
        "spec-truncated.data",
        _classic(frames[:1])[:-1],
        None,
        ["pcap", "truncated-file"],
        "CAPTURE_INVALID",
    )
    options = _option(9, b"\x82") + _option(14, struct.pack("<q", -3))
    options += _option(65000, b"xyz") + _option(0, b"")
    transition = _section() + _interface(options=options) + _interface(link=147)
    transition += _enhanced(frames[0], ticks=7) + _enhanced(b"fictional", interface=1)
    transition += _block(0x12345678, bytes(4))
    transition += _block(
        3, struct.pack("<I", len(frames[1])) + frames[1] + bytes(-len(frames[1]) % 4)
    )
    transition += (
        _section(">")
        + _interface(
            endian=">", options=_option(9, b"\x03", ">") + _option(14, struct.pack(">q", 4), ">")
        )
        + _enhanced(frames[2], ticks=7, endian=">")
    )
    put(
        "spec-sections.data",
        transition,
        4,
        [
            "pcapng",
            "multiple-sections",
            "multiple-interfaces",
            "endianness-transition",
            "epb",
            "spb",
            "binary-resolution",
            "decimal-resolution",
            "timestamp-offset",
            "unknown-block",
            "unknown-option",
            "alignment-padding",
            "mixed-encapsulation",
        ],
    )
    for name, data, error in (
        ("unsupported-section", _section(major=2), "CAPTURE_INVALID"),
        ("inconsistent-length", transition[:-4] + struct.pack(">I", 12), "CAPTURE_INVALID"),
        (
            "invalid-interface",
            _section() + _interface() + _enhanced(frames[0], interface=1),
            "CAPTURE_INVALID",
        ),
        (
            "hostile-block",
            b"\x0a\x0d\x0d\x0a" + struct.pack("<II", 0x7FFFFFFC, 0x1A2B3C4D),
            "LIMIT_EXCEEDED",
        ),
        (
            "hostile-record",
            _classic([]) + struct.pack("<IIII", 1, 0, 0xFFFFFFFF, 0xFFFFFFFF),
            "LIMIT_EXCEEDED",
        ),
    ):
        put(f"spec-{name}.data", data, None, ["hostile", name], error)

    lines: list[str] = []
    for index, frame in enumerate(frames):
        lines.append(f"2020-01-01T00:00:{index:02d}.123456789Z")
        for offset in range(0, len(frame), 16):
            lines.append(
                f"{offset:06x}  " + " ".join(f"{b:02x}" for b in frame[offset : offset + 16])
            )
        lines.append("")
    (directory / "fictional-frames.txt").write_text("\n".join(lines), encoding="ascii")
    writer_version = _run([text2pcap, "--version"], directory).splitlines()[0]
    for kind in ("pcap", "nsecpcap", "pcapng"):
        name = f"text2pcap-{kind}.data"
        _run([text2pcap, "-q", "-t", "ISO", "-F", kind, "fictional-frames.txt", name], directory)
        put(
            name,
            (directory / name).read_bytes(),
            len(frames),
            [
                kind,
                "ethernet",
                "ipv4",
                "ipv6",
                "tcp",
                "udp",
                "icmp",
                "icmpv6",
                "arp",
                "vlan",
                "fragmented",
                "truncated-traffic",
                "malformed-header",
                "missing-transport",
            ],
            origin=writer_version,
        )
    command = [
        tshark,
        "-n",
        "-r",
        "text2pcap-pcapng.data",
        "-T",
        "fields",
        "-E",
        "separator=\t",
        "-E",
        "occurrence=f",
    ]
    for field in FIELDS:
        command += ["-e", field]
    rows = _run(command, directory).splitlines()
    reference = {
        "decoder": _run([tshark, "--version"], directory).splitlines()[0],
        "input_sha256": next(
            s["sha256"] for s in specimens if s["file"] == "text2pcap-pcapng.data"
        ),
        "command": "tshark -n -r text2pcap-pcapng.data -T fields -E separator=TAB -E occurrence=f "
        + " ".join("-e " + field for field in FIELDS),
        "rows": [dict(zip(FIELDS, row.split("\t"), strict=True)) for row in rows],
    }
    container_reference: dict[str, Any] = {}
    for specimen in specimens:
        if specimen["error"] is not None:
            continue
        decoded = json.loads(_run([tshark, "-n", "-r", specimen["file"], "-T", "json"], directory))
        container_reference[specimen["file"]] = {
            "sha256": specimen["sha256"],
            "packets": [
                {
                    key: item["_source"]["layers"]["frame"].get(key)
                    for key in (
                        "frame.number",
                        "frame.interface_id",
                        "frame.time_epoch",
                        "frame.cap_len",
                        "frame.len",
                    )
                }
                for item in decoded
            ],
        }
    reference["containers"] = container_reference
    (directory / "reference-decoder.json").write_text(
        json.dumps(reference, indent=2) + "\n", encoding="utf-8"
    )
    manifest = {
        "corpus_version": 1,
        "privacy": "Original fictional documentation addresses only",
        "license": "Apache-2.0; original fixtures; no redistributed Wireshark code",
        "writer": writer_version,
        "specimens": specimens,
    }
    (directory / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--wireshark-bin", type=Path)
    args = parser.parse_args()
    build(args.output.resolve(), args.wireshark_bin)


if __name__ == "__main__":
    main()
