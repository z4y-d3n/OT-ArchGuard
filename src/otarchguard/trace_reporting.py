"""Separate trace-version-1 serialization with the accepted offline report styling."""

import json
from dataclasses import asdict

from otarchguard.reporting import _STYLE, _query_evidence, _query_rows, _table, escape
from otarchguard.trace import TraceResult


def trace_json(result: TraceResult) -> bytes:
    return (json.dumps(asdict(result), sort_keys=True, ensure_ascii=True, indent=2) + "\n").encode(
        "ascii"
    )


def trace_html(result: TraceResult) -> bytes:
    sections = (
        ("scope", "Service binding and finite scope"),
        ("intervals", "Exact destination-port intervals"),
        ("evidence", "Witness and bounded frontier evidence"),
        ("policy", "Optional policy evidence"),
        ("work", "Evaluation work"),
        ("interpretation", "Interpretation and unassessed conditions"),
        ("json", "Complete trace JSON"),
    )
    payload = asdict(result)
    query = {**asdict(result.scope), "intervals": payload["intervals"]}
    body = (
        '<a class="skip-link" href="#scope">Skip to trace scope</a>'
        "<header><h1>OT-ArchGuard · communication trace</h1>"
        f"<p>Status: {result.status}; trace version 1; engine {escape(result.engine_version)}; "
        f"schema 1.</p><p>Model SHA-256: <code>{escape(result.model_sha256)}</code></p>"
        "<p>Completion does not assert reachability. "
        "Communication intents: unassessed.</p></header>"
        '<nav aria-label="Trace contents"><ul>'
        + "".join(f'<li><a href="#{identity}">{title}</a></li>' for identity, title in sections)
        + '</ul></nav><main><section id="scope"><h2>Service binding and finite scope</h2>'
        + _table("One original source and declared listener", [asdict(result.scope)])
        + '</section><section id="intervals"><h2>Exact destination-port intervals</h2>'
        + _table(
            "Inclusive evaluator atoms",
            [
                {"start": i.start, "end": i.end, "protocol": i.protocol, "reachable": i.reachable}
                for i in result.intervals
            ],
        )
        + '</section><section id="evidence"><h2>Witness and bounded frontier evidence</h2>'
        "<p>A witness is one supported directed initiation route. No structural path differs "
        "from a structural path blocked by policy. Frontier entries may be truncated and "
        "establish neither a unique root cause nor a minimal cut or guaranteed fix.</p>"
        + _query_evidence(_query_rows(query))
        + '</section><section id="policy"><h2>Optional policy evidence</h2>'
        + _table("Finite diagnostic scope and findings", [payload["policy_evidence"]])
        + '</section><section id="work"><h2>Evaluation work</h2>'
        + _table("Trace evaluator counters (additional policy work is separate)", [payload["work"]])
        + _table("Accepted resource ceilings for this run", [payload["resource_ceilings"]])
        + '</section><section id="interpretation"><h2>Interpretation and unassessed conditions</h2>'
        f"<p>{escape(result.interpretation)}</p>"
        "<p>Asset ownership and interface placement are distinct declarations. Unmodeled paths "
        "remain unassessed. This report is confined to the declared finite model.</p>"
        '</section><section id="json"><h2>Complete trace JSON</h2>'
        "<details><summary>Machine-readable trace version 1</summary>"
        f"<pre>{escape(trace_json(result).decode('ascii'))}</pre></details></section></main>"
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta http-equiv="Content-Security-Policy" content="default-src &#39;none&#39;; '
        'style-src &#39;unsafe-inline&#39;; base-uri &#39;none&#39;; form-action &#39;none&#39;">'
        f"<title>OT-ArchGuard exact trace</title><style>{_STYLE}</style></head><body>"
        + body
        + "</body></html>\n"
    ).encode("utf-8")
