"""Deterministic native/evidence differences plus explicitly evaluated exact traces."""

from dataclasses import asdict
from pathlib import Path
from typing import Any, Literal

from pydantic import Field

from otarchguard.comparison import declaration_catalogs, declaration_fields
from otarchguard.diagnostics import ModelError, check_limit, fail
from otarchguard.domain import Id
from otarchguard.explorer_data import ProjectProvenance, load_model, load_provenance
from otarchguard.ingestion.tabular import digest
from otarchguard.quality import (
    EntityKind,
    QualityProfile,
    ReviewControl,
    ReviewQuery,
    Sha,
    _assess_snapshot,
    canonical,
    evidence_identity,
    load_control,
)
from otarchguard.trace import TraceResult, trace_architecture


class Correspondence(ReviewControl):
    entity_kind: EntityKind
    baseline_id: Id
    proposed_id: Id
    rationale: str = Field(min_length=1, max_length=4096)


class ReusedIdentifier(ReviewControl):
    entity_kind: EntityKind
    id: Id
    rationale: str = Field(min_length=1, max_length=4096)


class IdentityMapping(ReviewControl):
    mapping_version: Literal[1]
    baseline_model_sha256: Sha
    proposed_model_sha256: Sha
    correspondences: tuple[Correspondence, ...] = Field(default=(), max_length=2000)
    reused_identifiers: tuple[ReusedIdentifier, ...] = Field(default=(), max_length=2000)


def _evidence(p: ProjectProvenance) -> dict[str, dict[str, Any]]:
    """Source-qualified native locators; document revisions and observations stay separate."""
    result: dict[str, dict[str, Any]] = {
        k: {}
        for k in (
            "sources",
            "candidates",
            "document_observations",
            "documentary_nodes",
            "documentary_connectors",
            "owner_decisions",
            "conflicts",
            "field_selections",
        )
    }
    for source in p.catalog.sources:
        result["sources"][source.id] = source.evidence.source.model_dump(mode="json")
        for c in source.evidence.candidates:
            result["candidates"][source.id + "::" + c.row_id] = c.model_dump(mode="json")
        if source.evidence.document:
            for observation in source.evidence.document.observations:
                value = observation.model_dump(mode="json")
                # Content IDs may change; the exact structural source locator is correspondence.
                key = source.id + "::" + digest([value["location"], value["category"]])
                result["document_observations"][key] = value
        if source.evidence.graph:
            for collection, values in (
                ("documentary_nodes", source.evidence.graph.nodes),
                ("documentary_connectors", source.evidence.graph.edges),
            ):
                for graph_record in values:
                    result[collection][
                        source.id + "::" + digest([graph_record.scope_id, graph_record.element_id])
                    ] = graph_record.model_dump(mode="json")
    for d in p.decisions.entities:
        key = digest(sorted(d.members))
        result["owner_decisions"][key] = d.model_dump(mode="json")
        result["field_selections"][key] = {
            "members": sorted(d.members),
            "canonical_id": d.canonical_id,
            "field_sources": d.field_sources,
            "corrections": d.corrections,
            "references": d.references,
            "decision": d.decision,
        }
    for resolution in p.decisions.conflicts:
        result["owner_decisions"][resolution.group_id] = resolution.model_dump(mode="json")
    for conflict in p.catalog.conflicts:
        result["conflicts"][conflict.group_id] = conflict.model_dump(mode="json")
    for ack in p.decisions.acknowledgments:
        result["owner_decisions"]["ack::" + ack.source_id] = ack.model_dump(mode="json")
    result["owner_decisions"]["model-review"] = {
        "reviewer": p.decisions.reviewer,
        "model_confirmed": p.decisions.model_confirmed,
        "model_rationale": p.decisions.model_rationale,
    }
    return result


def _analytical_delta(left: TraceResult, right: TraceResult) -> dict[str, Any]:
    if left.scope != right.scope:
        return {
            "classification": "NOT_COMPARABLE",
            "reason": "Exact service binding/query definition changed.",
            "intervals": [],
        }
    # Overlay only evaluated port intervals; never expand ports or invent queries.
    boundaries = sorted(
        {p for result in (left, right) for i in result.intervals for p in (i.start, i.end + 1)}
    )
    changes = []
    for start, stop in zip(boundaries, boundaries[1:], strict=False):
        a = next((i for i in left.intervals if i.start <= start <= i.end), None)
        b = next((i for i in right.intervals if i.start <= start <= i.end), None)
        if a is None or b is None:
            continue
        classification = "UNCHANGED_EVALUATED_RESULT"
        if not a.reachable and b.reachable:
            classification = "NEWLY_ALLOWED_FOR_EVALUATED_QUERY"
        elif a.reachable and not b.reachable:
            classification = "NO_LONGER_ALLOWED_FOR_EVALUATED_QUERY"
        elif (a.witness, a.diagnostics) != (b.witness, b.diagnostics):
            classification = "CHANGED_EXPLANATION"
        changes.append(
            {
                "start": start,
                "end": stop - 1,
                "protocol": a.protocol,
                "classification": classification,
                "baseline_reachable": a.reachable,
                "proposed_reachable": b.reachable,
                "reason": "Derived from both exact native trace intervals; witnesses and "
                "frontier diagnostics retained.",
            }
        )
    return {
        "classification": "EVALUATED",
        "intervals": changes,
        "reason": "Only the displayed source, destination, interface, protocol and "
        "port union were assessed.",
    }


def compare_architecture_versions(
    baseline: Path,
    proposed: Path,
    *,
    baseline_provenance: Path | None = None,
    proposed_provenance: Path | None = None,
    mapping: Path | None = None,
    baseline_profile: Path | None = None,
    proposed_profile: Path | None = None,
    queries: tuple[ReviewQuery, ...] = (),
) -> dict[str, Any]:
    left, right = load_model(baseline), load_model(proposed)
    lp = load_provenance(baseline_provenance, left) if baseline_provenance else None
    rp = load_provenance(proposed_provenance, right) if proposed_provenance else None
    owner = load_control(mapping, IdentityMapping) if mapping else None
    if owner and (owner.baseline_model_sha256, owner.proposed_model_sha256) != (
        left.sha256,
        right.sha256,
    ):
        fail(
            "COMPARISON_IDENTITY", "$", "Correspondence mapping does not bind both ordered models."
        )
    lc, rc = declaration_catalogs(left), declaration_catalogs(right)
    pairs: dict[str, dict[str, tuple[str, str]]] = {k: {} for k in lc}
    reused: set[tuple[str, str]] = set()
    if owner:
        for reuse in owner.reused_identifiers:
            reuse_key = (reuse.entity_kind, reuse.id)
            if (
                reuse_key in reused
                or reuse.id not in lc[reuse.entity_kind]
                or reuse.id not in rc[reuse.entity_kind]
                or not reuse.rationale.strip()
            ):
                fail(
                    "COMPARISON_MAPPING",
                    "$",
                    "Reused IDs must uniquely exist on both sides and need rationale.",
                )
            reused.add(reuse_key)
        for pair in owner.correspondences:
            kind: str = pair.entity_kind
            before, after = pair.baseline_id, pair.proposed_id
            existing = pairs[kind]
            if (
                before not in lc[kind]
                or after not in rc[kind]
                or before in existing
                or after in {v[0] for v in existing.values()}
                or not pair.rationale.strip()
                or (kind, before) in reused
                or (kind, after) in reused
            ):
                fail(
                    "COMPARISON_MAPPING",
                    "$",
                    "Mapping must be one-to-one, existing and reasoned; split/merge "
                    "remain unmatched.",
                )
            existing[before] = (after, pair.rationale)
    correspondences: list[dict[str, Any]] = []
    changes: list[dict[str, Any]] = []
    change_bytes = 0

    def change(
        layer: str,
        kind: str,
        key: object,
        before: object,
        after: object,
        *,
        fields: object = None,
        correspondence: object = None,
    ) -> None:
        nonlocal change_bytes
        if before == after:
            return
        check_limit("comparison_changes", len(changes) + 1, 24000)
        action = "ADDED" if before is None else "REMOVED" if after is None else "MODIFIED"
        changes.append(
            {
                "change_id": "change-" + digest([layer, kind, key, action, before, after]),
                "layer": layer,
                "entity_kind": kind,
                "entity": key,
                "action": action,
                "baseline": before,
                "proposed": after,
                "fields": fields,
                "correspondence": correspondence,
                "meaning": "Removed means removed from the proposed model/evidence, not from "
                "the physical plant.",
            }
        )

        change_bytes += len(canonical(changes[-1]))
        check_limit("comparison_change_bytes", change_bytes, 24 * 1024 * 1024)

    for kind in sorted(lc):
        old, new = lc[kind], rc[kind]
        selected = pairs[kind]
        explicit_destinations = {v[0] for v in selected.values()}
        for identity in sorted(old.keys() & new.keys()):
            if (kind, identity) in reused:
                continue
            if identity in selected or identity in explicit_destinations:
                # Swaps/cycles require explicit correspondence for all displaced common IDs.
                if identity not in selected or identity not in explicit_destinations:
                    fail(
                        "COMPARISON_MAPPING",
                        "$",
                        "Mapping displaces a stable ID; map both sides explicitly or mark "
                        "identifier reuse.",
                    )
                continue
            selected[identity] = (
                identity,
                "Equal canonical IDs; owner must declare any identifier reuse explicitly.",
            )
        for before, (after, rationale) in sorted(selected.items()):
            correspondence = {
                "entity_kind": kind,
                "baseline_id": before,
                "proposed_id": after,
                "policy": "explicit_owner_mapping"
                if owner
                and any(
                    p.entity_kind == kind and p.baseline_id == before for p in owner.correspondences
                )
                else "equal_canonical_id",
                "rationale": rationale,
            }
            correspondences.append(correspondence)
            change(
                "NATIVE",
                kind,
                [before, after],
                old[before].model_dump(mode="json"),
                new[after].model_dump(mode="json"),
                fields=[asdict(f) for f in declaration_fields(old[before], new[after], kind)],
                correspondence=correspondence,
            )
        for identity in sorted(old.keys() - selected.keys()):
            change("NATIVE", kind, [identity, None], old[identity].model_dump(mode="json"), None)
        targets = {v[0] for v in selected.values()}
        for identity in sorted(new.keys() - targets):
            change("NATIVE", kind, [None, identity], None, new[identity].model_dump(mode="json"))
    # Exact administrative ownership index; no physical placement or path inference.
    left_members: dict[str, list[str]] = {z: [] for z in lc["zones"]}
    right_members: dict[str, list[str]] = {z: [] for z in rc["zones"]}
    for asset in left.model.assets:
        left_members[asset.zone_id].append(asset.id)
    for asset in right.model.assets:
        right_members[asset.zone_id].append(asset.id)
    for zone in sorted(left_members.keys() | right_members.keys()):
        change(
            "NATIVE",
            "declared_zone_membership",
            zone,
            sorted(left_members[zone]) if zone in left_members else None,
            sorted(right_members[zone]) if zone in right_members else None,
            correspondence="Exact asset.zone_id index; not physical placement or permission.",
        )
    change(
        "NATIVE",
        "suc",
        "suc",
        left.model.suc.model_dump(mode="json"),
        right.model.suc.model_dump(mode="json"),
        fields=[asdict(f) for f in declaration_fields(left.model.suc, right.model.suc, "suc")],
    )
    change(
        "NATIVE",
        "snapshot",
        "snapshot",
        {k: getattr(left.model, k) for k in ("architecture_id", "revision")},
        {k: getattr(right.model, k) for k in ("architecture_id", "revision")},
    )
    if lp and rp:
        le, re = _evidence(lp), _evidence(rp)
        for kind in sorted(le):
            for key in sorted(le[kind].keys() | re[kind].keys()):
                change(
                    "OWNER_DECISION"
                    if kind in {"owner_decisions", "field_selections"}
                    else "DOCUMENTARY",
                    kind,
                    key,
                    le[kind].get(key),
                    re[kind].get(key),
                )
    check_limit("comparison_queries", len(queries), 16)
    analyses: list[dict[str, Any]] = []
    for source, service in sorted({(q.source_asset_id, q.service_id) for q in queries}):
        results: list[TraceResult | None] = []
        reasons: list[str] = []
        for snapshot, catalogs in ((left, lc), (right, rc)):
            if source not in catalogs["assets"] or service not in catalogs["services"]:
                results.append(None)
                reasons.append("Query endpoint/service is absent from this model.")
                continue
            try:
                results.append(trace_architecture(snapshot, source, service))
            except ModelError as error:
                if not all(d.code == "UNSUPPORTED_QUERY" for d in error.diagnostics):
                    raise
                results.append(None)
                reasons.append(
                    "Native engine does not support this query (including self-only queries)."
                )
        a, b = results
        # Explicit identifier reuse or mapping does not silently rewrite a query.
        changed_identity = any(
            (k, identity) in reused or pairs[k].get(identity, (identity, ""))[0] != identity
            for k, identity in (
                ("assets", source),
                ("services", service),
                *(
                    (
                        ("assets", a.scope.destination_asset_id),
                        ("interfaces", a.scope.destination_interface_id),
                    )
                    if a
                    else ()
                ),
            )
        )
        changed_identity = changed_identity or left.model.suc.id != right.model.suc.id
        delta = (
            _analytical_delta(a, b)
            if a and b and not changed_identity
            else {
                "classification": "NOT_COMPARABLE",
                "intervals": [],
                "reason": reasons
                or [
                    "Endpoint identity correspondence changed; exact queries are "
                    "never silently remapped."
                ],
            }
        )
        analyses.append(
            {
                "query": {"source_asset_id": source, "service_id": service},
                "baseline_model_sha256": left.sha256,
                "proposed_model_sha256": right.sha256,
                "baseline": asdict(a) if a else None,
                "proposed": asdict(b) if b else None,
                **delta,
            }
        )
    quality_left = _assess_snapshot(
        left, lp, load_control(baseline_profile, QualityProfile) if baseline_profile else None
    )
    quality_right = _assess_snapshot(
        right, rp, load_control(proposed_profile, QualityProfile) if proposed_profile else None
    )

    # Model binding differs across versions. Scope equality excludes only that binding.
    def quality_scope(report: dict[str, Any]) -> object:
        scope = report["scope"]
        return {k: v for k, v in scope.items() if k != "model_sha256"} if scope else None

    same_scope = quality_scope(quality_left) == quality_scope(quality_right)
    ql = {f["finding_id"]: f for f in quality_left["findings"]}
    qr = {f["finding_id"]: f for f in quality_right["findings"]}
    quality_changes = []
    for identity in sorted(ql.keys() | qr.keys()):
        a, b = ql.get(identity), qr.get(identity)
        state = (
            "NOT_COMPARABLE"
            if not same_scope or a is None or b is None
            else (
                "NEWLY_ASSESSED"
                if a["state"] == "NOT_ASSESSED" and b["state"] != "NOT_ASSESSED"
                else "NEWLY_UNASSESSED"
                if a["state"] != "NOT_ASSESSED" and b["state"] == "NOT_ASSESSED"
                else "RESOLVED"
                if a["state"]
                in {
                    "MISSING_REQUIRED_INFORMATION",
                    "REVIEW_REQUIRED",
                    "CONTRADICTORY_EVIDENCE",
                    "UNSUPPORTED",
                }
                and b["state"] == "SATISFIED"
                else "INTRODUCED"
                if a["state"] == "SATISFIED"
                and b["state"]
                in {
                    "MISSING_REQUIRED_INFORMATION",
                    "REVIEW_REQUIRED",
                    "CONTRADICTORY_EVIDENCE",
                    "UNSUPPORTED",
                }
                else "PERSISTING"
            )
        )
        quality_changes.append(
            {
                "finding_id": identity,
                "classification": state,
                "baseline_state": a["state"] if a else None,
                "proposed_state": b["state"] if b else None,
            }
        )
    report = {
        "comparison_version": 1,
        "rule_version": 1,
        "baseline_model_sha256": left.sha256,
        "proposed_model_sha256": right.sha256,
        "baseline_provenance_sha256": evidence_identity(lp),
        "proposed_provenance_sha256": evidence_identity(rp),
        "mapping": owner.model_dump(mode="json") if owner else None,
        "correspondences": correspondences,
        "changes": sorted(changes, key=lambda c: c["change_id"]),
        "analytical_results": analyses,
        "analytical_status": (
            "EVALUATED"
            if analyses and all(a["baseline"] and a["proposed"] for a in analyses)
            else "PARTIALLY_EVALUATED"
            if any(a["baseline"] or a["proposed"] for a in analyses)
            else "NOT_EVALUATED"
        ),
        "documentary_status": "COMPARED" if lp and rp else "NOT_ASSESSED",
        "quality_baseline": quality_left,
        "quality_proposed": quality_right,
        "quality_changes": quality_changes,
        "limitations": [
            "Same IDs mean declared continuity unless explicitly marked "
            "reused. No fuzzy, label or IP matching.",
            "Splits/merges require unmatched add/remove records; one-to-one mappings only.",
            "Documentary connectors do not declare transport or network permission.",
            "Missing provenance on either side prevents documentary history claims.",
            "Exact results apply only to evaluated queries, never global network security.",
        ],
    }
    report["comparison_sha256"] = digest(report)
    check_limit("comparison_report_bytes", len(canonical(report)), 32 * 1024 * 1024)
    return report
