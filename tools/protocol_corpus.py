"""Development-only, offline provenance and integrity checks for protocol fixtures.

This tool never downloads or extracts anything. A candidate manifest entry is not
approval to acquire or redistribute bytes. Hashes establish integrity, not origin.
"""

import argparse
import hashlib
import json
import os
import re
import stat
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any
from urllib.parse import urlsplit

MAX_MANIFEST_BYTES = 128 * 1024
MAX_FILE_BYTES = 16 * 1024 * 1024
MAX_ENTRIES = 64
PROTOCOLS = frozenset(
    {"modbus_tcp", "profinet_dcp", "ethernet_ip", "s7comm", "iec104", "opcua_binary", "dnp3"}
)
_FIELDS = frozenset(
    {
        "id",
        "tier",
        "source_organization",
        "original_author",
        "source_url",
        "upstream_revision",
        "original_filename",
        "sha256",
        "size_bytes",
        "capture_type",
        "protocol_families",
        "license",
        "redistribution",
        "attribution",
        "sensitivity_review",
        "expected_positive",
        "expected_negative",
        "parser_identity",
        "reference_tool",
        "known_limitations",
        "review_status",
    }
)


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name, value in pairs:
        if name in result:
            raise ValueError("Duplicate JSON key in corpus manifest")
        result[name] = value
    return result


def _constant(value: str) -> None:
    raise ValueError("Nonfinite number in corpus manifest")


def _text(value: Any, *, nullable: bool = False) -> None:
    if value is None and nullable:
        return
    if not isinstance(value, str) or not value.strip() or len(value) > 4096:
        raise ValueError("Invalid bounded corpus text")
    if any(ord(char) < 32 for char in value):
        raise ValueError("Control character in corpus text")


def _strings(value: Any) -> None:
    if not isinstance(value, list) or len(value) > 32:
        raise ValueError("Invalid corpus string list")
    for item in value:
        _text(item)


def _local(path: Path) -> None:
    if str(path).startswith(("\\\\", "//")) or PureWindowsPath(path).drive.startswith("\\\\"):
        raise ValueError("Only local corpus paths are supported")
    for part in (path.absolute(), *path.absolute().parents):
        info = part.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("Corpus paths cannot traverse links or reparse points")


def _read(path: Path, maximum: int) -> bytes:
    _local(path)
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_size > maximum:
        raise ValueError("Corpus input must be a bounded regular file")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    with os.fdopen(os.open(path, flags), "rb") as stream:
        opened = os.fstat(stream.fileno())
        identity = (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns)
        if identity != (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns):
            raise ValueError("Corpus input changed while opening")
        data = stream.read(maximum + 1)
        after = os.fstat(stream.fileno())
        _local(path)
        final = path.lstat()
        if (
            len(data) > maximum
            or any(
                identity != (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
                for info in (after, final)
            )
            or after.st_ctime_ns != opened.st_ctime_ns
        ):
            raise ValueError("Corpus input changed while reading")
    return data


def load_manifest(path: Path) -> dict[str, Any]:
    """Reject unknown versions, duplicate keys, invalid types and unsafe paths."""
    try:
        value = json.loads(
            _read(path, MAX_MANIFEST_BYTES).decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_constant=_constant,
        )
    except (UnicodeError, RecursionError, json.JSONDecodeError) as error:
        raise ValueError("Invalid corpus manifest JSON") from error
    if not isinstance(value, dict) or set(value) != {"manifest_version", "tiers", "entries"}:
        raise ValueError("Invalid corpus manifest root")
    if type(value["manifest_version"]) is not int or value["manifest_version"] != 1:
        raise ValueError("Unsupported corpus manifest version")
    if value["tiers"] != {
        "1": "original_synthetic",
        "2": "external_redistributable",
        "3": "external_reference_only",
    }:
        raise ValueError("Unknown corpus tier definition")
    entries = value["entries"]
    if not isinstance(entries, list) or len(entries) > MAX_ENTRIES:
        raise ValueError("Corpus entry limit exceeded")
    identities: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != _FIELDS:
            raise ValueError("Invalid corpus entry fields")
        corpus_id = entry["id"]
        if (
            not isinstance(corpus_id, str)
            or re.fullmatch(r"[a-z][a-z0-9-]{0,63}", corpus_id) is None
        ):
            raise ValueError("Invalid corpus identity")
        if corpus_id in identities:
            raise ValueError("Duplicate corpus identity")
        identities.add(corpus_id)
        if type(entry["tier"]) is not int or entry["tier"] not in {1, 2, 3}:
            raise ValueError("Unknown corpus tier")
        for field in (
            "source_organization",
            "original_author",
            "source_url",
            "upstream_revision",
            "original_filename",
            "license",
            "attribution",
            "parser_identity",
            "reference_tool",
        ):
            _text(entry[field], nullable=True)
        for field in ("expected_positive", "expected_negative", "known_limitations"):
            _strings(entry[field])
        families = entry["protocol_families"]
        _strings(families)
        if not families or len(families) != len(set(families)) or not set(families) <= PROTOCOLS:
            raise ValueError("Unknown or duplicate corpus protocol family")
        filename = entry["original_filename"]
        if filename is not None and (
            PurePosixPath(filename).is_absolute()
            or ".." in PurePosixPath(filename).parts
            or "\\" in filename
            or ":" in filename
            or PurePosixPath(filename).as_posix() != filename
        ):
            raise ValueError("Unsafe corpus filename")
        source = entry["source_url"]
        if source is not None:
            url = urlsplit(source)
            if url.scheme != "https" or not url.hostname or url.username or url.password:
                raise ValueError("Corpus references must use credential-free HTTPS")
        digest = entry["sha256"]
        if digest is not None and (
            not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None
        ):
            raise ValueError("Invalid corpus SHA-256")
        size = entry["size_bytes"]
        if size is not None and (type(size) is not int or not 0 < size <= MAX_FILE_BYTES):
            raise ValueError("Invalid corpus file size")
        _text(entry["capture_type"], nullable=True)
        for field in ("redistribution", "sensitivity_review", "review_status"):
            _text(entry[field])
        if entry["capture_type"] not in {"frame-vectors", "pcap", "pcapng", "reference-only", None}:
            raise ValueError("Unknown corpus capture type")
        if entry["redistribution"] not in {"original", "permitted", "unknown", "not_applicable"}:
            raise ValueError("Unknown corpus redistribution status")
        if entry["sensitivity_review"] not in {"fictional", "reviewed", "not_reviewed"}:
            raise ValueError("Unknown corpus sensitivity review")
        if entry["review_status"] not in {"approved_synthetic", "approved_external", "candidate"}:
            raise ValueError("Unknown corpus review status")
        status = entry["review_status"]
        if status == "approved_synthetic" and (
            entry["tier"] != 1
            or entry["redistribution"] != "original"
            or entry["sensitivity_review"] != "fictional"
        ):
            raise ValueError("Synthetic provenance is inconsistent")
        if status == "approved_external" and (
            entry["tier"] not in {2, 3}
            or entry["license"] is None
            or entry["redistribution"] not in {"permitted", "unknown"}
            or entry["sensitivity_review"] != "reviewed"
            or source is None
            or entry["upstream_revision"] is None
        ):
            raise ValueError("External provenance approval is incomplete")
        if entry["tier"] == 2 and entry["redistribution"] != "permitted":
            raise ValueError("Tier 2 requires explicit redistribution permission")
        if status != "candidate" and (digest is None or size is None or filename is None):
            raise ValueError("Approved corpus entry lacks exact byte identity")
    return value


def verify_file(manifest: dict[str, Any], corpus_id: str, path: Path) -> dict[str, Any]:
    """Verify explicitly supplied local bytes; never treats an LFS pointer as PCAP."""
    entries = [entry for entry in manifest["entries"] if entry["id"] == corpus_id]
    if len(entries) != 1 or entries[0]["review_status"] == "candidate":
        raise ValueError("Corpus entry is unknown or not approved for verification")
    entry = entries[0]
    data = _read(path, MAX_FILE_BYTES)
    if data.startswith(b"version https://git-lfs.github.com/spec/v1"):
        raise ValueError("Git LFS pointer is not capture payload bytes")
    if len(data) != entry["size_bytes"] or hashlib.sha256(data).hexdigest() != entry["sha256"]:
        raise ValueError("Corpus byte identity mismatch")
    if entry["capture_type"] == "pcap" and data[:4] not in {
        b"\xd4\xc3\xb2\xa1",
        b"\xa1\xb2\xc3\xd4",
        b"\x4d\x3c\xb2\xa1",
        b"\xa1\xb2\x3c\x4d",
    }:
        raise ValueError("Expected PCAP header is absent")
    if entry["capture_type"] == "pcapng" and data[:4] != b"\x0a\x0d\x0d\x0a":
        raise ValueError("Expected PCAPNG header is absent")
    return {"id": corpus_id, "status": "integrity_verified", "sha256": entry["sha256"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--verify", metavar="CORPUS_ID")
    parser.add_argument("--file", type=Path)
    args = parser.parse_args()
    try:
        manifest = load_manifest(args.manifest)
        if (args.verify is None) != (args.file is None):
            raise ValueError("--verify and --file must be supplied together")
        if args.verify is not None:
            result = verify_file(manifest, args.verify, args.file)
        else:
            entries = manifest["entries"]
            result = {
                "manifest_version": 1,
                "entries": len(entries),
                "approved": sum(e["review_status"] != "candidate" for e in entries),
                "candidates": sum(e["review_status"] == "candidate" for e in entries),
            }
    except (OSError, ValueError) as error:
        parser.exit(2, f"Corpus verification failed: {error}\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
