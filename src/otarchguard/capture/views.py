"""Read-only presentation of canonical capture counts, scope and protocol hints."""

from collections import Counter
from typing import Any

from otarchguard.capture.display import bullet_list, identity, property_list
from otarchguard.explorer_html import escape, table

CLASSIFICATION_LABELS = {
    "OBSERVED_MODEL_REACHABLE": "Compatible with declared reachability",
    "OBSERVED_MODEL_UNREACHABLE": "Discrepancy with declared reachability",
    "OBSERVED_SERVICE_UNDECLARED": "No matching declared service",
    "OBSERVED_ENDPOINT_UNMAPPED": "Endpoint not associated with the model",
    "OBSERVED_DIRECTION_UNCERTAIN": "Initiation direction uncertain",
    "OBSERVED_MODEL_UNSUPPORTED": "Outside current model capabilities",
    "OBSERVED_EVALUATION_INCOMPLETE": "Declared-model evaluation incomplete",
    "DECLARED_SERVICE_NOT_OBSERVED": "Declared service not observed",
    "EVIDENCE_AMBIGUOUS": "Evidence identity is ambiguous",
}

INTERPRETATIONS = {
    "OBSERVED_MODEL_REACHABLE": "The native model supports this specific evaluated initiation "
    "and destination port. This does not prove deployed authorization or application success.",
    "OBSERVED_MODEL_UNREACHABLE": "The native model evaluates this initiation as unreachable. "
    "This does not prove that a physical firewall denied the observed traffic.",
    "OBSERVED_SERVICE_UNDECLARED": "The observed destination header has no matching declared "
    "service within the reviewed model scope. This does not establish unauthorized traffic.",
    "OBSERVED_ENDPOINT_UNMAPPED": "The owner-reviewed endpoint mapping needed for model "
    "evaluation is missing or insufficient.",
    "OBSERVED_DIRECTION_UNCERTAIN": "The available packet evidence does not establish a unique "
    "justified initiator. No model reachability conclusion is made.",
    "OBSERVED_MODEL_UNSUPPORTED": "This observation cannot be evaluated under the current "
    "native analytical scope. Unsupported does not mean blocked or authorized.",
    "OBSERVED_EVALUATION_INCOMPLETE": "The declared-model evaluation did not complete for this "
    "observation. Its reachability remains unassessed.",
    "DECLARED_SERVICE_NOT_OBSERVED": "No matching observation appeared within the documented "
    "capture and interpretation scope. This does not prove blocking or absence outside that scope.",
    "EVIDENCE_AMBIGUOUS": "The evidence matches multiple declared interfaces or services. "
    "A unique supported model evaluation is not established; the observation remains unassessed.",
}

_CAPTURE_LIMITATIONS = {
    "SNAPSHOT_TRUNCATED_PACKETS_PRESENT": "Some packet records retain fewer bytes than their "
    "reported original length; relevant headers or traffic may be incomplete.",
    "PACKETS_WITHOUT_TIMESTAMPS": "Some packet records have no timestamp; missing times remain "
    "unknown.",
    "UNKNOWN_BLOCK_CONTENTS_NOT_INTERPRETED": "Unknown capture-container blocks were counted "
    "but their content was not interpreted.",
    "OBSOLETE_PACKET_BLOCKS_NOT_DECODED": "Obsolete PCAPNG Packet Blocks were counted as "
    "unknown content and were not decoded.",
    "PCAPNG_MINOR_2_TREATED_AS_0": "Compatible PCAPNG minor-version 2 sections were interpreted "
    "using the supported version 1.0 subset.",
}

PORT_HINT_NOTICE = (
    "Port hints are associations based on observed port numbers. They do not confirm that the "
    "corresponding industrial application protocol was decoded or used successfully."
)


def interpretation(code: str) -> str:
    return INTERPRETATIONS.get(
        code,
        "This classification is not recognized by this presentation. Treat it as unassessed "
        "and consult the canonical evidence.",
    )


def _label(code: str) -> str:
    return CLASSIFICATION_LABELS.get(code, code)


def _transport(value: str) -> str:
    return "Unknown" if value == "unknown" else value.upper()


def overview_summary(observations: dict[str, Any], comparison: dict[str, Any] | None) -> str:
    """Expose canonical inventory/counts; flow and declaration counts stay distinct."""
    coverage = observations["coverage"]
    metrics: list[tuple[object, object]] = [
        ("Total packet records", coverage["packets"]),
        ("Observed addresses", len(observations["hosts"])),
        ("Directed aggregates", len(observations["flows"])),
        ("Bidirectional groups", len(observations["conversations"])),
        ("Decoded packet records", coverage["decoded"]),
        ("Unsupported packet records", coverage["unsupported"]),
        (
            "Model-comparison flow findings",
            len(comparison["findings"]) if comparison else "Not requested",
        ),
    ]
    body = "<h2>Capture summary</h2>" + property_list(metrics)
    body += (
        "<p>These counts describe capture records and evidence aggregates. They do not count "
        "established sessions or prove complete sensor visibility.</p>"
    )
    if comparison is None:
        return body + "<p>Model comparison was not requested; no finding count is inferred.</p>"
    categories: Counter[str] = Counter(f["classification"] for f in comparison["findings"])
    rows = [
        (escape(_label(code)), escape(count), "Directed aggregates", escape(interpretation(code)))
        for code, count in sorted(categories.items())
    ]
    declarations = comparison["declared_services_not_observed"]
    body += property_list([("Declared services not observed", len(declarations))])
    if declarations:
        code = "DECLARED_SERVICE_NOT_OBSERVED"
        rows.append(
            (
                escape(_label(code)),
                escape(len(declarations)),
                "Declared services",
                escape(interpretation(code)),
            )
        )
    return body + table(
        "Comparison categories", ("Category", "Count", "Counted evidence", "Interpretation"), rows
    )


def capture_metadata(capture: dict[str, Any]) -> str:
    body = "<h2>Capture metadata</h2>" + property_list(
        [
            ("Container format", capture["format"].upper()),
            ("File bytes", capture["size_bytes"]),
            ("Packet records", capture["packets"]),
            ("Captured packet bytes", capture["captured_bytes"]),
            ("Reported original packet bytes", capture["original_bytes"]),
            ("Container blocks", capture["blocks"]),
            ("Unknown blocks", capture["unknown_blocks"]),
        ]
    )
    rows = [
        tuple(
            escape(i[key])
            for key in (
                "section",
                "interface",
                "linktype",
                "snaplen",
                "timestamp_denominator",
                "timestamp_offset_seconds",
            )
        )
        for i in capture["interfaces"]
    ]
    return (
        body
        + table(
            "Capture interfaces",
            (
                "Section",
                "Interface",
                "Link type",
                "Snapshot bytes",
                "Timestamp ticks per second",
                "Timestamp offset (seconds)",
            ),
            rows,
        )
        + (
            "<p>Interface numbers are local to each section. Interface metadata describes the "
            "capture format and does not establish physical links or clock accuracy. A zero "
            "snapshot length has no interface-level snapshot limit; product budgets still "
            "apply.</p>"
        )
        + identity("Capture SHA-256", capture["sha256"])
    )


def protocols_view(flows: list[dict[str, Any]]) -> str:
    transports: Counter[str] = Counter()
    hints: Counter[tuple[str, str, int, str]] = Counter()
    for flow in flows:
        transport, packets = flow["transport"], flow["packets"]
        transports[transport] += packets
        for hint in flow["protocol_hints"]:
            hints[transport, hint["protocol"], hint["port"], hint["level"]] += packets
    body = "<h2>Transport categories in packet metadata</h2>" + table(
        "Packet records by transport",
        ("Transport", "Observed packet records"),
        [(escape(_transport(name)), escape(count)) for name, count in sorted(transports.items())],
    )
    body += '<h2>Industrial port hints</h2><p class="notice">' + escape(PORT_HINT_NOTICE) + "</p>"
    rows = [
        (
            escape(protocol),
            escape(_transport(transport)),
            escape(port),
            escape(count),
            escape(level),
        )
        for (transport, protocol, port, level), count in sorted(hints.items())
    ]
    body += (
        table(
            "Port associations",
            (
                "Suggested protocol",
                "Observed transport",
                "Port",
                "Packet records",
                "Evidence category",
            ),
            rows,
        )
        if rows
        else "<p>No port associations were recorded.</p>"
    )
    return body + (
        "<p>Hint counts may overlap: a packet can contribute to multiple port associations, "
        "so their sum may exceed the total packet count. Transport labels come from the "
        "corresponding observed aggregate. A category may be known from an IP header even "
        "when transport decoding is incomplete. No application or session success is inferred.</p>"
    )


def coverage_view(observations: dict[str, Any], comparison: dict[str, Any] | None) -> str:
    coverage = observations["coverage"]
    body = "<h2>Capture processing</h2>" + property_list(
        [
            ("Total packet records", coverage["packets"]),
            ("Decoded", coverage["decoded"]),
            ("Unsupported", coverage["unsupported"]),
            ("Malformed", coverage["malformed"]),
            ("Truncated", coverage["truncated"]),
            ("Fragmented", coverage["fragmented"]),
            ("Complete container scan", coverage["complete_file_scan"]),
            ("Interpreted packet records", coverage["interpreted_packets"]),
            ("Uninterpreted packet records", coverage["uninterpreted_packets"]),
            ("Snapshot-truncated records", coverage["capture_records_truncated"]),
        ]
    )
    body += (
        "<p>A successful container scan means the file framing was processed. Decoding means "
        "a packet was interpreted within the supported subset. Neither establishes complete "
        "analytical coverage, successful communication or physical sensor visibility.</p>"
        "<h2>Observation limitations</h2>"
    ) + bullet_list(observations["limitations"], empty="No observation limitations were recorded.")
    limits = observations["capture"]["limitations"]
    body += (
        "<h2>Capture-container limitations</h2>"
        + bullet_list(
            [_CAPTURE_LIMITATIONS.get(value, value) for value in limits],
            empty="No additional capture-container limitations were recorded.",
        )
        + "<p>This does not establish full sensor coverage or complete capture visibility.</p>"
    )
    body += "<h2>Comparison limitations</h2>"
    if comparison is None:
        return body + "<p>Model comparison was not requested.</p>"
    body += bullet_list(
        comparison["limitations"], empty="No additional comparison limitations recorded."
    )
    assessment = comparison["absence_assessment"]
    status = {"scoped": "Scoped to this finite capture", "suppressed": "Suppressed"}.get(
        assessment["status"], assessment["status"]
    )
    return (
        body
        + "<h2>Declared-service observation scope</h2>"
        + property_list(
            [
                ("Absence assessment", status),
                ("Reason", assessment["reason"]),
                ("Scope", comparison["absence_scope"]),
            ]
        )
        + (
            "<p>A declared service not observed does not prove blocking, service unavailability "
            "or absence of communication outside the documented scope.</p>"
        )
    )
