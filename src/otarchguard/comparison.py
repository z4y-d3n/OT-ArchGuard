"""Stable-ID, common-scope snapshot comparison without risk or deployment conclusions."""

from dataclasses import dataclass
from pathlib import Path
from typing import cast

from otarchguard.api import ValidatedArchitecture, validate_bytes, validate_file
from otarchguard.contract import RESOURCE_LIMITS, ResourceLimits
from otarchguard.diagnostics import fail
from otarchguard.domain import CommunicationIntent, Record
from otarchguard.exposure import (
    ExposureResult,
    QueryScope,
    evaluate_scope,
    normalize_scope,
    scenario_scope,
)
from otarchguard.flows import FlowInterval, difference, intersection, observations
from otarchguard.loading import YamlValue
from otarchguard.validation import expand_selector


@dataclass(frozen=True, slots=True)
class InventoryChange:
    entity_kind: str
    added_ids: tuple[str, ...]
    removed_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class FieldChange:
    field: str
    classification: str
    baseline: YamlValue
    proposed: YamlValue


@dataclass(frozen=True, slots=True)
class EntityChange:
    entity_kind: str
    id: str
    fields: tuple[FieldChange, ...]


@dataclass(frozen=True, slots=True)
class ComparedAsset:
    asset_id: str
    baseline_criticality: str
    proposed_criticality: str


@dataclass(frozen=True, slots=True)
class IntentComparison:
    id: str
    classification: str
    baseline_passed: bool | None
    proposed_passed: bool | None
    introduced_failures: tuple[FlowInterval, ...]
    resolved_failures: tuple[FlowInterval, ...]
    persisting_failures: tuple[FlowInterval, ...]


@dataclass(frozen=True, slots=True)
class IntentFlowChange:
    intent_id: str
    flow: FlowInterval


@dataclass(frozen=True, slots=True)
class ComparisonResult:
    suc_id: str
    scenario_id: str | None
    query_scope: QueryScope
    baseline: ExposureResult
    proposed: ExposureResult
    comparable_service_ids: tuple[str, ...]
    noncomparable_service_ids: tuple[str, ...]
    newly_reachable: tuple[FlowInterval, ...]
    no_longer_reachable: tuple[FlowInterval, ...]
    newly_reachable_assets: tuple[ComparedAsset, ...]
    no_longer_reachable_assets: tuple[ComparedAsset, ...]
    inventory_changes: tuple[InventoryChange, ...]
    entity_changes: tuple[EntityChange, ...]
    suc_definition_changes: tuple[FieldChange, ...]
    intent_changes: tuple[IntentComparison, ...]
    broken_required_communications: tuple[IntentFlowChange, ...]
    introduced_prohibited_violations: tuple[IntentFlowChange, ...]
    resolved_prohibited_violations: tuple[IntentFlowChange, ...]
    passed: bool
    interpretation: str = (
        "Connectivity deltas over common stable entities/services only. "
        "Reduced exposure does not imply risk reduction or cancel failed communication intents."
    )


def _fields(left: Record, right: Record, kind: str) -> tuple[FieldChange, ...]:
    before = cast(dict[str, YamlValue], left.model_dump(mode="json", exclude_none=True))
    after = cast(dict[str, YamlValue], right.model_dump(mode="json", exclude_none=True))
    result: list[FieldChange] = []
    for name in sorted(before.keys() | after.keys()):
        if before.get(name) == after.get(name):
            continue
        classification = "metadata"
        if kind in {"services", "scenarios"}:
            classification = "definition"
        elif kind == "intents":
            classification = "intent_definition"
        elif kind == "rules":
            classification = "enforcement"
        elif kind in {"suc", "access_points", "external_dependencies"} or (
            kind in {"assets", "zones"} and name == "scope"
        ):
            classification = "suc_definition"
        elif kind in {"interfaces", "conduits", "transport_edges", "forwarding_edges"} or name in {
            "zone_id",
            "kind",
        }:
            classification = "structural"
        result.append(FieldChange(name, classification, before.get(name), after.get(name)))
    return tuple(result)


def _catalogs(validated: ValidatedArchitecture) -> dict[str, dict[str, Record]]:
    model = validated.model
    collections: dict[str, tuple[Record, ...]] = {
        "assets": model.assets,
        "zones": model.zones,
        "interfaces": model.interfaces,
        "conduits": model.conduits,
        "transport_edges": model.transport_edges,
        "forwarding_edges": model.forwarding_edges,
        "services": model.services,
        "rules": model.rules,
        "intents": model.intents,
        "scenarios": model.scenarios,
        "access_points": model.suc.access_points,
        "external_dependencies": model.suc.external_dependencies,
    }
    return {
        kind: {cast(str, record.model_dump()["id"]): record for record in records}
        for kind, records in collections.items()
    }


def declaration_catalogs(validated: ValidatedArchitecture) -> dict[str, dict[str, Record]]:
    """Canonical native collections shared by structural and analytical comparison."""
    return _catalogs(validated)


def declaration_fields(left: Record, right: Record, kind: str) -> tuple[FieldChange, ...]:
    """Exact native field differences; no reachability is inferred."""
    return _fields(left, right, kind)


def _intent_signature(validated: ValidatedArchitecture, intent: CommunicationIntent) -> object:
    model = validated.model
    assets, zones = {a.id: a for a in model.assets}, {z.id: z for z in model.zones}
    services = {s.id: s for s in model.services}
    return (
        intent,
        expand_selector(intent.source, assets, zones),
        tuple(services[s] for s in intent.destination_service_ids),
    )


def _intent_comparisons(
    before: ValidatedArchitecture,
    after: ValidatedArchitecture,
    left: ExposureResult,
    right: ExposureResult,
) -> tuple[IntentComparison, ...]:
    definitions_left = {i.id: i for i in before.model.intents}
    definitions_right = {i.id: i for i in after.model.intents}
    results_left = {i.id: i for i in left.intent_checks.intents}
    results_right = {i.id: i for i in right.intent_checks.intents}
    result: list[IntentComparison] = []
    for identity in sorted(definitions_left.keys() | definitions_right.keys()):
        old_result, new_result = results_left.get(identity), results_right.get(identity)
        classification = "unchanged"
        if old_result is None:
            classification = "added"
        elif new_result is None:
            classification = "removed"
        elif _intent_signature(before, definitions_left[identity]) != _intent_signature(
            after, definitions_right[identity]
        ):
            classification = "definition_changed"
        introduced: tuple[FlowInterval, ...] = ()
        resolved: tuple[FlowInterval, ...] = ()
        persisting: tuple[FlowInterval, ...] = ()
        if classification == "unchanged" and old_result is not None and new_result is not None:
            failed_reachability = old_result.kind == "prohibited"
            old = observations(old_result.queries, failed_reachability)
            new = observations(new_result.queries, failed_reachability)
            introduced, resolved, persisting = (
                difference(new, old),
                difference(old, new),
                intersection(old, new),
            )
        result.append(
            IntentComparison(
                identity,
                classification,
                old_result.passed if old_result else None,
                new_result.passed if new_result else None,
                introduced,
                resolved,
                persisting,
            )
        )
    return tuple(result)


def compare_architectures(
    baseline: ValidatedArchitecture,
    proposed: ValidatedArchitecture,
    scenario_id: str | None = None,
    *,
    scope: QueryScope | None = None,
    limits: ResourceLimits = RESOURCE_LIMITS,
) -> ComparisonResult:
    if baseline.model.suc.id != proposed.model.suc.id:
        fail("SCOPE_MISMATCH", "$.suc.id", "Comparison requires matching SUC identities.")
    if (scenario_id is None) == (scope is None):
        fail(
            "SCOPE_MISMATCH",
            "$.comparison_scope",
            "Choose one embedded scenario or one explicit common scope.",
        )
    if scenario_id is not None:
        if any(
            scenario_id not in {s.id for s in snapshot.model.scenarios}
            for snapshot in (baseline, proposed)
        ):
            fail(
                "SCOPE_MISMATCH",
                "$.comparison_scope",
                "The same declared scenario ID must exist in both snapshots.",
            )
        scope = scenario_scope(baseline, scenario_id)
        if scope != scenario_scope(proposed, scenario_id):
            fail(
                "SCOPE_MISMATCH",
                "$.comparison_scope",
                "Embedded scenario sets must match; align them or supply one explicit scope.",
            )
    assert scope is not None
    scope = normalize_scope(scope)
    left_catalogs, right_catalogs = _catalogs(baseline), _catalogs(proposed)
    for field, identities, catalog in (
        ("origin_asset_ids", scope.origin_asset_ids, "assets"),
        ("destination_service_ids", scope.destination_service_ids, "services"),
    ):
        if not set(identities) <= left_catalogs[catalog].keys() | right_catalogs[catalog].keys():
            fail(
                "MISSING_REFERENCE",
                f"$.comparison_scope.{field}",
                "Explicit query IDs must exist in the union inventory.",
            )

    def side(
        validated: ValidatedArchitecture,
        peer: ValidatedArchitecture,
        catalogs: dict[str, dict[str, Record]],
    ) -> ExposureResult:
        origins = tuple(i for i in scope.origin_asset_ids if i in catalogs["assets"])
        services = tuple(i for i in scope.destination_service_ids if i in catalogs["services"])
        if not origins or not services:
            fail(
                "SCOPE_MISMATCH",
                "$.comparison_scope",
                "At least one origin and listener must exist in each snapshot.",
            )
        return evaluate_scope(
            validated,
            QueryScope(origins, services),
            scenario_id,
            limits,
            partition_peers=(peer.model,),
            unavailable_origins=tuple(
                i for i in scope.origin_asset_ids if i not in catalogs["assets"]
            ),
            unavailable_services=tuple(
                i for i in scope.destination_service_ids if i not in catalogs["services"]
            ),
        )

    left, right = side(baseline, proposed, left_catalogs), side(proposed, baseline, right_catalogs)
    common_services = set(left_catalogs["services"]) & set(right_catalogs["services"])
    comparable = {
        s for s in common_services if left_catalogs["services"][s] == right_catalogs["services"][s]
    }
    common_assets = set(left_catalogs["assets"]) & set(right_catalogs["assets"])

    def eligible(flows: tuple[FlowInterval, ...]) -> tuple[FlowInterval, ...]:
        return tuple(
            f
            for f in flows
            if f.service_id in comparable
            and f.source_asset_id in common_assets
            and f.destination_asset_id in common_assets
        )

    old, new = eligible(left.observations), eligible(right.observations)
    added, removed = difference(new, old), difference(old, new)
    old_assets, new_assets = (
        {f.destination_asset_id for f in old},
        {f.destination_asset_id for f in new},
    )
    assets_before = {a.id: a for a in baseline.model.assets}
    assets_after = {a.id: a for a in proposed.model.assets}

    def asset_summary(identities: set[str]) -> tuple[ComparedAsset, ...]:
        return tuple(
            ComparedAsset(i, assets_before[i].criticality, assets_after[i].criticality)
            for i in sorted(identities)
        )

    inventory: list[InventoryChange] = []
    entities: list[EntityChange] = []
    for kind in sorted(left_catalogs):
        old_records, new_records = left_catalogs[kind], right_catalogs[kind]
        if old_records.keys() != new_records.keys():
            inventory.append(
                InventoryChange(
                    kind,
                    tuple(sorted(new_records.keys() - old_records.keys())),
                    tuple(sorted(old_records.keys() - new_records.keys())),
                )
            )
        for identity in sorted(old_records.keys() & new_records.keys()):
            fields = _fields(old_records[identity], new_records[identity], kind)
            if fields:
                entities.append(EntityChange(kind, identity, fields))
    suc_changes = list(_fields(baseline.model.suc, proposed.model.suc, "suc"))
    for kind in ("assets", "zones"):
        for change in entities:
            if change.entity_kind == kind:
                suc_changes.extend(
                    FieldChange(
                        f"{kind}.{change.id}.{f.field}", f.classification, f.baseline, f.proposed
                    )
                    for f in change.fields
                    if f.field == "scope"
                )
    snapshot_fields = tuple(
        FieldChange(name, "metadata", getattr(baseline.model, name), getattr(proposed.model, name))
        for name in ("architecture_id", "revision")
        if getattr(baseline.model, name) != getattr(proposed.model, name)
    )
    if snapshot_fields:
        entities.append(EntityChange("snapshot", "snapshot", snapshot_fields))
    intent_changes = _intent_comparisons(baseline, proposed, left, right)
    intent_kinds = {i.id: i.kind for i in proposed.model.intents}
    broken = tuple(
        IntentFlowChange(c.id, flow)
        for c in intent_changes
        if intent_kinds.get(c.id) == "required"
        for flow in c.introduced_failures
    )
    introduced = tuple(
        IntentFlowChange(c.id, flow)
        for c in intent_changes
        if intent_kinds.get(c.id) == "prohibited"
        for flow in c.introduced_failures
    )
    resolved = tuple(
        IntentFlowChange(c.id, flow)
        for c in intent_changes
        if intent_kinds.get(c.id) == "prohibited"
        for flow in c.resolved_failures
    )
    return ComparisonResult(
        baseline.model.suc.id,
        scenario_id,
        scope,
        left,
        right,
        tuple(sorted(comparable & set(scope.destination_service_ids))),
        tuple(sorted((common_services - comparable) & set(scope.destination_service_ids))),
        added,
        removed,
        asset_summary(new_assets - old_assets),
        asset_summary(old_assets - new_assets),
        tuple(inventory),
        tuple(entities),
        tuple(suc_changes),
        intent_changes,
        broken,
        introduced,
        resolved,
        left.passed and right.passed,
    )


def compare_files(
    baseline: Path,
    proposed: Path,
    scenario_id: str | None = None,
    *,
    scope: QueryScope | None = None,
    limits: ResourceLimits = RESOURCE_LIMITS,
) -> ComparisonResult:
    return compare_architectures(
        validate_file(baseline, limits),
        validate_file(proposed, limits),
        scenario_id,
        scope=scope,
        limits=limits,
    )


def compare_bytes(
    baseline: bytes,
    proposed: bytes,
    scenario_id: str | None = None,
    *,
    scope: QueryScope | None = None,
    limits: ResourceLimits = RESOURCE_LIMITS,
) -> ComparisonResult:
    return compare_architectures(
        validate_bytes(baseline, limits),
        validate_bytes(proposed, limits),
        scenario_id,
        scope=scope,
        limits=limits,
    )
