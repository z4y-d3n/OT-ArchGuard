"""Bounded, deterministic, offline presentation of independent capture evidence."""

import hashlib
import html
import json
import os
import re
import tempfile
from collections.abc import Callable
from fractions import Fraction
from pathlib import Path, PureWindowsPath
from typing import Any

from otarchguard.capture.contract import CAPTURE_LIMITS, CaptureLimits
from otarchguard.capture.display import bullet_list, identity, render_value, timestamp_html
from otarchguard.capture.views import (
    capture_metadata,
    coverage_view,
    interpretation,
    overview_summary,
    protocols_view,
)
from otarchguard.diagnostics import check_limit, fail
from otarchguard.explorer_html import (
    COMPACT_CSS,
    CSS,
    audit_site,
    compact_value,
    escape,
    link,
    properties,
    table,
)
from otarchguard.ingestion.project import _no_links
from otarchguard.ingestion.workflow import serialize, write_new_file

NOTICE = (
    "Sensitive network metadata: review before sharing. Observed traffic is evidence, "
    "not authorization. Missing traffic does not establish blocking. No application success, "
    "physical topology, intrusion or compliance conclusion is established."
)
NAV = (
    ("index.html", "Overview"),
    ("hosts.html", "Observed addresses"),
    ("conversations.html", "Conversations"),
    ("protocols.html", "Protocols"),
    ("findings.html", "Findings / comparison"),
    ("coverage.html", "Coverage and limits"),
)
SECONDARY_NAV = (
    ("groups.html", "Bidirectional groups"),
    ("associations.html", "Owner associations"),
    ("evidence.html", "Evidence index"),
    ("address-links.html", "Address communication links"),
    ("not-observed.html", "Services not observed"),
)
CAPTURE_CSS = (
    CSS
    + """
nav a[aria-current=page]{font-weight:750;border-bottom:3px solid #375b75;
text-decoration-thickness:.18em}.secondary-nav{font-size:.95rem}
.metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(10rem,1fr));
gap:.6rem}.metrics>div{padding:.75rem;background:white;border:1px solid #657b8b}
.metrics dt{font-weight:600}.metrics dd{font-size:1.4rem;margin:0}
td details{max-width:38rem}section:target,tr:target{outline:3px solid #854700;
outline-offset:-3px}section.evidence-record{border-top:2px solid #657b8b;padding-top:1rem}
.related-list{margin:.25rem 0;padding-left:1.25rem}.secondary-nav p{margin:.25rem 0}
"""
)

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


def _classification(code: str) -> str:
    return CLASSIFICATION_LABELS.get(code, code)


def _packet_count(count: int) -> str:
    return f"{count} packet" + ("" if count == 1 else "s")


def _endpoint(flow: dict[str, Any], side: str) -> str:
    arp = flow.get("arp")
    value = flow[f"{side}_ip"]
    if arp:
        return ("Sender IP: " if side == "source" else "Target IP (reference): ") + str(value)
    return str(value) if value is not None else "Unavailable"


def fresh_destination(path: Path) -> None:
    """No-clobber local destinations; reject platform device names and linked parents."""
    if str(path).startswith(("\\\\", "//")) or PureWindowsPath(path).drive.startswith("\\\\"):
        fail("CAPTURE_PATH", "$", "Only local filesystem paths are supported.")
    _no_links(path)
    for part in path.absolute().parts[1:]:
        if (
            any(c in part for c in ":*?<>|\x00")
            or part.endswith((".", " "))
            or any(ord(c) < 32 for c in part)
            or re.fullmatch(r"(?i)(con|prn|aux|nul|com[0-9]|lpt[0-9])(?:\..*)?", part)
        ):
            fail("CAPTURE_PATH", "$", "Use a portable local output path.")
    if path.exists() or path.is_symlink():
        fail("CAPTURE_OUTPUT", "$", "Output already exists; choose a fresh destination.")
    if not path.parent.is_dir():
        fail("CAPTURE_OUTPUT", "$", "Output parent must be an existing local directory.")


def write_mapping(path: Path, mapping: dict[str, Any], limits: CaptureLimits) -> None:
    fresh_destination(path)
    data = serialize(mapping)
    check_limit("capture_mapping_bytes", len(data), min(limits.output_bytes, 8 * 1024 * 1024))
    write_new_file(path, data)


def _document(title: str, body: str, capture_hash: str, filename: str = "index.html") -> bytes:
    current = re.sub(r"-\d+\.html$", ".html", filename)
    if filename.startswith(("evidence-", "evidenceindex-")):
        current = "evidence.html"

    def navigation(items: tuple[tuple[str, str], ...]) -> str:
        return (
            "<ul>"
            + "".join(
                '<li><a href="'
                + path
                + '"'
                + (' aria-current="page"' if path == current else "")
                + ">"
                + escape(label)
                + "</a></li>"
                for path, label in items
            )
            + "</ul>"
        )

    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta http-equiv="Content-Security-Policy" content="default-src &#39;none&#39;; '
        "style-src &#39;self&#39;; script-src &#39;none&#39;; img-src &#39;none&#39;; "
        "connect-src &#39;none&#39;; base-uri &#39;none&#39;; form-action &#39;none&#39;; "
        'object-src &#39;none&#39;">'
        '<link rel="stylesheet" href="assets.css"><title>'
        + escape(title)
        + ' · PCAP Evidence Studio</title></head><body><a class="skip" href="#main">'
        "Skip to main content</a><header><p>OT-ArchGuard · PCAP Evidence Studio</p><h1>"
        + escape(title)
        + '</h1><p class="notice">'
        + escape(NOTICE)
        + "</p>"
        + identity("Capture SHA-256", capture_hash)
        + '</header><nav aria-label="Main evidence views">'
        + navigation(NAV)
        + '</nav><nav class="secondary-nav" aria-label="Related evidence views">'
        + navigation(SECONDARY_NAV)
        + '</nav><main id="main">'
        + body
        + "</main><footer><p>Capture site contract 1. No original capture or payload copied. "
        "No JavaScript, server or network resources required. Hashes bind bytes and decisions; "
        "they do not authenticate reviewer identity. No formal accessibility certification "
        "is claimed.</p></footer></body></html>\n"
    ).encode("utf-8")


def _json(value: object) -> str:
    # Bound/check individual source strings; page and output budgets bound the
    # serialized aggregate. Applying the scalar limit to an entire witness would
    # reject otherwise valid reports. Reuse the existing path/bidi minimization.
    def display(item: object) -> object:
        if isinstance(item, str):
            return html.unescape(escape(item))
        if isinstance(item, dict):
            return {str(k): display(v) for k, v in item.items()}
        if isinstance(item, (list, tuple)):
            return [display(v) for v in item]
        return item

    return html.escape(json.dumps(display(value), sort_keys=True, ensure_ascii=True), quote=True)


def _properties(title: str, value: object) -> str:
    return "<h2>" + escape(title) + "</h2><pre>" + _json(value) + "</pre>"


def _evidence_target(index: int, flow_id: str, rows_per_page: int) -> str:
    return f"evidence-{index // rows_per_page + 1}.html#flow-{flow_id}"


def _diagram(
    flows: list[dict[str, Any]], comparison: dict[str, Any] | None, rows_per_page: int = 100
) -> str:
    ips = sorted({f[k] for f in flows for k in ("source_ip", "destination_ip") if f[k]})
    if len(ips) > 16 or len(flows) > 24:
        return (
            "<p>Diagram omitted: more than 16 addresses or 24 directed aggregates. "
            "The complete paginated tables and JSON retain every aggregate.</p>"
        )
    if not ips:
        return "<p>No decodable IP-address relationships to diagram.</p>"
    lines: list[str] = []
    findings = {f["flow_id"]: f for f in comparison["findings"]} if comparison else {}
    for i, flow in enumerate(flows):
        source, target = flow["source_ip"], flow["destination_ip"]
        if not source or not target:
            continue
        # Each aggregate owns one lane. Repeated/reverse/self flows cannot share
        # arrow paths, and visual position never implies a physical topology.
        y = 100 + len(lines) * 150
        finding = findings.get(flow["id"], {})
        classification = finding.get("classification", "Not compared")
        arp = flow.get("arp")
        transport = "ARP " + arp["operation"] if arp else flow["transport"]
        ports = (
            f"{flow['source_port']} → {flow['destination_port']}"
            if flow["source_port"] is not None and flow["destination_port"] is not None
            else "Ports unavailable"
        )
        evidence = _evidence_target(i, flow["id"], rows_per_page)
        if arp:
            lines.append(
                f'<g><a href="{evidence}"><text x="24" y="{y}">'
                + escape(
                    f"Aggregate {i + 1:02d} · {_packet_count(flow['packets'])} · Evidence details"
                )
                + f'</text></a><rect x="24" y="{y + 12}" width="1048" height="80" '
                'fill="#eef4f8" stroke="#657b8b"/>'
                + f'<text x="36" y="{y + 33}">'
                + escape(f"{transport} · Sender IP: {source} · Target IP: {target}")
                + f'</text><text x="36" y="{y + 55}">'
                + escape(
                    "Ethernet destination: "
                    + arp["ethernet_delivery"].capitalize()
                    + " · "
                    + arp["ethernet_destination_mac"]
                )
                + f'</text><text x="36" y="{y + 77}">'
                "Target is a protocol reference; no target presence, response or IP ownership "
                "is established.</text>"
                + f'<text x="24" y="{y + 112}">Comparison: '
                + escape(_classification(classification))
                + f'</text><text x="24" y="{y + 132}">Code: '
                + escape(classification)
                + "</text></g>"
            )
            continue
        lines.append(
            f'<g><a href="{evidence}"><text x="24" y="{y}">'
            + escape(f"Aggregate {i + 1:02d} · {_packet_count(flow['packets'])} · Evidence details")
            + f'</text></a><rect x="24" y="{y + 12}" width="332" height="54" '
            'fill="#eef4f8" stroke="#657b8b"/>'
            + f'<text x="36" y="{y + 32}">Observed source</text>'
            + f'<text x="36" y="{y + 54}">{escape(source)}</text>'
            + f'<path class="diagram-line documentary" d="M 372 {y + 48} H 724" '
            'marker-end="url(#observed-arrow)"/>'
            + f'<text x="548" y="{y + 26}" text-anchor="middle">'
            + escape(f"{transport} · {ports}")
            + f'</text><rect x="740" y="{y + 12}" width="332" height="54" '
            'fill="#eef4f8" stroke="#657b8b"/>'
            + f'<text x="752" y="{y + 32}">Observed destination</text>'
            + f'<text x="752" y="{y + 54}">{escape(target)}</text>'
            + f'<text x="24" y="{y + 100}">Comparison: '
            + escape(_classification(classification))
            + f'</text><text x="24" y="{y + 122}">Code: '
            + escape(classification)
            + "</text></g>"
        )
    return (
        "<figure><figcaption>Observed directed aggregates · dashed arrows. "
        "IP lanes show packet direction, transport and decoded ports; ARP panels separately "
        "show sender/target protocol fields and Ethernet delivery. An ARP target is not an "
        "observed destination device. Neither layout infers "
        "the initiator. Select Evidence details for packet references, owner decisions and "
        "the original native model query. "
        "Arrow multiplicity is neither session count nor physical connectivity. "
        "MODEL_REACHABLE / MODEL_UNREACHABLE refer only to a separately evaluated declared "
        "initiation, never deployed authorization or application success. Owner association "
        "is reviewed evidence, not a discovered physical link. All aggregates, including "
        "those without IP endpoints, remain in the tables.</figcaption>"
        '<div class="scroll" tabindex="0" '
        'role="region" aria-label="Observed communication diagram"><svg '
        f'xmlns="http://www.w3.org/2000/svg" width="1100" height="{len(lines) * 150 + 120}" '
        'viewBox="0 0 1100 ' + str(len(lines) * 150 + 120) + '" '
        'role="group" aria-labelledby="diagram-title diagram-description" font-size="13">'
        '<title id="diagram-title">Observed communication, not authorization</title>'
        '<desc id="diagram-description">Independent IP direction lanes and ARP field panels. '
        "Each evidence link opens the complete aggregate and comparison.</desc>"
        '<text x="24" y="30" font-size="18">Observed communication, not authorization</text>'
        '<text x="24" y="57">Dashed arrow = observed packet direction · '
        "Comparison text = separate declared-model assessment</text>"
        '<defs><marker id="observed-arrow" '
        'viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" '
        'orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#505c66"/>'
        "</marker></defs>" + "".join(lines) + "</svg></div></figure>"
    )


def _anchor(kind: str, value: str) -> str:
    """Preserve canonical IDs in fragments; never accept imported URL syntax."""
    # Native service identifiers may differ only by '_' versus '-'. Their
    # anchors must remain distinct without introducing URL syntax into a link.
    if kind == "service":
        return kind + "-" + hashlib.sha256(value.encode()).hexdigest()
    safe = value.replace("_", "-")
    if re.fullmatch(r"[a-z0-9-]+", safe) is None:
        safe = "encoded-" + hashlib.sha256(value.encode()).hexdigest()
    return kind + "-" + safe


def _page_name(stem: str, page: int) -> str:
    if stem == "evidence" and page:
        return f"evidenceindex-{page + 1}.html"
    return stem + (f"-{page + 1}" if page else "") + ".html"


def _targets(
    records: list[dict[str, Any]], stem: str, kind: str, size: int, key: str = "id"
) -> dict[str, str]:
    return {
        r[key]: _page_name(stem, i // size) + "#" + _anchor(kind, r[key])
        for i, r in enumerate(records)
    }


def _record_table(
    title: str, headings: tuple[str, ...], rows: list[tuple[str, tuple[str, ...]]]
) -> str:
    if not rows:
        return '<p class="muted">None recorded in this view.</p>'
    return (
        '<div class="scroll" tabindex="0" role="region" aria-label="'
        + escape(title)
        + '"><table><caption>'
        + escape(title)
        + "</caption><thead><tr>"
        + "".join('<th scope="col">' + escape(h) + "</th>" for h in headings)
        + "</tr></thead><tbody>"
        + "".join(
            '<tr id="'
            + escape(anchor)
            + '">'
            + "".join("<td>" + c + "</td>" for c in cells)
            + "</tr>"
            for anchor, cells in rows
        )
        + "</tbody></table></div>"
    )


def _flow_label(flow: dict[str, Any]) -> str:
    if flow.get("arp"):
        return (
            "ARP "
            + str(flow["arp"]["operation"])
            + " · "
            + _endpoint(flow, "source")
            + " · "
            + _endpoint(flow, "destination")
        )
    protocol = str(flow["transport"]).upper()
    port = flow["destination_port"]
    if port is not None:
        protocol += "/" + str(port)
    source_port = flow["source_port"]
    return (
        _endpoint(flow, "source")
        + " → "
        + _endpoint(flow, "destination")
        + " · "
        + protocol
        + (" · from port " + str(source_port) if source_port is not None else "")
    )


def _decision_label(proposal: dict[str, Any] | None, version: int | None = None) -> str:
    if proposal is None:
        return "Not reviewed"
    if proposal["decision"] == "ACCEPT":
        return (
            "Accepted · Asset "
            + str(proposal["selected_asset_id"])
            + " · Interface "
            + str(proposal["selected_interface_id"])
        )
    if proposal["decision"] == "REJECT":
        return "Rejected"
    if not proposal["candidates"]:
        return "Unsupported IPv6 association" if version == 6 else "No candidate · pending review"
    return "Pending owner review"


def _technical(label: str, value: object) -> str:
    return (
        "<details><summary>" + escape(label) + "</summary><pre>" + _json(value) + "</pre></details>"
    )


def _packet_rows(samples: list[dict[str, Any]]) -> str:
    rows = []
    for sample in samples:
        stamp = sample["timestamp"]
        value = None
        if stamp is not None:
            exact = Fraction(stamp["ticks"], stamp["denominator"]) + stamp["offset_seconds"]
            value = f"{exact.numerator}/{exact.denominator}"
        rows.append(
            tuple(escape(sample[k]) for k in ("index", "offset"))
            + (escape(f"{sample['section']}:{sample['interface']}"),)
            + tuple(escape(sample[k]) for k in ("captured_length", "original_length"))
            + (timestamp_html(value),)
        )
    return table(
        "Packet references in the original capture",
        (
            "Packet record",
            "Record / block byte offset",
            "Section : interface",
            "Captured bytes",
            "Original bytes",
            "Observed UTC",
        ),
        rows,
    )


def generate_site(
    observations: dict[str, Any],
    output: Path,
    comparison: dict[str, Any] | None = None,
    limits: CaptureLimits = CAPTURE_LIMITS,
    *,
    mapping: dict[str, Any] | None = None,
    compact_prototype: bool = False,
) -> dict[str, Any]:
    """Render indexed human views without modifying canonical analytical evidence."""
    fresh_destination(output)
    files: dict[str, str] = {}
    total = 0
    capture = observations["capture"]
    flows = observations["flows"]
    hosts = observations["hosts"]
    groups = observations["conversations"]
    found = comparison["findings"] if comparison else []
    decisions = (
        comparison["association_decisions"]
        if comparison
        else (mapping["proposals"] if mapping else [])
    )
    size = limits.rows_per_page
    flow_by_id = {f["id"]: f for f in flows}
    finding_by_flow = {f["flow_id"]: f for f in found}
    host_by_ip = {h["ip"]: h for h in hosts}
    decision_by_ip = {p["observed_ip"]: p for p in decisions}
    decision_by_id = {p["id"]: p for p in decisions}
    host_targets = _targets(hosts, "hosts", "address", size)
    group_targets = _targets(groups, "groups", "group", size)
    finding_targets = _targets(found, "findings", "finding", size, "flow_id")
    association_targets = _targets(decisions, "associations", "association", size)
    aggregate_targets = _targets(flows, "conversations", "aggregate", size)
    index_targets = _targets(flows, "evidence", "evidence", size)
    evidence_targets = {f["id"]: _evidence_target(i, f["id"], size) for i, f in enumerate(flows)}
    related: dict[str, list[dict[str, Any]]] = {h["ip"]: [] for h in hosts}
    for flow in flows:
        for ip in dict.fromkeys((flow["source_ip"], flow["destination_ip"])):
            if ip in related:
                related[ip].append(flow)
    references = [{"host": h, "flow": f} for h in hosts for f in related[h["ip"]]]
    reference_targets: dict[str, str] = {}
    for i, ref in enumerate(references):
        reference_targets.setdefault(
            ref["host"]["id"],
            _page_name("address-links", i // size)
            + "#"
            + _anchor("reference", ref["host"]["id"] + "-" + ref["flow"]["id"]),
        )

    def address(value: str | None, *, arp_target: bool = False) -> str:
        if value is None:
            return "Address unavailable"
        host = host_by_ip.get(value)
        label = value + (" · ARP target reference" if arp_target else "")
        return link(host_targets[host["id"]], label) if host else escape(label) + " · not cataloged"

    def assessment(flow_id: str) -> str:
        finding = finding_by_flow.get(flow_id)
        if finding is None:
            return "Model comparison not requested"
        code = finding["classification"]
        return (
            link(finding_targets[flow_id], _classification(code))
            + "<p>"
            + escape(interpretation(code))
            + "</p>"
        )

    def flow_links(values: list[dict[str, Any]], target: dict[str, str]) -> str:
        return (
            '<ul class="related-list">'
            + "".join("<li>" + link(target[f["id"]], _flow_label(f)) + "</li>" for f in values)
            + "</ul>"
            if values
            else "None recorded"
        )

    def decision_view(proposal: dict[str, Any], *, heading: bool = False) -> str:
        selected = (
            (
                "Asset "
                + str(proposal["selected_asset_id"])
                + " · Interface "
                + str(proposal["selected_interface_id"])
            )
            if proposal["decision"] == "ACCEPT"
            else "No selection"
        )
        candidates = bullet_list(
            [
                "Asset " + p["asset_id"] + " · Interface " + p["interface_id"]
                for p in proposal["candidates"]
            ],
            empty="No declared candidate",
        )
        body = ("<h3>Owner review assertion</h3>" if heading else "") + properties(
            [
                ("Observed address", address(proposal["observed_ip"])),
                (
                    "Decision",
                    escape(
                        _decision_label(
                            proposal, host_by_ip.get(proposal["observed_ip"], {}).get("ip_version")
                        )
                    ),
                ),
                ("Candidates", candidates),
                ("Selected association", escape(selected)),
                ("Reviewer", escape(proposal["reviewer"] or "Not recorded")),
                ("Rationale", escape(proposal["rationale"] or "No review rationale recorded")),
            ]
        )
        return body + (
            "<p>An accepted association is an owner assertion for this "
            "evidence; it does not prove physical identity or IP "
            "ownership.</p>"
        )

    try:
        with tempfile.TemporaryDirectory(dir=output.parent, prefix=".otarchguard-capture-") as tmp:
            stage = Path(tmp)

            def write(name: str, data: bytes) -> None:
                nonlocal total
                if re.fullmatch(r"[a-z0-9-]+\.(html|css|json)", name) is None or name in files:
                    fail("CAPTURE_OUTPUT", "$", "Unsafe or duplicate generated filename.")
                check_limit("capture_site_files", len(files) + 1, limits.pages)
                if name.endswith(".html"):
                    check_limit("capture_page_bytes", len(data), 1024 * 1024)
                check_limit("capture_output_bytes", total + len(data), limits.output_bytes)
                (stage / name).write_bytes(data)
                files[name] = hashlib.sha256(data).hexdigest()
                total += len(data)

            def page(name: str, title: str, body: str) -> None:
                write(name, _document(title, body, capture["sha256"], name))

            def listing(
                stem: str,
                title: str,
                headings: tuple[str, ...],
                records: list[dict[str, Any]],
                render: Callable[[dict[str, Any], int], tuple[str, tuple[str, ...]]],
                introduction: str = "",
            ) -> None:
                count = max(1, (len(records) + size - 1) // size)
                check_limit("capture_site_files", count, limits.pages)
                for p in range(count):
                    nav = '<p aria-label="Table pages">'
                    if p:
                        nav += link(_page_name(stem, p - 1), "Previous page") + " · "
                    nav += f"Page {p + 1} of {count} · {len(records)} records"
                    if p + 1 < count:
                        nav += " · " + link(_page_name(stem, p + 1), "Next page")
                    nav += "</p>"
                    rows = [
                        render(r, i)
                        for i, r in enumerate(records[p * size : (p + 1) * size], p * size)
                    ]
                    page(
                        _page_name(stem, p),
                        title,
                        introduction + nav + _record_table(title, headings, rows),
                    )

            write("assets.css", (CAPTURE_CSS + (COMPACT_CSS if compact_prototype else "")).encode())
            write("observations.json", serialize(observations))
            if comparison is not None:
                write("comparison.json", serialize(comparison))
            if mapping is not None:
                write("mapping.json", serialize(mapping))
            page(
                "index.html",
                "Observed evidence overview",
                overview_summary(observations, comparison)
                + (
                    "<p>Start with a finding or an observed address, then follow "
                    "its communication to the exact evidence. The diagram shows "
                    "recorded direction; the model assessment is a separate "
                    "result.</p>"
                )
                + _diagram(flows, comparison, size)
                + capture_metadata(capture)
                + '<p><a href="evidence.html">Browse all evidence with communication context</a> · '
                '<a href="observations.json">Canonical observations JSON</a></p>',
            )

            def host_row(host: dict[str, Any], i: int) -> tuple[str, tuple[str, ...]]:
                values = related[host["ip"]]
                proposal = decision_by_ip.get(host["ip"])
                label = _decision_label(proposal, host["ip_version"])
                reviewed = (
                    link(association_targets[proposal["id"]], label) if proposal else escape(label)
                )
                context = flow_links(values[:8], aggregate_targets)
                if values:
                    context += link(
                        reference_targets[host["id"]], f"All {len(values)} related communications"
                    )
                return _anchor("address", host["id"]), (
                    escape(host["ip"]),
                    escape("IPv" + str(host["ip_version"])),
                    bullet_list(
                        [str(r).replace("_", " ") for r in host.get("observation_roles", [])]
                    ),
                    escape(host["packets"]),
                    bullet_list(host["source_macs"], empty="No source MAC recorded"),
                    bullet_list(host["destination_macs"], empty="No destination MAC recorded"),
                    reviewed,
                    context,
                )

            listing(
                "hosts",
                "Observed addresses (host catalog)",
                (
                    "Observed address",
                    "IP version",
                    "Observation roles",
                    "Packet appearances",
                    "Ethernet source MAC evidence",
                    "Ethernet destination MAC evidence",
                    "Reviewed association",
                    "Related communications",
                ),
                hosts,
                host_row,
                (
                    "<p>Addresses remain unresolved until owner review. ARP "
                    "target-only references and unspecified sender addresses do "
                    "not create catalog entries. MAC evidence describes captured "
                    "Ethernet delivery, not ownership. Packet appearances are "
                    "address appearances, not established sessions.</p>"
                ),
            )
            listing(
                "address-links",
                "All address communication references",
                ("Observed address", "Communication", "Evidence", "Finding"),
                references,
                lambda ref, i: (
                    _anchor("reference", ref["host"]["id"] + "-" + ref["flow"]["id"]),
                    (
                        link(host_targets[ref["host"]["id"]], ref["host"]["ip"]),
                        link(aggregate_targets[ref["flow"]["id"]], _flow_label(ref["flow"])),
                        link(evidence_targets[ref["flow"]["id"]], "Packet and model evidence"),
                        assessment(ref["flow"]["id"]),
                    ),
                ),
                (
                    "<p>Every cataloged-address reference is listed, ordered by "
                    "address and canonical aggregate order. Follow Next page for "
                    "continuing records. An ARP target reference does not "
                    "establish a destination device.</p>"
                ),
            )

            def conversation_row(flow: dict[str, Any], i: int) -> tuple[str, tuple[str, ...]]:
                return _anchor("aggregate", flow["id"]), (
                    link(evidence_targets[flow["id"]], _flow_label(flow)),
                    address(flow["source_ip"]),
                    address(flow["destination_ip"], arp_target=bool(flow.get("arp"))),
                    escape(flow["packets"]),
                    timestamp_html(flow["first_timestamp"]),
                    timestamp_html(flow["last_timestamp"]),
                    escape(flow["status"].capitalize()),
                    assessment(flow["id"]),
                    link(group_targets[flow["conversation_id"]], "Related bidirectional group"),
                )

            listing(
                "conversations",
                "Conversations: directed aggregates",
                (
                    "Communication / exact evidence",
                    "IP source / ARP sender",
                    "IP destination / ARP target reference",
                    "Packets",
                    "First observed UTC",
                    "Last observed UTC",
                    "Decoding",
                    "Finding",
                    "Group",
                ),
                flows,
                conversation_row,
                (
                    "<p>Each row is a directed aggregate, not a completed "
                    "session. Times are exact UTC displays; expandable fields "
                    "retain the canonical rational value.</p>"
                ),
            )
            listing(
                "evidence",
                "Evidence index",
                ("Communication", "Packet records", "Directed aggregate", "Finding"),
                flows,
                lambda f, i: (
                    _anchor("evidence", f["id"]),
                    (
                        link(evidence_targets[f["id"]], _flow_label(f)),
                        escape(f["packets"]),
                        link(aggregate_targets[f["id"]], "Communication context"),
                        assessment(f["id"]),
                    ),
                ),
                (
                    "<p>Choose a readable communication label to inspect packet "
                    "references, owner associations and model evidence. Canonical"
                    " identifiers remain in technical details.</p>"
                ),
            )

            def group_row(group: dict[str, Any], i: int) -> tuple[str, tuple[str, ...]]:
                members = [flow_by_id[k] for k in group["flow_ids"]]
                endpoints = _flow_label(members[0]) if members else "Endpoints unavailable"
                links = flow_links(members[:8], aggregate_targets)
                if len(members) > 8:
                    links += (
                        "<details><summary>Remaining directed aggregates</summary>"
                        + flow_links(members[8:], aggregate_targets)
                        + "</details>"
                    )
                return _anchor("group", group["id"]), (
                    escape(endpoints),
                    escape(group["transport"].upper()),
                    escape(len(members)),
                    escape(group["packets"]),
                    timestamp_html(group["first_timestamp"]),
                    timestamp_html(group["last_timestamp"]),
                    links,
                    escape(group["initiation_direction"].replace("_", " ")),
                )

            listing(
                "groups",
                "Bidirectional groups (not sessions)",
                (
                    "Endpoint context",
                    "Transport",
                    "Directed aggregates",
                    "Packets",
                    "First observed UTC",
                    "Last observed UTC",
                    "Linked communications",
                    "Initiation evidence",
                ),
                groups,
                group_row,
                (
                    "<p>A bidirectional group is a collection of related observed"
                    " endpoint tuples, not proof of an established application "
                    "session. Two recorded directions do not prove communication "
                    "success. Endpoint context is taken from a member, not a new "
                    "inferred connection.</p>"
                ),
            )
            page(
                "protocols.html", "Protocols: transport facts and port hints", protocols_view(flows)
            )

            def finding_row(finding: dict[str, Any], i: int) -> tuple[str, tuple[str, ...]]:
                flow = flow_by_id[finding["flow_id"]]
                code = finding["classification"]
                return _anchor("finding", flow["id"]), (
                    link(evidence_targets[flow["id"]], _flow_label(flow)),
                    escape(_classification(code)),
                    "<p>"
                    + escape(interpretation(code))
                    + "</p><p>"
                    + escape(finding.get("reason", ""))
                    + "</p>",
                    link(aggregate_targets[flow["id"]], "Communication context")
                    + " · "
                    + link(group_targets[flow["conversation_id"]], "Related group")
                    + "<details><summary>Exact classification code</summary><code>"
                    + escape(code)
                    + "</code></details>",
                )

            listing(
                "findings",
                "Findings / architecture comparison",
                (
                    "Communication / supporting evidence",
                    "Model assessment",
                    "Interpretation and recorded reason",
                    "Related context",
                ),
                found,
                finding_row,
                (
                    "<p>Findings compare specific observed evidence with the "
                    "declared model. A discrepancy is not a confirmed intrusion "
                    "or deployed firewall violation.</p>"
                )
                if comparison
                else (
                    "<p>Model comparison was not requested. Observation alone "
                    "establishes neither authorization nor blocking.</p>"
                ),
            )

            def association_row(proposal: dict[str, Any], i: int) -> tuple[str, tuple[str, ...]]:
                host = host_by_ip.get(proposal["observed_ip"])
                related_link = (
                    link(reference_targets[host["id"]], "All related communications")
                    if host and host["id"] in reference_targets
                    else "No related aggregate recorded"
                )
                binding_source = comparison or mapping
                bindings = (
                    {
                        k: binding_source[k]
                        for k in ("capture_sha256", "model_sha256", "observations_sha256")
                    }
                    if binding_source
                    else {}
                )
                return _anchor("association", proposal["id"]), (
                    address(proposal["observed_ip"]),
                    decision_view(proposal),
                    related_link,
                    "<details><summary>Evidence binding and original review record</summary>"
                    + identity("Association ID", proposal["id"])
                    + render_value(bindings)
                    + _technical("Complete canonical decision", proposal)
                    + "</details>",
                )

            listing(
                "associations",
                "Owner associations and review decisions",
                ("Observed address", "Owner review", "Related observations", "Technical binding"),
                decisions,
                association_row,
                (
                    "<p>Accepted, pending, rejected and unavailable candidates "
                    "remain explicit. Reviewed associations assert identity "
                    "within this finite evidence; they do not prove physical "
                    "device ownership.</p>"
                )
                if decisions
                else (
                    "<p>No model association review was supplied. No identity has"
                    " been inferred from the capture.</p>"
                ),
            )
            absent = comparison["declared_services_not_observed"] if comparison else []
            listing(
                "not-observed",
                "Declared services not observed",
                ("Declared service", "Assessment", "Scope and interpretation"),
                absent,
                lambda s, i: (
                    _anchor("service", s["service_id"]),
                    (
                        escape(s["service_id"]),
                        escape(_classification(s["classification"])),
                        escape(s["reason"])
                        + "<p>"
                        + escape(interpretation(s["classification"]))
                        + "</p>",
                    ),
                ),
                (
                    "<p>Absence assessment: "
                    + escape(comparison["absence_assessment"]["status"])
                    + ". "
                    + escape(comparison["absence_assessment"]["reason"])
                    + "</p><p>"
                    + escape(comparison["absence_scope"])
                    + "</p>"
                )
                if comparison
                else (
                    "<p>Declared-service comparison was not requested. No absence"
                    " assessment is made.</p>"
                ),
            )
            page(
                "coverage.html",
                "Coverage and interpretation limits",
                coverage_view(observations, comparison),
            )

            def detail(flow: dict[str, Any]) -> str:
                finding = finding_by_flow.get(flow["id"])
                body = (
                    '<section class="evidence-record" id="'
                    + _anchor("flow", flow["id"])
                    + '"><h2>'
                    + escape(_flow_label(flow))
                    + "</h2>"
                )
                body += (
                    "<p>"
                    + link(aggregate_targets[flow["id"]], "Return to this communication")
                    + " · "
                    + link(index_targets[flow["id"]], "Evidence index")
                    + " · "
                    + link(group_targets[flow["conversation_id"]], "Related group")
                )
                if finding:
                    body += " · " + link(finding_targets[flow["id"]], "Related finding")
                body += "</p><h3>Communication summary</h3>" + properties(
                    [
                        ("IP source / ARP sender", address(flow["source_ip"])),
                        (
                            "IP destination / ARP target reference",
                            address(flow["destination_ip"], arp_target=bool(flow.get("arp"))),
                        ),
                        ("Transport", escape(flow["transport"].upper())),
                        ("Packets", escape(flow["packets"])),
                        ("First observed UTC", timestamp_html(flow["first_timestamp"])),
                        ("Last observed UTC", timestamp_html(flow["last_timestamp"])),
                    ]
                )
                body += (
                    "<h3>Unsupported conditions and uncertainty</h3><p>Recorded "
                    "direction is not proof of an initiator, completed session, "
                    "successful application exchange or authorization.</p>"
                )
                body += (
                    "<p>Decoding status: "
                    + escape(flow["status"])
                    + ".</p>"
                    + bullet_list(
                        flow["limitations"],
                        empty=(
                            "No additional per-aggregate decoding incident recorded; "
                            "sensor visibility remains unknown."
                        ),
                    )
                )
                if flow.get("arp"):
                    body += (
                        "<p>ARP sender and target fields are message claims. A target"
                        " reference does not establish a device, response or "
                        "ownership. Ethernet delivery is recorded separately.</p>"
                    )
                body += "<h3>Original observed evidence</h3>" + render_value(
                    {
                        "source_port": flow["source_port"],
                        "destination_port": flow["destination_port"],
                        "captured_bytes": flow["captured_bytes"],
                        "original_bytes": flow["original_bytes"],
                        "source_macs": flow["source_macs"],
                        "destination_macs": flow["destination_macs"],
                        "vlans": flow["vlans"],
                        "interfaces": flow["interfaces"],
                        "tcp_flags": flow["tcp_flags"],
                        "arp": flow.get("arp"),
                        "protocol_hints": flow["protocol_hints"],
                    }
                )
                body += (
                    "<h3>Packet references</h3><p>References identify records or "
                    "blocks in the original capture with the bound digest; "
                    "payloads are not copied.</p>"
                ) + _packet_rows(flow["samples"])
                body += (
                    "<p>"
                    + escape(flow["samples_omitted"])
                    + (
                        " additional packet references omitted from bounded samples; "
                        "aggregate counts retain every record.</p>"
                    )
                )
                body += (
                    "<details><summary>Initial SYN evidence and sampling</summary><p>"
                    + escape(flow["initiation_packets"])
                    + " initial SYN records; "
                    + escape(flow["initiation_evidence_omitted"])
                    + " references omitted.</p>"
                    + _packet_rows(flow["initiation_evidence"])
                    + "</details>"
                )
                body += "<h3>Reviewed associations</h3>"
                joined = (
                    finding["association_decision_ids"]
                    if finding
                    else [
                        p["id"]
                        for ip in dict.fromkeys((flow["source_ip"], flow["destination_ip"]))
                        if (p := decision_by_ip.get(ip))
                    ]
                )
                for decision_id in joined:
                    proposal = decision_by_id[decision_id]
                    body += (
                        "<p>"
                        + link(
                            association_targets[decision_id],
                            "Review for " + proposal["observed_ip"],
                        )
                        + "</p>"
                        + decision_view(proposal)
                    )
                if not joined:
                    body += "<p>No owner association decision is linked to this aggregate.</p>"
                body += "<h3>Architecture comparison</h3>" + assessment(flow["id"])
                if finding:
                    body += "<p>Recorded reason: " + escape(finding["reason"]) + "</p>"
                    native = finding["native_result"]
                    if native is not None:
                        body += (
                            "<h3>Native evaluator witness / diagnostic</h3><p>This is "
                            "declared-model evidence for the selected initiation and "
                            "port. It does not prove the captured route or deployed "
                            "firewall behavior. Frontier diagnostics are not a unique "
                            "root cause or a guaranteed fix.</p>"
                        )
                        native_display = (
                            (lambda value: compact_value(value, lambda item, _: render_value(item)))
                            if compact_prototype
                            else render_value
                        )
                        body += native_display(
                            {
                                "source_asset": native["query"]["source_asset_id"],
                                "destination_asset": native["query"]["destination_asset_id"],
                                "declared_service": native["query"]["service_id"],
                                "observed_destination_port": native["observed_destination_port"],
                            }
                        )
                        body += (
                            (
                                "<details><summary>Selected interval: complete witness or "
                                "diagnostic</summary>"
                            )
                            + native_display(native["selected_interval"])
                            + "</details>"
                            + _technical("Complete original native evaluator record", native)
                        )
                    else:
                        body += (
                            "<p>No native model evaluation is available for this observation.</p>"
                        )
                body += "<h3>Canonical identifiers and machine-readable references</h3>"
                body += (
                    identity("Evidence ID", flow["id"])
                    + identity("Group ID", flow["conversation_id"])
                    + identity("Observation SHA-256", observations["observations_sha256"])
                )
                body += '<p><a href="observations.json">Canonical observations JSON</a>'
                if comparison:
                    body += ' · <a href="comparison.json">Canonical comparison JSON</a>'
                if mapping:
                    body += ' · <a href="mapping.json">Canonical owner mapping JSON</a>'
                body += (
                    "</p>"
                    + _technical("Complete canonical aggregate record (advanced)", flow)
                    + "</section>"
                )
                return body

            for start in range(0, len(flows), size):
                page(
                    f"evidence-{start // size + 1}.html",
                    "Evidence details with communication context",
                    "".join(detail(f) for f in flows[start : start + size]),
                )
            audit = audit_site(stage)
            _no_links(output)
            if output.exists():
                fail("CAPTURE_OUTPUT", "$", "Output appeared during staging; publication refused.")
            os.rename(stage, output)
    except OSError:
        fail("CAPTURE_OUTPUT", "$", "Cannot publish the complete local capture report.")
    return {
        "capture_sha256": capture["sha256"],
        "files": files,
        "output_bytes": total,
        "audit": audit,
        "entrypoint": "index.html",
        "status": "complete",
    }
