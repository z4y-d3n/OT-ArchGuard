"""Schema-aware F1 exposure tables, used only by the opt-in Explorer prototype."""

import json
from collections.abc import Callable, Sequence
from dataclasses import asdict
from html import escape as html_escape
from html import unescape
from typing import Any

from otarchguard.explorer_html import escape, link, table
from otarchguard.exposure import ExposureResult
from otarchguard.intents import IntentResult
from otarchguard.reachability import IntervalResult, QueryResult

type Value = Callable[[object, str], str]


def _truth(value: object) -> str:
    if type(value) is bool:
        return "Yes" if value else "No"
    return "Not retained" if value is None else "Unsupported retained value: " + escape(value)


def _range(start: int, end: int) -> str:
    return escape(f"{start}–{end}")


def _values(values: Sequence[str], field: str, value: Value) -> str:
    return " · ".join(value(item, field) for item in values) or "None retained"


def _context(query: QueryResult, interval: IntervalResult) -> str:
    return (
        f"{query.source_asset_id} → {query.destination_asset_id} · {query.service_id} · "
        f"{query.protocol} {interval.start}–{interval.end}"
    )


def _interval_rows(
    queries: Sequence[QueryResult],
    value: Value,
    destinations: dict[tuple[str, str], str],
) -> list[tuple[str, ...]]:
    rows: list[tuple[str, ...]] = []
    for query in queries:
        destination = destinations.get((query.source_asset_id, query.service_id))
        for interval in query.intervals:
            diagnostic = interval.diagnostics
            rows.append(
                (
                    value(query.source_asset_id, "source_asset_id"),
                    value(query.destination_asset_id, "destination_asset_id"),
                    value(query.service_id, "service_id"),
                    escape(query.protocol),
                    _range(interval.start, interval.end),
                    _truth(interval.reachable),
                    _truth(diagnostic.structural_path_exists) if diagnostic else "Not retained",
                    escape(diagnostic.reason) if diagnostic else "No diagnostic retained",
                    link(destination, "Complete query evidence")
                    if destination
                    else link("#exposure-exact-evidence", "Complete exact evidence"),
                )
            )
    return rows


_INTERVAL_HEADERS = (
    "Source",
    "Destination",
    "Service",
    "Protocol",
    "Exact port range",
    "Reachable",
    "Structural path (diagnostic)",
    "Global diagnostic reason",
    "Evidence",
)


def _evidence(
    query: QueryResult,
    interval: IntervalResult,
    value: Value,
    *,
    show_diagnostic: bool = True,
    group: str = "",
) -> str:
    """Keep each diagnostic edge and ordered step separate; never fuse their reasons."""
    context = (group + " · " if group else "") + _context(query, interval)
    body = ""
    diagnostic = interval.diagnostics
    if diagnostic is not None and show_diagnostic:
        body += table(
            "Diagnostic bounds and limitation · " + context,
            ("Recorded blocked-edge count", "Retained edge records", "Truncated", "Limitation"),
            [
                (
                    escape(diagnostic.blocked_edge_count),
                    escape(len(diagnostic.blocked_edges)),
                    _truth(diagnostic.truncated),
                    escape(diagnostic.limitation),
                )
            ],
        )
        body += table(
            "Individual blocked-edge evidence · " + context,
            ("Record", "Edge ID", "Edge reason", "Allow rules", "Deny rules"),
            [
                (
                    str(index),
                    value(edge.edge_id, "edge_id"),
                    escape(edge.reason),
                    _values(edge.allow_rule_ids, "allow_rule_ids", value),
                    _values(edge.deny_rule_ids, "deny_rule_ids", value),
                )
                for index, edge in enumerate(diagnostic.blocked_edges, 1)
            ],
            row_headers=True,
        )
    witness = interval.witness
    if witness is not None:
        body += (
            "<p>Retained witness binding: "
            + value(witness.source_asset_id, "source_asset_id")
            + " → "
            + value(witness.destination_asset_id, "destination_asset_id")
            + " · "
            + value(witness.service_id, "service_id")
            + " · "
            + escape(witness.protocol)
            + " "
            + _range(witness.start, witness.end)
            + ". Witness model SHA-256: <code>"
            + escape(witness.snapshot_sha256)
            + "</code>.</p>"
        )
        body += table(
            "Ordered witness steps · " + context,
            ("Step", "Edge ID", "Kind", "Conduit", "Allow rules"),
            [
                (
                    str(index),
                    value(step.edge_id, "edge_id"),
                    escape(step.kind),
                    value(step.conduit_id, "conduit_id")
                    if step.conduit_id is not None
                    else "None declared",
                    _values(step.allow_rule_ids, "allow_rule_ids", value),
                )
                for index, step in enumerate(witness.steps, 1)
            ],
            row_headers=True,
        )
        endpoints = []
        for index, step in enumerate(witness.steps, 1):
            for role, endpoint in (("Source", step.source), ("Target", step.target)):
                endpoints.append(
                    (
                        str(index),
                        role,
                        value(endpoint.asset_id, "asset_id"),
                        value(endpoint.state.interface_id, "interface_id"),
                        escape(endpoint.state.phase),
                        escape(endpoint.ipv4),
                        value(endpoint.placement_zone_id, "placement_zone_id"),
                    )
                )
        body += table(
            "Witness step endpoints · " + context,
            (
                "Step",
                "Endpoint",
                "Asset",
                "Interface",
                "Phase",
                "IPv4 declaration",
                "Placement zone",
            ),
            endpoints,
            row_headers=True,
        )
        if not witness.steps:
            body += "<p>No witness steps retained.</p>"
    if witness is None and diagnostic is None:
        body += '<p class="notice">No witness or diagnostic retained for this exact interval.</p>'
    return body


def _intent(intent: IntentResult, value: Value, destinations: dict[tuple[str, str], str]) -> str:
    body = "<h3>" + value(intent.id, "required_intent_ids")
    body += " · Kind: " + escape(intent.kind) + " · Passed: " + _truth(intent.passed) + "</h3>"
    body += table(
        "Exact evaluated intent intervals · " + intent.id,
        _INTERVAL_HEADERS,
        _interval_rows(intent.queries, value, destinations),
    )
    for query in intent.queries:
        if not query.intervals:
            body += (
                "<p>No intervals retained for "
                + escape(
                    f"{query.source_asset_id} → {query.destination_asset_id} · "
                    f"{query.service_id} · {query.protocol}"
                )
                + ".</p>"
            )
        for interval in query.intervals:
            body += _evidence(query, interval, value, group="Intent " + intent.id)
    if not intent.queries:
        body += "<p>No query records retained for this intent.</p>"
    return body


def _prohibited(intents: Sequence[IntentResult], value: Value) -> str:
    """One comparison table, with separately keyed diagnostic/edge records."""
    results: list[tuple[str, ...]] = []
    bounds: list[tuple[str, ...]] = []
    edges: list[tuple[str, ...]] = []
    absent: list[tuple[str, ...]] = []
    witnesses = ""
    for intent in intents:
        if not intent.queries:
            absent.append(
                (
                    value(intent.id, "required_intent_ids"),
                    _truth(intent.passed),
                    "No query records retained",
                )
            )
        for query in intent.queries:
            if not query.intervals:
                absent.append(
                    (
                        value(intent.id, "required_intent_ids"),
                        _truth(intent.passed),
                        escape(
                            f"No intervals retained: {query.source_asset_id} → "
                            f"{query.destination_asset_id} · {query.service_id} · {query.protocol}"
                        ),
                    )
                )
            for interval in query.intervals:
                number = len(results) + 1
                label, anchor = f"P{number}", f"exposure-prohibited-{number}"
                reference = link("#" + anchor, label)
                diagnostic = interval.diagnostics
                results.append(
                    (
                        '<code id="' + anchor + '">' + label + "</code>",
                        value(intent.id, "required_intent_ids"),
                        _truth(intent.passed),
                        value(query.source_asset_id, "source_asset_id"),
                        value(query.destination_asset_id, "destination_asset_id"),
                        value(query.service_id, "service_id") + " · " + escape(query.protocol),
                        _range(interval.start, interval.end),
                        _truth(interval.reachable),
                        _truth(diagnostic.structural_path_exists) if diagnostic else "Not retained",
                        escape(diagnostic.reason) if diagnostic else "No diagnostic retained",
                    )
                )
                if diagnostic is not None:
                    bounds.append(
                        (
                            reference,
                            escape(diagnostic.blocked_edge_count),
                            escape(len(diagnostic.blocked_edges)),
                            _truth(diagnostic.truncated),
                            escape(diagnostic.limitation),
                        )
                    )
                    for index, edge in enumerate(diagnostic.blocked_edges, 1):
                        edges.append(
                            (
                                reference,
                                str(index),
                                value(edge.edge_id, "edge_id"),
                                escape(edge.reason),
                                _values(edge.allow_rule_ids, "allow_rule_ids", value),
                                _values(edge.deny_rule_ids, "deny_rule_ids", value),
                            )
                        )
                if interval.witness is not None:
                    witnesses += "<h3>Retained prohibited-intent witness · " + reference + "</h3>"
                    witnesses += _evidence(
                        query,
                        interval,
                        value,
                        show_diagnostic=False,
                        group="Prohibited interval " + label,
                    )
    body = table(
        "Prohibited intent interval results",
        (
            "Record",
            "Intent",
            "Intent passed",
            "Source",
            "Destination",
            "Service / protocol",
            "Exact port range",
            "Reachable",
            "Structural path (diagnostic)",
            "Global diagnostic reason",
        ),
        results,
        row_headers=True,
    )
    if bounds:
        body += table(
            "Prohibited diagnostic bounds and limitations",
            (
                "Record",
                "Recorded blocked-edge count",
                "Retained edge records",
                "Truncated",
                "Limitation",
            ),
            bounds,
            row_headers=True,
        )
    if edges:
        body += table(
            "Individual prohibited blocked-edge records",
            (
                "Interval record",
                "Edge record",
                "Edge ID",
                "Edge reason",
                "Allow rules",
                "Deny rules",
            ),
            edges,
            row_headers=True,
        )
    if absent:
        body += table(
            "Prohibited intents without retained intervals",
            ("Intent", "Intent passed", "Missing evidence"),
            absent,
            row_headers=True,
        )
    return body + witnesses


def exposure_tables(
    result: ExposureResult,
    value: Value,
    query_links: Sequence[tuple[str, str]],
) -> str:
    """Five primary sections plus complete exact evidence outside the tables.

    Observations are the exposure engine's normalized model-reachable intervals,
    not packet observations. Independent intents may extend beyond scenario scope.
    No absence of diagnostics is converted to a structural-path assertion.
    """
    checks = result.intent_checks
    destinations = {
        (query.source_asset_id, query.service_id): target
        for query, (target, _) in zip(result.queries, query_links, strict=True)
    }
    overview = [
        ("Scenario", value(result.scenario_id, "scenario_id")),
        ("Declared system ID", escape(result.suc_id)),
        ("Scenario passed", _truth(result.passed)),
        ("Model SHA-256", "<code>" + escape(result.snapshot_sha256) + "</code>"),
        ("Origin scope", _values(result.query_scope.origin_asset_ids, "origin_asset_ids", value)),
        (
            "Destination service scope",
            _values(result.query_scope.destination_service_ids, "destination_service_ids", value),
        ),
        (
            "Unavailable origins",
            _values(result.unavailable_origin_asset_ids, "origin_asset_ids", value),
        ),
        (
            "Unavailable services",
            _values(result.unavailable_destination_service_ids, "destination_service_ids", value),
        ),
        (
            "Exposure evaluation metrics",
            escape(
                f"Atom queries: {result.atom_queries} · "
                f"State/edge visits: {result.state_edge_visits} · "
                f"Edge/rule/atom checks: {result.edge_rule_atom_checks}"
            ),
        ),
        ("Completeness assertion", escape(result.completeness_assertion)),
        ("Interpretation limitation", escape(result.interpretation)),
        (
            "Independent intent outcomes",
            "Passed: "
            + _truth(checks.passed)
            + escape(
                f" · Failed intents: {checks.failed_intent_count} · "
                f"Failed intervals: {checks.failed_interval_count}"
            ),
        ),
        ("Intent-check model SHA-256", "<code>" + escape(checks.snapshot_sha256) + "</code>"),
        (
            "Intent evaluation metrics",
            escape(
                f"Atom queries: {checks.atom_queries} · "
                f"State/edge visits: {checks.state_edge_visits} · "
                f"Edge/rule/atom checks: {checks.edge_rule_atom_checks}"
            ),
        ),
        ("Intent scope limitation", escape(checks.scope)),
    ]
    body = '<div class="exposure-tables"><section><h2>Scenario overview</h2>'
    body += "<p>Declared initiation reachability only. Independent intents may extend beyond "
    body += "the selected scenario scope. No session, deployed enforcement or operational "
    body += "success is asserted. Port bounds are inclusive destination ports.</p>"
    body += table(
        "Scenario properties and evaluation scope",
        ("Property", "Retained value"),
        [(escape(name), rendered) for name, rendered in overview],
        row_headers=True,
    )
    body += "</section><section><h2>Destination assets</h2>"
    body += "<p>Destinations in retained model-reachable observations; criticality is declared.</p>"
    body += table(
        "Retained destination assets",
        ("Asset ID", "Criticality"),
        [
            (value(asset.asset_id, "asset_id"), escape(asset.criticality))
            for asset in result.destination_assets
        ],
        row_headers=True,
    )
    body += "</section><section><h2>Observations</h2>"
    body += "<p>Normalized model-reachable initiation intervals retained by the exposure engine; "
    body += "these are not captured packets or successful application sessions.</p>"
    body += table(
        "Retained exposure observations",
        ("Source", "Destination", "Service", "Protocol", "Exact port range"),
        [
            (
                value(flow.source_asset_id, "source_asset_id"),
                value(flow.destination_asset_id, "destination_asset_id"),
                value(flow.service_id, "service_id"),
                escape(flow.protocol),
                _range(flow.start, flow.end),
            )
            for flow in result.observations
        ],
    )
    body += table(
        "All evaluated scenario intervals",
        _INTERVAL_HEADERS,
        _interval_rows(result.queries, value, destinations),
    )
    # Exact equal query evidence already displayed with its intent is not repeated.
    covered = {query for intent in checks.intents for query in intent.queries}
    for query, (target, label) in zip(result.queries, query_links, strict=True):
        if not query.intervals:
            body += (
                "<p>No intervals retained: "
                + link(target, label)
                + " · "
                + escape(f"destination {query.destination_asset_id} · {query.protocol}")
                + ".</p>"
            )
        if query not in covered:
            body += "<h3>Additional scenario evidence · " + link(target, label) + "</h3>"
            for interval in query.intervals:
                body += _evidence(query, interval, value)
    body += "</section><section><h2>Prohibited intents</h2>"
    prohibited = [intent for intent in checks.intents if intent.kind == "prohibited"]
    body += _prohibited(prohibited, value)
    if not prohibited:
        body += "<p>No prohibited intents retained.</p>"
    body += "</section><section><h2>Required intents and path steps</h2>"
    required = [intent for intent in checks.intents if intent.kind == "required"]
    body += "".join(_intent(intent, value, destinations) for intent in required)
    if not required:
        body += "<p>No required intents retained.</p>"
    for intent in checks.intents:
        if intent.kind not in {"required", "prohibited"}:
            body += (
                '<p class="notice">Unsupported retained intent kind; '
                "no classification inferred.</p>"
            )
            body += _intent(intent, value, destinations)
    body += (
        '</section><details id="exposure-exact-evidence"><summary>'
        "Complete exact exposure evidence · all retained records</summary>"
    )
    body += "<pre>" + _exact_evidence(result) + "</pre></details></div>"
    return body


def _exact_evidence(result: ExposureResult) -> str:
    """Escape the complete payload while applying the existing per-field boundary.

    Container JSON may exceed the per-field text ceiling. Validate and minimize
    each original string first, then HTML-escape the serialization as plain text.
    Local-path/bidi minimization remains the same as the primary Explorer view.
    """

    def retained(item: Any) -> Any:
        if isinstance(item, str):
            return unescape(escape(item))
        if isinstance(item, dict):
            return {key: retained(value) for key, value in item.items()}
        if isinstance(item, (tuple, list)):
            return [retained(value) for value in item]
        return item

    return html_escape(json.dumps(retained(asdict(result)), sort_keys=True, indent=2), quote=True)
