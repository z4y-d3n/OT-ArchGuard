"""Independent per-port simple-path oracle and fixed-seed synthetic graph properties."""

import random
from copy import deepcopy
from dataclasses import asdict
from typing import Any

import pytest
import yaml

from otarchguard.api import validate_bytes
from otarchguard.intents import check_bytes
from otarchguard.reachability import ReachabilityEngine, Witness, evaluate_query


def replay_raw(data: dict[str, Any], witness: Witness) -> None:
    """Independently inspect the supplied path, not merely whether some path exists."""
    interfaces = {i["id"]: i for i in data["interfaces"]}
    assets = {a["id"]: a for a in data["assets"]}
    service = next(s for s in data["services"] if s["id"] == witness.service_id)
    assert witness.destination_asset_id == service["asset_id"]
    current = witness.steps[0].source.state
    assert (
        current.phase == "egress"
        and interfaces[current.interface_id]["asset_id"] == witness.source_asset_id
    )

    def selected(selector: dict[str, Any], asset: str) -> bool:
        return bool(
            selector.get("all_assets")
            or asset in selector.get("asset_ids", [])
            or assets[asset]["zone_id"] in selector.get("zone_ids", [])
        )

    for step in witness.steps:
        assert step.source.state == current
        records = data["transport_edges"] if step.kind == "transport" else data["forwarding_edges"]
        raw = next(e for e in records if e["id"] == step.edge_id)
        left, right = (
            ("source_interface_id", "destination_interface_id")
            if step.kind == "transport"
            else ("ingress_interface_id", "egress_interface_id")
        )
        phases = ("egress", "ingress") if step.kind == "transport" else ("ingress", "egress")
        assert (step.source.state.interface_id, step.target.state.interface_id) == (
            raw[left],
            raw[right],
        )
        assert (step.source.state.phase, step.target.state.phase) == phases
        assert step.conduit_id == raw.get("conduit_id")
        for endpoint in (step.source, step.target):
            original = interfaces[endpoint.state.interface_id]
            assert (endpoint.asset_id, endpoint.placement_zone_id, endpoint.ipv4) == (
                original["asset_id"],
                original["placement_zone_id"],
                original["ipv4"],
            )
        matching = [
            r
            for r in data["rules"]
            if raw["id"] in r["edge_ids"]
            and selected(r["source"], witness.source_asset_id)
            and selected(r["destination"], witness.destination_asset_id)
            and r["protocol"] == witness.protocol
            and any(
                p["start"] <= witness.start <= witness.end <= p["end"]
                for p in r["destination_ports"]
            )
        ]
        assert not any(r["effect"] == "deny" for r in matching)
        assert step.allow_rule_ids == tuple(
            sorted(r["id"] for r in matching if r["effect"] == "allow")
        )
        assert step.allow_rule_ids
        current = step.target.state
    assert (current.interface_id, current.phase) == (service["interface_id"], "ingress")


def synthetic(base: dict[str, Any], seed: int) -> dict[str, Any]:
    data = deepcopy(base)
    generator = random.Random(seed)
    data["intents"] = []
    data["scenarios"] = []
    for name, offset in (("gwa", 30), ("gwb", 40)):
        data["assets"].append({**data["assets"][0], "id": name, "kind": "boundary_device"})
        for index in range(2):
            data["interfaces"].append(
                {
                    "id": f"{name}_{index}",
                    "asset_id": name,
                    "placement_zone_id": "control",
                    "ipv4": f"198.51.100.{offset + index}/24",
                }
            )
    data["services"][0]["destination_ports"] = [{"start": 1, "end": 8}]
    data["services"].append({**deepcopy(data["services"][0]), "id": "svc_udp", "protocol": "udp"})
    data["transport_edges"] = []
    data["forwarding_edges"] = []
    for left in data["interfaces"]:
        for right in data["interfaces"]:
            if left["asset_id"] != right["asset_id"] and generator.random() < 0.3:
                data["transport_edges"].append(
                    {
                        "id": f"t_{len(data['transport_edges'])}",
                        "source_interface_id": left["id"],
                        "destination_interface_id": right["id"],
                    }
                )
            elif (
                left["asset_id"] == right["asset_id"]
                and left["id"] != right["id"]
                and generator.random() < 0.7
            ):
                data["forwarding_edges"].append(
                    {
                        "id": f"f_{len(data['forwarding_edges'])}",
                        "ingress_interface_id": left["id"],
                        "egress_interface_id": right["id"],
                    }
                )
    data["rules"] = []
    for edge in data["transport_edges"] + data["forwarding_edges"]:
        for _ in range(generator.randint(0, 3)):
            low = generator.randint(1, 8)
            high = generator.randint(low, 8)
            data["rules"].append(
                {
                    "id": f"r_{len(data['rules'])}",
                    "edge_ids": [edge["id"]],
                    "source": generator.choice(
                        [{"all_assets": True}, {"asset_ids": ["eng"]}, {"asset_ids": ["gwa"]}]
                    ),
                    "destination": generator.choice(
                        [{"all_assets": True}, {"asset_ids": ["plc"]}, {"asset_ids": ["gwa"]}]
                    ),
                    "protocol": generator.choice(["tcp", "udp"]),
                    "destination_ports": [{"start": low, "end": high}],
                    "effect": generator.choice(["allow", "allow", "deny"]),
                }
            )
    return data


def oracle(data: dict[str, Any], origin: str, service_id: str, port: int) -> bool:
    """Raw declarations + recursive simple paths; no production evaluation helpers."""
    assets = {a["id"]: a for a in data["assets"]}
    service = next(s for s in data["services"] if s["id"] == service_id)

    def selects(selector: dict[str, Any], identity: str) -> bool:
        if "all_assets" in selector:
            return True
        if "asset_ids" in selector:
            return identity in selector["asset_ids"]
        return assets[identity]["zone_id"] in selector["zone_ids"]

    def permitted(identity: str) -> bool:
        effects = [
            r["effect"]
            for r in data["rules"]
            if identity in r["edge_ids"]
            and selects(r["source"], origin)
            and selects(r["destination"], service["asset_id"])
            and r["protocol"] == service["protocol"]
            and any(p["start"] <= port <= p["end"] for p in r["destination_ports"])
        ]
        return "allow" in effects and "deny" not in effects

    transitions = [
        ((e["source_interface_id"], "out"), (e["destination_interface_id"], "in"), e["id"])
        for e in data["transport_edges"]
    ]
    transitions += [
        ((e["ingress_interface_id"], "in"), (e["egress_interface_id"], "out"), e["id"])
        for e in data["forwarding_edges"]
    ]
    goal = (service["interface_id"], "in")

    def visit(state: tuple[str, str], active: frozenset[tuple[str, str]]) -> bool:
        if state == goal:
            return True
        return any(
            visit(target, active | {target})
            for start, target, identity in transitions
            if start == state and target not in active and permitted(identity)
        )

    return any(
        visit((i["id"], "out"), frozenset({(i["id"], "out")}))
        for i in data["interfaces"]
        if i["asset_id"] == origin
    )


@pytest.mark.parametrize("seed", range(36))
def test_exact_intervals_agree_with_per_port_oracle(minimal: dict[str, Any], seed: int) -> None:
    data = synthetic(minimal, seed)
    validated = validate_bytes(yaml.safe_dump(data).encode())
    engine = ReachabilityEngine(validated)
    for source in ("eng", "gwa"):
        for listener in ("svc_plc", "svc_udp"):
            result = engine.evaluate(source, listener)
            observed = {
                p: item.reachable
                for item in result.intervals
                for p in range(item.start, item.end + 1)
            }
            assert set(observed) == set(range(1, 9))
            assert observed == {p: oracle(data, source, listener, p) for p in range(1, 9)}
            for item in result.intervals:
                if item.witness is not None:
                    assert engine.replay(item.witness)
                    replay_raw(data, item.witness)
                    assert oracle(data, source, listener, item.start)


@pytest.mark.parametrize("seed", range(12))
def test_permission_monotonicity_and_ordering(minimal: dict[str, Any], seed: int) -> None:
    data = synthetic(minimal, seed)

    def reachable(candidate: dict[str, Any]) -> set[int]:
        result = evaluate_query(
            validate_bytes(yaml.safe_dump(candidate).encode()), "eng", "svc_plc"
        )
        return {p for i in result.intervals if i.reachable for p in range(i.start, i.end + 1)}

    original = reachable(data)
    added = deepcopy(data)
    edges = [e["id"] for e in added["transport_edges"] + added["forwarding_edges"]]
    if not edges:
        return
    added["rules"].append(
        {
            "id": "extra",
            "edge_ids": edges,
            "source": {"all_assets": True},
            "destination": {"all_assets": True},
            "protocol": "tcp",
            "effect": "allow",
            "destination_ports": [{"start": 1, "end": 8}],
        }
    )
    assert original <= reachable(added)
    added["rules"][-1]["effect"] = "deny"
    assert reachable(added) <= original
    reordered = deepcopy(data)
    for name in (
        "assets",
        "interfaces",
        "transport_edges",
        "forwarding_edges",
        "rules",
        "services",
    ):
        reordered[name].reverse()
    first = evaluate_query(validate_bytes(yaml.safe_dump(data).encode()), "eng", "svc_plc")
    second = evaluate_query(validate_bytes(yaml.safe_dump(reordered).encode()), "eng", "svc_plc")
    assert first == second


def test_check_bytes_order_invariance(boundary: dict[str, Any]) -> None:
    original = asdict(check_bytes(yaml.safe_dump(boundary).encode()))
    for name in ("assets", "interfaces", "transport_edges", "forwarding_edges", "rules", "intents"):
        boundary[name].reverse()
    assert asdict(check_bytes(yaml.safe_dump(boundary).encode())) == original
