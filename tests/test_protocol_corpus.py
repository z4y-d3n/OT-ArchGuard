"""Original synthetic corpus provenance and fail-closed development tooling."""

import copy
import hashlib
import json
import struct
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from tools.protocol_corpus import load_manifest, verify_file

CORPUS = Path(__file__).parent / "fixtures" / "protocol-corpus"


def synthetic_capture() -> bytes:
    """Hand-authored framing, independent of every OT-ArchGuard decoder.

    RFC 791/793/894 headers; Modbus guide MBAP example structure; DCP Identify
    AllSelector per the independently maintained PLC4X grammar. All values are
    fictional. Checksums are zero and no checksum validation is claimed.
    """
    ethernet = bytes.fromhex("0200000000200200000000100800")
    packets = []
    for source, destination, pdu in (
        (40000, 502, bytes.fromhex("000100000006010300000001")),
        (502, 40000, bytes.fromhex("0001000000050103020000")),
    ):
        addresses = [bytes.fromhex("c000020a"), bytes.fromhex("c0000214")]
        if source == 502:
            addresses.reverse()
        ip = struct.pack("!BBHHHBBH4s4s", 0x45, 0, 40 + len(pdu), 1, 0, 64, 6, 0, *addresses)
        tcp = struct.pack("!HHIIBBHHH", source, destination, 1, 1, 0x50, 0x18, 4096, 0, 0)
        frame = ethernet + ip + tcp + pdu
        packets.append(frame + bytes(max(0, 60 - len(frame))))
    dcp = bytes.fromhex("010ecf0000000200000000108892fefe05000000000100000004ffff0000")
    unrelated = bytes.fromhex("02000000002002000000001088928000")
    packets += [dcp + bytes(60 - len(dcp)), unrelated + bytes(60 - len(unrelated))]
    result = struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1)
    for index, frame in enumerate(packets):
        result += struct.pack("<IIII", 1_600_000_000 + index, 0, len(frame), len(frame)) + frame
    return result


def _write(tmp_path: Path, value: Any) -> Path:
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_original_fixture_generation_and_integrity() -> None:
    manifest = load_manifest(CORPUS / "manifest.json")
    data = (CORPUS / "synthetic-industrial.pcap").read_bytes()
    assert data == synthetic_capture()
    result = verify_file(manifest, "synthetic-industrial", CORPUS / "synthetic-industrial.pcap")
    assert result["sha256"] == hashlib.sha256(data).hexdigest()
    assert result["status"] == "integrity_verified"
    receipt = json.loads((CORPUS / "tshark-receipt.json").read_text(encoding="utf-8"))
    assert receipt["input_sha256"] == result["sha256"]
    assert receipt["tool_version"].startswith("TShark (Wireshark) 4.6.7")
    assert len(receipt["packets"]) == 4
    assert receipt["packets"][0]["modbus.func_code"] == "3"
    assert receipt["packets"][2]["pn_dcp.service_id"] == "5"
    assert receipt["packets"][3]["pn_dcp.service_id"] == ""


def test_external_candidates_are_explicitly_unverified() -> None:
    manifest = load_manifest(CORPUS / "manifest.json")
    external = [e for e in manifest["entries"] if e["tier"] != 1]
    assert external
    for entry in external:
        assert entry["review_status"] == "candidate"
        assert entry["sha256"] is None
        assert entry["size_bytes"] is None
        assert entry["sensitivity_review"] == "not_reviewed"
        with pytest.raises(ValueError, match="not approved"):
            verify_file(manifest, entry["id"], CORPUS / "synthetic-industrial.pcap")


@pytest.mark.parametrize("version", [True, False, 0, 2, "1", None])
def test_future_or_mistyped_versions_are_rejected(tmp_path: Path, version: Any) -> None:
    manifest = load_manifest(CORPUS / "manifest.json")
    manifest["manifest_version"] = version
    with pytest.raises(ValueError, match="version"):
        load_manifest(_write(tmp_path, manifest))


@pytest.mark.parametrize(
    "field,value",
    [
        ("id", "../escape"),
        ("id", "a" * 65),
        ("original_filename", "../outside.pcap"),
        ("original_filename", "/absolute.pcap"),
        ("original_filename", "C:\\outside.pcap"),
        ("original_filename", "a//b.pcap"),
        ("source_url", "http://example.com/file.pcap"),
        ("source_url", "https://user:secret@example.com/file.pcap"),
        ("sha256", "A" * 64),
        ("size_bytes", True),
        ("size_bytes", 16 * 1024 * 1024 + 1),
        ("tier", True),
        ("protocol_families", ["bacnet"]),
        ("source_organization", "bad\ntext"),
        ("review_status", "future_approved"),
        ("redistribution", "unknown"),
        ("sensitivity_review", "not_reviewed"),
    ],
)
def test_adversarial_manifest_entry_rejected(tmp_path: Path, field: str, value: Any) -> None:
    manifest = load_manifest(CORPUS / "manifest.json")
    manifest["entries"][0][field] = value
    with pytest.raises(ValueError):
        load_manifest(_write(tmp_path, manifest))


def test_duplicate_and_missing_fields_are_rejected(tmp_path: Path) -> None:
    manifest = load_manifest(CORPUS / "manifest.json")
    manifest["entries"].append(copy.deepcopy(manifest["entries"][0]))
    with pytest.raises(ValueError, match="Duplicate"):
        load_manifest(_write(tmp_path, manifest))
    manifest["entries"].pop()
    del manifest["entries"][0]["license"]
    with pytest.raises(ValueError, match="fields"):
        load_manifest(_write(tmp_path, manifest))


@pytest.mark.parametrize(
    "text",
    [
        '{"manifest_version":1,"manifest_version":1}',
        '{"number":NaN}',
        "[" * 1200 + "]" * 1200,
        '{"entries":',
        "x" * (128 * 1024 + 1),
    ],
    ids=["duplicate-key", "nonfinite", "deep-nesting", "truncated", "oversized"],
)
def test_hostile_manifest_json(tmp_path: Path, text: str) -> None:
    path = tmp_path / "hostile.json"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError):
        load_manifest(path)


def test_byte_tampering_and_lfs_pointers_are_rejected(tmp_path: Path) -> None:
    manifest = load_manifest(CORPUS / "manifest.json")
    path = tmp_path / "capture.pcap"
    path.write_bytes(synthetic_capture() + b"x")
    with pytest.raises(ValueError, match="identity"):
        verify_file(manifest, "synthetic-industrial", path)
    path.write_bytes(b"version https://git-lfs.github.com/spec/v1\noid sha256:abc\nsize 123\n")
    with pytest.raises(ValueError, match="LFS"):
        verify_file(manifest, "synthetic-industrial", path)


@pytest.mark.parametrize(
    "field", ["capture_type", "redistribution", "sensitivity_review", "review_status"]
)
def test_unhashable_classifications_are_controlled(tmp_path: Path, field: str) -> None:
    manifest = load_manifest(CORPUS / "manifest.json")
    manifest["entries"][0][field] = []
    with pytest.raises(ValueError):
        load_manifest(_write(tmp_path, manifest))


def test_manifest_and_verification_cli() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "tools.protocol_corpus",
            "--manifest",
            str(CORPUS / "manifest.json"),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(completed.stdout)["approved"] == 1


def test_symlink_input_rejected(tmp_path: Path) -> None:
    link = tmp_path / "linked.json"
    try:
        link.symlink_to((CORPUS / "manifest.json").resolve())
    except OSError:
        pytest.skip("Creating symlinks requires host privilege")
    with pytest.raises(ValueError, match="links"):
        load_manifest(link)
