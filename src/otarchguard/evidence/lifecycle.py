"""Fully validated historical workflows used by the public offline CLI.

Storage inventories are necessary but insufficient: every public read and write
here verifies component semantics, exact dependencies and human decision graphs.
"""

from pathlib import Path
from typing import Any

from otarchguard.diagnostics import fail
from otarchguard.evidence.attachments import build_attachment, validate_attachment
from otarchguard.evidence.history import (
    HISTORY_LIMITS,
    _read_bytes,
    publish_object,
    read_document,
    read_history,
    verify_history,
)
from otarchguard.evidence.reviews import (
    baseline_summary,
    build_baseline,
    build_review,
    validate_baseline,
    validate_reviews,
)
from otarchguard.evidence.revisions import build_revision, validate_revision


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


def _validate_state(state: dict[str, Any]) -> None:
    """Validate the complete bounded dependency graph, including unselected objects."""
    snapshots = {s["capture_sha256"]: s for s in state["snapshots"].values()}
    for _, attachment in sorted(state["attachments"].items()):
        snapshot = snapshots.get(attachment.get("capture_sha256"))
        if snapshot is None:
            fail("EVIDENCE_ATTACHMENT", "$", "Attachment physical collection is unavailable.")
        dependencies = {
            name: _member(state, "attachments", aid)
            for name, aid in attachment.get("dependencies", {}).items()
            if aid is not None
        }
        validate_attachment(attachment, snapshot, dependencies)
    for _, analysis in sorted(state["analyses"].items()):
        snapshot = snapshots.get(analysis.get("capture_sha256"))
        if snapshot is None or snapshot["observations_sha256"] != analysis.get(
            "observations_sha256"
        ):
            fail("EVIDENCE_REVISION", "$", "Exact revision observations are unavailable.")
        components = {
            name: _member(state, "attachments", component["attachment_id"])
            for name, component in analysis.get("components", {}).items()
            if component is not None and name != "policy"
        }
        validate_revision(analysis, snapshot, components)
    for baseline in state["baselines"].values():
        validate_baseline(baseline, state)
    validate_reviews(state)


def validate_state(state: dict[str, Any]) -> None:
    """Return only controlled diagnostics for malformed dependency metadata."""
    try:
        _validate_state(state)
    except (KeyError, TypeError, ValueError, AttributeError, IndexError, RecursionError):
        fail("EVIDENCE_GRAPH", "$", "Malformed or unsupported historical dependency graph.")


def load_state(workspace: Path) -> dict[str, Any]:
    state = read_history(workspace)
    validate_state(state)
    return state


def import_attachment(
    workspace: Path,
    snapshot_id: str,
    kind: str,
    source: Path,
    model: str | None = None,
    mapping: str | None = None,
) -> dict[str, Any]:
    state = load_state(workspace)
    snapshot = _member(state, "snapshots", snapshot_id)
    dependencies = {
        name: _member(state, "attachments", aid)
        for name, aid in {"model": model, "mapping": mapping}.items()
        if aid is not None
    }
    payload = _read_bytes(source, HISTORY_LIMITS) if kind == "model" else read_document(source)
    attachment = build_attachment(kind, payload, snapshot, dependencies)
    result = publish_object(workspace, "attachments", attachment, validate_state)
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
    state = load_state(workspace)
    components = {
        name: _member(state, "attachments", aid)
        for name, aid in {
            "enrichment": enrichment,
            "model": model,
            "mapping": mapping,
            "comparison": comparison,
        }.items()
        if aid is not None
    }
    value = build_revision(
        _member(state, "snapshots", snapshot_id),
        components,
        read_document(semantics) if semantics is not None else None,
    )
    return {**publish_object(workspace, "analyses", value, validate_state), "analysis": value}


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
    state = load_state(workspace)
    value = _member(state, kind, identity)
    return baseline_summary(value, state) if kind == "baselines" else value


def propose_baseline(
    workspace: Path,
    scope_path: Path,
    revisions: list[str],
    kind: str = "evidence",
    model: str | None = None,
) -> dict[str, Any]:
    state = load_state(workspace)
    value = build_baseline(kind, revisions, read_document(scope_path), state, model)
    result = publish_object(workspace, "baselines", value, validate_state)
    return {**result, "baseline": baseline_summary(value, load_state(workspace))}


def record_review(
    workspace: Path,
    baseline_id: str,
    decision: str,
    reviewer: str,
    rationale: str,
    predecessor: str | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    state = load_state(workspace)
    value = build_review(baseline_id, decision, reviewer, rationale, state, predecessor, timestamp)
    result = publish_object(workspace, "reviews", value, validate_state)
    return {
        **result,
        "review": value,
        "baseline_status": validate_reviews(load_state(workspace))[baseline_id],
    }


def list_baselines(workspace: Path) -> dict[str, Any]:
    state = load_state(workspace)
    return {
        "baselines": [baseline_summary(b, state) for _, b in sorted(state["baselines"].items())]
    }


def list_history(workspace: Path) -> dict[str, Any]:
    state = load_state(workspace)
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
        "baselines": {k: v for k, v in sorted(validate_reviews(state).items())},
    }


def verify_lifecycle(workspace: Path) -> dict[str, Any]:
    result = verify_history(workspace, validate_state)
    state = load_state(workspace)
    statuses = list(validate_reviews(state).values())
    return {
        **result,
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
