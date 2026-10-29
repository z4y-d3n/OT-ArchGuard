"""Independent release counterexamples across the whole supported port domain."""

from copy import deepcopy
from dataclasses import replace
from typing import Any

import pytest
import yaml

from otarchguard.api import validate_bytes
from otarchguard.contract import RESOURCE_LIMITS
from otarchguard.diagnostics import ModelError
from otarchguard.intents import check_architecture
from otarchguard.reachability import ReachabilityEngine
from otarchguard.reporting import build_report
from otarchguard.trace import trace_architecture
from otarchguard.trace_reporting import trace_json


def _closed_domain(minimal: dict[str, Any]) -> dict[str, Any]:
    """A single link with both edge ports denied and every interior port allowed."""
    data = deepcopy(minimal)
    data["services"][0]["destination_ports"] = [{"start": 1, "end": 65535}]
    data["rules"][0]["destination_ports"] = [{"start": 1, "end": 65535}]
    for identity, port in (("deny_first", 1), ("deny_last", 65535)):
        data["rules"].append(
            {
                **deepcopy(data["rules"][0]),
                "id": identity,
                "effect": "deny",
                "destination_ports": [{"start": port, "end": port}],
            }
        )
    return data


def test_entire_closed_port_domain_and_rule_permutation(minimal: dict[str, Any]) -> None:
    data = _closed_domain(minimal)
    validated = validate_bytes(yaml.safe_dump(data).encode())
    result = trace_architecture(validated, "eng", "svc_plc")
    # Literal closed-interval answer follows directly from the three raw rules.
    assert [(i.start, i.end, i.reachable) for i in result.intervals] == [
        (1, 1, False),
        (2, 65534, True),
        (65535, 65535, False),
    ]
    assert result.work.query_atoms == 3
    for interval, deny_id in (
        (result.intervals[0], "deny_first"),
        (result.intervals[2], "deny_last"),
    ):
        assert interval.witness is None
        assert interval.diagnostics is not None
        assert interval.diagnostics.structural_path_exists
        assert interval.diagnostics.reason == "no_permitted_path"
        assert interval.diagnostics.blocked_edges[0].reason == "explicit_deny"
        assert interval.diagnostics.blocked_edges[0].deny_rule_ids == (deny_id,)
    witness = result.intervals[1].witness
    assert witness is not None
    assert witness.snapshot_sha256 == validated.sha256
    assert tuple(s.edge_id for s in witness.steps) == ("t_eng_plc",)
    assert witness.steps[0].allow_rule_ids == ("allow_eng_plc",)
    data["rules"].reverse()
    reordered = trace_architecture(validate_bytes(yaml.safe_dump(data).encode()), "eng", "svc_plc")
    assert trace_json(reordered) == trace_json(result)


@pytest.mark.parametrize("kind", ["required", "prohibited"])
def test_partial_reachability_fails_both_independent_intent_kinds(
    minimal: dict[str, Any], kind: str
) -> None:
    data = _closed_domain(minimal)
    data["intents"][0]["kind"] = kind
    result = check_architecture(validate_bytes(yaml.safe_dump(data).encode()))
    assert not result.passed
    assert not result.intents[0].passed
    assert result.failed_intent_count == 1
    assert result.failed_interval_count == (2 if kind == "required" else 1)
    assert [(i.start, i.end, i.reachable) for i in result.intents[0].queries[0].intervals] == [
        (1, 1, False),
        (2, 65534, True),
        (65535, 65535, False),
    ]


def test_identical_topology_different_revision_cannot_reuse_native_evidence(
    minimal: dict[str, Any],
) -> None:
    first = validate_bytes(yaml.safe_dump(minimal).encode())
    engine = ReachabilityEngine(first)
    witness = engine.evaluate("eng", "svc_plc").intervals[0].witness
    assert witness is not None
    check = check_architecture(first)
    minimal["revision"] = "different_owner_revision"
    second = validate_bytes(yaml.safe_dump(minimal).encode())
    assert first.sha256 != second.sha256
    second_engine = ReachabilityEngine(second)
    assert second_engine.evaluate("eng", "svc_plc").intervals[0].reachable
    assert not second_engine.replay(witness)
    with pytest.raises(ValueError, match="snapshot hashes"):
        build_report("check", (second,), check)


def test_query_budget_rejects_before_any_atom_can_be_assessed(
    minimal: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    validated = validate_bytes(yaml.safe_dump(_closed_domain(minimal)).encode())
    engine = ReachabilityEngine(validated, limits=replace(RESOURCE_LIMITS, edge_rule_atom_checks=8))

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("A rejected prospective query must not execute even its first atom")

    monkeypatch.setattr(engine, "_atom", forbidden)
    with pytest.raises(ModelError) as error:
        engine.evaluate("eng", "svc_plc")
    assert error.value.diagnostics[0].category == "resource_limit"
    assert engine.queries_reserved == engine.work.state_edge_visits == 0
