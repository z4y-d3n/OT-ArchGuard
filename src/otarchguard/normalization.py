"""Canonical declared-model serialization, without graph or analysis results."""

import hashlib
import ipaddress
import json
from typing import cast

from otarchguard.domain import ArchitectureSnapshot, PortInterval
from otarchguard.loading import YamlValue


def normalize_ports(intervals: tuple[PortInterval, ...]) -> tuple[PortInterval, ...]:
    """Union closed intervals only; no atom partition or per-port evaluation."""
    pairs = sorted((p.start, p.end) for p in intervals)
    if not pairs:
        return ()
    result: list[PortInterval] = []
    start, end = pairs[0]
    for low, high in pairs[1:]:
        if low <= end + 1:
            end = max(end, high)
        else:
            result.append(PortInterval(start=start, end=end))
            start, end = low, high
    result.append(PortInterval(start=start, end=end))
    return tuple(result)


def _normalize(value: YamlValue) -> YamlValue:
    if isinstance(value, dict):
        result = {key: _normalize(child) for key, child in value.items()}
        if "ipv4" in result and isinstance(result["ipv4"], str):
            result["ipv4"] = str(ipaddress.IPv4Interface(result["ipv4"]))
        return result
    if isinstance(value, list):
        items = [_normalize(child) for child in value]
        if all(isinstance(child, str) for child in items):
            return sorted(items, key=str)
        if items and all(isinstance(child, dict) and "id" in child for child in items):
            return sorted(items, key=lambda child: str(cast(dict[str, YamlValue], child)["id"]))
        if items and all(
            isinstance(child, dict) and set(child) == {"start", "end"} for child in items
        ):
            intervals = tuple(PortInterval.model_validate(child) for child in items)
            return [{"start": p.start, "end": p.end} for p in normalize_ports(intervals)]
        return items
    return value


def normalize(snapshot: ArchitectureSnapshot) -> ArchitectureSnapshot:
    """Call only after structural validation; preserve all declared prose and IDs."""
    payload = cast(YamlValue, snapshot.model_dump(mode="json", exclude_none=True))
    return ArchitectureSnapshot.model_validate(_normalize(payload))


def canonical_bytes(snapshot: ArchitectureSnapshot) -> bytes:
    normalized = normalize(snapshot)
    return json.dumps(
        normalized.model_dump(mode="json", exclude_none=True),
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def model_hash(snapshot: ArchitectureSnapshot) -> str:
    return hashlib.sha256(canonical_bytes(snapshot)).hexdigest()
