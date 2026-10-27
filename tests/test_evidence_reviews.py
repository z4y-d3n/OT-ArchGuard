"""Independent lifecycle expectations for scoped local human assertions."""

import copy
import hashlib
import json
from typing import Any

import pytest

from otarchguard.diagnostics import ModelError
from otarchguard.evidence.reviews import (
    baseline_summary,
    build_baseline,
    build_review,
    validate_baseline,
    validate_reviews,
)


def scope() -> dict[str, Any]:
    return {
        "environment": "Fictional site",
        "purpose": "Synthetic review test",
        "coverage": "Unknown packet loss and visibility",
        "uncertainties": ["No continuous monitoring asserted"],
        "vantage_points": [],
        "protocols": [],
    }


def state() -> dict[str, Any]:
    return {
        "analyses": {
            "analysis-" + "a" * 64: {"capture_sha256": "a" * 64},
            "analysis-" + "b" * 64: {"capture_sha256": "a" * 64},
            "analysis-" + "c" * 64: {"capture_sha256": "c" * 64},
        },
        "attachments": {},
        "baselines": {},
        "reviews": {},
    }


def propose(
    s: dict[str, Any], member: str = "a", selected_scope: dict[str, Any] | None = None
) -> str:
    baseline = build_baseline("evidence", ["analysis-" + member * 64], selected_scope or scope(), s)
    s["baselines"][baseline["baseline_id"]] = baseline
    return str(baseline["baseline_id"])


def decide(
    s: dict[str, Any], subject: str, action: str = "approve", predecessor: str | None = None
) -> str:
    review = build_review(
        subject, action, "Fictional reviewer", "Fictional rationale", s, predecessor
    )
    s["reviews"][review["review_id"]] = review
    return str(review["review_id"])


def test_proposal_is_not_an_approval_and_identity_is_independently_canonical() -> None:
    s = state()
    bid = propose(s)
    baseline = s["baselines"][bid]
    body = {k: v for k, v in baseline.items() if k != "baseline_id"}
    independent = json.dumps(
        {"domain": "otarchguard.baseline", "value": body},
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("ascii")
    assert bid == "baseline-" + hashlib.sha256(independent).hexdigest()
    assert validate_reviews(s) == {bid: "PROPOSED"}
    validate_baseline(baseline, s)
    assert baseline_summary(baseline, s)["review_history"] == []


def test_new_interpretation_has_no_automatic_approval_and_scope_conflict_fails() -> None:
    s = state()
    a, b = propose(s), propose(s, "b")
    decide(s, a)
    assert validate_reviews(s) == {a: "APPROVED", b: "PROPOSED"}
    with pytest.raises(ModelError):
        decide(s, b)
    assert len(s["reviews"]) == 1


def test_supersession_then_revocation_retains_every_historical_record() -> None:
    s = state()
    a, b = propose(s), propose(s, "b")
    first = decide(s, a)
    original = copy.deepcopy(s["reviews"][first])
    successor = decide(s, b, "supersede", first)
    assert validate_reviews(s) == {a: "SUPERSEDED", b: "APPROVED"}
    decide(s, b, "revoke", successor)
    assert validate_reviews(s) == {a: "SUPERSEDED", b: "REVOKED"}
    assert s["reviews"][first] == original
    assert len(s["reviews"]) == 3


def test_identical_decision_is_idempotent_without_time_ordering() -> None:
    s = state()
    bid = propose(s)
    rid = decide(s, bid)
    again = build_review(bid, "approve", "Fictional reviewer", "Fictional rationale", s)
    assert again == s["reviews"][rid]
    assert again["asserted_at"] is None


@pytest.mark.parametrize("action", ["approve", "reject", "revoke", "supersede", "future"])
def test_missing_explicit_reviewer_or_rationale_never_creates_decision(action: str) -> None:
    s = state()
    bid = propose(s)
    for reviewer, rationale in (
        ("", "reason"),
        ("reviewer", ""),
        (" ", "reason"),
        ("x\n", "reason"),
    ):
        with pytest.raises(ModelError):
            build_review(bid, action, reviewer, rationale, s)
    assert s["reviews"] == {}


@pytest.mark.parametrize("action", ["revoke", "supersede"])
def test_predecessor_must_be_available_and_active_with_one_successor(action: str) -> None:
    s = state()
    a, b = propose(s), propose(s, "b")
    first = decide(s, a)
    with pytest.raises(ModelError):
        decide(s, b, action, "review-" + "f" * 64)
    decide(s, a, "revoke", first)
    with pytest.raises(ModelError):
        build_review(
            a if action == "revoke" else b,
            action,
            "Another fictional reviewer",
            "A conflicting successor",
            s,
            first,
        )


def test_changed_scope_does_not_inherit_or_cancel_previous_scope_approval() -> None:
    s = state()
    a = propose(s)
    first = decide(s, a)
    changed = scope()
    changed["coverage"] = "Different explicitly asserted coverage"
    b = propose(s, "b", changed)
    with pytest.raises(ModelError):
        decide(s, b, "supersede", first)
    decide(s, b)
    assert validate_reviews(s) == {a: "APPROVED", b: "APPROVED"}


@pytest.mark.parametrize("mutation", ["version", "field", "scope", "reference", "reviewer"])
def test_rehashed_malformed_review_is_rejected(mutation: str) -> None:
    s = state()
    bid = propose(s)
    rid = decide(s, bid)
    review = s["reviews"].pop(rid)
    if mutation == "version":
        review["review_version"] = True
    elif mutation == "field":
        review["authority"] = "authenticated"
    elif mutation == "scope":
        review["scope_sha256"] = "0" * 64
    elif mutation == "reference":
        review["evidence_references"] = []
    else:
        review["reviewer"] = ""
    body = {k: v for k, v in review.items() if k != "review_id"}
    canonical = json.dumps(
        {"domain": "otarchguard.review", "value": body},
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("ascii")
    review["review_id"] = "review-" + hashlib.sha256(canonical).hexdigest()
    s["reviews"][review["review_id"]] = review
    with pytest.raises(ModelError):
        validate_reviews(s)


def test_one_baseline_cannot_count_two_revisions_as_two_physical_collections() -> None:
    s = state()
    with pytest.raises(ModelError):
        build_baseline("evidence", ["analysis-" + c * 64 for c in "ab"], scope(), s)
    good = build_baseline("evidence", ["analysis-" + c * 64 for c in "ac"], scope(), s)
    assert len(good["members"]) == 2


@pytest.mark.parametrize("mutation", ["missing", "unknown", "unsorted", "control", "oversized"])
def test_bounded_explicit_scope_is_required(mutation: str) -> None:
    s = state()
    value = scope()
    if mutation == "missing":
        del value["coverage"]
    elif mutation == "unknown":
        value["authentic"] = True
    elif mutation == "unsorted":
        value["protocols"] = ["z", "a"]
    elif mutation == "control":
        value["environment"] = "site\x1b[2J"
    else:
        value["uncertainties"] = ["x"] * 33
    with pytest.raises(ModelError):
        propose(s, selected_scope=value)


def test_architecture_baseline_requires_a_validated_model_attachment() -> None:
    s = state()
    with pytest.raises(ModelError):
        build_baseline("architecture", [], scope(), s)


def test_rejection_is_historical_terminal_and_never_approval() -> None:
    s = state()
    bid = propose(s)
    rejected = decide(s, bid, "reject")
    assert validate_reviews(s) == {bid: "REJECTED"}
    with pytest.raises(ModelError):
        decide(s, bid)
    with pytest.raises(ModelError):
        decide(s, bid, "revoke", rejected)
