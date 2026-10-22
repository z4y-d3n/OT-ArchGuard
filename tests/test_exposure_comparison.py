"""T14–T17 and comparison T22: exact scope, definitions, inventory and operational regressions."""

from copy import deepcopy
from dataclasses import asdict, replace
from typing import Any

import pytest
import yaml

from otarchguard.comparison import compare_bytes
from otarchguard.contract import RESOURCE_LIMITS
from otarchguard.diagnostics import ModelError
from otarchguard.exposure import QueryScope, exposure_bytes
from otarchguard.reachability import ReachabilityEngine


def encoded(data: dict[str, Any]) -> bytes:
    return yaml.safe_dump(data, sort_keys=False).encode()


def test_boundary_scenario_is_finite_and_deduplicated(boundary: dict[str, Any]) -> None:
    result = exposure_bytes(encoded(boundary), "support_scope")
    assert result.passed and len(result.queries) == 10
    assert [
        (f.source_asset_id, f.destination_asset_id, f.service_id, f.protocol, f.start, f.end)
        for f in result.observations
    ] == [
        ("it", "jump", "svc_jump", "tcp", 3389, 3389),
        ("jump", "fw", "svc_fw", "tcp", 443, 443),
        ("jump", "scada", "svc_scada", "tcp", 3389, 3389),
        ("scada", "plc", "svc_plc", "tcp", 502, 502),
    ]
    assert [(a.asset_id, a.criticality) for a in result.destination_assets] == [
        ("fw", "high"),
        ("jump", "high"),
        ("plc", "critical"),
        ("scada", "high"),
    ]
    assert result.atom_queries == 20 and result.intent_checks.atom_queries == 10
    assert result.completeness_assertion
    assert all(q.source_asset_id != q.destination_asset_id for q in result.queries)


def test_t14_new_reachable_critical_destination(minimal: dict[str, Any]) -> None:
    before = deepcopy(minimal)
    before["rules"] = []
    result = compare_bytes(encoded(before), encoded(minimal), "engineering_scope")
    assert [
        (f.source_asset_id, f.destination_asset_id, f.service_id, f.start, f.end)
        for f in result.newly_reachable
    ] == [("eng", "plc", "svc_plc", 502, 502)]
    assert result.newly_reachable_assets[0].asset_id == "plc"
    assert result.newly_reachable_assets[0].proposed_criticality == "critical"
    assert result.no_longer_reachable == ()


def test_t15_reduced_exposure_does_not_hide_broken_requirement(boundary: dict[str, Any]) -> None:
    after = deepcopy(boundary)
    after["rules"][1]["edge_ids"].remove("f_dmz_ot")
    result = compare_bytes(encoded(boundary), encoded(after), "support_scope")
    assert not result.passed
    assert len(result.no_longer_reachable) == 1 and not result.newly_reachable
    assert result.no_longer_reachable_assets[0].asset_id == "scada"
    assert result.broken_required_communications[0].intent_id == "req_jump_scada"
    assert result.baseline.passed and not result.proposed.passed


def test_broken_required_and_introduced_prohibited_are_both_reported(
    boundary: dict[str, Any],
) -> None:
    after = deepcopy(boundary)
    after["rules"][1]["edge_ids"].remove("f_dmz_ot")
    after["rules"].append(
        {
            "id": "allow_jump_plc",
            "source": {"asset_ids": ["jump"]},
            "destination": {"asset_ids": ["plc"]},
            "protocol": "tcp",
            "effect": "allow",
            "destination_ports": [{"start": 502, "end": 502}],
            "edge_ids": ["t_jump_fw", "f_dmz_ot", "t_fw_plc"],
        }
    )
    result = compare_bytes(encoded(boundary), encoded(after), "support_scope")
    assert not result.passed
    assert result.broken_required_communications[0].intent_id == "req_jump_scada"
    assert result.introduced_prohibited_violations[0].intent_id == "prohibit_jump_plc"
    assert len(result.newly_reachable) == len(result.no_longer_reachable) == 1
    assert not result.newly_reachable_assets  # PLC was already reached from SCADA.


def test_new_and_resolved_prohibited_violations(minimal: dict[str, Any]) -> None:
    minimal["intents"][0]["kind"] = "prohibited"
    before = deepcopy(minimal)
    before["rules"] = []
    added = compare_bytes(encoded(before), encoded(minimal), "engineering_scope")
    assert not added.passed
    assert added.introduced_prohibited_violations[0].intent_id == "req_eng_plc"
    repaired = compare_bytes(encoded(minimal), encoded(before), "engineering_scope")
    assert repaired.resolved_prohibited_violations == added.introduced_prohibited_violations
    assert not repaired.introduced_prohibited_violations
    assert repaired.proposed.passed and not repaired.baseline.passed


def test_extra_origin_is_tuple_delta_not_new_destination(minimal: dict[str, Any]) -> None:
    minimal["assets"].append({**minimal["assets"][0], "id": "client"})
    minimal["interfaces"].append(
        {
            "id": "client_net",
            "asset_id": "client",
            "placement_zone_id": "control",
            "ipv4": "192.0.2.30/24",
        }
    )
    minimal["transport_edges"].append(
        {
            "id": "t_client",
            "source_interface_id": "client_net",
            "destination_interface_id": "plc_net",
        }
    )
    minimal["scenarios"][0]["origin_asset_ids"].append("client")
    after = deepcopy(minimal)
    allow = deepcopy(minimal["rules"][0])
    allow.update(id="allow_client", source={"asset_ids": ["client"]}, edge_ids=["t_client"])
    after["rules"].append(allow)
    result = compare_bytes(encoded(minimal), encoded(after), "engineering_scope")
    assert result.newly_reachable[0].source_asset_id == "client"
    assert not result.newly_reachable_assets


def test_common_service_definition_change_is_not_connectivity_delta(
    minimal: dict[str, Any],
) -> None:
    after = deepcopy(minimal)
    after["services"][0]["destination_ports"] = [{"start": 503, "end": 503}]
    result = compare_bytes(encoded(minimal), encoded(after), "engineering_scope")
    assert result.noncomparable_service_ids == ("svc_plc",)
    assert not result.newly_reachable and not result.no_longer_reachable
    assert not result.broken_required_communications
    assert result.intent_changes[0].classification == "definition_changed"
    assert result.intent_changes[0].baseline_passed and not result.intent_changes[0].proposed_passed
    assert any(c.entity_kind == "services" for c in result.entity_changes)


@pytest.mark.parametrize("field", ["asset_id", "interface_id", "protocol", "destination_ports"])
def test_each_service_semantic_field_blocks_false_deltas(
    minimal: dict[str, Any], field: str
) -> None:
    # Use listener on eng for a valid changed asset+binding, otherwise change one field.
    after = deepcopy(minimal)
    if field == "asset_id":
        after["services"][0].update(asset_id="eng", interface_id="eng_net")
        after["scenarios"][0]["origin_asset_ids"] = ["eng", "plc"]
        minimal["scenarios"][0]["origin_asset_ids"] = ["eng", "plc"]
        after["intents"] = []
    elif field == "interface_id":
        after["interfaces"].append(
            {
                "id": "other",
                "asset_id": "plc",
                "placement_zone_id": "control",
                "ipv4": "192.0.2.21/24",
            }
        )
        after["services"][0][field] = "other"
    elif field == "protocol":
        after["services"][0][field] = "udp"
    else:
        after["services"][0][field] = [{"start": 501, "end": 503}]
    result = compare_bytes(encoded(minimal), encoded(after), "engineering_scope")
    assert result.noncomparable_service_ids == ("svc_plc",)
    assert result.newly_reachable == result.no_longer_reachable == ()


def test_inventory_additions_are_observed_separately(minimal: dict[str, Any]) -> None:
    before = deepcopy(minimal)
    after = deepcopy(minimal)
    after["assets"].append({**after["assets"][1], "id": "new_plc"})
    after["interfaces"].append(
        {
            "id": "new_net",
            "asset_id": "new_plc",
            "placement_zone_id": "control",
            "ipv4": "192.0.2.21/24",
        }
    )
    after["services"].append(
        {
            **deepcopy(after["services"][0]),
            "id": "new_service",
            "asset_id": "new_plc",
            "interface_id": "new_net",
        }
    )
    after["transport_edges"].append(
        {"id": "t_new", "source_interface_id": "eng_net", "destination_interface_id": "new_net"}
    )
    after["rules"].append(
        {
            **deepcopy(after["rules"][0]),
            "id": "allow_new",
            "edge_ids": ["t_new"],
            "destination": {"asset_ids": ["new_plc"]},
        }
    )
    scope = QueryScope(("eng",), ("svc_plc", "new_service"))
    result = compare_bytes(encoded(before), encoded(after), scope=scope)
    assert result.baseline.unavailable_destination_service_ids == ("new_service",)
    assert len(result.proposed.observations) == 2
    assert not result.newly_reachable and not result.newly_reachable_assets
    assert next(i for i in result.inventory_changes if i.entity_kind == "assets").added_ids == (
        "new_plc",
    )
    reverse = compare_bytes(encoded(after), encoded(before), scope=scope)
    assert next(i for i in reverse.inventory_changes if i.entity_kind == "assets").removed_ids == (
        "new_plc",
    )


def test_rename_is_inventory_add_remove_not_identity_inference(minimal: dict[str, Any]) -> None:
    before = deepcopy(minimal)
    after = deepcopy(minimal)
    after["services"][0]["id"] = "renamed"
    after["intents"] = []
    after["scenarios"] = []
    scope = QueryScope(("eng",), ("svc_plc", "renamed"))
    result = compare_bytes(encoded(before), encoded(after), scope=scope)
    changes = next(i for i in result.inventory_changes if i.entity_kind == "services")
    assert changes.added_ids == ("renamed",) and changes.removed_ids == ("svc_plc",)
    assert result.newly_reachable == result.no_longer_reachable == ()


def test_criticality_only_is_metadata(minimal: dict[str, Any]) -> None:
    after = deepcopy(minimal)
    after["assets"][1]["criticality"] = "unspecified"
    result = compare_bytes(encoded(minimal), encoded(after), "engineering_scope")
    assert not result.newly_reachable and not result.no_longer_reachable
    change = next(c for c in result.entity_changes if c.entity_kind == "assets")
    assert change.fields[0].classification == "metadata"
    assert result.baseline.destination_assets[0].criticality == "critical"
    assert result.proposed.destination_assets[0].criticality == "unspecified"


def test_redundant_path_and_extra_atom_boundaries_make_no_delta(minimal: dict[str, Any]) -> None:
    minimal["services"][0]["destination_ports"] = [{"start": 500, "end": 510}]
    minimal["rules"][0]["destination_ports"] = [{"start": 500, "end": 510}]
    after = deepcopy(minimal)
    after["transport_edges"].append({**after["transport_edges"][0], "id": "parallel"})
    after["rules"].append(
        {
            **deepcopy(after["rules"][0]),
            "id": "redundant",
            "edge_ids": ["parallel"],
            "destination_ports": [{"start": 503, "end": 506}],
        }
    )
    result = compare_bytes(encoded(minimal), encoded(after), "engineering_scope")
    assert result.newly_reachable == result.no_longer_reachable == ()
    assert [(f.start, f.end) for f in result.baseline.observations] == [(500, 510)]
    assert [(i.start, i.end) for i in result.baseline.queries[0].intervals] == [
        (500, 502),
        (503, 506),
        (507, 510),
    ]
    assert [(i.start, i.end) for i in result.proposed.queries[0].intervals] == [
        (500, 502),
        (503, 506),
        (507, 510),
    ]


def test_identity_and_reversal(minimal: dict[str, Any]) -> None:
    identical = compare_bytes(encoded(minimal), encoded(minimal), "engineering_scope")
    assert identical.passed
    assert not identical.entity_changes and not identical.inventory_changes
    assert identical.newly_reachable == identical.no_longer_reachable == ()
    assert not identical.broken_required_communications
    after = deepcopy(minimal)
    after["rules"] = []
    forward = compare_bytes(encoded(minimal), encoded(after), "engineering_scope")
    backward = compare_bytes(encoded(after), encoded(minimal), "engineering_scope")
    assert forward.newly_reachable == backward.no_longer_reachable
    assert forward.no_longer_reachable == backward.newly_reachable
    assert forward.newly_reachable_assets == backward.no_longer_reachable_assets
    assert forward.baseline == backward.proposed


@pytest.mark.parametrize(
    "field", ["purpose", "controlled_process", "boundary_description", "completeness_assertion"]
)
def test_t22_suc_definition_change_not_risk_reduction(minimal: dict[str, Any], field: str) -> None:
    after = deepcopy(minimal)
    after["suc"][field] = "Updated owner declaration"
    result = compare_bytes(encoded(minimal), encoded(after), "engineering_scope")
    assert result.suc_definition_changes[0].field == field
    assert result.newly_reachable == result.no_longer_reachable == ()


def test_suc_identity_and_embedded_scope_are_mandatory(minimal: dict[str, Any]) -> None:
    after = deepcopy(minimal)
    after["suc"]["id"] = "different"
    with pytest.raises(ModelError) as caught:
        compare_bytes(encoded(minimal), encoded(after), "engineering_scope")
    assert caught.value.diagnostics[0].code == "SCOPE_MISMATCH"
    after = deepcopy(minimal)
    after["scenarios"][0]["origin_asset_ids"].append("plc")
    with pytest.raises(ModelError) as caught:
        compare_bytes(encoded(minimal), encoded(after), "engineering_scope")
    assert caught.value.diagnostics[0].code == "SCOPE_MISMATCH"


def test_changed_intent_and_selector_expansion_are_not_regressions(minimal: dict[str, Any]) -> None:
    minimal["intents"][0]["source"] = {"all_assets": True}
    after = deepcopy(minimal)
    after["assets"].append({**after["assets"][0], "id": "new_origin"})
    after["interfaces"].append(
        {
            "id": "new_if",
            "asset_id": "new_origin",
            "placement_zone_id": "control",
            "ipv4": "192.0.2.30/24",
        }
    )
    result = compare_bytes(encoded(minimal), encoded(after), "engineering_scope")
    assert result.intent_changes[0].classification == "definition_changed"
    assert not result.broken_required_communications
    assert not result.proposed.passed


def test_new_removed_modified_intents_keep_per_side_status(minimal: dict[str, Any]) -> None:
    after = deepcopy(minimal)
    after["intents"][0]["id"] = "new_requirement"
    after["rules"] = []
    result = compare_bytes(encoded(minimal), encoded(after), "engineering_scope")
    assert {i.id: i.classification for i in result.intent_changes} == {
        "new_requirement": "added",
        "req_eng_plc": "removed",
    }
    assert not result.broken_required_communications and not result.passed


def test_partial_regression_detected_even_if_intent_already_fails(minimal: dict[str, Any]) -> None:
    minimal["services"][0]["destination_ports"] = [{"start": 500, "end": 502}]
    minimal["rules"][0]["destination_ports"] = [{"start": 500, "end": 500}]
    after = deepcopy(minimal)
    after["rules"] = []
    result = compare_bytes(encoded(minimal), encoded(after), "engineering_scope")
    assert not result.baseline.passed and not result.proposed.passed
    assert [(i.flow.start, i.flow.end) for i in result.broken_required_communications] == [
        (500, 500)
    ]
    assert [(i.start, i.end) for i in result.intent_changes[0].persisting_failures] == [(501, 502)]


@pytest.mark.parametrize(
    "name",
    [
        "invalid-missing-reference.yaml",
        "invalid-interface-placement.yaml",
        "unsupported-model.yaml",
    ],
)
def test_invalid_snapshots_still_stop_before_analysis(name: str, minimal: dict[str, Any]) -> None:
    from pathlib import Path

    invalid = (Path(__file__).parent / "fixtures" / name).read_bytes()
    with pytest.raises(ModelError):
        compare_bytes(encoded(minimal), invalid, "engineering_scope")


def test_combined_scenario_and_intent_budget_precedes_bfs(
    minimal: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("preflight must stop before BFS")

    monkeypatch.setattr(ReachabilityEngine, "_search", forbidden)
    # One scenario atom plus one intent atom: 2 * 3 * (4 states + 1 edge) = 30.
    with pytest.raises(ModelError) as caught:
        exposure_bytes(
            encoded(minimal), "engineering_scope", replace(RESOURCE_LIMITS, state_edge_visits=29)
        )
    assert caught.value.diagnostics[0].category == "resource_limit"


def test_set_ordering_does_not_change_json(boundary: dict[str, Any]) -> None:
    original = compare_bytes(encoded(boundary), encoded(boundary), "support_scope")
    for field in (
        "assets",
        "interfaces",
        "services",
        "rules",
        "intents",
        "transport_edges",
        "forwarding_edges",
    ):
        boundary[field].reverse()
    changed = compare_bytes(encoded(boundary), encoded(boundary), "support_scope")
    assert asdict(original) == asdict(changed)


def test_asset_deduplication_preserves_service_and_origin_observations(
    minimal: dict[str, Any],
) -> None:
    other = deepcopy(minimal["services"][0])
    other["id"] = "overlapping_listener"
    minimal["services"].append(other)
    minimal["scenarios"][0]["destination_service_ids"].append("overlapping_listener")
    result = exposure_bytes(encoded(minimal), "engineering_scope")
    assert len(result.observations) == 2 and len(result.destination_assets) == 1
    assert {f.service_id for f in result.observations} == {"svc_plc", "overlapping_listener"}


def test_suc_access_and_dependency_changes_are_explicit(boundary: dict[str, Any]) -> None:
    after = deepcopy(boundary)
    after["suc"]["access_points"][1]["description"] = "Updated physical access declaration"
    after["suc"]["external_dependencies"][0]["description"] = (
        "Updated external dependency declaration"
    )
    result = compare_bytes(encoded(boundary), encoded(after), "support_scope")
    assert {f.field for f in result.suc_definition_changes} == {
        "access_points",
        "external_dependencies",
    }
    assert not result.newly_reachable and not result.no_longer_reachable


def test_embedded_scenario_ids_must_match(minimal: dict[str, Any]) -> None:
    after = deepcopy(minimal)
    after["scenarios"][0]["id"] = "renamed"
    with pytest.raises(ModelError) as caught:
        compare_bytes(encoded(minimal), encoded(after), "engineering_scope")
    assert caught.value.diagnostics[0].code == "SCOPE_MISMATCH"


@pytest.mark.parametrize(
    "scope",
    [
        QueryScope(("absent",), ("svc_plc",)),
        QueryScope(("eng",), ("absent",)),
        QueryScope(("eng", "eng"), ("svc_plc",)),
        QueryScope((), ("svc_plc",)),
        QueryScope(("Bad",), ("svc_plc",)),
    ],
)
def test_invalid_explicit_scopes_are_not_empty_success(
    minimal: dict[str, Any], scope: QueryScope
) -> None:
    with pytest.raises(ModelError):
        compare_bytes(encoded(minimal), encoded(minimal), scope=scope)


def test_comparison_budget_uses_common_boundaries_from_both_sides(minimal: dict[str, Any]) -> None:
    from otarchguard.api import validate_bytes
    from otarchguard.intervals import partition

    minimal["services"][0]["destination_ports"] = [{"start": 1, "end": 65535}]
    minimal["rules"][0]["destination_ports"] = [{"start": 1, "end": 65535}]
    before, after = deepcopy(minimal), deepcopy(minimal)
    for data, offset in ((before, 2), (after, 3002)):
        for index in range(600):
            rule = deepcopy(data["rules"][0])
            rule.update(
                id=f"boundary_{index}",
                destination_ports=[{"start": offset + 4 * index, "end": offset + 4 * index}],
            )
            data["rules"].append(rule)
        model = validate_bytes(encoded(data)).model
        assert len(partition(model, frozenset({"svc_plc"}), RESOURCE_LIMITS)["tcp"]) < 2048
    with pytest.raises(ModelError) as caught:
        compare_bytes(encoded(before), encoded(after), "engineering_scope")
    assert "protocol_port_atoms" in caught.value.diagnostics[0].message


def test_added_origin_is_inventory_not_new_connectivity(minimal: dict[str, Any]) -> None:
    after = deepcopy(minimal)
    after["assets"].append({**after["assets"][0], "id": "client"})
    after["interfaces"].append(
        {
            "id": "client_net",
            "asset_id": "client",
            "placement_zone_id": "control",
            "ipv4": "192.0.2.30/24",
        }
    )
    after["transport_edges"].append(
        {
            "id": "client_plc",
            "source_interface_id": "client_net",
            "destination_interface_id": "plc_net",
        }
    )
    rule = deepcopy(after["rules"][0])
    rule.update(id="allow_client", source={"asset_ids": ["client"]}, edge_ids=["client_plc"])
    after["rules"].append(rule)
    result = compare_bytes(
        encoded(minimal), encoded(after), scope=QueryScope(("eng", "client"), ("svc_plc",))
    )
    assert result.baseline.unavailable_origin_asset_ids == ("client",)
    assert len(result.proposed.observations) == 2
    assert result.newly_reachable == ()


def test_per_side_scope_cannot_be_empty(minimal: dict[str, Any]) -> None:
    after = deepcopy(minimal)
    after["services"][0]["id"] = "renamed"
    after["intents"] = []
    after["scenarios"] = []
    with pytest.raises(ModelError) as caught:
        compare_bytes(encoded(minimal), encoded(after), scope=QueryScope(("eng",), ("renamed",)))
    assert caught.value.diagnostics[0].code == "SCOPE_MISMATCH"


def test_scenario_description_is_definition_metadata_not_scope_change(
    minimal: dict[str, Any],
) -> None:
    after = deepcopy(minimal)
    after["scenarios"][0]["description"] = "Updated origin assumption prose"
    result = compare_bytes(encoded(minimal), encoded(after), "engineering_scope")
    assert result.newly_reachable == result.no_longer_reachable == ()
    assert any(c.entity_kind == "scenarios" for c in result.entity_changes)


def test_t22_scope_changes_are_revalidated_and_explicit(boundary: dict[str, Any]) -> None:
    after = deepcopy(boundary)
    after["assets"][0]["scope"] = "internal"
    after["zones"][0]["scope"] = "internal"
    after["suc"]["access_points"] = [
        a for a in after["suc"]["access_points"] if a["id"] != "ap_it_dmz"
    ]
    after["suc"]["external_dependencies"][0]["external_asset_ids"] = []
    result = compare_bytes(encoded(boundary), encoded(after), "support_scope")
    assert {"assets.it.scope", "zones.enterprise.scope"} <= {
        c.field for c in result.suc_definition_changes
    }
    assert result.newly_reachable == result.no_longer_reachable == ()


def test_changed_criticality_is_annotated_on_connectivity_delta(minimal: dict[str, Any]) -> None:
    before = deepcopy(minimal)
    before["rules"] = []
    before["assets"][1]["criticality"] = "high"
    result = compare_bytes(encoded(before), encoded(minimal), "engineering_scope")
    asset = result.newly_reachable_assets[0]
    assert asset.baseline_criticality == "high" and asset.proposed_criticality == "critical"
