"""Exact single-query adapters over the established evaluator; no intent evaluation."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from otarchguard import __version__
from otarchguard.api import ValidatedArchitecture, validate_bytes, validate_file
from otarchguard.contract import ID_PATTERN, RESOURCE_LIMITS, ResourceLimits
from otarchguard.diagnostics import fail
from otarchguard.domain import ProtocolValue
from otarchguard.policy_evidence import PolicyEvidence, policy_evidence_for_query
from otarchguard.reachability import ReachabilityEngine, UnreachableDiagnostics, Witness


@dataclass(frozen=True, slots=True)
class TracePortInterval:
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class TraceScope:
    source_asset_id: str
    destination_asset_id: str
    destination_interface_id: str
    service_id: str
    protocol: ProtocolValue
    destination_ports: tuple[TracePortInterval, ...]


@dataclass(frozen=True, slots=True)
class TraceInterval:
    start: int
    end: int
    protocol: ProtocolValue
    reachable: bool
    witness: Witness | None
    diagnostics: UnreachableDiagnostics | None


@dataclass(frozen=True, slots=True)
class TraceWork:
    query_atoms: int
    state_edge_visits: int
    edge_rule_atom_checks: int


@dataclass(frozen=True, slots=True)
class PolicyNotRequested:
    status: Literal["not_requested"] = "not_requested"


@dataclass(frozen=True, slots=True)
class TraceResult:
    scope: TraceScope
    intervals: tuple[TraceInterval, ...]
    model_sha256: str
    work: TraceWork
    resource_ceilings: ResourceLimits
    policy_evidence: PolicyNotRequested | PolicyEvidence
    trace_version: Literal[1] = 1
    engine_version: str = __version__
    schema_version: Literal[1] = 1
    status: Literal["complete"] = "complete"
    intents_assessed: Literal[False] = False
    interpretation: str = (
        "Exact declared initiation for one original source and service-bound destination. "
        "Other pairs and communication intents are unassessed. A witness is one supported route, "
        "not proof of uniqueness, return traffic, authentication, availability or application "
        "success. No deployed connectivity, risk reduction or conformity is established."
    )


def _identifier(value: str, field: str) -> None:
    if type(value) is not str or re.fullmatch(ID_PATTERN, value) is None:
        fail("INVALID_ID", f"$.trace_scope.{field}", "Use the schema-v1 identifier syntax.")


def trace_architecture(
    validated: ValidatedArchitecture,
    source_asset_id: str,
    service_id: str,
    limits: ResourceLimits = RESOURCE_LIMITS,
    *,
    destination_asset_id: str | None = None,
    policy_evidence: bool = False,
) -> TraceResult:
    """Use a completed shared-validation snapshot; retain its immutable identity."""
    _identifier(source_asset_id, "source_asset_id")
    _identifier(service_id, "service_id")
    if type(policy_evidence) is not bool:
        fail("INVALID_VALUE", "$.policy_evidence", "Policy evidence must be a boolean option.")
    assets = {a.id for a in validated.model.assets}
    if source_asset_id not in assets:
        fail("MISSING_REFERENCE", "$.trace_scope.source_asset_id", "Unknown source asset.")
    service = next((s for s in validated.model.services if s.id == service_id), None)
    if service is None:
        fail("MISSING_REFERENCE", "$.trace_scope.service_id", "Unknown destination service.")
    if destination_asset_id is not None:
        _identifier(destination_asset_id, "destination_asset_id")
        if destination_asset_id not in assets:
            fail("MISSING_REFERENCE", "$.trace_scope.destination_asset_id", "Unknown destination.")
        if destination_asset_id != service.asset_id:
            fail(
                "SCOPE_MISMATCH",
                "$.trace_scope.destination_asset_id",
                "Asserted destination must equal the declared service destination asset.",
            )
    engine = ReachabilityEngine(validated, frozenset({service_id}), limits)
    query = engine.evaluate(source_asset_id, service_id)
    return TraceResult(
        TraceScope(
            source_asset_id,
            service.asset_id,
            service.interface_id,
            service_id,
            service.protocol,
            tuple(TracePortInterval(p.start, p.end) for p in service.destination_ports),
        ),
        tuple(
            TraceInterval(i.start, i.end, query.protocol, i.reachable, i.witness, i.diagnostics)
            for i in query.intervals
        ),
        validated.sha256,
        TraceWork(
            engine.queries_reserved,
            engine.work.state_edge_visits,
            engine.work.edge_rule_atom_checks,
        ),
        limits,
        policy_evidence_for_query(engine, query) if policy_evidence else PolicyNotRequested(),
    )


def trace_bytes(
    data: bytes,
    source_asset_id: str,
    service_id: str,
    limits: ResourceLimits = RESOURCE_LIMITS,
    *,
    destination_asset_id: str | None = None,
    policy_evidence: bool = False,
) -> TraceResult:
    return trace_architecture(
        validate_bytes(data, limits),
        source_asset_id,
        service_id,
        limits,
        destination_asset_id=destination_asset_id,
        policy_evidence=policy_evidence,
    )


def trace_file(
    path: Path,
    source_asset_id: str,
    service_id: str,
    limits: ResourceLimits = RESOURCE_LIMITS,
    *,
    destination_asset_id: str | None = None,
    policy_evidence: bool = False,
) -> TraceResult:
    return trace_architecture(
        validate_file(path, limits),
        source_asset_id,
        service_id,
        limits,
        destination_asset_id=destination_asset_id,
        policy_evidence=policy_evidence,
    )
