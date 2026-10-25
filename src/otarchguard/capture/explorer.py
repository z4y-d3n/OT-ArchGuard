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
    ("hosts.html", "Observed devices"),
    ("conversations.html", "Conversations"),
    ("protocols.html", "Protocols"),
    ("findings.html", "Comparison"),
    ("coverage.html", "Coverage and limits"),
)


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


def _diagram(flows: list[dict[str, Any]], comparison: dict[str, Any] | None) -> str:
    ips = sorted({f[k] for f in flows for k in ("source_ip", "destination_ip") if f[k]})
    if len(ips) > 16 or len(flows) > 24:
        return (
            "<p>Diagram omitted: more than 16 addresses or 24 directed aggregates. "
            "The complete paginated tables and JSON retain every aggregate.</p>"
        )
    if not ips:
        return "<p>No decodable IP-address relationships to diagram.</p>"
    positions = {ip: 70 + i * 56 for i, ip in enumerate(ips)}
    lines: list[str] = []
    findings = {f["flow_id"]: f for f in comparison["findings"]} if comparison else {}
    for i, flow in enumerate(flows):
        source, target = flow["source_ip"], flow["destination_ip"]
        if source not in positions or target not in positions:
            continue
        x = 350 + i * 18
        y1, y2 = positions[source], positions[target]
        lines.append(
            f'<path class="diagram-line documentary" d="M 300 {y1} H {x} V {y2} H 310" '
            'marker-end="url(#observed-arrow)"/>'
        )
        finding = findings.get(flow["id"], {})
        # Show comparison as a separate textual mark; never label a packet arrow permitted.
        if finding.get("classification") in {
            "OBSERVED_MODEL_REACHABLE",
            "OBSERVED_MODEL_UNREACHABLE",
        }:
            lines.append(
                f'<text x="{x + 4}" y="{(y1 + y2) // 2}">'
                + ("R" if finding["classification"] == "OBSERVED_MODEL_REACHABLE" else "U")
                + "</text>"
            )
    return (
        "<figure><figcaption>Observed directed aggregates · dashed arrows. "
        "Arrow multiplicity is neither session count nor physical connectivity. "
        "Comparison marks R/U mean model reachable/unreachable for a separately evaluated "
        "initiation; route witnesses remain in evidence details. Pending and unsupported "
        'evidence is explained in the tables.</figcaption><div class="scroll" tabindex="0" '
        'role="region" aria-label="Observed communication diagram"><svg '
        f'xmlns="http://www.w3.org/2000/svg" width="850" height="{len(ips) * 56 + 100}" '
        'role="img" aria-labelledby="diagram-title"><text id="diagram-title" x="20" y="30">'
        'Observed communication, not authorization</text><defs><marker id="observed-arrow" '
        'viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" '
        'orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#505c66"/>'
        "</marker></defs>"
        + "".join(lines)
        + "".join(f'<text x="20" y="{positions[ip] + 5}">{escape(ip)}</text>' for ip in ips)
        + "</svg></div></figure>"
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
                stem: str, title: str, headings: tuple[str, ...], rows: list[tuple[str, ...]]
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
                        navigation + table(title, headings, rows[i * size : (i + 1) * size]),
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
                + _properties("Capture metadata and interfaces", capture)
                + _properties("Coverage", observations["coverage"])
                + _diagram(flows, comparison)
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
                    "Reviewed association",
                ),
                [
                    tuple(
                        _json(h[k])
                        for k in ("ip", "ip_version", "source_macs", "destination_macs", "packets")
                    )
                    + (_json(associations.get(h["ip"], {"decision": "Not reviewed"})),)
                    for h in observations["hosts"]
                ],
            )
            detail_rows: list[str] = []
            conversation_rows: list[tuple[str, ...]] = []
            for i, flow in enumerate(flows):
                detail_name = f"evidence-{i // limits.rows_per_page + 1}.html"
                anchor = "flow-" + flow["id"]
                conclusion = findings.get(flow["id"], {}).get("classification", "Not compared")
                conversation_rows.append(
                    (
                        link(detail_name + "#" + anchor, str(flow["source_ip"])),
                        escape(flow["destination_ip"]),
                        escape(flow["transport"]),
                        escape(f"{flow['source_port']} → {flow['destination_port']}"),
                        escape(flow["packets"]),
                        escape(flow["captured_bytes"]),
                        escape(flow["first_timestamp"]),
                        escape(flow["last_timestamp"]),
                        escape(flow["status"]),
                        escape(conclusion),
                    )
                )
                detail_rows.append(
                    '<section id="'
                    + anchor
                    + '"><h2>Directed aggregate '
                    + escape(flow["id"][:12])
                    + "</h2><p>Direction is packet direction. "
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
                    "Observed source",
                    "Observed destination",
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
                    (escape(f["flow_id"]), escape(f["classification"]), escape(f.get("reason", "")))
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
