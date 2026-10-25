"""Independent binary builders and adversarial oracles for capture container contract 1."""

import hashlib
import io
import os
import random
import struct
from dataclasses import replace
from pathlib import Path
from typing import BinaryIO

import pytest

from otarchguard.capture.contract import CAPTURE_LIMITS, Packet, Timestamp
from otarchguard.capture.parser import scan_capture
from otarchguard.diagnostics import ModelError


def pcap(
    data: bytes = b"abc",
    *,
    endian: str = "<",
    nano: bool = False,
    seconds: int = 17,
    fraction: int = 23,
    original: int | None = None,
    snaplen: int = 65535,
    linktype: int = 1,
) -> bytes:
    magic = 0xA1B23C4D if nano else 0xA1B2C3D4
    return (
        struct.pack(endian + "IHHIIII", magic, 2, 4, 0, 0, snaplen, linktype)
        + struct.pack(
            endian + "IIII",
            seconds,
            fraction,
            len(data),
            len(data) if original is None else original,
        )
        + data
    )


def block(kind: int, body: bytes, endian: str = "<") -> bytes:
    assert len(body) % 4 == 0
    length = len(body) + 12
    return struct.pack(endian + "II", kind, length) + body + struct.pack(endian + "I", length)


def option(code: int, value: bytes, endian: str = "<") -> bytes:
    return struct.pack(endian + "HH", code, len(value)) + value + b"\x00" * ((-len(value)) % 4)


def section(endian: str = "<", *, length: int = -1, options: bytes = b"") -> bytes:
    return block(
        0x0A0D0D0A, struct.pack(endian + "IHHq", 0x1A2B3C4D, 1, 0, length) + options, endian
    )


def interface(
    endian: str = "<", *, linktype: int = 1, snaplen: int = 65535, options: bytes = b""
) -> bytes:
    return block(1, struct.pack(endian + "HHI", linktype, 0, snaplen) + options, endian)


def enhanced(
    data: bytes = b"abc",
    endian: str = "<",
    *,
    interface_id: int = 0,
    ticks: int = 123456789,
    original: int | None = None,
    options: bytes = b"",
) -> bytes:
    return block(
        6,
        struct.pack(
            endian + "IIIII",
            interface_id,
            ticks >> 32,
            ticks & 0xFFFFFFFF,
            len(data),
            len(data) if original is None else original,
        )
        + data
        + b"\x00" * ((-len(data)) % 4)
        + options,
        endian,
    )


def simple(data: bytes = b"abc", *, original: int | None = None, endian: str = "<") -> bytes:
    return block(
        3,
        struct.pack(endian + "I", len(data) if original is None else original)
        + data
        + b"\x00" * ((-len(data)) % 4),
        endian,
    )


def put(tmp_path: Path, data: bytes | bytearray) -> Path:
    path = tmp_path / "capture with spaces.unrelated-extension"
    path.write_bytes(data)
    return path


def error(path: Path, data: bytes, code: str = "CAPTURE_INVALID") -> None:
    path.write_bytes(data)
    with pytest.raises(ModelError) as raised:
        scan_capture(path)
    assert raised.value.diagnostics[0].code == code


@pytest.mark.parametrize("endian", ["<", ">"])
@pytest.mark.parametrize("nano", [False, True])
def test_classic_magic_variants_exact_metadata(tmp_path: Path, endian: str, nano: bool) -> None:
    data = pcap(endian=endian, nano=nano, seconds=0x12345678, fraction=999999)
    packets: list[Packet] = []
    result = scan_capture(put(tmp_path, data), packets.append)
    denominator = 10**9 if nano else 10**6
    assert result["sha256"] == hashlib.sha256(data).hexdigest() == result["capture_id"]
    assert result["format"] == "pcap" and result["size_bytes"] == len(data)
    assert result["packets"] == 1 and result["blocks"] == 0
    assert result["captured_bytes"] == result["original_bytes"] == 3
    assert packets == [
        Packet(
            1,
            24,
            0,
            0,
            1,
            Timestamp(0x12345678 * denominator + 999999, denominator),
            3,
            3,
            b"abc",
        )
    ]
    assert result["interfaces"] == [
        {
            "section": 0,
            "interface": 0,
            "linktype": 1,
            "snaplen": 65535,
            "timestamp_denominator": denominator,
            "timestamp_offset_seconds": 0,
        }
    ]


def test_classic_unknown_linktype_and_snapshot_truncation(tmp_path: Path) -> None:
    result = scan_capture(put(tmp_path, pcap(linktype=65400, original=900)))
    assert result["interfaces"][0]["linktype"] == 65400
    assert result["captured_bytes"] == 3 and result["original_bytes"] == 900
    assert result["limitations"] == ["SNAPSHOT_TRUNCATED_PACKETS_PRESENT"]


@pytest.mark.parametrize("endian", ["<", ">"])
def test_pcapng_sections_interfaces_exact_binary_and_decimal_times(
    tmp_path: Path, endian: str
) -> None:
    other = ">" if endian == "<" else "<"
    options = option(9, b"\x89", endian) + option(14, struct.pack(endian + "q", -3), endian)
    data = (
        section(endian)
        + interface(endian, options=options)
        + interface(endian, linktype=101, snaplen=0, options=option(9, b"\x09", endian))
        + enhanced(endian=endian, ticks=0x1122334455667788)
        + enhanced(b"ip", endian, interface_id=1, ticks=2)
        + section(other)
        + interface(other)
        + enhanced(b"last", other, ticks=0)
    )
    packets: list[Packet] = []
    result = scan_capture(put(tmp_path, data), packets.append)
    assert result["format"] == "pcapng" and result["blocks"] == 8
    assert result["packets"] == 3 and result["unknown_blocks"] == 0
    assert [(p.section, p.interface, p.linktype) for p in packets] == [
        (0, 0, 1),
        (0, 1, 101),
        (1, 0, 1),
    ]
    assert [p.timestamp for p in packets] == [
        Timestamp(0x1122334455667788, 512, -3),
        Timestamp(2, 10**9),
        Timestamp(0, 10**6),
    ]
    assert packets[0].offset == 28 + 40 + 28
    assert result["sha256"] == hashlib.sha256(data).hexdigest()


@pytest.mark.parametrize("resolution", [0, 18, 127, 128, 255])
def test_resolution_extremes_remain_exact(tmp_path: Path, resolution: int) -> None:
    data = section() + interface(options=option(9, bytes([resolution]))) + enhanced(ticks=7)
    packets: list[Packet] = []
    scan_capture(put(tmp_path, data), packets.append)
    denominator = 2 ** (resolution & 127) if resolution & 128 else 10**resolution
    assert packets[0].timestamp == Timestamp(7, denominator)


@pytest.mark.parametrize("endian", ["<", ">"])
def test_compatible_minor_2_is_explicit_and_other_versions_fail(
    tmp_path: Path, endian: str
) -> None:
    data = bytearray(section(endian) + interface(endian) + enhanced(endian=endian))
    struct.pack_into(endian + "H", data, 14, 2)
    result = scan_capture(put(tmp_path, data))
    assert result["packets"] == 1
    assert result["limitations"] == ["PCAPNG_MINOR_2_TREATED_AS_0"]
    for major, minor in ((2, 0), (1, 1), (1, 3)):
        struct.pack_into(endian + "HH", data, 12, major, minor)
        error(put(tmp_path, data), bytes(data))


@pytest.mark.parametrize(
    "flags,errors,offloaded",
    [
        (0, False, False),
        (1 << 24, True, False),
        (1 << 11, False, True),
        ((1 << 24) | (1 << 11), True, True),
    ],
)
def test_epb_link_errors_and_segmentation_offload_retained_for_safe_decoding(
    tmp_path: Path, flags: int, errors: bool, offloaded: bool
) -> None:
    data = section() + interface() + enhanced(options=option(2, struct.pack("<I", flags)))
    packets: list[Packet] = []
    scan_capture(put(tmp_path, data), packets.append)
    assert packets[0].link_errors is errors and packets[0].offloaded is offloaded


@pytest.mark.parametrize("kind", ["option", "enhanced", "simple"])
def test_nonzero_alignment_padding_rejected(tmp_path: Path, kind: str) -> None:
    if kind == "option":
        bad = bytearray(option(9, b"\x06"))
        bad[-1] = 1
        data = section() + interface(options=bytes(bad))
    else:
        packet = bytearray(enhanced() if kind == "enhanced" else simple())
        packet[-5] = 1
        data = section() + interface() + packet
    error(put(tmp_path, data), data)


@pytest.mark.parametrize("kind", [0x00000BAD, 0x40000BAD])
def test_custom_block_pen_is_structurally_required(tmp_path: Path, kind: int) -> None:
    data = section() + block(kind, b"")
    error(put(tmp_path, data), data)
    valid = section() + block(kind, b"\x00\x00\x00\x01")
    assert scan_capture(put(tmp_path, valid))["unknown_blocks"] == 1


def test_spb_uses_interface_zero_and_has_no_invented_time(tmp_path: Path) -> None:
    data = section() + interface(snaplen=3) + interface(linktype=101) + simple(original=80)
    packets: list[Packet] = []
    result = scan_capture(put(tmp_path, data), packets.append)
    assert packets[0].interface == 0 and packets[0].timestamp is None
    assert packets[0].data == b"abc" and packets[0].original_length == 80
    assert result["limitations"] == [
        "PACKETS_WITHOUT_TIMESTAMPS",
        "SNAPSHOT_TRUNCATED_PACKETS_PRESENT",
    ]


def test_valid_unknown_and_obsolete_blocks_counted_without_metadata_export(tmp_path: Path) -> None:
    marker = b"CREDENTIAL SECRET DO NOT EXPORT!"
    assert len(marker) % 4 == 0
    data = section() + block(0x40000BAD, marker) + block(2, b"\x00" * 20)
    result = scan_capture(put(tmp_path, data))
    assert result["blocks"] == 3 and result["unknown_blocks"] == 2 and result["packets"] == 0
    assert result["limitations"] == [
        "OBSOLETE_PACKET_BLOCKS_NOT_DECODED",
        "UNKNOWN_BLOCK_CONTENTS_NOT_INTERPRETED",
    ]
    assert "SECRET" not in str(result)


def test_declared_section_boundaries(tmp_path: Path) -> None:
    body = interface() + enhanced()
    valid = section(length=len(body)) + body
    assert scan_capture(put(tmp_path, valid))["packets"] == 1
    assert scan_capture(put(tmp_path, valid + section(">", length=0)))["blocks"] == 4
    for bad in (
        section(length=4) + body,
        section(length=len(body) + 4) + body,
        section(length=len(body) + 4) + body + section(),
        section(length=-2),
        section(length=3),
        section(length=0) + interface(),
    ):
        error(put(tmp_path, bad), bad)


@pytest.mark.parametrize("offset,value", [(4, 3), (6, 5)])
def test_classic_versions_rejected(tmp_path: Path, offset: int, value: int) -> None:
    data = bytearray(pcap())
    struct.pack_into("<H", data, offset, value)
    error(put(tmp_path, data), bytes(data))


@pytest.mark.parametrize("offset,value", [(8, 1), (12, 1), (16, 0), (20, 0x04000001)])
def test_classic_unsupported_header_fields(tmp_path: Path, offset: int, value: int) -> None:
    data = bytearray(pcap())
    struct.pack_into("<I", data, offset, value)
    error(put(tmp_path, data), bytes(data))


@pytest.mark.parametrize(
    "data",
    [
        pcap(fraction=1_000_000),
        pcap(nano=True, fraction=1_000_000_000),
        pcap(original=2),
        pcap(snaplen=2),
    ],
)
def test_classic_inconsistent_packet_header(tmp_path: Path, data: bytes) -> None:
    error(put(tmp_path, data), data)


def test_forged_classic_packet_size_rejected_before_data_read(tmp_path: Path) -> None:
    data = bytearray(pcap())
    struct.pack_into("<II", data, 32, 0xFFFFFFFF, 0xFFFFFFFF)
    error(put(tmp_path, data), bytes(data), "LIMIT_EXCEEDED")


def test_every_truncated_classic_header_or_record_fails(tmp_path: Path) -> None:
    data = pcap(b"x" * 30)
    path = put(tmp_path, b"")
    for boundary in range(len(data)):
        if boundary == 24:  # A header-only classic capture is valid.
            continue
        error(path, data[:boundary])


@pytest.mark.parametrize(
    "data",
    [
        section() + enhanced(),
        section() + interface() + enhanced(interface_id=1),
        section() + interface() + section() + enhanced(),
        section() + simple(),
        section() + interface(snaplen=2) + enhanced(),
        section() + interface() + enhanced(original=2),
        section() + interface() + simple(original=5),
        section() + interface() + simple() + b"\x00",
        section() + interface() + block(6, b"\x00" * 16),
        section() + block(1, b"\x00" * 4),
        section() + block(3, b""),
    ],
)
def test_pcapng_invalid_interface_or_packet_boundaries(tmp_path: Path, data: bytes) -> None:
    error(put(tmp_path, data), data)


def test_every_truncated_pcapng_block_fails(tmp_path: Path) -> None:
    data = section() + interface() + enhanced(b"payload")
    path = put(tmp_path, b"")
    for boundary in range(len(data)):
        if boundary in {28, 48}:  # Complete SHB and SHB+IDB are valid empty captures.
            continue
        error(path, data[:boundary])


@pytest.mark.parametrize("kind", [0x0A0D0D0A, 1, 6, 3, 99])
def test_redundant_block_lengths_must_agree(tmp_path: Path, kind: int) -> None:
    if kind == 0x0A0D0D0A:
        data = bytearray(section())
    else:
        data = bytearray(section() + block(kind, b"\x00" * 24))
    struct.pack_into("<I", data, len(data) - 4, 12)
    error(put(tmp_path, data), bytes(data))


@pytest.mark.parametrize("length", [0, 4, 8, 13, 27, 0xFFFFFFFF])
def test_forged_block_length_rejected_before_allocation(tmp_path: Path, length: int) -> None:
    data = bytearray(section())
    struct.pack_into("<I", data, 4, length)
    error(
        put(tmp_path, data),
        bytes(data),
        "LIMIT_EXCEEDED"
        if length > CAPTURE_LIMITS.block_bytes and length % 4 == 0
        else "CAPTURE_INVALID",
    )


def test_oversized_aligned_block_rejected(tmp_path: Path) -> None:
    data = bytearray(section())
    struct.pack_into("<I", data, 4, CAPTURE_LIMITS.block_bytes + 4)
    error(put(tmp_path, data), bytes(data), "LIMIT_EXCEEDED")


@pytest.mark.parametrize(
    "options",
    [
        option(9, b""),
        option(9, b"\x09\x09"),
        option(14, b"\x00" * 4),
        option(9, b"\x06") + option(9, b"\x06"),
        option(14, b"\x00" * 8) + option(14, b"\x00" * 8),
        option(0, b"x"),
        option(0, b"") + option(0, b""),
        struct.pack("<HH", 1, 5) + b"xx\x00\x00",
        option(2988, b"x"),
    ],
)
def test_hostile_interface_options_rejected(tmp_path: Path, options: bytes) -> None:
    data = section() + interface(options=options)
    error(put(tmp_path, data), data)


@pytest.mark.parametrize("code,size", [(2, 3), (4, 4), (5, 4), (6, 8), (3, 0), (7, 0)])
def test_malformed_packet_options_rejected(tmp_path: Path, code: int, size: int) -> None:
    data = section() + interface() + enhanced(options=option(code, b"x" * size))
    error(put(tmp_path, data), data)


def test_unknown_options_are_inert_and_optional_end_marker_supported(tmp_path: Path) -> None:
    hostile = b'<script>fetch("https://invalid")</script>'
    for ending in (b"", option(0, b"")):
        data = section(options=option(1, hostile) + ending) + interface(
            options=option(65000, b"opaque") + ending
        )
        result = scan_capture(put(tmp_path, data))
        assert result["blocks"] == 2 and "script" not in str(result)


def test_file_packet_and_interface_limits_exact_boundaries(tmp_path: Path) -> None:
    data = pcap()
    path = put(tmp_path, data)
    limits = replace(CAPTURE_LIMITS, file_bytes=len(data), packet_bytes=3, packets=1, interfaces=1)
    assert scan_capture(path, limits=limits)["packets"] == 1
    for field, value in (("file_bytes", len(data) - 1), ("packet_bytes", 2), ("packets", 0)):
        with pytest.raises(ModelError) as raised:
            scan_capture(path, limits=replace(limits, **{field: value}))
        assert raised.value.diagnostics[0].code == "LIMIT_EXCEEDED"
    with pytest.raises(ModelError):
        scan_capture(path, limits=replace(limits, interfaces=0))


def test_pcapng_block_metadata_interface_limits_exact_boundaries(tmp_path: Path) -> None:
    metadata = option(9, b"\x06") + option(0, b"")
    data = section() + interface(options=metadata) + enhanced()
    path = put(tmp_path, data)
    limits = replace(
        CAPTURE_LIMITS,
        file_bytes=len(data),
        block_bytes=36,
        blocks=3,
        metadata_bytes=len(metadata),
        packets=1,
        packet_bytes=3,
    )
    assert scan_capture(path, limits=limits)["packets"] == 1
    for field, value in (("blocks", 2), ("block_bytes", 35), ("metadata_bytes", 11)):
        with pytest.raises(ModelError) as raised:
            scan_capture(path, limits=replace(limits, **{field: value}))
        assert raised.value.diagnostics[0].code == "LIMIT_EXCEEDED"
    path.write_bytes(section() + interface() + section() + interface())
    with pytest.raises(ModelError) as raised:
        scan_capture(path, limits=replace(CAPTURE_LIMITS, interfaces=1))
    assert raised.value.diagnostics[0].code == "LIMIT_EXCEEDED"


def test_metadata_limits_also_cover_unknown_blocks(tmp_path: Path) -> None:
    path = put(tmp_path, section() + block(99, b"x" * 12))
    result = scan_capture(path, limits=replace(CAPTURE_LIMITS, metadata_bytes=12))
    assert result["unknown_blocks"] == 1
    with pytest.raises(ModelError) as raised:
        scan_capture(path, limits=replace(CAPTURE_LIMITS, metadata_bytes=11))
    assert raised.value.diagnostics[0].code == "LIMIT_EXCEEDED"


def test_empty_captures_and_zero_length_packets(tmp_path: Path) -> None:
    assert scan_capture(put(tmp_path, pcap()[:24]))["packets"] == 0
    assert scan_capture(put(tmp_path, section()))["packets"] == 0
    assert scan_capture(put(tmp_path, pcap(b"")))["captured_bytes"] == 0
    assert scan_capture(put(tmp_path, section() + interface() + enhanced(b"")))["packets"] == 1


def test_mutation_during_scan_is_fatal(tmp_path: Path) -> None:
    path = put(tmp_path, pcap())

    def mutate(packet: Packet) -> None:
        if packet.index == 1:
            with path.open("ab") as stream:
                stream.write(b"\x00" * 16)

    with pytest.raises(ModelError):
        scan_capture(path, mutate)


def test_replacement_during_scan_is_fatal(tmp_path: Path) -> None:
    path = put(tmp_path, pcap())

    def mutate(packet: Packet) -> None:
        # Changing timestamps alone must invalidate a successful result as well.
        info = path.stat()
        os.utime(path, ns=(info.st_atime_ns, info.st_mtime_ns + 10_000_000))

    with pytest.raises(ModelError) as raised:
        scan_capture(path, mutate)
    assert raised.value.diagnostics[0].code == "CAPTURE_CHANGED"


def test_input_symlink_and_ancestor_links_rejected_before_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = put(tmp_path, pcap())
    original = Path.is_symlink
    monkeypatch.setattr(Path, "is_symlink", lambda p: p == path.parent or original(p))
    with pytest.raises(ModelError) as raised:
        scan_capture(path)
    assert raised.value.diagnostics[0].code == "PROJECT_PATH"


def test_nonregular_and_missing_inputs_rejected(tmp_path: Path) -> None:
    with pytest.raises(ModelError) as raised:
        scan_capture(tmp_path)
    assert raised.value.diagnostics[0].code == "CAPTURE_FILE"
    with pytest.raises(ModelError) as raised:
        scan_capture(tmp_path / "missing")
    assert raised.value.diagnostics[0].code == "CAPTURE_READ"


def test_network_paths_rejected_before_filesystem_probe(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(path: Path) -> os.stat_result:
        raise AssertionError("Network filesystem was probed")

    monkeypatch.setattr(Path, "lstat", forbidden)
    with pytest.raises(ModelError) as raised:
        scan_capture(Path("//capture-server/share/trace.pcap"))
    assert raised.value.diagnostics[0].code == "CAPTURE_PATH"


def test_format_uses_header_not_name(tmp_path: Path) -> None:
    error(put(tmp_path, b"not a capture"), b"not a capture", "CAPTURE_FORMAT")
    error(
        put(tmp_path, b"\x34\xcd\xb2\xa1" + b"\x00" * 20),
        b"\x34\xcd\xb2\xa1" + b"\x00" * 20,
        "CAPTURE_FORMAT",
    )


def test_bounded_reproducible_mutations_never_escape_controlled_failure(tmp_path: Path) -> None:
    """Fixed 192 tiny mutations; no subprocess, open-ended fuzz loop or disk growth."""
    randomizer = random.Random(1301)
    seeds = [pcap(), section() + interface() + enhanced()]
    path = put(tmp_path, b"")
    for index in range(192):
        data = bytearray(seeds[index % 2])
        position = randomizer.randrange(len(data))
        data[position] ^= randomizer.randrange(1, 256)
        path.write_bytes(data)
        try:
            result = scan_capture(path)
        except ModelError:
            continue
        assert result["size_bytes"] == len(data)
        assert result["sha256"] == hashlib.sha256(data).hexdigest()
        assert result["packets"] <= 1


def test_repeated_scan_is_identical_and_no_payload_is_retained(tmp_path: Path) -> None:
    raw = pcap(b"password=fictional")
    data = raw[:24] + raw[24:] * 1000
    path = put(tmp_path, data)
    first = scan_capture(path)
    assert first == scan_capture(path)
    assert first["packets"] == 1000
    assert "password" not in str(first) and str(path) not in str(first)


def test_input_reads_are_incremental_and_bounded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Instrument the real descriptor's reads; a full-file read would fail this oracle."""
    raw = pcap(b"x" * 60)
    path = put(tmp_path, raw[:24] + raw[24:] * 2000)
    requests: list[int] = []

    class MeteredReader(io.BufferedReader):
        def read(self, size: int | None = -1) -> bytes:
            assert size is not None and 0 <= size <= 60
            requests.append(size)
            return super().read(size)

    def fdopen(descriptor: int, mode: str) -> BinaryIO:
        assert mode == "rb"
        return MeteredReader(io.FileIO(descriptor, mode="rb", closefd=True))

    monkeypatch.setattr("otarchguard.capture.parser.os.fdopen", fdopen)
    result = scan_capture(path)
    assert result["packets"] == 2000 and max(requests) == 60
    assert len(requests) == 4003  # magic, global header, two reads/record, EOF probe.
