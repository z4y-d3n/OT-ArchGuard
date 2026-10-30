"""Human review, explicit partitions and native-validated multi-source emission."""

import html
import json
import re
from collections import Counter
from pathlib import Path
from typing import cast

from otarchguard.api import validate_bytes
from otarchguard.diagnostics import check_limit, fail
from otarchguard.ingestion.project import (
    PROJECT_LIMITS,
    check_project_envelope,
    create_project,
    project_digest,
)
from otarchguard.ingestion.project_records import (
    ConflictDecision,
    EntityDecision,
    EvidenceAcknowledgment,
    ProjectDecisions,
    ProjectDraft,
)
from otarchguard.ingestion.reconciliation import Candidate, catalog, observed
from otarchguard.ingestion.records import EntityKind, StructuredCandidate
from otarchguard.ingestion.tabular import IMPORT_LIMITS, digest
from otarchguard.ingestion.workflow import (
    _COLLECTIONS,
    _allowed,
    _declaration_yaml,
    _field_problems,
    serialize,
)
from otarchguard.loading import YamlValue


def connector_sets(draft: ProjectDraft) -> dict[str, tuple[str, ...]]:
    return {
        source.id: tuple(
            sorted(
                [
                    source.id + "::edge::" + digest([e.scope_id, e.element_id])
                    for e in source.evidence.graph.edges
                ]
                if source.evidence.graph
                else [
                    source.id + "::document::" + o.observation_id
                    for o in source.evidence.document.observations
                ]
                if source.evidence.document
                else [
                    source.id + "::" + c.candidate_id
                    for c in source.evidence.candidates
                    if c.entity == "connection"
                ]
            )
        )
        for source in draft.sources
    }


def project_template(draft: ProjectDraft) -> ProjectDecisions:
    return ProjectDecisions(
        project_decisions_version=1,
        draft_sha256=project_digest(draft),
        entities=tuple(
            EntityDecision(
                members=(key,),
                decision="UNRESOLVED",
                canonical_id=observed(c).get("id", ""),
            )
            for key, (_, c) in catalog(draft.sources).items()
            if c.entity != "connection"
        ),
        conflicts=tuple(ConflictDecision(group_id=g.group_id) for g in draft.conflicts),
    )


def acknowledge_connectors(
    draft: ProjectDraft,
    owner: ProjectDecisions,
    source_id: str,
    reviewer: str,
    rationale: str,
) -> ProjectDecisions:
    if owner.draft_sha256 != project_digest(draft):
        fail("PROJECT_STALE_REVIEW", "$", "Connector acknowledgment requires this exact draft.")
    members = connector_sets(draft).get(source_id)
    if not members or not reviewer.strip() or not rationale.strip():
        fail(
            "PROJECT_ACK",
            "$",
            "Select a nonempty documentary source, reviewer and rationale.",
        )
    if owner.reviewer and owner.reviewer != reviewer:
        fail("PROJECT_REVIEWER", "$", "Keep the same named reviewer within a decision document.")
    ack = EvidenceAcknowledgment(
        source_id=source_id,
        members=members,
        set_sha256=digest(members),
        rationale=rationale,
    )
    updated = owner.model_copy(
        update={
            "reviewer": reviewer,
            "acknowledgments": tuple(
                sorted(
                    (*[a for a in owner.acknowledgments if a.source_id != source_id], ack),
                    key=lambda a: a.source_id,
                )
            ),
            # Updating this evidence action must never set model_confirmed or accept an entity.
        }
    )
    check_project_envelope(updated, PROJECT_LIMITS.draft_bytes)
    return updated


def resolve_entity(
    draft: ProjectDraft,
    owner: ProjectDecisions,
    decision: EntityDecision,
    reviewer: str,
) -> ProjectDecisions:
    """Replace exact selected partitions; never split a prior identity decision implicitly."""
    if owner.draft_sha256 != project_digest(draft):
        fail("PROJECT_STALE_REVIEW", "$", "Resolution requires the exact current draft.")
    if not reviewer.strip() or not decision.rationale.strip() or decision.decision == "UNRESOLVED":
        fail("PROJECT_REVIEW", "$", "Select a decision, named reviewer and rationale.")
    if owner.reviewer and owner.reviewer != reviewer:
        fail("PROJECT_REVIEWER", "$", "Keep the same reviewer within one decision document.")
    candidates = catalog(draft.sources)
    selected = set(decision.members)
    if len(selected) != len(decision.members) or not selected <= candidates.keys():
        fail("PROJECT_IDENTITY", "$", "Select distinct existing qualified candidates.")
    kinds = {candidates[k][1].entity for k in selected}
    if len(kinds) != 1 or "connection" in kinds:
        fail("PROJECT_IDENTITY", "$", "Select one non-connector entity family.")
    retained = []
    for previous in owner.entities:
        overlap = selected & set(previous.members)
        if overlap and not set(previous.members) <= selected:
            fail("PROJECT_IDENTITY", "$", "Explicitly replace the entire previous partition.")
        if not overlap:
            retained.append(previous)
    updated = owner.model_copy(
        update={
            "reviewer": reviewer,
            "model_confirmed": False,
            "entities": tuple(
                sorted((*retained, decision), key=lambda d: tuple(sorted(d.members)))
            ),
        }
    )
    check_project_envelope(updated, PROJECT_LIMITS.draft_bytes)
    return updated


def project_summary(
    draft: ProjectDraft, owner: ProjectDecisions | None = None
) -> dict[str, object]:
    candidates = catalog(draft.sources)
    counts = Counter(c.entity for _, c in candidates.values())
    missing = [key for key, (_, c) in candidates.items() if c.ambiguities]
    graphs = [s.evidence.graph for s in draft.sources if s.evidence.graph]
    return {
        "project_id": draft.manifest.project_id,
        "project_draft_version": 1,
        "draft_sha256": project_digest(draft),
        "sources": len(draft.sources),
        "entities": dict(sorted(counts.items())),
        "graphical_nodes": sum(len(g.nodes) for g in graphs),
        "graphical_connectors": sum(len(g.edges) for g in graphs),
        "documentary_observations": sum(
            len(s.evidence.document.observations) for s in draft.sources if s.evidence.document
        ),
        "document_summaries": {
            s.id: s.evidence.document.summary for s in draft.sources if s.evidence.document
        },
        "potential_duplicate_groups": len(draft.proposals),
        "blocking_conflicts": len(draft.conflicts),
        "candidates_requiring_correction": len(missing),
        "candidates_ready_for_review": len(candidates) - len(missing),
        "owner_confirmed_declarations": sum(d.decision == "OWNER_CONFIRMED" for d in owner.entities)
        if owner
        else 0,
        "evidence_only_relationships": sum(len(v) for v in connector_sets(draft).values()),
        "diagnostics": sum(len(s.evidence.diagnostics) for s in draft.sources),
        "accounting": draft.accounting,
        "scope": "Documentation coverage and review state; deployed completeness unverified.",
    }


def _safe(value: object) -> str:
    text = str(value).replace("\r", " ").replace("\n", " ")
    text = re.sub(r"([\\`*_{}\[\]()#+.!|~-])", r"\\\1", text)
    # Escape Markdown first. Escaping the generated entity's '#' would display
    # the entity literally; quotes need no HTML escaping in a text context.
    return html.escape(text, quote=False)


def _markdown_field(label: str, value: object, indent: int = 0) -> list[str]:
    """Retain every location/diagnostic field as safely escaped Markdown text."""
    prefix = " " * indent + "- " + _safe(label) + ":"
    if isinstance(value, dict):
        return (
            [prefix]
            + [
                line
                for key, item in value.items()
                for line in _markdown_field(str(key), item, indent + 2)
            ]
            if value
            else [prefix + " No fields recorded"]
        )
    if isinstance(value, (list, tuple)):
        return (
            [prefix]
            + [
                line
                for index, item in enumerate(value, 1)
                for line in _markdown_field(str(index), item, indent + 2)
            ]
            if value
            else [prefix + " None recorded"]
        )
    return [prefix + " " + ("Not recorded" if value is None else _safe(value))]


def review_markdown(draft: ProjectDraft, group_id: str | None = None) -> bytes:
    candidates = catalog(draft.sources)
    lines = [
        "# Import project review",
        "",
        _safe(draft.manifest.project_id),
        "",
        "Evidence and proposed identity are unconfirmed. Each final declaration needs a named "
        "owner decision. Matching labels and addresses do not establish physical identity.",
        "",
    ]
    for key, value in project_summary(draft).items():
        if key not in {"scope", "accounting"}:
            lines.extend(_markdown_field(key, value))
    groups = (*draft.conflicts, *draft.proposals)
    if group_id:
        groups = tuple(g for g in groups if g.group_id == group_id)
        if not groups:
            fail("PROJECT_GROUP", "$", "Unknown proposed match or conflict group.")
    lines += ["", "## Blocking conflicts and matching proposals", ""]
    for group in groups:
        lines += [
            "### " + _safe(group.code) + " — " + _safe(group.group_id),
            "",
            _safe(group.explanation),
            "",
            "Claim: " + _safe(group.field) + " = " + _safe(group.value),
            "",
            "Differing attributes: " + _safe(", ".join(group.differences) or "none"),
            "",
        ]
        for key in group.members:
            source_id, candidate = candidates[key]
            location = (
                candidate.location.model_dump()
                if isinstance(candidate, StructuredCandidate)
                else {
                    "row": candidate.row_id,
                }
            )
            lines.append("- " + _safe(key) + " (" + _safe(source_id) + ")")
            lines.extend(_markdown_field("Source location", location, 2))
        lines += [
            "",
            "Action: put same-entity members in one decision, or retain separate decisions "
            "with distinct final IDs. Resolve differing fields by field_sources/corrections; "
            "record a rationale for each blocking conflict.",
            "",
        ]
    if not group_id:
        lines += ["## Missing or invalid native fields", ""]
        for key, (_, candidate) in candidates.items():
            if candidate.ambiguities:
                lines.append("- " + _safe(key) + ": " + _safe("; ".join(candidate.ambiguities)))
        lines += ["", "## Source diagnostics", ""]
        for source in draft.sources:
            for diagnostic in source.evidence.diagnostics:
                lines.extend(_markdown_field(source.id, diagnostic.model_dump()))
        lines += ["", "## Preferred evidence suggestions", ""]
        for field, preferred_source in sorted(draft.manifest.preferred_sources.items()):
            lines.append(
                "- "
                + _safe(field)
                + ": "
                + _safe(preferred_source)
                + "; confirmation still required."
            )
        lines += ["", "## Evidence-only documentary sets", ""]
        for connector_source, members in connector_sets(draft).items():
            if members:
                lines.append(
                    f"- {_safe(connector_source)}: {len(members)} documentary records; "
                    f"SHA-256 {digest(members)}"
                )
        lines += [
            "",
            "Use project acknowledge with an exact source ID to retain its connectors "
            "as evidence-only. The new decision file discloses every selected identity. "
            "This grants no transport, forwarding, routing, policy or model confirmation.",
            "",
        ]
    return ("\n".join(lines) + "\n").encode()


def _values(decision: EntityDecision, members: dict[str, Candidate]) -> dict[str, str]:
    kind = next(iter(members.values())).entity
    allowed = _allowed(kind)
    controls = set(decision.field_sources) | set(decision.corrections) | set(decision.references)
    if not controls <= allowed - {"id"} or (
        set(decision.field_sources) & set(decision.corrections)
        or set(decision.references) & (set(decision.corrections) | set(decision.field_sources))
    ):
        fail("PROJECT_FIELDS", "$", "Use distinct supported non-ID field controls.")
    values = {"id": decision.canonical_id}
    observations = {key: observed(c) for key, c in members.items()}
    fields = {f for v in observations.values() for f in v} - {"id"}
    for field in sorted(fields | controls):
        if field in decision.corrections:
            values[field] = decision.corrections[field]
        elif field in decision.references:
            continue  # Explicit reviewed target is resolved after the complete partition exists.
        elif field in decision.field_sources:
            selected = decision.field_sources[field]
            if selected not in observations or field not in observations[selected]:
                fail(
                    "PROJECT_FIELDS",
                    "$",
                    "Field source must be usable evidence within this entity.",
                )
            values[field] = observations[selected][field]
        else:
            alternatives = {v[field] for v in observations.values() if field in v}
            if len(alternatives) > 1:
                fail(
                    "PROJECT_FIELD_CONFLICT", "$", "Select or correct each contradictory attribute."
                )
            if alternatives:
                values[field] = next(iter(alternatives))
    for candidate in members.values():
        if isinstance(candidate, StructuredCandidate):
            for field in candidate.required_corrections:
                if field in decision.corrections or field in decision.references:
                    continue
                selected_other = decision.field_sources.get(field)
                other = members.get(selected_other or "")
                if (
                    not isinstance(other, StructuredCandidate)
                    or field in other.required_corrections
                ):
                    # A legacy tabular field can also be selected explicitly and validated natively.
                    if other is None or isinstance(other, StructuredCandidate):
                        fail(
                            "PROJECT_CORRECTION",
                            "$",
                            "Invalid fields require correction or valid selected evidence.",
                        )
    for value in values.values():
        check_limit("project_field_characters", len(value), IMPORT_LIMITS.field_characters)
    return values


def _verify_acknowledgments(draft: ProjectDraft, owner: ProjectDecisions) -> None:
    sets = {k: v for k, v in connector_sets(draft).items() if v}
    acks = {a.source_id: a for a in owner.acknowledgments}
    if len(acks) != len(owner.acknowledgments) or set(acks) != set(sets):
        fail("PROJECT_ACK", "$", "Acknowledge every nonempty connector source exactly once.")
    for source, members in sets.items():
        ack = acks[source]
        if ack.members != members or ack.set_sha256 != digest(members) or not ack.rationale.strip():
            fail(
                "PROJECT_ACK", "$", "Connector acknowledgment does not bind the exact bounded set."
            )


def emit_project(
    draft: ProjectDraft,
    owner: ProjectDecisions,
    manifest_path: Path,
) -> dict[str, bytes]:
    """Reopen/reparse every input, reproduce the draft, then validate before any write."""
    reproduced = create_project(manifest_path)
    if serialize(reproduced) != serialize(draft):
        fail(
            "PROJECT_SOURCE_CHANGED", "$", "Project inputs or draft changed; map and review again."
        )
    return reviewed_project_artifacts(draft, owner)


def reviewed_project_artifacts(draft: ProjectDraft, owner: ProjectDecisions) -> dict[str, bytes]:
    """Revalidate retained review evidence without reopening original documents.

    This proves internal consistency, not document authenticity. Emission still
    reproduces original inputs above; offline consumers can verify a saved sidecar.
    """
    if owner.draft_sha256 != project_digest(draft):
        fail("PROJECT_STALE_REVIEW", "$", "Owner decisions must bind this exact project draft.")
    if not owner.model_confirmed or not owner.reviewer.strip() or not owner.model_rationale.strip():
        fail("PROJECT_REVIEW", "$", "Named owner, model confirmation and rationale required.")
    check_project_envelope(owner, PROJECT_LIMITS.draft_bytes)
    check_limit("project_decisions", len(owner.entities), PROJECT_LIMITS.decisions)
    _verify_acknowledgments(draft, owner)
    conflicts = {c.group_id: c for c in owner.conflicts}
    if len(conflicts) != len(owner.conflicts) or set(conflicts) != {
        c.group_id for c in draft.conflicts
    }:
        fail("PROJECT_CONFLICT", "$", "Exactly one resolution is required per blocking conflict.")
    if any(not c.resolved or not c.rationale.strip() for c in conflicts.values()):
        fail("PROJECT_CONFLICT", "$", "Resolve and explain every blocking conflict.")
    candidates = {k: c for k, (_, c) in catalog(draft.sources).items() if c.entity != "connection"}
    partition: dict[str, EntityDecision] = {}
    accepted: dict[str, dict[str, str]] = {}
    groups: list[tuple[EntityDecision, dict[str, str], EntityKind]] = []
    seen_ids: set[tuple[str, str]] = set()
    for decision in sorted(owner.entities, key=lambda d: tuple(sorted(d.members))):
        if decision.decision == "UNRESOLVED" or not decision.rationale.strip():
            fail(
                "PROJECT_UNRESOLVED",
                "$",
                "Each entity partition needs an explicit decision and rationale.",
            )
        if not set(decision.members) <= candidates.keys() or len(set(decision.members)) != len(
            decision.members
        ):
            fail(
                "PROJECT_IDENTITY",
                "$",
                "Entity members must be distinct existing entity candidates.",
            )
        members = {key: candidates[key] for key in sorted(decision.members)}
        kinds = {c.entity for c in members.values()}
        if len(kinds) != 1 or set(members) & partition.keys():
            fail(
                "PROJECT_IDENTITY", "$", "Partitions must be disjoint and share one entity family."
            )
        partition.update(dict.fromkeys(members, decision))
        kind = next(iter(kinds))
        if decision.decision != "OWNER_CONFIRMED":
            if decision.field_sources or decision.corrections or decision.references:
                fail(
                    "PROJECT_FIELDS", "$", "Only confirmed declarations may select/correct fields."
                )
            continue
        identity = kind, decision.canonical_id
        if identity in seen_ids:
            fail(
                "PROJECT_IDENTITY", "$", "Separate clusters cannot claim the same final native ID."
            )
        seen_ids.add(identity)
        values = _values(decision, members)
        for key in members:
            accepted[key] = values
        groups.append((decision, values, kind))
    if set(partition) != set(candidates):
        fail(
            "PROJECT_UNRESOLVED", "$", "Every non-connector candidate must occur in one partition."
        )
    reference_kinds = {
        ("asset", "zone_id"): "zone",
        ("interface", "asset_id"): "asset",
        ("interface", "placement_zone_id"): "zone",
    }
    for decision, values, kind in groups:
        for field, target in decision.references.items():
            if target not in accepted or candidates[target].entity != reference_kinds.get(
                (kind, field)
            ):
                fail(
                    "PROJECT_REFERENCE",
                    "$",
                    "Reviewed reference requires an accepted target of the correct family.",
                )
            values[field] = accepted[target]["id"]
        for key in decision.members:
            candidate = candidates[key]
            if isinstance(candidate, StructuredCandidate):
                for reference in candidate.references:
                    field = reference.field
                    if field in decision.corrections or field in decision.references:
                        continue
                    if field in decision.field_sources and decision.field_sources[field] != key:
                        continue
                    source_id = key.split("::", 1)[0]
                    target_values = accepted.get(
                        source_id + "::" + (reference.target_candidate_id or "")
                    )
                    if target_values is None or values.get(field) != target_values["id"]:
                        fail(
                            "PROJECT_REFERENCE",
                            "$",
                            "Source target unresolved/rejected/renamed; resolve its reference.",
                        )
        if _field_problems(candidates[decision.members[0]].entity, values):
            fail(
                "PROJECT_FIELDS",
                "$",
                "Confirmed entity still has missing or invalid native fields.",
            )
    model = dict(draft.context)
    for entity_kind, collection in sorted(_COLLECTIONS.items()):
        items = [values for _, values, k in groups if k == entity_kind]
        existing = model.get(collection, [])
        if not isinstance(existing, list):
            fail("PROJECT_CONTEXT", "$", "Native context collections must be sequences.")
        imported = cast(list[YamlValue], sorted(items, key=lambda v: v["id"]))
        model[collection] = existing + imported
    validated = validate_bytes(_declaration_yaml(model))
    data = _declaration_yaml(json.loads(validated.canonical_json))
    if validate_bytes(data).sha256 != validated.sha256:
        fail("PROJECT_INTERNAL", "$", "Published model identity differs from native validation.")
    records = []
    for key, (source, candidate) in catalog(draft.sources).items():
        records.append(
            {
                "candidate_entity_id": key,
                "source_id": source,
                "observation_id": source + "::" + candidate.row_id,
                "proposed_canonical_identity": observed(candidate).get("id"),
                "model_id": accepted[key]["id"] if key in accepted else None,
                "review_status": partition[key].decision if key in partition else "EVIDENCE_ONLY",
            }
        )
    # Keep each original observation once, including contradictory/rejected alternatives.
    decisions_payload = owner.model_dump(mode="json")
    decisions_payload["entities"] = sorted(
        [{**d.model_dump(mode="json"), "members": sorted(d.members)} for d in owner.entities],
        key=lambda d: d["members"],
    )
    decisions_payload["conflicts"] = sorted(
        decisions_payload["conflicts"], key=lambda d: d["group_id"]
    )
    decisions_payload["acknowledgments"] = sorted(
        decisions_payload["acknowledgments"], key=lambda d: d["source_id"]
    )
    sidecar: dict[str, object] = {
        "project_provenance_version": 1,
        "draft_sha256": project_digest(draft),
        "model_sha256": validated.sha256,
        "catalog": draft.model_dump(mode="json"),
        "decisions": decisions_payload,
        "identity_index": records,
        "declarations": [
            {"members": sorted(d.members), "model_collection": _COLLECTIONS[k], "fields": v}
            for d, v, k in groups
        ],
        "scope": "Owner-declared architecture; evidence is not deployed-network verification.",
    }
    check_project_envelope(sidecar, PROJECT_LIMITS.sidecar_bytes)
    return {"architecture.yaml": data, "architecture.provenance.json": serialize(sidecar)}
