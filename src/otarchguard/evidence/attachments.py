"""Versioned, content-bound analytical attachments over preserved observations.

These are offline metadata consumers. Replaying a native comparison establishes
consistency with the selected model, never the truth of the original capture or
the authority of a reviewer. Original packet bytes are neither opened nor stored.
"""

import hashlib
import json
from collections.abc import Mapping
from fractions import Fraction
from typing import Any

from otarchguard.api import ValidatedArchitecture, validate_bytes
from otarchguard.capture.contract import CAPTURE_LIMITS
from otarchguard.capture.protocols import digest as enrichment_digest
from otarchguard.capture.protocols import validate_enrichment
from otarchguard.capture.protocols.header_validation import validate_header
from otarchguard.capture.reconciliation import _reviewed, compare_capture
from otarchguard.diagnostics import ModelError, check_limit, fail
from otarchguard.evidence.observations import digest, identity
from otarchguard.evidence.workspace import (
    EVIDENCE_LIMITS,
    _decode,
    serialize,
    validate_snapshot,
)

KINDS = ("enrichment", "model", "mapping", "comparison")
ATTACHMENT_LIMITATIONS = [
    "Validated metadata and exact dependency joins establish integrity, not authenticity.",
    "Original capture bytes have not been reopened or independently verified.",
    "Unsampled packet references cannot be fully revalidated without original capture bytes.",
    "Structural protocol recognition and reviewed mappings never approve a baseline.",
    "Reviewer identities are unauthenticated local assertions.",
]


def canonical(value: object) -> bytes:
    """Unambiguous integer-only JSON; resource/type validation precedes this call."""
    return json.dumps(
        value, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False
    ).encode("ascii")


def object_digest(domain: str, value: object) -> str:
    return hashlib.sha256(canonical({"domain": domain, "value": value})).hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        fail("EVIDENCE_ATTACHMENT", "$", message)


def _clone(value: dict[str, Any]) -> dict[str, Any]:
    # Validate the in-memory API as strictly as file JSON: json.dumps otherwise
    # silently coerces integer object keys and tuples. Charge bounded traversal
    # work before allocating the serialized document, including repeated aliases.
    pending: list[tuple[Any, int]] = [(value, 0)]
    nodes = planned = 0
    while pending:
        item, depth = pending.pop()
        nodes += 1
        check_limit("attachment_nodes", nodes, EVIDENCE_LIMITS.nodes)
        check_limit("attachment_depth", depth, EVIDENCE_LIMITS.depth)
        _require(
            item is None or type(item) in {dict, list, str, int, bool},
            "Attachment values must be exact JSON primitives without coercion.",
        )
        if type(item) is dict:
            _require(all(type(key) is str for key in item), "Attachment JSON keys must be strings.")
            pending.extend((v, depth + 1) for v in item.values())
            pending.extend((k, depth + 1) for k in item)
            planned += 2 + len(item) * 2
        elif type(item) is list:
            pending.extend((v, depth + 1) for v in item)
            planned += 2 + len(item)
        elif isinstance(item, str):
            _require(
                len(item) <= 4096 and not any(0xD800 <= ord(c) <= 0xDFFF for c in item),
                "Attachment text contains invalid Unicode or exceeds its limit.",
            )
            planned += len(json.dumps(item, ensure_ascii=True))
        else:
            try:
                planned += len(str(item)) + 1
            except ValueError:
                fail("EVIDENCE_ATTACHMENT", "$", "Attachment integer exceeds safe limits.")
        check_limit("attachment_canonical_bytes", planned, EVIDENCE_LIMITS.snapshot_bytes)
    try:
        copied = _decode(serialize(value), EVIDENCE_LIMITS)
    except (ValueError, TypeError, RecursionError, OverflowError):
        fail("EVIDENCE_ATTACHMENT", "$", "Attachment must contain bounded JSON metadata.")
    return copied


def _dependency(
    kind: str, snapshot: dict[str, Any], dependencies: Mapping[str, dict[str, Any]]
) -> dict[str, Any]:
    dependency = dependencies.get(kind)
    _require(type(dependency) is dict, "Required validated " + kind + " attachment is absent.")
    assert dependency is not None
    _require(dependency.get("kind") == kind, "Attachment dependency has the wrong type.")
    # The dependency graph is fixed: comparison -> mapping -> model; it cannot recurse
    # through arbitrary caller-supplied references.
    validate_attachment(dependency, snapshot, dependencies)
    return dependency


def model_architecture(attachment: dict[str, Any]) -> ValidatedArchitecture:
    """Revalidate the stored canonical model through the authoritative native API."""
    _require(attachment.get("kind") == "model", "A native model attachment is required.")
    validated = validate_bytes(canonical(attachment["payload"]))
    _require(validated.sha256 == attachment["component_sha256"], "Native model identity mismatch.")
    return validated


def _validate_enrichment(payload: dict[str, Any], snapshot: dict[str, Any]) -> None:
    # The V14-01 producer emits null. Attachment-v1 additionally accepts an explicit
    # observation binding: validate its original digest, validate the exact join,
    # then pass the equivalent null-bound producer document to its frozen validator.
    # The original document and original digest are retained in the attachment.
    asserted = payload.get("observations_sha256")
    _require(
        asserted is None or asserted == snapshot["observations_sha256"],
        "Protocol enrichment belongs to different observations.",
    )
    _require(
        payload.get("enrichment_sha256")
        == enrichment_digest({k: v for k, v in payload.items() if k != "enrichment_sha256"}),
        "Protocol enrichment canonical digest mismatch.",
    )
    producer = dict(payload)
    if asserted is not None:
        producer["observations_sha256"] = None
        producer["enrichment_sha256"] = enrichment_digest(
            {k: v for k, v in producer.items() if k != "enrichment_sha256"}
        )
    validate_enrichment(producer)
    observations = snapshot["observations"]
    _require(
        canonical(payload["capture"]) == canonical(observations["capture"]),
        "Enrichment capture metadata differs from the preserved physical collection.",
    )
    sampled: dict[int, tuple[dict[str, Any], dict[str, Any]]] = {}
    flow_keys: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for flow in observations["flows"]:
        key = tuple(
            flow[name]
            for name in ("source_ip", "destination_ip", "source_port", "destination_port")
        )
        flow_keys.setdefault((*key, tuple(flow["vlans"])), []).append(flow)
        for ref in flow["samples"] + flow["initiation_evidence"]:
            sampled[ref["index"]] = (ref, flow)
    for record in payload["records"]:
        ref = record["packet"]
        key = tuple(
            record[name]
            for name in ("source_ip", "destination_ip", "source_port", "destination_port")
        )
        candidates = flow_keys.get((*key, tuple(record["vlans"])), [])
        _require(bool(candidates), "Enrichment endpoints have no preserved observation flow.")
        if ref["index"] in sampled:
            sample, flow = sampled[ref["index"]]
            _require(
                canonical(ref) == canonical(sample) and flow in candidates,
                "Enrichment packet reference or endpoint metadata conflicts with observations.",
            )
            candidates = [flow]
        else:
            # An aggregate may retain only the first eight packet references. Check
            # everything still independently available; do not invent exact joins.
            _require(
                any(
                    f"{ref['section']}:{ref['interface']}" in flow["interfaces"]
                    and ref["captured_length"] <= flow["captured_bytes"]
                    and ref["original_length"] <= flow["original_bytes"]
                    and _within_window(ref["timestamp"], flow)
                    for flow in candidates
                ),
                "Unsampled enrichment reference conflicts with flow provenance.",
            )
        protocol = record["protocol"]
        method = record["recognition_method"]
        if protocol == "profinet_dcp":
            _require(
                record["source_ip"] is record["destination_ip"] is None
                and record["source_port"] is record["destination_port"] is None
                and method in {"ETHERTYPE", "HEADER_STRUCTURE"},
                "DCP enrichment cannot assert TCP or IP identity.",
            )
            _require(
                any(flow["linktype"] == 1 for flow in candidates),
                "DCP enrichment requires an observed Ethernet link.",
            )
        else:
            ports = {record["source_port"], record["destination_port"]}
            standard_ports = {
                "modbus_tcp": 502,
                "ethernet_ip": 44818,
                "s7comm": 102,
                "iec104": 2404,
                "opcua_binary": 4840,
                "dnp3": 20000,
            }
            selected = next((p for p, port in standard_ports.items() if port in ports), None)
            _require(
                selected == protocol
                or protocol == "modbus_tcp"
                and method == "EXPLICIT_PROTOCOL_SELECTION",
                "Protocol enrichment contradicts supported port selection semantics.",
            )
            _require(
                method != "ETHERTYPE" and all(flow["transport"] == "tcp" for flow in candidates),
                "Industrial TCP enrichment conflicts with transport metadata.",
            )
            _require(
                any(
                    flow["status"] == "decoded" and flow["linktype"] in {1, 101}
                    for flow in candidates
                ),
                "Industrial TCP enrichment requires a supported decoded outer frame.",
            )
        if record["status"] == "STRUCTURALLY_VALID":
            fields = record["fields"]
            size = (
                fields["adu_length"]
                if protocol == "modbus_tcp"
                else 12 + fields["data_length"]
                if protocol == "profinet_dcp"
                else validate_header(protocol, fields, record["message_category"])
            )
            _require(
                any(
                    record["record_offset"] + size + _outer_minimum(flow, protocol)
                    <= ref["captured_length"]
                    for flow in candidates
                ),
                "Structural protocol bytes do not fit after required outer headers.",
            )


def _outer_minimum(flow: dict[str, Any], protocol: str) -> int:
    link = 14 + 4 * len(flow["vlans"]) if flow["linktype"] == 1 else 0
    return (
        link if protocol == "profinet_dcp" else link + 20 + (40 if flow["ip_version"] == 6 else 20)
    )


def _within_window(stamp: dict[str, int] | None, flow: dict[str, Any]) -> bool:
    if stamp is None:
        return bool(flow["missing_timestamps"])
    instant = Fraction(stamp["ticks"], stamp["denominator"]) + stamp["offset_seconds"]
    return flow["first_timestamp"] is not None and (
        Fraction(flow["first_timestamp"]) <= instant <= Fraction(flow["last_timestamp"])
    )


def build_attachment(
    kind: str,
    payload: dict[str, Any] | bytes,
    snapshot: dict[str, Any],
    dependencies: Mapping[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Validate actual input and exact joins before deriving attachment identity."""
    validate_snapshot(snapshot)
    _require(kind in KINDS, "Unsupported analytical attachment type.")
    dependencies = dependencies or {}
    _require(set(dependencies) <= {"model", "mapping"}, "Unsupported attachment dependency.")
    references: dict[str, str | None] = {"model": None, "mapping": None}
    try:
        if kind == "model":
            data = payload if isinstance(payload, bytes) else canonical(_clone(payload))
            validated = validate_bytes(data)
            retained = _clone(json.loads(validated.canonical_json))
            component_sha256 = validated.sha256
        else:
            _require(type(payload) is dict, "This attachment requires a JSON metadata object.")
            assert isinstance(payload, dict)
            retained = _clone(payload)
            if kind == "enrichment":
                _validate_enrichment(retained, snapshot)
                component_sha256 = str(retained["enrichment_sha256"])
            else:
                model = _dependency("model", snapshot, dependencies)
                references["model"] = model["attachment_id"]
                validated = model_architecture(model)
                if kind == "mapping":
                    _reviewed(snapshot["observations"], validated, retained, CAPTURE_LIMITS)
                    component_sha256 = digest(retained)
                else:
                    mapping = _dependency("mapping", snapshot, dependencies)
                    _require(
                        mapping["dependencies"]["model"] == model["attachment_id"],
                        "Comparison mapping and selected model attachments differ.",
                    )
                    references["mapping"] = mapping["attachment_id"]
                    expected = compare_capture(
                        snapshot["observations"], validated, mapping["payload"]
                    )
                    _require(
                        canonical(expected) == canonical(retained),
                        "Native comparison differs from independently replayed dependencies.",
                    )
                    # Native comparison-v1 has no standalone digest. Attachment-v1
                    # defines a separate domain without modifying producer output.
                    component_sha256 = object_digest("otarchguard.native-comparison.v1", retained)
        result = {
            "attachment_version": 1,
            "kind": kind,
            "capture_sha256": snapshot["capture_sha256"],
            "observations_sha256": snapshot["observations_sha256"],
            "component_sha256": component_sha256,
            "dependencies": references,
            "payload": retained,
            "limitations": list(ATTACHMENT_LIMITATIONS),
        }
        result["attachment_id"] = "attachment-" + object_digest("otarchguard.attachment", result)
        return _clone(result)
    except (
        ValueError,
        KeyError,
        TypeError,
        AttributeError,
        IndexError,
        OverflowError,
        RecursionError,
    ):
        fail("EVIDENCE_ATTACHMENT", "$", "Invalid or inconsistent analytical attachment.")


def validate_attachment(
    attachment: dict[str, Any],
    snapshot: dict[str, Any],
    dependencies: Mapping[str, dict[str, Any]] | None = None,
) -> None:
    """Rebuild stored meaning, rather than trusting a self-reported checksum."""
    try:
        attachment = _clone(attachment)
        _require(
            type(attachment.get("attachment_version")) is int
            and attachment["attachment_version"] == 1
            and identity(attachment.get("attachment_id"), "attachment-"),
            "Unsupported attachment version or identity.",
        )
        expected = build_attachment(
            attachment["kind"], attachment["payload"], snapshot, dependencies
        )
        _require(
            canonical(attachment) == canonical(expected),
            "Attachment metadata or identity mismatch.",
        )
    except ModelError:
        raise
    except (
        ValueError,
        KeyError,
        TypeError,
        AttributeError,
        IndexError,
        OverflowError,
        RecursionError,
    ):
        fail("EVIDENCE_ATTACHMENT", "$", "Invalid or inconsistent analytical attachment.")
