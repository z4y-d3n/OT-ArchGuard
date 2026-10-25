"""Evidence-bound owner review and conservative adapters to the native evaluator.

These records never modify the declared model. A reviewed identity is an owner
assertion about a finite capture, not proof that an address remained unique.
"""

import hashlib
import ipaddress
import json
from collections import Counter
from dataclasses import asdict, dataclass, replace
from pathlib import Path, PureWindowsPath
from typing import Any, NoReturn, cast

from otarchguard import __version__
from otarchguard.api import ValidatedArchitecture
from otarchguard.capture.contract import CAPTURE_LIMITS, CaptureLimits
from otarchguard.contract import RESOURCE_LIMITS
from otarchguard.diagnostics import check_limit, fail
from otarchguard.ingestion.project import _no_links
from otarchguard.ingestion.tabular import read_regular
from otarchguard.reachability import QueryResult, ReachabilityEngine

CLASSIFICATIONS = (
    "OBSERVED_MODEL_REACHABLE",
    "OBSERVED_MODEL_UNREACHABLE",
    "OBSERVED_SERVICE_UNDECLARED",
    "OBSERVED_ENDPOINT_UNMAPPED",
    "OBSERVED_DIRECTION_UNCERTAIN",
    "OBSERVED_MODEL_UNSUPPORTED",
    "OBSERVED_EVALUATION_INCOMPLETE",
    "DECLARED_SERVICE_NOT_OBSERVED",
    "EVIDENCE_AMBIGUOUS",
)

_DECISION_FIELDS = frozenset(
    {"decision", "selected_asset_id", "selected_interface_id", "reviewer", "rationale"}
)
_LIMITATIONS = [
    "Observation does not establish authorization, application success or a complete session.",
    "Reviewed identities are owner assertions bound to this capture and model; NAT, DHCP, "
    "address reuse and sensor visibility remain external uncertainties.",
    "MAC addresses describe captured frame endpoints and never establish IP ownership.",
    "Only decoded IPv4 TCP initial-SYN observations with reviewed endpoints are evaluated. "
    "UDP, midstream TCP, fragments, IPv6, ARP and multihomed origins remain unevaluated.",
    "Declared-service absence concerns only reviewed decoded destination headers in this "
    "capture. Unobserved traffic does not establish blocking or service unavailability.",
    "Discrepancies identify disagreement with the declared abstraction; they establish "
    "neither intrusions nor deployed firewall violations.",
]


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode()
    ).hexdigest()


def _mapping_error(message: str) -> NoReturn:
    fail("CAPTURE_MAPPING", "$.association", message)


@dataclass(frozen=True, slots=True)
class _NativeEvidence:
    query: dict[str, Any]
    query_bytes: int
    query_lines: int
    interval_metrics: tuple[tuple[int, int], ...]


def _evidence_allocation(query: QueryResult) -> int:
    """Conservative accounting before dataclass-to-container expansion.

    Native identifiers are ASCII and at most 64 characters. Per-record charges
    include nested endpoint dictionaries, strings, container overhead and rule
    identifier sequences; they are rejection accounting, not measured RSS.
    """
    total = 1024
    for interval in query.intervals:
        total += 1024
        if interval.witness is not None:
            total += 1024
            for step in interval.witness.steps:
                total += 4096 + 128 * len(step.allow_rule_ids)
        if interval.diagnostics is not None:
            total += 1024
            for edge in interval.diagnostics.blocked_edges:
                total += 1024 + 128 * (len(edge.allow_rule_ids) + len(edge.deny_rule_ids))
    return total


def _json_metrics(value: object) -> tuple[int, int]:
    text = json.dumps(value, sort_keys=True, ensure_ascii=True, indent=2)
    return len(text), text.count("\n") + 1


def load_mapping(path: Path, limits: CaptureLimits = CAPTURE_LIMITS) -> dict[str, Any]:
    """Read bounded strict JSON; do not coerce numbers, duplicate keys or versions."""
    maximum = min(8 * 1024 * 1024, limits.output_bytes)
    if str(path).startswith(("\\\\", "//")) or PureWindowsPath(path).drive.startswith("\\\\"):
        _mapping_error("Network filesystem paths are outside offline association scope.")
    _no_links(path)
    data = read_regular(path, maximum)
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        _mapping_error("Association JSON must use strict UTF-8.")
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
            check_limit("association_depth", depth, 32)
        elif character in "]}":
            depth -= 1

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                _mapping_error("Duplicate association JSON keys are forbidden.")
            result[key] = value
        return result

    def invalid_number(value: str) -> NoReturn:
        _mapping_error("Nonstandard association JSON numbers are forbidden.")

    try:
        document = json.loads(text, object_pairs_hook=pairs, parse_constant=invalid_number)
    except (ValueError, RecursionError):
        _mapping_error("Malformed association JSON.")
    if not isinstance(document, dict):
        _mapping_error("Association document must be an object.")
    # Bound tree work and strings after the parser's pre-allocation byte/depth checks.
    stack = [document]
    nodes = 0
    while stack:
        item = stack.pop()
        nodes += 1
        check_limit("association_nodes", nodes, limits.decisions * 64 + 64)
        if isinstance(item, dict):
            stack.extend(item.keys())
            stack.extend(item.values())
        elif isinstance(item, list):
            stack.extend(item)
        elif isinstance(item, str):
            check_limit("association_text", len(item), limits.metadata_bytes)
            if any(ord(c) < 32 or 127 <= ord(c) <= 159 or 0xD800 <= ord(c) <= 0xDFFF for c in item):
                _mapping_error(
                    "Association strings must not contain control or surrogate characters."
                )
    return cast(dict[str, Any], document)


def mapping_template(
    observations: dict[str, Any],
    validated: ValidatedArchitecture,
    limits: CaptureLimits = CAPTURE_LIMITS,
) -> dict[str, Any]:
    """Propose only exact declared IPv4 addresses, with every decision pending."""
    for name in ("observation_version", "catalog_version"):
        if type(observations.get(name)) is not int or observations[name] != 1:
            _mapping_error("Unsupported observation or protocol-catalog version.")
    canonical = json.dumps(
        {k: v for k, v in observations.items() if k != "observations_sha256"},
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode()
    check_limit("capture_observation_bytes", len(canonical), limits.output_bytes)
    if hashlib.sha256(canonical).hexdigest() != observations.get("observations_sha256"):
        _mapping_error("Observation contents differ from their canonical digest.")
    hosts = observations["hosts"]
    check_limit("association_decisions", len(hosts), limits.decisions)
    check_limit(
        "association_work", len(hosts) * len(validated.model.interfaces), limits.comparison_work
    )
    by_ip: dict[str, list[dict[str, str]]] = {}
    for interface in validated.model.interfaces:
        ip = str(ipaddress.IPv4Interface(interface.ipv4).ip)
        by_ip.setdefault(ip, []).append(
            {"asset_id": interface.asset_id, "interface_id": interface.id}
        )
    proposals: list[dict[str, Any]] = []
    seen: set[str] = set()
    for host in sorted(hosts, key=lambda h: h["id"]):
        if host["id"] in seen:
            _mapping_error("Duplicate observation host identifiers.")
        seen.add(host["id"])
        candidates = by_ip.get(host["ip"], []) if host["ip_version"] == 4 else []
        core = {
            "host_id": host["id"],
            "observed_ip": host["ip"],
            "candidates": sorted(candidates, key=lambda c: (c["asset_id"], c["interface_id"])),
        }
        proposals.append(
            {
                "id": "association_" + _digest(core),
                **core,
                "decision": "PENDING",
                "selected_asset_id": None,
                "selected_interface_id": None,
                "reviewer": "",
                "rationale": "",
            }
        )
    return {
        "association_version": 1,
        "capture_sha256": observations["capture"]["sha256"],
        "model_sha256": validated.sha256,
        "observations_sha256": observations["observations_sha256"],
        "candidates_sha256": _digest(
            [{k: v for k, v in p.items() if k not in _DECISION_FIELDS} for p in proposals]
        ),
        "proposals": proposals,
    }


def _reviewed(
    observations: dict[str, Any],
    validated: ValidatedArchitecture,
    review: dict[str, Any],
    limits: CaptureLimits,
) -> dict[str, dict[str, Any]]:
    expected = mapping_template(observations, validated, limits)
    if set(review) != set(expected) or type(review.get("association_version")) is not int:
        _mapping_error("Unsupported association version or document fields.")
    for key in expected.keys() - {"proposals"}:
        if review[key] != expected[key]:
            _mapping_error("Stale or mismatched capture, model, observations or candidate binding.")
    proposals = review["proposals"]
    if not isinstance(proposals, list) or len(proposals) != len(expected["proposals"]):
        _mapping_error("Every original proposal must occur exactly once.")
    originals = {p["id"]: p for p in expected["proposals"]}
    resolved: dict[str, dict[str, Any]] = {}
    seen: set[str] = set()
    for proposal in proposals:
        if not isinstance(proposal, dict) or not isinstance(proposal.get("id"), str):
            _mapping_error("Invalid association proposal.")
        identity = proposal["id"]
        if identity in seen or identity not in originals:
            _mapping_error("Duplicate or orphaned association proposal.")
        seen.add(identity)
        original = originals[identity]
        if set(proposal) != set(original):
            _mapping_error("Only documented owner decision fields may be changed.")
        for key in original.keys() - _DECISION_FIELDS:
            if _digest(proposal[key]) != _digest(original[key]):
                _mapping_error("Association candidate facts were changed.")
        decision = proposal["decision"]
        if decision not in ("PENDING", "ACCEPT", "REJECT"):
            _mapping_error("Decision must be PENDING, ACCEPT or REJECT.")
        for key in ("reviewer", "rationale"):
            text = proposal[key]
            if not isinstance(text, str):
                _mapping_error("Owner decision text must be a string.")
            check_limit("association_text", len(text), min(limits.metadata_bytes, 4096))
            if any(ord(c) < 32 or 127 <= ord(c) <= 159 or 0xD800 <= ord(c) <= 0xDFFF for c in text):
                _mapping_error("Owner decision text contains forbidden characters.")
            if decision != "PENDING" and not text.strip():
                _mapping_error("Accepted and rejected decisions need reviewer and rationale.")
            if decision == "PENDING" and text != "":
                _mapping_error("Pending decisions must retain the empty review fields.")
        selection = {
            "asset_id": proposal["selected_asset_id"],
            "interface_id": proposal["selected_interface_id"],
        }
        if decision == "ACCEPT":
            if selection not in original["candidates"]:
                _mapping_error("Accepted identities must select one original exact candidate.")
        elif any(value is not None for value in selection.values()):
            _mapping_error("Unaccepted decisions cannot carry a selected identity.")
        resolved[proposal["observed_ip"]] = proposal
    return resolved


def compare_capture(
    observations: dict[str, Any],
    validated: ValidatedArchitecture,
    review: dict[str, Any],
    limits: CaptureLimits = CAPTURE_LIMITS,
) -> dict[str, Any]:
    """Compare only justified initiation queries through the existing engine.

    Precedence is unsupported metadata, unresolved model ambiguity, unreviewed
    identities, uncertain direction, missing service, unsupported query scope,
    then an exact native evaluation. Resource failure aborts the entire result.
    """
    resolved = _reviewed(observations, validated, review, limits)
    flows = observations["flows"]
    services = validated.model.services
    check_limit("comparison_work", len(flows) * len(services), limits.comparison_work)
    check_limit("association_decisions", len(flows), limits.decisions)
    source_interfaces = Counter(i.asset_id for i in validated.model.interfaces)
    syn_directions: dict[str, set[tuple[str, int | None, str, int | None]]] = {}
    for flow in flows:
        if flow["status"] == "decoded" and flow["initiation_evidence"]:
            syn_directions.setdefault(flow["conversation_id"], set()).add(
                (
                    flow["source_ip"],
                    flow["source_port"],
                    flow["destination_ip"],
                    flow["destination_port"],
                )
            )
    findings: list[dict[str, Any]] = []
    jobs: list[tuple[dict[str, Any], str, str, int]] = []
    observed_services: set[str] = set()
    seen_flows: set[str] = set()
    for flow in flows:
        if flow["id"] in seen_flows:
            _mapping_error("Duplicate observation flow identifiers.")
        seen_flows.add(flow["id"])
        source = resolved.get(flow["source_ip"])
        destination = resolved.get(flow["destination_ip"])
        associations = [p["id"] for p in (source, destination) if p is not None]
        finding = {
            "flow_id": flow["id"],
            "conversation_id": flow["conversation_id"],
            "classification": "OBSERVED_MODEL_UNSUPPORTED",
            "reason": "Packet metadata is outside the evaluator's supported IPv4 TCP/UDP scope.",
            "samples": flow["samples"],
            "association_decision_ids": associations,
            "capture_sha256": observations["capture"]["sha256"],
            "model_sha256": validated.sha256,
            "native_result": None,
        }
        findings.append(finding)
        if flow["status"] != "decoded" or flow["ip_version"] != 4:
            continue
        if flow["transport"] not in ("tcp", "udp"):
            continue
        matching = [
            s
            for s in services
            if destination is not None
            and destination["decision"] == "ACCEPT"
            and s.interface_id == destination["selected_interface_id"]
            and s.asset_id == destination["selected_asset_id"]
            and s.protocol == flow["transport"]
            and type(flow["destination_port"]) is int
            and any(p.start <= flow["destination_port"] <= p.end for p in s.destination_ports)
        ]
        observed_services.update(s.id for s in matching)
        if any(p is not None and len(p["candidates"]) > 1 for p in (source, destination)):
            finding.update(
                classification="EVIDENCE_AMBIGUOUS",
                reason="An observed address has multiple declared interface candidates.",
            )
            continue
        if any(p is None or p["decision"] != "ACCEPT" for p in (source, destination)):
            finding.update(
                classification="OBSERVED_ENDPOINT_UNMAPPED",
                reason="Both endpoint identities require explicit accepted owner decisions.",
            )
            continue
        assert source is not None and destination is not None
        if (
            flow["transport"] != "tcp"
            or not flow["initiation_evidence"]
            or len(syn_directions.get(flow["conversation_id"], ())) != 1
        ):
            finding.update(
                classification="OBSERVED_DIRECTION_UNCERTAIN",
                reason="No unique decoded initial TCP SYN direction is evidenced; UDP and "
                "midstream traffic do not establish initiation.",
            )
            continue
        if not matching:
            finding.update(
                classification="OBSERVED_SERVICE_UNDECLARED",
                reason="No declared service covers this reviewed destination interface, "
                "transport and destination port.",
            )
            continue
        if len(matching) != 1:
            finding.update(
                classification="EVIDENCE_AMBIGUOUS",
                reason="Multiple declared services cover this destination port.",
            )
            continue
        service = matching[0]
        source_asset = source["selected_asset_id"]
        if source_asset == service.asset_id or source_interfaces[source_asset] != 1:
            finding["reason"] = (
                "The native engine's asset-origin query cannot represent this observed "
                "self-asset or multihomed-interface initiation exactly."
            )
            continue
        jobs.append((finding, source_asset, service.id, flow["destination_port"]))
    pairs = {(source, service) for _, source, service, _ in jobs}
    check_limit("capture_queries", len(pairs), limits.queries)
    native_limits = replace(
        RESOURCE_LIMITS,
        state_edge_visits=min(RESOURCE_LIMITS.state_edge_visits, limits.comparison_work),
        edge_rule_atom_checks=min(RESOURCE_LIMITS.edge_rule_atom_checks, limits.comparison_work),
    )
    native_queries: dict[tuple[str, str], _NativeEvidence] = {}
    native_allocated = native_output_bytes = 0
    engine: ReachabilityEngine | None = None
    if pairs:
        engine = ReachabilityEngine(validated, frozenset(s for _, s in pairs), native_limits)
        # Reserve the whole finite workload before publishing any query conclusions.
        engine.ensure_capacity(sum(len(engine.service_atoms[s]) for _, s in pairs))
        for source_key, service_key in sorted(pairs):
            query = engine.evaluate(source_key, service_key)
            native_allocated += _evidence_allocation(query)
            check_limit("capture_native_evidence_bytes", native_allocated, limits.aggregation_bytes)
            # Exactly one conversion per unique native query; findings share this evidence.
            query_data = asdict(query)
            query_bytes, query_lines = _json_metrics(query_data)
            check_limit("capture_native_query_bytes", query_bytes, limits.output_bytes)
            native_queries[source_key, service_key] = _NativeEvidence(
                query_data,
                query_bytes,
                query_lines,
                tuple(_json_metrics(value) for value in query_data["intervals"]),
            )
    for finding, source_key, service_key, port in jobs:
        native = native_queries[source_key, service_key]
        index, interval = next(
            (index, value)
            for index, value in enumerate(native.query["intervals"])
            if value["start"] <= port <= value["end"]
        )
        interval_bytes, interval_lines = native.interval_metrics[index]
        # Repeated references are repeated bytes in JSON. Account for both query
        # and selected interval, wrapper fields and their maximum envelope indent
        # before attaching another result. Cached exact lengths avoid reserializing
        # a large native query for every observed five-tuple.
        native_output_bytes += (
            native.query_bytes + interval_bytes + 16 * (native.query_lines + interval_lines) + 1024
        )
        check_limit("capture_native_output_bytes", native_output_bytes, limits.output_bytes)
        finding.update(
            classification=(
                "OBSERVED_MODEL_REACHABLE"
                if interval["reachable"]
                else "OBSERVED_MODEL_UNREACHABLE"
            ),
            reason=(
                "The existing engine evaluates this declared initiation and observed port "
                + ("as reachable." if interval["reachable"] else "as unreachable under the model.")
            ),
            native_result={
                "engine_version": __version__,
                "model_sha256": validated.sha256,
                "query": native.query,
                "observed_destination_port": port,
                "selected_interval": interval,
            },
        )
    coverage = observations["coverage"]
    complete_absence_scope = (
        coverage["complete_file_scan"] is True
        and coverage["uninterpreted_packets"] == 0
        and observations["capture"]["unknown_blocks"] == 0
        and "SNAPSHOT_TRUNCATED_PACKETS_PRESENT" not in observations["capture"]["limitations"]
    )
    limitations = list(_LIMITATIONS)
    if not complete_absence_scope:
        limitations.append(
            "Declared-service absence findings were suppressed because packet interpretation "
            "or container coverage is incomplete; skipped bytes may contain relevant traffic."
        )
    return {
        "comparison_version": 1,
        "capture_sha256": observations["capture"]["sha256"],
        "model_sha256": validated.sha256,
        "observations_sha256": observations["observations_sha256"],
        "mapping_sha256": _digest(review),
        "association_decisions": review["proposals"],
        "findings": findings,
        "declared_services_not_observed": [
            {
                "service_id": service.id,
                "classification": "DECLARED_SERVICE_NOT_OBSERVED",
                "reason": "No reviewed decoded destination header matched this declared "
                "service in this capture; this does not establish blocking.",
            }
            for service in services
            if complete_absence_scope and service.id not in observed_services
        ],
        "absence_assessment": {
            "status": "scoped" if complete_absence_scope else "suppressed",
            "reason": "Absence is assessed only in fully scanned, fully interpreted packet "
            "metadata without unknown blocks or snapshot truncation; sensor visibility "
            "still remains unknown.",
        },
        "absence_scope": "All declared services versus accepted decoded IPv4 destination "
        "headers in this finite capture only; no visibility completeness is asserted.",
        "work": {
            "native_query_pairs": len(pairs),
            "native_evidence_accounted_bytes": native_allocated,
            "native_output_accounted_bytes": native_output_bytes,
            "query_atoms": engine.queries_reserved if engine is not None else 0,
            "state_edge_visits": engine.work.state_edge_visits if engine is not None else 0,
            "edge_rule_atom_checks": engine.work.edge_rule_atom_checks if engine is not None else 0,
        },
        "limitations": limitations,
    }
