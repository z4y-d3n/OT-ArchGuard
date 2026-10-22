"""Independent concrete-port comparison and interval-set oracles."""

import random
from copy import deepcopy
from typing import Any

import pytest
import yaml

from otarchguard.comparison import compare_bytes
from otarchguard.flows import FlowInterval, difference, intersection, merge

type Concrete = tuple[str, str, str, str, int]


def concrete(flows: tuple[FlowInterval, ...]) -> set[Concrete]:
    return {
        (f.source_asset_id, f.destination_asset_id, f.service_id, f.protocol, port)
        for f in flows
        for port in range(f.start, f.end + 1)
    }


@pytest.mark.parametrize("seed", range(30))
def test_interval_operations_against_independent_port_sets(seed: int) -> None:
    generator = random.Random(seed)
    groups = []
    for _ in range(2):
        items = []
        for _ in range(12):
            low = generator.randint(1, 16)
            high = generator.randint(low, 16)
            items.append(
                FlowInterval(generator.choice(["eng", "client"]), "plc", "svc", "tcp", low, high)
            )
        groups.append(tuple(items))
    left, right = groups
    assert concrete(difference(left, right)) == concrete(left) - concrete(right)
    assert concrete(intersection(left, right)) == concrete(left) & concrete(right)
    assert concrete(merge(left)) == concrete(left)
    assert merge(merge(left)) == merge(left)


def small_network(minimal: dict[str, Any], seed: int) -> dict[str, Any]:
    data = deepcopy(minimal)
    data["intents"] = []
    data["scenarios"] = []
    data["assets"].extend(
        [{**data["assets"][0], "id": "client"}, {**data["assets"][1], "id": "hist"}]
    )
    data["interfaces"].extend(
        [
            {
                "id": "client_net",
                "asset_id": "client",
                "placement_zone_id": "control",
                "ipv4": "192.0.2.30/24",
            },
            {
                "id": "hist_net",
                "asset_id": "hist",
                "placement_zone_id": "control",
                "ipv4": "192.0.2.40/24",
            },
        ]
    )
    data["services"] = [
        {
            "id": f"svc_{destination}_{protocol}",
            "asset_id": destination,
            "interface_id": f"{destination}_net",
            "protocol": protocol,
            "destination_ports": [{"start": 1, "end": 8}],
        }
        for destination in ("plc", "hist")
        for protocol in ("tcp", "udp")
    ]
    data["transport_edges"] = [
        {
            "id": f"t_{source}_{destination}",
            "source_interface_id": f"{source}_net",
            "destination_interface_id": f"{destination}_net",
        }
        for source in ("eng", "client")
        for destination in ("plc", "hist")
    ]
    generator = random.Random(seed)
    data["rules"] = []
    for index in range(18):
        low = generator.randint(1, 8)
        data["rules"].append(
            {
                "id": f"r_{index}",
                "edge_ids": [generator.choice(data["transport_edges"])["id"]],
                "source": {"all_assets": True},
                "destination": {"all_assets": True},
                "protocol": generator.choice(["tcp", "udp"]),
                "effect": generator.choice(["allow", "allow", "deny"]),
                "destination_ports": [{"start": low, "end": generator.randint(low, 8)}],
            }
        )
    data["scenarios"] = [
        {
            "id": "scope",
            "origin_asset_ids": ["eng", "client"],
            "destination_service_ids": [s["id"] for s in data["services"]],
        }
    ]
    return data


def direct_oracle(data: dict[str, Any]) -> set[Concrete]:
    """For this endpoint-only fixture a permitted path must be one declared edge.

    Reads raw rules and ports, with no production interval/graph/query helpers.
    """
    result: set[Concrete] = set()
    for source in data["scenarios"][0]["origin_asset_ids"]:
        for service in data["services"]:
            for port in range(1, 9):
                for edge in data["transport_edges"]:
                    if (
                        edge["source_interface_id"] != f"{source}_net"
                        or edge["destination_interface_id"] != service["interface_id"]
                    ):
                        continue
                    matching = [
                        rule["effect"]
                        for rule in data["rules"]
                        if edge["id"] in rule["edge_ids"]
                        and rule["protocol"] == service["protocol"]
                        and any(i["start"] <= port <= i["end"] for i in rule["destination_ports"])
                    ]
                    if "allow" in matching and "deny" not in matching:
                        result.add(
                            (source, service["asset_id"], service["id"], service["protocol"], port)
                        )
    return result


@pytest.mark.parametrize("seed", range(16))
def test_comparison_matches_independent_small_model_oracle(
    minimal: dict[str, Any], seed: int
) -> None:
    before, after = small_network(minimal, seed), small_network(minimal, seed + 100)
    old, new = direct_oracle(before), direct_oracle(after)
    forward = compare_bytes(
        yaml.safe_dump(before).encode(), yaml.safe_dump(after).encode(), "scope"
    )
    reverse = compare_bytes(
        yaml.safe_dump(after).encode(), yaml.safe_dump(before).encode(), "scope"
    )
    same = compare_bytes(yaml.safe_dump(before).encode(), yaml.safe_dump(before).encode(), "scope")
    assert concrete(forward.baseline.observations) == old
    assert concrete(forward.proposed.observations) == new
    assert concrete(forward.newly_reachable) == new - old
    assert concrete(forward.no_longer_reachable) == old - new
    assert forward.newly_reachable == reverse.no_longer_reachable
    assert forward.no_longer_reachable == reverse.newly_reachable
    assert not same.newly_reachable and not same.no_longer_reachable
    assert not same.entity_changes and not same.inventory_changes
    assert {a.asset_id for a in forward.newly_reachable_assets} == {t[1] for t in new} - {
        t[1] for t in old
    }
    assert (
        forward.passed and reverse.passed and same.passed
    )  # No intents in this synthetic catalog.
