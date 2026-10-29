"""Independent literal native-model deltas and model-relative assessment oracles."""

import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
import yaml

from otarchguard.api import ValidatedArchitecture, validate_bytes
from otarchguard.capture.reconciliation import compare_capture, mapping_template
from otarchguard.diagnostics import ModelError
from otarchguard.drift.architecture import compare_models, compare_native_evidence
from otarchguard.drift.contract import DRIFT_LIMITS, Budget, Side
from otarchguard.evidence.attachments import _clone, build_attachment, canonical, model_architecture
from otarchguard.evidence.revisions import build_revision
from otarchguard.evidence.workspace import build_snapshot
from tools.capture_workloads import plant_model

QUERY = [{"source_asset_id": "eng", "service_id": "svc_plc"}]
REFERENCE = {"analysis_id": "reference", "attachments": {"model": "reference-model"}}
CANDIDATE = {"analysis_id": "candidate", "attachments": {"model": "candidate-model"}}


def model(data: dict[str, Any]) -> ValidatedArchitecture:
    return validate_bytes(yaml.safe_dump(data).encode())


def compare(
    reference: dict[str, Any],
    candidate: dict[str, Any],
    queries: list[dict[str, str]] | None = None,
) -> list[dict[str, Any]]:
    return compare_models(
        model(reference), model(candidate), REFERENCE, CANDIDATE, queries or [], Budget()
    )


def test_yaml_presentation_and_collection_order_produce_no_changes(
    minimal: dict[str, Any],
) -> None:
    raw = yaml.safe_dump(minimal)
    first = validate_bytes(raw.encode())
    reordered = deepcopy(minimal)
    reordered["assets"].reverse()
    reordered["interfaces"].reverse()
    second = validate_bytes(("# fictional YAML comment\n" + yaml.safe_dump(reordered)).encode())
    assert first.sha256 == second.sha256
    assert compare_models(first, second, REFERENCE, CANDIDATE, [], Budget()) == []


def test_literal_policy_removal_oracle_preserves_native_reachability(
    minimal: dict[str, Any],
) -> None:
    candidate = deepcopy(minimal)
    candidate["rules"] = []
    findings = compare(minimal, candidate, QUERY)
    assert [(f["category"], f["subtype"], f["key"]) for f in findings] == [
        (
            "DECLARED_ARCHITECTURE_CHANGE",
            "DECLARED_OBJECT_REMOVED",
            {"entity_kind": "rules", "id": "allow_eng_plc"},
        ),
        (
            "NATIVE_ASSESSMENT_DIFFERENCE",
            "REACHABILITY_CHANGED",
            {"source_asset_id": "eng", "service_id": "svc_plc"},
        ),
    ]
    native = findings[1]
    left, right = native["reference"]["native_result"], native["candidate"]["native_result"]
    assert [(i["start"], i["end"], i["reachable"]) for i in left["intervals"]] == [(502, 502, True)]
    assert [(i["start"], i["end"], i["reachable"]) for i in right["intervals"]] == [
        (502, 502, False)
    ]
    assert [s["edge_id"] for s in left["intervals"][0]["witness"]["steps"]] == ["t_eng_plc"]
    assert right["intervals"][0]["diagnostics"]["reason"] == "no_permitted_path"
    assert native["reference"]["source"] == REFERENCE
    assert native["candidate"]["source"] == CANDIDATE
    assert native["reference"]["native_engine_version"] == "1.3.0"
    assert native["candidate"]["native_engine_version"] == "1.3.0"
    assert native["reference"]["model_sha256"] != native["candidate"]["model_sha256"]
    assert all(f["unsupported_interpretations"] for f in findings)


def test_changed_policy_uses_enforcement_classification(minimal: dict[str, Any]) -> None:
    candidate = deepcopy(minimal)
    candidate["rules"][0]["effect"] = "deny"
    findings = compare(minimal, candidate)
    assert len(findings) == 1
    assert findings[0]["candidate"]["fields"] == {"effect": "deny"}
    assert findings[0]["candidate"]["field_classifications"] == {"effect": "enforcement"}


def test_metadata_changes_do_not_invent_structural_changes(minimal: dict[str, Any]) -> None:
    candidate = deepcopy(minimal)
    candidate["assets"][0]["name"] = "Fictional engineering label"
    candidate["revision"] = "fictional_revision"
    findings = compare(minimal, candidate)
    assert [f["key"] for f in findings] == [
        {"entity_kind": "assets", "id": "eng"},
        {"entity_kind": "snapshot"},
    ]
    assert findings[0]["candidate"]["field_classifications"] == {"name": "metadata"}
    assert findings[1]["candidate"]["field_classifications"] == {"revision": "metadata"}


def test_renamed_declaration_is_added_removed_without_heuristic_asset_identity(
    minimal: dict[str, Any],
) -> None:
    candidate = deepcopy(minimal)
    candidate["assets"][0]["id"] = "eng_replacement"
    candidate["interfaces"][0]["asset_id"] = "eng_replacement"
    candidate["rules"][0]["source"]["asset_ids"] = ["eng_replacement"]
    candidate["intents"][0]["source"]["asset_ids"] = ["eng_replacement"]
    candidate["scenarios"][0]["origin_asset_ids"] = ["eng_replacement"]
    findings = compare(minimal, candidate, QUERY)
    assets = [f for f in findings if f["key"].get("entity_kind") == "assets"]
    assert [(f["subtype"], f["key"]["id"]) for f in assets] == [
        ("DECLARED_OBJECT_REMOVED", "eng"),
        ("DECLARED_OBJECT_ADDED", "eng_replacement"),
    ]
    assert findings[-1]["subtype"] == "NATIVE_QUERY_NOT_EQUIVALENT"
    assert findings[-1]["comparability"] == "INDETERMINATE"


@pytest.mark.parametrize("change", ["service_port", "source_address", "source_zone", "suc"])
def test_changed_query_semantics_abstain_instead_of_denied(
    minimal: dict[str, Any], change: str
) -> None:
    candidate = deepcopy(minimal)
    if change == "service_port":
        candidate["services"][0]["destination_ports"] = [{"start": 503, "end": 503}]
    elif change == "source_address":
        candidate["interfaces"][0]["ipv4"] = "192.0.2.11/24"
    elif change == "source_zone":
        candidate["zones"].append({**candidate["zones"][0], "id": "replacement_zone"})
        candidate["assets"][0]["zone_id"] = "replacement_zone"
        candidate["interfaces"][0]["placement_zone_id"] = "replacement_zone"
        candidate["conduits"] = [
            {
                "id": "replacement_channel",
                "name": "Fictional replacement channel",
                "purpose": "Independent changed-placement fixture.",
                "common_security_needs": "Finite declared evidence.",
                "zone_ids": ["control", "replacement_zone"],
            }
        ]
        candidate["transport_edges"][0]["conduit_id"] = "replacement_channel"
    else:
        candidate["suc"]["id"] = "different_fictional_scope"
    findings = compare(minimal, candidate, QUERY)
    assert findings[-1]["subtype"] == "NATIVE_QUERY_NOT_EQUIVALENT"
    assert findings[-1]["comparability"] == "INDETERMINATE"
    assert not any(f["category"] == "NATIVE_ASSESSMENT_DIFFERENCE" for f in findings)


def test_self_asset_and_missing_queries_remain_indeterminate(minimal: dict[str, Any]) -> None:
    findings = compare(
        minimal,
        minimal,
        [
            {"source_asset_id": "plc", "service_id": "svc_plc"},
            {"source_asset_id": "missing", "service_id": "svc_plc"},
        ],
    )
    assert [f["subtype"] for f in findings] == [
        "NATIVE_QUERY_NOT_EQUIVALENT",
        "NATIVE_QUERY_NOT_EQUIVALENT",
    ]
    assert all(f["comparability"] == "INDETERMINATE" for f in findings)


def test_missing_models_do_not_become_empty_architecture(minimal: dict[str, Any]) -> None:
    findings = compare_models(model(minimal), None, REFERENCE, CANDIDATE, QUERY, Budget())
    assert len(findings) == 1
    assert findings[0]["subtype"] == "MODEL_UNAVAILABLE"
    assert findings[0]["candidate"]["model_sha256"] is None


def test_identical_native_results_have_exact_unchanged_assessment(minimal: dict[str, Any]) -> None:
    findings = compare(minimal, minimal, QUERY)
    assert len(findings) == 1
    assert findings[0]["subtype"] == "REACHABILITY_UNCHANGED"
    assert findings[0]["reference"]["native_result"] == findings[0]["candidate"]["native_result"]
    assert type(findings[0]["reference"]["native_result"]["intervals"]) is list
    assert _clone({"findings": findings}) == {"findings": findings}


def test_native_rule_boundaries_are_exactly_paired_without_per_port_expansion(
    minimal: dict[str, Any],
) -> None:
    reference = deepcopy(minimal)
    reference["services"][0]["destination_ports"] = [{"start": 500, "end": 510}]
    reference["rules"][0]["destination_ports"] = [{"start": 500, "end": 505}]
    candidate = deepcopy(reference)
    candidate["rules"][0]["destination_ports"] = [{"start": 500, "end": 507}]
    native = compare(reference, candidate, QUERY)[-1]
    assert native["subtype"] == "REACHABILITY_CHANGED"
    assert [
        (i["start"], i["end"], i["reachable"])
        for i in native["reference"]["native_result"]["intervals"]
    ] == [(500, 505, True), (506, 507, False), (508, 510, False)]
    assert [
        (i["start"], i["end"], i["reachable"])
        for i in native["candidate"]["native_result"]["intervals"]
    ] == [(500, 505, True), (506, 507, True), (508, 510, False)]


@pytest.mark.parametrize(
    "queries",
    [
        [{"source_asset_id": "eng", "service_id": "svc_plc", "force": "true"}],
        [{"source_asset_id": "../eng", "service_id": "svc_plc"}],
        QUERY + QUERY,
        [{"source_asset_id": "eng"}],
    ],
)
def test_malformed_query_selection_is_controlled(
    minimal: dict[str, Any], queries: list[dict[str, str]]
) -> None:
    with pytest.raises(ModelError) as error:
        compare(minimal, minimal, queries)
    assert error.value.diagnostics[0].code == "DRIFT_QUERY"


@pytest.mark.parametrize(
    "field,value", [("native_queries", 1), ("work_units", 1), ("findings", 1), ("report_bytes", 1)]
)
def test_explicit_architecture_budgets_fail_without_partial_result(
    minimal: dict[str, Any], field: str, value: int
) -> None:
    limits = replace(DRIFT_LIMITS, **{field: value})
    candidate = deepcopy(minimal)
    candidate["rules"] = []
    with pytest.raises(ModelError) as error:
        compare_models(
            model(minimal), model(candidate), REFERENCE, CANDIDATE, QUERY, Budget(limits)
        )
    assert error.value.diagnostics[0].code == "LIMIT_EXCEEDED"


def _native_side(*, changed_model: bool = False, pending_source: bool = False) -> Side:
    observations = json.loads(
        (
            Path(__file__).parent / ("fixtures/capture-contract-v2/supported/observations.json")
        ).read_bytes()
    )
    snapshot = build_snapshot(observations)
    declared = plant_model()
    if changed_model:
        declared["rules"] = []
    model_attachment = build_attachment("model", declared, snapshot)
    validated = model_architecture(model_attachment)
    mapping = mapping_template(observations, validated)
    for proposal in mapping["proposals"]:
        if len(proposal["candidates"]) == 1 and not (
            pending_source and proposal["observed_ip"] == "192.0.2.10"
        ):
            proposal.update(
                decision="ACCEPT",
                selected_asset_id=proposal["candidates"][0]["asset_id"],
                selected_interface_id=proposal["candidates"][0]["interface_id"],
                reviewer="Fictional native evidence reviewer",
                rationale="Independently selected fixture assertions only",
            )
    mapping_attachment = build_attachment("mapping", mapping, snapshot, {"model": model_attachment})
    comparison = build_attachment(
        "comparison",
        json.loads(canonical(compare_capture(observations, validated, mapping))),
        snapshot,
        {"model": model_attachment, "mapping": mapping_attachment},
    )
    attachments = {
        "model": model_attachment,
        "mapping": mapping_attachment,
        "comparison": comparison,
    }
    return Side(build_revision(snapshot, attachments), snapshot, attachments)


def test_validated_capture_native_evidence_pairs_exact_model_relative_queries() -> None:
    side = _native_side()
    results = compare_native_evidence(side, side, Budget())
    assert len(results) == 2
    assert {r["subtype"] for r in results} == {"RECONCILIATION_ASSESSMENT_UNCHANGED"}
    assert {r["key"]["source_ip"] for r in results} == {"192.0.2.10", "192.0.2.11"}
    assert all(r["comparability"] == "COMPARABLE" for r in results)
    assert all(
        r["reference"]["native_assessments"][0]["engine_version"] == "1.3.0" for r in results
    )
    assert all(
        r["reference"]["source"]["attachments"]["comparison"]
        == side.attachments["comparison"]["attachment_id"]
        for r in results
    )
    assert _clone({"results": results}) == {"results": results}


def test_capture_native_evidence_changed_model_abstains() -> None:
    results = compare_native_evidence(_native_side(), _native_side(changed_model=True), Budget())
    assert len(results) == 1
    assert results[0]["subtype"] == "NATIVE_RECONCILIATION_MODEL_CHANGED"
    assert results[0]["comparability"] == "INDETERMINATE"


def test_capture_native_evidence_unreviewed_endpoint_never_becomes_denied() -> None:
    results = compare_native_evidence(_native_side(), _native_side(pending_source=True), Budget())
    statuses = {result["key"]["source_ip"]: result["subtype"] for result in results}
    assert statuses == {
        "192.0.2.10": "NATIVE_RECONCILIATION_UNPAIRED",
        "192.0.2.11": "RECONCILIATION_ASSESSMENT_UNCHANGED",
    }


def test_capture_native_evidence_missing_component_remains_explicit() -> None:
    side = _native_side()
    attachments = {k: v for k, v in side.attachments.items() if k != "comparison"}
    absent = Side(build_revision(side.snapshot, attachments), side.snapshot, attachments)
    results = compare_native_evidence(side, absent, Budget())
    assert results[0]["subtype"] == "NATIVE_RECONCILIATION_UNAVAILABLE"
    assert results[0]["comparability"] == "INDETERMINATE"
    assert compare_native_evidence(absent, absent, Budget()) == []
