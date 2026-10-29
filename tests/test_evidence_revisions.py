"""Independent canonical envelopes and exact analytical revision requirements."""

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from test_evidence_attachments import captured, fixture

from otarchguard.diagnostics import ModelError
from otarchguard.evidence.attachments import build_attachment
from otarchguard.evidence.revisions import (
    build_revision,
    build_semantics,
    implementation_identities,
    validate_revision,
)
from otarchguard.evidence.workspace import build_snapshot
from tools.capture_workloads import plant_model


def independent_sha(domain: str, value: object) -> str:
    encoded = json.dumps(
        {"domain": domain, "value": value}, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def rehash(value: dict[str, Any]) -> None:
    value["analysis_id"] = "analysis-" + independent_sha(
        "otarchguard.analysis", {k: v for k, v in value.items() if k != "analysis_id"}
    )


def test_independent_canonical_fixture_defines_domains_unicode_and_nulls() -> None:
    # Hand-specified bytes intentionally do not call any production canonicalizer.
    canonical = b'{"domain":"otarchguard.analysis","value":{"a":null,"z":"\\u00f1"}}'
    expected = hashlib.sha256(canonical).hexdigest()
    assert independent_sha("otarchguard.analysis", {"z": "ñ", "a": None}) == expected
    assert expected == "ecb496b5aacca75be73b5fde02cfbdfcf6faf843d7609d9f9c4ce20d058becef"


def test_observation_only_revision_explicit_absence_and_independent_identity() -> None:
    snapshot = build_snapshot(fixture("observations"))
    revision = build_revision(snapshot)
    assert revision["analysis_id"] == "analysis-" + independent_sha(
        "otarchguard.analysis", {k: v for k, v in revision.items() if k != "analysis_id"}
    )
    assert revision["components"] == {
        "enrichment": None,
        "model": None,
        "mapping": None,
        "comparison": None,
        "policy": None,
    }
    assert revision["producer_semantics_sha256"] == independent_sha(
        "otarchguard.producer-semantics.v1", revision["producer_semantics"]
    )
    assert build_revision(snapshot) == revision
    validate_revision(revision, snapshot)


def test_snapshot_labels_do_not_contaminate_analytical_identity() -> None:
    observations = fixture("observations")
    first = build_snapshot(observations, "first label")
    second = build_snapshot(observations, "another label")
    assert first["snapshot_id"] != second["snapshot_id"]
    assert build_revision(first) == build_revision(second)


def test_semantics_bind_actual_sources_without_platform_path_clock() -> None:
    snapshot = build_snapshot(fixture("observations"))
    semantics = build_semantics(snapshot)
    sources = implementation_identities()
    assert {
        "evidence/attachments.py",
        "evidence/revisions.py",
        "capture/parser.py",
        "reachability.py",
    } <= set(sources)
    package = Path(__file__).parent.parent / "src/otarchguard"
    # Installed distributions are audited separately; source-checkout expectations
    # compare only when the running implementation is this source inventory.
    assert all(len(digest) == 64 for digest in sources.values())
    assert (
        hashlib.sha256((package / "capture/parser.py").read_bytes()).hexdigest()
        == sources["capture/parser.py"]
    )
    assert semantics["implementation_sha256"] == sources
    assert semantics["original_capture_parameters"] is None
    assert semantics["native_engine_version"] == "1.3.0"
    assert not {"os", "python", "timestamp", "path", "duration"} & semantics.keys()


def test_one_capture_multiple_enrichment_and_configuration_revisions(tmp_path: Path) -> None:
    snapshot, enrichment = captured(tmp_path)
    attached = build_attachment("enrichment", enrichment, snapshot)
    selected = {"enrichment": attached}
    a1 = build_revision(snapshot)
    a2 = build_revision(snapshot, selected)
    a3 = build_revision(
        snapshot, selected, build_semantics(snapshot, selected, require_complete_scan=True)
    )
    assert len({a1["analysis_id"], a2["analysis_id"], a3["analysis_id"]}) == 3
    assert {a["capture_sha256"] for a in (a1, a2, a3)} == {snapshot["capture_sha256"]}
    assert a2["producer_semantics"]["decoder_version"] == 2
    validate_revision(a3, snapshot, selected)


def test_model_mapping_and_comparison_revisions_have_exact_components() -> None:
    snapshot = build_snapshot(fixture("observations"))
    model = build_attachment("model", plant_model(), snapshot)
    mapping = build_attachment("mapping", fixture("mapping"), snapshot, {"model": model})
    comparison = build_attachment(
        "comparison", fixture("comparison"), snapshot, {"model": model, "mapping": mapping}
    )
    components = {"model": model, "mapping": mapping, "comparison": comparison}
    revision = build_revision(snapshot, components)
    for kind, attachment in components.items():
        assert revision["components"][kind] == {
            "attachment_id": attachment["attachment_id"],
            "sha256": attachment["component_sha256"],
        }
    validate_revision(revision, snapshot, components)


@pytest.mark.parametrize(
    "mutation",
    [
        "capture",
        "observations",
        "snapshot",
        "component",
        "semantics",
        "source",
        "limits",
        "options",
        "extra",
        "version",
    ],
)
def test_rehashed_revision_cannot_change_validated_meaning(mutation: str) -> None:
    snapshot = build_snapshot(fixture("observations"))
    revision = build_revision(snapshot)
    if mutation in {"capture", "observations"}:
        revision[mutation + "_sha256"] = "f" * 64
    elif mutation == "snapshot":
        revision["snapshot_id"] = "snapshot-" + "e" * 64
    elif mutation == "component":
        revision["components"]["model"] = {
            "attachment_id": "attachment-" + "a" * 64,
            "sha256": "b" * 64,
        }
    elif mutation == "semantics":
        revision["producer_semantics"]["decoder_version"] = 99
    elif mutation == "source":
        revision["producer_semantics"]["implementation_sha256"]["reachability.py"] = "c" * 64
    elif mutation == "limits":
        revision["producer_semantics"]["capture_validation_limits"]["packet_bytes"] += 1
    elif mutation == "options":
        revision["producer_semantics"]["analysis_options"]["arbitrary_mode"] = "approve"
    elif mutation == "extra":
        revision["approved"] = True
    else:
        revision["analysis_version"] = True
    revision["producer_semantics_sha256"] = independent_sha(
        "otarchguard.producer-semantics.v1", revision["producer_semantics"]
    )
    rehash(revision)
    with pytest.raises(ModelError):
        validate_revision(revision, snapshot)


@pytest.mark.parametrize("option", ["require_complete_scan", "require_reviewed_mapping"])
@pytest.mark.parametrize("bad", [1, "true", None, [], {}])
def test_semantics_rejects_coerced_options(option: str, bad: object) -> None:
    snapshot = build_snapshot(fixture("observations"))
    semantics = build_semantics(snapshot)
    semantics["analysis_options"][option] = bad
    with pytest.raises(ModelError):
        build_revision(snapshot, semantics=semantics)


def test_required_reviewed_mapping_is_enforced_and_missing_is_not_null_equivalent() -> None:
    snapshot = build_snapshot(fixture("observations"))
    with pytest.raises(ModelError):
        build_revision(snapshot, semantics=build_semantics(snapshot, require_reviewed_mapping=True))
    model = build_attachment("model", plant_model(), snapshot)
    mapping = build_attachment("mapping", fixture("mapping"), snapshot, {"model": model})
    selected = {"model": model, "mapping": mapping}
    with pytest.raises(ModelError):
        build_revision(
            snapshot, selected, build_semantics(snapshot, selected, require_reviewed_mapping=True)
        )


def test_incomplete_scan_requirement_is_enforced() -> None:
    snapshot = build_snapshot(fixture("observations"))
    incomplete = copy.deepcopy(snapshot["observations"])
    incomplete["coverage"]["complete_file_scan"] = False
    incomplete["observations_sha256"] = hashlib.sha256(
        json.dumps(
            {k: v for k, v in incomplete.items() if k != "observations_sha256"},
            sort_keys=True,
            ensure_ascii=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    other = build_snapshot(incomplete)
    assert build_revision(other)
    with pytest.raises(ModelError):
        build_revision(other, semantics=build_semantics(other, require_complete_scan=True))


def test_revision_uses_deep_copies_for_inputs_and_semantics() -> None:
    snapshot = build_snapshot(fixture("observations"))
    semantics = build_semantics(snapshot)
    revision = build_revision(snapshot, semantics=semantics)
    semantics["analysis_options"]["require_complete_scan"] = True
    assert revision["producer_semantics"]["analysis_options"]["require_complete_scan"] is False
