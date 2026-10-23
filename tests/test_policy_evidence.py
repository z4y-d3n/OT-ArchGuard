"""Finite policy truth tables directly from raw declarations, without compiler reuse."""

from copy import deepcopy
from dataclasses import replace
from typing import Any

import pytest
import yaml
from test_reachability_oracle import synthetic

from otarchguard.api import validate_bytes
from otarchguard.contract import RESOURCE_LIMITS
from otarchguard.diagnostics import ModelError
from otarchguard.policy_evidence import PolicyEvidence, policy_evidence_for_query
from otarchguard.reachability import ReachabilityEngine
from otarchguard.trace import trace_bytes


def raw_matches(
    data: dict[str, Any], source: str, service_id: str, rule: dict[str, Any]
) -> set[tuple[str, int]]:
    assets = {a["id"]: a for a in data["assets"]}
    service = next(s for s in data["services"] if s["id"] == service_id)

    def selects(selector: dict[str, Any], identity: str) -> bool:
        return bool(
            selector.get("all_assets")
            or identity in selector.get("asset_ids", [])
            or assets[identity]["zone_id"] in selector.get("zone_ids", [])
        )

    if (
        rule["protocol"] != service["protocol"]
        or not selects(rule["source"], source)
        or not selects(rule["destination"], service["asset_id"])
    ):
        return set()
    return {
        (edge, port)
        for edge in rule["edge_ids"]
        for interval in service["destination_ports"]
        for port in range(interval["start"], interval["end"] + 1)
        if any(p["start"] <= port <= p["end"] for p in rule["destination_ports"])
    }


@pytest.mark.parametrize("seed", range(36))
def test_raw_policy_oracle(minimal: dict[str, Any], seed: int) -> None:
    data = synthetic(minimal, seed)
    # Guaranteed same-scoped and outside-scope differences, and duplicate denies.
    if data["rules"]:
        for index, effect in enumerate(("allow", "allow", "deny", "deny")):
            rule = deepcopy(data["rules"][0])
            rule.update(
                id=f"dupe_{index}",
                source={"all_assets": True},
                destination={"all_assets": True},
                protocol="tcp",
                effect=effect,
                destination_ports=[{"start": 1, "end": 8 + index % 2}],
            )
            data["rules"].append(rule)
    for source in ("eng", "gwa"):
        for service in ("svc_plc", "svc_udp"):
            result = trace_bytes(
                yaml.safe_dump(data).encode(), source, service, policy_evidence=True
            )
            evidence = result.policy_evidence
            assert isinstance(evidence, PolicyEvidence)
            matches = {r["id"]: raw_matches(data, source, service, r) for r in data["rules"]}
            effects = {r["id"]: r["effect"] for r in data["rules"]}
            expected_groups: dict[tuple[str, frozenset[tuple[str, int]]], set[str]] = {}
            for identity, domain in matches.items():
                if domain:
                    expected_groups.setdefault((effects[identity], frozenset(domain)), set()).add(
                        identity
                    )
            expected = {frozenset(ids) for ids in expected_groups.values() if len(ids) > 1}
            assert {frozenset(d.rule_ids) for d in evidence.scoped_duplicate_effects} == expected
            for group in evidence.scoped_duplicate_effects:
                observed = {
                    (edge, p)
                    for edge in group.matching_domain.edge_ids
                    for start, end in group.matching_domain.destination_ports
                    for p in range(start, end + 1)
                }
                assert all(observed == matches[r] for r in group.rule_ids)
            assert set(evidence.no_match_in_scope_rule_ids) == {
                r for r, domain in matches.items() if not domain
            }
            actual_overlap = {}
            for overlap in evidence.allow_deny_overlaps:
                assert overlap.effective_decision == "explicit_deny"
                assert overlap.source_asset_id == source
                for port in range(overlap.start, overlap.end + 1):
                    key = (overlap.edge_id, port)
                    assert key not in actual_overlap
                    actual_overlap[key] = (set(overlap.allow_rule_ids), set(overlap.deny_rule_ids))
            expected_overlap = {}
            for edge in data["transport_edges"] + data["forwarding_edges"]:
                for port in range(1, 9):
                    allow = {
                        r
                        for r, domain in matches.items()
                        if (edge["id"], port) in domain and effects[r] == "allow"
                    }
                    deny = {
                        r
                        for r, domain in matches.items()
                        if (edge["id"], port) in domain and effects[r] == "deny"
                    }
                    if allow and deny:
                        expected_overlap[(edge["id"], port)] = (allow, deny)
            assert actual_overlap == expected_overlap
            assert (
                evidence.work.edge_rule_atom_checks == evidence.work.planned_edge_rule_atom_checks
            )
            assert (
                evidence.work.edge_atom_evaluations == evidence.work.planned_edge_atom_evaluations
            )
            plain = trace_bytes(yaml.safe_dump(data).encode(), source, service)
            assert plain.intervals == result.intervals and plain.work == result.work
            reordered = deepcopy(data)
            for field in ("rules", "transport_edges", "forwarding_edges", "assets", "services"):
                reordered[field].reverse()
            assert (
                trace_bytes(
                    yaml.safe_dump(reordered).encode(), source, service, policy_evidence=True
                )
                == result
            )


def test_policy_evidence_budget_checked_before_predicates(
    minimal: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    snap = validate_bytes(yaml.safe_dump(minimal).encode())
    # One reachability predicate reservation fits, the added one does not.
    engine = ReachabilityEngine(snap, limits=replace(RESOURCE_LIMITS, edge_rule_atom_checks=1))
    query = engine.evaluate("eng", "svc_plc")

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("No diagnostic enumeration may start before the prospective rejection")

    monkeypatch.setattr("otarchguard.policy_evidence.decide", forbidden)
    with pytest.raises(ModelError) as error:
        policy_evidence_for_query(engine, query)
    assert error.value.diagnostics[0].category == "resource_limit"
    with pytest.raises(ModelError):
        policy_evidence_for_query(engine, replace(query, destination_asset_id="eng"))
    with pytest.raises(ModelError):
        policy_evidence_for_query(engine, replace(query, service_id="missing"))


def test_owner_selector_and_edges_are_part_of_duplicate_domain(minimal: dict[str, Any]) -> None:
    data = deepcopy(minimal)
    data["transport_edges"].append({**data["transport_edges"][0], "id": "other_edge"})
    for identity, edges, source, protocol in (
        ("same", ["t_eng_plc"], {"zone_ids": ["control"]}, "tcp"),
        ("other", ["other_edge"], {"all_assets": True}, "tcp"),
        ("udp", ["t_eng_plc"], {"all_assets": True}, "udp"),
        ("outside", ["t_eng_plc"], {"asset_ids": ["plc"]}, "tcp"),
    ):
        data["rules"].append(
            {
                **deepcopy(data["rules"][0]),
                "id": identity,
                "edge_ids": edges,
                "source": source,
                "protocol": protocol,
            }
        )
    result = trace_bytes(yaml.safe_dump(data).encode(), "eng", "svc_plc", policy_evidence=True)
    evidence = result.policy_evidence
    assert isinstance(evidence, PolicyEvidence)
    assert [d.rule_ids for d in evidence.scoped_duplicate_effects] == [("allow_eng_plc", "same")]
    assert evidence.no_match_in_scope_rule_ids == ("outside", "udp")
