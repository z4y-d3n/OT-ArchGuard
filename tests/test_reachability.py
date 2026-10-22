"""T04–T13 and boundary B01–B12: exact, directed initiation semantics."""

from copy import deepcopy
from dataclasses import asdict, replace
from typing import Any

import pytest
import yaml

from otarchguard.api import validate_bytes
from otarchguard.contract import RESOURCE_LIMITS
from otarchguard.diagnostics import ModelError
from otarchguard.graph import State, build_graph
from otarchguard.intents import check_bytes
from otarchguard.policy import Work
from otarchguard.reachability import ReachabilityEngine, evaluate_query


def encoded(data: dict[str, Any]) -> bytes:
    return yaml.safe_dump(data, sort_keys=False).encode()


def query(data: dict[str, Any], source: str, service: str) -> bool:
    return all(
        r.reachable
        for r in evaluate_query(validate_bytes(encoded(data)), source, service).intervals
    )


def test_t04_explicit_edge_and_every_edge_permission(minimal: dict[str, Any]) -> None:
    minimal["transport_edges"] = []
    minimal["rules"] = []
    assert not query(minimal, "eng", "svc_plc")
    minimal["transport_edges"] = [
        {"id": "t", "source_interface_id": "eng_net", "destination_interface_id": "plc_net"}
    ]
    assert not query(minimal, "eng", "svc_plc")
    minimal["rules"] = [
        {
            "id": "allow",
            "edge_ids": ["t"],
            "source": {"asset_ids": ["eng"]},
            "destination": {"asset_ids": ["plc"]},
            "protocol": "tcp",
            "destination_ports": [{"start": 502, "end": 502}],
            "effect": "allow",
        }
    ]
    assert query(minimal, "eng", "svc_plc")


def test_t05_direction_and_protocol(minimal: dict[str, Any]) -> None:
    minimal["transport_edges"].append(
        {"id": "reverse", "source_interface_id": "plc_net", "destination_interface_id": "eng_net"}
    )
    minimal["rules"][0]["edge_ids"].append("reverse")
    minimal["services"].extend(
        [
            {
                "id": "svc_eng",
                "asset_id": "eng",
                "interface_id": "eng_net",
                "protocol": "tcp",
                "destination_ports": [{"start": 502, "end": 502}],
            },
            {
                "id": "svc_udp",
                "asset_id": "plc",
                "interface_id": "plc_net",
                "protocol": "udp",
                "destination_ports": [{"start": 502, "end": 502}],
            },
        ]
    )
    assert query(minimal, "eng", "svc_plc")
    assert not query(minimal, "plc", "svc_eng")
    assert not query(minimal, "eng", "svc_udp")


def test_t06_boundary_states_and_witness(boundary: dict[str, Any]) -> None:
    validated = validate_bytes(encoded(boundary))
    graph = build_graph(validated.model, RESOURCE_LIMITS)
    assert len(graph.adjacency) == 2 * len(validated.model.interfaces)
    assert graph.edges["f_dmz_ot"].source == State("fw_dmz", "ingress")
    assert graph.edges["f_dmz_ot"].target == State("fw_ot", "egress")
    engine = ReachabilityEngine(validated)
    result = engine.evaluate("jump", "svc_scada")
    witness = result.intervals[0].witness
    assert witness is not None
    assert [s.edge_id for s in witness.steps] == ["t_jump_fw", "f_dmz_ot", "t_fw_scada"]
    assert witness.steps[1].conduit_id == "c_dmz_ot"
    assert all(s.allow_rule_ids == ("allow_jump_scada",) for s in witness.steps)
    assert (witness.source_asset_id, witness.destination_asset_id) == ("jump", "scada")
    assert engine.replay(witness)
    assert not engine.replay(replace(witness, snapshot_sha256="wrong"))
    assert not engine.replay(replace(witness, source_asset_id="it"))
    assert not engine.replay(replace(witness, end=3390))
    assert not engine.replay(replace(witness, steps=witness.steps[1:]))
    damaged = replace(witness.steps[1], allow_rule_ids=())
    assert not engine.replay(replace(witness, steps=(witness.steps[0], damaged, witness.steps[2])))


def test_b01_all_independent_intents(boundary: dict[str, Any]) -> None:
    result = check_bytes(encoded(boundary))
    assert result.passed and len(result.intents) == 8
    assert result.failed_intent_count == result.failed_interval_count == 0
    assert sum(r.reachable for i in result.intents for q in i.queries for r in q.intervals) == 4
    assert result.atom_queries == 10


@pytest.mark.parametrize("mutation", ["B02", "B03", "B04", "B05"])
def test_boundary_regressions(boundary: dict[str, Any], mutation: str) -> None:
    if mutation == "B02":
        boundary["forwarding_edges"] = [
            e for e in boundary["forwarding_edges"] if e["id"] != "f_dmz_ot"
        ]
        for rule in boundary["rules"]:
            rule["edge_ids"] = [e for e in rule["edge_ids"] if e != "f_dmz_ot"]
    elif mutation == "B03":
        boundary["rules"][1]["edge_ids"].remove("f_dmz_ot")
    elif mutation == "B04":
        deny = deepcopy(boundary["rules"][1])
        deny.update(id="deny_jump_scada", effect="deny", edge_ids=["f_dmz_ot"])
        boundary["rules"].append(deny)
    else:
        boundary["rules"][1]["source"] = {"asset_ids": ["fw"]}
    result = check_bytes(encoded(boundary))
    assert not result.passed and result.failed_intent_count == 1
    required = next(i for i in result.intents if i.id == "req_jump_scada")
    assert not required.passed
    diagnostic = required.queries[0].intervals[0].diagnostics
    assert diagnostic is not None
    assert diagnostic.structural_path_exists == (mutation != "B02")
    if mutation == "B04":
        assert diagnostic.blocked_edges[0].deny_rule_ids == ("deny_jump_scada",)
    assert query(boundary, "scada", "svc_plc")


def test_b06_no_application_pivot_or_forwarding_chain(boundary: dict[str, Any]) -> None:
    assert query(boundary, "it", "svc_jump")
    assert query(boundary, "jump", "svc_scada")
    assert not query(boundary, "it", "svc_scada")
    assert not query(boundary, "it", "svc_plc")
    boundary["rules"].append(
        {
            "id": "all_explicit_edges",
            "effect": "allow",
            "source": {"all_assets": True},
            "destination": {"all_assets": True},
            "protocol": "tcp",
            "destination_ports": [{"start": 1, "end": 65535}],
            "edge_ids": [
                e["id"] for e in boundary["transport_edges"] + boundary["forwarding_edges"]
            ],
        }
    )
    result = evaluate_query(validate_bytes(encoded(boundary)), "it", "svc_scada")
    assert not result.intervals[0].reachable
    assert result.intervals[0].diagnostics is not None
    assert not result.intervals[0].diagnostics.structural_path_exists


def test_b07_listener_binding(boundary: dict[str, Any]) -> None:
    boundary["rules"].append(
        {
            "id": "allow_it_fw",
            "effect": "allow",
            "source": {"asset_ids": ["it"]},
            "destination": {"asset_ids": ["fw"]},
            "protocol": "tcp",
            "destination_ports": [{"start": 443, "end": 443}],
            "edge_ids": ["t_it_fw"],
        }
    )
    assert not query(boundary, "it", "svc_fw")
    assert check_bytes(encoded(boundary)).passed


def test_b08_reverse_initiation_is_independent(boundary: dict[str, Any]) -> None:
    boundary["intents"][-1]["destination_service_ids"].remove("svc_jump")
    boundary["intents"].append(
        {
            "id": "reverse_required",
            "kind": "required",
            "source": {"asset_ids": ["scada"]},
            "destination_service_ids": ["svc_jump"],
        }
    )
    result = check_bytes(encoded(boundary))
    assert not next(i for i in result.intents if i.id == "reverse_required").passed


def test_t07_required_and_prohibited_are_independent(minimal: dict[str, Any]) -> None:
    minimal["intents"][0]["kind"] = "prohibited"
    result = check_bytes(encoded(minimal))
    assert not result.passed
    assert result.intents[0].queries[0].intervals[0].witness is not None
    minimal["rules"] = []
    assert check_bytes(encoded(minimal)).passed


def test_t08_deny_order_and_alternate_path(minimal: dict[str, Any]) -> None:
    edge = {**minimal["transport_edges"][0], "id": "alternate"}
    minimal["transport_edges"].append(edge)
    minimal["rules"][0]["edge_ids"].append("alternate")
    deny = deepcopy(minimal["rules"][0])
    deny.update(id="deny", effect="deny", edge_ids=["t_eng_plc"])
    minimal["rules"].append(deny)
    first = check_bytes(encoded(minimal))
    assert first.passed
    witness = first.intents[0].queries[0].intervals[0].witness
    assert witness is not None and witness.steps[0].edge_id == "alternate"
    minimal["rules"].reverse()
    assert asdict(check_bytes(encoded(minimal))) == asdict(first)


def test_t09_shared_ingress_transport_cannot_relay(boundary: dict[str, Any]) -> None:
    boundary["transport_edges"].append(
        {"id": "t_fake_relay", "source_interface_id": "fw_it", "destination_interface_id": "it_net"}
    )
    boundary["services"].append(
        {
            "id": "svc_it",
            "asset_id": "it",
            "interface_id": "it_net",
            "protocol": "tcp",
            "destination_ports": [{"start": 443, "end": 443}],
        }
    )
    # IT->fw_it arrival cannot use another transport out of fw_it without forwarding.
    boundary["rules"].append(
        {
            "id": "allow_all",
            "effect": "allow",
            "source": {"all_assets": True},
            "destination": {"all_assets": True},
            "protocol": "tcp",
            "destination_ports": [{"start": 1, "end": 65535}],
            "edge_ids": ["t_it_fw", "t_fake_relay"],
        }
    )
    assert not query(boundary, "jump", "svc_it")


def test_t10_parallel_tie_determinism_and_cycle(boundary: dict[str, Any]) -> None:
    boundary["transport_edges"].append(
        {
            "id": "a_parallel",
            "source_interface_id": "jump_net",
            "destination_interface_id": "fw_dmz",
        }
    )
    boundary["rules"][1]["edge_ids"].append("a_parallel")
    result = evaluate_query(validate_bytes(encoded(boundary)), "jump", "svc_scada")
    witness = result.intervals[0].witness
    assert witness is not None and witness.steps[0].edge_id == "a_parallel"
    boundary["rules"].reverse()
    boundary["transport_edges"].reverse()
    assert evaluate_query(validate_bytes(encoded(boundary)), "jump", "svc_scada") == result


def test_t12_and_t13_exact_ranges(minimal: dict[str, Any]) -> None:
    minimal["services"][0]["destination_ports"] = [{"start": 100, "end": 200}]
    minimal["rules"][0]["destination_ports"] = [{"start": 100, "end": 200}]
    deny = deepcopy(minimal["rules"][0])
    deny.update(id="deny_middle", effect="deny", destination_ports=[{"start": 150, "end": 160}])
    minimal["rules"].append(deny)
    result = check_bytes(encoded(minimal))
    intervals = result.intents[0].queries[0].intervals
    assert [(r.start, r.end, r.reachable) for r in intervals] == [
        (100, 149, True),
        (150, 160, False),
        (161, 200, True),
    ]
    assert sum(r.end - r.start + 1 for r in intervals if r.reachable) == 90
    assert not result.passed
    minimal["intents"][0]["kind"] = "prohibited"
    assert not check_bytes(encoded(minimal)).passed


def test_required_all_ports_not_samples(minimal: dict[str, Any]) -> None:
    minimal["services"][0]["destination_ports"] = [{"start": 500, "end": 502}]
    minimal["rules"][0]["destination_ports"] = [
        {"start": 500, "end": 500},
        {"start": 502, "end": 502},
    ]
    result = check_bytes(encoded(minimal))
    assert not result.passed and result.failed_interval_count == 1
    failed = [r for r in result.intents[0].queries[0].intervals if not r.reachable]
    assert [(r.start, r.end) for r in failed] == [(501, 501)]


def test_source_can_start_at_any_boundary_interface(boundary: dict[str, Any]) -> None:
    boundary["rules"].append(
        {
            "id": "fw_local",
            "effect": "allow",
            "source": {"asset_ids": ["fw"]},
            "destination": {"asset_ids": ["plc"]},
            "protocol": "tcp",
            "destination_ports": [{"start": 502, "end": 502}],
            "edge_ids": ["t_fw_plc"],
        }
    )
    assert query(boundary, "fw", "svc_plc")


def test_self_query_is_unsupported(minimal: dict[str, Any]) -> None:
    with pytest.raises(ModelError) as caught:
        evaluate_query(validate_bytes(encoded(minimal)), "plc", "svc_plc")
    assert caught.value.diagnostics[0].code == "UNSUPPORTED_QUERY"


@pytest.mark.parametrize(
    "limit",
    [
        "protocol_port_atoms",
        "state_edge_visits",
        "edge_rule_atom_checks",
        "edges",
        "interfaces",
        "edge_rule_associations",
        "rules",
    ],
)
def test_resource_errors_are_never_unreachable(minimal: dict[str, Any], limit: str) -> None:
    with pytest.raises(ModelError) as caught:
        check_bytes(encoded(minimal), replace(RESOURCE_LIMITS, **{limit: 0}))
    assert caught.value.diagnostics[0].category == "resource_limit"
    assert caught.value.diagnostics[0].code == "LIMIT_EXCEEDED"


def test_work_bound_exact_boundaries(minimal: dict[str, Any]) -> None:
    # One atom, four states and one edge: 3*(4+1)=15 planned visits, one rule association.
    assert check_bytes(
        encoded(minimal), replace(RESOURCE_LIMITS, state_edge_visits=15, edge_rule_atom_checks=1)
    ).passed
    with pytest.raises(ModelError):
        check_bytes(encoded(minimal), replace(RESOURCE_LIMITS, state_edge_visits=14))


def test_diagnostic_frontier_is_bounded(minimal: dict[str, Any]) -> None:
    minimal["rules"] = []
    minimal["transport_edges"] = [
        {
            "id": f"parallel_{i:02}",
            "source_interface_id": "eng_net",
            "destination_interface_id": "plc_net",
        }
        for i in range(25)
    ]
    result = check_bytes(encoded(minimal))
    diagnostic = result.intents[0].queries[0].intervals[0].diagnostics
    assert diagnostic is not None and diagnostic.structural_path_exists
    assert diagnostic.blocked_edge_count == 25 and len(diagnostic.blocked_edges) == 20
    assert diagnostic.truncated
    assert result.failed_interval_count == 1


def test_no_intents_is_explicitly_empty_not_scenario_evaluation(minimal: dict[str, Any]) -> None:
    minimal["intents"] = []
    result = check_bytes(encoded(minimal))
    assert result.passed and result.intents == () and result.atom_queries == 0


def chain(minimal: dict[str, Any]) -> dict[str, Any]:
    for name, offset in (("gwa", 30), ("gwb", 40)):
        minimal["assets"].append({**minimal["assets"][0], "id": name, "kind": "boundary_device"})
        for i in range(2):
            minimal["interfaces"].append(
                {
                    "id": f"{name}_{i}",
                    "asset_id": name,
                    "placement_zone_id": "control",
                    "ipv4": f"198.51.100.{offset + i}/24",
                }
            )
    minimal["transport_edges"] = [
        {"id": "entry", "source_interface_id": "eng_net", "destination_interface_id": "gwa_0"},
        {"id": "middle", "source_interface_id": "gwa_1", "destination_interface_id": "gwb_0"},
        {"id": "loop", "source_interface_id": "gwb_1", "destination_interface_id": "gwa_0"},
        {"id": "exit", "source_interface_id": "gwb_1", "destination_interface_id": "plc_net"},
    ]
    minimal["forwarding_edges"] = [
        {"id": f"f_{name}", "ingress_interface_id": f"{name}_0", "egress_interface_id": f"{name}_1"}
        for name in ("gwa", "gwb")
    ]
    minimal["rules"][0]["edge_ids"] = [
        e["id"] for e in minimal["transport_edges"] + minimal["forwarding_edges"]
    ]
    return minimal


def test_cycle_terminates_and_shortest_path_wins(minimal: dict[str, Any]) -> None:
    data = chain(minimal)
    witness = evaluate_query(validate_bytes(encoded(data)), "eng", "svc_plc").intervals[0].witness
    assert witness is not None and len(witness.steps) == 5
    data["transport_edges"].append(
        {"id": "direct", "source_interface_id": "eng_net", "destination_interface_id": "plc_net"}
    )
    data["rules"][0]["edge_ids"].append("direct")
    witness = evaluate_query(validate_bytes(encoded(data)), "eng", "svc_plc").intervals[0].witness
    assert witness is not None and len(witness.steps) == 1
    data["transport_edges"] = [
        e for e in data["transport_edges"] if e["id"] not in {"exit", "direct"}
    ]
    data["rules"][0]["edge_ids"] = [
        e for e in data["rules"][0]["edge_ids"] if e not in {"exit", "direct"}
    ]
    result = evaluate_query(validate_bytes(encoded(data)), "eng", "svc_plc")
    assert not result.intervals[0].reachable
    assert result.intervals[0].diagnostics is not None
    assert result.intervals[0].diagnostics.reason == "no_structural_path"


def test_shared_interface_is_not_an_implicit_relay(minimal: dict[str, Any]) -> None:
    data = chain(minimal)
    data["forwarding_edges"] = [e for e in data["forwarding_edges"] if e["id"] != "f_gwa"]
    data["rules"][0]["edge_ids"].remove("f_gwa")
    data["transport_edges"][1]["source_interface_id"] = "gwa_0"
    assert not query(data, "eng", "svc_plc")


def test_default_atom_limit_rejects_dense_interval_boundaries(minimal: dict[str, Any]) -> None:
    minimal["services"][0]["destination_ports"] = [{"start": 1, "end": 65535}]
    for i in range(1025):
        rule = deepcopy(minimal["rules"][0])
        rule.update(id=f"boundary_{i}", destination_ports=[{"start": 2 * i + 2, "end": 2 * i + 2}])
        minimal["rules"].append(rule)
    with pytest.raises(ModelError) as caught:
        check_bytes(encoded(minimal))
    assert caught.value.diagnostics[0].category == "resource_limit"
    assert "protocol_port_atoms" in caught.value.diagnostics[0].message


def test_runtime_counter_rejects_even_if_estimate_were_wrong(minimal: dict[str, Any]) -> None:
    engine = ReachabilityEngine(validate_bytes(encoded(minimal)))
    engine.work = Work(replace(RESOURCE_LIMITS, state_edge_visits=0))
    with pytest.raises(ModelError) as caught:
        engine.evaluate("eng", "svc_plc")
    assert caught.value.diagnostics[0].category == "resource_limit"


def test_preflight_stops_before_any_bfs(
    minimal: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("BFS must not start when planned work exceeds budget")

    monkeypatch.setattr(ReachabilityEngine, "_search", forbidden)
    with pytest.raises(ModelError) as caught:
        check_bytes(encoded(minimal), replace(RESOURCE_LIMITS, state_edge_visits=1))
    assert caught.value.diagnostics[0].category == "resource_limit"


@pytest.mark.parametrize("protocol", ["tcp", "udp"])
def test_exact_port_extremes_without_enumeration(minimal: dict[str, Any], protocol: str) -> None:
    minimal["services"][0].update(protocol=protocol, destination_ports=[{"start": 1, "end": 65535}])
    minimal["rules"][0].update(protocol=protocol, destination_ports=[{"start": 1, "end": 65535}])
    deny = deepcopy(minimal["rules"][0])
    deny.update(id="deny_last", effect="deny", destination_ports=[{"start": 65535, "end": 65535}])
    minimal["rules"].append(deny)
    result = evaluate_query(validate_bytes(encoded(minimal)), "eng", "svc_plc")
    assert [(i.start, i.end, i.reachable) for i in result.intervals] == [
        (1, 65534, True),
        (65535, 65535, False),
    ]


def test_policy_zone_selectors_use_ownership(boundary: dict[str, Any]) -> None:
    boundary["rules"][0]["source"] = {"zone_ids": ["enterprise"]}
    assert query(boundary, "it", "svc_jump")
    assert not query(boundary, "fw", "svc_jump")
    boundary["rules"][1]["source"] = {"zone_ids": ["dmz"]}
    assert query(boundary, "jump", "svc_scada")
    assert query(boundary, "fw", "svc_scada")


def test_atom_budget_is_combined_across_protocols(minimal: dict[str, Any]) -> None:
    udp = deepcopy(minimal["services"][0])
    udp.update(id="svc_udp", protocol="udp")
    minimal["services"].append(udp)
    minimal["intents"][0]["destination_service_ids"].append("svc_udp")
    assert not check_bytes(encoded(minimal), replace(RESOURCE_LIMITS, protocol_port_atoms=2)).passed
    with pytest.raises(ModelError) as caught:
        check_bytes(encoded(minimal), replace(RESOURCE_LIMITS, protocol_port_atoms=1))
    assert "protocol_port_atoms" in caught.value.diagnostics[0].message
