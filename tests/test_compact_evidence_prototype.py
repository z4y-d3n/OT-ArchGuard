"""Compatibility coverage for prototype API arguments now using production layouts."""

import copy
import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from test_capture_ux_integrity import frozen
from test_historical_explorer_layout import DOM
from test_historical_explorer_render import _fixture, _structural_oracle

from otarchguard.api import validate_file
from otarchguard.architecture_comparison import compare_architecture_versions
from otarchguard.capture.explorer import generate_site
from otarchguard.drift.explorer_bundle import audit_files
from otarchguard.drift.explorer_render import render
from otarchguard.explorer import ExploreOptions, generate_explorer
from otarchguard.explorer_html import COMPACT_CSS, CSS, PageAudit, compact_value, document, escape
from otarchguard.ingestion.project import create_project
from otarchguard.ingestion.project_review import emit_project
from otarchguard.quality import ReviewQuery, canonical
from otarchguard.review_explorer import generate_review
from otarchguard.trace import trace_architecture
from otarchguard.trace_reporting import trace_html, trace_json
from tools.synthetic_projects import synthetic_project, tutorial_decisions

ROOT = Path(__file__).resolve().parents[1]


def leaf(value: object, field: str) -> str:
    return escape("Not recorded" if value is None else value)


def test_simple_fields_have_associated_inline_pairs_without_a_grid() -> None:
    value = {
        "element": "fw",
        "kind": "node",
        "label": "Industrial firewall",
        "parent": "area_b",
        "scope": "page1",
        "source": "topology",
    }
    raw = compact_value(value, leaf)
    dom = DOM(raw.encode()).root
    (fields,) = dom.nodes("dl", "compact-fields")
    assert len(fields.children) == 6
    for node, (key, expected) in zip(fields.children, value.items(), strict=True):
        assert not isinstance(node, str)
        assert [child.tag for child in node.children if not isinstance(child, str)] == ["dt", "dd"]
        assert node.nodes("dt")[0].text == key.capitalize() + ": "
        assert node.nodes("dd")[0].text == expected
    assert not dom.nodes("ul") and not dom.nodes("section") and not dom.nodes("details")
    assert "display:inline" in COMPACT_CSS and "grid" not in COMPACT_CSS
    assert "compact-fields" in CSS


@pytest.mark.parametrize("depth", [1, 3, 8, 24])
def test_deep_objects_preserve_hierarchy_and_complete_leaf_sequence(depth: int) -> None:
    value: Any = {
        "identifier": "a" * 128,
        "negative": False,
        "limitation": "No deployed authorization or application outcome is established.",
    }
    for index in range(depth):
        value = {"level_" + str(index): value}
    before = copy.deepcopy(value)
    seen: list[tuple[str, object]] = []

    def exact(item: object, field: str) -> str:
        seen.append((field, item))
        return leaf(item, field)

    html = compact_value(value, exact)
    dom = DOM(html.encode()).root
    assert len(dom.nodes("section", "evidence-group")) == depth
    assert len(dom.nodes("dl")) == 1 and not dom.nodes("ul")
    assert seen == [
        ("identifier", "a" * 128),
        ("negative", False),
        ("limitation", "No deployed authorization or application outcome is established."),
    ]
    assert not dom.nodes("details") and value == before
    assert len(html) < 25_000
    assert "padding:0" in COMPACT_CSS and "overflow-wrap:anywhere" in COMPACT_CSS


@pytest.mark.parametrize(
    "value",
    [
        {"long_" + "label" * 40: "b" * 256},
        {"absent": None, "empty_object": {}, "empty_list": [], "empty_text": ""},
        {"records": [{"name": "same", "value": 0}, {"name": "same", "value": 2**100}]},
        {"ports": [502, 503], "nested": [[1, 2], [3, 4]]},
        {'<script onload="bad">': '</dd><img src="https://bad.invalid"> & "quotes"'},
    ],
)
def test_adversarial_values_are_passive_complete_and_deterministic(value: dict[str, Any]) -> None:
    before = copy.deepcopy(value)
    raw = compact_value(value, leaf)
    parser = PageAudit()
    parser.feed(document("Synthetic presentation only", raw, "a" * 64).decode())
    dom = DOM(raw.encode()).root
    assert not dom.nodes("script") and not dom.nodes("img")
    assert raw == compact_value(value, leaf) and value == before
    if "empty_object" in value:
        assert "{}" in dom.text and "[]" in dom.text and "Not recorded" in dom.text
    if "records" in value:
        assert dom.text.count("same") == 2 and str(2**100) in dom.text
    if "ports" in value:
        assert dom.nodes("ul", "evidence-values") and not dom.nodes("ol")


def test_witness_steps_are_numbered_in_exact_input_order() -> None:
    value = {
        "steps": [{"edge_id": "z_last_lexically"}, {"edge_id": "a_first_lexically"}],
        "other_records": [{"id": "one"}, {"id": "two"}],
    }
    dom = DOM(compact_value(value, leaf, sort_keys=True).encode()).root
    tables = dom.nodes("table")
    assert len(tables) == 2 and not dom.nodes("ol")
    assert "Ordered witness steps" in tables[-1].text
    assert [cell.text for cell in tables[-1].nodes("td")] == [
        "z_last_lexically",
        "a_first_lexically",
    ]
    assert [cell.text for cell in tables[-1].nodes("tbody")[0].nodes("th")] == ["1", "2"]


def test_historical_prototype_changes_only_pair_pages_and_keeps_exact_utc() -> None:
    report, verification = _fixture()
    report["comparisons"][0]["comparability"]["dimensions"].append(
        {
            "dimension": "timestamps",
            "result": "COMPARABLE",
            "source_evidence": {"values": [{"first_timestamp": "1700000000000000001/1000000000"}]},
            "reason": "Exact recorded bound",
            "consequence": "No continuity inferred",
        }
    )
    original = copy.deepcopy(report)
    before = render(report, verification, page_size=10)
    after = render(report, verification, page_size=10, compact_prototype=True)
    pages = _structural_oracle(after)
    assert "2023-11-14 22:13:20.000000001 UTC" in pages["pair-1.html"].text
    assert "1700000000000000001/1000000000" in pages["pair-1.html"].text
    assert 'class="compact-fields"' in after["pair-1.html"].decode()
    for name in before:
        if name not in {"pair-1.html", "style.css", "verification.html"}:
            assert before[name] == after[name], name
    assert before == after
    after["report.json"] = canonical(report)
    after["verification.json"] = canonical(verification)
    assert audit_files(after)["broken_links"] == 0
    assert "not a canonical Historical Explorer publication" not in pages["verification.html"].text
    assert report == original


def test_native_trace_prototype_retains_exact_json_and_default_output() -> None:
    result = trace_architecture(
        validate_file(ROOT / "examples/trace/communication.yaml"),
        "eng",
        "svc_blocked",
        policy_evidence=True,
    )
    exact = trace_json(result)
    default = trace_html(result)
    assert default == trace_html(result, compact_prototype=False)
    assert 'class="compact-evidence"' in default.decode()
    raw = trace_html(result, compact_prototype=True)
    dom = DOM(raw).root
    assert (
        'class="compact-evidence"' in raw.decode()
        and "<pre>" not in raw.decode().split('<section id="policy">')[1].split("</section>")[0]
    )
    assert json.loads(dom.nodes("pre")[-1].text) == json.loads(exact)
    assert "Content-Security-Policy" in raw.decode() and trace_json(result) == exact


def test_capture_prototype_has_ordered_witness_and_unchanged_canonical_json(tmp_path: Path) -> None:
    source = frozen("supported")
    before = copy.deepcopy(source)
    output = tmp_path / "capture"
    result = generate_site(
        source["observations"],
        output,
        source["comparison"],
        mapping=source["mapping"],
        compact_prototype=True,
    )
    text = "".join(path.read_text(encoding="utf-8") for path in output.glob("evidence*.html"))
    assert 'class="compact-evidence"' in text and "Ordered witness steps" in text
    assert source == before and result["audit"]["broken_links"] == 0
    for name, data in source.items():
        assert json.loads((output / (name + ".json")).read_bytes()) == data


def test_architecture_prototype_renders_exact_intent_evidence(tmp_path: Path) -> None:
    source = ROOT / "tests/fixtures/boundary-device.yaml"
    original = source.read_bytes()
    output = tmp_path / "architecture"
    result = generate_explorer(
        source, output, options=ExploreOptions(scenarios=("support_scope",), compact_prototype=True)
    )
    candidates = [p.read_text(encoding="utf-8") for p in output.glob("analysis-*.html")]
    exposure = next(text for text in candidates if "Independent intent outcomes" in text)
    # F1 now uses the requested table-centric prototype; other consumers keep
    # the preceding compact object layout until separate visual acceptance.
    assert 'class="exposure-tables"' in exposure and "Retained exposure observations" in exposure
    assert "<table>" in exposure and 'class="compact-fields"' not in exposure
    site = result["site"]
    assert isinstance(site, dict)
    assert original == source.read_bytes() and site["broken_links"] == 0


def test_simple_documentary_nodes_keep_descriptive_navigation(tmp_path: Path) -> None:
    manifest = synthetic_project(tmp_path / "project", count=4)
    draft = create_project(manifest)
    accepted = tmp_path / "accepted"
    accepted.mkdir()
    for name, data in emit_project(draft, tutorial_decisions(draft), manifest).items():
        (accepted / name).write_bytes(data)
    output = tmp_path / "documentary"
    generate_explorer(
        accepted / "architecture.yaml",
        output,
        provenance=accepted / "architecture.provenance.json",
        options=ExploreOptions(compact_prototype=True),
    )
    nodes = [DOM(path.read_bytes()).root for path in output.glob("node-*.html")]
    assert nodes and any(node.nodes("dl", "compact-fields") for node in nodes)
    assert any("Documented only" in link.text for node in nodes for link in node.nodes("a"))
    candidates = [p.read_text(encoding="utf-8") for p in output.glob("candidate-*.html")]
    assert all('class="compact-fields"' in text for text in candidates)


def test_comparison_keeps_canonical_review_and_exact_links(
    tmp_path: Path, minimal: dict[str, Any]
) -> None:
    before, after = tmp_path / "before.yaml", tmp_path / "after.yaml"
    before.write_text(yaml.safe_dump(minimal), encoding="utf-8")
    changed = copy.deepcopy(minimal)
    changed["rules"] = []
    after.write_text(yaml.safe_dump(changed), encoding="utf-8")
    queries = (ReviewQuery(source_asset_id="eng", service_id="svc_plc"),)
    expected = canonical(compare_architecture_versions(before, after, queries=queries))
    output = tmp_path / "comparison"
    result = generate_review(
        before, output, proposed=after, queries=queries, compact_prototype=True
    )
    assert (output / "review.json").read_bytes() == expected
    records = [p.read_text(encoding="utf-8") for p in output.glob("record-*.html")]
    assert any('class="compact-evidence"' in text for text in records)
    assert result["site"]["broken_links"] == 0
