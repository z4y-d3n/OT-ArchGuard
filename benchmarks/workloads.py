"""Fixed, reproducible synthetic workloads for the approved NFR-05 envelope."""

from pathlib import Path
from typing import Any

import yaml


def routine(profile: str = "routine") -> dict[str, Any]:
    if profile not in {"routine", "sparse", "deny-heavy", "dense-policy", "interval-heavy"}:
        raise ValueError("Unknown benchmark profile")
    root = Path(__file__).resolve().parents[1]
    model: dict[str, Any] = yaml.safe_load(
        (root / "tests/fixtures/minimal-valid.yaml").read_bytes()
    )
    model.update(architecture_id="nfr05", revision=profile)
    model["suc"].update(
        id="synthetic_benchmark",
        name="Synthetic benchmark inventory",
        controlled_process="No physical process; finite deterministic performance workload.",
        boundary_description="One internal declared zone; no perimeter crossings.",
        completeness_assertion="Synthetic workload only; no deployed inventory or risk claims.",
    )
    template = model["assets"][0]
    model["assets"] = [
        {
            **template,
            "id": f"a{i:03}",
            "name": f"Synthetic asset {i}",
            "kind": "boundary_device" if 10 <= i < 30 else "endpoint",
        }
        for i in range(200)
    ]
    model["interfaces"] = [
        {
            "id": f"a{i:03}_{side}",
            "asset_id": f"a{i:03}",
            "placement_zone_id": "control",
            "ipv4": f"{prefix}.{i + 1}/24",
        }
        for i in range(200)
        for side, prefix in (("a", "192.0.2"), ("b", "198.51.100"))
    ]
    model["forwarding_edges"] = [
        {
            "id": f"f{i:03}_{side}",
            "ingress_interface_id": f"a{i:03}_{side}",
            "egress_interface_id": f"a{i:03}_{other}",
        }
        for i in range(10, 30)
        for side, other in (("a", "b"), ("b", "a"))
    ]
    pairs: dict[tuple[int, int], None] = {}
    for source in range(10):
        pairs[source, 10] = None
    for gateway in range(10, 30):
        pairs[gateway, 10 + (gateway - 9) % 20] = None
        for destination in range(175, 200):
            pairs[gateway, destination] = None
    # Add distinct directed edges deterministically, without inventing transit
    # through the ordinary endpoints used to fill the declared inventory.
    for offset in range(1, 200):
        for source in range(200):
            if len(pairs) < 1160:
                pairs[source, (source + offset) % 200] = None
    if profile == "sparse":
        pairs = dict.fromkeys(tuple(pairs)[:200])
    model["transport_edges"] = [
        {
            "id": f"t{index:04}",
            "source_interface_id": f"a{source:03}_b",
            "destination_interface_id": f"a{destination:03}_a",
        }
        for index, (source, destination) in enumerate(pairs)
    ]
    edges = [e["id"] for e in model["forwarding_edges"] + model["transport_edges"]]
    model["rules"] = [
        {
            "id": f"r{i:03}",
            "edge_ids": edges[:600] if profile == "dense-policy" else edges[i::200],
            "source": {"all_assets": True},
            "destination": {"all_assets": True},
            "protocol": "tcp",
            "destination_ports": [{"start": 1, "end": 65535}],
            "effect": "deny"
            if (i % 4 != 0 if profile == "deny-heavy" else i % 10 == 9)
            else "allow",
        }
        for i in range(200)
    ]
    model["services"] = [
        {
            "id": f"svc{i:02}",
            "asset_id": f"a{175 + i:03}",
            "interface_id": f"a{175 + i:03}_a",
            "protocol": "tcp",
            "destination_ports": [{"start": 5000 + i, "end": 5000 + i}],
        }
        for i in range(25)
    ]
    origins = [f"a{i:03}" for i in range(10)]
    model["scenarios"] = [
        {
            "id": "scope",
            "origin_asset_ids": origins.copy(),
            "destination_service_ids": [s["id"] for s in model["services"]],
        }
    ]
    model["intents"] = [
        {
            "id": "operational",
            "kind": "required",
            "source": {"asset_ids": origins},
            "destination_service_ids": [s["id"] for s in model["services"][:5]],
        }
    ]
    if profile == "dense-policy":
        model["intents"][0]["destination_service_ids"] = [s["id"] for s in model["services"]]
    if profile == "interval-heavy":
        model["services"][0]["destination_ports"] = [{"start": 1, "end": 65535}]
        for index, rule in enumerate(model["rules"]):
            rule["destination_ports"] = [{"start": 2 * index + 2, "end": 2 * index + 2}]
    return model


def source_bytes(profile: str = "routine") -> bytes:
    return yaml.safe_dump(routine(profile), sort_keys=False).encode("utf-8")
