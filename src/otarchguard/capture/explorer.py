"""Bounded, deterministic, offline presentation of independent capture evidence."""

import hashlib
import html
import json
import os
import re
import tempfile
from collections import Counter
from pathlib import Path, PureWindowsPath
from typing import Any

from otarchguard.capture.contract import CAPTURE_LIMITS, CaptureLimits
from otarchguard.diagnostics import check_limit, fail
from otarchguard.explorer_html import CSS, audit_site, escape, link, table
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
    ("findings.html", "Comparison"),
    ("coverage.html", "Coverage and limits"),
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


def _document(title: str, body: str, capture_hash: str) -> bytes:
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
        + "</p><p>Capture SHA-256: <code>"
        + escape(capture_hash)
        + '</code></p></header><nav aria-label="Evidence views"><ul>'
        + "".join("<li>" + link(p, label) + "</li>" for p, label in NAV)
        + '</ul></nav><main id="main">'
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


def generate_site(
    observations: dict[str, Any],
    output: Path,
    comparison: dict[str, Any] | None = None,
    limits: CaptureLimits = CAPTURE_LIMITS,
    *,
    mapping: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Publish a complete, audited fresh directory or fail without replacing old files."""
    fresh_destination(output)
    files: dict[str, str] = {}
    total = 0
    capture = observations["capture"]
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
                write(name, _document(title, body, capture["sha256"]))

            def listing(
                stem: str,
                title: str,
                headings: tuple[str, ...],
                rows: list[tuple[str, ...]],
                introduction: str = "",
            ) -> None:
                size = limits.rows_per_page
                check_limit("capture_site_files", (len(rows) + size - 1) // size, limits.pages)
                count = max(1, (len(rows) + size - 1) // size)
                names = [stem + ("" if i == 0 else f"-{i + 1}") + ".html" for i in range(count)]
                for i, name in enumerate(names):
                    navigation = '<p aria-label="Table pages">'
                    if i:
                        navigation += link(names[i - 1], "Previous") + " · "
                    navigation += f"Page {i + 1} of {count} · {len(rows)} records"
                    if i + 1 < count:
                        navigation += " · " + link(names[i + 1], "Next")
                    navigation += "</p>"
                    page(
                        name,
                        title,
                        introduction
                        + navigation
                        + table(title, headings, rows[i * size : (i + 1) * size]),
                    )

            write("assets.css", CSS.encode())
            write("observations.json", serialize(observations))
            if comparison is not None:
                write("comparison.json", serialize(comparison))
            if mapping is not None:
                write("mapping.json", serialize(mapping))
            flows = observations["flows"]
            findings = {f["flow_id"]: f for f in comparison["findings"]} if comparison else {}
            page(
                "index.html",
                "Observed evidence overview",
                "<p>This site contains complete container processing within the stated limits. "
                "Capture visibility and packet decoding have separate limitations. First/last "
                "timestamps are exact rational UTC seconds; missing timestamps remain missing.</p>"
                + _diagram(flows, comparison, limits.rows_per_page)
                + _properties("Coverage", observations["coverage"])
                + _properties("Capture metadata and interfaces", capture)
                + '<p><a href="observations.json">Canonical observations JSON</a></p>'
                + (
                    '<p><a href="comparison.json">Canonical comparison JSON</a> · '
                    '<a href="associations.html">Reviewed association decisions</a></p>'
                    if comparison
                    else ""
                ),
            )
            associations = (
                {p["observed_ip"]: p for p in comparison["association_decisions"]}
                if comparison
                else {}
            )
            listing(
                "hosts",
                "Observed addresses and transit MAC evidence",
                (
                    "Observed IP",
                    "Version",
                    "Source MAC evidence",
                    "Destination MAC evidence",
                    "Appearances",
                    "Observation roles",
                    "Reviewed association",
                ),
                [
                    tuple(
                        _json(h[k])
                        for k in ("ip", "ip_version", "source_macs", "destination_macs", "packets")
                    )
                    + (
                        _json(h.get("observation_roles", [])),
                        _json(associations.get(h["ip"], {"decision": "Not reviewed"})),
                    )
                    for h in observations["hosts"]
                ],
                "<p>Addresses are observations with unresolved identity until owner review. "
                "ARP target-only references and unspecified ARP sender addresses do not create "
                "catalog entries. MAC evidence describes Ethernet delivery, not ownership.</p>",
            )
            detail_rows: list[str] = []
            conversation_rows: list[tuple[str, ...]] = []
            evidence_targets = {
                flow["id"]: _evidence_target(i, flow["id"], limits.rows_per_page)
                for i, flow in enumerate(flows)
            }
            for i, flow in enumerate(flows):
                detail_name = f"evidence-{i // limits.rows_per_page + 1}.html"
                anchor = "flow-" + flow["id"]
                conclusion = findings.get(flow["id"], {}).get("classification", "Not compared")
                conversation_rows.append(
                    (
                        link(detail_name + "#" + anchor, _endpoint(flow, "source")),
                        escape(_endpoint(flow, "destination")),
                        escape(
                            "ARP " + flow["arp"]["operation"]
                            if flow.get("arp")
                            else flow["transport"]
                        ),
                        escape(
                            f"{flow['source_port']} → {flow['destination_port']}"
                            if flow["source_port"] is not None
                            and flow["destination_port"] is not None
                            else "Unavailable"
                        ),
                        escape(flow["packets"]),
                        escape(flow["captured_bytes"]),
                        escape(flow["first_timestamp"]),
                        escape(flow["last_timestamp"]),
                        escape(flow["status"]),
                        escape(_classification(conclusion))
                        + "<br><code>"
                        + escape(conclusion)
                        + "</code>",
                    )
                )
                detail_rows.append(
                    '<section id="'
                    + anchor
                    + '"><h2>Directed aggregate '
                    + escape(flow["id"][:12])
                    + "</h2><p>For IP packets, direction is packet direction. For ARP, "
                    "source_ip/destination_ip retain historical sender/target protocol fields; "
                    "explicit ARP metadata records Ethernet delivery. Mentioning a target "
                    "does not establish its presence or response. "
                    "A five-tuple is not an established session. Sample omissions do not alter "
                    "aggregate denominators. Packet references identify record/block offsets "
                    "in the capture with the digest above.</p><pre>"
                    + _json(flow)
                    + "</pre>"
                    + _properties(
                        "Comparison and original evaluator evidence",
                        findings.get(flow["id"], {"classification": "Not compared"}),
                    )
                    + "</section>"
                )
                if len(detail_rows) == limits.rows_per_page or i == len(flows) - 1:
                    page(
                        detail_name,
                        "Reproducible evidence details",
                        "".join(detail_rows),
                    )
                    detail_rows.clear()
            listing(
                "conversations",
                "Directed aggregates in bidirectional conversations",
                (
                    "IP source / ARP sender",
                    "IP destination / ARP target reference",
                    "Transport",
                    "Ports",
                    "Packets",
                    "Captured bytes",
                    "First UTC seconds",
                    "Last UTC seconds",
                    "Decoding",
                    "Finding",
                ),
                conversation_rows,
            )
            listing(
                "groups",
                "Bidirectional conversation groups (not sessions)",
                ("Group metadata",),
                [(_json(c),) for c in observations["conversations"]],
            )
            # Group semantics are complete and linkable even when there are no initiating packets.
            transports: Counter[str] = Counter()
            hints: Counter[str] = Counter()
            for flow in flows:
                transports[flow["transport"]] += flow["packets"]
                for hint in flow["protocol_hints"]:
                    hints[json.dumps(hint, sort_keys=True)] += flow["packets"]
            page(
                "protocols.html",
                "Transport facts and industrial port hints",
                "<p>TRANSPORT_OBSERVED records parsed transport headers. PORT_HINT is a versioned "
                "port association only. No SIGNATURE_SUPPORTED application identification is "
                "implemented. Unknown and damaged metadata retains its classification.</p>"
                + _properties("Packet counts by transport", dict(sorted(transports.items())))
                + _properties("Port hints (may overlap)", dict(sorted(hints.items())))
                + '<p><a href="groups.html">Bidirectional group metadata</a></p>',
            )
            listing(
                "findings",
                "Architecture comparison and uncertainty",
                ("Flow", "Classification", "Explanation"),
                [
                    (
                        link(evidence_targets[f["flow_id"]], f["flow_id"]),
                        escape(_classification(f["classification"]))
                        + "<br><code>"
                        + escape(f["classification"])
                        + "</code>",
                        escape(f.get("reason", "")),
                    )
                    for f in comparison["findings"]
                ]
                if comparison
                else [],
            )
            if comparison:
                listing(
                    "associations",
                    "Evidence-bound association decisions",
                    ("Owner decision and binding",),
                    [(_json(p),) for p in comparison["association_decisions"]],
                )
                listing(
                    "not-observed",
                    "Declared services not observed in this capture",
                    ("Scoped declaration and interpretation",),
                    [(_json(s),) for s in comparison["declared_services_not_observed"]],
                )
            page(
                "coverage.html",
                "Limitations, coverage and interpretation",
                _properties("Packet coverage", observations["coverage"])
                + _properties("Observation limitations", observations["limitations"])
                + _properties("Capture limitations", capture["limitations"])
                + (
                    _properties("Comparison limitations", comparison["limitations"])
                    + '<p><a href="not-observed.html">Declared services not observed</a></p>'
                    if comparison
                    else "<p>Model comparison was not requested.</p>"
                )
                + "<p>SPAN, capture loss, partial visibility, reused addresses, DHCP and unmodeled "
                "NAT can limit interpretation. MACs may belong to transit equipment. Interface "
                "counts do not prove physical links. Repeated packets and multiple sensors are "
                "counted as capture records, not independent sessions. The JSON preserves all "
                "aggregates; bounded packet samples explicitly disclose omissions.</p>",
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
