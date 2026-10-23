"""Finite summaries and conservative change interpretation from completed evidence only."""

from dataclasses import dataclass

from otarchguard.api import ValidatedArchitecture
from otarchguard.comparison import ComparisonResult
from otarchguard.diagnostics import fail
from otarchguard.domain import ProtocolValue
from otarchguard.exposure import ExposureResult, QueryScope
from otarchguard.flows import observations


@dataclass(frozen=True, slots=True)
class PairCoverage:
    source_asset_id: str
    service_id: str
    destination_asset_id: str
    protocol: ProtocolValue
    evaluated_ports: tuple[tuple[int, int], ...]
    exact_interval_records: int
    reachable_interval_records: int
    unreachable_interval_records: int


@dataclass(frozen=True, slots=True)
class CommunicationTuple:
    source_asset_id: str
    destination_asset_id: str
    service_id: str
    protocol: ProtocolValue
    source_owner_zone_id: str
    destination_owner_zone_id: str
    reachable_ports: tuple[tuple[int, int], ...]


@dataclass(frozen=True, slots=True)
class FiniteScopeSummary:
    snapshot_sha256: str
    query_scope: QueryScope
    evaluated_query_pairs: int
    evaluated_exact_interval_records: int
    reachable_exact_interval_records: int
    unreachable_exact_interval_records: int
    evaluated_destination_ports_across_pairs: int
    reachable_destination_ports_across_pairs: int
    distinct_reachable_destination_asset_ids: tuple[str, ...]
    pair_coverage: tuple[PairCoverage, ...]
    reachable_communication_tuples: tuple[CommunicationTuple, ...]
    cross_owner_zone_tuples: tuple[CommunicationTuple, ...]
    unavailable_origin_asset_ids: tuple[str, ...]
    unavailable_service_ids: tuple[str, ...]
    noncomparable_service_ids: tuple[str, ...]
    excluded_self_asset_pairs: tuple[tuple[str, str], ...]
    unevaluated_present_query_pairs: int
    outside_scope_pair_count: None = None
    limitation: str = (
        "Counts apply only to completed scenario queries, not additional intent queries. "
        "Port counts sum individual destination ports across source/service pairs. Owner zones "
        "are administrative asset declarations, distinct from interface placement. Unavailable, "
        "noncomparable and excluded entities are not unreachable. All pairs outside this finite "
        "scope, unmodeled access and operational behavior remain unassessed. Intent outcomes "
        "must be reviewed independently; no security or risk score is computed."
    )


def summarize_exposure(
    validated: ValidatedArchitecture,
    result: ExposureResult,
    *,
    noncomparable_service_ids: tuple[str, ...] = (),
) -> FiniteScopeSummary:
    """Aggregate the result's concrete queries without any search or policy evaluation."""
    if validated.sha256 != result.snapshot_sha256:
        fail("SCOPE_MISMATCH", "$.summary", "Summary snapshot must match completed query evidence.")
    assets = {a.id: a for a in validated.model.assets}
    services = {s.id: s for s in validated.model.services}
    pairs = tuple(sorted(result.queries, key=lambda q: (q.source_asset_id, q.service_id)))
    if len({(q.source_asset_id, q.service_id) for q in pairs}) != len(pairs):
        fail("DUPLICATE_ITEM", "$.summary", "Completed query pairs must be distinct.")
    coverage = tuple(
        PairCoverage(
            q.source_asset_id,
            q.service_id,
            q.destination_asset_id,
            q.protocol,
            tuple((i.start, i.end) for i in q.intervals),
            len(q.intervals),
            sum(i.reachable for i in q.intervals),
            sum(not i.reachable for i in q.intervals),
        )
        for q in pairs
    )
    reachable = observations(result.queries)
    ports: dict[tuple[str, str, str, ProtocolValue], list[tuple[int, int]]] = {}
    for flow in reachable:
        identity = (flow.source_asset_id, flow.destination_asset_id, flow.service_id, flow.protocol)
        ports.setdefault(identity, []).append((flow.start, flow.end))
    tuples = tuple(
        CommunicationTuple(
            *identity, assets[identity[0]].zone_id, assets[identity[1]].zone_id, tuple(intervals)
        )
        for identity, intervals in sorted(ports.items())
    )
    origins = set(result.query_scope.origin_asset_ids)
    excluded = tuple(
        sorted(
            (services[s].asset_id, s)
            for s in result.query_scope.destination_service_ids
            if services[s].asset_id in origins
        )
    )
    return FiniteScopeSummary(
        result.snapshot_sha256,
        result.query_scope,
        len(pairs),
        sum(len(q.intervals) for q in pairs),
        sum(i.reachable for q in pairs for i in q.intervals),
        sum(not i.reachable for q in pairs for i in q.intervals),
        sum(i.end - i.start + 1 for q in pairs for i in q.intervals),
        sum(i.end - i.start + 1 for q in pairs for i in q.intervals if i.reachable),
        tuple(sorted({q.destination_asset_id for q in tuples})),
        coverage,
        tuples,
        tuple(t for t in tuples if t.source_owner_zone_id != t.destination_owner_zone_id),
        result.unavailable_origin_asset_ids,
        result.unavailable_destination_service_ids,
        tuple(sorted(noncomparable_service_ids)),
        excluded,
        len(origins) * len(result.query_scope.destination_service_ids) - len(excluded) - len(pairs),
    )


@dataclass(frozen=True, slots=True)
class DeclarationChangeReference:
    entity_kind: str
    entity_id: str
    change: str
    fields: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ObservedChangeExplanation:
    declaration_changes: tuple[DeclarationChangeReference, ...]
    newly_reachable_interval_records: int
    no_longer_reachable_interval_records: int
    source_service_tuples_gaining_ports: int
    source_service_tuples_losing_ports: int
    newly_reachable_source_service_pairs: int
    no_longer_reachable_source_service_pairs: int
    newly_reachable_destination_assets: int
    no_longer_reachable_destination_assets: int
    noncomparable_service_ids: tuple[str, ...]
    interpretation: str = (
        "Observed communication changes occur alongside these declaration changes; no unique "
        "causal attribution is established. Newly reachable tuples may access an already "
        "reachable asset. Exact intervals, independent required/prohibited intent findings, "
        "service definition changes and unavailable entities remain separate evidence. No "
        "counterfactual, cut-edge, minimal remediation, global redundancy, deployed connectivity "
        "or reduced-risk conclusion is established."
    )


def explain_comparison(result: ComparisonResult) -> ObservedChangeExplanation:
    """Reference existing classified diffs and outcomes; no new causal analysis."""
    references = [
        DeclarationChangeReference(change.entity_kind, identity, verb, ())
        for change in result.inventory_changes
        for verb, identities in (("added", change.added_ids), ("removed", change.removed_ids))
        for identity in identities
    ]
    references.extend(
        DeclarationChangeReference(
            c.entity_kind, c.id, "modified", tuple(f.field for f in c.fields)
        )
        for c in result.entity_changes
    )
    if result.suc_definition_changes:
        references.append(
            DeclarationChangeReference(
                "suc",
                result.suc_id,
                "definition_changed",
                tuple(c.field for c in result.suc_definition_changes),
            )
        )
    return ObservedChangeExplanation(
        tuple(sorted(references, key=lambda r: (r.entity_kind, r.entity_id, r.change))),
        len(result.newly_reachable),
        len(result.no_longer_reachable),
        len({(f.source_asset_id, f.service_id) for f in result.newly_reachable}),
        len({(f.source_asset_id, f.service_id) for f in result.no_longer_reachable}),
        len(
            {(f.source_asset_id, f.service_id) for f in result.newly_reachable}
            - {(f.source_asset_id, f.service_id) for f in result.baseline.observations}
        ),
        len(
            {(f.source_asset_id, f.service_id) for f in result.no_longer_reachable}
            - {(f.source_asset_id, f.service_id) for f in result.proposed.observations}
        ),
        len(result.newly_reachable_assets),
        len(result.no_longer_reachable_assets),
        result.noncomparable_service_ids,
    )
