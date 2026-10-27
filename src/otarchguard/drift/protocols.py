"Bounded structural protocol metadata joins under exact decoder equivalence."

from typing import Any

from otarchguard.drift.comparability import protocol_equivalent
from otarchguard.drift.contract import Budget, Side, finding, source
from otarchguard.evidence.attachments import canonical

# Only supported categorical/header identities participate. Lengths and transient
# transaction/sequence identities do not become protocol-operation differences.
_HEADERS = {
    "modbus_tcp": {"protocol_id", "unit_id", "function_code", "exception_response"},
    "profinet_dcp": {"frame_id", "service_id", "service_type"},
    "ethernet_ip": {
        "encapsulation_command",
        "encapsulation_status",
        "cip_metadata",
        "cip_service",
        "cip_response",
        "cip_operation",
    },
    "s7comm": {"protocol_id", "rosctr", "pdu_category", "function_code"},
    "iec104": {"frame_format", "asdu_type", "u_function"},
    "opcua_binary": {"message_type", "chunk_type"},
    "dnp3": {
        "link_status",
        "protocol_source",
        "protocol_destination",
        "link_function",
        "link_primary",
        "application_function",
        "application_category",
    },
}


def _manifest(side: Side) -> dict[str, Any]:
    attachment = side.attachments.get("enrichment")
    if attachment is None:
        return {"source": source(side), "enrichment": None}
    payload = attachment["payload"]
    return {
        "source": source(side),
        "capture_packets": payload["capture"]["packets"],
        "retained_records": len(payload["records"]),
        "enrichment": {
            name: payload[name]
            for name in (
                "enrichment_version",
                "decoder_version",
                "supported_protocols",
                "limits",
                "counts",
                "packets_with_records",
                "skipped_packets",
                "enrichment_sha256",
            )
        },
    }


def _index(side: Side, budget: Budget) -> dict[bytes, dict[str, Any]]:
    indexed: dict[bytes, dict[str, Any]] = {}
    for record in side.attachments["enrichment"]["payload"]["records"]:
        budget.charge("protocol_records")
        budget.charge("work_units")
        key = {
            name: record[name]
            for name in (
                "source_ip",
                "destination_ip",
                "source_port",
                "destination_port",
                "vlans",
                "protocol",
                "status",
                "recognition_method",
                "message_category",
            )
        }
        key["header_metadata"] = {
            name: value
            for name, value in record["fields"].items()
            if name in _HEADERS[record["protocol"]]
        }
        key["endpoint_scope"] = (
            "COLLECTION_LINK_METADATA"
            if record["source_ip"] is record["destination_ip"] is None
            else "OBSERVED_IP_HEADER"
        )
        encoded = canonical(key)
        if encoded not in indexed:
            budget.charge("keys")
            indexed[encoded] = {"key": key, "record_count": 0, "packet_references": []}
        group = indexed[encoded]
        group["record_count"] += 1
        if len(group["packet_references"]) < 8:
            budget.charge("references")
            group["packet_references"].append(
                {
                    "packet": record["packet"],
                    "record_offset": record["record_offset"],
                }
            )
    return indexed


def _summary(side: Side, group: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": source(side),
        "record_count": group["record_count"],
        "packet_references": group["packet_references"],
        "packet_references_omitted": group["record_count"] - len(group["packet_references"]),
        "reference_policy": (
            "At most eight original packet/record-offset references per metadata "
            "category; counts measure records, not sessions."
        ),
    }


def compare_protocols(
    reference: Side, candidate: Side, assessment: dict[str, Any], budget: Budget
) -> list[dict[str, Any]]:
    "Return structural category differences, abstaining across parser changes."
    if not protocol_equivalent(reference, candidate):
        absent = all("enrichment" not in side.attachments for side in (reference, candidate))
        return [
            finding(
                "INDETERMINATE_COMPARISON" if absent else "ANALYTICAL_INTERPRETATION_DIFFERENCE",
                "PROTOCOL_EVIDENCE_UNAVAILABLE" if absent else "PROTOCOL_SEMANTICS_CHANGED",
                {"domain": "protocol_metadata"},
                _manifest(reference),
                _manifest(candidate),
                "INDETERMINATE",
                "Selected analyses have no protocol enrichment evidence."
                if absent
                else (
                    "Selected enrichment schema, decoder, inventory, limits or local "
                    "consumer semantics are not equivalent; operational protocol "
                    "comparison is withheld."
                ),
                budget,
                [
                    (
                        "A decoder change can alter recognized metadata for the same physical "
                        "collection; it is not network-change evidence."
                    )
                ],
            )
        ]
    first, second = _index(reference, budget), _index(candidate, budget)
    results: list[dict[str, Any]] = []
    accounting_fields = ("counts", "packets_with_records", "skipped_packets")
    first_payload = reference.attachments["enrichment"]["payload"]
    second_payload = candidate.attachments["enrichment"]["payload"]
    budget.charge("work_units", len(accounting_fields))
    if any(first_payload[name] != second_payload[name] for name in accounting_fields):
        results.append(
            finding(
                "PROTOCOL_METADATA_DIFFERENCE",
                "PROTOCOL_COUNTERS_CHANGED",
                {"domain": "protocol_record_accounting"},
                _manifest(reference),
                _manifest(candidate),
                assessment["protocol_metadata"],
                (
                    "Raw retained protocol-status record counts, packets with records or "
                    "skipped-packet counters differ; these are finite-scan denominators "
                    "rather than activity rates."
                ),
                budget,
                [
                    (
                        "Counts measure retained records or explicitly named packets, not "
                        "independent sessions, successful commands or normalized activity."
                    )
                ],
            )
        )
    for encoded in sorted(first.keys() | second.keys()):
        budget.charge("work_units")
        a, b = first.get(encoded), second.get(encoded)
        if a is not None and b is not None and a["record_count"] == b["record_count"]:
            continue
        key = (a if a is not None else b)["key"]  # type: ignore[index]
        subtype = (
            "CANDIDATE_ONLY_METADATA"
            if a is None
            else "REFERENCE_ONLY_METADATA"
            if b is None
            else "RECORD_COUNTS_CHANGED"
        )
        results.append(
            finding(
                "PROTOCOL_METADATA_DIFFERENCE",
                subtype,
                key,
                _summary(reference, a) if a is not None else None,
                _summary(candidate, b) if b is not None else None,
                assessment["protocol_metadata"],
                (
                    "Supported structural metadata categories or their raw retained "
                    "record counts differ between the selected finite captures."
                ),
                budget,
                [
                    (
                        "Structural recognition, hints, truncation, malformed and unsupported "
                        "records retain distinct meanings."
                    ),
                    (
                        "Headers do not prove industrial command execution, process "
                        "manipulation, authorization or application success."
                    ),
                    (
                        "Missing protocol records do not prove protocol absence; record "
                        "counts are not normalized activity."
                    ),
                    (
                        "Link-layer records without IP endpoints are scoped to collection "
                        "metadata and do not establish device identity."
                    ),
                ],
            )
        )
    return results
