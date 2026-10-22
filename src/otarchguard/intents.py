"""Independent quantified intent evaluation; embedded exposure scenarios are not run."""

from dataclasses import dataclass
from pathlib import Path

from otarchguard.api import ValidatedArchitecture, validate_bytes, validate_file
from otarchguard.contract import RESOURCE_LIMITS, ResourceLimits
from otarchguard.reachability import QueryResult, ReachabilityEngine
from otarchguard.validation import expand_selector


@dataclass(frozen=True, slots=True)
class IntentResult:
    id: str
    kind: str
    passed: bool
    queries: tuple[QueryResult, ...]


@dataclass(frozen=True, slots=True)
class CheckResult:
    snapshot_sha256: str
    passed: bool
    intents: tuple[IntentResult, ...]
    failed_intent_count: int
    failed_interval_count: int
    atom_queries: int
    state_edge_visits: int
    edge_rule_atom_checks: int
    scope: str = "Declared initiation reachability; not sessions, compromise, risk or compliance."


def check_architecture(
    validated: ValidatedArchitecture,
    limits: ResourceLimits = RESOURCE_LIMITS,
) -> CheckResult:
    model = validated.model
    requested = frozenset(s for intent in model.intents for s in intent.destination_service_ids)
    engine = ReachabilityEngine(validated, requested, limits)
    return check_intents(engine)


def intent_query_count(engine: ReachabilityEngine) -> int:
    model = engine.model
    assets, zones = {a.id: a for a in model.assets}, {z.id: z for z in model.zones}
    return sum(
        (len(origins) - int(engine.services[s].asset_id in origins)) * len(engine.service_atoms[s])
        for intent in model.intents
        for origins in (expand_selector(intent.source, assets, zones),)
        for s in intent.destination_service_ids
    )


def check_intents(engine: ReachabilityEngine) -> CheckResult:
    """Evaluate intents using the caller's run-local engine and remaining shared budget."""
    model, validated = engine.model, engine.validated
    initial = (
        engine.queries_reserved,
        engine.work.state_edge_visits,
        engine.work.edge_rule_atom_checks,
    )
    assets, zones = {a.id: a for a in model.assets}, {z.id: z for z in model.zones}
    sources = {intent.id: expand_selector(intent.source, assets, zones) for intent in model.intents}
    # Conservative sum counts repeats across intents, before creating any pair product.
    engine.ensure_capacity(engine.queries_reserved + intent_query_count(engine))
    cache: dict[tuple[str, str], QueryResult] = {}
    outcomes: list[IntentResult] = []
    failed_intervals = 0
    for intent in sorted(model.intents, key=lambda i: i.id):
        results: list[QueryResult] = []
        passed = True
        for source in sources[intent.id]:
            for service_id in sorted(intent.destination_service_ids):
                if source == engine.services[service_id].asset_id:
                    continue
                key = (source, service_id)
                if key not in cache:
                    cache[key] = engine.evaluate(*key)
                result = cache[key]
                results.append(result)
                failures = sum(
                    interval.reachable != (intent.kind == "required")
                    for interval in result.intervals
                )
                failed_intervals += failures
                passed = passed and failures == 0
        outcomes.append(IntentResult(intent.id, intent.kind, passed, tuple(results)))
    failed = sum(not item.passed for item in outcomes)
    return CheckResult(
        validated.sha256,
        failed == 0,
        tuple(outcomes),
        failed,
        failed_intervals,
        engine.queries_reserved - initial[0],
        engine.work.state_edge_visits - initial[1],
        engine.work.edge_rule_atom_checks - initial[2],
    )


def check_file(path: Path, limits: ResourceLimits = RESOURCE_LIMITS) -> CheckResult:
    return check_architecture(validate_file(path, limits), limits)


def check_bytes(data: bytes, limits: ResourceLimits = RESOURCE_LIMITS) -> CheckResult:
    return check_architecture(validate_bytes(data, limits), limits)
