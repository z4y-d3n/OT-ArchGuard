"""Bounded finite matching effects, never rule-removal or global redundancy analysis."""

from dataclasses import dataclass
from typing import Literal

from otarchguard.contract import ResourceLimits
from otarchguard.diagnostics import check_limit, fail
from otarchguard.domain import ProtocolValue
from otarchguard.policy import decide
from otarchguard.reachability import QueryResult, ReachabilityEngine


@dataclass(frozen=True, slots=True)
class PolicyScope:
    source_asset_id: str
    destination_asset_id: str
    service_id: str
    protocol: ProtocolValue
    destination_ports: tuple[tuple[int, int], ...]
    examined_edge_ids: tuple[str, ...]
    examined_rule_ids: tuple[str, ...]
    rule_edge_associations: int
    resource_ceilings: ResourceLimits


@dataclass(frozen=True, slots=True)
class MatchingDomain:
    edge_ids: tuple[str, ...]
    destination_ports: tuple[tuple[int, int], ...]


@dataclass(frozen=True, slots=True)
class ScopedDuplicateEffect:
    effect: str
    rule_ids: tuple[str, ...]
    matching_domain: MatchingDomain
    kind: Literal["scoped_duplicate_effect"] = "scoped_duplicate_effect"


@dataclass(frozen=True, slots=True)
class AllowDenyOverlap:
    edge_id: str
    source_asset_id: str
    destination_asset_id: str
    protocol: ProtocolValue
    start: int
    end: int
    allow_rule_ids: tuple[str, ...]
    deny_rule_ids: tuple[str, ...]
    effective_decision: Literal["explicit_deny"] = "explicit_deny"


@dataclass(frozen=True, slots=True)
class PolicyEvidenceWork:
    edge_atom_evaluations: int
    edge_rule_atom_checks: int
    planned_edge_atom_evaluations: int
    planned_edge_rule_atom_checks: int


@dataclass(frozen=True, slots=True)
class PolicyEvidence:
    scope: PolicyScope
    scoped_duplicate_effects: tuple[ScopedDuplicateEffect, ...]
    allow_deny_overlaps: tuple[AllowDenyOverlap, ...]
    no_match_in_scope_rule_ids: tuple[str, ...]
    work: PolicyEvidenceWork
    status: Literal["complete"] = "complete"
    limitation: str = (
        "All findings share this exact endpoint/protocol/port and declared-edge scope, including "
        "edges outside the chosen witness. Duplicate means identical nonempty matching effects "
        "inside this scope only. No-match is not globally unused. No rule removal, end-to-end "
        "redundancy, ordered shadowing, optimization or safe remediation is established."
    )


def policy_evidence_for_query(engine: ReachabilityEngine, query: QueryResult) -> PolicyEvidence:
    """Reuse compiled predicates for a completed query on the caller's run-local engine.

    Prospective combined budgets include conservative reserved query work plus this
    complete diagnostic expansion. Actual additional work is returned separately.
    Signatures group matching spans, avoiding pairwise comparisons between rules.
    """
    service = engine.services.get(query.service_id)
    if (
        service is None
        or query.service_id not in engine.requested
        or query.source_asset_id not in engine.graph.origins
        or not engine.graph.origins[query.source_asset_id]
        or query.source_asset_id == service.asset_id
        or query.destination_asset_id != service.asset_id
        or query.protocol != service.protocol
        or tuple((i.start, i.end) for i in query.intervals)
        != tuple((a.start, a.end) for a in engine.service_atoms[service.id])
    ):
        fail(
            "SCOPE_MISMATCH",
            "$.policy_evidence",
            "Evidence requires an exact supported query scope.",
        )
    atoms = engine.service_atoms[service.id]
    planned_rows = len(atoms) * len(engine.graph.edges)
    planned_checks = len(atoms) * engine.associations
    check_limit(
        "state_edge_visits",
        max(
            engine.queries_reserved * 3 * (len(engine.graph.adjacency) + len(engine.graph.edges)),
            engine.work.state_edge_visits,
        )
        + planned_rows,
        engine.limits.state_edge_visits,
    )
    check_limit(
        "edge_rule_atom_checks",
        max(engine.queries_reserved * engine.associations, engine.work.edge_rule_atom_checks)
        + planned_checks,
        engine.limits.edge_rule_atom_checks,
    )
    work = engine.work
    initial_rows, initial_checks = work.state_edge_visits, work.edge_rule_atom_checks
    edges = tuple(sorted(engine.graph.edges))
    # A rule has the same endpoint/protocol/port predicate on every associated
    # edge. Factor edges x ports instead of storing association/atom products.
    first_edge = {r.id: min(r.edge_ids) for r in engine.model.rules}
    signatures: dict[str, list[tuple[int, int]]] = {}
    overlaps: list[AllowDenyOverlap] = []
    for edge_id in edges:
        for atom in atoms:
            work.visit()
            decision = decide(
                engine.policy.get(edge_id, ()),
                query.source_asset_id,
                service.asset_id,
                service.protocol,
                atom.start,
                work,
            )
            for identity in (*decision.allow_rule_ids, *decision.deny_rule_ids):
                if first_edge[identity] != edge_id:
                    continue
                spans = signatures.setdefault(identity, [])
                if spans and spans[-1][1] + 1 == atom.start:
                    spans[-1] = (spans[-1][0], atom.end)
                else:
                    spans.append((atom.start, atom.end))
            if decision.allow_rule_ids and decision.deny_rule_ids:
                overlaps.append(
                    AllowDenyOverlap(
                        edge_id,
                        query.source_asset_id,
                        service.asset_id,
                        service.protocol,
                        atom.start,
                        atom.end,
                        decision.allow_rule_ids,
                        decision.deny_rule_ids,
                    )
                )
    groups: dict[tuple[str, tuple[str, ...], tuple[tuple[int, int], ...]], list[str]] = {}
    for rule in sorted(engine.model.rules, key=lambda r: r.id):
        if rule.id in signatures:
            groups.setdefault(
                (rule.effect, tuple(sorted(rule.edge_ids)), tuple(signatures[rule.id])), []
            ).append(rule.id)
    duplicates = tuple(
        ScopedDuplicateEffect(effect, tuple(identities), MatchingDomain(edge_ids, spans))
        for (effect, edge_ids, spans), identities in sorted(groups.items())
        if len(identities) > 1
    )
    return PolicyEvidence(
        PolicyScope(
            query.source_asset_id,
            service.asset_id,
            service.id,
            service.protocol,
            tuple((p.start, p.end) for p in service.destination_ports),
            edges,
            tuple(sorted(r.id for r in engine.model.rules)),
            engine.associations,
            engine.limits,
        ),
        duplicates,
        tuple(overlaps),
        tuple(sorted(r.id for r in engine.model.rules if r.id not in signatures)),
        PolicyEvidenceWork(
            work.state_edge_visits - initial_rows,
            work.edge_rule_atom_checks - initial_checks,
            planned_rows,
            planned_checks,
        ),
    )
