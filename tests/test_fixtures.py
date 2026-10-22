"""Inspect trusted static declarations, without implementing a model validator.

safe_load is used only on repository-owned fixtures. This is not the future
bounded strict production loader and is never exposed through the application.
"""

from copy import deepcopy
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name: str) -> dict[str, Any]:
    return cast(dict[str, Any], yaml.safe_load((FIXTURES / name).read_text(encoding="utf-8")))


@pytest.mark.parametrize("name", sorted(path.name for path in FIXTURES.glob("*.yaml")))
def test_fixture_document_envelope(name: str) -> None:
    data = fixture(name)
    assert type(data["schema_version"]) is int
    assert data["schema_version"] == 1
    assert set(data) == {
        "schema_version",
        "architecture_id",
        "revision",
        "suc",
        "zones",
        "assets",
        "interfaces",
        "conduits",
        "transport_edges",
        "forwarding_edges",
        "services",
        "rules",
        "intents",
        "scenarios",
    }
    assert set(data["suc"]) == {
        "id",
        "name",
        "purpose",
        "controlled_process",
        "boundary_description",
        "completeness_assertion",
        "access_points",
        "external_dependencies",
    }


def test_minimal_declarations() -> None:
    data = fixture("minimal-valid.yaml")
    assert [(a["id"], a["zone_id"], a["kind"]) for a in data["assets"]] == [
        ("eng", "control", "endpoint"),
        ("plc", "control", "endpoint"),
    ]
    assert data["transport_edges"] == [
        {
            "id": "t_eng_plc",
            "source_interface_id": "eng_net",
            "destination_interface_id": "plc_net",
        }
    ]
    assert data["forwarding_edges"] == data["conduits"] == []
    assert data["services"][0] == {
        "id": "svc_plc",
        "asset_id": "plc",
        "interface_id": "plc_net",
        "protocol": "tcp",
        "destination_ports": [{"start": 502, "end": 502}],
    }


@pytest.mark.parametrize(
    ("negative", "baseline", "collection", "index", "field", "replacement"),
    [
        (
            "invalid-missing-reference.yaml",
            "minimal-valid.yaml",
            "transport_edges",
            0,
            "destination_interface_id",
            "absent_net",
        ),
        (
            "invalid-interface-placement.yaml",
            "boundary-device.yaml",
            "interfaces",
            0,
            "placement_zone_id",
            "dmz",
        ),
        (
            "unsupported-model.yaml",
            "boundary-device.yaml",
            "conduits",
            1,
            "zone_ids",
            ["enterprise", "dmz", "control"],
        ),
    ],
)
def test_negative_fixture_is_exactly_one_documented_mutation(
    negative: str,
    baseline: str,
    collection: str,
    index: int,
    field: str,
    replacement: object,
) -> None:
    expected = deepcopy(fixture(baseline))
    expected[collection][index][field] = replacement
    assert fixture(negative) == expected


def test_boundary_inventory_and_placements_match_approved_example() -> None:
    data = fixture("boundary-device.yaml")
    assert data["suc"]["id"] == "demo_cell"
    assert {a["id"]: (a["zone_id"], a["kind"], a["scope"]) for a in data["assets"]} == {
        "it": ("enterprise", "endpoint", "external"),
        "fw": ("dmz", "boundary_device", "internal"),
        "jump": ("dmz", "endpoint", "internal"),
        "scada": ("control", "endpoint", "internal"),
        "plc": ("control", "endpoint", "internal"),
    }
    assert [
        (i["id"], i["asset_id"], i["placement_zone_id"], i["ipv4"]) for i in data["interfaces"]
    ] == [
        ("it_net", "it", "enterprise", "192.0.2.10/24"),
        ("fw_it", "fw", "enterprise", "192.0.2.1/24"),
        ("fw_dmz", "fw", "dmz", "198.51.100.1/24"),
        ("fw_ot", "fw", "control", "203.0.113.1/24"),
        ("jump_net", "jump", "dmz", "198.51.100.10/24"),
        ("scada_net", "scada", "control", "203.0.113.10/24"),
        ("plc_net", "plc", "control", "203.0.113.20/24"),
    ]


def test_boundary_conduits_and_owner_classifications() -> None:
    data = fixture("boundary-device.yaml")
    assert [(c["id"], c["zone_ids"]) for c in data["conduits"]] == [
        ("c_it_dmz", ["enterprise", "dmz"]),
        ("c_dmz_ot", ["dmz", "control"]),
    ]
    assert [
        (a["id"], a["domain_classification"], a["safety_classification"], a["criticality"])
        for a in data["assets"]
    ] == [
        ("it", "business", "non_safety", "medium"),
        ("fw", "iacs", "non_safety", "high"),
        ("jump", "iacs", "non_safety", "high"),
        ("scada", "iacs", "non_safety", "high"),
        ("plc", "iacs", "non_safety", "critical"),
    ]
    assert all(z["safety_designation"] == "non_safety" for z in data["zones"])


def test_boundary_explicit_edges_and_management_binding() -> None:
    data = fixture("boundary-device.yaml")
    assert data["forwarding_edges"] == [
        {
            "id": "f_it_dmz",
            "ingress_interface_id": "fw_it",
            "egress_interface_id": "fw_dmz",
            "conduit_id": "c_it_dmz",
        },
        {
            "id": "f_dmz_ot",
            "ingress_interface_id": "fw_dmz",
            "egress_interface_id": "fw_ot",
            "conduit_id": "c_dmz_ot",
        },
    ]
    assert [
        (e["id"], e["source_interface_id"], e["destination_interface_id"])
        for e in data["transport_edges"]
    ] == [
        ("t_it_fw", "it_net", "fw_it"),
        ("t_fw_jump", "fw_dmz", "jump_net"),
        ("t_jump_fw", "jump_net", "fw_dmz"),
        ("t_fw_scada", "fw_ot", "scada_net"),
        ("t_fw_plc", "fw_ot", "plc_net"),
        ("t_scada_plc", "scada_net", "plc_net"),
    ]
    assert all("conduit_id" not in e for e in data["transport_edges"])
    assert [
        (s["id"], s["asset_id"], s["interface_id"], s["protocol"], s["destination_ports"])
        for s in data["services"]
    ] == [
        ("svc_jump", "jump", "jump_net", "tcp", [{"start": 3389, "end": 3389}]),
        ("svc_scada", "scada", "scada_net", "tcp", [{"start": 3389, "end": 3389}]),
        ("svc_plc", "plc", "plc_net", "tcp", [{"start": 502, "end": 502}]),
        ("svc_fw", "fw", "fw_dmz", "tcp", [{"start": 443, "end": 443}]),
    ]


def test_boundary_rules_preserve_original_endpoints() -> None:
    data = fixture("boundary-device.yaml")
    assert [
        (
            r["id"],
            r["effect"],
            r["source"],
            r["destination"],
            r["protocol"],
            r["destination_ports"],
            r["edge_ids"],
        )
        for r in data["rules"]
    ] == [
        (
            "allow_it_jump",
            "allow",
            {"asset_ids": ["it"]},
            {"asset_ids": ["jump"]},
            "tcp",
            [{"start": 3389, "end": 3389}],
            ["t_it_fw", "f_it_dmz", "t_fw_jump"],
        ),
        (
            "allow_jump_scada",
            "allow",
            {"asset_ids": ["jump"]},
            {"asset_ids": ["scada"]},
            "tcp",
            [{"start": 3389, "end": 3389}],
            ["t_jump_fw", "f_dmz_ot", "t_fw_scada"],
        ),
        (
            "allow_scada_plc",
            "allow",
            {"asset_ids": ["scada"]},
            {"asset_ids": ["plc"]},
            "tcp",
            [{"start": 502, "end": 502}],
            ["t_scada_plc"],
        ),
        (
            "allow_jump_fw",
            "allow",
            {"asset_ids": ["jump"]},
            {"asset_ids": ["fw"]},
            "tcp",
            [{"start": 443, "end": 443}],
            ["t_jump_fw"],
        ),
        (
            "deny_it_plc",
            "deny",
            {"asset_ids": ["it"]},
            {"asset_ids": ["plc"]},
            "tcp",
            [{"start": 502, "end": 502}],
            ["t_it_fw", "f_it_dmz", "f_dmz_ot", "t_fw_plc"],
        ),
    ]


def test_boundary_suc_and_scope_declarations() -> None:
    data = fixture("boundary-device.yaml")
    access = data["suc"]["access_points"]
    assert access[0] == {
        "id": "ap_it_dmz",
        "kind": "modeled_network",
        "description": "Directed firewall IT-to-DMZ perimeter crossing.",
        "external_interface_id": "fw_it",
        "internal_interface_id": "fw_dmz",
        "edge_ids": ["f_it_dmz"],
    }
    assert set(access[1]) == {"id", "kind", "description"}
    assert (access[1]["id"], access[1]["kind"]) == ("ap_cabinet", "unmodeled")
    dependency = data["suc"]["external_dependencies"][0]
    assert (
        dependency["id"],
        dependency["external_asset_ids"],
        dependency["required_intent_ids"],
    ) == ("dep_support", ["it"], ["req_it_jump"])
    assert data["scenarios"] == [
        {
            "id": "support_scope",
            "origin_asset_ids": ["it", "jump", "scada"],
            "destination_service_ids": ["svc_jump", "svc_scada", "svc_plc", "svc_fw"],
        }
    ]
    assert [
        (i["id"], i["kind"], i["source"], i["destination_service_ids"]) for i in data["intents"]
    ] == [
        ("req_it_jump", "required", {"asset_ids": ["it"]}, ["svc_jump"]),
        ("req_jump_scada", "required", {"asset_ids": ["jump"]}, ["svc_scada"]),
        ("req_scada_plc", "required", {"asset_ids": ["scada"]}, ["svc_plc"]),
        ("req_jump_fw", "required", {"asset_ids": ["jump"]}, ["svc_fw"]),
        ("prohibit_it_ot", "prohibited", {"asset_ids": ["it"]}, ["svc_scada", "svc_plc"]),
        ("prohibit_it_fw", "prohibited", {"asset_ids": ["it"]}, ["svc_fw"]),
        ("prohibit_jump_plc", "prohibited", {"asset_ids": ["jump"]}, ["svc_plc"]),
        ("prohibit_scada_dmz", "prohibited", {"asset_ids": ["scada"]}, ["svc_jump", "svc_fw"]),
    ]
