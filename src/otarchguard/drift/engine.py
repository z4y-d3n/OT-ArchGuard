"""One-acquisition historical comparison; no source artifacts are modified."""

import hashlib
import re
from collections import Counter
from dataclasses import asdict
from importlib.resources import files
from pathlib import Path
from typing import Any, cast

from otarchguard.diagnostics import check_limit, fail
from otarchguard.drift.contract import (
    DRIFT_LIMITS,
    DRIFT_VERSION,
    ENGINE_VERSION,
    LIMITATIONS,
    MODES,
    POLICY_VERSION,
    Budget,
    DriftLimits,
    Side,
    finding,
    source,
)
from otarchguard.evidence import lifecycle
from otarchguard.evidence.attachments import _clone, object_digest
from otarchguard.evidence.history import _HistoryImage
from otarchguard.evidence.reviews import _scope, _text, validate_reviews
from otarchguard.evidence.validation import _ValidationContext
from otarchguard.evidence.workspace import serialize

_MODULES = (
    "drift/__init__.py",
    "drift/contract.py",
    "drift/engine.py",
    "drift/comparability.py",
    "drift/communications.py",
    "drift/protocols.py",
    "drift/architecture.py",
    "drift/reports.py",
)


def implementation() -> dict[str, str]:
    package = files("otarchguard")
    try:
        return {
            name: hashlib.sha256(package.joinpath(name).read_bytes()).hexdigest()
            for name in _MODULES
        }
    except OSError:
        fail(
            "DRIFT_IMPLEMENTATION", "$", "Cannot identify the supported comparison implementation."
        )


def _require(condition: bool, message: str) -> None:
    if not condition:
        fail("DRIFT_INPUT", "$", message)


def _ids(values: object, maximum: int, name: str) -> list[str]:
    _require(type(values) is list, "Select an explicit list of exact " + name + " identities.")
    assert isinstance(values, list)
    check_limit("drift_" + name, len(values), maximum)
    prefix = "review" if name == "review_frontier" else "analysis"
    _require(
        all(
            type(v) is str
            and len(v) == len(prefix) + 65
            and re.fullmatch(prefix + r"-[0-9a-f]{64}", v) is not None
            for v in values
        ),
        "Select exact bounded " + prefix + " identities.",
    )
    _require(len(values) == len(set(values)), "Duplicate selected " + name + " identities.")
    return sorted(values)


def _approval(state: dict[str, Any], baseline: str, statuses: dict[str, str]) -> dict[str, Any]:
    _require(
        statuses.get(baseline) == "APPROVED",
        "Normal comparison requires this exact baseline to be currently APPROVED.",
    )
    successors = {
        r["predecessor"] for r in state["reviews"].values() if r["predecessor"] is not None
    }
    selected = [
        r
        for rid, r in state["reviews"].items()
        if r["subject_id"] == baseline
        and r["decision"] in {"approve", "supersede"}
        and rid not in successors
    ]
    _require(len(selected) == 1, "An exact effective introducing approval is required.")
    return cast(dict[str, Any], selected[0])


def _context(value: dict[str, Any], refs: list[str], candidates: list[str]) -> dict[str, Any]:
    value = _clone(value)
    _require(
        set(value) == {"context_version", "pairs"}
        and type(value["context_version"]) is int
        and value["context_version"] == 1
        and type(value["pairs"]) is list,
        "Use supported comparison context version 1.",
    )
    check_limit("drift_pairs", len(value["pairs"]), DRIFT_LIMITS.collections)
    used_refs: set[str] = set()
    used_candidates: set[str] = set()
    for pair in value["pairs"]:
        _require(
            type(pair) is dict
            and set(pair)
            == {
                "reference_analysis_id",
                "candidate_analysis_id",
                "candidate_scope",
                "alignment",
                "rationale",
                "native_queries",
            },
            "Use exact comparison pair fields.",
        )
        r, c = pair["reference_analysis_id"], pair["candidate_analysis_id"]
        _require(
            type(r) is str and type(c) is str and r in refs and c in candidates,
            "Pair members must be explicitly selected source revisions.",
        )
        _require(
            r not in used_refs and c not in used_candidates,
            "Alignment must be one-to-one; no collection may be counted twice.",
        )
        used_refs.add(r)
        used_candidates.add(c)
        _require(
            type(pair["alignment"]) is str
            and pair["alignment"] in {"asserted", "unresolved"}
            and _text(pair["rationale"]),
            "Supply a bounded explicit alignment assertion.",
        )
        _scope(pair["candidate_scope"])
        queries = pair["native_queries"]
        _require(type(queries) is list, "Native queries must be an explicit list.")
        check_limit("drift_native_query_pairs", len(queries), DRIFT_LIMITS.native_queries // 2)
        for query in queries:
            _require(
                type(query) is dict
                and set(query) == {"source_asset_id", "service_id"}
                and all(_text(v, 256) for v in query.values()),
                "Use exact source_asset_id and service_id native query fields.",
            )
        keys = [(q["source_asset_id"], q["service_id"]) for q in queries]
        _require(len(keys) == len(set(keys)), "Duplicate native query.")
        pair["native_queries"] = sorted(
            queries, key=lambda q: (q["source_asset_id"], q["service_id"])
        )
    value["pairs"] = sorted(
        value["pairs"], key=lambda p: (p["reference_analysis_id"], p["candidate_analysis_id"])
    )
    return value


def _side(state: dict[str, Any], snapshots: dict[str, dict[str, Any]], aid: str) -> Side:
    analysis = state["analyses"].get(aid)
    _require(analysis is not None, "Exact selected analytical revision is unavailable.")
    assert analysis is not None
    selected = {
        name: state["attachments"][component["attachment_id"]]
        for name, component in analysis["components"].items()
        if component is not None and name != "policy"
    }
    return Side(analysis, snapshots[analysis["capture_sha256"]], selected)


def _candidate_authorities(
    state: dict[str, Any],
    statuses: dict[str, str],
    budget: Budget,
) -> dict[str, list[dict[str, Any]]]:
    successors = {r["predecessor"] for r in state["reviews"].values()}
    active = {
        r["subject_id"]: rid
        for rid, r in state["reviews"].items()
        if rid not in successors and r["decision"] in {"approve", "supersede"}
    }
    budget.charge("work_units", 2 * len(state["reviews"]))
    memberships: dict[str, list[dict[str, Any]]] = {}
    for bid, baseline in sorted(state["baselines"].items()):
        budget.charge("work_units", 1 + len(baseline["members"]))
        if statuses[bid] == "APPROVED":
            for member in baseline["members"]:
                memberships.setdefault(member["analysis_id"], []).append(
                    {
                        "baseline_id": bid,
                        "review_id": active[bid],
                        "scope_sha256": baseline["scope_sha256"],
                    }
                )
    return memberships


def _build(
    image: _HistoryImage,
    validated: _ValidationContext,
    baseline_id: str,
    candidates: list[str],
    context: dict[str, Any],
    *,
    mode: str = "qualified",
    reference_members: list[str] | None = None,
    candidate_model: str | None = None,
    limits: DriftLimits = DRIFT_LIMITS,
    review_frontier: list[str] | None = None,
) -> dict[str, Any]:
    from otarchguard.drift.architecture import compare_models, compare_native_evidence
    from otarchguard.drift.communications import compare_communications
    from otarchguard.drift.comparability import assess, compare_coverage
    from otarchguard.drift.protocols import compare_protocols

    _require(type(mode) is str and mode in MODES, "Use strict, qualified or descriptive mode.")
    _require(
        type(baseline_id) is str
        and len(baseline_id) == 73
        and re.fullmatch(r"baseline-[0-9a-f]{64}", baseline_id) is not None,
        "Select an exact baseline identity.",
    )
    budget = Budget(limits)
    state = validated._state
    statuses = validated.statuses
    frontier = sorted(state["reviews"])
    if review_frontier is not None:
        frontier = _ids(review_frontier, 1024, "review_frontier")
        _require(
            all(r in state["reviews"] for r in frontier),
            "Original review decisions are unavailable.",
        )
        state = {**state, "reviews": {rid: state["reviews"][rid] for rid in frontier}}
    # Compare only the baseline/review dependency closure represented in this
    # report. Later unrelated proposals must not alter canonical work accounting
    # or historical candidate authority. Full current lifecycle validation above
    # still includes every unselected object.
    subjects = {baseline_id} | {r["subject_id"] for r in state["reviews"].values()}
    state = {
        **state,
        "baselines": {bid: b for bid, b in state["baselines"].items() if bid in subjects},
    }
    if review_frontier is not None:
        # Historical verification replays an exact validated predecessor-closed graph.
        # It never grants current authority; current status is returned separately.
        statuses = validate_reviews(state)
    baseline = state["baselines"].get(baseline_id)
    _require(baseline is not None, "Exact baseline is unavailable.")
    assert baseline is not None
    approval = _approval(state, baseline_id, statuses)
    candidate_authorities = _candidate_authorities(state, statuses, budget)
    all_refs = [m["analysis_id"] for m in baseline["members"]]
    refs = _ids(
        all_refs if reference_members is None else reference_members, limits.revisions, "references"
    )
    selected_candidates = _ids(candidates, limits.revisions, "candidates")
    _require(
        set(refs) <= set(all_refs),
        "Reference revisions must belong to this exact approved baseline.",
    )
    _require(
        baseline["kind"] != "evidence" or bool(refs) and bool(selected_candidates),
        "Evidence comparisons require reference and candidate revisions.",
    )
    selected_context = _context(context, refs, selected_candidates)
    budget.charge("revisions", len(refs) + len(selected_candidates))
    snapshots = {s["capture_sha256"]: s for s in state["snapshots"].values()}
    sides = {aid: _side(state, snapshots, aid) for aid in sorted(set(refs + selected_candidates))}
    for selected_ids in (refs, selected_candidates):
        captures = [sides[aid].analysis["capture_sha256"] for aid in selected_ids]
        _require(
            len(captures) == len(set(captures)),
            "Select one interpretation per physical collection per side.",
        )
    budget.charge("collections", len({s.analysis["capture_sha256"] for s in sides.values()}))
    comparisons: list[dict[str, Any]] = []
    paired_refs: set[str] = set()
    paired_candidates: set[str] = set()
    for pair in selected_context["pairs"]:
        rid, cid = pair["reference_analysis_id"], pair["candidate_analysis_id"]
        reference, candidate = sides[rid], sides[cid]
        assessment = assess(
            reference,
            candidate,
            baseline["scope"],
            pair["candidate_scope"],
            pair["alignment"],
            budget,
        )
        if mode == "strict":
            _require(
                assessment["communication_metadata"] == "COMPARABLE",
                "Strict comparison requires equivalent supported observation scope and coverage.",
            )
        findings = compare_communications(reference, candidate, assessment, budget)
        findings.extend(compare_coverage(reference, candidate, budget))
        findings.extend(compare_protocols(reference, candidate, assessment, budget))
        reference_model = reference.attachments.get("model")
        candidate_model_attachment = candidate.attachments.get("model")
        findings.extend(
            compare_models(
                validated._native_models.get(reference_model["component_sha256"])
                if reference_model
                else None,
                validated._native_models.get(candidate_model_attachment["component_sha256"])
                if candidate_model_attachment
                else None,
                source(reference),
                source(candidate),
                pair["native_queries"],
                budget,
            )
        )
        findings.extend(compare_native_evidence(reference, candidate, budget))
        if (
            reference.analysis["producer_semantics_sha256"]
            != candidate.analysis["producer_semantics_sha256"]
        ):
            findings.append(
                finding(
                    "ANALYTICAL_INTERPRETATION_DIFFERENCE",
                    "SELECTED_SEMANTICS_CHANGED",
                    "producer_semantics",
                    source(reference),
                    source(candidate),
                    "PARTIALLY_COMPARABLE",
                    "Selected local analytical semantics differ; "
                    "this is not independent evidence of a network change.",
                    budget,
                )
            )
        if any(
            reference.analysis["components"][k] != candidate.analysis["components"][k]
            for k in ("model", "mapping", "comparison")
        ):
            findings.append(
                finding(
                    "ANALYTICAL_INTERPRETATION_DIFFERENCE",
                    "ANALYTICAL_COMPONENTS_CHANGED",
                    "components",
                    source(reference),
                    source(candidate),
                    "PARTIALLY_COMPARABLE",
                    "Selected model, mapping or native assessment inputs differ; "
                    "approval is not transferred.",
                    budget,
                )
            )
        comparisons.append(
            {
                "reference_analysis_id": rid,
                "candidate_analysis_id": cid,
                "comparability": assessment,
                "findings": findings,
            }
        )
        paired_refs.add(rid)
        paired_candidates.add(cid)
    unmatched: list[dict[str, Any]] = []
    for role, identities in (
        ("reference", set(refs) - paired_refs),
        ("candidate", set(selected_candidates) - paired_candidates),
    ):
        for aid in sorted(identities):
            unmatched.append(
                finding(
                    "INDETERMINATE_COMPARISON",
                    "UNALIGNED_COLLECTION",
                    role,
                    source(sides[aid]) if role == "reference" else None,
                    source(sides[aid]) if role == "candidate" else None,
                    "INDETERMINATE",
                    "No explicit collection correspondence was supplied; "
                    "no cross-collection join is performed.",
                    budget,
                )
            )
    _require(
        mode != "strict" or not unmatched,
        "Strict comparison requires explicit alignment for every selected collection.",
    )
    architecture_findings: list[dict[str, Any]] = []
    model_manifest = None
    if candidate_model is not None:
        _require(
            type(candidate_model) is str
            and len(candidate_model) == 75
            and re.fullmatch(r"attachment-[0-9a-f]{64}", candidate_model) is not None
            and candidate_model in state["attachments"],
            "Exact candidate model attachment is unavailable.",
        )
        ref_model = state["attachments"].get(baseline["model_attachment_id"])
        cand_model = state["attachments"][candidate_model]
        _require(
            ref_model is not None and cand_model["kind"] == "model",
            "Select both exact validated baseline and candidate model attachments.",
        )
        assert ref_model is not None
        model_manifest = {
            "reference": {
                "attachment_id": ref_model["attachment_id"],
                "model_sha256": ref_model["component_sha256"],
            },
            "candidate": {
                "attachment_id": cand_model["attachment_id"],
                "model_sha256": cand_model["component_sha256"],
            },
        }
        architecture_findings = compare_models(
            validated._native_models[ref_model["component_sha256"]],
            validated._native_models[cand_model["component_sha256"]],
            model_manifest["reference"],
            model_manifest["candidate"],
            [],
            budget,
        )
    _require(
        baseline["kind"] != "architecture" or candidate_model is not None,
        "Architecture baseline comparison requires an exact candidate model attachment.",
    )
    all_findings = (
        [f for pair in comparisons for f in pair["findings"]] + unmatched + architecture_findings
    )
    counts = dict(sorted(Counter(f["category"] for f in all_findings).items()))
    unchanged_subtypes = {
        "OBSERVED_IN_BOTH",
        "REACHABILITY_UNCHANGED",
        "RECONCILIATION_ASSESSMENT_UNCHANGED",
    }
    unchanged = sum(f["subtype"] in unchanged_subtypes for f in all_findings)
    abstentions = sum(
        f["category"] == "INDETERMINATE_COMPARISON"
        or f["subtype"] == "UNASSESSED_OPAQUE_OBSERVATIONS"
        for f in all_findings
    )
    report: dict[str, Any] = {
        "drift_version": DRIFT_VERSION,
        "engine_version": ENGINE_VERSION,
        "comparability_policy_version": POLICY_VERSION,
        "implementation_sha256": implementation(),
        "inputs": {
            "workspace_manifest_sha256": image.files["workspace.json"][1],
            "baseline": baseline,
            "approval": approval,
            "approval_state": "APPROVED",
            "review_frontier": frontier,
            "reference_sources": [source(sides[aid]) for aid in refs],
            "candidate_sources": [
                {
                    **source(sides[aid]),
                    "review_authority": {
                        "inherits_reference_approval": False,
                        "independent_approved_memberships": candidate_authorities.get(aid, []),
                        "reviewer_authority": "unauthenticated-local-assertion",
                    },
                }
                for aid in selected_candidates
            ],
            "selected_models": model_manifest,
        },
        "options": {
            "mode": mode,
            "reference_members": refs,
            "candidates": selected_candidates,
            "candidate_model": candidate_model,
            "context": selected_context,
        },
        "comparisons": comparisons,
        "unaligned_findings": unmatched,
        "architecture_findings": architecture_findings,
        "summary": {
            "categories": counts,
            "findings": len(all_findings),
            "difference_records": len(all_findings) - unchanged - abstentions,
            "unchanged_support_records": unchanged,
            "abstentions": abstentions,
            "aligned_pairs": len(comparisons),
            "distinct_physical_collections": len(
                {s.analysis["capture_sha256"] for s in sides.values()}
            ),
            "interpretation": "Descriptive finite-dataset differences."
            if mode == "descriptive"
            else "Qualified evidence differences; operational change remains unproven.",
        },
        "limits": asdict(limits),
        "resource_usage": dict(sorted(budget.used.items())),
        "limitations": list(LIMITATIONS),
        "reproduction": (
            "Revalidate all lifecycle dependencies, replay the recorded review graph, "
            "and require exact canonical equality. Current approval is checked separately."
        ),
    }
    report["drift_id"] = "drift-" + object_digest("otarchguard.drift.v1", report)
    check_limit("drift_report_bytes", len(serialize(report)), limits.report_bytes)
    return report


def compare(
    workspace: Path,
    baseline_id: str,
    candidates: list[str],
    context: dict[str, Any],
    *,
    mode: str = "qualified",
    reference_members: list[str] | None = None,
    candidate_model: str | None = None,
    limits: DriftLimits = DRIFT_LIMITS,
) -> dict[str, Any]:
    """Validate one exact approved reference and explicitly aligned candidate selection."""
    image, validated = lifecycle._operation(workspace)
    return _build(
        image,
        validated,
        baseline_id,
        candidates,
        context,
        mode=mode,
        reference_members=reference_members,
        candidate_model=candidate_model,
        limits=limits,
    )
