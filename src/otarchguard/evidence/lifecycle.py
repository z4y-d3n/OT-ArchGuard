"""Fully validated historical workflows used by the public offline CLI.

Storage inventories are necessary but insufficient: every public read and write
here verifies component semantics, exact dependencies and human decision graphs.
"""

from pathlib import Path
from typing import Any

from otarchguard.diagnostics import fail
from otarchguard.evidence.history import (
    HISTORY_LIMITS,
    _HistoryImage,
    _publish_from_image,
    _read_bytes,
    _read_image,
    read_document,
)
from otarchguard.evidence.reviews import (
    _baseline_summary,
    _build_review,
    build_baseline,
)
from otarchguard.evidence.validation import _ValidationContext


def _member(state: dict[str, Any], kind: str, identity: str) -> dict[str, Any]:
    if kind not in {
        "snapshots",
        "attachments",
        "analyses",
        "baselines",
        "reviews",
    } or not isinstance(identity, str):
        fail("EVIDENCE_ID", "$", "Use an exact supported historical object identity.")
    value = state[kind].get(identity)
    if value is None:
        fail("EVIDENCE_NOT_FOUND", "$", "Exact dependency is not present in this workspace.")
    return value  # type: ignore[no-any-return]


def validate_state(state: dict[str, Any]) -> None:
    """Return only controlled diagnostics for malformed dependency metadata."""
    try:
        _ValidationContext(state).validate()
    except (KeyError, TypeError, ValueError, AttributeError, IndexError, RecursionError):
        fail("EVIDENCE_GRAPH", "$", "Malformed or unsupported historical dependency graph.")


def _operation(workspace: Path) -> tuple[_HistoryImage, _ValidationContext]:
    """Acquire and validate the complete workspace for exactly one public operation.

    The image's parsed objects are owned by this invocation. Its context never
    escapes, and no cache or mutable validation flag is returned to callers.
    """
    image = _read_image(workspace)
    context = _ValidationContext._from_image(image)
    try:
        context.validate()
    except (KeyError, TypeError, ValueError, AttributeError, IndexError, RecursionError):
        fail("EVIDENCE_GRAPH", "$", "Malformed or unsupported historical dependency graph.")
    return image, context


def load_state(workspace: Path) -> dict[str, Any]:
    _, context = _operation(workspace)
    return context._state


def _publish(
    workspace: Path,
    image: _HistoryImage,
    context: _ValidationContext,
    kind: str,
    value: dict[str, Any],
) -> dict[str, Any]:
    singular = {
        "attachments": "attachment",
        "analyses": "analysis",
        "baselines": "baseline",
        "reviews": "review",
    }[kind]
    identity = value[singular + "_id"]

    def validate(prospective: dict[str, Any]) -> None:
        context.add(kind, prospective[kind][identity])

    return _publish_from_image(workspace, kind, value, image, validate)


def import_attachment(
    workspace: Path,
    snapshot_id: str,
    kind: str,
    source: Path,
    model: str | None = None,
    mapping: str | None = None,
) -> dict[str, Any]:
    image, context = _operation(workspace)
    # Preserve legacy selection/error order before reading the new source.
    _member(context._state, "snapshots", snapshot_id)
    for identity in (model, mapping):
        if identity is not None:
            _member(context._state, "attachments", identity)
    payload = _read_bytes(source, HISTORY_LIMITS) if kind == "model" else read_document(source)
    attachment = context.build_attachment(kind, payload, snapshot_id, model, mapping)
    result = _publish(workspace, image, context, "attachments", attachment)
    return {**result, "attachment": {k: v for k, v in attachment.items() if k != "payload"}}


def create_revision(
    workspace: Path,
    snapshot_id: str,
    enrichment: str | None = None,
    model: str | None = None,
    mapping: str | None = None,
    comparison: str | None = None,
    semantics: Path | None = None,
) -> dict[str, Any]:
    image, context = _operation(workspace)
    components = {
        name: aid
        for name, aid in {
            "enrichment": enrichment,
            "model": model,
            "mapping": mapping,
            "comparison": comparison,
        }.items()
        if aid is not None
    }
    for identity in components.values():
        _member(context._state, "attachments", identity)
    _member(context._state, "snapshots", snapshot_id)
    value = context.build_revision(
        snapshot_id,
        components,
        read_document(semantics) if semantics is not None else None,
    )
    return {**_publish(workspace, image, context, "analyses", value), "analysis": value}


def list_revisions(workspace: Path, capture: str | None = None) -> dict[str, Any]:
    state = load_state(workspace)
    if capture is not None and not any(
        s["capture_sha256"] == capture for s in state["snapshots"].values()
    ):
        fail("EVIDENCE_NOT_FOUND", "$", "Physical capture is not present in this workspace.")
    return {
        "analyses": [
            a
            for _, a in sorted(state["analyses"].items())
            if capture is None or a["capture_sha256"] == capture
        ]
    }


def show_object(workspace: Path, kind: str, identity: str) -> dict[str, Any]:
    _, context = _operation(workspace)
    state = context._state
    value = _member(state, kind, identity)
    return _baseline_summary(value, state, context.statuses) if kind == "baselines" else value


def propose_baseline(
    workspace: Path,
    scope_path: Path,
    revisions: list[str],
    kind: str = "evidence",
    model: str | None = None,
) -> dict[str, Any]:
    image, context = _operation(workspace)
    state = context._state
    value = build_baseline(kind, revisions, read_document(scope_path), state, model)
    result = _publish(workspace, image, context, "baselines", value)
    return {**result, "baseline": _baseline_summary(value, context._state, context.statuses)}


def record_review(
    workspace: Path,
    baseline_id: str,
    decision: str,
    reviewer: str,
    rationale: str,
    predecessor: str | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    image, context = _operation(workspace)
    value = _build_review(
        baseline_id, decision, reviewer, rationale, context._state, predecessor, timestamp
    )
    result = _publish(workspace, image, context, "reviews", value)
    return {
        **result,
        "review": value,
        "baseline_status": context.statuses[baseline_id],
    }


def list_baselines(workspace: Path) -> dict[str, Any]:
    _, context = _operation(workspace)
    state = context._state
    histories: dict[str, list[dict[str, Any]]] = {bid: [] for bid in state["baselines"]}
    for _, review in sorted(state["reviews"].items()):
        histories[review["subject_id"]].append(review)
    statuses = context.statuses
    return {
        "baselines": [
            _baseline_summary(b, state, statuses, histories[bid])
            for bid, b in sorted(state["baselines"].items())
        ]
    }


def list_history(workspace: Path) -> dict[str, Any]:
    _, context = _operation(workspace)
    state = context._state
    return {
        "workspace_version": 2,
        "physical_collections": len(state["snapshots"]),
        "analytical_revisions": len(state["analyses"]),
        "snapshots": [
            {
                k: s[k]
                for k in (
                    "snapshot_id",
                    "capture_sha256",
                    "observations_sha256",
                    "label",
                    "collection",
                )
            }
            for _, s in sorted(state["snapshots"].items())
        ],
        "attachments": [
            {k: a[k] for k in ("attachment_id", "kind", "capture_sha256", "component_sha256")}
            for _, a in sorted(state["attachments"].items())
        ],
        "analyses": sorted(state["analyses"]),
        "baselines": {k: v for k, v in sorted(context.statuses.items())},
    }


def verify_lifecycle(workspace: Path) -> dict[str, Any]:
    _, context = _operation(workspace)
    state = context._state
    statuses = list(context.statuses.values())
    return {
        "workspace_version": 2,
        "physical_collections": len(state["snapshots"]),
        **{
            kind: len(state[kind])
            for kind in ("snapshots", "attachments", "analyses", "reviews", "baselines")
        },
        "status": "VERIFIED_METADATA",
        "analytical_attachments": "STRUCTURALLY_VALIDATED",
        "cross_artifact_consistency": "VERIFIED",
        "source_authenticity": "UNVERIFIED",
        "reviewer_authority": "UNAUTHENTICATED_LOCAL_ASSERTION",
        "approved_baselines": statuses.count("APPROVED"),
        "revoked_baselines": statuses.count("REVOKED"),
        "superseded_baselines": statuses.count("SUPERSEDED"),
        "limitations": [
            "Metadata integrity and supported cross-artifact relationships were verified.",
            "Original capture bytes were not reopened; "
            "metadata cannot revalidate the original PCAP.",
            "Reviewer labels are local assertions, not authenticated organizational authority.",
            "Approval does not establish safety, deployment or comprehensive coverage.",
        ],
    }
