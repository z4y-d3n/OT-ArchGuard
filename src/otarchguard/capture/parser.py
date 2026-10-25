"""Bounded streaming PCAP 2.4 / PCAPNG 1.0 reader with exact provenance.

See draft-ietf-opsawg-pcap-09 and draft-ietf-opsawg-pcapng-06. Only
SHB/IDB/EPB/SPB contents are interpreted. Other blocks are framing-validated
and counted; their bytes, names, comments and secrets are never retained.
"""

import hashlib
import os
import stat
import struct
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Any, BinaryIO, NoReturn

from otarchguard.capture.contract import CAPTURE_LIMITS, CaptureLimits, Packet, Timestamp
from otarchguard.diagnostics import check_limit, fail
from otarchguard.ingestion.project import _no_links

_SHB = b"\x0a\x0d\x0d\x0a"
_MAGIC = {
    b"\xd4\xc3\xb2\xa1": ("<", 1_000_000),
    b"\xa1\xb2\xc3\xd4": (">", 1_000_000),
    b"\x4d\x3c\xb2\xa1": ("<", 1_000_000_000),
    b"\xa1\xb2\x3c\x4d": (">", 1_000_000_000),
}


def _bad(message: str, offset: int = 0) -> NoReturn:
    fail("CAPTURE_INVALID", f"$@{offset}", message)


def _align(length: int) -> int:
    return (length + 3) & ~3


class _Reader:
    def __init__(self, stream: BinaryIO, limits: CaptureLimits) -> None:
        self.stream = stream
        self.limits = limits
        self.offset = 0
        self.sha256 = hashlib.sha256()

    def read(self, length: int, *, eof: bool = False) -> bytes:
        # Permit an EOF probe at the exact file-byte budget while bounding growth.
        maximum = max(0, self.limits.file_bytes - self.offset) + 1
        result = self.stream.read(min(length, maximum))
        if eof and not result:
            return b""
        check_limit("capture_file_bytes", self.offset + len(result), self.limits.file_bytes)
        if len(result) != length:
            _bad("Truncated capture header, block or packet record.", self.offset)
        self.sha256.update(result)
        self.offset += len(result)
        return result


@dataclass(frozen=True, slots=True)
class _Interface:
    section: int
    interface: int
    linktype: int
    snaplen: int
    denominator: int = 1_000_000
    offset_seconds: int = 0

    def metadata(self) -> dict[str, int]:
        return {
            "section": self.section,
            "interface": self.interface,
            "linktype": self.linktype,
            "snaplen": self.snaplen,
            "timestamp_denominator": self.denominator,
            "timestamp_offset_seconds": self.offset_seconds,
        }


class _Scan:
    def __init__(
        self, reader: _Reader, consume: Callable[[Packet], None] | None, limits: CaptureLimits
    ) -> None:
        self.reader = reader
        self.consume = consume
        self.limits = limits
        self.interfaces: list[dict[str, int]] = []
        self.packets = 0
        self.captured_bytes = 0
        self.original_bytes = 0
        self.blocks = 0
        self.unknown_blocks = 0
        self.limitations: set[str] = set()

    def interface(self, interface: _Interface) -> None:
        check_limit("capture_interfaces", len(self.interfaces) + 1, self.limits.interfaces)
        self.interfaces.append(interface.metadata())

    def packet(
        self,
        offset: int,
        interface: _Interface,
        timestamp: Timestamp | None,
        captured: int,
        original: int,
        data: bytes,
        flags: int = 0,
    ) -> None:
        check_limit("capture_packets", self.packets + 1, self.limits.packets)
        check_limit("capture_packet_bytes", captured, self.limits.packet_bytes)
        if captured > original or (interface.snaplen and captured > interface.snaplen):
            _bad("Captured packet length exceeds original length or interface snapshot.", offset)
        self.packets += 1
        self.captured_bytes += captured
        self.original_bytes += original
        if captured < original:
            self.limitations.add("SNAPSHOT_TRUNCATED_PACKETS_PRESENT")
        if timestamp is None:
            self.limitations.add("PACKETS_WITHOUT_TIMESTAMPS")
        if self.consume is not None:
            self.consume(
                Packet(
                    self.packets,
                    offset,
                    interface.section,
                    interface.interface,
                    interface.linktype,
                    timestamp,
                    captured,
                    original,
                    data,
                    bool(flags & 0xFFFF0000),
                    bool(flags & (1 << 11)),
                )
            )

    def classic(self, magic: bytes) -> None:
        endian, denominator = _MAGIC[magic]
        major, minor, reserved1, reserved2, snaplen, linktype = struct.unpack(
            endian + "HHIIII", self.reader.read(20)
        )
        if (major, minor) != (2, 4):
            _bad("Only classic PCAP version 2.4 is supported.")
        if reserved1 or reserved2 or linktype > 0xFFFF:
            _bad("PCAP reserved fields and linktype/FCS flags are outside the supported subset.")
        if snaplen == 0:
            _bad("Classic PCAP snapshot length must be nonzero.")
        interface = _Interface(0, 0, linktype, snaplen, denominator)
        self.interface(interface)
        while True:
            offset = self.reader.offset
            header = self.reader.read(16, eof=True)
            if not header:
                return
            seconds, fraction, captured, original = struct.unpack(endian + "IIII", header)
            if fraction >= denominator:
                _bad("PCAP fractional timestamp exceeds its declared precision.", offset)
            check_limit("capture_packets", self.packets + 1, self.limits.packets)
            check_limit("capture_packet_bytes", captured, self.limits.packet_bytes)
            if captured > original or captured > snaplen:
                _bad("Invalid PCAP captured/original/snapshot lengths.", offset)
            data = self.reader.read(captured)
            self.packet(
                offset,
                interface,
                Timestamp(seconds * denominator + fraction, denominator),
                captured,
                original,
                data,
            )

    def options(self, data: bytes, endian: str, offset: int) -> list[tuple[int, bytes]]:
        check_limit("capture_metadata_bytes", len(data), self.limits.metadata_bytes)
        result: list[tuple[int, bytes]] = []
        position = 0
        while position < len(data):
            if len(data) - position < 4:
                _bad("Truncated PCAPNG option header.", offset)
            code, size = struct.unpack_from(endian + "HH", data, position)
            position += 4
            if code == 0:
                if size or position != len(data):
                    _bad("Invalid or repeated PCAPNG end-of-options marker.", offset)
                break
            end = position + _align(size)
            if end > len(data):
                _bad("PCAPNG option value or alignment padding exceeds its block.", offset)
            if any(data[position + size : end]):
                _bad("PCAPNG option alignment padding must be zero.", offset)
            if code in {2988, 2989, 19372, 19373} and size < 4:
                _bad("PCAPNG custom options require a private enterprise number.", offset)
            result.append((code, data[position : position + size]))
            position = end
        # Readers accept a missing end marker when the list ends exactly at the boundary.
        return result

    def generic(self) -> None:
        endian = ""
        section = -1
        section_end: int | None = None
        local: list[_Interface] = []
        first = True
        while True:
            offset = 0 if first else self.reader.offset
            header = _SHB if first else self.reader.read(4, eof=True)
            first = False
            if not header:
                if section_end is not None and offset != section_end:
                    _bad("PCAPNG section length does not match the file boundary.", offset)
                return
            if section_end is not None and (
                offset > section_end or (offset == section_end and header != _SHB)
            ):
                _bad("PCAPNG block lies beyond the declared section boundary.", offset)
            check_limit("capture_blocks", self.blocks + 1, self.limits.blocks)
            self.blocks += 1
            if header == _SHB:
                if section_end is not None and offset != section_end:
                    _bad("PCAPNG section length does not match the next section.", offset)
                prefix = self.reader.read(8)
                bom = prefix[4:8]
                if bom == b"\x4d\x3c\x2b\x1a":
                    endian = "<"
                elif bom == b"\x1a\x2b\x3c\x4d":
                    endian = ">"
                else:
                    _bad("Invalid PCAPNG byte-order magic.", offset)
                length = struct.unpack(endian + "I", prefix[:4])[0]
                self.block_length(length, 28, offset)
                rest = self.reader.read(length - 12)
                self.trailer(rest, length, endian, offset)
                major, minor, declared_length = struct.unpack_from(endian + "HHq", rest)
                if major != 1 or minor not in {0, 2}:
                    _bad("Only PCAPNG 1.0 and compatible minor-2 sections are supported.", offset)
                if minor == 2:
                    self.limitations.add("PCAPNG_MINOR_2_TREATED_AS_0")
                if declared_length < -1 or (declared_length >= 0 and declared_length % 4):
                    _bad("Invalid PCAPNG declared section length.", offset)
                section_end = offset + length + declared_length if declared_length >= 0 else None
                if section_end is not None:
                    check_limit("capture_section_end", section_end, self.limits.file_bytes)
                self.options(rest[12:-4], endian, offset)
                section += 1
                local = []
                continue
            if not endian:
                _bad("PCAPNG must begin with a Section Header Block.", offset)
            length = struct.unpack(endian + "I", self.reader.read(4))[0]
            self.block_length(length, 12, offset)
            if section_end is not None and offset + length > section_end:
                _bad("PCAPNG block crosses its declared section boundary.", offset)
            rest = self.reader.read(length - 8)
            self.trailer(rest, length, endian, offset)
            body = rest[:-4]
            kind = struct.unpack(endian + "I", header)[0]
            if kind == 1:
                if len(body) < 8:
                    _bad("Truncated PCAPNG Interface Description Block.", offset)
                linktype, _reserved, snaplen = struct.unpack_from(endian + "HHI", body)
                denominator, seconds = 1_000_000, 0
                seen: set[int] = set()
                for code, value in self.options(body[8:], endian, offset):
                    if code not in {9, 14}:
                        continue
                    if code in seen or len(value) != (1 if code == 9 else 8):
                        _bad("Invalid or duplicate PCAPNG timestamp interface option.", offset)
                    seen.add(code)
                    if code == 9:
                        resolution = value[0]
                        denominator = (
                            2 ** (resolution & 0x7F) if resolution & 0x80 else 10**resolution
                        )
                    else:
                        seconds = struct.unpack(endian + "q", value)[0]
                interface = _Interface(section, len(local), linktype, snaplen, denominator, seconds)
                self.interface(interface)
                local.append(interface)
            elif kind == 6:
                if len(body) < 20:
                    _bad("Truncated PCAPNG Enhanced Packet Block.", offset)
                interface_id, high, low, captured, original = struct.unpack_from(
                    endian + "IIIII", body
                )
                if interface_id >= len(local):
                    _bad("PCAPNG packet references a nonexistent section-local interface.", offset)
                check_limit("capture_packet_bytes", captured, self.limits.packet_bytes)
                end = 20 + _align(captured)
                if end > len(body):
                    _bad("PCAPNG packet or alignment padding exceeds the block.", offset)
                if any(body[20 + captured : end]):
                    _bad("PCAPNG packet alignment padding must be zero.", offset)
                options = self.options(body[end:], endian, offset)
                self.packet_options(options, offset)
                flags = next(
                    (struct.unpack(endian + "I", value)[0] for code, value in options if code == 2),
                    0,
                )
                interface = local[interface_id]
                self.packet(
                    offset,
                    interface,
                    Timestamp((high << 32) | low, interface.denominator, interface.offset_seconds),
                    captured,
                    original,
                    body[20 : 20 + captured],
                    flags,
                )
            elif kind == 3:
                if not local or len(body) < 4:
                    _bad("PCAPNG Simple Packet Block requires an existing first interface.", offset)
                original = struct.unpack_from(endian + "I", body)[0]
                interface = local[0]
                captured = min(original, interface.snaplen) if interface.snaplen else original
                check_limit("capture_packet_bytes", captured, self.limits.packet_bytes)
                if len(body) != 4 + _align(captured):
                    _bad("PCAPNG Simple Packet Block length disagrees with its snapshot.", offset)
                if any(body[4 + captured :]):
                    _bad("PCAPNG packet alignment padding must be zero.", offset)
                self.packet(offset, interface, None, captured, original, body[4 : 4 + captured])
            else:
                if kind in {0x00000BAD, 0x40000BAD} and len(body) < 4:
                    _bad("PCAPNG custom blocks require a private enterprise number.", offset)
                self.unknown_blocks += 1
                check_limit("capture_metadata_bytes", len(body), self.limits.metadata_bytes)
                self.limitations.add("UNKNOWN_BLOCK_CONTENTS_NOT_INTERPRETED")
                if kind == 2:
                    self.limitations.add("OBSOLETE_PACKET_BLOCKS_NOT_DECODED")

    @staticmethod
    def packet_options(options: list[tuple[int, bytes]], offset: int) -> None:
        seen: set[int] = set()
        for code, value in options:
            expected = {2: 4, 4: 8, 5: 8, 6: 4}.get(code)
            if expected is not None:
                if code in seen or len(value) != expected:
                    _bad("Invalid or duplicate fixed-size PCAPNG packet option.", offset)
                seen.add(code)
            if code in {3, 7} and not value:
                _bad("PCAPNG packet hash/verdict option is missing its type.", offset)

    def block_length(self, length: int, minimum: int, offset: int) -> None:
        if length < minimum or length % 4:
            _bad("PCAPNG block length must be aligned and cover its fixed fields.", offset)
        check_limit("capture_block_bytes", length, self.limits.block_bytes)

    @staticmethod
    def trailer(rest: bytes, length: int, endian: str, offset: int) -> None:
        if struct.unpack(endian + "I", rest[-4:])[0] != length:
            _bad("PCAPNG redundant block lengths disagree.", offset)


def _identity(info: os.stat_result) -> tuple[int, int, int, int]:
    # Windows lstat/fstat may expose different ctime meanings during Python's
    # transition to st_birthtime. Compare ctime only between the two fstat calls.
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns


def scan_capture(
    path: Path,
    consume: Callable[[Packet], None] | None = None,
    limits: CaptureLimits = CAPTURE_LIMITS,
) -> dict[str, Any]:
    """Validate all container bytes before returning successful canonical metadata.

    Consumers receive transient bounded packet data and must discard raw bytes.
    A failing scan yields no valid partial report. This is local single-writer I/O;
    metadata checks detect ordinary mutation, not a malicious filesystem sandbox.
    """
    if str(path).startswith(("\\\\", "//")) or PureWindowsPath(path).drive.startswith("\\\\"):
        fail("CAPTURE_PATH", "$", "Network filesystem paths are outside offline capture scope.")
    _no_links(path)
    try:
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode):
            fail("CAPTURE_FILE", "$", "Capture input must be a regular, non-symlink file.")
        check_limit("capture_file_bytes", before.st_size, limits.file_bytes)
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        with os.fdopen(os.open(path, flags), "rb") as stream:
            opened = os.fstat(stream.fileno())
            if not stat.S_ISREG(opened.st_mode) or _identity(opened) != _identity(before):
                fail("CAPTURE_CHANGED", "$", "Capture input changed while opening.")
            reader = _Reader(stream, limits)
            magic = reader.read(4)
            scan = _Scan(reader, consume, limits)
            if magic in _MAGIC:
                format_name = "pcap"
                scan.classic(magic)
            elif magic == _SHB:
                format_name = "pcapng"
                scan.generic()
            else:
                fail("CAPTURE_FORMAT", "$", "Unrecognized or unsupported capture header.")
            after = os.fstat(stream.fileno())
            _no_links(path)
            if (
                _identity(opened) != _identity(after)
                or opened.st_ctime_ns != after.st_ctime_ns
                or _identity(opened) != _identity(path.lstat())
                or reader.offset != opened.st_size
            ):
                fail("CAPTURE_CHANGED", "$", "Capture input changed during processing.")
    except OSError:
        fail("CAPTURE_READ", "$", "Cannot read the local capture input.")
    sha = reader.sha256.hexdigest()
    return {
        "capture_version": 1,
        "capture_id": sha,
        "sha256": sha,
        "size_bytes": reader.offset,
        "format": format_name,
        "interfaces": scan.interfaces,
        "packets": scan.packets,
        "captured_bytes": scan.captured_bytes,
        "original_bytes": scan.original_bytes,
        "blocks": scan.blocks,
        "unknown_blocks": scan.unknown_blocks,
        "limitations": sorted(scan.limitations),
    }
