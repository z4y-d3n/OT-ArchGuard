"""Bounded, presentation-only static views of source-reproduced drift-v1 evidence.

The caller owns analytical verification. This module neither replays sources nor
creates new findings. Record buckets copy the version-1 summary vocabulary only.
"""

import hashlib
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any

from otarchguard.diagnostics import check_limit, fail
from otarchguard.evidence.attachments import canonical
from otarchguard.explorer_html import escape, identity_details, link, properties, table

RENDERER_VERSION = "1.4.0-historical-explorer.1"
# Leave space for the canonical report, verification receipt and completion manifest.
MAX_PAGES = 4090
MAX_PAGE_BYTES = 2 * 1024 * 1024
MAX_RENDERED_BYTES = 224 * 1024 * 1024
DOMAINS = {
    "communications": "Observed communications",
    "protocols": "Industrial protocol metadata",
    "architecture": "Declared architecture",
    "native": "Native model assessments",
    "interpretation": "Analytical interpretation",
    "coverage": "Coverage and uncertainty",
    "unassessed": "Other unassessed comparisons",
}
PROTOCOLS = {
    "modbus_tcp": "Modbus TCP",
    "profinet_dcp": "PROFINET DCP",
    "ethernet_ip": "EtherNet/IP and limited CIP",
    "s7comm": "Classic S7comm",
    "iec104": "IEC-104",
    "opcua_binary": "OPC UA Binary",
    "dnp3": "DNP3/TCP",
}
_UNCHANGED = {
    "OBSERVED_IN_BOTH",
    "REACHABILITY_UNCHANGED",
    "RECONCILIATION_ASSESSMENT_UNCHANGED",
}
_STATES = ("COMPARABLE", "PARTIALLY_COMPARABLE", "INDETERMINATE", "INCOMPARABLE")
_NOTES = {
    "communications": (
        "Direction follows packet headers. Relationships are finite-capture aggregates; "
        "they are not proven TCP sessions or inferred client/server roles. "
        "Reference-only observations do not prove blocking, absence or an outage."
    ),
    "protocols": (
        "Structural recognition, port hints, malformed, truncated and unsupported records "
        "retain their canonical status. Write-type function metadata does not prove "
        "successful command execution. Only retained header metadata is shown."
    ),
    "architecture": (
        "These are declarations in validated native models. Equal native IDs align "
        "declarations; changes do not establish a physical deployment change."
    ),
    "native": (
        "Reachability under the selected declared model applies to the exact query and "
        "port interval. It does not establish real firewall enforcement, a successful "
        "connection or application success. Retained source attachment and query/flow "
        "identities locate exact witnesses in the original workspace."
    ),
    "interpretation": (
        "Decoder, producer semantics and analytical input differences are interpretations, "
        "not independent evidence of operational network change."
    ),
    "coverage": (
        "Raw counts are not rates. Observed timestamp bounds do not establish continuous "
        "monitoring, synchronized clocks or the duration of missing coverage."
    ),
    "unassessed": (
        "An abstention means the selected evidence does not answer this question. "
        "Indeterminate evidence is neither success nor failure."
    ),
}

CSS = """*{box-sizing:border-box}html{background:#f2f5f7;color:#182c3b;
font:100%/1.55 system-ui,-apple-system,Segoe UI,sans-serif}body{margin:0}
header,nav,main,footer{max-width:96rem;margin:auto;padding:1rem 3%}
header{background:#fff;border-top:6px solid #154e61;border-bottom:1px solid #9aadb5}
.eyebrow{font-weight:700;color:#285968;letter-spacing:.04em;font-size:.85rem}
h1{font-size:2rem;line-height:1.2;margin:.5rem 0 1rem}h2{font-size:1.4rem;margin-top:2rem}
h3{font-size:1.12rem}a{color:#09527e;text-underline-offset:.18em}a:hover{color:#754000}
a:focus-visible,summary:focus-visible,[tabindex]:focus-visible{outline:3px solid #8c4300;
outline-offset:4px}nav{border-bottom:1px solid #9aadb5}nav ul{display:flex;flex-wrap:wrap;
gap:.7rem 1.4rem;list-style:none;padding:0;margin:.4rem 0}.skip{position:absolute;left:-10000px}
.skip:focus{position:static;display:block;padding:1rem;background:#fff}.notice,.legend{
padding:.8rem 1.1rem;border-left:5px solid #8d5b15;background:#fff4dd}
.legend{border:1px solid #9aadb5;background:#fff}.muted{color:#405966}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(12rem,1fr));gap:1rem;
list-style:none;padding:0}.cards li{padding:1rem;background:white;border:1px solid #9aadb5}
.metric{font-size:1.8rem;font-weight:750;display:block}.compare{display:grid;
grid-template-columns:repeat(auto-fit,minmax(min(100%,32rem),1fr));gap:1rem}
.compare>section{min-width:0;
padding:1rem;background:#fff;border:1px solid #9aadb5}.record{margin:1.5rem 0;padding:1rem;
border:1px solid #9aadb5;background:#fff;scroll-margin-top:1rem}.record>h2{margin-top:0}
.badge{display:inline-block;padding:.15rem .5rem;border:1px solid #536b77;
font-size:.85rem;font-weight:650;background:#edf3f5;margin:.15rem .3rem .15rem 0}
.properties{display:grid;grid-template-columns:fit-content(34%) minmax(0,1fr);
gap:.25rem .85rem;margin:.5rem 0}.properties>dt{font-weight:650;min-width:0}
.properties>dd{margin:0;min-width:0}.properties>dd>.properties{margin-top:0}
.retained-fields{display:block;margin:.5rem 0;min-width:0}
.retained-fields>dt{font-weight:650;margin-top:.75rem}
.retained-fields>dd{margin:0;min-width:0}
.retained-fields>dd>.retained-fields{margin:0;border-top:1px solid #c3ced3;
border-bottom:1px solid #c3ced3}
.retained-list{list-style:none;padding:0;margin:.5rem 0;min-width:0}
.retained-list>li+li{border-top:1px solid #c3ced3;margin-top:.5rem;padding-top:.5rem}
code{font-family:ui-monospace,Consolas,monospace;font-size:.9em}
dd,dt,td,th,p,li,h1,h2,h3,a,summary{overflow-wrap:break-word}
code,.properties a,.retained-fields a{overflow-wrap:anywhere;word-break:normal}
ul{padding-left:1.4rem}details{margin:.65rem 0}summary{cursor:pointer;font-weight:650}
.scroll{overflow:auto;max-width:100%;border:1px solid #9aadb5;background:white}
.finding-table,.pair-table{min-width:0;max-width:100%}
.finding-table table{table-layout:fixed;min-width:60rem}
.finding-table th:nth-child(1){width:14rem}.finding-table th:nth-child(2){width:16rem}
.finding-table th:nth-child(3){width:13rem}
.pair-table table{table-layout:fixed;min-width:62rem}.pair-table th:first-child{width:6rem}
.status-part{display:inline-block;overflow-wrap:normal;word-break:normal}
table{width:100%;border-collapse:collapse;min-width:34rem}caption{text-align:left;
padding:.8rem;font-weight:700}th,td{padding:.65rem;text-align:left;vertical-align:top;
border-bottom:1px solid #c3ced3}th{background:#e5edf1}.pagination{padding:.75rem 0}
.pagination p{margin:.25rem 0}.breadcrumbs{font-size:.9rem}.record .compare h3{margin-top:0}
svg{max-width:100%;height:auto;display:block;background:white;border:1px solid #9aadb5}
.diagram-scroll svg{width:100%;min-width:900px;max-width:none}
svg text{font:14px system-ui,sans-serif;fill:#182c3b}svg rect{fill:#edf3f5;stroke:#536b77}
.relationship{stroke:#154e61;stroke-width:3;fill:none}.reference-edge{stroke-dasharray:8 5}
.candidate-edge{stroke-dasharray:2 4}.common-edge{stroke-width:5}
footer{border-top:1px solid #9aadb5;font-size:.9rem}figure{margin:1rem 0}figcaption{padding:.5rem 0}
@media(max-width:700px){header,nav,main,footer{padding:1rem}h1{font-size:1.65rem}
.cards{grid-template-columns:minmax(0,1fr)}}
@media(max-width:480px){.properties{grid-template-columns:minmax(0,1fr);gap:.1rem}
.properties>dt{margin-top:.45rem}.record{padding:.75rem}}
@media print{html{background:white;color:black}nav,.skip{display:none}a{color:black}
.scroll{overflow:visible}table{min-width:0}.compare{display:block}.record{break-inside:avoid}
.finding-table table,.pair-table table{min-width:0}
.finding-table th:nth-child(1){width:22%}.finding-table th:nth-child(2){width:24%}
.finding-table th:nth-child(3){width:22%}.pair-table th:first-child{width:8%}
.diagram-scroll svg{min-width:0;width:100%;max-width:100%}}
"""


def _label(value: str) -> str:
    return value.replace("_", " ").strip().capitalize()


def _checked_tree(value: object) -> None:
    """Bound presentation work before constructing output, including hidden fields."""
    stack = [(value, 0)]
    nodes = 0
    while stack:
        item, depth = stack.pop()
        nodes += 1
        check_limit("historical_display_nodes", nodes, 2_000_000)
        check_limit("historical_display_depth", depth, 32)
        if isinstance(item, dict):
            for key, child in item.items():
                if type(key) is not str:
                    fail("HISTORICAL_DISPLAY", "$", "Display fields must have text names.")
                escape(key)
                stack.append((child, depth + 1))
        elif isinstance(item, list):
            stack.extend((child, depth + 1) for child in item)
        elif isinstance(item, str):
            escape(item)
        elif item is not None and type(item) not in {int, float, bool}:
            fail("HISTORICAL_DISPLAY", "$", "Unsupported display value.")


def _value(value: object, *, source_links: dict[str, str] | None = None) -> str:
    """Readable retained fields, never raw JSON or user-provided markup."""
    if value is None:
        return '<span class="muted">Not retained or not available on this side</span>'
    if type(value) is bool:
        return "Yes" if value else "No"
    if isinstance(value, dict):
        if not value:
            return '<span class="muted">No retained fields</span>'
        # Each nested value keeps its full parent width. Reapplying the two-column
        # summary property grid at every depth collapses native witness evidence.
        return (
            '<dl class="retained-fields">'
            + "".join(
                "<dt>"
                + escape(_label(str(k)))
                + "</dt><dd>"
                + _value(v, source_links=source_links)
                + "</dd>"
                for k, v in sorted(value.items())
            )
            + "</dl>"
        )
    if isinstance(value, list):
        if not value:
            return '<span class="muted">None retained</span>'
        return (
            '<ul class="retained-list" role="list">'
            + "".join("<li>" + _value(v, source_links=source_links) + "</li>" for v in value)
            + "</ul>"
        )
    if isinstance(value, str) and source_links and value in source_links:
        return link(source_links[value], value)
    return "<code>" + escape(value) + "</code>"


def _status(value: str) -> str:
    """Allow a line break at status separators, retaining the exact text/code."""
    parts = value.split("_")
    return "".join(
        '<span class="status-part">'
        + escape(part + ("_" if i < len(parts) - 1 else ""))
        + "</span>"
        for i, part in enumerate(parts)
    )


def _domain(finding: dict[str, Any]) -> str:
    category, subtype = finding["category"], finding["subtype"]
    direct = {
        "OBSERVED_COMMUNICATION_DIFFERENCE": "communications",
        "PROTOCOL_METADATA_DIFFERENCE": "protocols",
        "DECLARED_ARCHITECTURE_CHANGE": "architecture",
        "NATIVE_ASSESSMENT_DIFFERENCE": "native",
        "ANALYTICAL_INTERPRETATION_DIFFERENCE": "interpretation",
        "COVERAGE_DIFFERENCE": "coverage",
    }
    if category in direct:
        return direct[category]
    if subtype.startswith("NATIVE_") or subtype == "MODEL_UNAVAILABLE":
        return "native" if subtype.startswith("NATIVE_") else "architecture"
    if subtype.startswith("PROTOCOL_"):
        return "protocols"
    return "unassessed"


def _bucket(finding: dict[str, Any]) -> str:
    if finding["subtype"] in _UNCHANGED:
        return "unchanged"
    if finding["category"] == "INDETERMINATE_COMPARISON" or finding["subtype"] == (
        "UNASSESSED_OPAQUE_OBSERVATIONS"
    ):
        return "abstentions"
    return "differences"


@dataclass(frozen=True)
class _Record:
    finding: dict[str, Any]
    context: int | None
    identity: str
    domain: str


def _records(report: dict[str, Any]) -> list[_Record]:
    records: list[_Record] = []
    groups: list[tuple[int | None, list[dict[str, Any]]]] = [
        (i, pair["findings"]) for i, pair in enumerate(report["comparisons"], 1)
    ]
    groups += [(None, report["unaligned_findings"]), (None, report["architecture_findings"])]
    for group_index, (context, findings) in enumerate(groups):
        for position, finding in enumerate(findings):
            identity = (
                "f-" + hashlib.sha256(canonical([group_index, position, finding])).hexdigest()
            )
            records.append(_Record(finding, context, identity, _domain(finding)))
            check_limit("historical_display_findings", len(records), 20_000)
    return records


def _pages(prefix: str, count: int, page_size: int) -> list[str]:
    return [
        prefix + ("" if n == 0 else f"-{n + 1}") + ".html"
        for n in range(max(1, (count + page_size - 1) // page_size))
    ]


def _pagination(names: list[str], index: int, count: int, size: int) -> str:
    start, end = min(index * size + 1, count), min((index + 1) * size, count)
    choices = []
    if index:
        choices += [link(names[0], "First page"), link(names[index - 1], "Previous page")]
    if index + 1 < len(names):
        choices += [link(names[index + 1], "Next page"), link(names[-1], "Last page")]
    return (
        '<nav class="pagination" aria-label="Pagination"><p>'
        + (f"Page {index + 1} of {len(names)} · Records {start}–{end} of {count}")
        + "</p><p>"
        + " · ".join(choices)
        + "</p></nav>"
    )


def _document(title: str, body: str, drift_id: str) -> bytes:
    navigation = (
        ("index.html", "Overview"),
        ("scope.html", "Scope and comparability"),
        ("findings.html", "Finding indexes"),
        ("evidence.html", "Evidence and approval"),
        ("verification.html", "Verify this report"),
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta http-equiv="Content-Security-Policy" content="default-src &#39;none&#39;; '
        "style-src &#39;self&#39;; img-src &#39;none&#39;; script-src &#39;none&#39;; "
        "connect-src &#39;none&#39;; base-uri &#39;none&#39;; form-action &#39;none&#39;; "
        'object-src &#39;none&#39;">'
        '<link rel="stylesheet" href="style.css"><title>'
        + escape(title)
        + " · Historical Evidence Explorer</title></head><body>"
        '<a class="skip" href="#main">Skip to main content</a><header>'
        '<p class="eyebrow">OT-ArchGuard · OFFLINE HISTORICAL EVIDENCE</p><h1>'
        + escape(title)
        + "</h1>"
        + identity_details("Historical drift report", drift_id)
        + '</header><nav aria-label="Historical Explorer"><ul>'
        + "".join("<li>" + link(path, label) + "</li>" for path, label in navigation)
        + '</ul></nav><main id="main">'
        + body
        + '<aside class="legend" aria-label="Interpretation limits"><h2>Read these results '
        "within their limits</h2><p>Presentation is not authority. Differences describe "
        "selected finite evidence and declared models. No observation is not proof of "
        "absence. Model reachability is not deployed enforcement. Hashes establish "
        "integrity, not capture authenticity or reviewer identity.</p></aside></main>"
        "<footer><p><strong>Sensitive engineering evidence.</strong> Review internal "
        "addresses, device labels, zones, architecture relationships, protocol presence "
        "and reviewer rationales before sharing.</p><p>Approval status verified when this "
        "offline site was generated; it may have changed subsequently. Review decisions "
        "are local reviewer assertions. No server, JavaScript or network is required. "
        "Historical Explorer contract 1; renderer "
        + escape(RENDERER_VERSION)
        + ".</p></footer></body></html>\n"
    ).encode("utf-8")


class _Renderer:
    def __init__(self, report: dict[str, Any], verification: dict[str, Any], size: int) -> None:
        self.report, self.verification, self.size = report, verification, size
        self.output: dict[str, bytes] = {"style.css": CSS.encode("utf-8")}
        self.output_bytes = len(self.output["style.css"])
        self.page_count = 0
        self.records = _records(report)
        summary = report["summary"]
        buckets = Counter(_bucket(record.finding) for record in self.records)
        if (
            summary["findings"] != len(self.records)
            or summary["categories"] != dict(Counter(r.finding["category"] for r in self.records))
            or summary["difference_records"] != buckets["differences"]
            or summary["unchanged_support_records"] != buckets["unchanged"]
            or summary["abstentions"] != buckets["abstentions"]
        ):
            fail("HISTORICAL_DISPLAY_COUNTS", "$", "Retained record counts disagree with report.")
        self.domains: dict[str, list[_Record]] = {name: [] for name in DOMAINS}
        self.pair_records: dict[int, list[_Record]] = defaultdict(list)
        self.relationship_records: dict[bytes, list[_Record]] = defaultdict(list)
        self.relationship_keys: dict[str, bytes] = {}
        self.locations: dict[str, str] = {}
        for record in self.records:
            self.domains[record.domain].append(record)
            if record.context is not None:
                self.pair_records[record.context].append(record)
                key = record.finding["key"]
                if (
                    isinstance(key, dict)
                    and key.get("source_ip") is not None
                    and key.get("destination_ip") is not None
                ):
                    encoded = canonical(
                        [
                            record.context,
                            {
                                name: key.get(name)
                                for name in (
                                    "source_ip",
                                    "destination_ip",
                                    "source_port",
                                    "destination_port",
                                    "vlans",
                                )
                            },
                        ]
                    )
                    self.relationship_records[encoded].append(record)
                    self.relationship_keys[record.identity] = encoded
        for domain, records in self.domains.items():
            names = _pages(domain, len(records), size)
            for index, record in enumerate(records):
                self.locations[record.identity] = names[index // size] + "#" + record.identity
        self.sources: dict[str, dict[str, Any]] = {}
        self.source_roles: dict[str, list[str]] = defaultdict(list)
        for role in ("reference", "candidate"):
            for source in report["inputs"][role + "_sources"]:
                aid = source["analysis_id"]
                self.sources[aid] = source
                self.source_roles[aid].append(role)
        self.source_links = {
            aid: "source-" + hashlib.sha256(aid.encode("ascii")).hexdigest() + ".html"
            for aid in self.sources
        }
        self.source_records: dict[str, list[_Record]] = defaultdict(list)
        for record in self.records:
            referenced: set[str] = set()
            stack: list[object] = [record.finding["reference"], record.finding["candidate"]]
            while stack:
                item = stack.pop()
                if isinstance(item, dict):
                    aid = item.get("analysis_id")
                    if isinstance(aid, str) and aid in self.sources:
                        referenced.add(aid)
                    stack.extend(item.values())
                elif isinstance(item, list):
                    stack.extend(item)
            for aid in sorted(referenced):
                self.source_records[aid].append(record)

    def put(self, name: str, title: str, body: str) -> None:
        if name in self.output:
            fail("HISTORICAL_DISPLAY", "$", "Duplicate generated page identity.")
        self.page_count += 1
        check_limit("historical_render_pages", self.page_count, MAX_PAGES)
        data = _document(title, body, self.report["drift_id"])
        check_limit("historical_render_page_bytes", len(data), MAX_PAGE_BYTES)
        self.output_bytes += len(data)
        check_limit("historical_render_total_bytes", self.output_bytes, MAX_RENDERED_BYTES)
        self.output[name] = data

    def row(self, record: _Record) -> tuple[str, ...]:
        f = record.finding
        return (
            link(self.locations[record.identity], _label(f["subtype"])),
            escape(_label(f["category"])),
            _status(f["comparability"]),
            escape(f["explanation"]),
        )

    def record_table(self, title: str, records: list[_Record]) -> str:
        return (
            '<div class="finding-table">'
            + table(
                title,
                ("Finding and evidence", "Canonical category", "Comparability", "Meaning"),
                [self.row(record) for record in records],
            )
            + "</div>"
        )

    def overview(self) -> None:
        inputs, summary = self.report["inputs"], self.report["summary"]
        counts = (
            ("Differences", summary["difference_records"], "differences.html"),
            ("Unchanged support", summary["unchanged_support_records"], "unchanged.html"),
            ("Abstentions", summary["abstentions"], "abstentions.html"),
        )
        body = (
            '<p class="notice">'
            + escape(summary["interpretation"])
            + (" Counts are canonical report records, not incidents, risk scores or devices.</p>")
        )
        body += (
            '<ul class="cards">'
            + "".join(
                '<li><span class="metric">' + str(count) + "</span>" + link(path, title) + "</li>"
                for title, count, path in counts
            )
            + "</ul><h2>Compared evidence and authority</h2>"
        )
        body += properties(
            [
                ("Declared environment", escape(inputs["baseline"]["scope"]["environment"])),
                ("Comparison mode", escape(self.report["options"]["mode"])),
                (
                    "Reference baseline",
                    link("evidence.html#baseline", inputs["baseline"]["baseline_id"]),
                ),
                (
                    "Recorded approval",
                    link("evidence.html#approval", inputs["approval"]["review_id"]),
                ),
                ("Recorded approval state", escape(self.verification["recorded_baseline_status"])),
                ("State at site generation", escape(self.verification["current_baseline_status"])),
                ("Source-dependent reproduction", escape(self.verification["status"])),
                ("Distinct physical collections", str(summary["distinct_physical_collections"])),
                (
                    "Selected candidate revisions",
                    "<ul>"
                    + "".join(
                        "<li>"
                        + link(self.source_links[source["analysis_id"]], source["analysis_id"])
                        + "</li>"
                        for source in inputs["candidate_sources"]
                    )
                    + "</ul>"
                    if inputs["candidate_sources"]
                    else "No candidate capture revisions selected",
                ),
            ]
        )
        body += "<h2>Comparability by selected pair</h2><p>Each status is copied from the "
        body += "comparison engine. An overall indeterminate result can coexist with "
        body += "comparable metadata dimensions.</p>" + self.pair_table()
        body += "<h2>Investigate a domain</h2>" + table(
            "Complete domain navigation",
            ("Domain", "Canonical records", "Interpretation"),
            [
                (
                    link(domain + ".html", title),
                    str(len(self.domains[domain])),
                    escape(_NOTES[domain]),
                )
                for domain, title in DOMAINS.items()
            ],
        )
        body += "<h2>Major limitations</h2>" + _value(self.report["limitations"])
        self.put("index.html", "Historical comparison overview", body)

    def pair_table(self) -> str:
        return (
            '<div class="pair-table">'
            + table(
                "Selected comparison pairs",
                ("Pair", "Overall", "Communications", "Protocol metadata", "Asset continuity"),
                [
                    (
                        link(f"pair-{index}.html", f"Pair {index}"),
                        _status(p["comparability"]["overall"]),
                        _status(p["comparability"]["communication_metadata"]),
                        _status(p["comparability"]["protocol_metadata"]),
                        _status(p["comparability"]["asset_continuity"]),
                    )
                    for index, p in enumerate(self.report["comparisons"], 1)
                ],
            )
            + "</div>"
        )

    def scope(self) -> None:
        body = "<h2>Declared reference scope</h2>" + _value(
            self.report["inputs"]["baseline"]["scope"]
        )
        body += "<h2>Explicit alignment</h2><p>Matching labels and reviewed alignment assertions "
        body += "do not authenticate sensors, physical devices or clocks.</p>" + self.pair_table()
        body += "<h2>Unaligned evidence</h2><p>Every unaligned collection remains discoverable "
        body += "through " + link("abstentions.html", "the abstention index") + ".</p>"
        self.put("scope.html", "Comparison scope and comparability", body)
        contexts = self.report["options"]["context"]["pairs"]
        for index, pair in enumerate(self.report["comparisons"], 1):
            assessment = pair["comparability"]
            context = contexts[index - 1]
            body = '<p class="breadcrumbs">' + link("scope.html", "Back to all pairs") + "</p>"
            body += "<h2>Exact evidence selection</h2>" + _value(
                {k: v for k, v in pair.items() if k not in {"comparability", "findings"}},
                source_links=self.source_links,
            )
            body += "<h2>Reviewed alignment and candidate scope</h2>" + _value(
                context, source_links=self.source_links
            )
            body += "<h2>Comparator assessment</h2>" + _value(
                {k: v for k, v in assessment.items() if k != "dimensions"}
            )
            for dim_index, dimension in enumerate(assessment["dimensions"], 1):
                body += f'<section id="dimension-{dim_index}"><h2>'
                body += (
                    escape(_label(dimension["dimension"]))
                    + "</h2>"
                    + _value(
                        {k: v for k, v in dimension.items() if k != "dimension"},
                        source_links=self.source_links,
                    )
                    + "</section>"
                )
            names = _pages(f"pair-{index}-findings", len(pair["findings"]), self.size)
            body += "<h2>Findings in this context</h2><p>" + link(
                names[0], "Browse all pair findings"
            )
            body += f" · {len(pair['findings'])} canonical records.</p>"
            self.put(f"pair-{index}.html", f"Comparison pair {index}", body)
            self.index_pages(
                f"pair-{index}-findings",
                f"Pair {index} findings",
                self.pair_records[index],
            )

    def index_pages(self, prefix: str, title: str, records: list[_Record], intro: str = "") -> None:
        names = _pages(prefix, len(records), self.size)
        for index, name in enumerate(names):
            page = records[index * self.size : (index + 1) * self.size]
            pager = _pagination(names, index, len(records), self.size)
            body = intro + pager + self.record_table(title, page)
            if not records:
                body += "<p>No records retained in this view. No supported difference does "
                body += "not establish operational safety or complete visibility.</p>"
            self.put(name, title, body + pager)

    def indexes(self) -> None:
        categories: dict[str, list[_Record]] = defaultdict(list)
        for record in self.records:
            categories[record.finding["category"]].append(record)
        body = "<h2>Canonical categories</h2>"
        rows = []
        for index, (category, records) in enumerate(sorted(categories.items()), 1):
            prefix = f"category-{index}"
            rows.append((link(prefix + ".html", _label(category)), str(len(records))))
            self.index_pages(prefix, _label(category), records)
        body += table("Findings by canonical category", ("Category", "Records"), rows)
        body += "<h2>Supported outcome groups</h2><p>Groups preserve the drift-v1 summary "
        body += "rules. A record with an indeterminate comparator state may also represent "
        body += "an analytical interpretation difference; its category remains unchanged.</p>"
        for bucket, title in (
            ("differences", "Differences"),
            ("unchanged", "Unchanged support"),
            ("abstentions", "Abstentions"),
        ):
            records = [r for r in self.records if _bucket(r.finding) == bucket]
            body += "<p>" + link(bucket + ".html", title) + f" · {len(records)} records.</p>"
            self.index_pages(bucket, title, records)
        body += "<h2>Comparator states</h2>"
        for index, state in enumerate(_STATES, 1):
            records = [r for r in self.records if r.finding["comparability"] == state]
            body += "<p>" + link(f"state-{index}.html", state) + f" · {len(records)} records.</p>"
            self.index_pages(f"state-{index}", "Comparator state: " + state, records)
        self.put("findings.html", "Findings and outcome indexes", body)

    def detail(self, record: _Record) -> str:
        f = record.finding
        body = '<section class="record" id="' + record.identity + '"><h2>'
        body += escape(_label(f["subtype"])) + "</h2>"
        body += '<p><span class="badge">' + escape(f["category"]) + '</span><span class="badge">'
        body += escape(f["comparability"]) + "</span></p><p>" + escape(f["explanation"]) + "</p>"
        body += '<p class="breadcrumbs">' + link(record.domain + ".html", "Back to domain")
        if record.context is not None:
            body += " · " + link(f"pair-{record.context}.html", f"Pair {record.context} context")
        else:
            body += " · " + link("evidence.html", "Baseline and model context")
        body += " · " + link("findings.html", "All finding indexes") + "</p>"
        body += "<h3>Exact compared key</h3>" + _value(f["key"])
        body += '<div class="compare"><section><h3>Reference evidence</h3>'
        body += _value(f["reference"], source_links=self.source_links)
        body += "</section><section><h3>Candidate evidence</h3>"
        body += _value(f["candidate"], source_links=self.source_links) + "</section></div>"
        body += "<h3>Limitations for this finding</h3>" + _value(f["limitations"])
        relationship = self.relationship_keys.get(record.identity)
        if relationship is not None:
            related = self.relationship_records[relationship]
            count = len(related) - 1
            if count:
                preview = [other for other in related[:9] if other.identity != record.identity][:8]
                body += "<h3>Related retained records</h3><p>Matching IP address, port and VLAN "
                body += "metadata in this selected pair; this does not establish physical "
                body += (
                    f"device continuity. Preview of {min(count, 8)} of {count} related records.</p>"
                )
                body += (
                    "<ul>"
                    + "".join(
                        "<li>"
                        + link(self.locations[other.identity], _label(other.finding["subtype"]))
                        + " · "
                        + escape(_label(other.finding["category"]))
                        + "</li>"
                        for other in preview
                    )
                    + "</ul>"
                )
                if count > 8:
                    body += (
                        "<p>"
                        + link(
                            f"pair-{record.context}-findings.html",
                            "Browse the complete pair finding index",
                        )
                        + ". The related-record preview is incomplete.</p>"
                    )
        body += "<details><summary>Unsupported interpretations</summary>"
        body += _value(f["unsupported_interpretations"]) + "</details>"
        body += identity_details("Presentation record identity", record.identity)
        return body + "</section>"

    def diagram(self, records: list[_Record]) -> str:
        if not records:
            return "<p>No observed relationships retained; no diagram is drawn.</p>"
        if len(records) > 12 or any(
            not isinstance(r.finding["key"], dict)
            or r.finding["key"].get("source_ip") is None
            or r.finding["key"].get("destination_ip") is None
            for r in records
        ):
            return (
                '<p class="notice">Communication diagram omitted: more than 12 '
                "relationships or opaque endpoints. Complete paginated records remain below.</p>"
            )
        height = 60 + len(records) * 86
        body = (
            '<figure><div class="scroll diagram-scroll" tabindex="0" role="region" '
            'aria-label="Observed communication diagram; scroll horizontally for complete '
            'relationships"><svg viewBox="0 0 900 ' + str(height)
        )
        body += '" role="img" aria-labelledby="communication-title communication-desc">'
        body += '<title id="communication-title">Observed packet-header directions</title>'
        body += '<desc id="communication-desc">Each independent lane links to its exact '
        body += "retained finding. Solid means common, dashed reference only, dotted candidate "
        body += "only. No intermediate network hops or client/server roles are inferred.</desc>"
        body += '<defs><marker id="direction-arrow" viewBox="0 0 10 10" refX="9" refY="5" '
        body += 'markerWidth="6" markerHeight="6" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" '
        body += 'fill="#154e61"></path></marker></defs>'
        for index, record in enumerate(records):
            f, y = record.finding, 50 + index * 86
            key, subtype = f["key"], f["subtype"]
            state, category = (
                ("Reference only", "reference-edge")
                if subtype == "REFERENCE_ONLY_OBSERVATION"
                else ("Candidate only", "candidate-edge")
                if subtype == "CANDIDATE_ONLY_OBSERVATION"
                else ("Common relationship", "common-edge")
            )
            body += '<a href="' + self.locations[record.identity] + '">'
            body += f'<rect x="15" y="{y - 21}" width="280" height="50" rx="4"></rect>'
            body += f'<rect x="605" y="{y - 21}" width="280" height="50" rx="4"></rect>'
            body += f'<text x="27" y="{y}">' + escape(key["source_ip"]) + "</text>"
            body += f'<text x="617" y="{y}">' + escape(key["destination_ip"]) + "</text>"
            body += f'<path class="relationship {category}" d="M 305 {y} L 595 {y}" '
            body += 'marker-end="url(#direction-arrow)"></path>'
            body += f'<text x="320" y="{y - 12}">' + escape(state) + "</text>"
            body += (
                f'<text x="320" y="{y + 24}">'
                + escape(f"{key['transport']} {key['source_port']} → {key['destination_port']}")
                + "</text></a>"
            )
        return (
            body + "</svg></div><figcaption>On narrow screens, focus the diagram region and "
            "scroll horizontally to keep labels readable. Selected finite evidence; follow each "
            "relationship "
            "for exact source identifiers, counts, VLAN and ARP context. Diagram is an aid; "
            "complete retained evidence follows.</figcaption></figure>"
        )

    def domain_pages(self) -> None:
        for domain, title in DOMAINS.items():
            records = self.domains[domain]
            names = _pages(domain, len(records), self.size)
            for index, name in enumerate(names):
                body = '<p class="notice">' + escape(_NOTES[domain]) + "</p>"
                if domain == "protocols" and index == 0:
                    body += "<h2>Supported protocol families</h2><p>Absence of a difference "
                    body += "record does not establish protocol absence. Decoder availability "
                    body += (
                        "and visibility are detailed in "
                        + link("scope.html", "comparability")
                        + ".</p>"
                    )
                    body += table(
                        "Seven supported metadata families",
                        ("Family", "Retained differences"),
                        [
                            (
                                link("protocol-" + family.replace("_", "-") + ".html", label),
                                str(
                                    sum(
                                        isinstance(r.finding["key"], dict)
                                        and r.finding["key"].get("protocol") == family
                                        for r in records
                                    )
                                ),
                            )
                            for family, label in PROTOCOLS.items()
                        ],
                    )
                if domain == "communications" and index == 0:
                    body += self.diagram(records)
                pager = _pagination(names, index, len(records), self.size)
                page = records[index * self.size : (index + 1) * self.size]
                body += pager + self.record_table("Findings on this page", page)
                if not records:
                    body += "<p>No records retained in this domain. No supported difference "
                    body += "does not establish operational safety or complete visibility.</p>"
                body += "".join(self.detail(record) for record in page) + pager
                self.put(name, title, body)
        for family, label in PROTOCOLS.items():
            records = [
                r
                for r in self.domains["protocols"]
                if isinstance(r.finding["key"], dict) and r.finding["key"].get("protocol") == family
            ]
            self.index_pages(
                "protocol-" + family.replace("_", "-"),
                label + " metadata",
                records,
                "<p>"
                + link("protocols.html", "Back to all protocol metadata")
                + ". Retained canonical differences only; missing records do not prove "
                "protocol absence. Decoder compatibility is assessed separately.</p>",
            )

    def evidence(self) -> None:
        inputs = self.report["inputs"]
        body = '<section id="baseline"><h2>Exact historical reference</h2>'
        body += _value(inputs["baseline"], source_links=self.source_links) + "</section>"
        body += '<section id="approval"><h2>Recorded introducing approval</h2><p>Local '
        body += "reviewer assertion; reviewer identity and authority are unauthenticated.</p>"
        body += _value(inputs["approval"]) + "</section><h2>State verified at generation</h2>"
        body += _value(self.verification) + "<h2>Historical review frontier</h2>"
        body += _value(inputs["review_frontier"])
        body += "<h2>Selected model attachments</h2>" + _value(inputs["selected_models"])
        body += "<h2>Source evidence index</h2>" + table(
            "Selected analytical revisions and physical evidence",
            ("Role", "Exact source and context", "Related findings"),
            [
                (
                    escape(", ".join(self.source_roles[aid])),
                    link(self.source_links[aid], aid),
                    str(len(self.source_records[aid])),
                )
                for aid in sorted(self.sources)
            ],
        )
        body += "<p>Physical capture SHA-256, snapshot, observation and attachment identities "
        body += "remain distinct. Exact packet, flow, record-offset and retained query references "
        body += "appear in each linked finding. Original captures and arbitrary source documents "
        body += "are not copied into this site.</p>"
        self.put("evidence.html", "Evidence and approval history", body)
        for aid, source in sorted(self.sources.items()):
            prefix = self.source_links[aid][:-5]
            records = self.source_records[aid]
            names = _pages(prefix, len(records), self.size)
            for index, name in enumerate(names):
                pager = _pagination(names, index, len(records), self.size)
                body = (
                    '<p class="breadcrumbs">'
                    + link("evidence.html", "Back to evidence index")
                    + "</p>"
                )
                body += "<h2>Exact retained source identities</h2>" + _value(source)
                body += "<p>Selected as " + escape(", ".join(self.source_roles[aid])) + ".</p>"
                body += (
                    "<h2>Findings with this source</h2>"
                    + pager
                    + self.record_table(
                        "Related findings and retained source references",
                        records[index * self.size : (index + 1) * self.size],
                    )
                    + pager
                )
                self.put(name, "Analytical revision and supporting evidence", body)

    def verification_page(self) -> None:
        body = "<h2>Two different checks</h2><h3>Portable bundle integrity</h3><p>The "
        body += "manifest binds emitted files and their hashes. A portable check verifies "
        body += "the inventory, file bytes and local link/fragment structure. Integrity alone "
        body += "does not establish analytical reproduction or authenticate sources.</p>"
        body += "<p><code>otarchguard evidence drift explore-verify OUTPUT_DIRECTORY</code></p>"
        body += "<h3>Source-dependent analytical reproduction</h3><p>Supply the original "
        body += "workspace to replay the canonical drift-v1 report and obtain a fresh current "
        body += "approval state. The saved site remains a historical presentation snapshot; "
        body += "verification does not rewrite it.</p><p><code>otarchguard evidence drift "
        body += "explore-verify OUTPUT_DIRECTORY --workspace WORKSPACE</code></p>"
        body += "<h2>Canonical report identity</h2>" + properties(
            [
                ("Drift identity", escape(self.report["drift_id"])),
                ("Drift version", str(self.report["drift_version"])),
                ("Drift engine", escape(self.report["engine_version"])),
                ("Comparability policy", str(self.report["comparability_policy_version"])),
                (
                    "Historical workspace manifest SHA-256",
                    escape(self.report["inputs"]["workspace_manifest_sha256"]),
                ),
                ("Presentation renderer", escape(RENDERER_VERSION)),
                ("Rows per static page", str(self.size)),
            ]
        )
        body += (
            "<h2>Analytical reproduction method</h2><p>"
            + escape(self.report["reproduction"])
            + "</p>"
        )
        body += "<details><summary>Exact comparison implementation identities</summary>"
        body += _value(self.report["implementation_sha256"]) + "</details>"
        body += "<p>The manifest records the exact source report byte digest and renderer "
        body += "identity. Local paths and generation clock time do not form presentation "
        body += "identity. Approval may be revoked or superseded after generation; a static "
        body += "site cannot update that state automatically.</p>"
        self.put("verification.html", "Verification and trust boundaries", body)

    def run(self) -> dict[str, bytes]:
        self.overview()
        self.scope()
        self.indexes()
        self.domain_pages()
        self.evidence()
        self.verification_page()
        return self.output


def render(
    report: dict[str, Any], verification: dict[str, Any], *, page_size: int = 50
) -> dict[str, bytes]:
    """Render one operation-owned source-reproduced report without reading or writing files.

    Resource ceilings are display-only and never narrow canonical analytical data.
    Over-budget data fails; no finding is silently dropped.
    """
    if type(page_size) is not int or not 5 <= page_size <= 200:
        fail("HISTORICAL_OPTIONS", "$", "Rows per page must be an integer from 5 to 200.")
    _checked_tree(report)
    _checked_tree(verification)
    try:
        return _Renderer(report, verification, page_size).run()
    except (KeyError, TypeError, ValueError, AttributeError, IndexError, RecursionError):
        fail("HISTORICAL_DISPLAY", "$", "Malformed or unsupported historical display input.")
