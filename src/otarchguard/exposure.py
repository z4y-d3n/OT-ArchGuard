"""Finite owner-declared scenario evaluation; exposure is initiation reachability only."""

import re
from dataclasses import dataclass
from pathlib import Path

from otarchguard.api import ValidatedArchitecture, validate_bytes, validate_file
from otarchguard.contract import ID_PATTERN, RESOURCE_LIMITS, ResourceLimits
from otarchguard.diagnostics import fail
from otarchguard.domain import ArchitectureSnapshot
from otarchguard.flows import FlowInterval, observations
from otarchguard.intents import CheckResult, check_intents, intent_query_count
from otarchguard.reachability import QueryResult, ReachabilityEngine


@dataclass(frozen=True, slots=True)
class QueryScope:
    origin_asset_ids: tuple[str, ...]
    destination_service_ids: tuple[str, ...]


def normalize_scope(scope: QueryScope) -> QueryScope:
    for field, values in (
        ("origin_asset_ids", scope.origin_asset_ids),
        ("destination_service_ids", scope.destination_service_ids),
    ):
        if not values:
            fail(
                "EMPTY_QUERY_SCOPE",
                f"$.comparison_scope.{field}",
                "An explicit nonempty scope is required.",
            )
        if len(set(values)) != len(values):
            fail("DUPLICATE_ITEM", f"$.comparison_scope.{field}", "Scope IDs must be distinct.")
        if any(type(v) is not str or re.fullmatch(ID_PATTERN, v) is None for v in values):
            fail(
                "INVALID_ID",
                f"$.comparison_scope.{field}",
                "Scope uses the schema-v1 identifier syntax.",
            )
    return QueryScope(
        tuple(sorted(scope.origin_asset_ids)), tuple(sorted(scope.destination_service_ids))
    )


def scenario_scope(validated: ValidatedArchitecture, scenario_id: str) -> QueryScope:
    scenario = next((s for s in validated.model.scenarios if s.id == scenario_id), None)
    if scenario is None:
        fail("MISSING_REFERENCE", "$.scenario", "Requested exposure scenario does not exist.")
    return QueryScope(scenario.origin_asset_ids, scenario.destination_service_ids)


@dataclass(frozen=True, slots=True)
class AssetExposure:
    asset_id: str
    criticality: str


@dataclass(frozen=True, slots=True)
class ExposureResult:
    snapshot_sha256: str
    suc_id: str
    scenario_id: str | None
    query_scope: QueryScope
    unavailable_origin_asset_ids: tuple[str, ...]
    unavailable_destination_service_ids: tuple[str, ...]
    observations: tuple[FlowInterval, ...]
    destination_assets: tuple[AssetExposure, ...]
    queries: tuple[QueryResult, ...]
    intent_checks: CheckResult
    passed: bool
    atom_queries: int
    state_edge_visits: int
    edge_rule_atom_checks: int
    completeness_assertion: str
    interpretation: str = (
        "Owner-declared origin assumptions and listener reachability; "
        "not compromise probability, damage, risk or security levels."
    )


def evaluate_scope(
    validated: ValidatedArchitecture,
    scope: QueryScope,
    scenario_id: str | None,
    limits: ResourceLimits = RESOURCE_LIMITS,
    *,
    partition_peers: tuple[ArchitectureSnapshot, ...] = (),
    unavailable_origins: tuple[str, ...] = (),
    unavailable_services: tuple[str, ...] = (),
) -> ExposureResult:
    """Evaluate present scoped entities; never label absent inventory unreachable."""
    scope = normalize_scope(scope)
    model = validated.model
    assets, services = {a.id: a for a in model.assets}, {s.id: s for s in model.services}
    if (
        not set(scope.origin_asset_ids) <= assets.keys()
        or not set(scope.destination_service_ids) <= services.keys()
    ):
        fail(
            "MISSING_REFERENCE",
            "$.query_scope",
            "Selected origin/listener does not exist in this snapshot.",
        )
    if not set(scope.origin_asset_ids) <= {i.asset_id for i in model.interfaces}:
        fail(
            "EMPTY_QUERY_SCOPE", "$.query_scope", "Each selected origin needs a declared interface."
        )
    if not any(
        len(scope.origin_asset_ids) > int(services[s].asset_id in scope.origin_asset_ids)
        for s in scope.destination_service_ids
    ):
        fail(
            "EMPTY_QUERY_SCOPE",
            "$.query_scope",
            "Scope must contain at least one inter-asset pair.",
        )
    requested = frozenset(scope.destination_service_ids) | frozenset(
        service for intent in model.intents for service in intent.destination_service_ids
    )
    engine = ReachabilityEngine(validated, requested, limits, partition_peers=partition_peers)
    planned = sum(
        (len(scope.origin_asset_ids) - int(services[s].asset_id in scope.origin_asset_ids))
        * len(engine.service_atoms[s])
        for s in scope.destination_service_ids
    )
    engine.ensure_capacity(planned + intent_query_count(engine))
    queries = tuple(
        engine.evaluate(source, service)
        for source in scope.origin_asset_ids
        for service in scope.destination_service_ids
        if source != services[service].asset_id
    )
    reachable = observations(queries)
    destinations = tuple(
        AssetExposure(identity, assets[identity].criticality)
        for identity in sorted({f.destination_asset_id for f in reachable})
    )
    checks = check_intents(engine)
    return ExposureResult(
        validated.sha256,
        model.suc.id,
        scenario_id,
        scope,
        unavailable_origins,
        unavailable_services,
        reachable,
        destinations,
        queries,
        checks,
        checks.passed,
        engine.queries_reserved,
        engine.work.state_edge_visits,
        engine.work.edge_rule_atom_checks,
        model.suc.completeness_assertion,
    )


def exposure_architecture(
    validated: ValidatedArchitecture,
    scenario_id: str,
    limits: ResourceLimits = RESOURCE_LIMITS,
) -> ExposureResult:
    return evaluate_scope(validated, scenario_scope(validated, scenario_id), scenario_id, limits)


def exposure_file(
    path: Path, scenario_id: str, limits: ResourceLimits = RESOURCE_LIMITS
) -> ExposureResult:
    return exposure_architecture(validate_file(path, limits), scenario_id, limits)


def exposure_bytes(
    data: bytes, scenario_id: str, limits: ResourceLimits = RESOURCE_LIMITS
) -> ExposureResult:
    return exposure_architecture(validate_bytes(data, limits), scenario_id, limits)
