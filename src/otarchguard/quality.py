"""Read-only, requirement-backed assessment of declarations and verified evidence."""

import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import AfterValidator, Field, ValidationError, field_validator

from otarchguard.api import ValidatedArchitecture
from otarchguard.comparison import declaration_catalogs, declaration_field_names
from otarchguard.diagnostics import check_limit, fail
from otarchguard.domain import Id, Record
from otarchguard.explorer_data import ProjectProvenance, check_text, load_model, load_provenance
from otarchguard.ingestion.json_inventory import parse_json
from otarchguard.ingestion.project import _no_links
from otarchguard.ingestion.reconciliation import catalog
from otarchguard.ingestion.structured import StructuredLimits
from otarchguard.ingestion.tabular import digest, read_regular
from otarchguard.trace import trace_architecture

type EntityKind = Literal[
    "assets",
    "zones",
    "interfaces",
    "conduits",
    "transport_edges",
    "forwarding_edges",
    "services",
    "rules",
    "intents",
    "scenarios",
    "access_points",
    "external_dependencies",
]
type State = Literal[
    "SATISFIED",
    "MISSING_REQUIRED_INFORMATION",
    "CONTRADICTORY_EVIDENCE",
    "REVIEW_REQUIRED",
    "NOT_DOCUMENTED",
    "NOT_ASSESSED",
    "NOT_APPLICABLE",
    "UNSUPPORTED",
]


def _sha(value: str) -> str:
    if re.fullmatch(r"[a-f0-9]{64}", value) is None:
        raise ValueError("SHA-256 required")
    return value


type Sha = Annotated[str, AfterValidator(_sha)]


class ReviewControl(Record):
    @field_validator("profile_version", "mapping_version", check_fields=False, mode="before")
    @classmethod
    def integer_version(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("Integer version required")
        return value


class ReviewQuery(ReviewControl):
    source_asset_id: Id
    service_id: Id


class Requirement(ReviewControl):
    id: Id
    expectation: Literal[
        "DECLARED_VALUE",
        "FIELD_PROVENANCE",
        "ENTITY_PROVENANCE",
        "SOURCE_AVAILABLE",
        "OWNER_INFORMATION",
    ]
    entity_kind: EntityKind = "assets"
    entity_ids: tuple[str, ...] = Field(default=("*",), min_length=1, max_length=2000)
    field: Id | None = None
    expected_value: str | None = Field(default=None, max_length=4096)
    rationale: str = Field(min_length=1, max_length=4096)


class OwnerInformation(ReviewControl):
    entity_kind: EntityKind
    entity_id: Id
    field: Id
    value: str = Field(min_length=1, max_length=4096)
    reviewer: str = Field(min_length=1, max_length=256)
    rationale: str = Field(min_length=1, max_length=4096)


class QualityProfile(ReviewControl):
    profile_version: Literal[1]
    model_sha256: Sha
    context: str = Field(min_length=1, max_length=256)
    requirements: tuple[Requirement, ...] = Field(default=(), max_length=1000)
    information: tuple[OwnerInformation, ...] = Field(default=(), max_length=2000)
    queries: tuple[ReviewQuery, ...] = Field(default=(), max_length=16)


def load_control[T: ReviewControl](path: Path, record: type[T]) -> T:
    """Strict JSON only, bounded before parsing, no links or source instructions."""
    _no_links(path)
    value = parse_json(
        read_regular(path, 2 * 1024 * 1024),
        StructuredLimits(
            source_bytes=2 * 1024 * 1024, depth=16, records=10000, scalars=100000, text=4096
        ),
    )
    try:
        result = record.model_validate(value)
    except (ValidationError, ValueError):
        fail("QUALITY_CONTROL", "$", "Invalid versioned assessment/comparison control.")
    check_strings(result.model_dump(mode="json"))
    return result


def check_strings(value: object) -> None:
    if isinstance(value, str):
        check_text(value)
    elif isinstance(value, (list, tuple)):
        for child in value:
            check_strings(child)
    elif isinstance(value, dict):
        for key, child in value.items():
            check_strings(key)
            check_strings(child)


def canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=True, indent=2) + "\n").encode()


def evidence_identity(sidecar: ProjectProvenance | None) -> str | None:
    return digest(sidecar.model_dump(mode="json")) if sidecar else None


def evidence_support(sidecar: ProjectProvenance | None) -> dict[tuple[str, str, str], list[object]]:
    """Only owner-selected fields without literal correction count as source support."""
    support: dict[tuple[str, str, str], list[object]] = {}
    if sidecar is None:
        return support
    candidates = catalog(sidecar.catalog.sources)
    kinds = {"asset": "assets", "zone": "zones", "interface": "interfaces"}
    for decision in sidecar.decisions.entities:
        if decision.decision != "OWNER_CONFIRMED":
            continue
        for field, key in decision.field_sources.items():
            if field in decision.corrections or field in decision.references:
                continue
            source, candidate = candidates[key]
            observed = next(f for f in candidate.fields if f.field == field)
            if observed.location is None or observed.transformation == "profile_constant":
                continue
            reference = {
                "source_id": source,
                "candidate_id": key,
                "field": field,
                "location": observed.model_dump(mode="json"),
            }
            support.setdefault((kinds[candidate.entity], decision.canonical_id, field), []).append(
                reference
            )
        # A single-member partition can have implicit unambiguous field selections.
        if len(decision.members) == 1:
            key = decision.members[0]
            source, candidate = candidates[key]
            for observed in candidate.fields:
                field = observed.field
                target = (kinds[candidate.entity], decision.canonical_id, field)
                if (
                    target in support
                    or field in decision.corrections
                    or field in decision.references
                ):
                    continue
                if (
                    observed.state not in {"UNRESOLVED", "UNSUPPORTED"}
                    and observed.normalized_value
                    and observed.location is not None
                    and observed.transformation != "profile_constant"
                ):
                    support[target] = [
                        {
                            "source_id": source,
                            "candidate_id": key,
                            "field": field,
                            "location": observed.model_dump(mode="json"),
                        }
                    ]
    return support


def _assess(
    model_path: Path,
    provenance_path: Path | None,
    profile_path: Path | None,
    queries: tuple[ReviewQuery, ...] = (),
) -> dict[str, Any]:
    model = load_model(model_path)
    p = load_provenance(provenance_path, model) if provenance_path else None
    profile = load_control(profile_path, QualityProfile) if profile_path else None
    return _assess_snapshot(model, p, profile, queries)


def _assess_snapshot(
    model: ValidatedArchitecture,
    p: ProjectProvenance | None,
    profile: QualityProfile | None,
    queries: tuple[ReviewQuery, ...] = (),
) -> dict[str, Any]:
    """Internal reuse after every native/provenance input has been verified."""
    check_limit("quality_queries", len(queries), 16)
    if profile and profile.model_sha256 != model.sha256:
        fail("QUALITY_IDENTITY", "$", "Profile does not bind this model.")
    if profile and not profile.context.strip():
        fail("QUALITY_PROFILE", "$", "A nonblank assessment context is required.")
    catalogs = declaration_catalogs(model)
    provenance_id = evidence_identity(p)
    support = evidence_support(p)
    by_entity: dict[tuple[str, str], list[object]] = {}
    for (kind, identity, _field), references in support.items():
        by_entity.setdefault((kind, identity), []).extend(references)
    finding_bytes = 0
    findings: list[dict[str, object]] = []
    coverage: list[dict[str, object]] = []

    def finding(
        rule: str,
        domain: str,
        entity: object,
        state: State,
        expected: object,
        actual: object,
        explanation: str,
        refs: list[object] | None = None,
        requirement: str | None = None,
    ) -> None:
        nonlocal finding_bytes
        check_limit("quality_findings", len(findings) + 1, 24000)
        findings.append(
            {
                "finding_id": "finding-" + digest([rule, 1, entity, requirement]),
                "rule_id": rule,
                "rule_version": 1,
                "domain": domain,
                "entity": entity,
                "scope": {"entity": entity, "requirement_id": requirement},
                "model_sha256": model.sha256,
                "provenance_sha256": provenance_id,
                "state": state,
                "expected": expected,
                "actual": actual,
                "explanation": explanation,
                "requirement_id": requirement,
                "priority": "owner_review"
                if state in {"MISSING_REQUIRED_INFORMATION", "REVIEW_REQUIRED"}
                else "information",
                "owner_action": "Review the explicit requirement and supply or revise information."
                if state == "MISSING_REQUIRED_INFORMATION"
                else None,
                "limitations": [
                    "Assessment of declarations/evidence; no deployed-network or "
                    "security-score claim."
                ],
                "source_references": refs or [],
            }
        )

        finding_bytes += len(canonical(findings[-1]))
        check_limit("quality_finding_bytes", finding_bytes, 24 * 1024 * 1024)

    finding(
        "native-validation",
        "STRUCTURAL",
        "model",
        "SATISFIED",
        "Valid schema 1",
        "Validated",
        "The existing native validator accepted this immutable snapshot.",
    )
    finding(
        "provenance-availability",
        "DOCUMENTARY",
        "model",
        "SATISFIED" if p else "NOT_ASSESSED",
        "Optional verified provenance",
        "Verified project-1" if p else "Not supplied",
        "Model-only operation is supported. Missing provenance establishes no vulnerability.",
    )
    if not profile:
        finding(
            "requirements-scope",
            "REQUIREMENT_BACKED",
            "model",
            "NOT_ASSESSED",
            "Explicit owner profile",
            "No profile supplied",
            "No completeness denominator or security score is invented.",
        )
    if p:
        for source in p.catalog.sources:
            if source.evidence.diagnostics:
                finding(
                    "document-interpretation",
                    "DOCUMENTARY",
                    source.id,
                    "REVIEW_REQUIRED",
                    "Supported selected subset",
                    [d.model_dump(mode="json") for d in source.evidence.diagnostics],
                    "Retained diagnostics describe exclusions/limitations, not a "
                    "complete document interpretation.",
                )
        resolutions = {d.group_id: d for d in p.decisions.conflicts}
        for conflict in p.catalog.conflicts:
            resolution = resolutions[conflict.group_id]
            finding(
                "retained-conflict",
                "RECONCILIATION",
                conflict.group_id,
                "SATISFIED" if resolution.resolved else "REVIEW_REQUIRED",
                "Explicit owner resolution",
                {
                    "conflict": conflict.model_dump(mode="json"),
                    "decision": resolution.model_dump(mode="json"),
                },
                "Contradictory observations remain retained; a valid final "
                "resolution is not an unresolved model error.",
                [{"candidate_id": m} for m in conflict.members],
            )
        for decision in p.decisions.entities:
            if decision.decision in {"OWNER_REJECTED", "EVIDENCE_ONLY"}:
                finding(
                    "retained-alternative",
                    "RECONCILIATION",
                    sorted(decision.members),
                    "SATISFIED",
                    "Traceable final owner decision",
                    decision.model_dump(mode="json"),
                    "Rejected/evidence-only alternatives grant no native declaration "
                    "or network permission.",
                    [{"candidate_id": m} for m in decision.members],
                )
    if profile:
        reqids = [r.id for r in profile.requirements]
        if len(set(reqids)) != len(reqids):
            fail("QUALITY_PROFILE", "$", "Requirement IDs must be distinct.")
        info: dict[tuple[str, str, str], OwnerInformation] = {}
        for item in profile.information:
            key = (item.entity_kind, item.entity_id, item.field)
            if key in info or item.entity_id not in catalogs[item.entity_kind]:
                fail(
                    "QUALITY_PROFILE",
                    "$",
                    "Owner information must uniquely select existing entities.",
                )
            if not all(s.strip() for s in (item.value, item.reviewer, item.rationale)):
                fail(
                    "QUALITY_PROFILE", "$", "Owner information needs value, reviewer and rationale."
                )
            info[key] = item
        for req in sorted(profile.requirements, key=lambda r: r.id):
            if not req.rationale.strip() or len(set(req.entity_ids)) != len(req.entity_ids):
                fail(
                    "QUALITY_PROFILE", "$", "Requirements need a rationale and distinct selectors."
                )
            entities = catalogs[req.entity_kind]
            ids = (
                tuple(sorted(entities))
                if req.entity_ids == ("*",)
                else tuple(sorted(req.entity_ids))
            )
            if req.expectation == "SOURCE_AVAILABLE":
                if "*" in ids or req.field is not None or req.expected_value is not None:
                    fail(
                        "QUALITY_PROFILE",
                        "$",
                        "Source requirements select explicit source IDs only.",
                    )
            else:
                if not set(ids) <= entities.keys():
                    fail("QUALITY_PROFILE", "$", "Requirement selects an unknown native entity.")
                if req.expectation in {"DECLARED_VALUE", "FIELD_PROVENANCE", "OWNER_INFORMATION"}:
                    if req.field is None:
                        fail("QUALITY_PROFILE", "$", "This requirement needs an explicit field.")
                elif req.field is not None:
                    fail("QUALITY_PROFILE", "$", "Entity provenance does not select a field.")
                if req.field and req.expectation != "OWNER_INFORMATION":
                    if req.field not in declaration_field_names(req.entity_kind) or any(
                        req.field not in type(entities[i]).model_fields for i in ids
                    ):
                        fail(
                            "QUALITY_PROFILE",
                            "$",
                            "Unsupported native field; use external owner information.",
                        )
                if req.expected_value is not None and req.expectation not in {
                    "DECLARED_VALUE",
                    "OWNER_INFORMATION",
                }:
                    fail(
                        "QUALITY_PROFILE",
                        "$",
                        "Expected values apply only to declared/owner information.",
                    )
            passed = 0
            for identity in ids:
                refs: list[object] = []
                if req.expectation == "SOURCE_AVAILABLE":
                    available = (
                        {s.id: s.evidence.source.sha256 for s in p.catalog.sources} if p else {}
                    )
                    actual: object = available.get(identity)
                    satisfied = identity in available
                elif req.expectation == "OWNER_INFORMATION":
                    note = info.get((req.entity_kind, identity, req.field or ""))
                    actual = note.model_dump(mode="json") if note else None
                    satisfied = bool(
                        note and (req.expected_value is None or note.value == req.expected_value)
                    )
                elif req.expectation == "DECLARED_VALUE":
                    actual = entities[identity].model_dump(mode="json").get(req.field or "")
                    satisfied = actual is not None and actual not in (
                        "",
                        "unassessed",
                        "unspecified",
                    )
                    if req.expected_value is not None:
                        satisfied = actual == req.expected_value
                else:
                    refs = (
                        by_entity.get((req.entity_kind, identity), [])
                        if req.expectation == "ENTITY_PROVENANCE"
                        else support.get((req.entity_kind, identity, req.field or ""), [])
                    )
                    actual = {
                        "selected_source_references": len(refs),
                        "provenance_available": p is not None,
                    }
                    satisfied = bool(refs)
                passed += satisfied
                finding(
                    "requirement-" + req.expectation.lower(),
                    "REQUIREMENT_BACKED",
                    [
                        req.entity_kind if req.expectation != "SOURCE_AVAILABLE" else "sources",
                        identity,
                        req.field,
                    ],
                    "SATISFIED" if satisfied else "MISSING_REQUIRED_INFORMATION",
                    req.model_dump(mode="json", exclude={"entity_ids"}),
                    actual,
                    req.rationale,
                    refs,
                    req.id,
                )
            coverage.append(
                {
                    "requirement_id": req.id,
                    "scope": req.model_dump(mode="json"),
                    "satisfied": passed,
                    "required": len(ids),
                    "excluded": [],
                    "state": "ASSESSED" if ids else "NOT_APPLICABLE",
                    "meaning": "Requirement coverage, never a security score.",
                }
            )
        queries = (*queries, *profile.queries)
    normalized = sorted({(q.source_asset_id, q.service_id) for q in queries})
    check_limit("quality_queries", len(normalized), 16)
    analyses = []
    for source_id, service in normalized:
        result = trace_architecture(model, source_id, service)
        analyses.append(asdict(result))
        finding(
            "exact-query",
            "ANALYTICAL",
            [source_id, service],
            "SATISFIED",
            "Actual model-bound evaluation",
            {"model_sha256": result.model_sha256, "scope": asdict(result.scope)},
            "The exact query was evaluated. Completion does not imply every flow was permitted.",
        )
    if not analyses:
        finding(
            "exact-query",
            "ANALYTICAL",
            "model",
            "NOT_ASSESSED",
            "Explicit queries",
            "NOT_EVALUATED",
            "No analysis requested; no permission or denial is asserted.",
        )
    report: dict[str, object] = {
        "quality_version": 1,
        "rule_version": 1,
        "model_sha256": model.sha256,
        "provenance_sha256": provenance_id,
        "profile_sha256": digest(profile.model_dump(mode="json")) if profile else None,
        "scope": profile.model_dump(mode="json") if profile else None,
        "findings": sorted(findings, key=lambda f: str(f["finding_id"])),
        "coverage": coverage,
        "analyses": analyses,
        "supplied_sources": [s.id for s in p.catalog.sources] if p else [],
        "limitations": [
            "Only explicit profile requirements have denominators.",
            "No live infrastructure, physical completeness, or global segmentation assessment.",
        ],
    }
    report["assessment_sha256"] = digest(report)
    check_limit("quality_report_bytes", len(canonical(report)), 32 * 1024 * 1024)
    return report


def assess_quality(
    model: Path,
    *,
    provenance: Path | None = None,
    profile: Path | None = None,
    queries: tuple[ReviewQuery, ...] = (),
) -> dict[str, Any]:
    """Revalidate untrusted inputs; no arbitrary claimed analytical artifacts are accepted."""
    return _assess(model, provenance, profile, queries)
