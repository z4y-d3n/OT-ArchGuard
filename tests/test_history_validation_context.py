"""Differential contracts and hostile reuse cases for operation-private validation."""

import copy
import hashlib
import json
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from test_evidence_attachments import captured, fixture

from otarchguard.api import validate_bytes
from otarchguard.capture.reconciliation import compare_capture
from otarchguard.diagnostics import ModelError, fail
from otarchguard.evidence import validation
from otarchguard.evidence.attachments import build_attachment, validate_attachment
from otarchguard.evidence.history import (
    HISTORY_LIMITS,
    _read_image,
    initialize_history,
    publish_object,
)
from otarchguard.evidence.reviews import (
    build_baseline,
    build_review,
    validate_baseline,
    validate_reviews,
)
from otarchguard.evidence.revisions import build_revision, build_semantics, validate_revision
from otarchguard.evidence.validation import _ValidationContext
from otarchguard.evidence.workspace import build_snapshot
from tools.capture_workloads import plant_model


def state() -> dict[str, Any]:
    snapshot = build_snapshot(fixture("observations"))
    model = build_attachment("model", plant_model(), snapshot)
    mapping = build_attachment("mapping", fixture("mapping"), snapshot, {"model": model})
    comparison = build_attachment(
        "comparison", fixture("comparison"), snapshot, {"model": model, "mapping": mapping}
    )
    selected = {"model": model, "mapping": mapping, "comparison": comparison}
    plain = build_revision(snapshot)
    full = build_revision(snapshot, selected)
    return {
        "snapshots": {snapshot["snapshot_id"]: snapshot},
        "attachments": {a["attachment_id"]: a for a in selected.values()},
        "analyses": {a["analysis_id"]: a for a in (plain, full)},
        "baselines": {},
        "reviews": {},
    }


def original_validation(s: dict[str, Any]) -> None:
    """Pre-optimization graph order using the unchanged standalone contracts."""
    try:
        snapshots = {v["capture_sha256"]: v for v in s["snapshots"].values()}
        for _, attachment in sorted(s["attachments"].items()):
            snapshot = snapshots.get(attachment.get("capture_sha256"))
            if snapshot is None:
                fail("EVIDENCE_ATTACHMENT", "$", "Unavailable collection")
            dependencies = {
                k: member(s, "attachments", aid)
                for k, aid in attachment.get("dependencies", {}).items()
                if aid is not None
            }
            validate_attachment(attachment, snapshot, dependencies)
        for _, analysis in sorted(s["analyses"].items()):
            snapshot = snapshots.get(analysis.get("capture_sha256"))
            if snapshot is None or snapshot["observations_sha256"] != analysis.get(
                "observations_sha256"
            ):
                fail("EVIDENCE_REVISION", "$", "Unavailable observations")
            components = {
                k: member(s, "attachments", a["attachment_id"])
                for k, a in analysis.get("components", {}).items()
                if a is not None and k != "policy"
            }
            validate_revision(analysis, snapshot, components)
        for baseline in s["baselines"].values():
            validate_baseline(baseline, s)
        validate_reviews(s)
    except (KeyError, TypeError, ValueError, AttributeError, IndexError, RecursionError):
        fail("EVIDENCE_GRAPH", "$", "Malformed graph")


def member(s: dict[str, Any], kind: str, aid: str) -> dict[str, Any]:
    result = s[kind].get(aid)
    if result is None:
        fail("EVIDENCE_NOT_FOUND", "$", "Unavailable dependency")
    return result  # type: ignore[no-any-return]


def code(operation: Callable[[], Any]) -> str:
    with pytest.raises(ModelError) as error:
        operation()
    return error.value.diagnostics[0].code


def seal(value: dict[str, Any], kind: str) -> None:
    body = {k: v for k, v in value.items() if k != kind + "_id"}
    raw = json.dumps(
        {"domain": "otarchguard." + kind, "value": body},
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode()
    value[kind + "_id"] = kind + "-" + hashlib.sha256(raw).hexdigest()


def scope() -> dict[str, Any]:
    return {
        "environment": "Fictional context test",
        "purpose": "Exact dependency validation",
        "coverage": "Unknown outside the fictional selected packets",
        "uncertainties": [],
        "vantage_points": [],
        "protocols": [],
    }


def test_exact_stored_components_and_revisions_match_original_contracts() -> None:
    s = state()
    original_validation(s)
    context = _ValidationContext(s)
    context.validate()
    assert context._state == s
    assert context._counts == {
        "snapshots": 1,
        "attachments": 3,
        "analyses": 2,
        "baselines": 0,
        "native_models": 1,
        "mappings": 1,
        "comparisons": 1,
    }
    assert context.statuses == {}
    before = dict(context._counts)
    context.validate()
    assert context._counts == before


def test_native_model_is_validated_once_and_comparison_is_replayed_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    s = state()
    calls = {"model": 0, "comparison": 0}
    native, compare = validate_bytes, compare_capture

    def counted_native(data: bytes) -> Any:
        calls["model"] += 1
        return native(data)

    def counted_compare(*args: Any, **kwargs: Any) -> Any:
        calls["comparison"] += 1
        return compare(*args, **kwargs)

    monkeypatch.setattr(validation, "validate_bytes", counted_native)
    monkeypatch.setattr(validation, "compare_capture", counted_compare)
    for _ in range(2):
        context = _ValidationContext(s)
        context.validate()
        context.validate()
    # A second independent context repeats every required native check.
    assert calls == {"model": 2, "comparison": 2}


def test_model_cache_uses_actual_content_and_is_not_capture_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    s = state()
    s["analyses"] = {}
    s["attachments"] = {k: a for k, a in s["attachments"].items() if a["kind"] == "model"}
    other = build_snapshot(
        json.loads(
            (
                Path(__file__).parent / "fixtures/capture-contract-v2/limited/observations.json"
            ).read_bytes()
        )
    )
    second = build_attachment("model", plant_model(), other)
    s["snapshots"][other["snapshot_id"]] = other
    s["attachments"][second["attachment_id"]] = second
    native = validate_bytes
    count = 0

    def counted(data: bytes) -> Any:
        nonlocal count
        count += 1
        return native(data)

    monkeypatch.setattr(validation, "validate_bytes", counted)
    context = _ValidationContext(s)
    context.validate()
    assert count == 1
    assert context._counts["attachments"] == 2
    assert context._counts["snapshots"] == 2


def test_caller_alias_changes_cannot_modify_a_validation_context() -> None:
    s = state()
    context = _ValidationContext(s)
    next(iter(s["attachments"].values()))["payload"] = {"arbitrary": "mutated after acquisition"}
    s["analyses"].clear()
    context.validate()
    assert len(context._state["analyses"]) == 2
    assert context._counts["native_models"] == 1
    assert code(lambda: _ValidationContext(s).validate()) == code(lambda: original_validation(s))


@pytest.mark.parametrize(
    "selected", [(), ("model",), ("model", "mapping"), ("model", "mapping", "comparison")]
)
def test_new_revision_is_byte_identical_to_frozen_builder(selected: tuple[str, ...]) -> None:
    s = state()
    context = _ValidationContext(s)
    snapshot_id, snapshot = next(iter(s["snapshots"].items()))
    attachments = {a["kind"]: a for a in s["attachments"].values() if a["kind"] in selected}
    actual = context.build_revision(
        snapshot_id, {k: a["attachment_id"] for k, a in attachments.items()}
    )
    assert actual == build_revision(snapshot, attachments)


@pytest.mark.parametrize("kind", ["model", "mapping", "comparison"])
def test_new_attachment_is_byte_identical_to_frozen_builder(kind: str) -> None:
    s = state()
    context = _ValidationContext(s)
    snapshot_id, snapshot = next(iter(s["snapshots"].items()))
    attachments = {a["kind"]: a for a in s["attachments"].values()}
    dependencies = {k: a for k, a in attachments.items() if k in {"model", "mapping"}}
    payload = plant_model() if kind == "model" else fixture(kind)
    actual = context.build_attachment(
        kind,
        payload,
        snapshot_id,
        dependencies["model"]["attachment_id"],
        dependencies["mapping"]["attachment_id"],
    )
    assert actual == build_attachment(kind, payload, snapshot, dependencies)


def test_enrichment_and_strict_options_match_frozen_builders(tmp_path: Path) -> None:
    snapshot, enrichment = captured(tmp_path)
    s = {
        "snapshots": {snapshot["snapshot_id"]: snapshot},
        "attachments": {},
        "analyses": {},
        "baselines": {},
        "reviews": {},
    }
    context = _ValidationContext(s)
    attached = context.build_attachment("enrichment", enrichment, snapshot["snapshot_id"])
    assert attached == build_attachment("enrichment", enrichment, snapshot)
    context.add("attachments", attached)
    semantics = build_semantics(snapshot, {"enrichment": attached}, require_complete_scan=True)
    actual = context.build_revision(
        snapshot["snapshot_id"], {"enrichment": attached["attachment_id"]}, semantics
    )
    assert actual == build_revision(snapshot, {"enrichment": attached}, semantics)


@pytest.mark.parametrize(
    "mutation", ["version", "field", "capture", "digest", "payload", "dependencies", "missing"]
)
def test_rehashed_unreferenced_attachment_rejection_matches_original(mutation: str) -> None:
    s = state()
    model = next(a for a in s["attachments"].values() if a["kind"] == "model")
    s["attachments"] = {model["attachment_id"]: model}
    s["analyses"] = {}
    if mutation == "version":
        model["attachment_version"] = True
    elif mutation == "field":
        model["owner_approved"] = True
    elif mutation == "capture":
        model["capture_sha256"] = "f" * 64
    elif mutation == "digest":
        model["component_sha256"] = "f" * 64
    elif mutation == "payload":
        model["payload"]["assets"][0]["id"] = "UNKNOWN"
    elif mutation == "dependencies":
        model["dependencies"] = []
    else:
        model["dependencies"]["model"] = "attachment-" + "f" * 64
    seal(model, "attachment")
    s["attachments"] = {model["attachment_id"]: model}
    assert code(lambda: _ValidationContext(s).validate()) == code(lambda: original_validation(s))


@pytest.mark.parametrize(
    "mutation",
    ["version", "field", "observations", "component", "options", "source", "limits", "shape"],
)
def test_rehashed_revision_rejection_matches_original(mutation: str) -> None:
    s = state()
    plain = next(a for a in s["analyses"].values() if a["components"]["model"] is None)
    if mutation == "version":
        plain["analysis_version"] = True
    elif mutation == "field":
        plain["owner_approved"] = True
    elif mutation == "observations":
        plain["observations_sha256"] = "f" * 64
    elif mutation == "component":
        plain["components"]["model"] = {
            "attachment_id": "attachment-" + "f" * 64,
            "sha256": "f" * 64,
        }
    elif mutation == "options":
        plain["producer_semantics"]["analysis_options"]["require_complete_scan"] = 1
    elif mutation == "source":
        plain["producer_semantics"]["implementation_sha256"]["reachability.py"] = "f" * 64
    elif mutation == "limits":
        plain["producer_semantics"]["capture_validation_limits"]["packets"] += 1
    else:
        plain["components"] = []
    seal(plain, "analysis")
    s["analyses"] = {plain["analysis_id"]: plain}
    assert code(lambda: _ValidationContext(s).validate()) == code(lambda: original_validation(s))


def test_rejected_initial_validation_poison_prevents_retained_partial_success() -> None:
    s = state()
    model = next(a for a in s["attachments"].values() if a["kind"] == "model")
    model["component_sha256"] = "f" * 64
    context = _ValidationContext(s)
    code(context.validate)
    assert context._failed and not context._complete
    assert code(context.validate) == "EVIDENCE_GRAPH"
    assert code(lambda: context.statuses) == "EVIDENCE_GRAPH"


def test_adding_exact_object_is_idempotent_but_modified_claimed_id_never_is() -> None:
    s = state()
    context = _ValidationContext(s)
    model = next(a for a in s["attachments"].values() if a["kind"] == "model")
    context.add("attachments", model)
    count = dict(context._counts)
    context.add("attachments", copy.deepcopy(model))
    assert context._counts == count
    altered = copy.deepcopy(model)
    altered["payload"]["revision"] = "mutated"
    assert code(lambda: context.add("attachments", altered)) == "EVIDENCE_EXISTS"


def test_image_ownership_and_addition_are_copy_on_write(tmp_path: Path) -> None:
    workspace = tmp_path / "history"
    initialize_history(workspace)
    snapshot = build_snapshot(fixture("observations"))
    publish_object(workspace, "snapshots", snapshot)
    image = _read_image(workspace)
    context = _ValidationContext._from_image(image)
    assert context._state is image.state
    revision = context.build_revision(snapshot["snapshot_id"])
    context.add("analyses", revision)
    assert image.state["analyses"] == {}
    assert context._state["analyses"] == {revision["analysis_id"]: revision}
    revision["components"]["policy"] = "outside mutation"
    assert next(iter(context._state["analyses"].values()))["components"]["policy"] is None


def test_review_conflict_poison_and_new_revision_never_acquires_old_authority() -> None:
    s = state()
    analyses = list(s["analyses"])
    first = build_baseline("evidence", [analyses[0]], scope(), s)
    second = build_baseline("evidence", [analyses[1]], scope(), s)
    s["baselines"] = {b["baseline_id"]: b for b in (first, second)}
    approved = build_review(first["baseline_id"], "approve", "Fictional A", "Synthetic only", s)
    s["reviews"][approved["review_id"]] = approved
    context = _ValidationContext(s)
    context.validate()
    assert context.statuses == {first["baseline_id"]: "APPROVED", second["baseline_id"]: "PROPOSED"}
    independent = {**s, "reviews": {}}
    conflicting = build_review(
        second["baseline_id"], "approve", "Fictional B", "Conflicting assertion", independent
    )
    assert code(lambda: context.add("reviews", conflicting)) == "EVIDENCE_REVIEW"
    assert context._state == s
    assert code(context.validate) == "EVIDENCE_GRAPH"
    fresh = _ValidationContext(s)
    fresh.validate()
    assert fresh.statuses[second["baseline_id"]] == "PROPOSED"


def test_mapping_under_another_valid_model_preserves_native_rejection_diagnostic() -> None:
    s = state()
    snapshot_id, snapshot = next(iter(s["snapshots"].items()))
    different = plant_model()
    different["revision"] = "different model"
    model = build_attachment("model", different, snapshot)
    s["attachments"][model["attachment_id"]] = model
    mapping = next(a for a in s["attachments"].values() if a["kind"] == "mapping")
    context = _ValidationContext(s)
    actual = code(
        lambda: context.build_revision(
            snapshot_id, {"model": model["attachment_id"], "mapping": mapping["attachment_id"]}
        )
    )
    expected = code(lambda: build_revision(snapshot, {"model": model, "mapping": mapping}))
    assert actual == expected


def test_comparison_cannot_reuse_mapping_from_another_cached_model() -> None:
    s = state()
    snapshot_id, snapshot = next(iter(s["snapshots"].items()))
    different = plant_model()
    different["revision"] = "different model"
    model = build_attachment("model", different, snapshot)
    s["attachments"][model["attachment_id"]] = model
    mapping = next(a for a in s["attachments"].values() if a["kind"] == "mapping")
    context = _ValidationContext(s)
    context.validate()
    actual = code(
        lambda: context.build_attachment(
            "comparison",
            fixture("comparison"),
            snapshot_id,
            model["attachment_id"],
            mapping["attachment_id"],
        )
    )
    expected = code(
        lambda: build_attachment(
            "comparison",
            fixture("comparison"),
            snapshot,
            {"model": model, "mapping": mapping},
        )
    )
    assert actual == expected


def test_cache_capacity_cannot_reject_idempotent_yaml_presentation_at_object_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    s = state()
    model = next(a for a in s["attachments"].values() if a["kind"] == "model")
    s["attachments"] = {model["attachment_id"]: model}
    s["analyses"] = {}
    monkeypatch.setattr(validation, "HISTORY_LIMITS", replace(HISTORY_LIMITS, attachments=1))
    context = _ValidationContext(s)
    context.validate()
    snapshot_id = next(iter(s["snapshots"]))
    variant = json.dumps(plant_model()).encode() + b"\n# different source presentation\n"
    result = context.build_attachment("model", variant, snapshot_id)
    assert result == model
    assert len(context._native_inputs) == len(context._native_models) == 1
    context.add("attachments", result)
    assert len(context._state["attachments"]) == 1


@pytest.mark.parametrize("mutation", ["cycle", "depth", "nodes", "text", "object_bytes", "objects"])
def test_direct_caller_input_is_bounded_before_any_deepcopy(
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    s: dict[str, Any] = {
        "snapshots": {},
        "attachments": {},
        "analyses": {},
        "baselines": {},
        "reviews": {},
    }
    limits = HISTORY_LIMITS
    value: dict[str, Any] = {}
    if mutation == "cycle":
        value["cycle"] = value
    elif mutation == "depth":
        value = {"value": [[[]]]}
        limits = replace(limits, depth=2)
    elif mutation == "nodes":
        value = {"value": [None] * 8}
        limits = replace(limits, nodes=4)
    elif mutation == "text":
        value = {"value": "x" * 4097}
    elif mutation == "object_bytes":
        value = {"value": "large"}
        limits = replace(limits, object_bytes=4)
    else:
        limits = replace(limits, attachments=0)
    s["attachments"]["attachment-" + "a" * 64] = value
    monkeypatch.setattr(validation, "HISTORY_LIMITS", limits)
    copies = 0

    def forbidden_copy(*args: Any, **kwargs: Any) -> Any:
        nonlocal copies
        copies += 1
        raise AssertionError("Copy must not run before bounds reject hostile input")

    monkeypatch.setattr(copy, "deepcopy", forbidden_copy)
    assert code(lambda: _ValidationContext(s)) in {"EVIDENCE_GRAPH", "LIMIT_EXCEEDED"}
    assert copies == 0


def test_unused_outer_data_is_not_copied_and_expanded_aliases_are_charged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    s: dict[str, Any] = {
        "snapshots": {},
        "attachments": {},
        "analyses": {},
        "baselines": {},
        "reviews": {},
    }
    cycle: list[Any] = []
    cycle.append(cycle)
    s["irrelevant_outer_key"] = cycle
    context = _ValidationContext(s)
    context.validate()
    assert "irrelevant_outer_key" not in context._state
    alias = {"text": "x" * 64}
    s["attachments"] = {"attachment-" + "a" * 64: {"aliases": [alias] * 16}}
    monkeypatch.setattr(validation, "HISTORY_LIMITS", replace(HISTORY_LIMITS, object_bytes=512))
    assert code(lambda: _ValidationContext(s)) == "LIMIT_EXCEEDED"


def test_direct_constructor_charges_workspace_bytes_across_objects_not_single_object(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    s: dict[str, Any] = {
        "snapshots": {},
        "attachments": {},
        "analyses": {},
        "baselines": {},
        "reviews": {},
    }
    s["attachments"] = {
        "attachment-" + "a" * 64: {"text": "x" * 48},
        "attachment-" + "b" * 64: {"text": "y" * 48},
    }
    monkeypatch.setattr(
        validation, "HISTORY_LIMITS", replace(HISTORY_LIMITS, object_bytes=64, workspace_bytes=128)
    )
    # Both subdocuments fit independently; a whole-state 64-byte cap would fail.
    context = _ValidationContext(s)
    assert len(context._state["attachments"]) == 2
    monkeypatch.setattr(
        validation, "HISTORY_LIMITS", replace(HISTORY_LIMITS, object_bytes=64, workspace_bytes=100)
    )
    assert code(lambda: _ValidationContext(s)) == "LIMIT_EXCEEDED"
