"""Versioned, deterministic offline evidence. No analysis or inferred topology."""

import json
import os
import tempfile
from dataclasses import asdict
from html import escape as _html_escape
from pathlib import Path
from typing import Any, Literal

from otarchguard import __version__
from otarchguard.api import ValidatedArchitecture
from otarchguard.comparison import ComparisonResult
from otarchguard.contract import RESOURCE_LIMITS, DiagnosticCategory, ResourceLimits
from otarchguard.diagnostics import Diagnostic, ModelError
from otarchguard.exposure import ExposureResult
from otarchguard.intents import CheckResult

type ReportKind = Literal["validation", "check", "exposure", "comparison"]
type Analysis = CheckResult | ExposureResult | ComparisonResult | None

LIMITATIONS = (
    "Declared IPv4 TCP/UDP initiation only; no return-path or session-completion guarantee.",
    "No implicit forwarding, application relay or host-compromise assumption.",
    "Completeness, scope, classifications and criticality are unverified owner declarations.",
    "Unmodeled access points and external dependencies require human review; they grant no paths.",
    "Reachability is not exploitability, compromise probability, physical impact or reduced risk.",
    "No conformity or certification claim. SL-T, SL-C and SL-A are unassessed, not zero.",
    "Unsupported input and resource exhaustion stop evaluation; neither means unreachable.",
    "Resource ceilings are provisional and are not benchmarked performance claims.",
    "This report is not a complete cybersecurity requirements specification or deployed inventory.",
)


def escape(value: str) -> str:
    """Escape markup and replace characters XML 1.0 cannot represent."""
    return _html_escape(
        "".join(
            char
            if char in "\t\n\r"
            or 0x20 <= ord(char) <= 0xD7FF
            or 0xE000 <= ord(char) <= 0xFFFD
            or 0x10000 <= ord(char) <= 0x10FFFF
            else "\ufffd"
            for char in value
        )
    )


_STYLE = """
body{font:16px system-ui,sans-serif;color:#182e40;background:#f5f7fa;margin:2rem auto;
max-width:1200px;padding:0 1.5rem}h1,h2,h3{color:#12334b}section{background:white;
padding:1rem;margin:1rem 0;border:1px solid #ccd6df}.table-scroll{overflow-x:auto;
max-width:100%;margin:1rem 0}table{border-collapse:collapse;min-width:100%;width:max-content}
th,td{border:1px solid #ccd6df;padding:.6rem;text-align:left;vertical-align:top;
min-width:10ch;max-width:36rem;word-break:normal;overflow-wrap:normal}
th{background:#e8f0f5;white-space:nowrap}td pre{min-width:22rem;max-width:36rem;
max-height:18rem;overflow:auto;margin:0}pre{white-space:pre-wrap;overflow-wrap:break-word;
font-size:.85rem}details{margin:1rem 0}summary{cursor:pointer;font-weight:bold;padding:.6rem;
background:#e8f0f5}figure{margin:1rem 0}figcaption{font-weight:bold;padding:.6rem 0}
.finding{padding:1rem;border-left:5px solid #a12121}.alert{border:3px solid
#a12121;background:#fff1ed}.note{border-left:5px solid #426784;padding-left:1rem}
.architecture-canvas{overflow-x:auto}svg{width:100%;height:auto;min-width:1000px}
caption{text-align:left;font-weight:bold;padding:.5rem 0}
"""


def json_report(report: dict[str, Any]) -> bytes:
    """UTF-8, sorted keys, LF termination; no machine paths or clock values."""
    return (json.dumps(report, sort_keys=True, ensure_ascii=True, indent=2) + "\n").encode()


def build_report(
    kind: ReportKind,
    snapshots: tuple[ValidatedArchitecture, ...],
    result: Analysis = None,
    *,
    limits: ResourceLimits = RESOURCE_LIMITS,
) -> dict[str, Any]:
    """Bind evidence to the exact validated models; reject stale/mismatched evidence."""
    expected: tuple[str, ...]
    if kind == "comparison" and isinstance(result, ComparisonResult):
        expected = (result.baseline.snapshot_sha256, result.proposed.snapshot_sha256)
    elif kind == "validation" and result is None:
        expected = tuple(snapshot.sha256 for snapshot in snapshots)
    elif kind == "check" and isinstance(result, CheckResult):
        expected = (result.snapshot_sha256,)
    elif kind == "exposure" and isinstance(result, ExposureResult):
        expected = (result.snapshot_sha256,)
    else:
        raise ValueError("Report kind and evidence do not match")
    if len(snapshots) != (2 if kind == "comparison" else 1) or expected != tuple(
        snapshot.sha256 for snapshot in snapshots
    ):
        raise ValueError("Report snapshot hashes do not match evidence")
    return {
        "report_version": 1,
        "engine_version": __version__,
        "schema_version": 1,
        "kind": kind,
        "status": "valid" if result is None else "passed" if result.passed else "failed_intents",
        "scope": (
            "Structural declarations only; reachability and intents not evaluated."
            if result is None
            else "Declared initiation model; finite evaluated scope and evidence follow."
        ),
        "limitations": LIMITATIONS,
        "security_level_evidence": {
            "SL-T": "unassessed",
            "SL-C": "unassessed",
            "SL-A": "unassessed",
            "evidence": "External assessment required; no security-level evidence evaluated.",
        },
        "resource_ceilings": asdict(limits),
        "snapshots": [
            {
                "role": "baseline"
                if kind == "comparison" and index == 0
                else "proposed"
                if kind == "comparison"
                else "architecture",
                "model_sha256": snapshot.sha256,
                "model": json.loads(snapshot.canonical_json),
                "diagram": diagram_summary(snapshot),
            }
            for index, snapshot in enumerate(snapshots)
        ],
        "result": {"structural_validation": "valid"} if result is None else asdict(result),
    }


def diagram_summary(snapshot: ValidatedArchitecture) -> dict[str, Any]:
    model = snapshot.model
    summarized = (
        len(model.interfaces) > 24
        or (len(model.transport_edges) + len(model.forwarding_edges) > 48)
        or len(model.assets) > 24
        or len(model.zones) > 12
    )
    return {
        "mode": "summary" if summarized else "full",
        "legend": (
            "Zone containers enclose interface placements. Cards label administrative owner zones; "
            "boundary attachment cards with the same ID represent one asset across placements. "
            "Only explicit directed arrows declare edges; they do not assert permission. "
            "Pairwise conduits annotate edges, never create links. Crossings are not junctions."
        ),
        "omitted_from_diagram": {
            "asset_ids": [a.id for a in model.assets] if summarized else [],
            "interface_ids": [i.id for i in model.interfaces] if summarized else [],
            "edge_ids": sorted(
                [e.id for e in model.transport_edges] + [e.id for e in model.forwarding_edges]
            )
            if summarized
            else [],
            "zone_ids": [z.id for z in model.zones[12:]] if summarized else [],
            "conduit_ids": [
                c.id
                for c in model.conduits
                if summarized
                or c.id
                not in (
                    {e.conduit_id for e in model.transport_edges}
                    | {e.conduit_id for e in model.forwarding_edges}
                )
            ],
        },
        "label_limit_characters": 100,
        "label_note": (
            "Long visual labels are truncated; full values are in tables. XML-incompatible "
            "characters display as replacement characters; JSON retains the original text."
        ),
    }


def architecture_svg(snapshot: ValidatedArchitecture) -> str:
    """Spatial placement schematic; only declared edges become routed arrows."""
    from otarchguard.diagrams import spatial_svg

    return spatial_svg(snapshot, diagram_summary(snapshot)["mode"] == "summary", escape)


def _value(value: Any) -> str:
    return value if isinstance(value, str) else json.dumps(value, sort_keys=True, ensure_ascii=True)


def _table(caption: str, rows: list[dict[str, Any]]) -> str:
    if not rows:
        return f"<p>{escape(caption)}: none.</p>"
    keys = list(dict.fromkeys(key for row in rows for key in row))

    def cell(value: Any) -> str:
        if isinstance(value, (dict, tuple, list)):
            return "<pre>" + escape(json.dumps(value, sort_keys=True, indent=2)) + "</pre>"
        return escape(_value(value))

    return (
        '<div class="table-scroll" role="region" tabindex="0" '
        f'aria-label="{escape(caption)} — scroll horizontally for all columns">'
        f"<table><caption>{escape(caption)}</caption><thead><tr>"
        + "".join(f"<th>{escape(key)}</th>" for key in keys)
        + "</tr></thead><tbody>"
        + "".join(
            "<tr>" + "".join(f"<td>{cell(row.get(key))}</td>" for key in keys) + "</tr>"
            for row in rows
        )
        + "</tbody></table></div>"
    )


def _intent_rows(value: Any, side: str = "architecture") -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if isinstance(value, dict):
        if "intents" in value and "snapshot_sha256" in value:
            for intent in value["intents"]:
                rows.append(
                    {
                        "snapshot": side,
                        "intent": intent["id"],
                        "kind": intent["kind"],
                        "outcome": "passed" if intent["passed"] else "FAILED",
                        "query_count": len(intent["queries"]),
                        "failed_intervals": [
                            {
                                "source": q["source_asset_id"],
                                "destination": q["destination_asset_id"],
                                "service": q["service_id"],
                                "protocol": q["protocol"],
                                "start": i["start"],
                                "end": i["end"],
                            }
                            for q in intent["queries"]
                            for i in q["intervals"]
                            if i["reachable"] != (intent["kind"] == "required")
                        ],
                    }
                )
        else:
            for key, child in value.items():
                rows.extend(_intent_rows(child, key if key in ("baseline", "proposed") else side))
    return rows


def _query_rows(value: Any, side: str = "architecture") -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if isinstance(value, dict):
        if "intervals" in value and "source_asset_id" in value:
            for interval in value["intervals"]:
                witness = interval["witness"]
                rows.append(
                    {
                        "snapshot": side,
                        "source": value["source_asset_id"],
                        "destination": value["destination_asset_id"],
                        "service": value["service_id"],
                        "protocol": value["protocol"],
                        "ports": f"{interval['start']}–{interval['end']}",
                        "reachable": interval["reachable"],
                        "witness_sha256": witness["snapshot_sha256"] if witness else None,
                        "permitted_steps": witness["steps"] if witness else [],
                        "unreachable_diagnostics": interval["diagnostics"],
                    }
                )
        else:
            for key, child in value.items():
                rows.extend(_query_rows(child, key if key in ("baseline", "proposed") else side))
    elif isinstance(value, (tuple, list)):
        for child in value:
            rows.extend(_query_rows(child, side))
    # The same query may occur in both the scenario and several intents.
    return list({json.dumps(row, sort_keys=True): row for row in rows}.values())


def _analysis_summary(result: dict[str, Any]) -> str:
    parts: list[str] = []
    for side in ("baseline", "proposed"):
        if side in result:
            parts.append(f"<h3>{side}</h3>" + _analysis_summary(result[side]))
    if "query_scope" in result:
        parts.append(_table("Finite evaluated scope", [result["query_scope"]]))
    for key in (
        "unavailable_origin_asset_ids",
        "unavailable_destination_service_ids",
        "comparable_service_ids",
        "noncomparable_service_ids",
    ):
        if key in result:
            parts.append(f"<p>{escape(key)}: {escape(_value(result[key]))}</p>")
    for key in (
        "observations",
        "destination_assets",
        "newly_reachable",
        "no_longer_reachable",
        "newly_reachable_assets",
        "no_longer_reachable_assets",
        "inventory_changes",
        "entity_changes",
        "suc_definition_changes",
        "intent_changes",
        "introduced_prohibited_violations",
        "resolved_prohibited_violations",
    ):
        if key in result:
            parts.append(_table(key, result[key]))
    return "".join(parts)


def _required_findings(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "<p>No failed required communications in the evaluated evidence.</p>"
    parts: list[str] = []
    for row in rows:
        parts.append(
            '<article class="finding"><h3>'
            + escape(f"{row['snapshot']} · {row['intent']} — FAILED")
            + "</h3><p>Required initiation is not permitted for:</p><ul>"
        )
        for interval in row["failed_intervals"]:
            text = (
                f"{interval['source']} → {interval['destination']} · "
                f"{interval['service']} · {interval['protocol'].upper()} "
                f"{interval['start']}–{interval['end']}"
            )
            parts.append(f"<li>{escape(text)}</li>")
        parts.append("</ul></article>")
    return "".join(parts)


def _query_evidence(rows: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for row in rows:
        title = (
            f"{row['snapshot']} · {row['source']} → {row['destination']} · "
            f"{row['service']} · {row['protocol'].upper()} {row['ports']} · "
            f"{'reachable' if row['reachable'] else 'unreachable'}"
        )
        parts.append(f"<details><summary>{escape(title)}</summary>")
        if row["reachable"]:
            parts.append(
                f"<p>Witness model SHA-256: <code>{escape(row['witness_sha256'])}</code></p>"
            )
            parts.append(_table("Permitted path steps (in replay order)", row["permitted_steps"]))
        else:
            parts.append(
                _table("Bounded unreachable explanation", [row["unreachable_diagnostics"]])
            )
        parts.append("</details>")
    return "".join(parts)


def html_report(report: dict[str, Any], snapshots: tuple[ValidatedArchitecture, ...]) -> bytes:
    """All model/evidence text is escaped; only generated SVG/CSS are trusted markup."""
    if [s.sha256 for s in snapshots] != [s["model_sha256"] for s in report["snapshots"]]:
        raise ValueError("HTML snapshot hashes do not match report")
    intents = _intent_rows(report["result"])
    failed_required = [
        row for row in intents if row["kind"] == "required" and row["outcome"] == "FAILED"
    ]
    body = [
        f"<h1>OT-ArchGuard · {escape(report['kind'])}</h1>",
        f"<p>Status: <strong>{escape(report['status'])}</strong>. {escape(report['scope'])}</p>",
        f'<section class="{"alert" if failed_required else "note"}">'
        "<h2>Operational communication findings</h2>",
        "<p>Review required communications independently of any exposure decrease.</p>",
        (
            "<p>Intent outcomes are unassessed in a structural validation report.</p>"
            if report["kind"] == "validation"
            else ""
        ),
        _required_findings(failed_required) if report["kind"] != "validation" else "",
        "</section>",
        "<p>Model-based initiation only; no conformity or physical-risk-reduction claim. "
        "SL-T, SL-C and SL-A: unassessed.</p>",
        "<section><h2>Architecture diagrams</h2><p>Visible diagrams follow immediately. "
        "Each arrow is an explicit declaration, not an assertion of permission.</p>",
    ]
    inventories: list[str] = []
    for entry, snapshot in zip(report["snapshots"], snapshots, strict=True):
        model = entry["model"]
        body += [
            f"<h3>{escape(entry['role'])}: {escape(model['architecture_id'])}</h3>",
            f"<p>SHA-256: <code>{escape(snapshot.sha256)}</code></p>",
            '<p class="note">Administrative ownership is asset.zone_id. Interface attachment '
            "is interface.placement_zone_id. Neither establishes connectivity. Business/IACS "
            "and safety classifications are displayed for human review; no level is inferred.</p>",
            f"<p>{escape(entry['diagram']['legend'])}</p>",
            f"<p>{escape(entry['diagram']['label_note'])}</p>",
            "<figure><figcaption>"
            f"{escape(entry['role'])} — {escape(entry['diagram']['mode'])} architecture diagram"
            "</figcaption>",
            '<div class="architecture-canvas" role="region" tabindex="0" '
            'aria-label="Architecture schematic — scroll horizontally if needed">',
            architecture_svg(snapshot),
            "</div></figure>",
        ]
        inventories += [
            "<details><summary>Full SUC declaration and inventory: "
            f"{escape(entry['role'])}</summary>",
            _table(
                "SUC declarations (owner assertions)",
                [{"field": k, "value": v} for k, v in model["suc"].items()],
            ),
            f"<p>Diagram omissions: {escape(_value(entry['diagram']['omitted_from_diagram']))}</p>",
        ]
        if any(entry["diagram"]["omitted_from_diagram"].values()):
            body.append(
                "<p>Diagram omissions: "
                + escape(_value(entry["diagram"]["omitted_from_diagram"]))
                + "</p>"
            )
        for collection in (
            "zones",
            "assets",
            "interfaces",
            "conduits",
            "transport_edges",
            "forwarding_edges",
            "services",
            "rules",
            "intents",
            "scenarios",
        ):
            inventories.append(_table(collection, model[collection]))
        inventories.append("</details>")
    body += [
        "</section><section><h2>Interpretation and unassessed evidence</h2><ul>",
        *(f"<li>{escape(item)}</li>" for item in report["limitations"]),
        "</ul><p>SL-T: unassessed; SL-C: unassessed; SL-A: unassessed. "
        "External security-level assessment evidence has not been evaluated.</p>",
        *(
            f"<p>{escape(e['role'])} completeness (owner assertion): "
            f"{escape(e['model']['suc']['completeness_assertion'])}</p>"
            for e in report["snapshots"]
        ),
        "<p>Unmodeled access points and dependencies remain unevaluated; expand SUC evidence "
        "for exact records. Assessment and approval evidence stays external.</p></section>",
        "<section><h2>Findings and witness provenance</h2>",
        "<p>Wide tables scroll horizontally without compressing text into narrow columns.</p>",
        _table("Independent intent outcomes", intents),
        _table(
            "Newly broken required intervals",
            report["result"].get("broken_required_communications", []),
        ),
        _analysis_summary(report["result"]),
        "<h3>Exact interval findings and replayable witnesses</h3><p>Expand a query to see "
        "original endpoints, states, edges, conduits and matching allows. Unreachable diagnostics "
        "are bounded explanations, not proof of a minimal cut.</p>",
        _query_evidence(_query_rows(report["result"])),
        "</section>",
        "<section><h2>SUC declarations and full inventory</h2>",
        *inventories,
        "</section>",
        "<section><h2>Complete reproducible report evidence</h2>",
        "<p>Report version 1; engine and schema versions, finite query scope, completeness "
        "assertions and provisional resource ceilings are included below. No timestamps.</p>",
        "<details><summary>Machine-readable JSON appendix (not an architecture diagram)</summary>",
        f"<pre>{escape(json_report(report).decode())}</pre></details></section>",
    ]
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta http-equiv="Content-Security-Policy" content="default-src &#39;none&#39;; '
        'style-src &#39;unsafe-inline&#39;; base-uri &#39;none&#39;; form-action &#39;none&#39;">'
        f"<title>OT-ArchGuard offline evidence</title><style>{_STYLE}</style></head><body>"
        + "".join(body)
        + "</body></html>\n"
    ).encode("utf-8")


def write_report(path: Path, data: bytes, inputs: tuple[Path, ...]) -> None:
    """Atomic single-artifact replacement; never overwrite an input architecture."""
    if path.resolve() in {item.resolve() for item in inputs}:
        raise ModelError(
            Diagnostic(
                DiagnosticCategory.IO_ERROR,
                "REPORT_IO_ERROR",
                "$",
                "Report output must differ from input paths.",
            )
        )
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent, prefix=".otarchguard-", delete=False
        ) as f:
            temporary = f.name
            f.write(data)
        os.replace(temporary, path)
    except OSError:
        raise ModelError(
            Diagnostic(
                DiagnosticCategory.IO_ERROR,
                "REPORT_IO_ERROR",
                "$",
                "Could not write the local report; no new report is available.",
            )
        ) from None
    finally:
        if temporary is not None:
            Path(temporary).unlink(missing_ok=True)
