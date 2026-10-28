"""Human presentation must preserve exact evidence and distinguish unassessed from zero."""

import copy
import json
import re
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import pytest
import yaml

from otarchguard.architecture_comparison import compare_architecture_versions
from otarchguard.diagnostics import ModelError
from otarchguard.explorer import Explorer, generate_explorer
from otarchguard.explorer_data import load_model
from otarchguard.explorer_html import CSS, LEGEND, SiteWriter, audit_site, document, escape
from otarchguard.ingestion.project import create_project
from otarchguard.ingestion.project_review import emit_project
from otarchguard.quality import ReviewQuery, assess_quality, canonical
from otarchguard.review_explorer import (
    _comparison_summary,
    _entity_label,
    _state_label,
    _value,
    generate_review,
)
from tools.synthetic_projects import synthetic_project, tutorial_decisions


class Rendered(HTMLParser):
    """Read emitted text and table cells, independently of renderer helper output."""

    def __init__(self, text: str) -> None:
        super().__init__(convert_charrefs=True)
        self.text: list[str] = []
        self.visible: list[str] = []
        self.links: list[str] = []
        self.tags: list[str] = []
        self.tables: dict[str, list[list[str]]] = {}
        self.caption = ""
        self.in_caption = False
        self.in_cell = False
        self.cell: list[str] = []
        self.row: list[str] = []
        self.rows: list[list[str]] = []
        self.details = 0
        self.in_summary = False
        self.dl_depth = self.max_dl_depth = 0
        self.feed(text)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append(tag)
        if tag == "a":
            self.links.append(dict(attrs)["href"] or "")
        if tag == "details":
            self.details += 1
        if tag == "summary":
            self.in_summary = True
        if tag == "dl":
            self.dl_depth += 1
            self.max_dl_depth = max(self.max_dl_depth, self.dl_depth)
        if tag == "table":
            self.rows, self.caption = [], ""
        if tag == "caption":
            self.in_caption = True
        if tag == "tr":
            self.row = []
        if tag in {"td", "th"}:
            self.in_cell, self.cell = True, []

    def handle_data(self, data: str) -> None:
        self.text.append(data)
        if not self.details or self.in_summary:
            self.visible.append(data)
        if self.in_caption:
            self.caption += data
        if self.in_cell:
            self.cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "details":
            self.details -= 1
        if tag == "summary":
            self.in_summary = False
        if tag == "dl":
            self.dl_depth -= 1
        if tag == "caption":
            self.in_caption = False
        if tag in {"td", "th"}:
            self.in_cell = False
            self.row.append("".join(self.cell))
        if tag == "tr":
            self.rows.append(self.row)
        if tag == "table":
            self.tables[self.caption] = self.rows


def model_file(path: Path, data: dict[str, Any]) -> Path:
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


@pytest.fixture
def models(tmp_path: Path, minimal: dict[str, Any]) -> tuple[Path, Path]:
    # The same public minimal model and transformations used by the installed tutorial.
    before = copy.deepcopy(minimal)
    retired = {**before["assets"][0], "id": "retired", "name": "Retired declaration"}
    before["assets"].append(retired)
    after = copy.deepcopy(before)
    after["assets"] = [a for a in after["assets"] if a["id"] != "retired"]
    after["assets"].append({**retired, "id": "sensor", "name": "New declared sensor"})
    after["zones"].append({**after["zones"][0], "id": "engineering", "name": "Engineering"})
    after["assets"][0]["zone_id"] = "engineering"
    after["interfaces"][0].update(placement_zone_id="engineering", ipv4="192.0.2.30/24")
    after["conduits"] = [
        {
            "id": "engineering-control",
            "name": "Declared crossing",
            "purpose": "Fictional crossing",
            "common_security_needs": "Owner context",
            "zone_ids": ["engineering", "control"],
        }
    ]
    after["transport_edges"][0]["conduit_id"] = "engineering-control"
    after["rules"] = []
    return model_file(tmp_path / "before.yaml", before), model_file(tmp_path / "after.yaml", after)


@pytest.fixture
def documentary_versions(tmp_path: Path) -> list[Path]:
    manifest = synthetic_project(tmp_path / "documents", count=4, contradictory=False)
    paths = []
    for version in ("before", "after"):
        if version == "after":
            graph = tmp_path / "documents/topology.drawio"
            graph.write_text(
                graph.read_text(encoding="utf-8").replace(
                    "</root>",
                    '<mxCell id="extra-arrow" edge="1" parent="1" source="n0" target="n1"/></root>',
                ),
                encoding="utf-8",
            )
        draft = create_project(manifest)
        accepted = tmp_path / version
        accepted.mkdir()
        for name, data in emit_project(draft, tutorial_decisions(draft), manifest).items():
            (accepted / name).write_bytes(data)
        paths.append(accepted)
    return paths


def comparison_site(paths: list[Path], output: Path, same: bool = False) -> dict[str, Any]:
    before, after = paths[0], paths[0] if same else paths[1]
    result = generate_review(
        before / "architecture.yaml",
        output,
        proposed=after / "architecture.yaml",
        provenance=before / "architecture.provenance.json",
        proposed_provenance=after / "architecture.provenance.json",
    )
    assert result["site"]["broken_links"] == 0
    report = json.loads((output / "review.json").read_bytes())
    assert isinstance(report, dict)
    return report


def test_unassessed_documentary_zero_is_not_presented_as_verified_zero(
    models: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    before, after = models
    query = (ReviewQuery(source_asset_id="eng", service_id="svc_plc"),)
    expected = canonical(compare_architecture_versions(before, after, queries=query))
    output = tmp_path / "comparison"
    generate_review(before, output, proposed=after, queries=query)
    assert (output / "review.json").read_bytes() == expected
    report = json.loads(expected)
    assert sum(c["layer"] == "NATIVE" for c in report["changes"]) == 10
    assert report["documentary_status"] == "NOT_ASSESSED"
    assert report["analytical_status"] == "EVALUATED"
    assert report["quality_baseline"]["analyses"] == []
    assert (
        next(f for f in report["quality_baseline"]["findings"] if f["rule_id"] == "exact-query")[
            "state"
        ]
        == "NOT_ASSESSED"
    )
    assessment_page = Rendered((output / "quality-baseline.html").read_text(encoding="utf-8"))
    assert "their own query scope" in "".join(assessment_page.visible)
    assert "analysis.html" in assessment_page.links
    page = Rendered((output / "index.html").read_text(encoding="utf-8"))
    assert page.tables["Compared layers"][1:] == [
        ["Native declarations", "Compared", "10"],
        ["Documentary evidence", "Not assessed", "Not assessed"],
        ["Owner decisions", "Not assessed", "Not assessed"],
    ]
    assert "not a verified zero" in "".join(page.visible)
    assert "Exact analysis: Evaluated" in "".join(page.visible)
    for name in ("evidence.html", "decisions.html"):
        assert "zero changes are not verified" in (output / name).read_text(encoding="utf-8")
    assert "review.json" in page.links and audit_site(output)["broken_links"] == 0


def test_documentary_only_changes_preserve_native_zero_and_unevaluated_analysis(
    documentary_versions: list[Path],
    tmp_path: Path,
) -> None:
    output = tmp_path / "comparison"
    report = comparison_site(documentary_versions, output)
    assert report["baseline_model_sha256"] == report["proposed_model_sha256"]
    assert report["documentary_status"] == "COMPARED"
    assert report["analytical_status"] == "NOT_EVALUATED"
    page = Rendered((output / "index.html").read_text(encoding="utf-8"))
    assert page.tables["Compared layers"][1:] == [
        ["Native declarations", "Compared", "0"],
        ["Documentary evidence", "Compared", "2"],
        ["Owner decisions", "Compared", "1"],
    ]
    assert "Exact analysis: Not evaluated" in "".join(page.visible)
    assert all(
        report[k] in "".join(page.text)
        for k in ["baseline_model_sha256", "proposed_model_sha256", "comparison_sha256"]
    )


def test_true_compared_zero_is_retained(
    documentary_versions: list[Path],
    tmp_path: Path,
) -> None:
    output = tmp_path / "same"
    report = comparison_site(documentary_versions, output, same=True)
    assert report["changes"] == [] and report["documentary_status"] == "COMPARED"
    rows = Rendered((output / "index.html").read_text(encoding="utf-8")).tables["Compared layers"]
    assert rows[1:] == [
        ["Native declarations", "Compared", "0"],
        ["Documentary evidence", "Compared", "0"],
        ["Owner decisions", "Compared", "0"],
    ]


def test_evaluated_no_native_delta_still_does_not_assess_documentary_layer(
    models: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    model = models[0]
    output = tmp_path / "same"
    generate_review(
        model,
        output,
        proposed=model,
        queries=(ReviewQuery(source_asset_id="eng", service_id="svc_plc"),),
    )
    page = Rendered((output / "index.html").read_text(encoding="utf-8"))
    assert page.tables["Compared layers"][1][2] == "0"
    assert page.tables["Compared layers"][2][2] == "Not assessed"
    assert "Exact analysis: Evaluated" in "".join(page.visible)


@pytest.mark.parametrize(
    "mutation",
    [
        "missing-documentary",
        "null-documentary",
        "unknown-documentary",
        "nonstring-documentary",
        "missing-analytical",
        "missing-changes",
        "null-changes",
        "unknown-layer",
        "unassessed-with-evidence",
        "unassessed-with-decision",
        "evaluated-without-query",
        "partial-without-query",
        "unevaluated-with-query",
        "compared-without-bindings",
    ],
)
def test_inconsistent_or_missing_comparison_report_never_renders_verified_zero(
    models: tuple[Path, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    report = compare_architecture_versions(*models)
    if mutation == "missing-documentary":
        del report["documentary_status"]
    elif mutation == "null-documentary":
        report["documentary_status"] = None
    elif mutation == "unknown-documentary":
        report["documentary_status"] = "UNKNOWN"
    elif mutation == "nonstring-documentary":
        report["documentary_status"] = []
    elif mutation == "missing-analytical":
        del report["analytical_status"]
    elif mutation == "missing-changes":
        del report["changes"]
    elif mutation == "null-changes":
        report["changes"] = None
    elif mutation == "unknown-layer":
        report["changes"][0]["layer"] = "UNKNOWN"
    elif mutation == "unassessed-with-evidence":
        report["changes"][0]["layer"] = "DOCUMENTARY"
    elif mutation == "unassessed-with-decision":
        report["changes"][0]["layer"] = "OWNER_DECISION"
    elif mutation == "evaluated-without-query":
        report["analytical_status"] = "EVALUATED"
    elif mutation == "partial-without-query":
        report["analytical_status"] = "PARTIALLY_EVALUATED"
    elif mutation == "unevaluated-with-query":
        report["analytical_results"] = [{"query": "not evaluated"}]
    elif mutation == "compared-without-bindings":
        report["documentary_status"] = "COMPARED"
    frozen = copy.deepcopy(report)
    with pytest.raises(ModelError) as summary_error:
        _comparison_summary(report)
    assert summary_error.value.diagnostics[0].code == "REVIEW_REPORT"
    assert report == frozen
    monkeypatch.setattr(
        "otarchguard.review_explorer.compare_architecture_versions", lambda *a, **kw: report
    )
    target = tmp_path / "rejected"
    with pytest.raises(ModelError) as publication_error:
        generate_review(models[0], target, proposed=models[1])
    assert publication_error.value.diagnostics[0].code == "REVIEW_REPORT"
    assert not target.exists() and not list(tmp_path.glob(".otarchguard-review-*"))


@pytest.mark.parametrize(
    "state,label",
    [
        ("SATISFIED", "Satisfied"),
        ("MISSING_REQUIRED_INFORMATION", "Missing required information"),
        ("NOT_ASSESSED", "Not assessed"),
        ("NOT_APPLICABLE", "Not applicable"),
        ("NOT_DOCUMENTED", "Not documented"),
        ("CONTRADICTORY_EVIDENCE", "Contradictory evidence"),
        ("REVIEW_REQUIRED", "Review required"),
        ("UNSUPPORTED", "Unsupported"),
    ],
)
def test_quality_state_labels_do_not_promote_unknown_states(state: str, label: str) -> None:
    assert _state_label(state) == label
    assert _state_label("UNRECOGNIZED") == "Unrecognized state: UNRECOGNIZED"
    assert "Unrecognized" in _state_label(None)


@pytest.mark.parametrize(
    "entity,label",
    [
        (["assets", "plc", None], "Asset: plc"),
        (["assets", "plc", "role"], "Asset: plc · Field: role"),
        (["assets", "plc", ""], 'Asset: plc · Field: ""'),
        (["sources", "drawing"], "Source: drawing"),
        ("model", "Model"),
        (None, "null"),
        (["unknown", "id", None], '[\n  "unknown",\n  "id",\n  null\n]'),
    ],
)
def test_entity_labels_preserve_field_distinctions(entity: object, label: str) -> None:
    assert _entity_label(entity) == label


def test_quality_summary_and_findings_preserve_exact_metadata(
    models: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    model = models[0]
    profile = tmp_path / "profile.json"
    profile.write_text(
        json.dumps(
            {
                "profile_version": 1,
                "model_sha256": load_model(model).sha256,
                "context": "Fictional owner requirement",
                "requirements": [
                    {
                        "id": "asset-documentation",
                        "expectation": "ENTITY_PROVENANCE",
                        "entity_kind": "assets",
                        "entity_ids": ["*"],
                        "rationale": "Missing evidence is not a vulnerability.",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    expected = assess_quality(model, profile=profile)
    first, second = tmp_path / "first", tmp_path / "second"
    for output in [first, second]:
        generate_review(model, output, profile=profile)
    assert (first / "review.json").read_bytes() == canonical(expected)
    assert {p.name: p.read_bytes() for p in first.iterdir()} == {
        p.name: p.read_bytes() for p in second.iterdir()
    }
    overview = Rendered((first / "index.html").read_text(encoding="utf-8"))
    assert "review.json" in overview.links
    assert overview.tables["Explicit requirement coverage"][1] == [
        "asset-documentation",
        "Assessed",
        "0",
        "3",
        "0",
    ]
    findings = Rendered((first / "quality.html").read_text(encoding="utf-8"))
    assert "Missing required information" in "".join(findings.text)
    assert "Asset: plc" in "".join(findings.text) and "['assets'" not in "".join(findings.text)
    pages = "\n".join(p.read_text(encoding="utf-8") for p in first.glob("*.html"))
    assert "No additional action required by this check" not in pages
    assert "No owner action is specified by this finding." in pages
    details = [
        json.loads(unescape(value))
        for value in re.findall(r"<pre><code>(.*?)</code></pre>", pages, re.S)
    ]
    exact = {
        value["finding_id"]: value
        for value in details
        if isinstance(value, dict) and "finding_id" in value
    }
    assert len(exact) == len(expected["findings"])
    for finding in expected["findings"]:
        assert finding["finding_id"] in pages and finding["state"] in pages
        assert finding["rule_id"] in pages and finding["model_sha256"] in pages
        for key in [
            "entity",
            "state",
            "scope",
            "requirement_id",
            "rule_id",
            "model_sha256",
            "provenance_sha256",
        ]:
            assert exact[finding["finding_id"]][key] == finding[key]
    assert audit_site(first)["broken_links"] == 0


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, "null"),
        (False, "false"),
        (True, "true"),
        (0, "0"),
        ("", '""'),
        ([], "No values recorded."),
    ],
)
def test_null_empty_false_and_zero_remain_distinct(value: object, expected: str) -> None:
    assert "".join(Rendered(_value(value)).text) == expected


def test_nested_properties_keep_links_repeated_values_long_unicode_and_inert_text(
    minimal: dict[str, Any],
    tmp_path: Path,
) -> None:
    model = model_file(tmp_path / "model.yaml", minimal)
    explorer = Explorer(load_model(model), None, SiteWriter(tmp_path, load_model(model).sha256))
    attack = '<script src="https://example.invalid/active">& 控制器</script>'
    values = {
        "name": "Controller",
        "nested": {"service_id": "svc_plc", "deeper": {"empty": None}},
        "repeated": ["same", "same"],
        "long": "界" * 3500,
        "evidence": attack,
    }
    original = copy.deepcopy(values)
    html = explorer.value(values)
    assert explorer.value(values) == html and values == original
    page = Rendered(html)
    assert page.max_dl_depth == 1 and page.dl_depth == 0
    assert "".join(page.text).count("same") == 2 and "界" * 3500 in "".join(page.text)
    assert attack in "".join(page.text) and "script" not in page.tags
    assert explorer.native_paths["services", "svc_plc"] in page.links
    assert page.tags.count("dt") == page.tags.count("dd") == 5
    assert ".compact-fields>div>dt,.compact-fields>div>dd{display:inline" in CSS
    assert ".compact-fields{display:flex" in CSS
    assert "grid-template-columns:fit-content(35%)" not in CSS
    assert "@media(max-width:480px)" in CSS
    output = tmp_path / "native"
    generate_explorer(model, output)
    assert audit_site(output)["broken_links"] == 0


def test_disclosures_preserve_full_identities_and_visible_trust_qualifications() -> None:
    identity = "abcd" * 16
    html = document("Standalone page", "<p>Result</p>", identity).decode()
    page = Rendered(html)
    assert identity in "".join(page.text) and identity not in "".join(page.visible)
    assert identity[:12] + "…" in "".join(page.visible)
    for text in [
        "Documentary evidence is not permission",
        "not evaluated does not mean denied",
        "review sensitive details before sharing",
    ]:
        assert text in "".join(page.visible)
    for text in [
        "drawings do not authorize communication",
        "not physical network truth",
        "Hashes detect changes; they do not authenticate authorship",
        "Unsupported input is an error",
    ]:
        assert text in "".join(page.text)
    assert "details" in page.tags and "summary" in page.tags
    assert "script" not in page.tags and "script-src &#39;none&#39;" in html
    assert LEGEND in html and "title=" not in html


def test_model_only_quality_defines_no_denominator(
    models: tuple[Path, Path], tmp_path: Path
) -> None:
    target = tmp_path / "quality"
    generate_review(models[0], target)
    page = Rendered((target / "index.html").read_text(encoding="utf-8"))
    assert "Only explicit profile requirements define denominators" in "".join(page.visible)
    assert "Explicit requirement coverage" not in page.tables
    assert "100%" not in "".join(page.text)


def test_trace_documentation_qualifies_completed_queries() -> None:
    root = Path(__file__).resolve().parents[1]
    guide = (root / "docs/trace.md").read_text(encoding="utf-8")
    assert "application version string (1.1.0)" not in guide
    readme = (root / "README.md").read_text(encoding="utf-8")
    exit_section = readme[
        readme.index("| Exit | Meaning |") : readme.index("## Examples and technical documentation")
    ]
    assert "Trace exit 0" in exit_section and "unreachable" in exit_section


@pytest.mark.parametrize(
    "text",
    [
        r"C:\Users\Owner\private.txt",
        "C:/Users/Owner/private.txt",
        "file:///C:/Users/Owner/private.txt",
        r"\\server\share\private.txt",
        "/home/owner/private.txt",
        "/Users/Owner/private.txt",
        "/tmp/private.txt",
        r"Source path: C:\Users\Owner\private.txt",
    ],
)
def test_actual_local_paths_remain_withheld(text: str) -> None:
    result = escape(text)
    assert "[local path withheld]" in result and "private.txt" not in result


@pytest.mark.parametrize(
    "text",
    [
        "https://example.invalid/evidence",
        "http://example.invalid/evidence",
        "HTTPS://example.invalid/evidence",
    ],
)
def test_inert_web_evidence_is_not_mistaken_for_a_windows_drive(text: str) -> None:
    assert escape(text) == text


@pytest.mark.parametrize("same_scope", [True, False])
def test_comparison_quality_states_and_full_finding_ids_remain_auditable(
    models: tuple[Path, Path],
    tmp_path: Path,
    same_scope: bool,
) -> None:
    profiles = []
    for side, model in zip(["before", "after"], models, strict=True):
        profile = tmp_path / (side + ".json")
        profile.write_text(
            json.dumps(
                {
                    "profile_version": 1,
                    "model_sha256": load_model(model).sha256,
                    "context": "Fictional explicit requirement",
                    "requirements": [
                        {
                            "id": "eng-zone" if same_scope else side + "-zone",
                            "expectation": "DECLARED_VALUE",
                            "entity_kind": "assets",
                            "entity_ids": ["eng"],
                            "field": "zone_id",
                            "expected_value": "control",
                            "rationale": "Declared information only; no vulnerability claim.",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        profiles.append(profile)
    expected = compare_architecture_versions(
        *models, baseline_profile=profiles[0], proposed_profile=profiles[1]
    )
    output = tmp_path / "comparison"
    generate_review(
        models[0], output, proposed=models[1], profile=profiles[0], proposed_profile=profiles[1]
    )
    assert (output / "review.json").read_bytes() == canonical(expected)
    page = Rendered((output / "quality.html").read_text(encoding="utf-8"))
    rows = page.tables["Quality changes"][1:]
    assert len(rows) == len(expected["quality_changes"]) > 0
    for row, change in zip(rows, expected["quality_changes"], strict=True):
        assert change["finding_id"] in row[0]
        assert row[2] == (
            _state_label(change["baseline_state"])
            if change["baseline_state"] is not None
            else "Not present"
        )
        assert row[3] == (
            _state_label(change["proposed_state"])
            if change["proposed_state"] is not None
            else "Not present"
        )
    if same_scope:
        assert any(row[2:] == ["Satisfied", "Missing required information"] for row in rows)
    else:
        assert any("Not present" in row[2:] for row in rows)
    assert audit_site(output)["broken_links"] == 0


@pytest.mark.parametrize(
    "case,status,counts",
    [
        ("missing-both", "NOT_EVALUATED", ["1", "0", "0"]),
        ("self-only", "NOT_EVALUATED", ["1", "0", "0"]),
        ("missing-proposed", "PARTIALLY_EVALUATED", ["1", "1", "0"]),
        ("missing-baseline", "PARTIALLY_EVALUATED", ["1", "0", "1"]),
        ("mixed", "PARTIALLY_EVALUATED", ["2", "1", "1"]),
        ("changed-protocol", "EVALUATED", ["1", "1", "1"]),
    ],
)
def test_requested_queries_are_distinct_from_completed_per_side_results(
    minimal: dict[str, Any],
    tmp_path: Path,
    case: str,
    status: str,
    counts: list[str],
) -> None:
    before_data, after_data = copy.deepcopy(minimal), copy.deepcopy(minimal)
    queries: tuple[ReviewQuery, ...] = (ReviewQuery(source_asset_id="eng", service_id="svc_plc"),)
    if case == "missing-both":
        queries = (ReviewQuery(source_asset_id="missing", service_id="absent"),)
    elif case == "self-only":
        queries = (ReviewQuery(source_asset_id="plc", service_id="svc_plc"),)
    elif case in {"missing-proposed", "missing-baseline"}:
        unavailable = after_data if case == "missing-proposed" else before_data
        unavailable.update(services=[], intents=[], scenarios=[])
    elif case == "mixed":
        queries += (ReviewQuery(source_asset_id="missing", service_id="absent"),)
    elif case == "changed-protocol":
        after_data["services"][0]["protocol"] = "udp"
        after_data["rules"][0]["protocol"] = "udp"
    before = model_file(tmp_path / "before.yaml", before_data)
    after = model_file(tmp_path / "after.yaml", after_data)
    expected = compare_architecture_versions(before, after, queries=queries)
    assert expected["analytical_status"] == status
    assert any(a["classification"] == "NOT_COMPARABLE" for a in expected["analytical_results"])
    output = tmp_path / "comparison"
    generate_review(before, output, proposed=after, queries=queries)
    assert (output / "review.json").read_bytes() == canonical(expected)
    for filename in ["index.html", "analysis.html"]:
        view = Rendered((output / filename).read_text(encoding="utf-8"))
        assert view.tables["Exact analysis coverage"][1] == counts
        assert _state_label(status) in "".join(view.visible)
        assert "not a denied query" in "".join(view.visible)
        assert "No analytical comparison was requested" not in "".join(view.text)
    assert audit_site(output)["broken_links"] == 0
