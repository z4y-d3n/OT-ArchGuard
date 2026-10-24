"""Shared restricted OOXML ZIP boundary, inherited from the XLSX adapter.

No filesystem extraction. All members are checked before any XML tree is built.
Format-specific OPC interpretation stays with each adapter.
"""

import io
import re
import stat
import zipfile
from pathlib import PurePosixPath
from typing import Protocol
from xml.etree import ElementTree as ET

from otarchguard.diagnostics import check_limit, fail
from otarchguard.ingestion.xml_safe import XmlBudget


class PackageLimits(Protocol):
    @property
    def members(self) -> int: ...
    @property
    def uncompressed_bytes(self) -> int: ...
    @property
    def ratio(self) -> int: ...


def read_parts(
    data: bytes,
    limits: PackageLimits,
    budget: XmlBudget,
    allowed: re.Pattern[str],
    directories: set[str],
    *,
    prefix: str,
) -> dict[str, ET.Element]:
    code = "IMPORT_" + prefix.upper()
    parts: dict[str, ET.Element] = {}
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            members = archive.infolist()
            check_limit(prefix + "_members", len(members), limits.members)
            seen: set[str] = set()
            uncompressed = 0
            for member in members:
                name = member.filename
                path = PurePosixPath(name)
                mode = member.external_attr >> 16
                if (
                    name.casefold() in seen
                    or member.orig_filename != name
                    or path.is_absolute()
                    or ".." in path.parts
                    or path.as_posix() != name.rstrip("/")
                    or "\\" in name
                    or ":" in name
                    or stat.S_IFMT(mode) not in {0, stat.S_IFREG, stat.S_IFDIR}
                    or member.flag_bits & 1
                    or member.compress_type not in {0, 8}
                ):
                    fail(code + "_ARCHIVE", "$", "Unsafe, duplicate or special ZIP member.")
                seen.add(name.casefold())
                if member.is_dir():
                    if member.file_size != 0 or name not in directories:
                        fail(code + "_PART", "$", "Unsupported or nonempty package directory.")
                    continue
                if allowed.fullmatch(name) is None:
                    fail(code + "_PART", "$", "Unsupported package part (macros/objects excluded).")
                uncompressed += member.file_size
                check_limit(prefix + "_uncompressed_bytes", uncompressed, limits.uncompressed_bytes)
                check_limit(
                    prefix + "_compression_ratio",
                    member.file_size,
                    max(1, member.compress_size) * limits.ratio,
                )
            for member in members:
                if not member.is_dir():
                    with archive.open(member) as stream:
                        payload = stream.read(min(member.file_size, limits.uncompressed_bytes) + 1)
                    if len(payload) != member.file_size:
                        fail(code + "_ARCHIVE", "$", "Archive member size mismatch.")
                    parts[member.filename] = budget.parse(payload)
    except (zipfile.BadZipFile, OSError, RuntimeError, NotImplementedError):
        fail(code + "_ARCHIVE", "$", "Corrupt or unsupported OOXML container.")
    return parts
