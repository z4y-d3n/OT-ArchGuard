"""F1 schema-aware tables: record conservation, truthful diagnostics and scope."""

import copy
import json
from dataclasses import asdict, replace
from pathlib import Path

import pytest
from test_historical_explorer_layout import DOM, Element

from otarchguard.api import validate_file
from otarchguard.explorer import ExploreOptions, Explorer, generate_explorer, path
from otarchguard.explorer_exposure import exposure_tables
from otarchguard.explorer_html import (
    EXPOSURE_TABLE_CSS,
    PageAudit,
    SiteWriter,
    audit_site,
    document,
    table,
)
from otarchguard.exposure import ExposureResult, exposure_architecture

SOURCE = Path(__file__).parent / "fixtures/boundary-device.yaml"


@pytest.fixture
def evidence(tmp_path: Path) -> tuple[Explorer, ExposureResult]:
    model = validate_file(SOURCE)
    return Explorer(model, None, SiteWriter(tmp_path, model.sha256)), exposure_architecture(
        model, "support_scope"
    )


def page(explorer: Explorer, result: ExposureResult) -> Element:
    links = [
        (
            path("analysis", ["exposure", result.scenario_id, q.source_asset_id, q.service_id]),
            f"{q.source_asset_id} → {q.service_id}",
        )
        for q in result.queries
    ]
    raw = exposure_tables(result, explorer.value, links)
    parser = PageAudit()
    parser.feed(document("Synthetic F1 presentation test", raw, result.snapshot_sha256).decode())
    return DOM(raw.encode()).root


def tables(root: Element, prefix: str) -> list[Element]:
    return [
        item for item in root.nodes("table") if item.nodes("caption")[0].text.startswith(prefix)
    ]


def rows(root: Element, prefix: str) -> list[list[str]]:
    return [
        [
            cell.text
            for cell in row.children
            if isinstance(cell, Element) and cell.tag in {"th", "td"}
        ]
        for item in tables(root, prefix)
        for row in item.nodes("tbody")[0].nodes("tr")
    ]


def test_real_scenario_has_five_sections_and_conserves_all_records(
    evidence: tuple[Explorer, ExposureResult],
) -> None:
    explorer, result = evidence
    original = copy.deepcopy(asdict(result))
    root = page(explorer, result)
    assert [item.text for item in root.nodes("h2")] == [
        "Scenario overview",
        "Destination assets",
        "Observations",
        "Prohibited intents",
        "Required intents and path steps",
    ]
    assert len(rows(root, "Retained destination assets")) == len(result.destination_assets) == 4
    assert len(rows(root, "Retained exposure observations")) == len(result.observations) == 4
    assert (
        len(rows(root, "All evaluated scenario intervals"))
        == sum(len(q.intervals) for q in result.queries)
        == 10
    )
    assert len(rows(root, "Prohibited intent interval results")) == 6
    assert len(rows(root, "Exact evaluated intent intervals")) == 4
    assert len(rows(root, "Individual prohibited blocked-edge records")) == 6
    assert len(rows(root, "Ordered witness steps")) == 8
    assert len(rows(root, "Witness step endpoints")) == 16
    for item in root.nodes("table"):
        assert not item.nodes("table") and not item.nodes("pre")
        assert item.nodes("caption") and item.nodes("thead") and item.nodes("tbody")
        assert all(h.attrs.get("scope") == "col" for h in item.nodes("thead")[0].nodes("th"))
    assert not root.nodes("ul") and not root.nodes("ol") and not root.nodes("dl")
    assert json.loads(root.nodes("pre")[0].text) == json.loads(json.dumps(original))
    assert original == asdict(result)
    properties = dict(rows(root, "Scenario properties"))
    assert properties["Scenario passed"] == "Yes"
    assert "Failed intents: 0" in properties["Independent intent outcomes"]
    assert "not captured packets" in root.text


def test_global_diagnostic_and_each_blocked_edge_remain_separate(
    evidence: tuple[Explorer, ExposureResult],
) -> None:
    explorer, result = evidence
    intent = next(i for i in result.intent_checks.intents if i.kind == "prohibited")
    query, interval = intent.queries[0], intent.queries[0].intervals[0]
    assert interval.diagnostics is not None
    edge = interval.diagnostics.blocked_edges[0]
    diagnostic = replace(
        interval.diagnostics,
        reason="GLOBAL_REASON",
        blocked_edge_count=9,
        truncated=True,
        blocked_edges=(
            replace(edge, reason="EDGE_REASON_1"),
            replace(edge, reason="EDGE_REASON_2"),
            edge,
        ),
    )
    query = replace(query, intervals=(replace(interval, diagnostics=diagnostic),))
    intent = replace(intent, queries=(query,))
    result = replace(
        result, queries=(), intent_checks=replace(result.intent_checks, intents=(intent,))
    )
    root = page(explorer, result)
    (summary,) = rows(root, "Prohibited intent interval results")
    assert summary[-1] == "GLOBAL_REASON" and summary[-2] == "No"
    assert [row[3] for row in rows(root, "Individual prohibited blocked-edge records")] == [
        "EDGE_REASON_1",
        "EDGE_REASON_2",
        edge.reason,
    ]
    assert rows(root, "Prohibited diagnostic bounds")[0][1:4] == ["9", "3", "Yes"]
    assert diagnostic.limitation in root.text
    assert len(root.nodes("a")) > 0


def test_ordered_witness_steps_and_endpoints_are_exact(
    evidence: tuple[Explorer, ExposureResult],
) -> None:
    explorer, result = evidence
    intent = next(i for i in result.intent_checks.intents if i.kind == "required")
    query = intent.queries[0]
    interval = query.intervals[0]
    assert interval.witness is not None
    witness = interval.witness
    steps = (
        replace(
            witness.steps[0],
            edge_id="z_synthetic",
            conduit_id="synthetic_conduit",
            allow_rule_ids=("rule_z", "rule_a"),
        ),
        replace(witness.steps[-1], edge_id="a_synthetic"),
    )
    witness = replace(witness, steps=steps)
    query = replace(query, intervals=(replace(interval, witness=witness),))
    intent = replace(intent, queries=(query,))
    result = replace(
        result, queries=(), intent_checks=replace(result.intent_checks, intents=(intent,))
    )
    root = page(explorer, result)
    step_rows = rows(root, "Ordered witness steps")
    assert [row[:4] for row in step_rows] == [
        [str(index), step.edge_id, step.kind, step.conduit_id or "None declared"]
        for index, step in enumerate(steps, 1)
    ]
    assert step_rows[0][4] == "rule_z · rule_a"
    expected = [
        [
            str(index),
            role,
            endpoint.asset_id,
            endpoint.state.interface_id,
            endpoint.state.phase,
            endpoint.ipv4,
            endpoint.placement_zone_id,
        ]
        for index, step in enumerate(steps, 1)
        for role, endpoint in (("Source", step.source), ("Target", step.target))
    ]
    assert rows(root, "Witness step endpoints") == expected
    assert witness.snapshot_sha256 in root.text
    assert rows(root, "Exact evaluated intent intervals")[0][6] == "Not retained"


@pytest.mark.parametrize("kind", ["required", "prohibited", "unsupported_retained_kind"])
def test_absent_intervals_witnesses_and_unknown_kinds_are_not_invented(
    evidence: tuple[Explorer, ExposureResult],
    kind: str,
) -> None:
    explorer, result = evidence
    intent = result.intent_checks.intents[0]
    query = intent.queries[0]
    interval = replace(query.intervals[0], reachable=False, witness=None, diagnostics=None)
    query = replace(query, intervals=(interval,))
    intent = replace(intent, kind=kind, queries=(query,), passed=False)
    result = replace(
        result, queries=(), intent_checks=replace(result.intent_checks, intents=(intent,))
    )
    root = page(explorer, result)
    summary = (
        rows(root, "Prohibited intent interval results")
        if kind == "prohibited"
        else rows(root, "Exact evaluated intent intervals")
    )
    assert "Not retained" in summary[0] and "No diagnostic retained" in summary[0]
    assert not rows(root, "Ordered witness steps") and not rows(
        root, "Individual prohibited blocked"
    )
    if kind == "unsupported_retained_kind":
        assert "Unsupported retained intent kind" in root.text and kind in root.text
    query = replace(query, intervals=())
    intent = replace(intent, queries=(query,))
    empty = replace(
        result, queries=(), intent_checks=replace(result.intent_checks, intents=(intent,))
    )
    assert "No intervals retained" in page(explorer, empty).text


def test_scenario_evidence_without_intents_and_duplicate_observations_are_retained(
    evidence: tuple[Explorer, ExposureResult],
) -> None:
    explorer, result = evidence
    result = replace(
        result,
        observations=result.observations + result.observations[:1],
        intent_checks=replace(result.intent_checks, intents=()),
    )
    root = page(explorer, result)
    assert len(rows(root, "Retained exposure observations")) == 5
    assert len(rows(root, "Ordered witness steps")) == 8
    assert len(rows(root, "Individual blocked-edge evidence")) == 6
    assert (
        "No prohibited intents retained" in root.text
        and "No required intents retained" in root.text
    )
    assert json.loads(root.nodes("pre")[0].text) == json.loads(json.dumps(asdict(result)))


def test_failed_prohibited_intent_keeps_its_positive_witness(
    evidence: tuple[Explorer, ExposureResult],
) -> None:
    explorer, result = evidence
    original = next(i for i in result.intent_checks.intents if i.kind == "required")
    intent = replace(original, kind="prohibited", passed=False)
    result = replace(
        result,
        queries=(),
        passed=False,
        intent_checks=replace(
            result.intent_checks,
            intents=(intent,),
            passed=False,
            failed_intent_count=1,
            failed_interval_count=1,
        ),
    )
    root = page(explorer, result)
    summary = rows(root, "Prohibited intent interval results")
    assert summary[0][2] == "No" and summary[0][7:9] == ["Yes", "Not retained"]
    witness = intent.queries[0].intervals[0].witness
    assert witness is not None
    assert len(rows(root, "Ordered witness steps")) == len(witness.steps)
    assert not rows(root, "Individual prohibited blocked-edge records")


def test_empty_record_collections_do_not_manufacture_evidence(
    evidence: tuple[Explorer, ExposureResult],
) -> None:
    explorer, result = evidence
    intents = tuple(replace(i, queries=()) for i in result.intent_checks.intents)
    result = replace(
        result,
        observations=(),
        destination_assets=(),
        queries=(),
        intent_checks=replace(result.intent_checks, intents=intents),
    )
    root = page(explorer, result)
    assert not rows(root, "Retained exposure observations")
    assert not rows(root, "Retained destination assets")
    assert not rows(root, "Ordered witness steps")
    assert "No query records retained" in root.text
    assert len(rows(root, "Prohibited intents without retained intervals")) == 4


@pytest.mark.parametrize(
    "text",
    [
        '</td><script>"& unsafe</script>',
        "界" * 4096,
        "0123456789abcdef" * 32,
        'quote\'s [label] <img src="https://host.invalid">',
    ],
)
def test_long_and_hostile_values_are_complete_and_inert(
    evidence: tuple[Explorer, ExposureResult],
    text: str,
) -> None:
    explorer, result = evidence
    result = replace(result, completeness_assertion=text)
    original = asdict(result)
    root = page(explorer, result)
    assert text in root.text and not root.nodes("script") and not root.nodes("img")
    assert json.loads(root.nodes("pre")[0].text)["completeness_assertion"] == text
    assert original == asdict(result)


def test_appendix_preserves_existing_path_and_bidi_minimization(
    evidence: tuple[Explorer, ExposureResult],
) -> None:
    explorer, result = evidence
    text = "C:/Users/private/secret.txt \u202eowner assertion"
    result = replace(result, completeness_assertion=text)
    root = page(explorer, result)
    assert "C:/Users/private" not in root.text and "\u202e" not in root.text
    assert "[local path withheld]" in root.text and "[U+202E]" in root.text
    assert result.completeness_assertion == text


def test_default_table_bytes_and_opt_in_row_headers() -> None:
    plain = table("Example", ("A", "B"), [("x", "y")])
    assert "<tbody><tr><td>x</td><td>y</td></tr></tbody>" in plain
    header = DOM(table("Example", ("A", "B"), [("x", "y")], row_headers=True).encode()).root
    assert header.nodes("tbody")[0].nodes("th")[0].attrs["scope"] == "row"
    assert "overflow:visible" in EXPOSURE_TABLE_CSS and "table-header-group" in EXPOSURE_TABLE_CSS


def test_only_exposure_page_changes_and_original_destinations_survive(tmp_path: Path) -> None:
    sites = []
    for compact in (False, True):
        site = tmp_path / ("prototype" if compact else "default")
        generate_explorer(
            SOURCE,
            site,
            options=ExploreOptions(
                traces=(("it", "svc_jump"),),
                check=True,
                scenarios=("support_scope",),
                compact_prototype=compact,
            ),
        )
        assert audit_site(site)["broken_links"] == 0
        sites.append(site)
    before, after = sites
    name = path("analysis", ["exposure", "support_scope"])
    old, new = DOM((before / name).read_bytes()).root, DOM((after / name).read_bytes()).root
    assert {node.attrs.get("href") for node in old.nodes("a")} <= {
        node.attrs.get("href") for node in new.nodes("a")
    }
    assert {node.attrs.get("id") for node in old.nodes("main")} <= {
        node.attrs.get("id") for node in new.nodes("main")
    }
    for file in before.glob("*.html"):
        if file.name != name:
            assert file.read_bytes() == (after / file.name).read_bytes(), file.name
    manifest_before = json.loads((before / "manifest.json").read_bytes())
    manifest_after = json.loads((after / "manifest.json").read_bytes())
    assert manifest_before["locations"] == manifest_after["locations"]
