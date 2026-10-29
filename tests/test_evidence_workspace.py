"""Independent frozen metadata and adversarial immutable-workspace expectations."""

import copy
import json
import os
from dataclasses import replace
from fractions import Fraction
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from otarchguard.diagnostics import ModelError
from otarchguard.evidence.cli import app
from otarchguard.evidence.observations import digest
from otarchguard.evidence.workspace import (
    EVIDENCE_LIMITS,
    add_snapshot,
    build_snapshot,
    initialize_workspace,
    list_snapshots,
    serialize,
    show_snapshot,
    validate_snapshot,
    verify_workspace,
)

FIXTURES = Path(__file__).parent / "fixtures/capture-contract-v2"


def observation(variant: str = "supported") -> dict[str, Any]:
    return json.loads((FIXTURES / variant / "observations.json").read_bytes())  # type: ignore[no-any-return]


def source(tmp_path: Path, variant: str = "supported") -> Path:
    path = tmp_path / (variant + ".json")
    path.write_bytes(serialize(observation(variant)))
    return path


def rehash(value: dict[str, Any]) -> dict[str, Any]:
    value["observations_sha256"] = digest(
        {k: v for k, v in value.items() if k != "observations_sha256"}
    )
    return value


def workspace(tmp_path: Path) -> Path:
    path = tmp_path / "evidence"
    initialize_workspace(path)
    return path


def test_snapshot_identity_is_compact_canonical_hash_without_local_path_or_clock() -> None:
    value = observation()
    snapshot = build_snapshot(value, "Fictional capture")
    expected = digest({k: v for k, v in snapshot.items() if k != "snapshot_id"})
    assert snapshot["snapshot_id"] == "snapshot-" + expected
    assert build_snapshot(value, "Fictional capture") == snapshot
    assert snapshot["capture_sha256"] == value["capture"]["sha256"]
    assert snapshot["observations_sha256"] == value["observations_sha256"]
    assert snapshot["observations"] == value
    assert not {"import_time", "path", "created_at", "approval"} & snapshot.keys()
    assert snapshot["collection"] == {
        "first_timestamp": "1700000000/1",
        "last_timestamp": "1700000000000009/1000000",
        "missing_timestamps": 0,
    }
    value["capture"]["packets"] = 0
    assert snapshot["observations"]["capture"]["packets"] != 0


def test_workspace_ingests_two_frozen_artifacts_without_copying_capture_bytes(
    tmp_path: Path,
) -> None:
    root = workspace(tmp_path)
    results = [
        add_snapshot(root, source(tmp_path, variant), variant)
        for variant in ("supported", "limited")
    ]
    assert [r["status"] for r in results] == ["ADDED", "ADDED"]
    listing = list_snapshots(root)
    assert len(listing["snapshots"]) == 2
    assert listing["snapshots"] == sorted(listing["snapshots"], key=lambda s: s["snapshot_id"])
    assert verify_workspace(root)["snapshots"] == 2
    for result in results:
        sid = result["snapshot"]["snapshot_id"]
        assert show_snapshot(root, sid)["snapshot_id"] == sid
    assert {p.name for p in root.iterdir()} == {"workspace.json", "snapshots"}
    assert all(p.suffix == ".json" for p in (root / "snapshots").iterdir())


def test_renamed_capture_metadata_is_explicit_duplicate_and_preserves_first_label(
    tmp_path: Path,
) -> None:
    root = workspace(tmp_path)
    original = source(tmp_path)
    added = add_snapshot(root, original, "first")
    renamed = tmp_path / "renamed.json"
    renamed.write_bytes(original.read_bytes())
    result = add_snapshot(root, renamed, "later")
    assert result["status"] == "DUPLICATE_CAPTURE"
    assert result["observations_match"] is True
    assert result["label_match"] is False
    assert result["existing"] == added["snapshot"]
    assert len(list_snapshots(root)["snapshots"]) == 1


def test_reprocessed_same_capture_is_not_silently_merged(tmp_path: Path) -> None:
    root = workspace(tmp_path)
    file = source(tmp_path)
    add_snapshot(root, file)
    value = observation()
    value["limitations"].append("Additional explicit input limitation")
    file.write_bytes(serialize(rehash(value)))
    result = add_snapshot(root, file)
    assert result["status"] == "DUPLICATE_CAPTURE"
    assert result["observations_match"] is False
    assert verify_workspace(root)["snapshots"] == 1


@pytest.mark.parametrize("version", [1, 3, True, "2", None])
def test_incompatible_observation_versions_never_migrate(version: object) -> None:
    value = observation()
    value["observation_version"] = version
    with pytest.raises(ModelError, match="Architecture processing failed"):
        build_snapshot(rehash(value))


@pytest.mark.parametrize("field", ["packets", "capture_records_truncated", "complete_file_scan"])
def test_rehashed_coverage_types_and_denominators_rejected(field: str) -> None:
    value = observation()
    value["coverage"][field] = True if field != "complete_file_scan" else 1
    with pytest.raises(ModelError):
        build_snapshot(rehash(value))


@pytest.mark.parametrize("mutation", ["host", "flow", "sample", "group", "timestamp"])
def test_rehashed_structural_tampering_cannot_become_a_snapshot(mutation: str) -> None:
    value = observation()
    if mutation == "host":
        value["hosts"][0]["observation_roles"] = ["owner_approved"]
    elif mutation == "flow":
        value["flows"][0]["destination_port"] += 1
    elif mutation == "sample":
        value["flows"][0]["samples"][0]["interface"] = 999
    elif mutation == "group":
        value["conversations"][0]["flow_ids"] = []
    else:
        value["flows"][0]["last_timestamp"] = "1/1"
    with pytest.raises(ModelError):
        build_snapshot(rehash(value))


@pytest.mark.parametrize("mutation", ["label", "digest", "capture", "collection", "version"])
def test_snapshot_tampering_is_rejected(mutation: str) -> None:
    snapshot = build_snapshot(observation())
    if mutation == "label":
        snapshot["label"] = "changed"
    elif mutation == "digest":
        snapshot["snapshot_id"] = "snapshot-" + "0" * 64
    elif mutation == "capture":
        snapshot["capture_sha256"] = "0" * 64
    elif mutation == "collection":
        snapshot["collection"]["missing_timestamps"] = 10
    else:
        snapshot["snapshot_version"] = True
    with pytest.raises(ModelError):
        validate_snapshot(snapshot)


def test_invalid_import_publishes_no_partial_snapshot(tmp_path: Path) -> None:
    root = workspace(tmp_path)
    bad = tmp_path / "bad.json"
    bad.write_text('{"observation_version":2,"observation_version":2}', encoding="utf-8")
    with pytest.raises(ModelError):
        add_snapshot(root, bad)
    assert list((root / "snapshots").iterdir()) == []


@pytest.mark.parametrize(
    "document", [b"[]", b'{"a":NaN}', b'{"a":Infinity}', b'{"a":1.5}', b"\xff"]
)
def test_invalid_json_is_controlled_and_does_not_publish(tmp_path: Path, document: bytes) -> None:
    root = workspace(tmp_path)
    bad = tmp_path / "bad.json"
    bad.write_bytes(document)
    with pytest.raises(ModelError):
        add_snapshot(root, bad)
    assert verify_workspace(root)["snapshots"] == 0


def test_workspace_bounds_fail_before_publication(tmp_path: Path) -> None:
    root = workspace(tmp_path)
    file = source(tmp_path)
    for limits in (
        replace(EVIDENCE_LIMITS, snapshot_bytes=32),
        replace(EVIDENCE_LIMITS, snapshots=0),
        replace(EVIDENCE_LIMITS, workspace_bytes=32),
        replace(EVIDENCE_LIMITS, nodes=10),
        replace(EVIDENCE_LIMITS, depth=2),
    ):
        with pytest.raises(ModelError):
            add_snapshot(root, file, limits=limits)
        assert list((root / "snapshots").iterdir()) == []


def test_existing_workspace_and_snapshot_files_never_overwritten(tmp_path: Path) -> None:
    root = workspace(tmp_path)
    marker = (root / "workspace.json").read_bytes()
    with pytest.raises(ModelError):
        initialize_workspace(root)
    assert (root / "workspace.json").read_bytes() == marker
    added = add_snapshot(root, source(tmp_path))
    file = root / "snapshots" / (added["snapshot"]["snapshot_id"] + ".json")
    original = file.read_bytes()
    assert add_snapshot(root, source(tmp_path))["status"] == "DUPLICATE_CAPTURE"
    assert file.read_bytes() == original


@pytest.mark.parametrize(
    "identifier", ["../outside", "snapshot-0", "SNAPSHOT-" + "0" * 64, "C:\\secret"]
)
def test_snapshot_identifiers_cannot_be_paths(tmp_path: Path, identifier: str) -> None:
    root = workspace(tmp_path)
    with pytest.raises(ModelError):
        show_snapshot(root, identifier)


def test_linked_workspace_and_input_rejected(tmp_path: Path) -> None:
    root = workspace(tmp_path)
    linked = tmp_path / "linked"
    try:
        os.symlink(root, linked, target_is_directory=True)
    except OSError:
        pytest.skip("Local account cannot create symlinks")
    with pytest.raises(ModelError):
        list_snapshots(linked)
    linked_file = tmp_path / "linked.json"
    os.symlink(source(tmp_path), linked_file)
    with pytest.raises(ModelError):
        add_snapshot(root, linked_file)


def test_interrupted_temporary_file_requires_explicit_review(tmp_path: Path) -> None:
    root = workspace(tmp_path)
    (root / "snapshots" / ".pending-interrupted.tmp").write_bytes(b"incomplete")
    with pytest.raises(ModelError) as error:
        verify_workspace(root)
    assert error.value.diagnostics[0].code == "EVIDENCE_INTERRUPTED"


def test_corrupted_snapshot_is_not_silently_ignored(tmp_path: Path) -> None:
    root = workspace(tmp_path)
    result = add_snapshot(root, source(tmp_path))
    file = root / "snapshots" / (result["snapshot"]["snapshot_id"] + ".json")
    value = json.loads(file.read_bytes())
    value["label"] = "tampered"
    file.write_bytes(serialize(value))
    with pytest.raises(ModelError):
        list_snapshots(root)


def test_unicode_cli_journey_and_structured_error(tmp_path: Path) -> None:
    runner = CliRunner()
    root = tmp_path / "evidence"
    assert runner.invoke(app, ["init", str(root)]).exit_code == 0
    result = runner.invoke(app, ["add", str(root), str(source(tmp_path)), "--label", "PerÃ­odo Î±"])
    assert result.exit_code == 0, result.output
    sid = json.loads(result.stdout)["snapshot"]["snapshot_id"]
    listing = runner.invoke(app, ["list", str(root)])
    assert json.loads(listing.stdout)["snapshots"][0]["label"] == "PerÃ­odo Î±"
    assert runner.invoke(app, ["show", str(root), sid]).exit_code == 0
    assert runner.invoke(app, ["verify", str(root)]).exit_code == 0
    error = runner.invoke(app, ["show", str(root), "../outside"])
    assert error.exit_code == 2
    assert json.loads(error.stderr)["code"] == "EVIDENCE_ID"


def test_unknown_classification_is_never_positively_interpreted() -> None:
    value = observation()
    value["flows"][0]["transport_evidence"] = "FUTURE_UNASSESSED"
    # A future code remains metadata; this slice produces no communication verdicts.
    snapshot = build_snapshot(rehash(value))
    assert snapshot["observations"]["flows"][0]["transport_evidence"] == "FUTURE_UNASSESSED"


def test_snapshot_copy_does_not_mutate_imported_observations() -> None:
    value = observation()
    previous = copy.deepcopy(value)
    build_snapshot(value)
    assert value == previous


def test_unknown_payload_extension_is_rejected_by_storage_policy() -> None:
    value = observation()
    value["raw_payload"] = "PRIVATE-PROCESS-DATA"
    with pytest.raises(ModelError):
        build_snapshot(rehash(value))


def test_oversized_rational_timestamp_fails_before_fraction_parsing() -> None:
    value = observation()
    value["flows"][0]["first_timestamp"] = "1" * 300 + "/1"
    with pytest.raises(ModelError):
        build_snapshot(rehash(value))


@pytest.mark.parametrize("name", ["CON", "plant.", "plant ", "plant:stream"])
def test_workspace_names_must_be_portable(tmp_path: Path, name: str) -> None:
    with pytest.raises(ModelError):
        initialize_workspace(tmp_path / name)


def test_option_diagnostic_belongs_to_evidence_namespace() -> None:
    error = CliRunner().invoke(app, ["unknown-command"])
    assert error.exit_code == 2
    diagnostic = json.loads(error.stderr)
    assert diagnostic["location"] == "$.evidence_options"
    assert "evidence --help" in diagnostic["message"]


@pytest.mark.parametrize("field", ["generator", "collection"])
def test_snapshot_numeric_boolean_substitution_does_not_bypass_integrity(field: str) -> None:
    snapshot = build_snapshot(observation())
    if field == "generator":
        snapshot["generator"]["snapshot_implementation"] = True
    else:
        snapshot["collection"]["missing_timestamps"] = False
    with pytest.raises(ModelError):
        validate_snapshot(snapshot)


def test_boolean_manifest_version_does_not_pass_integer_equality(tmp_path: Path) -> None:
    root = workspace(tmp_path)
    (root / "workspace.json").write_bytes(
        serialize({"workspace_version": True, "snapshot_version": 1})
    )
    with pytest.raises(ModelError):
        verify_workspace(root)


def test_maximum_supported_pcapng_precision_and_signed_offset_remain_exact() -> None:
    value = observation("limited")
    interface = value["capture"]["interfaces"][0]
    interface["timestamp_denominator"] = 10**127
    interface["timestamp_offset_seconds"] = 2**63 - 1
    for flow in value["flows"]:
        times = []
        for sample in flow["samples"] + flow["initiation_evidence"]:
            stamp = sample["timestamp"]
            assert stamp is not None
            stamp["ticks"] += 1
            stamp["denominator"] = interface["timestamp_denominator"]
            stamp["offset_seconds"] = interface["timestamp_offset_seconds"]
            times.append(Fraction(stamp["ticks"], stamp["denominator"]) + stamp["offset_seconds"])
        for name, result in (("first_timestamp", min(times)), ("last_timestamp", max(times))):
            flow[name] = f"{result.numerator}/{result.denominator}"
    by_id = {f["id"]: f for f in value["flows"]}
    for group in value["conversations"]:
        for name, operation in (("first_timestamp", min), ("last_timestamp", max)):
            result = operation(Fraction(by_id[fid][name]) for fid in group["flow_ids"])
            group[name] = f"{result.numerator}/{result.denominator}"
    snapshot = build_snapshot(rehash(value))
    assert len(snapshot["collection"]["first_timestamp"]) > 256
    validate_snapshot(snapshot)


@pytest.mark.parametrize(
    "mutation", ["group_boolean", "sample_resolution", "group_rational", "flow_bytes"]
)
def test_extended_summary_validation_rejects_rehashed_tampering(mutation: str) -> None:
    value = observation()
    if mutation == "group_boolean":
        value["conversations"][0]["linktypes"] = [True]
    elif mutation == "sample_resolution":
        value["flows"][0]["samples"][0]["timestamp"]["denominator"] = 1
    elif mutation == "group_rational":
        group = value["conversations"][0]
        stamp = Fraction(group["first_timestamp"])
        group["first_timestamp"] = f"{2 * stamp.numerator}/{2 * stamp.denominator}"
    else:
        value["flows"][0]["original_bytes"] = True
    with pytest.raises(ModelError):
        build_snapshot(rehash(value))
