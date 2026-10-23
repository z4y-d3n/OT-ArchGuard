"""Concrete tuple aggregation and conservative explanations without further analysis."""

from copy import deepcopy
from dataclasses import asdict, replace
from typing import Any

import pytest
import yaml
from test_comparison_properties import small_network
from test_reporting import OfflineHTML

from otarchguard.api import validate_bytes
from otarchguard.comparison import compare_bytes
from otarchguard.diagnostics import ModelError
from otarchguard.exposure import QueryScope, evaluate_scope, exposure_bytes
from otarchguard.reachability import ReachabilityEngine
from otarchguard.reporting import build_report, html_report, json_report
from otarchguard.summaries import explain_comparison, summarize_exposure
from otarchguard.trace import trace_bytes
from otarchguard.trace_reporting import trace_html


@pytest.mark.parametrize("seed", range(16))
def test_summary_concrete_tuple_oracle(
    minimal: dict[str, Any], seed: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    data = small_network(minimal, seed)
    snapshot = validate_bytes(yaml.safe_dump(data).encode())
    result = evaluate_scope(
        snapshot,
        QueryScope(("eng", "client", "plc"), tuple(s["id"] for s in data["services"])),
        None,
    )
    # Expected summary is a finite expansion of completed results, not summary helpers.
    evaluated = {
        (q.source_asset_id, q.service_id, p)
        for q in result.queries
        for i in q.intervals
        for p in range(i.start, i.end + 1)
    }
    reached = {
        (q.source_asset_id, q.destination_asset_id, q.service_id, q.protocol, p)
        for q in result.queries
        for i in q.intervals
        if i.reachable
        for p in range(i.start, i.end + 1)
    }

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("Summary must not evaluate reachability")

    monkeypatch.setattr(ReachabilityEngine, "evaluate", forbidden)
    summary = summarize_exposure(snapshot, result)
    assert summary.evaluated_query_pairs == len({(s, v) for s, v, _ in evaluated})
    assert summary.evaluated_destination_ports_across_pairs == len(evaluated)
    assert summary.reachable_destination_ports_across_pairs == len(reached)
    assert set(summary.distinct_reachable_destination_asset_ids) == {d for _, d, _, _, _ in reached}
    assert {
        (t.source_asset_id, t.destination_asset_id, t.service_id, t.protocol, p)
        for t in summary.reachable_communication_tuples
        for start, end in t.reachable_ports
        for p in range(start, end + 1)
    } == reached
    assert (
        summary.reachable_exact_interval_records + summary.unreachable_exact_interval_records
        == summary.evaluated_exact_interval_records
    )
    assert summary.unevaluated_present_query_pairs == 0
    assert summary.outside_scope_pair_count is None
    assert set(summary.excluded_self_asset_pairs) == {
        ("plc", "svc_plc_tcp"),
        ("plc", "svc_plc_udp"),
    }


def test_owner_zone_is_distinct_from_interface_placement(boundary: dict[str, Any]) -> None:
    snap = validate_bytes(yaml.safe_dump(boundary).encode())
    result = exposure_bytes(yaml.safe_dump(boundary).encode(), "support_scope")
    summary = summarize_exposure(snap, result)
    owners = {a["id"]: a["zone_id"] for a in boundary["assets"]}
    for item in summary.reachable_communication_tuples:
        assert item.source_owner_zone_id == owners[item.source_asset_id]
        assert item.destination_owner_zone_id == owners[item.destination_asset_id]
    assert summary.cross_owner_zone_tuples == tuple(
        t
        for t in summary.reachable_communication_tuples
        if owners[t.source_asset_id] != owners[t.destination_asset_id]
    )
    assert summary.cross_owner_zone_tuples
    # fw's owning zone and external placements differ in this fixture.
    assert any(
        i["asset_id"] == "fw" and i["placement_zone_id"] != owners["fw"]
        for i in boundary["interfaces"]
    )


def test_unavailable_noncomparable_and_unassessed(minimal: dict[str, Any]) -> None:
    snap = validate_bytes(yaml.safe_dump(minimal).encode())
    result = exposure_bytes(yaml.safe_dump(minimal).encode(), "engineering_scope")
    partial = replace(
        result,
        queries=(),
        unavailable_origin_asset_ids=("removed",),
        unavailable_destination_service_ids=("gone",),
    )
    summary = summarize_exposure(snap, partial, noncomparable_service_ids=("svc_plc",))
    assert summary.evaluated_query_pairs == 0 and summary.unevaluated_present_query_pairs == 1
    assert summary.unavailable_origin_asset_ids == ("removed",)
    assert summary.unavailable_service_ids == ("gone",)
    assert summary.noncomparable_service_ids == ("svc_plc",)
    with pytest.raises(ModelError):
        summarize_exposure(snap, replace(result, snapshot_sha256="bad"))
    with pytest.raises(ModelError):
        summarize_exposure(snap, replace(result, queries=result.queries * 2))


def test_new_service_access_is_not_new_destination_asset(minimal: dict[str, Any]) -> None:
    before = deepcopy(minimal)
    before["services"].append(
        {
            **deepcopy(before["services"][0]),
            "id": "second",
            "destination_ports": [{"start": 503, "end": 504}],
        }
    )
    before["scenarios"][0]["destination_service_ids"].append("second")
    after = deepcopy(before)
    after["rules"][0]["destination_ports"][0]["end"] = 503
    comparison = compare_bytes(
        yaml.safe_dump(before).encode(), yaml.safe_dump(after).encode(), "engineering_scope"
    )
    explanation = explain_comparison(comparison)
    assert explanation.source_service_tuples_gaining_ports == 1
    assert explanation.newly_reachable_source_service_pairs == 1
    assert explanation.newly_reachable_destination_assets == 0
    assert explanation.declaration_changes[0].entity_kind == "rules"
    assert "no unique causal attribution" in explanation.interpretation
    # Further expansion within that already reachable tuple gains ports, not a pair.
    more = deepcopy(after)
    more["rules"][0]["destination_ports"][0]["end"] = 504
    more_comparison = compare_bytes(
        yaml.safe_dump(after).encode(), yaml.safe_dump(more).encode(), "engineering_scope"
    )
    more_explanation = explain_comparison(more_comparison)
    assert more_explanation.source_service_tuples_gaining_ports == 1
    assert more_explanation.newly_reachable_source_service_pairs == 0


def test_additive_html_keeps_json_and_independent_intents(boundary: dict[str, Any]) -> None:
    before = validate_bytes(yaml.safe_dump(boundary).encode())
    after_raw = deepcopy(boundary)
    after_raw["rules"][1]["edge_ids"].remove("f_dmz_ot")
    after = validate_bytes(yaml.safe_dump(after_raw).encode())
    result = compare_bytes(
        yaml.safe_dump(boundary).encode(), yaml.safe_dump(after_raw).encode(), "support_scope"
    )
    report = build_report("comparison", (before, after), result)
    original = json_report(report)
    html = html_report(report, (before, after), analysis=result).decode()
    assert 'id="finite-summary"' in html and "no unique causal attribution" in html
    assert "Newly broken required intervals" in html and not result.passed
    assert json_report(report) == original
    parser = OfflineHTML()
    parser.feed(html)
    assert parser.csp
    assert html == html_report(report, (before, after), analysis=result).decode()
    with pytest.raises(ValueError):
        html_report(
            report, (before, after), analysis=replace(result, newly_reachable=())
        ) if result.newly_reachable else html_report(
            report, (before, after), analysis=replace(result, passed=True)
        )


@pytest.mark.parametrize(
    "attack",
    ["</pre><script>alert(1)</script>", '<a href="javascript:x">', 'á😀 & < > "' + "\uffff"],
)
def test_trace_html_escaping_and_local_fragments(minimal: dict[str, Any], attack: str) -> None:
    result = trace_bytes(yaml.safe_dump(minimal).encode(), "eng", "svc_plc", policy_evidence=True)
    result = replace(result, interpretation=attack)
    html = trace_html(result).decode()
    parser = OfflineHTML()
    parser.feed(html)
    assert parser.csp and not parser.svgs
    assert asdict(result)["interpretation"] == attack
