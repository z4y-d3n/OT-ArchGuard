"""Bounded immutable baseline proposals and locally asserted human decisions.

There are no authenticated users or implicit approvals. Effective state is derived
from exact predecessor references, never timestamps or filesystem ordering.
"""

import copy
import re
from collections import Counter
from datetime import datetime
from typing import Any

from otarchguard.diagnostics import check_limit, fail
from otarchguard.evidence.observations import digest

SCOPE_FIELDS = {
    "environment",
    "purpose",
    "coverage",
    "uncertainties",
    "vantage_points",
    "protocols",
}
REVIEW_LIMITATIONS = [
    "Reviewer identity and authority are unauthenticated local assertions.",
    "Approval does not establish authenticity, safety, deployment or complete visibility.",
    "Approval applies only to the exact baseline identity and declared scope.",
    "Labels and rationales may contain sensitive information; review before sharing.",
]


def _require(condition: bool, message: str) -> None:
    if not condition:
        fail("EVIDENCE_REVIEW", "$", message)


def _text(value: object, maximum: int = 1024, empty: bool = False) -> bool:
    return (
        isinstance(value, str)
        and (empty or bool(value.strip()))
        and len(value) <= maximum
        and all(c.isprintable() for c in value)
    )


def _id(kind: str, value: dict[str, Any]) -> str:
    return kind + "-" + digest({"domain": "otarchguard." + kind, "value": value})


def _scope(scope: dict[str, Any]) -> None:
    _require(
        isinstance(scope, dict) and set(scope) == SCOPE_FIELDS,
        "Use the exact baseline scope fields.",
    )
    for name in ("environment", "purpose", "coverage"):
        _require(
            _text(scope[name]),
            "Scope requires bounded printable environment, purpose and coverage.",
        )
    for name in ("uncertainties", "vantage_points", "protocols"):
        items = scope[name]
        _require(
            isinstance(items, list)
            and len(items) <= 32
            and all(_text(item, 256) for item in items),
            "Scope lists require at most 32 bounded printable strings.",
        )
        _require(items == sorted(set(items)), "Scope lists must be unique and sorted.")


def build_baseline(
    kind: str,
    members: list[str],
    scope: dict[str, Any],
    state: dict[str, Any],
    model_attachment_id: str | None = None,
) -> dict[str, Any]:
    """Select exact validated revisions or a model; this never creates approval."""
    _require(kind in {"evidence", "architecture"}, "Unsupported baseline kind.")
    _scope(scope)
    _require(
        isinstance(members, list) and all(isinstance(m, str) for m in members), "Invalid members."
    )
    check_limit("baseline_members", len(members), 256)
    _require(len(members) == len(set(members)), "Duplicate baseline analytical members.")
    _require(
        kind != "evidence" or bool(members), "Evidence baselines require an analytical member."
    )
    selected = []
    captures: set[str] = set()
    for member in sorted(members):
        analysis = state["analyses"].get(member)
        _require(analysis is not None, "Baseline analytical dependency is unavailable.")
        capture = analysis["capture_sha256"]
        _require(
            capture not in captures,
            "A baseline selects only one interpretation per physical collection.",
        )
        captures.add(capture)
        selected.append({"analysis_id": member, "capture_sha256": capture})
    model_sha256 = None
    if model_attachment_id is not None:
        model = state["attachments"].get(model_attachment_id)
        _require(
            model is not None and model.get("kind") == "model",
            "Select a validated model attachment.",
        )
        model_sha256 = model["component_sha256"]
    _require(
        kind != "architecture" or model_attachment_id is not None,
        "Architecture baselines require a model.",
    )
    value = {
        "baseline_version": 1,
        "kind": kind,
        "members": selected,
        "model_attachment_id": model_attachment_id,
        "model_sha256": model_sha256,
        "scope": copy.deepcopy(scope),
        "scope_sha256": digest(scope),
        "limitations": list(REVIEW_LIMITATIONS),
    }
    return {**value, "baseline_id": _id("baseline", value)}


def validate_baseline(value: dict[str, Any], state: dict[str, Any]) -> None:
    try:
        _require(
            type(value["baseline_version"]) is int and value["baseline_version"] == 1,
            "Unsupported baseline version.",
        )
        expected = build_baseline(
            value["kind"],
            [m["analysis_id"] for m in value["members"]],
            value["scope"],
            state,
            value["model_attachment_id"],
        )
        _require(
            digest(value) == digest(expected), "Baseline identity, fields or membership mismatch."
        )
    except (KeyError, TypeError, ValueError, AttributeError):
        fail("EVIDENCE_BASELINE", "$", "Invalid or unsupported baseline proposal.")


def _review_content(
    baseline_id: str,
    decision: str,
    reviewer: str,
    rationale: str,
    state: dict[str, Any],
    predecessor: str | None,
    timestamp: str | None,
) -> dict[str, Any]:
    _require(
        decision in {"approve", "reject", "revoke", "supersede"}, "Unsupported review decision."
    )
    _require(
        _text(reviewer, 256) and _text(rationale, 2048),
        "Reviewer and rationale must be supplied explicitly.",
    )
    _require(
        timestamp is None
        or (
            isinstance(timestamp, str)
            and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", timestamp)
            is not None
        ),
        "Contextual time must be null or asserted UTC second text.",
    )
    if timestamp is not None:
        try:
            datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            fail("EVIDENCE_REVIEW", "$", "Contextual UTC date or time is invalid.")
    baseline = state["baselines"].get(baseline_id)
    _require(baseline is not None, "Review subject baseline is unavailable.")
    _require(
        (decision in {"revoke", "supersede"}) == (predecessor is not None),
        "Successor decisions require an exact predecessor; root decisions forbid it.",
    )
    references = [m["analysis_id"] for m in baseline["members"]]
    if baseline["model_attachment_id"] is not None:
        references.append(baseline["model_attachment_id"])
    return {
        "review_version": 1,
        "subject_type": "baseline",
        "subject_id": baseline_id,
        "decision": decision,
        "scope_sha256": baseline["scope_sha256"],
        "reviewer": reviewer,
        "rationale": rationale,
        "evidence_references": sorted(references),
        "predecessor": predecessor,
        "asserted_at": timestamp,
        "limitations": list(REVIEW_LIMITATIONS),
    }


def build_review(
    baseline_id: str,
    decision: str,
    reviewer: str,
    rationale: str,
    state: dict[str, Any],
    predecessor: str | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    """Build a decision only after checking the entire prospective review graph."""
    value = _review_content(
        baseline_id, decision, reviewer, rationale, state, predecessor, timestamp
    )
    result = {**value, "review_id": _id("review", value)}
    prospective = {**state, "reviews": {**state["reviews"], result["review_id"]: result}}
    validate_reviews(prospective)
    return result


def validate_reviews(state: dict[str, Any]) -> dict[str, str]:
    """Resolve bounded predecessor chains; forks and active scope conflicts fail closed."""
    reviews = state["reviews"]
    baselines = state["baselines"]
    check_limit("review_records", len(reviews), 1024)
    successors: dict[str, str] = {}
    incoming: Counter[str] = Counter()
    statuses = dict.fromkeys(baselines, "PROPOSED")
    for rid, review in reviews.items():
        try:
            _require(
                type(review["review_version"]) is int and review["review_version"] == 1,
                "Unsupported review version.",
            )
            expected = _review_content(
                review["subject_id"],
                review["decision"],
                review["reviewer"],
                review["rationale"],
                state,
                review["predecessor"],
                review["asserted_at"],
            )
            expected["review_id"] = _id("review", expected)
            _require(
                digest(review) == digest(expected) and rid == expected["review_id"],
                "Review identity, scope or fields mismatch.",
            )
            predecessor = review["predecessor"]
            if review["decision"] != "revoke":
                incoming[review["subject_id"]] += 1
                _require(
                    incoming[review["subject_id"]] <= 1,
                    "Conflicting decisions for an exact baseline.",
                )
            if predecessor is not None:
                _require(
                    isinstance(predecessor, str) and predecessor in reviews,
                    "Missing predecessor review.",
                )
                previous = reviews[predecessor]
                _require(
                    previous["decision"] in {"approve", "supersede"},
                    "Only an approval can be revoked or superseded.",
                )
                _require(predecessor not in successors, "Conflicting review successors.")
                successors[predecessor] = rid
                old = baselines[previous["subject_id"]]
                new = baselines[review["subject_id"]]
                _require(
                    old["kind"] == new["kind"] and old["scope_sha256"] == new["scope_sha256"],
                    "Successors must retain the exact declared scope and baseline kind.",
                )
                _require(
                    (review["decision"] == "revoke")
                    == (review["subject_id"] == previous["subject_id"]),
                    "Revocation targets its exact subject; "
                    "supersession selects a different baseline.",
                )
        except (KeyError, TypeError, ValueError, AttributeError):
            fail("EVIDENCE_REVIEW", "$", "Invalid immutable review graph.")
    # Traverse once from each root. A remaining node is cyclic or unreachable.
    roots = sorted(rid for rid, r in reviews.items() if r["predecessor"] is None)
    visited: set[str] = set()
    active_scopes: set[tuple[str, str]] = set()
    for rid in roots:
        current: str | None = rid
        while current is not None:
            _require(current not in visited, "Cyclic or shared review chain.")
            visited.add(current)
            review = reviews[current]
            subject = review["subject_id"]
            action = review["decision"]
            statuses[subject] = {
                "approve": "APPROVED",
                "reject": "REJECTED",
                "revoke": "REVOKED",
                "supersede": "APPROVED",
            }[action]
            if action == "supersede":
                statuses[reviews[review["predecessor"]]["subject_id"]] = "SUPERSEDED"
            next_review = successors.get(current)
            if next_review is None and action in {"approve", "supersede"}:
                baseline = baselines[subject]
                key = baseline["kind"], baseline["scope_sha256"]
                _require(
                    key not in active_scopes,
                    "Conflicting active approvals under the same exact scope.",
                )
                active_scopes.add(key)
            current = next_review
    _require(len(visited) == len(reviews), "Review graph contains cyclic or unreachable decisions.")
    return statuses


def baseline_summary(baseline: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    """A bounded review summary; no packet arrays need to be read by a human."""
    status = validate_reviews(state)[baseline["baseline_id"]]
    return {
        **baseline,
        "status": status,
        "physical_collections": len(baseline["members"]),
        "review_history": [
            r
            for _, r in sorted(state["reviews"].items())
            if r["subject_id"] == baseline["baseline_id"]
        ],
        "pending_action": "Explicit human approval required."
        if status == "PROPOSED"
        else "Inspect exact immutable review history.",
    }
