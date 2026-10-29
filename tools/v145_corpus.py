"""Rebuild the original V14-05 corpus without importing product code or networking.

The JSON is a fixed development fixture, never a runtime protocol definition.
Expected interpretations were authored from the cited framing references, then
compared with a separately installed TShark executable. No decoder output feeds
the fixture builder.
"""

import argparse
import hashlib
import json
import struct
from pathlib import Path
from typing import Any

DIRECTORY = Path(__file__).resolve().parents[1] / "tests/fixtures/protocol-corpus"
SPECIFICATION = DIRECTORY / "v145-cases.json"
CAPTURE = DIRECTORY / "v145-equivalence.pcap"


def frame(case: dict[str, Any]) -> bytes:
    payload = bytes.fromhex(case["wire_hex"])
    macs = bytes.fromhex("020000000020020000000010")
    if case["protocol"] == "profinet_dcp":
        # Deliberately retain 802.1Q framing in the original source bytes.
        return (macs + bytes.fromhex("810000258892") + payload).ljust(60, b"\x00")
    reverse = case.get("reverse", False)
    source, destination = (case["port"], 42000) if reverse else (42000, case["port"])
    tcp = struct.pack("!HHIIBBHHH", source, destination, 1, 0, 0x50, 0x18, 4096, 0, 0)
    addresses = (bytes.fromhex("c000020a"), bytes.fromhex("c0000214"))
    if reverse:
        addresses = addresses[::-1]
    ip = struct.pack("!BBHHHBBH4s4s", 0x45, 0, 40 + len(payload), 1, 0, 64, 6, 0, *addresses)
    return (macs + bytes.fromhex("0800") + ip + tcp + payload).ljust(60, b"\x00")


def build(specification: dict[str, Any]) -> bytes:
    result = bytearray(struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1))
    for index, case in enumerate(specification["cases"]):
        packet = frame(case)
        result.extend(struct.pack("<IIII", 1_600_000_000 + index, 0, len(packet), len(packet)))
        result.extend(packet)
    return bytes(result)


def verify() -> dict[str, Any]:
    specification = json.loads(SPECIFICATION.read_text(encoding="utf-8"))
    actual = CAPTURE.read_bytes()
    if actual != build(specification):
        raise ValueError("Committed corpus differs from its independent literal builder")
    digest = hashlib.sha256(actual).hexdigest()
    if digest != specification["capture_sha256"] or len(actual) != specification["capture_bytes"]:
        raise ValueError("Corpus byte identity differs from its reviewed specification")
    return {
        "status": "integrity_verified",
        "capture_sha256": digest,
        "capture_bytes": len(actual),
        "packets": len(specification["cases"]),
        "specification_sha256": hashlib.sha256(SPECIFICATION.read_bytes()).hexdigest(),
        "input_origin": "original_fictional_synthetic",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = json.dumps(verify(), sort_keys=True, indent=2) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result, encoding="utf-8")
    print(result, end="")


if __name__ == "__main__":
    main()
