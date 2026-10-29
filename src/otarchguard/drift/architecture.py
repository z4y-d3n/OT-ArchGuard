"""Declared-model deltas and exact, explicitly selected native assessment pairs.

Matching native IDs identifies declarations, never deployed devices. The caller
supplies models obtained from the fully validated historical lifecycle image.
"""

import json
import re
from dataclasses import asdict, replace
from typing import Any

from otarchguard import NATIVE_ENGINE_VERSION
from otarchguard.api import ValidatedArchitecture
from otarchguard.comparison import declaration_catalogs, declaration_fields
from otarchguard.contract import ID_PATTERN, RESOURCE_LIMITS
from otarchguard.diagnostics import fail
from otarchguard.domain import Record
from otarchguard.drift.contract import Budget, Side, finding, source
from otarchguard.evidence.attachments import canonical
from otarchguard.reachability import IntervalResult, ReachabilityEngine

_DECLARATION_LIMITATIONS = [
    "Equal native IDs align declarations only; physical asset continuity is unverified.",
    "Declared changes do not establish a deployed infrastructure change.",
]
_NATIVE_LIMITATIONS = [
    "Native results describe declared initiation reachability, not real-world enforcement.",
    "Missing or unsupported results do not establish blocked communication.",
    "No packet observation, application success or physical identity is inferred.",
]


def _queries(queries: list[dict[str, str]], budget: Budget) -> list[tuple[str, str]]:
    if type(queries) is not list:
        fail("DRIFT_QUERY", "$", "Native queries must be an explicit list.")
    # Bound rejected inputs before building a duplicate-detection set.
    budget.charge("work_units", len(queries))
    if len(queries) > budget.limits.native_queries:
        budget.charge("native_queries", len(queries))
    result: list[tuple[str, str]] = []
    for query in queries:
        if (
            type(query) is not dict
            or set(query) != {"source_asset_id", "service_id"}
            or any(
                type(v) is not str or re.fullmatch(ID_PATTERN, v) is None for v in query.values()
            )
        ):
            fail(
                "DRIFT_QUERY",
                "$",
                "Use exact native source_asset_id and service_id fields for each query.",
            )
        result.append((query["source_asset_id"], query["service_id"]))
    if len(set(result)) != len(result):
        fail("DRIFT_QUERY", "$", "Native query pairs must be unique.")
    return sorted(result)


def _evidence(
    model: ValidatedArchitecture | None, source: dict[str, Any], **data: Any
) -> dict[str, Any]:
    return {"source": source, "model_sha256": model.sha256 if model else None, **data}


def _value(record: Record) -> dict[str, Any]:
    return record.model_dump(mode="json", exclude_none=True)


def _equivalent_query(
    reference: ValidatedArchitecture, candidate: ValidatedArchitecture, source: str, service: str
) -> str | None:
    if reference.model.suc.id != candidate.model.suc.id:
        return "Different declared SUC identities do not establish an equivalent native scope."
    assets = [{a.id: a for a in model.model.assets} for model in (reference, candidate)]
    services = [{s.id: s for s in model.model.services} for model in (reference, candidate)]
    if any(source not in values for values in assets) or any(
        service not in values for values in services
    ):
        return "The exact source asset or destination service is unavailable on one side."
    left_service, right_service = services[0][service], services[1][service]
    if left_service != right_service:
        return "The destination service definitions differ; equivalent query semantics are unknown."
    if source == left_service.asset_id:
        return "Self-asset queries are outside the native evaluator's supported scope."
    destination = left_service.asset_id
    if any(
        assets[0][identity].kind != assets[1][identity].kind
        or assets[0][identity].zone_id != assets[1][identity].zone_id
        or assets[0][identity].scope != assets[1][identity].scope
        for identity in (source, destination)
    ):
        return "The declared origin or destination asset scope/placement/kind differs."
    interfaces = [
        tuple(i for i in model.model.interfaces if i.asset_id in {source, destination})
        for model in (reference, candidate)
    ]
    if not any(i.asset_id == source for i in interfaces[0]):
        return "The selected source has no declared origin interface."
    if interfaces[0] != interfaces[1]:
        return "Origin/destination interface semantics differ; equivalent endpoints are unknown."
    return None


def compare_models(
    reference: ValidatedArchitecture | None,
    candidate: ValidatedArchitecture | None,
    reference_source: dict[str, Any],
    candidate_source: dict[str, Any],
    queries: list[dict[str, str]],
    budget: Budget,
) -> list[dict[str, Any]]:
    """Compare validated native records and bounded equivalent native queries.

    Queries contain exactly ``source_asset_id`` and ``service_id``. Results are
    model-relative and use a common exact port partition from the native engine.
    Partial or unsupported native scope yields explicit indeterminate evidence.
    """
    pairs = _queries(queries, budget)
    result: list[dict[str, Any]] = []

    def emit(
        category: str,
        subtype: str,
        key: object,
        left: object,
        right: object,
        state: str,
        explanation: str,
        limitations: list[str],
    ) -> None:
        budget.charge("references", int(left is not None) + int(right is not None))
        result.append(
            finding(category, subtype, key, left, right, state, explanation, budget, limitations)
        )

    if reference is None or candidate is None:
        emit(
            "INDETERMINATE_COMPARISON",
            "MODEL_UNAVAILABLE",
            {"domain": "declared_architecture"},
            _evidence(reference, reference_source),
            _evidence(candidate, candidate_source),
            "INDETERMINATE",
            "Both exact validated native models are required for architecture comparison.",
            _DECLARATION_LIMITATIONS,
        )
        return result

    catalogs = (declaration_catalogs(reference), declaration_catalogs(candidate))
    for kind in sorted(catalogs[0]):
        left_records, right_records = catalogs[0][kind], catalogs[1][kind]
        identities = left_records.keys() | right_records.keys()
        budget.charge("keys", len(identities))
        budget.charge("work_units", len(identities))
        for identity in sorted(identities):
            left_record, right_record = left_records.get(identity), right_records.get(identity)
            key = {"entity_kind": kind, "id": identity}
            if left_record is None or right_record is None:
                emit(
                    "DECLARED_ARCHITECTURE_CHANGE",
                    "DECLARED_OBJECT_ADDED" if left_record is None else "DECLARED_OBJECT_REMOVED",
                    key,
                    _evidence(reference, reference_source, declaration=_value(left_record))
                    if left_record is not None
                    else None,
                    _evidence(candidate, candidate_source, declaration=_value(right_record))
                    if right_record is not None
                    else None,
                    "COMPARABLE",
                    "This exact declaration ID occurs in only one selected native model.",
                    _DECLARATION_LIMITATIONS,
                )
                continue
            fields = declaration_fields(left_record, right_record, kind)
            if fields:
                budget.charge("work_units", len(fields))
                emit(
                    "DECLARED_ARCHITECTURE_CHANGE",
                    "DECLARED_OBJECT_CHANGED",
                    key,
                    _evidence(
                        reference,
                        reference_source,
                        fields={f.field: f.baseline for f in fields},
                    ),
                    _evidence(
                        candidate,
                        candidate_source,
                        fields={f.field: f.proposed for f in fields},
                        field_classifications={f.field: f.classification for f in fields},
                    ),
                    "COMPARABLE",
                    "Supported canonical native fields differ for this exact declaration ID.",
                    _DECLARATION_LIMITATIONS,
                )

    # Nested SUC collections already have their own canonical-ID catalogs.
    suc_fields = tuple(
        f
        for f in declaration_fields(reference.model.suc, candidate.model.suc, "suc")
        if f.field not in {"access_points", "external_dependencies"}
    )
    top_fields = [
        name
        for name in ("architecture_id", "revision")
        if getattr(reference.model, name) != getattr(candidate.model, name)
    ]
    for kind, left_values, right_values, classifications in (
        (
            "suc",
            {f.field: f.baseline for f in suc_fields},
            {f.field: f.proposed for f in suc_fields},
            {f.field: f.classification for f in suc_fields},
        ),
        (
            "snapshot",
            {name: getattr(reference.model, name) for name in top_fields},
            {name: getattr(candidate.model, name) for name in top_fields},
            {name: "metadata" for name in top_fields},
        ),
    ):
        if left_values:
            budget.charge("work_units", len(left_values))
            emit(
                "DECLARED_ARCHITECTURE_CHANGE",
                "DECLARED_OBJECT_CHANGED",
                {"entity_kind": kind},
                _evidence(reference, reference_source, fields=left_values),
                _evidence(
                    candidate,
                    candidate_source,
                    fields=right_values,
                    field_classifications=classifications,
                ),
                "COMPARABLE",
                "Validated native declaration fields differ; YAML presentation is ignored.",
                _DECLARATION_LIMITATIONS,
            )

    eligible: list[tuple[str, str]] = []
    for source_id, service_id in pairs:
        budget.charge(
            "work_units",
            sum(
                len(model.model.assets) + len(model.model.services) + len(model.model.interfaces)
                for model in (reference, candidate)
            ),
        )
        reason = _equivalent_query(reference, candidate, source_id, service_id)
        if reason is None:
            eligible.append((source_id, service_id))
        else:
            emit(
                "INDETERMINATE_COMPARISON",
                "NATIVE_QUERY_NOT_EQUIVALENT",
                {"source_asset_id": source_id, "service_id": service_id},
                _evidence(reference, reference_source),
                _evidence(candidate, candidate_source),
                "INDETERMINATE",
                reason,
                _NATIVE_LIMITATIONS,
            )
    if not eligible:
        return result

    budget.charge("native_queries", 2 * len(eligible))
    remaining = budget.limits.work_units - budget.used.get("work_units", 0)
    # Both complete native runs must fit the remaining comparison work budget.
    native_limits = replace(
        RESOURCE_LIMITS,
        state_edge_visits=min(RESOURCE_LIMITS.state_edge_visits, remaining // 4),
        edge_rule_atom_checks=min(RESOURCE_LIMITS.edge_rule_atom_checks, remaining // 4),
    )
    requested = frozenset(service for _, service in eligible)
    engines = (
        ReachabilityEngine(reference, requested, native_limits, partition_peers=(candidate.model,)),
        ReachabilityEngine(candidate, requested, native_limits, partition_peers=(reference.model,)),
    )
    for engine in engines:
        engine.ensure_capacity(sum(len(engine.service_atoms[service]) for _, service in eligible))

    def reserve(interval: IntervalResult) -> None:
        # Reject before dataclass expansion retains potentially large paths. The
        # charge is conservative accounted space, not measured output or RSS.
        charge = 1024
        references = 1
        if interval.witness is not None:
            charge += sum(4096 + 128 * len(s.allow_rule_ids) for s in interval.witness.steps)
            references += len(interval.witness.steps)
        if interval.diagnostics is not None:
            charge += sum(
                1024 + 128 * (len(e.allow_rule_ids) + len(e.deny_rule_ids))
                for e in interval.diagnostics.blocked_edges
            )
            references += len(interval.diagnostics.blocked_edges)
        budget.charge("report_bytes", charge)
        budget.charge("references", references)

    previous_work = [0, 0]
    for source_id, service_id in eligible:
        outcomes = []
        for index, engine in enumerate(engines):
            outcome = engine.evaluate(source_id, service_id, interval_observer=reserve)
            total = engine.work.state_edge_visits + engine.work.edge_rule_atom_checks
            budget.charge("work_units", total - previous_work[index])
            previous_work[index] = total
            outcomes.append(outcome)
        signatures = [
            [(i.start, i.end, i.reachable) for i in outcome.intervals] for outcome in outcomes
        ]
        emit(
            "NATIVE_ASSESSMENT_DIFFERENCE",
            "REACHABILITY_CHANGED" if signatures[0] != signatures[1] else "REACHABILITY_UNCHANGED",
            {"source_asset_id": source_id, "service_id": service_id},
            _evidence(
                reference,
                reference_source,
                native_engine_version=NATIVE_ENGINE_VERSION,
                native_result=json.loads(canonical(asdict(outcomes[0]))),
            ),
            _evidence(
                candidate,
                candidate_source,
                native_engine_version=NATIVE_ENGINE_VERSION,
                native_result=json.loads(canonical(asdict(outcomes[1]))),
            ),
            "COMPARABLE",
            "Exact equivalent declared queries were evaluated by the unchanged native engine "
            "over a common port partition; results describe these models only.",
            _NATIVE_LIMITATIONS,
        )
    return result


def compare_native_evidence(
    reference: Side, candidate: Side, budget: Budget
) -> list[dict[str, Any]]:
    """Compare validated capture reconciliation within its frozen narrow scope.

    Exact original comparison attachments retain native query/witness support.
    Only independently reviewed equivalent endpoint declarations under one exact
    model are paired here. Different models require explicit ``compare_models``
    query selection; unsupported packet metadata never becomes native denial.
    """
    components = [side.attachments.get("comparison") for side in (reference, candidate)]
    if not any(components):
        return []
    results: list[dict[str, Any]] = []

    def emit(
        subtype: str,
        key: object,
        left: object,
        right: object,
        state: str,
        explanation: str,
    ) -> None:
        budget.charge("references", int(left is not None) + int(right is not None))
        results.append(
            finding(
                "NATIVE_ASSESSMENT_DIFFERENCE"
                if state == "COMPARABLE"
                else "INDETERMINATE_COMPARISON",
                subtype,
                key,
                left,
                right,
                state,
                explanation,
                budget,
                _NATIVE_LIMITATIONS,
            )
        )

    if not all(components):
        emit(
            "NATIVE_RECONCILIATION_UNAVAILABLE",
            {"domain": "capture_native_assessment"},
            source(reference),
            source(candidate),
            "INDETERMINATE",
            "Both exact validated native reconciliation attachments are required.",
        )
        return results
    first_component, second_component = components
    assert first_component is not None and second_component is not None
    if first_component["payload"]["model_sha256"] != second_component["payload"]["model_sha256"]:
        emit(
            "NATIVE_RECONCILIATION_MODEL_CHANGED",
            {"domain": "capture_native_assessment"},
            source(reference),
            source(candidate),
            "INDETERMINATE",
            "Native reconciliation inputs select different models; explicit equivalent declared "
            "queries are required before comparing their model-relative reachability.",
        )
        return results

    indexes: list[dict[bytes, dict[str, Any]]] = []
    associations: list[dict[str, dict[str, Any]]] = []
    for side, component in zip((reference, candidate), components, strict=True):
        assert component is not None
        budget.charge("work_units", len(side.snapshot["observations"]["flows"]))
        flows = {flow["id"]: flow for flow in side.snapshot["observations"]["flows"]}
        indexed: dict[bytes, dict[str, Any]] = {}
        for assessment in component["payload"]["findings"]:
            budget.charge("work_units")
            flow = flows[assessment["flow_id"]]
            if flow["ip_version"] != 4 or flow["transport"] != "tcp" or flow["status"] != "decoded":
                continue
            key = {
                name: flow[name]
                for name in (
                    "ip_version",
                    "source_ip",
                    "destination_ip",
                    "transport",
                    "source_port",
                    "destination_port",
                    "vlans",
                )
            }
            encoded = canonical(key)
            if encoded not in indexed:
                budget.charge("keys")
                indexed[encoded] = {"key": key, "assessments": []}
            indexed[encoded]["assessments"].append(assessment)
        indexes.append(indexed)
        budget.charge("work_units", len(component["payload"]["association_decisions"]))
        associations.append(
            {
                p["observed_ip"]: p
                for p in component["payload"]["association_decisions"]
                if p["decision"] == "ACCEPT"
            }
        )

    def retained(side: Side, group: dict[str, Any] | None) -> dict[str, Any] | None:
        if group is None:
            return None
        records = group["assessments"]
        budget.charge("work_units", len(records))
        budget.charge("references", min(8, len(records)))
        native = [r["native_result"] for r in records if r["native_result"] is not None]
        summaries = []
        for value in native[:8]:
            query, interval = value["query"], value["selected_interval"]
            summaries.append(
                {
                    "engine_version": value["engine_version"],
                    "query": {
                        name: query[name]
                        for name in (
                            "source_asset_id",
                            "destination_asset_id",
                            "service_id",
                            "protocol",
                        )
                    },
                    "observed_destination_port": value["observed_destination_port"],
                    "interval": {name: interval[name] for name in ("start", "end", "reachable")},
                }
            )
        return {
            "source": source(side),
            "flow_references": [
                {"flow_id": r["flow_id"], "conversation_id": r["conversation_id"]}
                for r in records[:8]
            ],
            "flow_references_omitted": max(0, len(records) - 8),
            "native_assessments": summaries,
            "native_assessments_omitted": max(0, len(native) - 8),
            "support": "Exact comparison attachment and flow ID retain the replayed native "
            "query/witness.",
        }

    for encoded in sorted(indexes[0].keys() | indexes[1].keys()):
        budget.charge("work_units")
        groups = [index.get(encoded) for index in indexes]
        if not any(
            group and any(r["native_result"] is not None for r in group["assessments"])
            for group in groups
        ):
            continue
        key = next(group["key"] for group in groups if group is not None)
        support = [
            retained(side, group)
            for side, group in zip((reference, candidate), groups, strict=True)
        ]
        reason = None
        signatures = []
        for group in groups:
            if group is None or any(r["native_result"] is None for r in group["assessments"]):
                reason = (
                    "A supported native assessment is unavailable for this relationship "
                    "on one side."
                )
                break
            budget.charge("work_units", len(group["assessments"]))
            signatures.append(
                {
                    canonical(
                        {
                            "query": {
                                name: r["native_result"]["query"][name]
                                for name in (
                                    "source_asset_id",
                                    "destination_asset_id",
                                    "service_id",
                                    "protocol",
                                )
                            },
                            "port": r["native_result"]["observed_destination_port"],
                            "result": {
                                name: r["native_result"]["selected_interval"][name]
                                for name in ("start", "end", "reachable")
                            },
                        }
                    )
                    for r in group["assessments"]
                }
            )
        if reason is None:
            for endpoint in ("source_ip", "destination_ip"):
                choices = [mapping.get(key[endpoint]) for mapping in associations]
                if not all(choices) or any(
                    choices[0][name] != choices[1][name]  # type: ignore[index]
                    for name in ("selected_asset_id", "selected_interface_id")
                ):
                    reason = (
                        "Independent ACCEPTed endpoint associations do not establish equivalent "
                        "model-relative queries."
                    )
                    break
                budget.charge("references", 2)
        if reason is None and (len(signatures[0]) != 1 or signatures[0] != signatures[1]):
            reason = "Exact equivalent native query/outcome evidence is unavailable or ambiguous."
        emit(
            "NATIVE_RECONCILIATION_UNPAIRED" if reason else "RECONCILIATION_ASSESSMENT_UNCHANGED",
            key,
            support[0],
            support[1],
            "INDETERMINATE" if reason else "COMPARABLE",
            reason
            or "Independently reviewed directional IPv4 TCP SYN assessments agree under "
            "the same exact model and query; this does not establish physical device continuity.",
        )
    return results
