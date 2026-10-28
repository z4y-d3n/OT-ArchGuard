"""Compact assessment/comparison views using the existing offline Explorer boundary."""

import os
import tempfile
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from otarchguard.architecture_comparison import compare_architecture_versions
from otarchguard.comparison import declaration_catalogs
from otarchguard.diagnostics import fail
from otarchguard.diagrams import spatial_svg
from otarchguard.explorer_data import load_model, page_id
from otarchguard.explorer_html import (
    COMPACT_CSS,
    CSS,
    SiteWriter,
    compact_value,
    escape,
    identity_details,
    link,
    properties,
    table,
)
from otarchguard.ingestion.project import _no_links
from otarchguard.quality import ReviewQuery, assess_quality, canonical
from otarchguard.reporting import diagram_summary

NOTICE = (
    '<aside class="notice"><p>Quality findings assess requirements and evidence, '
    "not deployed security. Missing information is not a vulnerability; documentary "
    "changes do not establish network permission.</p>"
    "<details><summary>Assessment and change legend</summary><p>"
    "+ ADDED · − REMOVED from the proposed model · Δ MODIFIED native declarations. "
    "D DOCUMENTARY evidence · O OWNER DECISION · A EXACT ANALYTICAL result. "
    "? NOT ASSESSED / NOT EVALUATED. Labels carry meaning independently of color. "
    "Quality findings assess explicit requirements and supporting evidence; they do not "
    "measure deployed infrastructure or supply a security score.</p></details></aside>"
)

STATE_LABELS = {
    "ASSESSED": "Assessed",
    "SATISFIED": "Satisfied",
    "MISSING_REQUIRED_INFORMATION": "Missing required information",
    "CONTRADICTORY_EVIDENCE": "Contradictory evidence",
    "REVIEW_REQUIRED": "Review required",
    "NOT_DOCUMENTED": "Not documented",
    "NOT_ASSESSED": "Not assessed",
    "NOT_APPLICABLE": "Not applicable",
    "UNSUPPORTED": "Unsupported",
    "COMPARED": "Compared",
    "EVALUATED": "Evaluated",
    "PARTIALLY_EVALUATED": "Partially evaluated",
    "NOT_EVALUATED": "Not evaluated",
}
ENTITY_LABELS = {
    "assets": "Asset",
    "zones": "Zone",
    "interfaces": "Interface",
    "conduits": "Conduit",
    "transport_edges": "Transport edge",
    "forwarding_edges": "Forwarding edge",
    "services": "Service",
    "rules": "Rule",
    "intents": "Intent",
    "scenarios": "Scenario",
    "sources": "Source",
    "access_points": "Access point",
    "external_dependencies": "External dependency",
}


def _state_label(value: object) -> str:
    return STATE_LABELS.get(str(value), "Unrecognized state: " + str(value))


def _entity_label(value: object) -> str:
    if value == "model":
        return "Model"
    if isinstance(value, (list, tuple)):
        if len(value) in {2, 3} and isinstance(value[0], str) and value[0] in ENTITY_LABELS:
            text = ENTITY_LABELS[value[0]] + ": " + str(value[1])
            if len(value) == 3 and value[2] is not None:
                text += " · Field: " + (str(value[2]) if value[2] != "" else '""')
            return text
        return canonical(value).decode().strip()
    return "null" if value is None else str(value)


def _query_label(value: object) -> str:
    if isinstance(value, dict) and "source_asset_id" in value and "service_id" in value:
        return (
            "Source: " + str(value["source_asset_id"]) + " · Service: " + str(value["service_id"])
        )
    return canonical(value).decode().strip()


def _json_value(value: object) -> str:
    # Escape bounded chunks, never interpret source markup or source URLs.
    text = canonical(value).decode()
    return (
        "<pre><code>"
        + "".join(escape(text[i : i + 3000]) for i in range(0, len(text), 3000))
        + "</code></pre>"
    )


def _value(value: object) -> str:
    """Readable values retain nesting, every item and inert source text."""
    if isinstance(value, dict):
        return properties([(k.replace("_", " "), _value(v)) for k, v in sorted(value.items())])
    if isinstance(value, (list, tuple)):
        return (
            "<ul>" + "".join("<li>" + _value(v) + "</li>" for v in value) + "</ul>"
            if value
            else '<p class="muted">No values recorded.</p>'
        )
    if value is None:
        return "<code>null</code>"
    if isinstance(value, bool):
        return "true" if value else "false"
    text = str(value)
    return (
        "".join(escape(text[i : i + 3000]) for i in range(0, len(text), 3000))
        if text
        else '<code>""</code>'
    )


def _technical(value: object) -> str:
    return "<details><summary>Exact technical details</summary>" + _json_value(value) + "</details>"


def _coverage(report: dict[str, Any]) -> str:
    if not report["coverage"]:
        return (
            "<p>No requirement coverage is reported. Only explicit profile requirements "
            "define denominators; no completeness or security percentage is implied.</p>"
        )
    return (
        table(
            "Explicit requirement coverage",
            ("Requirement", "Assessment", "Satisfied", "Required", "Excluded"),
            [
                (
                    escape(c["requirement_id"]),
                    escape(_state_label(c["state"])),
                    str(c["satisfied"]),
                    str(c["required"]),
                    str(len(c["excluded"])),
                )
                for c in report["coverage"]
            ],
        )
        + "<p>Counts apply only to each recorded requirement scope. An empty scope is not "
        "a satisfied requirement. Coverage is not a security score.</p>"
    )


def _comparison_summary(report: dict[str, Any]) -> list[tuple[str, ...]]:
    documentary = report.get("documentary_status")
    analytical = report.get("analytical_status")
    changes, analyses = report.get("changes"), report.get("analytical_results")
    if not isinstance(changes, list) or not isinstance(analyses, list):
        fail("REVIEW_REPORT", "$", "Missing or inconsistent comparison state; no report accepted.")
    invalid = (
        not isinstance(documentary, str)
        or documentary not in {"COMPARED", "NOT_ASSESSED"}
        or not isinstance(analytical, str)
        or analytical not in {"EVALUATED", "PARTIALLY_EVALUATED", "NOT_EVALUATED"}
    )
    if invalid:
        fail("REVIEW_REPORT", "$", "Missing or inconsistent comparison state; no report accepted.")
    counts = {"NATIVE": 0, "DOCUMENTARY": 0, "OWNER_DECISION": 0}
    for change in changes:
        if (
            not isinstance(change, dict)
            or not isinstance(change.get("layer"), str)
            or change["layer"] not in counts
        ):
            fail("REVIEW_REPORT", "$", "Unknown comparison layer; no report accepted.")
        counts[change["layer"]] += 1
    if (documentary == "NOT_ASSESSED" and (counts["DOCUMENTARY"] or counts["OWNER_DECISION"])) or (
        documentary == "COMPARED"
        and not all(report.get(side + "_provenance_sha256") for side in ("baseline", "proposed"))
    ):
        fail(
            "REVIEW_REPORT",
            "$",
            "Inconsistent comparison evidence or evaluation; no report accepted.",
        )
    _analysis_counts(report)
    return [
        ("Native declarations", "Compared", str(counts["NATIVE"])),
        (
            "Documentary evidence",
            _state_label(documentary),
            str(counts["DOCUMENTARY"]) if documentary == "COMPARED" else "Not assessed",
        ),
        (
            "Owner decisions",
            _state_label(documentary),
            str(counts["OWNER_DECISION"]) if documentary == "COMPARED" else "Not assessed",
        ),
    ]


def _analysis_counts(report: dict[str, Any]) -> tuple[int, int, int]:
    records = report.get("analytical_results")
    if not isinstance(records, list):
        fail("REVIEW_REPORT", "$", "Missing analytical records; no report accepted.")
    completed = {"baseline": 0, "proposed": 0}
    for record in records:
        if (
            not isinstance(record, dict)
            or not isinstance(record.get("query"), dict)
            or not isinstance(record.get("classification"), str)
            or any(side not in record for side in completed)
        ):
            fail("REVIEW_REPORT", "$", "Incomplete analytical record; no report accepted.")
        for side in completed:
            result = record[side]
            if result is None:
                if record["classification"] != "NOT_COMPARABLE":
                    fail("REVIEW_REPORT", "$", "Unavailable comparison side; no report accepted.")
                continue
            if (
                not isinstance(result, dict)
                or result.get("status") != "complete"
                or result.get("model_sha256") != report.get(side + "_model_sha256")
            ):
                fail(
                    "REVIEW_REPORT", "$", "Unbound or incomplete native result; no report accepted."
                )
            completed[side] += 1
    expected = (
        "EVALUATED"
        if records and completed["baseline"] == completed["proposed"] == len(records)
        else "PARTIALLY_EVALUATED"
        if any(completed.values())
        else "NOT_EVALUATED"
    )
    if report.get("analytical_status") != expected:
        fail("REVIEW_REPORT", "$", "Inconsistent analytical status; no report accepted.")
    return len(records), completed["baseline"], completed["proposed"]


def _analysis_summary(report: dict[str, Any]) -> str:
    requested, before, after = _analysis_counts(report)
    explanation = (
        "No exact queries were requested."
        if not requested
        else "Requested queries were unavailable or unsupported on both model sides."
        if not before and not after
        else "Some model sides were not evaluated; inspect the per-query reasons and results."
        if before < requested or after < requested
        else "Inspect each record for its exact scope and whether results are comparable."
    )
    return (
        "<p>Exact analysis: "
        + escape(_state_label(report["analytical_status"]))
        + ".</p>"
        + table(
            "Exact analysis coverage",
            ("Requested query records", "Baseline evaluated", "Proposed evaluated"),
            [(str(requested), str(before), str(after))],
        )
        + "<p>"
        + explanation
        + " Unavailable or not comparable is not a denied query. "
        "Other queries remain unassessed.</p>"
    )


def _index(
    writer: SiteWriter,
    name: str,
    title: str,
    headings: tuple[str, ...],
    rows: Sequence[tuple[str, ...]],
    preface: str = "",
) -> None:
    pages = max(1, (len(rows) + 59) // 60)
    for number in range(pages):
        filename = name + ("" if number == 0 else f"-{number + 1}") + ".html"
        navigation = (
            "<p>"
            + " · ".join(
                link(name + ("" if n == 0 else f"-{n + 1}") + ".html", f"Page {n + 1}")
                for n in range(pages)
            )
            + "</p>"
        )
        writer.page(
            filename,
            title,
            preface
            + navigation
            + table(title, headings, rows[number * 60 : (number + 1) * 60])
            + NOTICE,
        )


def _quality_pages(
    writer: SiteWriter, report: dict[str, Any], prefix: str, title: str
) -> list[tuple[str, ...]]:
    rows: list[tuple[str, ...]] = []
    for finding in report["findings"]:
        name = page_id("finding", [prefix, finding["finding_id"]]) + ".html"
        body = (
            "<h3>"
            + escape(_state_label(finding["state"]))
            + " · "
            + escape(finding["domain"].replace("_", " ").capitalize())
            + "</h3>"
        )
        body += "<p>" + escape(finding["explanation"]) + "</p>"
        body += table(
            "Assessment and owner action",
            ("Item", "Value"),
            [
                ("Affected declaration or evidence", escape(_entity_label(finding["entity"]))),
                ("Expected condition", _value(finding["expected"])),
                ("Observed condition", _value(finding["actual"])),
                (
                    "Owner action",
                    escape(
                        finding["owner_action"] or "No owner action is specified by this finding."
                    ),
                ),
            ],
        )
        body += "<h3>Exact source references</h3>" + _value(finding["source_references"])
        body += "<h3>Finding identity and limitations</h3>" + _technical(
            {
                k: finding[k]
                for k in (
                    "finding_id",
                    "state",
                    "entity",
                    "scope",
                    "requirement_id",
                    "rule_id",
                    "rule_version",
                    "model_sha256",
                    "provenance_sha256",
                    "limitations",
                )
            }
        )
        writer.page(name, finding["rule_id"], body + NOTICE)
        rows.append(
            (
                link(name, finding["rule_id"]),
                escape(_state_label(finding["state"])),
                escape(finding["domain"]),
                escape(_entity_label(finding["entity"])),
            )
        )
    _index(
        writer,
        prefix,
        title,
        ("Rule", "State", "Domain", "Entity"),
        rows,
        "<h2>Requirement coverage</h2>"
        + _coverage(report)
        + (
            "<p>These per-model quality assessments have their own query scope. "
            "Selected comparison queries are reported separately in "
            + link("analysis.html", "Exact comparison analysis")
            + ".</p>"
            if prefix in {"quality-baseline", "quality-proposed"}
            else ""
        )
        + _technical({k: report[k] for k in ("model_sha256", "assessment_sha256")}),
    )
    return rows


def _render_quality(writer: SiteWriter, report: dict[str, Any]) -> None:
    _quality_pages(writer, report, "quality", "Quality findings")
    states = sorted({finding["state"] for finding in report["findings"]})
    writer.page(
        "index.html",
        "Architecture quality assessment",
        "<p>"
        + link("quality.html", "Review quality findings and explicit coverage")
        + "</p>"
        + "<h2>Reported finding outcomes</h2>"
        + table(
            "Finding states",
            ("State", "Reported findings"),
            [
                (
                    escape(_state_label(state)),
                    str(sum(f["state"] == state for f in report["findings"])),
                )
                for state in states
            ],
        )
        + _coverage(report)
        + "<p>Explicitly evaluated queries: "
        + str(len(report["analyses"]))
        + ". Queries absent from the analytical results are not evaluated.</p>"
        + NOTICE
        + '<p><a href="review.json">Canonical assessment JSON</a></p>'
        + _technical(
            {
                k: report[k]
                for k in (
                    "model_sha256",
                    "provenance_sha256",
                    "profile_sha256",
                    "assessment_sha256",
                    "limitations",
                )
            }
        ),
    )
    rows = []
    for result in report["analyses"]:
        name = page_id("record", ["quality-analysis", result["scope"]]) + ".html"
        writer.page(name, "Exact evaluated query", "<h3>Native engine result</h3>" + _value(result))
        rows.append((link(name, _query_label(result["scope"])),))
    _index(
        writer,
        "analysis",
        "Exact analytical results",
        ("Evaluated query",),
        rows,
        "<p>NOT_EVALUATED: no analytical conclusion exists for any query not listed here.</p>",
    )


def _render_comparison(
    writer: SiteWriter,
    report: dict[str, Any],
    baseline: Path,
    proposed: Path,
    *,
    compact_prototype: bool = False,
) -> None:
    layer_summary = _comparison_summary(report)
    change_rows: dict[str, list[tuple[str, ...]]] = {
        k: [] for k in ("native", "evidence", "decisions")
    }
    for change in report["changes"]:
        name = page_id("change", change["change_id"]) + ".html"
        body = "<h3>Exact change</h3>" + _value(
            {k: v for k, v in change.items() if k not in {"baseline", "proposed"}}
        )
        if change["fields"]:
            body += table(
                "Changed native fields",
                ("Field", "Meaning", "Baseline", "Proposed"),
                [
                    (
                        escape(f["field"]),
                        escape(f["classification"]),
                        _value(f["baseline"]),
                        _value(f["proposed"]),
                    )
                    for f in change["fields"]
                ],
            )
        body += "<h3>Baseline declaration or observation</h3>" + _value(change["baseline"])
        body += "<h3>Proposed declaration or observation</h3>" + _value(change["proposed"])
        writer.page(name, change["layer"] + " · " + change["action"], body)
        target = (
            "native"
            if change["layer"] == "NATIVE"
            else "decisions"
            if change["layer"] == "OWNER_DECISION"
            else "evidence"
        )
        change_rows[target].append(
            (link(name, change["action"]), escape(change["entity_kind"]), escape(change["entity"]))
        )
    for name, rows in change_rows.items():
        _index(
            writer,
            name,
            name.capitalize() + " changes",
            ("Action", "Collection", "Identity"),
            rows,
            "<p>Documentary status: "
            + escape(_state_label(report["documentary_status"]))
            + ". "
            + (
                "No documentary comparison was performed; zero changes are not verified. "
                if report["documentary_status"] == "NOT_ASSESSED" and name != "native"
                else ""
            )
            + "Documentary lines never establish native transport or permissions.</p>",
        )
    # Shared record views contain both exact versions. No duplicate complete Explorer sites.
    before_model, after_model = load_model(baseline), load_model(proposed)
    left = declaration_catalogs(before_model)
    right = declaration_catalogs(after_model)
    for side, catalogs, snapshot in (
        ("baseline", left, before_model),
        ("proposed", right, after_model),
    ):
        rows = []
        for kind in sorted(catalogs):
            for identity, _declaration in sorted(catalogs[kind].items()):
                name = page_id("record", ["native", kind, identity]) + ".html"
                if name not in writer.pending:
                    before = left[kind].get(identity)
                    after = right[kind].get(identity)
                    writer.page(
                        name,
                        kind + " · " + identity,
                        "<h3>Baseline native declaration</h3>"
                        + _value(before.model_dump(mode="json") if before else None)
                        + "<h3>Proposed native declaration</h3>"
                        + _value(after.model_dump(mode="json") if after else None)
                        + "<p>Same-ID view; explicit rename/reuse correspondence remains in "
                        "the change record.</p>",
                    )
                rows.append((escape(kind), link(name, identity)))
        summary = diagram_summary(snapshot)
        svg = spatial_svg(
            snapshot,
            summary["mode"] == "summary",
            escape,
            namespace=side + "-",
            forwarding_dashed=False,
        )
        diagram = (
            '<h2>Declared architecture</h2><figure><div class="scroll" tabindex="0" '
            'role="region" aria-label="Declared architecture diagram">'
            + svg
            + "</div><figcaption>"
            + escape(summary["legend"])
            + "</figcaption></figure>"
        )
        diagram += (
            "<p>Diagram mode: "
            + escape(summary["mode"])
            + ". Complete textual declarations follow.</p>"
        )
        _index(
            writer,
            side,
            side.capitalize() + " declarations",
            ("Collection", "Declared entity"),
            rows,
            "<p>Model SHA-256: " + escape(report[side + "_model_sha256"]) + "</p>" + diagram,
        )
    _quality_pages(
        writer, report["quality_baseline"], "quality-baseline", "Baseline quality findings"
    )
    _quality_pages(
        writer, report["quality_proposed"], "quality-proposed", "Proposed quality findings"
    )
    _index(
        writer,
        "quality",
        "Quality changes",
        ("Finding", "Classification", "Baseline", "Proposed"),
        [
            (
                identity_details("Finding identity", c["finding_id"]),
                escape(c["classification"].replace("_", " ").capitalize()),
                escape(_state_label(c["baseline_state"]))
                if c["baseline_state"] is not None
                else "Not present",
                escape(_state_label(c["proposed_state"]))
                if c["proposed_state"] is not None
                else "Not present",
            )
            for c in report["quality_changes"]
        ],
        "<p>"
        + link("quality-baseline.html", "Baseline assessment")
        + " · "
        + link("quality-proposed.html", "Proposed assessment")
        + "</p><p>A missing rule or changed scope never resolves a finding.</p>",
    )
    rows = []
    for result in report["analytical_results"]:
        name = page_id("record", ["analysis", result["query"]]) + ".html"
        writer.page(
            name,
            "Exact analytical comparison",
            "<h3>Query, model bindings, native results and interval deltas</h3>"
            + (
                compact_value(result, lambda value, _: _value(value), sort_keys=True)
                if compact_prototype
                else _value(result)
            ),
        )
        rows.append(
            (
                link(name, _query_label(result["query"])),
                escape(result["classification"].replace("_", " ").capitalize()),
            )
        )
    _index(
        writer,
        "analysis",
        "Exact analytical comparison",
        ("Query", "State"),
        rows,
        _analysis_summary(report) + "<p>Queries absent from this table are unassessed. A new edge "
        "alone establishes no reachability delta.</p>",
    )
    writer.page(
        "index.html",
        "Architecture comparison",
        "<h2>Comparison scope and outcomes</h2>"
        + table("Compared layers", ("Layer", "Assessment", "Changes"), layer_summary)
        + _analysis_summary(report)
        + (
            "<p>Documentary comparison requires both bound provenance records. "
            "Not assessed is not a verified zero.</p>"
            if report["documentary_status"] == "NOT_ASSESSED"
            else ""
        )
        + NOTICE
        + '<p><a href="review.json">Canonical comparison JSON</a></p>'
        + _technical(
            {
                k: report[k]
                for k in (
                    "baseline_model_sha256",
                    "proposed_model_sha256",
                    "comparison_sha256",
                    "baseline_provenance_sha256",
                    "proposed_provenance_sha256",
                    "analytical_status",
                    "documentary_status",
                    "limitations",
                )
            }
        ),
    )


def generate_review(
    architecture: Path,
    output: Path,
    *,
    proposed: Path | None = None,
    provenance: Path | None = None,
    proposed_provenance: Path | None = None,
    profile: Path | None = None,
    proposed_profile: Path | None = None,
    mapping: Path | None = None,
    queries: tuple[ReviewQuery, ...] = (),
    compact_prototype: bool = False,
) -> dict[str, Any]:
    """Publish JSON and static human views as one bounded, audited fresh directory."""
    started = time.perf_counter()
    _no_links(output)
    if output.exists():
        fail("REVIEW_OUTPUT", "$", "Output already exists; choose a fresh directory.")
    if proposed:
        report = compare_architecture_versions(
            architecture,
            proposed,
            baseline_provenance=provenance,
            proposed_provenance=proposed_provenance,
            baseline_profile=profile,
            proposed_profile=proposed_profile,
            mapping=mapping,
            queries=queries,
        )
        navigation = tuple(
            (n + ".html", label)
            for n, label in (
                ("index", "Comparison overview"),
                ("baseline", "Baseline"),
                ("proposed", "Proposed"),
                ("native", "Native changes"),
                ("evidence", "Documentary changes"),
                ("decisions", "Owner decisions"),
                ("quality", "Quality findings"),
                ("analysis", "Exact analysis"),
            )
        )
        model_hash = report["proposed_model_sha256"]
        identity = report["comparison_sha256"]
    else:
        report = assess_quality(
            architecture, provenance=provenance, profile=profile, queries=queries
        )
        navigation = (
            ("index.html", "Assessment overview"),
            ("quality.html", "Quality findings"),
            ("analysis.html", "Exact analysis"),
        )
        model_hash = report["model_sha256"]
        identity = report["assessment_sha256"]
    evaluated = time.perf_counter()
    try:
        with tempfile.TemporaryDirectory(
            dir=output.absolute().parent, prefix=".otarchguard-review-"
        ) as temporary:
            stage = Path(temporary)
            writer = SiteWriter(
                stage,
                model_hash,
                navigation,
                json_bytes=32 * 1024 * 1024,
                model_context=(
                    "baseline "
                    + report["baseline_model_sha256"]
                    + "; proposed "
                    + report["proposed_model_sha256"]
                )
                if proposed
                else None,
            )
            writer.write("assets.css", (CSS + (COMPACT_CSS if compact_prototype else "")).encode())
            data = canonical(report)
            writer.write("review.json", data)
            if proposed:
                _render_comparison(
                    writer, report, architecture, proposed, compact_prototype=compact_prototype
                )
            else:
                _render_quality(writer, report)
            result = writer.finish(
                {
                    "review_version": 1,
                    "review_sha256": identity,
                    **(
                        {
                            "baseline_model_sha256": report["baseline_model_sha256"],
                            "proposed_model_sha256": report["proposed_model_sha256"],
                        }
                        if proposed
                        else {}
                    ),
                }
            )
            if output.exists() or output.is_symlink():
                fail("REVIEW_OUTPUT", "$", "Output appeared during publication; refused.")
            os.rename(stage, output)
    except OSError:
        fail("REVIEW_OUTPUT", "$", "Cannot publish complete review output.")
    return {
        "status": "complete",
        "review_sha256": identity,
        "site": {k: v for k, v in result.items() if k not in {"files", "locations"}},
        "timings_seconds": {
            "validation_and_assessment": evaluated - started,
            "rendering_and_audit": time.perf_counter() - evaluated,
            "site_audit": writer.audit_seconds,
            "total": time.perf_counter() - started,
        },
    }
