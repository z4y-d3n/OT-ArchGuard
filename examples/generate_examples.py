"""Reproduce synthetic teaching YAML from the approved public fixtures, offline."""

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]


def save(family: str, name: str, model: dict[str, Any]) -> None:
    directory = ROOT / "examples" / family
    directory.mkdir(exist_ok=True)
    (directory / f"{name}.yaml").write_text(
        yaml.safe_dump(model, sort_keys=False, allow_unicode=True), encoding="utf-8", newline="\n"
    )


def direct_boundary(model: dict[str, Any]) -> None:
    """A separate, explicit pairwise path; consecutive forwarding cannot compose."""
    model["conduits"].append(
        {
            "id": "c_it_ot",
            "zone_ids": ["enterprise", "control"],
            "name": "Synthetic direct enterprise cell channel",
            "purpose": "Demonstrate an explicitly declared bypass candidate.",
            "common_security_needs": "No permission inferred from the conduit.",
        }
    )
    model["forwarding_edges"].append(
        {
            "id": "f_it_ot",
            "ingress_interface_id": "fw_it",
            "egress_interface_id": "fw_ot",
            "conduit_id": "c_it_ot",
        }
    )
    model["suc"]["access_points"].append(
        {
            "id": "ap_it_ot",
            "kind": "modeled_network",
            "description": "Explicit direct IT-to-control transition, separate from DMZ crossing.",
            "external_interface_id": "fw_it",
            "internal_interface_id": "fw_ot",
            "edge_ids": ["f_it_ot"],
        }
    )
    model["suc"]["boundary_description"] += (
        " A separate explicitly declared direct IT/control crossing is also present at f_it_ot."
    )


def permit_it_plc(model: dict[str, Any]) -> None:
    model["rules"] = [r for r in model["rules"] if r["id"] != "deny_it_plc"]
    model["rules"].append(
        {
            "id": "broad_boundary_permit",
            "effect": "allow",
            "source": {"asset_ids": ["it"]},
            "destination": {"asset_ids": ["plc"]},
            "protocol": "tcp",
            "destination_ports": [{"start": 1, "end": 65535}],
            "edge_ids": ["t_it_fw", "f_it_ot", "t_fw_plc"],
        }
    )


def generate() -> None:
    boundary = yaml.safe_load((ROOT / "tests/fixtures/boundary-device.yaml").read_text("utf-8"))
    # The remote baseline preserves every approved identity, placement and edge.
    save("remote-support", "baseline", boundary)
    proposed = deepcopy(boundary)
    proposed["revision"] = "explicit_direct_support_to_plc"
    direct_boundary(proposed)
    permit_it_plc(proposed)
    save("remote-support", "proposed", proposed)
    relay = deepcopy(boundary)
    relay["revision"] = "application_services_do_not_relay"
    relay["forwarding_edges"] = [e for e in relay["forwarding_edges"] if e["id"] != "f_dmz_ot"]
    for rule in relay["rules"]:
        rule["edge_ids"] = [e for e in rule["edge_ids"] if e != "f_dmz_ot"]
    save("remote-support", "application-only", relay)

    flat = yaml.safe_load((ROOT / "tests/fixtures/minimal-valid.yaml").read_text("utf-8"))
    flat["architecture_id"] = "flat_plant"
    flat["suc"]["name"] = "Synthetic flat permissive plant"
    flat["suc"]["controlled_process"] = "Imaginary HMI, engineer and critical controller."
    flat["assets"].append(
        {
            **flat["assets"][0],
            "id": "hmi",
            "name": "Operator HMI",
            "role": "HMI",
            "criticality": "high",
        }
    )
    flat["interfaces"].append(
        {
            "id": "hmi_net",
            "asset_id": "hmi",
            "placement_zone_id": "control",
            "ipv4": "192.0.2.30/24",
        }
    )
    flat["transport_edges"] += [
        {
            "id": "t_hmi_plc",
            "source_interface_id": "hmi_net",
            "destination_interface_id": "plc_net",
        },
        {
            "id": "t_eng_hmi",
            "source_interface_id": "eng_net",
            "destination_interface_id": "hmi_net",
        },
    ]
    flat["services"].append(
        {
            "id": "svc_hmi",
            "asset_id": "hmi",
            "interface_id": "hmi_net",
            "protocol": "tcp",
            "destination_ports": [{"start": 443, "end": 443}],
        }
    )
    flat["rules"] = [
        {
            "id": "flat_allow",
            "effect": "allow",
            "source": {"all_assets": True},
            "destination": {"all_assets": True},
            "protocol": "tcp",
            "destination_ports": [{"start": 1, "end": 65535}],
            "edge_ids": [e["id"] for e in flat["transport_edges"]],
        }
    ]
    flat["intents"].append(
        {
            "id": "req_hmi_plc",
            "kind": "required",
            "source": {"asset_ids": ["hmi"]},
            "destination_service_ids": ["svc_plc"],
        }
    )
    flat["scenarios"] = [
        {
            "id": "plant_scope",
            "origin_asset_ids": ["eng", "hmi"],
            "destination_service_ids": ["svc_plc", "svc_hmi"],
        }
    ]
    save("flat-plant", "baseline", flat)
    restricted = deepcopy(flat)
    restricted["revision"] = "narrowed_with_operational_regression"
    restricted["rules"] = [
        {
            "id": "only_eng_plc",
            "effect": "allow",
            "source": {"asset_ids": ["eng"]},
            "destination": {"asset_ids": ["plc"]},
            "protocol": "tcp",
            "destination_ports": [{"start": 502, "end": 502}],
            "edge_ids": ["t_eng_plc"],
        }
    ]
    save("flat-plant", "proposed", restricted)

    plant = deepcopy(boundary)
    plant["architecture_id"] = "segmented_plant"
    plant["suc"]["name"] = "Synthetic segmented manufacturing plant"
    plant["suc"]["controlled_process"] = (
        "Imaginary supervisory station, historian and cell controller."
    )
    plant["suc"]["boundary_description"] = (
        "External enterprise workstation it; internal DMZ firewall and historian, supervisory "
        "SCADA, and cell engineer/PLC. Firewall interfaces attach to all four placements. "
        "Declared IT-to-DMZ perimeter forwarding is f_it_dmz."
    )

    # Rename the teaching jump asset to a historian throughout declarations.
    def rename(value: Any) -> Any:
        if isinstance(value, str):
            return value.replace("jump", "hist").replace("Jump", "Historian")
        if isinstance(value, list):
            return [rename(v) for v in value]
        if isinstance(value, dict):
            return {k: rename(v) for k, v in value.items()}
        return value

    plant = rename(plant)
    plant["zones"].append(
        {
            **plant["zones"][2],
            "id": "supervisory",
            "name": "Supervisory",
            "purpose": "Declared supervisory station.",
            "grouping_rationale": "Separate synthetic supervisory administration.",
        }
    )
    for asset in plant["assets"]:
        if asset["id"] == "scada":
            asset["zone_id"] = "supervisory"
    for interface in plant["interfaces"]:
        if interface["id"] == "scada_net":
            interface.update(placement_zone_id="supervisory", ipv4="198.51.100.130/25")
    plant["interfaces"].append(
        {
            "id": "fw_sup",
            "asset_id": "fw",
            "placement_zone_id": "supervisory",
            "ipv4": "198.51.100.129/25",
        }
    )
    plant["conduits"] += [
        {
            "id": "c_dmz_sup",
            "zone_ids": ["dmz", "supervisory"],
            "name": "DMZ supervisory",
            "purpose": "Explicit historian to supervisory maintenance.",
            "common_security_needs": "Narrow declarations only.",
        },
        {
            "id": "c_sup_cell",
            "zone_ids": ["supervisory", "control"],
            "name": "Supervisory cell",
            "purpose": "Selected controller initiation.",
            "common_security_needs": "Explicit TCP listener only.",
        },
    ]
    plant["forwarding_edges"].append(
        {
            "id": "f_dmz_sup",
            "ingress_interface_id": "fw_dmz",
            "egress_interface_id": "fw_sup",
            "conduit_id": "c_dmz_sup",
        }
    )
    for edge in plant["transport_edges"]:
        if edge["id"] == "t_fw_scada":
            edge["source_interface_id"] = "fw_sup"
        if edge["id"] == "t_scada_plc":
            edge["conduit_id"] = "c_sup_cell"
    for rule in plant["rules"]:
        if rule["id"] == "allow_hist_scada":
            rule["edge_ids"] = ["t_hist_fw", "f_dmz_sup", "t_fw_scada"]
    plant["assets"].append(
        {**flat["assets"][0], "id": "eng", "name": "Cell engineering workstation"}
    )
    plant["interfaces"].append(
        {
            "id": "eng_net",
            "asset_id": "eng",
            "placement_zone_id": "control",
            "ipv4": "203.0.113.30/24",
        }
    )
    plant["transport_edges"].append(
        {"id": "t_eng_plc", "source_interface_id": "eng_net", "destination_interface_id": "plc_net"}
    )
    plant["rules"].append(
        {
            "id": "allow_eng_plc",
            "effect": "allow",
            "source": {"asset_ids": ["eng"]},
            "destination": {"asset_ids": ["plc"]},
            "protocol": "tcp",
            "destination_ports": [{"start": 502, "end": 502}],
            "edge_ids": ["t_eng_plc"],
        }
    )
    plant["intents"].append(
        {
            "id": "req_eng_plc",
            "kind": "required",
            "source": {"asset_ids": ["eng"]},
            "destination_service_ids": ["svc_plc"],
        }
    )
    plant["scenarios"] = [
        {
            "id": "plant_scope",
            "origin_asset_ids": ["it", "hist", "eng", "scada"],
            "destination_service_ids": ["svc_hist", "svc_scada", "svc_plc", "svc_fw"],
        }
    ]
    direct_boundary(plant)
    save("segmented-plant", "baseline", plant)
    broad = deepcopy(plant)
    broad["revision"] = "overly_broad_enterprise_controller_permit"
    permit_it_plc(broad)
    save("segmented-plant", "proposed", broad)


if __name__ == "__main__":
    generate()
