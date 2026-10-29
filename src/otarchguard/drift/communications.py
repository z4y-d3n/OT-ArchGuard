"Directional finite-capture relationship joins with bounded source evidence."

from fractions import Fraction
from typing import Any

from otarchguard.drift.contract import Budget, Side, finding, source
from otarchguard.evidence.attachments import canonical

_SAMPLES = 8


def _key(flow: dict[str, Any]) -> dict[str, Any]:
    result = {
        name: flow[name]
        for name in (
            "ip_version",
            "source_ip",
            "destination_ip",
            "transport",
            "source_port",
            "destination_port",
            "vlans",
        )
    }
    result["arp_operation"] = (
        {name: flow["arp"][name] for name in ("opcode", "operation")}
        if flow["arp"] is not None
        else None
    )
    result["opaque_linktype"] = (
        flow["linktype"] if flow["source_ip"] is flow["destination_ip"] is None else None
    )
    return result


def _index(side: Side, budget: Budget) -> dict[bytes, dict[str, Any]]:
    indexed: dict[bytes, dict[str, Any]] = {}
    for flow in side.snapshot["observations"]["flows"]:
        budget.charge("work_units")
        key = _key(flow)
        encoded = canonical(key)
        if encoded not in indexed:
            budget.charge("keys")
            indexed[encoded] = {"key": key, "flows": []}
        indexed[encoded]["flows"].append(flow)
    return indexed


def _stamp(flows: list[dict[str, Any]], name: str, minimum: bool) -> str | None:
    values = [Fraction(f[name]) for f in flows if f[name] is not None]
    if not values:
        return None
    result = min(values) if minimum else max(values)
    return f"{result.numerator}/{result.denominator}"


def _summary(side: Side, group: dict[str, Any], budget: Budget) -> dict[str, Any]:
    flows = sorted(group["flows"], key=lambda f: f["id"])
    packets = sum(f["packets"] for f in flows)
    status_counts: dict[str, int] = {}
    unions: dict[str, dict[bytes, Any]] = {
        name: {} for name in ("source_macs", "destination_macs", "tcp_flags", "protocol_hints")
    }
    packet_refs: list[dict[str, Any]] = []
    initiation_refs: list[dict[str, Any]] = []
    for flow in flows:
        budget.charge("work_units")
        status_counts[flow["status"]] = status_counts.get(flow["status"], 0) + flow["packets"]
        for name, values in unions.items():
            budget.charge("work_units", len(flow[name]))
            for value in flow[name]:
                values[canonical(value)] = value
        for name, refs in (("samples", packet_refs), ("initiation_evidence", initiation_refs)):
            for packet in flow[name]:
                if len(refs) < _SAMPLES:
                    refs.append({"flow_id": flow["id"], "packet": packet})
    budget.charge("references", min(len(flows), _SAMPLES) + len(packet_refs) + len(initiation_refs))
    metadata: dict[str, Any] = {
        "packets": packets,
        "captured_bytes": sum(f["captured_bytes"] for f in flows),
        "original_bytes": sum(f["original_bytes"] for f in flows),
        "status_packet_counts": dict(sorted(status_counts.items())),
        "linktypes": sorted({f["linktype"] for f in flows}),
        "transport_evidence": sorted({f["transport_evidence"] for f in flows}),
        "initiation_packets": sum(f["initiation_packets"] for f in flows),
        "arp_headers": [
            value
            for _, value in sorted(
                {canonical(f["arp"]): f["arp"] for f in flows if f["arp"] is not None}.items()
            )
        ],
    }
    metadata.update(
        {name: [value for _, value in sorted(values.items())] for name, values in unions.items()}
    )
    return {
        "source": source(side),
        "metadata": metadata,
        "observed_window": {
            "first_timestamp": _stamp(flows, "first_timestamp", True),
            "last_timestamp": _stamp(flows, "last_timestamp", False),
            "missing_timestamps": sum(f["missing_timestamps"] for f in flows),
        },
        "flow_references": [
            {"flow_id": f["id"], "conversation_id": f["conversation_id"]} for f in flows[:_SAMPLES]
        ],
        "flow_references_omitted": max(0, len(flows) - _SAMPLES),
        "packet_references": packet_refs,
        "packet_references_omitted": packets - len(packet_refs),
        "initiation_references": initiation_refs,
        "initiation_references_omitted": metadata["initiation_packets"] - len(initiation_refs),
        "reference_policy": (
            "At most eight source flow, packet and initiation references per "
            "relationship; exact sources retain full bounded evidence."
        ),
    }


def _accepted(side: Side, budget: Budget) -> dict[str, dict[str, Any]]:
    mapping = side.attachments.get("mapping")
    if mapping is None:
        return {}
    budget.charge("work_units", len(mapping["payload"]["proposals"]))
    return {
        p["observed_ip"]: p for p in mapping["payload"]["proposals"] if p["decision"] == "ACCEPT"
    }


def _associations(
    key: dict[str, Any],
    reference: Side,
    candidate: Side,
    mappings: list[dict[str, dict[str, Any]]],
    budget: Budget,
) -> dict[str, Any]:
    models = [side.attachments.get("model") for side in (reference, candidate)]
    if not all(models) or models[0]["component_sha256"] != models[1]["component_sha256"]:  # type: ignore[index]
        return {
            "status": "INDETERMINATE",
            "reason": "Exact common model and independently reviewed mappings are required.",
        }
    identities: list[dict[str, Any]] = []
    for endpoint in ("source_ip", "destination_ip"):
        decisions = [mapping.get(key[endpoint]) for mapping in mappings]
        if not all(decisions):
            return {
                "status": "INDETERMINATE",
                "reason": (
                    "At least one endpoint lacks an independently ACCEPTed association on "
                    "both sides."
                ),
            }
        first, second = decisions
        assert first is not None and second is not None
        if any(
            first[name] != second[name] for name in ("selected_asset_id", "selected_interface_id")
        ):
            return {
                "status": "INDETERMINATE",
                "reason": "Reviewed endpoint associations differ across selected captures.",
            }
        budget.charge("references", 2)
        identities.append(
            {
                "endpoint": endpoint,
                "asset_id": first["selected_asset_id"],
                "interface_id": first["selected_interface_id"],
                "reference_association_id": first["id"],
                "candidate_association_id": second["id"],
            }
        )
    return {
        "status": "EQUIVALENT_REVIEWED_MODEL_ASSOCIATIONS",
        "model_sha256": models[0]["component_sha256"],  # type: ignore[index]
        "endpoints": identities,
        "limitation": (
            "Equivalent independently reviewed model-relative assertions do not "
            "prove physical device continuity."
        ),
    }


def compare_communications(
    reference: Side, candidate: Side, assessment: dict[str, Any], budget: Budget
) -> list[dict[str, Any]]:
    """Join directional tuples without inferring role, sessions or absence."""
    first, second = _index(reference, budget), _index(candidate, budget)
    mappings = [_accepted(side, budget) for side in (reference, candidate)]
    results: list[dict[str, Any]] = []
    for encoded in sorted(first.keys() | second.keys()):
        budget.charge("work_units")
        a, b = first.get(encoded), second.get(encoded)
        key = (a if a is not None else b)["key"]  # type: ignore[index]
        reference_value = _summary(reference, a, budget) if a is not None else None
        candidate_value = _summary(candidate, b, budget) if b is not None else None
        if a is None:
            subtype = "CANDIDATE_ONLY_OBSERVATION"
            explanation = (
                "Observed in the candidate capture but not identified in the selected "
                "reference capture."
            )
        elif b is None:
            subtype = "REFERENCE_ONLY_OBSERVATION"
            explanation = (
                "Observed in the reference capture but not identified in the selected "
                "candidate capture."
            )
        elif reference_value["metadata"] != candidate_value["metadata"]:  # type: ignore[index]
            subtype = "OBSERVED_METADATA_CHANGED"
            explanation = (
                "The same directional raw relationship has different supported "
                "aggregate metadata in the selected finite captures."
            )
        else:
            subtype = "OBSERVED_IN_BOTH"
            explanation = (
                "The directional raw relationship and supported aggregate metadata "
                "were observed in both selected evidence sets."
            )
        state = assessment["communication_metadata"]
        if key["source_ip"] is key["destination_ip"] is None:
            subtype = "UNASSESSED_OPAQUE_OBSERVATIONS"
            explanation = (
                "Only opaque packet groups can be compared; no supported endpoint "
                "communication identity is available."
            )
            state = "INDETERMINATE"
        association = _associations(key, reference, candidate, mappings, budget)
        for value in (reference_value, candidate_value):
            if value is not None:
                value["reviewed_asset_correspondence"] = association
        results.append(
            finding(
                "OBSERVED_COMMUNICATION_DIFFERENCE",
                subtype,
                key,
                reference_value,
                candidate_value,
                state,
                explanation,
                budget,
                [
                    (
                        "Direction follows observed packet headers, not inferred "
                        "client/server or session roles."
                    ),
                    (
                        "Missing observations do not establish absent traffic, blocked "
                        "connections, outages or device removal."
                    ),
                    (
                        "Coverage, vantage points and raw packet counts may differ; "
                        "operational interpretation is withheld."
                    ),
                ]
                if state != "COMPARABLE"
                else [
                    (
                        "Raw endpoints are communication metadata, not stable physical device "
                        "identities."
                    ),
                    (
                        "No independent operational absence, application-success or "
                        "normalized activity claim is supported."
                    ),
                ],
            )
        )
    return results
