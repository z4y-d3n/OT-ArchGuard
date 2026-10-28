"""Cross-version presentation oracles; no operational or browser acceptance claims."""

import copy
import json
import re
from html import unescape
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

import pytest
from test_historical_explorer_layout import DOM, rules
from test_historical_explorer_render import _fixture, _structural_oracle

from otarchguard.api import validate_file
from otarchguard.capture.display import render_value
from otarchguard.diagrams import spatial_svg
from otarchguard.drift.explorer_render import _finding_label, _records, _value, render
from otarchguard.explorer import Explorer, generate_explorer
from otarchguard.explorer_data import load_model
from otarchguard.explorer_html import CSS, audit_site, escape
from otarchguard.ingestion.project import create_project
from otarchguard.ingestion.project_review import (
    _markdown_field,
    _safe,
    emit_project,
    review_markdown,
)
from otarchguard.reporting import _STYLE, _table, architecture_svg
from otarchguard.review_explorer import _value as review_value
from otarchguard.trace import trace_architecture
from otarchguard.trace_reporting import trace_html, trace_json
from tools.synthetic_projects import synthetic_project, tutorial_decisions

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("depth", [1, 3, 8, 24])
@pytest.mark.parametrize("consumer", ["architecture", "comparison", "capture"])
def test_nested_evidence_retains_width_order_and_exact_values(depth: int, consumer: str) -> None:
    hostile = '</dd><script>"& evidence</script>'
    value: Any = {"identifier": "a" * 64, "absent": None, "empty": [], "hostile": hostile}
    for index in range(depth):
        value = {"long_property_" + "x" * 80 + str(index): [{"step": index, "witness": value}]}
    before = copy.deepcopy(value)
    if consumer == "architecture":
        renderer = object.__new__(Explorer)
        renderer.native_paths = {}
        html = renderer.value(value)
    else:
        html = (review_value if consumer == "comparison" else render_value)(value)
    dom = DOM(html.encode()).root
    assert hostile in dom.text and "a" * 64 in dom.text
    assert not dom.nodes("script")
    assert len(dom.nodes("dt")) == 4 + 3 * depth
    assert value == before and len(html) < 80_000
    # Every nested object/list retains full parent width at every target size.
    for viewport in (1440, 1024, 768, 720, 390, 375):
        css = rules(CSS, viewport)
        assert css[".properties"]["display"] == "block"
        assert "grid-template-columns" not in css[".properties"]
        assert css[".properties ul"]["padding-left"] == "0"
    assert rules(CSS, 1440, print_mode=True)[".properties"]["display"] == "block"


def test_native_complex_records_are_lossless_full_width_fields() -> None:
    rows = [
        {
            "rule": "deny_exact",
            "scope": {"ports": [[502, 502]], "id": "b" * 64},
            "diagnostic": "long " * 100,
            "large": 2**128,
            "missing": None,
        },
        {
            "rule": "<script>hostile</script>",
            "scope": {},
            "diagnostic": "unsupported",
            "large": 0,
            "missing": [],
        },
    ]
    before = copy.deepcopy(rows)
    html = _table("Exact diagnostic records", rows)
    dom = DOM(html.encode()).root
    assert not dom.nodes("table") and not dom.nodes("pre") and not dom.nodes("script")
    for value in (
        "deny_exact",
        "b" * 64,
        "502",
        str(2**128),
        "null",
        "[]",
        "{}",
        "<script>hostile</script>",
        "unsupported",
    ):
        assert value in dom.text
    assert [node.text for node in dom.nodes("h4")] == ["Record 1", "Record 2"]
    assert [node.text for node in dom.nodes("dt")].count("rule") == 2
    assert rows == before
    assert rules(_STYLE, 390)[".report-fields dd"]["margin"] == "0 0 .5rem"
    assert rules(_STYLE, 1440, print_mode=True)["pre"]["max-height"] == "none"


def test_native_scalar_headers_and_wide_counters() -> None:
    html = _table("Intervals", [{"start": 502, "end": 503, "reachable": False}])
    dom = DOM(html.encode()).root
    assert [node.text for node in dom.nodes("th")] == ["start", "end", "reachable"]
    assert all(node.attrs["scope"] == "col" for node in dom.nodes("th"))
    assert "scroll horizontally" in html and 'tabindex="0"' in html
    counters = {f"counter_{index}": index for index in range(17)}
    wide = DOM(_table("Resource ceilings", [counters]).encode()).root
    assert [node.text for node in wide.nodes("dt")] == list(counters)
    assert not wide.nodes("table")
    assert "none" in _table("Unsupported results", [])


def test_native_trace_json_and_embedded_exact_appendix_are_unchanged() -> None:
    model = validate_file(ROOT / "tests/fixtures/boundary-device.yaml")
    result = trace_architecture(model, "it", "svc_plc", policy_evidence=True)
    before = trace_json(result)
    html = trace_html(result)
    dom = DOM(html).root
    assert "Finite diagnostic scope and findings" in dom.text
    assert "Accepted resource ceilings for this run" in dom.text
    assert 'class="report-fields"' in html.decode()
    assert json.loads(dom.nodes("pre")[-1].text) == json.loads(before)
    assert trace_json(result) == before and trace_html(result) == html
    assert "Content-Security-Policy" in html.decode() and not dom.nodes("script")


@pytest.mark.parametrize(
    "text",
    [
        "'apostrophe' and \"quotes\"",
        r"C:\literal\backslash",
        "*_[link](target)#`|~!{}",
        '<script onload="x">&</script>',
        "[x](javascript:bad)",
        "&#x27; <img src=x>",
        "Documentación · α → β",
        "line\n# heading\rnext",
    ],
)
def test_markdown_text_escaping_preserves_literal_content(text: str) -> None:
    escaped = _safe(text)
    assert "<" not in escaped and ">" not in escaped
    assert "&\\#" not in escaped
    # CommonMark punctuation escapes and character references are text, not markup.
    decoded = unescape(re.sub(r"\\([!\"#$%&'()*+,\-./:;<=>?@\[\\\]^_`{|}~])", r"\1", escaped))
    assert decoded == text.replace("\r", " ").replace("\n", " ")


def test_markdown_locations_diagnostics_and_real_project_are_structured(tmp_path: Path) -> None:
    location = {
        "collection": "Assets",
        "sheet": "Owner's sheet",
        "record": "2",
        "cell": None,
        "pointer": {"path": "<unsafe>"},
        "diagnostics": ["a", "b"],
    }
    lines = _markdown_field("Source location", location)
    joined = "\n".join(lines)
    assert "  - collection: Assets" in joined and "  - cell: Not recorded" in joined
    assert "    - path: &lt;unsafe&gt;" in joined
    assert "{'" not in joined and "&\\#x27;" not in joined
    manifest = synthetic_project(tmp_path / "project")
    draft = create_project(manifest)
    before = draft.model_dump(mode="json")
    markdown = review_markdown(draft).decode()
    assert "Source location" in markdown and "collection:" in markdown
    assert "None" not in markdown and "&\\#x27;" not in markdown and "{'" not in markdown
    assert "source order cannot resolve" in markdown
    assert draft.model_dump(mode="json") == before and review_markdown(draft).decode() == markdown


def _nine_communications() -> tuple[dict[str, Any], dict[str, Any]]:
    report, verification = _fixture()
    template = report["comparisons"][0]["findings"][2]
    findings = []
    for index in range(9):
        finding = copy.deepcopy(template)
        finding["key"].update(
            source_ip="192.0.2.10",
            destination_ip="192.0.2.20",
            source_port=41000 + index,
            destination_port=502,
        )
        findings.append(finding)
    report["comparisons"][0]["findings"] = findings
    report["summary"].update(
        findings=9,
        difference_records=0,
        unchanged_support_records=9,
        abstentions=0,
        categories={"OBSERVED_COMMUNICATION_DIFFERENCE": 9},
    )
    return report, verification


def test_nine_communications_have_distinct_labels_and_exact_identities() -> None:
    report, verification = _nine_communications()
    before = copy.deepcopy(report)
    identities = {record.identity for record in _records(report)}
    files = render(report, verification)
    pages = _structural_oracle(files)
    page = pages["pair-1-findings.html"]
    assert (
        len(identities) == 9
        and len(set(page.hrefs) & {"communications.html#" + identity for identity in identities})
        == 9
    )
    for index in range(9):
        assert f"source port {41000 + index}" in page.text
    assert "192.0.2.10 → 192.0.2.20 · TCP/502" in page.text
    assert all(identity in pages["communications.html"].ids for identity in identities)
    assert report == before and render(report, verification) == files


@pytest.mark.parametrize(
    "key",
    [
        {},
        {"source_ip": "not an IP", "transport": []},
        {"source_ip": None, "destination_port": True},
    ],
)
def test_missing_unsupported_and_colliding_finding_labels(key: dict[str, Any]) -> None:
    report, verification = _nine_communications()
    for finding in report["comparisons"][0]["findings"]:
        finding["key"] = copy.deepcopy(key)
    records = _records(report)
    files = render(report, verification)
    text = _structural_oracle(files)["pair-1-findings.html"].text
    for record in records:
        assert "#" + record.identity[2:14] in text
    assert "TCP/True" not in text and "not an IP →" not in text


def test_protocol_coverage_and_analytical_titles_have_stable_context() -> None:
    report, _ = _fixture()
    labels = [_finding_label(record) for record in _records(report)]
    assert len(set(labels)) == len(labels)
    assert any("PROFINET" in label for label in labels)
    assert any("#" in label and "coverage" in label.lower() for label in labels)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("1700000000/1", "2023-11-14 22:13:20 UTC"),
        ("1700000000000000001/1000000000", "2023-11-14 22:13:20.000000001 UTC"),
        ("-1/4", "1969-12-31 23:59:59.75 UTC"),
        ("1/3", "1970-01-01 00:00:00 UTC + 1/3 second (exact)"),
        (None, "Timestamp not recorded"),
        ("bad", "Invalid recorded timestamp"),
    ],
)
def test_historical_named_timestamps_preserve_precision(value: str | None, expected: str) -> None:
    data = {"source_evidence": {"values": [{"first_timestamp": value, "packets": 1700000000}]}}
    dom = DOM(_value(data).encode()).root
    assert expected in dom.text
    if value is not None:
        assert value in dom.text
    assert "1700000000" in dom.text
    assert "UTC" not in _value({"packets": "1700000000/1"})
    assert "UTC" not in _value({"first_timestamp": 1700000000})


def test_adapted_svg_legend_matches_style_without_changing_graph() -> None:
    model = validate_file(ROOT / "tests/fixtures/boundary-device.yaml")
    original = architecture_svg(model)
    adapted = spatial_svg(model, False, escape, forwarding_dashed=False)
    before, after = ET.fromstring(original), ET.fromstring(adapted)
    ns = {"s": "http://www.w3.org/2000/svg"}
    assert "Purple solid: explicit forwarding." in "".join(after.itertext())
    assert "Purple dashed:" in "".join(before.itertext())
    assert len(after.findall("s:g[@data-edge-id]", ns)) == len(model.model.transport_edges) + len(
        model.model.forwarding_edges
    )
    for left, right in zip(before.iter(), after.iter(), strict=True):
        assert left.tag == right.tag
        assert {
            k: v for k, v in left.attrib.items() if (k, v) != ("stroke-dasharray", "8 4")
        } == right.attrib
        if left.text and "Purple dashed:" not in left.text:
            assert left.text == right.text
    assert spatial_svg(model, False, escape, forwarding_dashed=False) == adapted


def test_forwarding_legend_cannot_rewrite_owner_text(tmp_path: Path) -> None:
    import yaml

    from otarchguard.api import validate_bytes

    data = yaml.safe_load((ROOT / "tests/fixtures/boundary-device.yaml").read_bytes())
    phrase = "Purple dashed: explicit forwarding."
    data["assets"][0]["name"] = phrase
    data["zones"][0]["name"] = phrase
    model = validate_bytes(yaml.safe_dump(data).encode())
    adapted = ET.fromstring(spatial_svg(model, False, escape, forwarding_dashed=False))
    titles = [node.text for node in adapted.iter() if node.tag.endswith("}title")]
    assert titles.count(phrase) == 2
    assert "Purple solid: explicit forwarding." in "".join(adapted.itertext())


def test_documentary_candidate_links_have_context_and_full_evidence(tmp_path: Path) -> None:
    manifest = synthetic_project(tmp_path / "project")
    draft = create_project(manifest)
    artifacts = emit_project(draft, tutorial_decisions(draft), manifest)
    accepted = tmp_path / "accepted"
    accepted.mkdir()
    for name, data in artifacts.items():
        (accepted / name).write_bytes(data)
    model = accepted / "architecture.yaml"
    provenance = accepted / "architecture.provenance.json"
    before = model.read_bytes(), provenance.read_bytes()
    site = tmp_path / "site"
    generate_explorer(model, site, provenance=provenance)
    assert audit_site(site)["broken_links"] == 0
    pages = [DOM(path.read_bytes()).root for path in site.glob("*.html")]
    links = [node for page in pages for node in page.nodes("a")]
    connector = [node for node in links if str(node.attrs.get("href", "")).startswith("connector-")]
    assert connector and all(
        "Documented only" in node.text and " — " in node.text for node in connector
    )
    candidates = [
        node for node in links if str(node.attrs.get("href", "")).startswith("candidate-")
    ]
    assert candidates and all("candidate ·" in node.text for node in candidates)
    assert all("Documentary connector connector-" not in page.text for page in pages)
    assert before == (model.read_bytes(), provenance.read_bytes())
    assert load_model(model).sha256 == validate_file(model).sha256
