"""Independent bounded concrete-port relations complement the established oracles."""

from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
import yaml
from test_reachability_oracle import oracle, replay_raw, synthetic

from otarchguard.api import validate_bytes, validate_file
from otarchguard.comparison import compare_architectures, compare_bytes, compare_files
from otarchguard.contract import RESOURCE_LIMITS
from otarchguard.diagnostics import ModelError
from otarchguard.exposure import exposure_architecture, exposure_bytes, exposure_file
from otarchguard.intents import check_architecture, check_bytes, check_file
from otarchguard.policy_evidence import PolicyEvidence
from otarchguard.trace import TraceResult, trace_bytes


def coverage(raw: dict[str, Any], service: str = "svc_plc") -> tuple[TraceResult, set[int]]:
    declaration = next(item for item in raw["services"] if item["id"] == service)
    declared_ports = {
        port
        for interval in declaration["destination_ports"]
        for port in range(interval["start"], interval["end"] + 1)
    }
    expected = {port: oracle(raw, "eng", service, port) for port in declared_ports}
    result = trace_bytes(yaml.safe_dump(raw).encode(), "eng", service, policy_evidence=True)
    scope_ports = [
        port
        for interval in result.scope.destination_ports
        for port in range(interval.start, interval.end + 1)
    ]
    assert set(scope_ports) == declared_ports
    assert len(scope_ports) == len(set(scope_ports))
    interval_ports = [
        port for interval in result.intervals for port in range(interval.start, interval.end + 1)
    ]
    assert set(interval_ports) == declared_ports
    assert len(interval_ports) == len(set(interval_ports))
    observed = {
        port: interval.reachable
        for interval in result.intervals
        for port in range(interval.start, interval.end + 1)
    }
    assert observed == expected
    for item in result.intervals:
        assert item.protocol == declaration["protocol"]
        if item.reachable:
            assert item.witness is not None and item.diagnostics is None
            replay_raw(raw, item.witness)
        else:
            assert item.witness is None and item.diagnostics is not None
    return result, {port for port, reachable in observed.items() if reachable}


@pytest.mark.parametrize(
    "mutation",
    [
        "scope_missing",
        "scope_extra",
        "interval_missing",
        "interval_extra",
        "interval_duplicate",
        "reachable_truth",
        "unreachable_truth",
    ],
)
def test_coverage_oracle_rejects_corrupted_trace(
    minimal: dict[str, Any], mutation: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    minimal["services"][0]["destination_ports"] = [{"start": 1, "end": 3}]
    minimal["rules"][0]["destination_ports"] = [{"start": 1, "end": 1}]
    result, ports = coverage(minimal)
    assert ports == {1}
    if mutation.startswith("scope_"):
        interval = replace(
            result.scope.destination_ports[0], end=1 if mutation == "scope_missing" else 4
        )
        corrupted = replace(result, scope=replace(result.scope, destination_ports=(interval,)))
    elif mutation == "interval_missing":
        corrupted = replace(result, intervals=result.intervals[:1])
    elif mutation == "interval_extra":
        extra = replace(result.intervals[-1], start=4, end=4)
        corrupted = replace(result, intervals=(*result.intervals, extra))
    elif mutation == "interval_duplicate":
        corrupted = replace(result, intervals=(*result.intervals, result.intervals[-1]))
    else:
        index = 0 if mutation == "reachable_truth" else 1
        intervals = list(result.intervals)
        intervals[index] = replace(intervals[index], reachable=not intervals[index].reachable)
        corrupted = replace(result, intervals=tuple(intervals))

    def corrupted_trace(*args: Any, **kwargs: Any) -> TraceResult:
        return corrupted

    monkeypatch.setattr(f"{__name__}.trace_bytes", corrupted_trace)
    with pytest.raises(AssertionError):
        coverage(minimal)


@pytest.mark.parametrize("seed", [104729, 130363, 155921, 196613])
def test_isolation_display_and_equivalent_rule_splitting(
    minimal: dict[str, Any], seed: int
) -> None:
    raw = synthetic(minimal, seed)
    # Guarantee mixed truth so splitting/display/isolation cannot pass solely
    # because every random route was already blocked. Keep the random surrounds.
    raw["transport_edges"].append(
        {
            "id": "controlled_path",
            "source_interface_id": "eng_net",
            "destination_interface_id": "plc_net",
        }
    )
    raw["rules"].extend(
        [
            {
                "id": "controlled_allow",
                "edge_ids": ["controlled_path"],
                "source": {"asset_ids": ["eng"]},
                "destination": {"asset_ids": ["plc"]},
                "protocol": "tcp",
                "effect": "allow",
                "destination_ports": [{"start": 1, "end": 8}],
            },
            {
                "id": "controlled_deny",
                "edge_ids": [e["id"] for e in raw["transport_edges"] + raw["forwarding_edges"]],
                "source": {"asset_ids": ["eng"]},
                "destination": {"asset_ids": ["plc"]},
                "protocol": "tcp",
                "effect": "deny",
                "destination_ports": [{"start": 3, "end": 4}],
            },
        ]
    )
    first, expected = coverage(raw)
    assert expected == {1, 2, 5, 6, 7, 8}
    isolated = deepcopy(raw)
    isolated["assets"].append({**isolated["assets"][0], "id": "isolated"})
    isolated["interfaces"].append(
        {
            "id": "isolated_if",
            "asset_id": "isolated",
            "placement_zone_id": "control",
            "ipv4": "203.0.113.254/24",
        }
    )
    assert coverage(isolated)[1] == expected
    display = deepcopy(raw)
    for record in display["assets"] + display["zones"]:
        record["name"] = "Changed display 😀"
    display["revision"] = "description only"
    assert coverage(display)[1] == expected
    split = deepcopy(raw)
    split["rules"] = []
    for rule in raw["rules"]:
        low = rule["destination_ports"][0]["start"]
        high = rule["destination_ports"][0]["end"]
        midpoint = (low + high) // 2
        ranges = [(low, midpoint)] + ([(midpoint + 1, high)] if midpoint < high else [])
        for index, (start, end) in enumerate(ranges):
            split["rules"].append(
                {
                    **deepcopy(rule),
                    "id": f"{rule['id']}_part{index}",
                    "destination_ports": [{"start": start, "end": end}],
                }
            )
    assert coverage(split)[1] == expected
    reordered = deepcopy(raw)
    for field in (
        "assets",
        "interfaces",
        "services",
        "rules",
        "transport_edges",
        "forwarding_edges",
    ):
        reordered[field].reverse()
    assert coverage(reordered)[0] == first
    assert coverage(raw)[0] == first


@pytest.mark.parametrize("protocol", ["tcp", "udp"])
def test_extreme_ports_parallel_associations_and_scope(
    minimal: dict[str, Any], protocol: str
) -> None:
    raw = minimal
    raw["services"][0].update(
        protocol=protocol,
        destination_ports=[
            {"start": 1, "end": 3},
            {"start": 65533, "end": 65535},
        ],
    )
    raw["services"].append(
        {
            **deepcopy(raw["services"][0]),
            "id": "other_protocol",
            "protocol": "udp" if protocol == "tcp" else "tcp",
        }
    )
    raw["transport_edges"].append({**raw["transport_edges"][0], "id": "parallel"})
    rule = raw["rules"][0]
    rule.update(protocol=protocol, destination_ports=[{"start": 1, "end": 65535}])
    raw["rules"].append(
        {
            **deepcopy(rule),
            "id": "nested_deny",
            "effect": "deny",
            "destination_ports": [{"start": 2, "end": 2}, {"start": 65534, "end": 65534}],
        }
    )
    result, ports = coverage(raw)
    assert ports == {1, 3, 65533, 65535}
    assert coverage(raw, "other_protocol")[1] == set()
    evidence = result.policy_evidence
    assert isinstance(evidence, PolicyEvidence)
    assert evidence.scope.examined_edge_ids == ("parallel", "t_eng_plc")
    assert {o.edge_id for o in evidence.allow_deny_overlaps} == {"t_eng_plc"}
    for interval in result.intervals:
        if interval.witness:
            assert [step.edge_id for step in interval.witness.steps] == ["t_eng_plc"]


def test_all_analytical_adapters_preserve_results_and_work(
    minimal: dict[str, Any], tmp_path: Path
) -> None:
    data = yaml.safe_dump(minimal).encode()
    path = tmp_path / "á same bytes.yaml"
    path.write_bytes(data)
    snap = validate_bytes(data)
    assert snap == validate_file(path)
    assert check_bytes(data) == check_file(path) == check_architecture(snap)
    assert (
        exposure_bytes(data, "engineering_scope")
        == exposure_file(path, "engineering_scope")
        == exposure_architecture(snap, "engineering_scope")
    )
    assert (
        compare_bytes(data, data, "engineering_scope")
        == compare_files(path, path, "engineering_scope")
        == compare_architectures(snap, snap, "engineering_scope")
    )


@pytest.mark.parametrize("budget", ["state_edge_visits", "edge_rule_atom_checks"])
@pytest.mark.parametrize("offset", [-1, 0, 1])
def test_raw_single_edge_prospective_and_evidence_work(
    minimal: dict[str, Any], budget: str, offset: int
) -> None:
    # Raw two interfaces => four phase states; one edge. One query atom reserves
    # 3*(4+1)=15 visits, plus one all-edge evidence row. One association reserves
    # one query predicate, plus one evidence predicate. Independent of actual BFS.
    ceiling = (16 if budget == "state_edge_visits" else 2) + offset
    limits = replace(RESOURCE_LIMITS, **{budget: ceiling})
    data = yaml.safe_dump(minimal).encode()
    if offset == -1:
        with pytest.raises(ModelError) as caught:
            trace_bytes(data, "eng", "svc_plc", limits, policy_evidence=True)
        assert caught.value.diagnostics[0].category == "resource_limit"
    else:
        result = trace_bytes(data, "eng", "svc_plc", limits, policy_evidence=True)
        assert result.work.query_atoms == 1
        assert result.work.state_edge_visits == 4  # start/edge/goal/witness replay
        assert result.work.edge_rule_atom_checks == 1
        evidence = result.policy_evidence
        assert isinstance(evidence, PolicyEvidence)
        assert evidence.work.edge_atom_evaluations == 1
        assert evidence.work.edge_rule_atom_checks == 1
