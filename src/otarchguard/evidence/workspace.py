"""Immutable metadata snapshots with deterministic identities and bounded local I/O.

This is a local single-writer workspace, not an authorization or custody system.
Input hashes bind metadata; the original capture is not reopened or copied.
"""

import json
import os
import re
import stat
import tempfile
from collections.abc import Iterator
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path, PureWindowsPath
from typing import Any

from otarchguard.diagnostics import ModelError, check_limit, fail
from otarchguard.evidence.observations import _stamp, digest, validate_observations


@dataclass(frozen=True, slots=True)
class EvidenceLimits:
    snapshot_bytes: int = 64 * 1024 * 1024
    workspace_bytes: int = 256 * 1024 * 1024
    snapshots: int = 256
    depth: int = 64
    nodes: int = 2_000_000
    label_characters: int = 256


EVIDENCE_LIMITS = EvidenceLimits()
_MANIFEST = {"workspace_version": 1, "snapshot_version": 1}
_LIMITATIONS = [
    "Metadata hashes verify integrity, not authenticity or collection authority.",
    "Original capture bytes have not been reopened; capture identity is an imported assertion.",
    "Capture windows describe available packets, not continuous monitoring or coverage.",
    "No address ownership, baseline approval or association validity is inferred.",
    "Imported network metadata can be sensitive; review it before sharing.",
]
_SNAPSHOT = re.compile(r"snapshot-[0-9a-f]{64}\.json$")


def serialize(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, ensure_ascii=True, indent=2, allow_nan=False) + "\n"
    ).encode()


def _local(path: Path) -> None:
    if str(path).startswith(("\\\\", "//")) or PureWindowsPath(path).drive.startswith("\\\\"):
        fail("EVIDENCE_PATH", "$", "Only local filesystem evidence paths are supported.")
    for name in path.absolute().parts[1:]:
        if (
            name in {".", ".."}
            or name.endswith((".", " "))
            or any(c in name for c in '\\:*?<>|"')
            or any(ord(c) < 32 or 127 <= ord(c) <= 159 for c in name)
            or re.fullmatch(r"(?i)(con|prn|aux|nul|com[0-9]|lpt[0-9])(?:\..*)?", name)
        ):
            fail("EVIDENCE_PATH", "$", "Evidence paths require portable local names.")
    for part in (path.absolute(), *path.absolute().parents):
        if part.is_symlink() or part.is_junction():
            fail("EVIDENCE_PATH", "$", "Evidence paths must not traverse links or junctions.")
        try:
            attributes = getattr(part.lstat(), "st_file_attributes", 0)
        except FileNotFoundError:
            continue
        except OSError:
            fail("EVIDENCE_PATH", "$", "Cannot inspect local evidence path attributes.")
        if attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400):
            fail("EVIDENCE_PATH", "$", "Evidence paths must not traverse reparse points.")


def _decode(data: bytes, limits: EvidenceLimits) -> dict[str, Any]:
    check_limit("evidence_file_bytes", len(data), limits.snapshot_bytes)
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        fail("EVIDENCE_JSON", "$", "Evidence requires strict UTF-8 JSON.")
    depth = 0
    quoted = escaped = False
    for character in text:
        if quoted:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                quoted = False
        elif character == '"':
            quoted = True
        elif character in "[{":
            depth += 1
            check_limit("evidence_depth", depth, limits.depth)
        elif character in "]}":
            depth -= 1

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                fail("EVIDENCE_JSON", "$", "Duplicate JSON object keys are forbidden.")
            result[key] = value
        return result

    def invalid(value: str) -> None:
        fail("EVIDENCE_JSON", "$", "Nonstandard JSON constants are forbidden.")

    try:
        result = json.loads(text, object_pairs_hook=pairs, parse_constant=invalid)
    except (ValueError, RecursionError):
        fail("EVIDENCE_JSON", "$", "Malformed evidence JSON.")
    if not isinstance(result, dict):
        fail("EVIDENCE_JSON", "$", "Evidence root must be an object.")
    stack: list[Any] = [result]
    nodes = 0
    while stack:
        item = stack.pop()
        nodes += 1
        check_limit("evidence_nodes", nodes, limits.nodes)
        if isinstance(item, dict):
            stack.extend(item.values())
        elif isinstance(item, list):
            stack.extend(item)
        elif isinstance(item, float):
            # Frozen evidence is integer/exact-rational metadata only.
            fail("EVIDENCE_JSON", "$", "Floating-point evidence values are unsupported.")
        elif isinstance(item, str):
            check_limit("evidence_text_characters", len(item), 4096)
    return result


def _read(path: Path, limits: EvidenceLimits) -> dict[str, Any]:
    _local(path)
    try:
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode):
            fail("EVIDENCE_FILE", "$", "Evidence input must be a regular local file.")
        check_limit("evidence_file_bytes", before.st_size, limits.snapshot_bytes)
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        with os.fdopen(os.open(path, flags), "rb") as stream:
            opened = os.fstat(stream.fileno())
            if _file_identity(opened) != _file_identity(before):
                fail("EVIDENCE_CHANGED", "$", "Evidence changed while opening.")
            data = stream.read(limits.snapshot_bytes + 1)
            after = os.fstat(stream.fileno())
        _local(path)
        if (
            _file_identity(opened) != _file_identity(after)
            or opened.st_ctime_ns != after.st_ctime_ns
            or _file_identity(after) != _file_identity(path.lstat())
        ):
            fail("EVIDENCE_CHANGED", "$", "Evidence changed during reading.")
    except OSError:
        fail("EVIDENCE_READ", "$", "Cannot read local evidence.")
    return _decode(data, limits)


def _file_identity(info: os.stat_result) -> tuple[int, int, int, int]:
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns


def _check_observations(observations: dict[str, Any]) -> None:
    try:
        _field_policy(observations)
        validate_observations(observations)
        _extra_contract_checks(observations)
    except (ValueError, KeyError, TypeError, AttributeError, OverflowError):
        fail("EVIDENCE_OBSERVATIONS", "$", "Invalid or incompatible version-2 observations.")


def _field_policy(observations: dict[str, Any]) -> None:
    """Reject unsupported extension fields rather than archive unknown payloads.

    This lifecycle-v1 storage policy is narrower than the frozen development probe.
    Unknown codes in supported fields remain unassessed; they are never verdicts.
    """

    def fields(value: dict[str, Any], names: str) -> None:
        if set(value) != set(names.split()):
            raise ValueError("Unsupported metadata fields")

    fields(
        observations,
        "observation_version catalog_version capture hosts flows conversations "
        "coverage aggregation_accounted_bytes limitations observations_sha256",
    )
    capture = observations["capture"]
    fields(
        capture,
        "capture_version capture_id sha256 size_bytes format interfaces packets "
        "captured_bytes original_bytes blocks unknown_blocks limitations",
    )
    for interface in capture["interfaces"]:
        fields(
            interface,
            "section interface linktype snaplen timestamp_denominator timestamp_offset_seconds",
        )
    for host in observations["hosts"]:
        fields(host, "id ip ip_version packets source_macs destination_macs observation_roles")
    for flow in observations["flows"]:
        fields(
            flow,
            "id conversation_id source_ip destination_ip source_port destination_port "
            "transport arp transport_evidence ip_version vlans linktype status packets "
            "captured_bytes original_bytes first_timestamp last_timestamp missing_timestamps "
            "interfaces source_macs destination_macs samples samples_omitted tcp_flags "
            "initiation_evidence initiation_packets "
            "initiation_evidence_omitted protocol_hints limitations",
        )
        if flow["arp"] is not None:
            fields(
                flow["arp"],
                "metadata_version opcode operation sender_protocol_address "
                "target_protocol_address sender_hardware_address target_hardware_address "
                "ethernet_source_mac ethernet_destination_mac ethernet_delivery",
            )
        for sample in flow["samples"] + flow["initiation_evidence"]:
            fields(
                sample, "index offset section interface captured_length original_length timestamp"
            )
            if sample["timestamp"] is not None:
                fields(sample["timestamp"], "ticks denominator offset_seconds")
        for hint in flow["protocol_hints"]:
            fields(hint, "protocol level port")
    for group in observations["conversations"]:
        fields(
            group,
            "id flow_ids transport ip_version vlans linktypes packets captured_bytes "
            "original_bytes first_timestamp last_timestamp initiation_direction "
            "initiator_flow_id limitations",
        )
    fields(
        observations["coverage"],
        "packets decoded truncated malformed fragmented unsupported "
        "interpreted_packets uninterpreted_packets complete_file_scan capture_records_truncated",
    )


def _extra_contract_checks(observations: dict[str, Any]) -> None:
    """Check summaries consumed here beyond the frozen consumer's finite joins."""
    capture = observations["capture"]

    def count(value: object, maximum: int = 2**64 - 1, minimum: int = 0) -> bool:
        return type(value) is int and minimum <= value <= maximum

    def texts(values: object) -> bool:
        return (
            isinstance(values, list)
            and len(values) <= 256
            and all(isinstance(value, str) for value in values)
        )

    if not count(observations["aggregation_accounted_bytes"], 64 * 1024 * 1024):
        raise ValueError("Invalid aggregation accounting")
    if not texts(observations["limitations"]) or not texts(capture["limitations"]):
        raise ValueError("Invalid limitations")
    if capture["format"] not in {"pcap", "pcapng"}:
        raise ValueError("Unsupported capture format")
    for name in ("size_bytes", "captured_bytes", "original_bytes", "blocks", "unknown_blocks"):
        if type(capture[name]) is not int or capture[name] < 0:
            raise ValueError("Invalid capture counters")
    if capture["captured_bytes"] > capture["original_bytes"]:
        raise ValueError("Capture byte mismatch")
    if not count(capture["size_bytes"], 512 * 1024 * 1024):
        raise ValueError("Unsupported capture size")
    if capture["captured_bytes"] > capture["size_bytes"]:
        raise ValueError("Capture payload bytes exceed file size")
    if not count(capture["blocks"], 2_000_000) or capture["unknown_blocks"] > capture["blocks"]:
        raise ValueError("Invalid capture block counts")
    interfaces = {(i["section"], i["interface"]): i for i in capture["interfaces"]}
    for interface in capture["interfaces"]:
        if not all(count(interface[k], 65535) for k in ("section", "interface", "linktype")):
            raise ValueError("Invalid interface integer fields")
        if not count(interface["snaplen"], 2**32 - 1):
            raise ValueError("Invalid interface snapshot length")
        if not count(interface["timestamp_denominator"], 10**127, 1):
            raise ValueError("Invalid interface timestamp resolution")
        if type(interface["timestamp_offset_seconds"]) is not int or not (
            -(2**63) <= interface["timestamp_offset_seconds"] < 2**63
        ):
            raise ValueError("Invalid interface timestamp offset")
    if type(observations["coverage"]["complete_file_scan"]) is not bool:
        raise ValueError("Invalid scan completeness")
    truncated = observations["coverage"]["capture_records_truncated"]
    if type(truncated) is not int or not 0 <= truncated <= capture["packets"]:
        raise ValueError("Invalid truncation count")
    if [f["id"] for f in observations["flows"]] != sorted(f["id"] for f in observations["flows"]):
        raise ValueError("Invalid flow ordering")
    if [h["ip"] for h in observations["hosts"]] != sorted(h["ip"] for h in observations["hosts"]):
        raise ValueError("Invalid host ordering")
    flows = observations["flows"]
    by_id = {f["id"]: f for f in flows}
    if any(sum(f[k] for f in flows) != capture[k] for k in ("captured_bytes", "original_bytes")):
        raise ValueError("Flow byte totals disagree with capture")
    samples_by_index: dict[int, tuple[str, dict[str, Any]]] = {}
    for flow in flows:
        if not all(count(flow[k]) for k in ("captured_bytes", "original_bytes")):
            raise ValueError("Invalid flow bytes")
        if flow["captured_bytes"] > flow["original_bytes"] or not texts(flow["limitations"]):
            raise ValueError("Invalid flow byte bounds or limitations")
        if not isinstance(flow["transport_evidence"], str):
            raise ValueError("Invalid transport evidence text")
        if not isinstance(flow["interfaces"], list) or flow["interfaces"] != sorted(
            set(flow["interfaces"])
        ):
            raise ValueError("Invalid flow interface list")
        known_interfaces = {f"{section}:{local}" for section, local in interfaces}
        if not flow["interfaces"] or not set(flow["interfaces"]) <= known_interfaces:
            raise ValueError("Unknown flow interfaces")
        if not texts(flow["tcp_flags"]) or flow["tcp_flags"] != sorted(set(flow["tcp_flags"])):
            raise ValueError("Invalid TCP flags")
        if not isinstance(flow["protocol_hints"], list) or len(flow["protocol_hints"]) > 16:
            raise ValueError("Invalid protocol hint inventory")
        for hint in flow["protocol_hints"]:
            if (
                not isinstance(hint["protocol"], str)
                or not isinstance(hint["level"], str)
                or not count(hint["port"], 65535)
            ):
                raise ValueError("Invalid protocol hint fields")
        missing = flow["missing_timestamps"]
        if type(missing) is not int or not 0 <= missing <= flow["packets"]:
            raise ValueError("Invalid missing timestamp count")
        first, last = flow["first_timestamp"], flow["last_timestamp"]
        if (first is None) != (last is None) or (first is None) != (missing == flow["packets"]):
            raise ValueError("Inconsistent timestamp presence")
        if first is not None and Fraction(first) > Fraction(last):
            raise ValueError("Invalid timestamp ordering")
        for value in (first, last):
            if value is not None:
                rational = Fraction(value)
                if f"{rational.numerator}/{rational.denominator}" != value:
                    raise ValueError("Noncanonical timestamp")
        if (
            sum(s["captured_length"] for s in flow["samples"]) > flow["captured_bytes"]
            or sum(s["original_length"] for s in flow["samples"]) > flow["original_bytes"]
        ):
            raise ValueError("Flow sample byte totals exceed aggregate")
        for sample in flow["samples"] + flow["initiation_evidence"]:
            previous = samples_by_index.setdefault(sample["index"], (flow["id"], sample))
            if previous != (flow["id"], sample):
                raise ValueError("Packet reference conflicts across flows")
            interface = interfaces[(sample["section"], sample["interface"])]
            if (
                interface["linktype"] != flow["linktype"]
                or f"{sample['section']}:{sample['interface']}" not in flow["interfaces"]
            ):
                raise ValueError("Packet interface disagrees with flow")
            stamp = sample["timestamp"]
            if stamp is None:
                if not missing:
                    raise ValueError("Missing sample timestamp contradicts flow")
            else:
                if (
                    not count(stamp["ticks"])
                    or stamp["denominator"] != interface["timestamp_denominator"]
                    or stamp["offset_seconds"] != interface["timestamp_offset_seconds"]
                ):
                    raise ValueError("Packet timestamp disagrees with interface")
                instant = Fraction(stamp["ticks"], stamp["denominator"]) + stamp["offset_seconds"]
                if first is None or not Fraction(first) <= instant <= Fraction(last):
                    raise ValueError("Packet timestamp outside flow bounds")
    groups = observations["conversations"]
    if [g["id"] for g in groups] != sorted(g["id"] for g in groups):
        raise ValueError("Invalid conversation ordering")
    for group in groups:
        if group["flow_ids"] != sorted(set(group["flow_ids"])) or not group["flow_ids"]:
            raise ValueError("Invalid conversation member ordering")
        members = [by_id[identity] for identity in group["flow_ids"]]
        if any(
            serialize(group[k]) != serialize(members[0][k])
            for k in ("transport", "ip_version", "vlans")
        ):
            raise ValueError("Conversation protocol metadata mismatch")
        if serialize(group["linktypes"]) != serialize(sorted({f["linktype"] for f in members})):
            raise ValueError("Conversation linktype mismatch")
        for name in ("packets", "captured_bytes", "original_bytes"):
            if not count(group[name]) or group[name] != sum(f[name] for f in members):
                raise ValueError("Conversation count mismatch")
        for name, operation in (("first_timestamp", min), ("last_timestamp", max)):
            _stamp(group[name])
            times = [Fraction(f[name]) for f in members if f[name] is not None]
            expected = operation(times) if times else None
            actual = Fraction(group[name]) if group[name] is not None else None
            canonical = (
                f"{expected.numerator}/{expected.denominator}" if expected is not None else None
            )
            if actual != expected or group[name] != canonical:
                raise ValueError("Conversation timestamp summary mismatch")
        initiating = {
            (f["source_ip"], f["source_port"], f["destination_ip"], f["destination_port"])
            for f in members
            if f["initiation_packets"]
        }
        initiators = [f["id"] for f in members if f["initiation_packets"]]
        expected_direction = (
            "conflicting_syn"
            if len(initiating) > 1
            else "observed_syn"
            if initiating
            else "uncertain"
        )
        if group["initiation_direction"] != expected_direction or group["initiator_flow_id"] != (
            min(initiators) if len(initiating) == 1 else None
        ):
            raise ValueError("Conversation initiation summary mismatch")
        if not texts(group["limitations"]):
            raise ValueError("Invalid conversation limitations")


def build_snapshot(
    observations: dict[str, Any], label: str = "", limits: EvidenceLimits = EVIDENCE_LIMITS
) -> dict[str, Any]:
    """Bind the complete imported metadata; never reinterpret owner associations."""
    check_limit("evidence_label_characters", len(label), limits.label_characters)
    if any(ord(c) < 32 or 127 <= ord(c) <= 159 or 0xD800 <= ord(c) <= 0xDFFF for c in label):
        fail("EVIDENCE_LABEL", "$", "Snapshot labels must contain printable Unicode text.")
    # A serialize/decode roundtrip prevents mutable aliases and bounds direct API inputs.
    try:
        observations = _decode(serialize(observations), limits)
    except (ValueError, TypeError, RecursionError):
        fail("EVIDENCE_OBSERVATIONS", "$", "Invalid observation metadata values.")
    _check_observations(observations)
    flows = observations["flows"]
    first = [Fraction(f["first_timestamp"]) for f in flows if f["first_timestamp"] is not None]
    last = [Fraction(f["last_timestamp"]) for f in flows if f["last_timestamp"] is not None]

    def stamp(values: list[Fraction], minimum: bool) -> str | None:
        if not values:
            return None
        value = min(values) if minimum else max(values)
        return f"{value.numerator}/{value.denominator}"

    snapshot: dict[str, Any] = {
        "snapshot_version": 1,
        "generator": {"name": "otarchguard", "snapshot_implementation": 1},
        "capture_sha256": observations["capture"]["sha256"],
        "observations_sha256": observations["observations_sha256"],
        "label": label,
        "collection": {
            "first_timestamp": stamp(first, True),
            "last_timestamp": stamp(last, False),
            "missing_timestamps": sum(f["missing_timestamps"] for f in flows),
        },
        "observations": observations,
        "limitations": list(_LIMITATIONS),
    }
    snapshot["snapshot_id"] = "snapshot-" + digest(snapshot)
    check_limit("evidence_snapshot_bytes", len(serialize(snapshot)), limits.snapshot_bytes)
    return snapshot


def validate_snapshot(snapshot: dict[str, Any], limits: EvidenceLimits = EVIDENCE_LIMITS) -> None:
    try:
        if type(snapshot["snapshot_version"]) is not int or snapshot["snapshot_version"] != 1:
            raise ValueError("Unsupported snapshot version")
        expected = build_snapshot(snapshot["observations"], snapshot["label"], limits)
        if serialize(snapshot) != serialize(expected):
            raise ValueError("Snapshot metadata or integrity mismatch")
    except (KeyError, TypeError, ValueError):
        fail("EVIDENCE_SNAPSHOT", "$", "Invalid or incompatible immutable snapshot.")


def _publish(path: Path, data: bytes) -> None:
    """Publish complete bytes without replacement; abandoned temps remain uncommitted."""
    _local(path)
    temporary: Path | None = None
    try:
        descriptor, name = tempfile.mkstemp(prefix=".pending-", suffix=".tmp", dir=path.parent)
        temporary = Path(name)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        # Windows rename refuses an existing destination. POSIX rename replaces,
        # so use an atomic no-replace hardlink there. Unsupported filesystems fail closed.
        _local(path)
        if os.name == "nt":
            os.rename(temporary, path)
        else:
            os.link(temporary, path)
    except FileExistsError:
        fail("EVIDENCE_EXISTS", "$", "Evidence destination already exists; nothing overwritten.")
    except OSError:
        fail("EVIDENCE_WRITE", "$", "Cannot atomically publish local evidence.")
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


def initialize_workspace(path: Path) -> dict[str, Any]:
    _local(path)
    if path.exists():
        fail("EVIDENCE_EXISTS", "$", "Workspace destination must be new.")
    created = False
    try:
        path.mkdir()
        created = True
        (path / "snapshots").mkdir()
        _publish(path / "workspace.json", serialize(_MANIFEST))
    except (OSError, ModelError) as error:
        if created:
            # Only remove our empty unpublished directories; never recursively delete.
            try:
                (path / "snapshots").rmdir()
                path.rmdir()
            except OSError:
                pass
        if isinstance(error, ModelError):
            raise
        fail("EVIDENCE_WRITE", "$", "Cannot initialize the local workspace.")
    return {"status": "INITIALIZED", **_MANIFEST}


def _inventory(path: Path, limits: EvidenceLimits) -> list[Path]:
    _local(path)
    if serialize(_read(path / "workspace.json", limits)) != serialize(_MANIFEST):
        fail("EVIDENCE_WORKSPACE", "$", "Unsupported or corrupted workspace manifest.")
    directory = path / "snapshots"
    _local(directory)
    if not directory.is_dir():
        fail("EVIDENCE_WORKSPACE", "$", "Snapshot directory is missing.")
    files = []
    total_bytes = 0
    try:
        for item in directory.iterdir():
            _local(item)
            info = item.lstat()
            if not stat.S_ISREG(info.st_mode):
                fail("EVIDENCE_WORKSPACE", "$", "Workspace contains a nonregular entry.")
            total_bytes += info.st_size
            check_limit("evidence_workspace_bytes", total_bytes, limits.workspace_bytes)
            if item.name.startswith(".pending-") and item.name.endswith(".tmp"):
                fail("EVIDENCE_INTERRUPTED", "$", "Uncommitted temporary evidence requires review.")
            if not _SNAPSHOT.fullmatch(item.name):
                fail("EVIDENCE_WORKSPACE", "$", "Unexpected snapshot directory entry.")
            files.append(item)
            check_limit("evidence_snapshot_count", len(files), limits.snapshots)
    except OSError:
        fail("EVIDENCE_READ", "$", "Cannot inspect the local workspace.")
    return sorted(files)


def _snapshots(path: Path, limits: EvidenceLimits) -> Iterator[dict[str, Any]]:
    captures: set[str] = set()
    for item in _inventory(path, limits):
        snapshot = _read(item, limits)
        validate_snapshot(snapshot, limits)
        if item.stem != snapshot["snapshot_id"] or snapshot["capture_sha256"] in captures:
            fail("EVIDENCE_WORKSPACE", "$", "Snapshot filename or capture uniqueness mismatch.")
        captures.add(snapshot["capture_sha256"])
        yield snapshot


def _summary(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        k: snapshot[k]
        for k in ("snapshot_id", "capture_sha256", "observations_sha256", "label", "collection")
    }


def add_snapshot(
    workspace: Path,
    observations_path: Path,
    label: str = "",
    limits: EvidenceLimits = EVIDENCE_LIMITS,
) -> dict[str, Any]:
    snapshot = build_snapshot(_read(observations_path, limits), label, limits)
    count = 0
    duplicate = None
    for previous in _snapshots(workspace, limits):
        count += 1
        if previous["capture_sha256"] == snapshot["capture_sha256"]:
            duplicate = {
                "status": "DUPLICATE_CAPTURE",
                "existing": _summary(previous),
                "observations_match": previous["observations_sha256"]
                == snapshot["observations_sha256"],
                "label_match": previous["label"] == label,
                "message": "Existing metadata and label preserved; no evidence added or merged.",
            }
    if duplicate is not None:
        return duplicate
    check_limit("evidence_snapshot_count", count + 1, limits.snapshots)
    data = serialize(snapshot)
    check_limit(
        "evidence_workspace_bytes",
        sum(p.stat().st_size for p in _inventory(workspace, limits)) + len(data),
        limits.workspace_bytes,
    )
    _publish(workspace / "snapshots" / (snapshot["snapshot_id"] + ".json"), data)
    return {"status": "ADDED", "snapshot": _summary(snapshot)}


def list_snapshots(workspace: Path, limits: EvidenceLimits = EVIDENCE_LIMITS) -> dict[str, Any]:
    return {
        "workspace_version": 1,
        "snapshots": [_summary(s) for s in _snapshots(workspace, limits)],
    }


def show_snapshot(
    workspace: Path, snapshot_id: str, limits: EvidenceLimits = EVIDENCE_LIMITS
) -> dict[str, Any]:
    if not _SNAPSHOT.fullmatch(snapshot_id + ".json"):
        fail("EVIDENCE_ID", "$", "Use an exact snapshot identity from evidence list.")
    # Validate the complete inventory before exposing a member as trusted metadata.
    found = None
    for snapshot in _snapshots(workspace, limits):
        if snapshot["snapshot_id"] == snapshot_id:
            found = snapshot
    if found is not None:
        return found
    fail("EVIDENCE_NOT_FOUND", "$", "Snapshot is not present in this workspace.")


def verify_workspace(workspace: Path, limits: EvidenceLimits = EVIDENCE_LIMITS) -> dict[str, Any]:
    count = sum(1 for _ in _snapshots(workspace, limits))
    return {
        "status": "VERIFIED_METADATA",
        "workspace_version": 1,
        "snapshots": count,
        "limitations": list(_LIMITATIONS),
    }
