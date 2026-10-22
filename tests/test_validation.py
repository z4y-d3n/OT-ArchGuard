"""T01–T03, structural T11/T22–T24, intent declarations and entity budgets."""

from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from otarchguard.api import validate_bytes, validate_file
from otarchguard.contract import RESOURCE_LIMITS, DiagnosticCategory
from otarchguard.diagnostics import ModelError
from otarchguard.domain import ZoneSelector
from otarchguard.validation import expand_selector

FIXTURES = Path(__file__).parent / "fixtures"


def encode(data: dict[str, Any]) -> bytes:
    return yaml.safe_dump(data, sort_keys=False).encode("utf-8")


def change(data: dict[str, Any], path: str, value: object) -> None:
    target: Any = data
    parts = path.split(".")
    for part in parts[:-1]:
        target = target[int(part)] if isinstance(target, list) else target[part]
    last = parts[-1]
    if isinstance(target, list):
        target[int(last)] = value
    else:
        target[last] = value


@pytest.mark.parametrize("name", ["minimal-valid.yaml", "boundary-device.yaml"])
def test_positive_fixtures(name: str) -> None:
    result = validate_file(FIXTURES / name)
    assert len(result.sha256) == 64
    assert result.model.schema_version == 1
    assert result.model.suc.completeness_assertion
    with pytest.raises(ValidationError):
        result.model.revision = "mutation"


@pytest.mark.parametrize(
    ("name", "category", "code", "location"),
    [
        (
            "invalid-missing-reference.yaml",
            "invalid_input",
            "MISSING_REFERENCE",
            "$.transport_edges[0].destination_interface_id",
        ),
        (
            "invalid-interface-placement.yaml",
            "invalid_input",
            "INVALID_PLACEMENT",
            "$.interfaces[0].placement_zone_id",
        ),
        (
            "unsupported-model.yaml",
            "unsupported_model",
            "UNSUPPORTED_CONDUIT",
            "$.conduits[1].zone_ids",
        ),
    ],
)
def test_negative_fixtures_expected_reason(
    name: str, category: str, code: str, location: str
) -> None:
    with pytest.raises(ModelError) as caught:
        validate_file(FIXTURES / name)
    assert (
        caught.value.diagnostics[0].category,
        caught.value.diagnostics[0].code,
        caught.value.diagnostics[0].location,
    ) == (category, code, location)


@pytest.mark.parametrize(
    ("path", "value", "code"),
    [
        ("schema_version", True, "TYPE_MISMATCH"),
        ("schema_version", "1", "TYPE_MISMATCH"),
        ("assets.0.id", "Upper", "INVALID_ID"),
        ("assets.0.id", "a" * 65, "INVALID_ID"),
        ("assets.0.id", "eng\n", "INVALID_ID"),
        ("assets.1.id", "eng", "DUPLICATE_ID"),
        ("assets.0.zone_id", "absent", "MISSING_REFERENCE"),
        ("assets.0.scope", "external", "SCOPE_MISMATCH"),
        ("assets.0.criticality", "maximum", "INVALID_VALUE"),
        ("assets.0.domain_classification", "auto", "INVALID_VALUE"),
        ("assets.0.name", "  ", "INVALID_VALUE"),
        ("assets.0.extra", 1, "UNKNOWN_FIELD"),
        ("interfaces.0.asset_id", "absent", "MISSING_REFERENCE"),
        ("interfaces.0.placement_zone_id", "absent", "MISSING_REFERENCE"),
        ("interfaces.0.ipv4", "hostname", "INVALID_ADDRESS"),
        ("interfaces.0.ipv4", "192.0.2.10", "INVALID_ADDRESS"),
        ("interfaces.0.ipv4", "192.0.2.10/255.255.255.0", "INVALID_ADDRESS"),
        ("interfaces.0.ipv4", "192.0.2.999/24", "INVALID_ADDRESS"),
        ("interfaces.0.ipv4", "192.0.2.10/33", "INVALID_ADDRESS"),
        ("interfaces.1.ipv4", "192.0.2.10/25", "DUPLICATE_ADDRESS"),
        ("transport_edges.0.destination_interface_id", "absent", "MISSING_REFERENCE"),
        ("transport_edges.0.destination_interface_id", "eng_net", "INVALID_EDGE"),
        ("transport_edges.0.conduit_id", "absent", "MISSING_REFERENCE"),
        ("services.0.asset_id", "absent", "MISSING_REFERENCE"),
        ("services.0.interface_id", "absent", "MISSING_REFERENCE"),
        ("services.0.interface_id", "eng_net", "INVALID_SERVICE_BINDING"),
        ("services.0.destination_ports.0.start", True, "TYPE_MISMATCH"),
        ("services.0.destination_ports.0.start", "502", "TYPE_MISMATCH"),
        ("services.0.destination_ports.0.start", 0, "INVALID_PORT"),
        ("services.0.destination_ports.0.end", 65536, "INVALID_PORT"),
        ("services.0.destination_ports.0.end", 501, "INVALID_PORT"),
        ("services.0.destination_ports", [], "INVALID_VALUE"),
        (
            "services.0.destination_ports",
            [{"start": 502, "end": 502}, {"start": 502, "end": 502}],
            "DUPLICATE_ITEM",
        ),
        ("rules.0.edge_ids", ["absent"], "MISSING_REFERENCE"),
        ("rules.0.edge_ids", ["t_eng_plc", "t_eng_plc"], "DUPLICATE_ITEM"),
        ("rules.0.source", {"asset_ids": ["absent"]}, "MISSING_REFERENCE"),
        ("rules.0.source", {"zone_ids": ["absent"]}, "MISSING_REFERENCE"),
        ("rules.0.source", {"asset_ids": ["eng", "eng"]}, "DUPLICATE_ITEM"),
        ("rules.0.source", {"asset_ids": []}, "INVALID_SELECTOR"),
        ("rules.0.source", {"all_assets": 1}, "INVALID_SELECTOR"),
        ("rules.0.source", {"all_assets": False}, "INVALID_SELECTOR"),
        ("rules.0.source", {"all_assets": True, "asset_ids": ["eng"]}, "INVALID_SELECTOR"),
        ("rules.0.source", {}, "INVALID_SELECTOR"),
        ("rules.0.destination", {"asset_ids": ["absent"]}, "MISSING_REFERENCE"),
        ("rules.0.destination_ports.0.end", 500, "INVALID_PORT"),
        ("rules.0.effect", "drop", "INVALID_VALUE"),
        ("intents.0.destination_service_ids", ["absent"], "MISSING_REFERENCE"),
        ("intents.0.source", {"asset_ids": ["plc"]}, "EMPTY_QUERY_SCOPE"),
        ("scenarios.0.origin_asset_ids", ["plc"], "EMPTY_QUERY_SCOPE"),
        ("scenarios.0.destination_service_ids", ["absent"], "MISSING_REFERENCE"),
        ("suc.purpose", None, "TYPE_MISMATCH"),
        (
            "suc.access_points",
            [
                {
                    "id": "ap",
                    "kind": "unmodeled",
                    "description": "physical",
                    "edge_ids": ["t_eng_plc"],
                }
            ],
            "UNKNOWN_FIELD",
        ),
    ],
)
def test_invalid_supported_declarations(
    minimal: dict[str, Any], path: str, value: object, code: str
) -> None:
    change(minimal, path, value)
    with pytest.raises(ModelError) as caught:
        validate_bytes(encode(minimal))
    assert caught.value.diagnostics[0].code == code
    assert caught.value.diagnostics[0].category == DiagnosticCategory.INVALID_INPUT


@pytest.mark.parametrize(
    ("path", "value", "code"),
    [
        ("schema_version", 2, "UNSUPPORTED_VERSION"),
        ("services.0.protocol", "icmp", "UNSUPPORTED_PROTOCOL"),
        ("interfaces.0.ipv4", "2001:db8::1/64", "UNSUPPORTED_ADDRESS_FAMILY"),
        ("interfaces.0.ipv4", "224.0.0.1/24", "UNSUPPORTED_ADDRESS_KIND"),
        ("interfaces.0.ipv4", "0.0.0.0/32", "UNSUPPORTED_ADDRESS_KIND"),
        ("interfaces.0.ipv4", "127.0.0.1/8", "UNSUPPORTED_ADDRESS_KIND"),
        ("interfaces.0.ipv4", "255.255.255.255/32", "UNSUPPORTED_ADDRESS_KIND"),
        ("interfaces.0.ipv4", "192.0.2.255/24", "UNSUPPORTED_ADDRESS_KIND"),
        ("assets.0.zone_id", ["control"], "UNSUPPORTED_OWNERSHIP"),
        ("assets.0.owner_conduit_id", "some", "UNSUPPORTED_OWNERSHIP"),
        ("assets.0.owner_zone_ids", ["control"], "UNSUPPORTED_OWNERSHIP"),
        ("rules.0.source_ports", [123], "UNSUPPORTED_POLICY"),
        ("rules.0.source_interface_ids", ["eng_net"], "UNSUPPORTED_POLICY"),
        ("rules.0.stateful", True, "UNSUPPORTED_POLICY"),
        ("rules.0.rule_order", 1, "UNSUPPORTED_POLICY"),
        ("suc.sl_t", 2, "UNSUPPORTED_FEATURE"),
        ("suc.sl_c", 2, "UNSUPPORTED_FEATURE"),
        ("suc.sl_a", 2, "UNSUPPORTED_FEATURE"),
        ("assets.0.nat", True, "UNSUPPORTED_FEATURE"),
        ("assets.0.vrf", "private", "UNSUPPORTED_FEATURE"),
        ("assets.0.vlan", 10, "UNSUPPORTED_FEATURE"),
        ("assets.0.proxy", True, "UNSUPPORTED_FEATURE"),
    ],
)
def test_unsupported_features(minimal: dict[str, Any], path: str, value: object, code: str) -> None:
    change(minimal, path, value)
    with pytest.raises(ModelError) as caught:
        validate_bytes(encode(minimal))
    assert caught.value.diagnostics[0].category == DiagnosticCategory.UNSUPPORTED_MODEL
    assert caught.value.diagnostics[0].code == code


@pytest.mark.parametrize(
    "field",
    [
        "purpose",
        "controlled_process",
        "completeness_assertion",
        "boundary_description",
        "external_dependencies",
        "access_points",
    ],
)
def test_required_suc_fields(minimal: dict[str, Any], field: str) -> None:
    del minimal["suc"][field]
    with pytest.raises(ModelError) as caught:
        validate_bytes(encode(minimal))
    assert caught.value.diagnostics[0].code == "MISSING_FIELD"


@pytest.mark.parametrize(
    ("path", "value", "code"),
    [
        ("forwarding_edges.0.conduit_id", "c_dmz_ot", "INVALID_CONDUIT_PAIR"),
        ("transport_edges.0.conduit_id", "c_it_dmz", "INVALID_CONDUIT_PAIR"),
        ("forwarding_edges.0.egress_interface_id", "jump_net", "INVALID_EDGE"),
        ("forwarding_edges.0.egress_interface_id", "fw_it", "UNSUPPORTED_FORWARDING"),
        ("forwarding_edges.0.id", "t_it_fw", "DUPLICATE_ID"),
        ("suc.access_points", [], "INVALID_ACCESS_POINT"),
        ("suc.access_points.0.external_interface_id", "absent", "MISSING_REFERENCE"),
        ("suc.access_points.0.external_interface_id", "fw_dmz", "INVALID_ACCESS_POINT"),
        ("suc.access_points.0.internal_interface_id", "jump_net", "INVALID_ACCESS_POINT"),
        ("suc.access_points.0.edge_ids", ["absent"], "MISSING_REFERENCE"),
        ("suc.access_points.0.edge_ids", ["t_it_fw"], "INVALID_ACCESS_POINT"),
        ("suc.external_dependencies.0.external_asset_ids", ["jump"], "INVALID_DEPENDENCY"),
        ("suc.external_dependencies.0.external_asset_ids", ["absent"], "MISSING_REFERENCE"),
        (
            "suc.external_dependencies.0.required_intent_ids",
            ["prohibit_it_ot"],
            "INVALID_DEPENDENCY",
        ),
        ("suc.external_dependencies.0.required_intent_ids", ["absent"], "MISSING_REFERENCE"),
        ("conduits.0.zone_ids", ["enterprise"], "INVALID_CONDUIT_PAIR"),
        ("conduits.0.zone_ids", ["enterprise", "enterprise"], "DUPLICATE_ITEM"),
        ("conduits.0.zone_ids", ["enterprise", "absent"], "MISSING_REFERENCE"),
        ("conduits.0.protected_transit", True, "UNSUPPORTED_CONDUIT"),
        ("conduits.0.transit_zone_ids", ["control"], "UNSUPPORTED_CONDUIT"),
    ],
)
def test_boundary_negative_cases(
    boundary: dict[str, Any], path: str, value: object, code: str
) -> None:
    change(boundary, path, value)
    with pytest.raises(ModelError) as caught:
        validate_bytes(encode(boundary))
    assert caught.value.diagnostics[0].code == code


def test_missing_conduit_and_duplicate_crossing(boundary: dict[str, Any]) -> None:
    bad = deepcopy(boundary)
    del bad["forwarding_edges"][0]["conduit_id"]
    with pytest.raises(ModelError) as caught:
        validate_bytes(encode(bad))
    assert caught.value.diagnostics[0].code == "INVALID_CONDUIT_PAIR"
    duplicate = deepcopy(boundary["suc"]["access_points"][0])
    duplicate["id"] = "another_access_point"
    boundary["suc"]["access_points"].append(duplicate)
    with pytest.raises(ModelError) as caught:
        validate_bytes(encode(boundary))
    assert caught.value.diagnostics[0].code == "INVALID_ACCESS_POINT"


def test_endpoint_cannot_forward_even_in_same_zone(boundary: dict[str, Any]) -> None:
    boundary["interfaces"].append(
        {
            "id": "jump_second",
            "asset_id": "jump",
            "placement_zone_id": "dmz",
            "ipv4": "198.51.100.11/24",
        }
    )
    boundary["forwarding_edges"].append(
        {"id": "bad", "ingress_interface_id": "jump_net", "egress_interface_id": "jump_second"}
    )
    with pytest.raises(ModelError) as caught:
        validate_bytes(encode(boundary))
    assert caught.value.diagnostics[0].code == "INVALID_EDGE"


def test_ownership_selectors_and_service_binding(boundary: dict[str, Any]) -> None:
    model = validate_bytes(encode(boundary)).model
    assets, zones = {a.id: a for a in model.assets}, {z.id: z for z in model.zones}
    assert expand_selector(ZoneSelector(zone_ids=("enterprise",)), assets, zones) == ("it",)
    assert expand_selector(ZoneSelector(zone_ids=("dmz",)), assets, zones) == ("fw", "jump")
    assert next(s for s in model.services if s.id == "svc_fw").interface_id == "fw_dmz"


def test_contradictory_intents_across_service_ids(minimal: dict[str, Any]) -> None:
    other = deepcopy(minimal["services"][0])
    other["id"] = "other_listener"
    other["destination_ports"] = [{"start": 500, "end": 503}]
    minimal["services"].append(other)
    minimal["intents"].append(
        {
            "id": "prohibit",
            "kind": "prohibited",
            "source": {"zone_ids": ["control"]},
            "destination_service_ids": ["other_listener"],
        }
    )
    with pytest.raises(ModelError) as caught:
        validate_bytes(encode(minimal))
    assert caught.value.diagnostics[0].code == "CONTRADICTORY_INTENTS"


def test_allow_deny_overlap_is_valid(minimal: dict[str, Any]) -> None:
    deny = deepcopy(minimal["rules"][0])
    deny.update(id="deny", effect="deny")
    minimal["rules"].append(deny)
    assert validate_bytes(encode(minimal)).model.rules


def test_mixed_self_pairs_retained(minimal: dict[str, Any]) -> None:
    minimal["intents"][0]["source"] = {"all_assets": True}
    minimal["scenarios"][0]["origin_asset_ids"] = ["eng", "plc"]
    assert validate_bytes(encode(minimal)).model.intents


def test_missing_origin_interface_and_empty_zone_selector(minimal: dict[str, Any]) -> None:
    minimal["assets"].append({**minimal["assets"][0], "id": "no_interface"})
    minimal["scenarios"][0]["origin_asset_ids"] = ["no_interface"]
    with pytest.raises(ModelError) as caught:
        validate_bytes(encode(minimal))
    assert caught.value.diagnostics[0].code == "EMPTY_QUERY_SCOPE"
    minimal["scenarios"] = []
    minimal["zones"].append({**minimal["zones"][0], "id": "empty"})
    minimal["rules"][0]["source"] = {"zone_ids": ["empty"]}
    with pytest.raises(ModelError) as caught:
        validate_bytes(encode(minimal))
    assert caught.value.diagnostics[0].code == "INVALID_SELECTOR"


@pytest.mark.parametrize(
    ("designation", "safety", "rationale", "valid"),
    [
        ("non_safety", "safety_related", None, False),
        ("safety", "non_safety", None, False),
        ("mixed_safety", "safety_related", None, False),
        ("mixed_safety", "safety_related", "Declared non-separation", True),
        ("non_safety", "unassessed", None, False),
        ("unassessed", "unassessed", None, True),
        ("non_safety", "non_safety", "Extraneous rationale", False),
    ],
)
def test_safety_assertions(
    minimal: dict[str, Any], designation: str, safety: str, rationale: str | None, valid: bool
) -> None:
    minimal["zones"][0]["safety_designation"] = designation
    minimal["assets"][0]["safety_classification"] = safety
    if rationale is not None:
        minimal["zones"][0]["mixed_safety_rationale"] = rationale
    if valid:
        assert validate_bytes(encode(minimal)).model.zones
    else:
        with pytest.raises(ModelError) as caught:
            validate_bytes(encode(minimal))
        assert caught.value.diagnostics[0].code == "SAFETY_INCONSISTENCY"


def test_known_mixed_with_unknown_stays_mixed(minimal: dict[str, Any]) -> None:
    minimal["zones"][0].update(
        safety_designation="mixed_safety", mixed_safety_rationale="Owner assertion"
    )
    minimal["assets"][0]["safety_classification"] = "safety_related"
    minimal["assets"].append(
        {**minimal["assets"][1], "id": "unknown", "safety_classification": "unassessed"}
    )
    assert validate_bytes(encode(minimal)).model.zones[0].safety_designation == "mixed_safety"


@pytest.mark.parametrize(
    "limit",
    [
        "assets",
        "interfaces",
        "edges",
        "rules",
        "services",
        "zones",
        "conduits",
        "access_points",
        "dependencies",
        "edge_rule_associations",
    ],
)
def test_declaration_resource_limits(boundary: dict[str, Any], limit: str) -> None:
    with pytest.raises(ModelError) as caught:
        validate_bytes(encode(boundary), replace(RESOURCE_LIMITS, **{limit: 0}))
    assert caught.value.diagnostics[0].category == DiagnosticCategory.RESOURCE_LIMIT
    assert limit in caught.value.diagnostics[0].message


def test_business_mixing_and_prefix_overlap_do_not_create_normative_failure(
    minimal: dict[str, Any],
) -> None:
    minimal["assets"][0]["domain_classification"] = "business"
    minimal["interfaces"][0]["ipv4"] = "192.0.2.10/25"
    assert validate_bytes(encode(minimal)).model.assets


def test_cross_zone_transport_requires_pair_conduit(minimal: dict[str, Any]) -> None:
    minimal["zones"].append({**minimal["zones"][0], "id": "cell"})
    minimal["assets"][1]["zone_id"] = "cell"
    minimal["interfaces"][1]["placement_zone_id"] = "cell"
    with pytest.raises(ModelError) as caught:
        validate_bytes(encode(minimal))
    assert caught.value.diagnostics[0].code == "INVALID_CONDUIT_PAIR"
    minimal["conduits"] = [
        {
            "id": "c",
            "name": "Channel",
            "purpose": "Declared transfer",
            "common_security_needs": "Narrow traffic",
            "zone_ids": ["control", "cell"],
        }
    ]
    minimal["transport_edges"][0]["conduit_id"] = "c"
    assert validate_bytes(encode(minimal)).model.conduits


def test_reverse_crossing_uses_explicit_edge_and_same_access_record(
    boundary: dict[str, Any],
) -> None:
    boundary["forwarding_edges"].append(
        {
            "id": "f_reverse",
            "ingress_interface_id": "fw_dmz",
            "egress_interface_id": "fw_it",
            "conduit_id": "c_it_dmz",
        }
    )
    boundary["suc"]["access_points"][0]["edge_ids"].append("f_reverse")
    assert validate_bytes(encode(boundary)).model.suc.access_points


def test_no_forwarding_or_permits_is_still_structurally_valid(boundary: dict[str, Any]) -> None:
    boundary["forwarding_edges"] = [
        edge for edge in boundary["forwarding_edges"] if edge["id"] != "f_dmz_ot"
    ]
    boundary["rules"] = []
    result = validate_bytes(encode(boundary))
    assert len(result.model.forwarding_edges) == 1
    assert result.model.rules == ()


def test_boundary_owner_move_changes_ownership_selection(boundary: dict[str, Any]) -> None:
    boundary["assets"][1]["zone_id"] = "control"
    model = validate_bytes(encode(boundary)).model
    assets, zones = {a.id: a for a in model.assets}, {z.id: z for z in model.zones}
    assert expand_selector(ZoneSelector(zone_ids=("dmz",)), assets, zones) == ("jump",)
    assert expand_selector(ZoneSelector(zone_ids=("control",)), assets, zones) == (
        "fw",
        "plc",
        "scada",
    )


def test_boundary_attachment_does_not_reclassify_other_zones(boundary: dict[str, Any]) -> None:
    boundary["assets"][1]["safety_classification"] = "safety_related"
    boundary["zones"][1].update(
        safety_designation="mixed_safety", mixed_safety_rationale="Teaching assertion"
    )
    model = validate_bytes(encode(boundary)).model
    assert {z.id: z.safety_designation for z in model.zones} == {
        "enterprise": "non_safety",
        "dmz": "mixed_safety",
        "control": "non_safety",
    }


def test_access_point_requires_internal_asset(boundary: dict[str, Any]) -> None:
    boundary["assets"][1].update(zone_id="enterprise", scope="external")
    with pytest.raises(ModelError) as caught:
        validate_bytes(encode(boundary))
    assert caught.value.diagnostics[0].code == "INVALID_ACCESS_POINT"


@pytest.mark.parametrize("address", ["192.0.2.0/31", "192.0.2.1/31", "192.0.2.255/32"])
def test_unicast_host_prefixes(minimal: dict[str, Any], address: str) -> None:
    minimal["interfaces"][0]["ipv4"] = address
    assert validate_bytes(encode(minimal)).model.interfaces


def test_disjoint_intents_are_not_contradictory(minimal: dict[str, Any]) -> None:
    service = {
        **minimal["services"][0],
        "id": "other",
        "destination_ports": [{"start": 503, "end": 504}],
    }
    minimal["services"].append(service)
    minimal["intents"].append(
        {
            "id": "prohibit",
            "kind": "prohibited",
            "source": {"all_assets": True},
            "destination_service_ids": ["other"],
        }
    )
    assert validate_bytes(encode(minimal)).model.intents


def test_large_selector_catalog_has_no_cartesian_query_materialization(
    minimal: dict[str, Any],
) -> None:
    for index in range(100):
        identity = f"eng_{index}"
        minimal["assets"].append({**minimal["assets"][0], "id": identity})
        minimal["interfaces"].append(
            {
                "id": f"net_{index}",
                "asset_id": identity,
                "placement_zone_id": "control",
                "ipv4": f"198.51.100.{index + 1}/24",
            }
        )
    minimal["intents"][0]["source"] = {"all_assets": True}
    assert len(validate_bytes(encode(minimal)).model.assets) == 102


def test_combined_edge_and_association_boundaries(boundary: dict[str, Any]) -> None:
    edge_count = len(boundary["transport_edges"]) + len(boundary["forwarding_edges"])
    associations = sum(len(rule["edge_ids"]) for rule in boundary["rules"])
    assert validate_bytes(
        encode(boundary),
        replace(RESOURCE_LIMITS, edges=edge_count, edge_rule_associations=associations),
    ).model
    for limits in (
        replace(RESOURCE_LIMITS, edges=edge_count - 1),
        replace(RESOURCE_LIMITS, edge_rule_associations=associations - 1),
    ):
        with pytest.raises(ModelError) as caught:
            validate_bytes(encode(boundary), limits)
        assert caught.value.diagnostics[0].code == "LIMIT_EXCEEDED"


@pytest.mark.parametrize(
    "field",
    [
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
    ],
)
def test_every_root_field_is_required(minimal: dict[str, Any], field: str) -> None:
    del minimal[field]
    with pytest.raises(ModelError) as caught:
        validate_bytes(encode(minimal))
    assert caught.value.diagnostics[0].code == "MISSING_FIELD"
    assert caught.value.diagnostics[0].location == f"$.{field}"


@pytest.mark.parametrize(
    ("collection", "field"),
    [
        ("assets", "scope"),
        ("assets", "domain_classification"),
        ("assets", "safety_classification"),
        ("zones", "scope"),
        ("zones", "grouping_rationale"),
        ("zones", "safety_designation"),
        ("interfaces", "placement_zone_id"),
    ],
)
def test_classification_and_placement_are_explicit(
    minimal: dict[str, Any], collection: str, field: str
) -> None:
    del minimal[collection][0][field]
    with pytest.raises(ModelError) as caught:
        validate_bytes(encode(minimal))
    assert caught.value.diagnostics[0].code == "MISSING_FIELD"


@pytest.mark.parametrize(
    "field", ["kind", "description", "external_interface_id", "internal_interface_id", "edge_ids"]
)
def test_modeled_access_point_fields_required(boundary: dict[str, Any], field: str) -> None:
    del boundary["suc"]["access_points"][0][field]
    with pytest.raises(ModelError) as caught:
        validate_bytes(encode(boundary))
    assert caught.value.diagnostics[0].code == "MISSING_FIELD"
    assert caught.value.diagnostics[0].location == f"$.suc.access_points[0].{field}"


def test_input_primitives_cannot_mutate_validated_model(minimal: dict[str, Any]) -> None:
    from otarchguard.parsing import parse_model

    model = parse_model(minimal)
    minimal["assets"][0]["name"] = "mutated"
    assert model.assets[0].name == "Engineering workstation"


def test_interface_restricted_same_origin_policy_is_not_silently_accepted(
    boundary: dict[str, Any],
) -> None:
    boundary["rules"][0]["source"] = {"interface_ids": ["it_net"]}
    with pytest.raises(ModelError) as caught:
        validate_bytes(encode(boundary))
    assert caught.value.diagnostics[0].code == "INVALID_SELECTOR"
