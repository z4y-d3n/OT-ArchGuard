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
from otarchguard.explorer_html import CSS, SiteWriter, escape, link, table
from otarchguard.ingestion.project import _no_links
from otarchguard.quality import ReviewQuery, assess_quality, canonical
from otarchguard.reporting import diagram_summary

NOTICE = (
    '<aside class="notice"><h2>Assessment and change legend</h2><p>'
    "+ ADDED · − REMOVED from the proposed model · Δ MODIFIED native declarations. "
    "D DOCUMENTARY evidence · O OWNER DECISION · A EXACT ANALYTICAL result. "
    "? NOT ASSESSED / NOT EVALUATED. Labels carry meaning independently of color. "
    "Quality findings assess explicit requirements and supporting evidence; they do not "
    "measure deployed infrastructure or supply a security score.</p></aside>"
)


def _value(value: object) -> str:
    # Escape bounded chunks, never interpret source markup or source URLs.
    text = canonical(value).decode()
    return (
        "<pre><code>"
        + "".join(escape(text[i : i + 3000]) for i in range(0, len(text), 3000))
        + "</code></pre>"
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
        body = "<h3>" + escape(finding["state"]) + " · " + escape(finding["domain"]) + "</h3>"
        body += "<p>" + escape(finding["explanation"]) + "</p>"
        body += table(
            "Assessment and owner action",
            ("Item", "Value"),
            [
                ("Affected declaration or evidence", _value(finding["entity"])),
                ("Expected condition", _value(finding["expected"])),
                ("Observed condition", _value(finding["actual"])),
                (
                    "Owner action",
                    escape(
                        finding["owner_action"] or "No additional action required by this check."
                    ),
                ),
            ],
        )
        body += "<h3>Exact source references</h3>" + _value(finding["source_references"])
        body += "<h3>Finding identity and limitations</h3>" + _value(
            {
                k: finding[k]
                for k in (
                    "finding_id",
                    "rule_id",
                    "rule_version",
                    "model_sha256",
                    "provenance_sha256",
                    "limitations",
                )
            }
        )
        writer.page(name, finding["rule_id"], body)
        rows.append(
            (
                link(name, finding["rule_id"]),
                escape(finding["state"]),
                escape(finding["domain"]),
                escape(finding["entity"]),
            )
        )
    _index(
        writer,
        prefix,
        title,
        ("Rule", "State", "Domain", "Entity"),
        rows,
        "<h2>Requirement coverage</h2>"
        + _value(report["coverage"])
        + "<p>Model: "
        + escape(report["model_sha256"])
        + " · Assessment: "
        + escape(report["assessment_sha256"])
        + "</p>",
    )
    return rows


def _render_quality(writer: SiteWriter, report: dict[str, Any]) -> None:
    _quality_pages(writer, report, "quality", "Quality findings")
    writer.page(
        "index.html",
        "Architecture quality assessment",
        "<p>"
        + link("quality.html", "Review quality findings and explicit coverage")
        + "</p>"
        + NOTICE
        + _value(
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
        rows.append((link(name, str(result["scope"])),))
    _index(
        writer,
        "analysis",
        "Exact analytical results",
        ("Evaluated query",),
        rows,
        "<p>NOT_EVALUATED: no analytical conclusion exists for any query not listed here.</p>",
    )


def _render_comparison(
    writer: SiteWriter, report: dict[str, Any], baseline: Path, proposed: Path
) -> None:
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
            + escape(report["documentary_status"])
            + ". Documentary lines never establish native transport or permissions.</p>",
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
        svg = spatial_svg(snapshot, summary["mode"] == "summary", escape, namespace=side + "-")
        svg = svg.replace(' stroke-dasharray="8 4"', "")
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
                escape(c["finding_id"]),
                escape(c["classification"]),
                escape(c["baseline_state"]),
                escape(c["proposed_state"]),
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
            "<h3>Query, model bindings, native results and interval deltas</h3>" + _value(result),
        )
        rows.append((link(name, str(result["query"])), escape(result["classification"])))
    _index(
        writer,
        "analysis",
        "Exact analytical comparison",
        ("Query", "State"),
        rows,
        "<p>"
        + escape(report["analytical_status"])
        + ". Queries absent from this table are unassessed. A new edge "
        "alone establishes no reachability delta.</p>",
    )
    writer.page(
        "index.html",
        "Architecture comparison",
        NOTICE
        + _value(
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
        )
        + "<h2>Declared changes and review</h2>"
        + table(
            "Change counts",
            ("Layer", "Changes"),
            [(escape(k), str(len(v))) for k, v in change_rows.items()],
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
            writer.write("assets.css", CSS.encode())
            data = canonical(report)
            writer.write("review.json", data)
            if proposed:
                _render_comparison(writer, report, architecture, proposed)
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
