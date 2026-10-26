"""Original fictional seven-family wire workloads, independent of product decoders."""

import struct
from pathlib import Path

# Published field layouts; no product decoder is used to manufacture these bytes.
TCP_MESSAGES = (
    ("modbus_tcp", 502, bytes.fromhex("000100000006010300000001")),
    (
        "ethernet_ip",
        44818,
        struct.pack("<HHII8sI", 0x65, 4, 1, 0, bytes(8), 0) + bytes.fromhex("01000000"),
    ),
    ("s7comm", 102, bytes.fromhex("0300001902f08032010000000100080000f0000001000101e0")),
    ("iec104", 2404, bytes.fromhex("680407000000")),
    ("opcua_binary", 4840, b"ACKF" + struct.pack("<6I", 28, 0, 65536, 65536, 0, 0)),
    ("dnp3", 20000, bytes.fromhex("056405c001000004e921")),
)
DCP = bytes.fromhex("fefe05000000000100000004ffff0000")


def ethernet(payload: bytes, ethertype: int = 0x0800) -> bytes:
    return bytes.fromhex("020000000020020000000010") + struct.pack("!H", ethertype) + payload


def tcp_frame(payload: bytes, port: int, *, fragments: int = 0) -> bytes:
    tcp = struct.pack("!HHIIBBHHH", 42000, port, 1, 0, 0x50, 0x18, 4096, 0, 0) + payload
    ip = struct.pack(
        "!BBHHHBBH4s4s",
        0x45,
        0,
        20 + len(tcp),
        1,
        fragments,
        64,
        6,
        0,
        bytes.fromhex("c000020a"),
        bytes.fromhex("c0000214"),
    )
    return ethernet(ip + tcp)


def capture(path: Path, frames: list[bytes], *, linktype: int = 1, truncate: bool = False) -> Path:
    with path.open("xb") as stream:
        stream.write(struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 262144, linktype))
        for index, frame in enumerate(frames):
            stream.write(
                struct.pack("<IIII", 1600000000 + index, 0, len(frame) - int(truncate), len(frame))
            )
            stream.write(frame[:-1] if truncate else frame)
    return path


def seven_frames() -> list[bytes]:
    return [tcp_frame(payload, port) for _, port, payload in TCP_MESSAGES] + [ethernet(DCP, 0x8892)]
