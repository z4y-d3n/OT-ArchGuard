"""Independent acceptance of benchmark pairing, outcomes and fixture identity."""

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from benchmarks.history_performance import (
    _relocate,
    assert_expected_outcome,
    compare_samples,
    summarize,
)
from tools.history_performance_worker import (
    canonical,
    console_arguments,
    file_manifest,
    identity,
    measure,
    prepare_case,
    prepare_fixture,
    run_operation,
)


def sample(elapsed: int) -> dict[str, Any]:
    return {
        "mode": "timing",
        "elapsed_ns": elapsed,
        "cpu_ns": elapsed - 1,
        "python_peak_bytes": None,
        "rss_bytes": 128,
        "input_identity": "one exact workload",
        "outcome_sha256": "same result",
        "artifact_manifest_sha256": "same immutable files",
    }


def test_measurement_summary_uses_all_trials_and_reports_outlier_spread() -> None:
    result = summarize([9, 1, 2, 3, 1000])
    assert result == {
        "median": 3.0,
        "minimum": 1.0,
        "maximum": 1000.0,
        "spread": 999.0,
        "median_absolute_deviation": 2.0,
    }
    paired = compare_samples(
        [sample(n) for n in [9, 1, 2, 3, 1000]], [sample(n) for n in [3, 1, 1, 2, 20]]
    )
    assert paired["speedup"] == 1.5
    assert paired["trials_each"] == 5


@pytest.mark.parametrize(
    "field",
    ["input_identity", "outcome_sha256", "artifact_manifest_sha256", "exit_code", "stderr_sha256"],
)
def test_favorable_timing_never_hides_differential_mismatch(field: str) -> None:
    old, new = sample(100), sample(1)
    new[field] = "changed"
    with pytest.raises(ValueError):
        compare_samples([old], [new])


def test_empty_or_unequal_trials_are_not_an_acceptable_comparison() -> None:
    with pytest.raises(ValueError):
        summarize([])
    for old, new in (([], []), ([sample(1)], []), ([sample(1)], [sample(1), sample(2)])):
        with pytest.raises(ValueError):
            compare_samples(old, new)


def test_matching_failures_cannot_be_reported_as_successful_workflow_acceleration() -> None:
    measured = {
        "mode": "timing",
        "outcome": {"exit_code": 2, "diagnostics": [{"code": "EVIDENCE_REVIEW"}]},
    }
    with pytest.raises(ValueError, match="unexpectedly failed"):
        assert_expected_outcome("approve", measured)
    assert_expected_outcome("conflict_approval", measured)


def test_matching_successes_cannot_hide_a_failed_attack_rejection() -> None:
    measured = {"mode": "timing", "outcome": {"exit_code": 0, "result": {}}}
    with pytest.raises(ValueError, match="required rejection"):
        assert_expected_outcome("tampered_object", measured)


def test_case_relocation_changes_only_its_owned_absolute_path_prefix(tmp_path: Path) -> None:
    before, after = tmp_path / "case", tmp_path / "trial"
    value = {
        "workspace": str(before / "history"),
        "nested": [str(before / "scope.json")],
        "label": str(tmp_path / "case-sibling"),
    }
    result = _relocate(value, before, after)
    assert result["workspace"] == str(after / "history")
    assert result["nested"] == [str(after / "scope.json")]
    assert result["label"] == value["label"]
    assert value["workspace"] == str(before / "history")


def test_native_fixture_generation_and_copied_requests_preserve_exact_inputs(
    tmp_path: Path,
) -> None:
    fixture = tmp_path / "fixture"
    receipt = prepare_fixture(fixture, 2, 2, 2)
    assert receipt["verification"]["physical_collections"] == 2
    assert receipt["verification"]["analyses"] == 4
    assert receipt["verification"]["reviews"] == 2
    assert receipt["workspace_manifest_sha256"] == identity(file_manifest(fixture / "history"))
    before = file_manifest(fixture / "history")
    left = prepare_case(fixture, tmp_path / "left", "verify")
    right = prepare_case(fixture, tmp_path / "right", "verify")
    assert left["input_identity"] == right["input_identity"]
    assert run_operation(left) == run_operation(right)
    assert file_manifest(fixture / "history") == before


def test_a_rehashed_attack_is_not_treated_as_a_faster_success(tmp_path: Path) -> None:
    fixture = tmp_path / "fixture"
    prepare_fixture(fixture, 1)
    request = prepare_case(fixture, tmp_path / "attack", "tampered_object")
    outcome = run_operation(request)
    assert outcome["exit_code"] == 2
    assert outcome["diagnostics"][0]["code"] == "EVIDENCE_REVISION"


@pytest.mark.parametrize(
    "operation", ["corrupt_json", "unsupported_version", "resource_exhaustion", "invalid_reference"]
)
def test_rejection_workloads_return_diagnostics_not_success(operation: str, tmp_path: Path) -> None:
    fixture = tmp_path / "fixture"
    prepare_fixture(fixture, 1)
    request = prepare_case(fixture, tmp_path / "case", operation)
    result = measure(request, "timing")
    assert result["outcome"]["exit_code"] == 2
    assert result["mode"] == "timing"
    assert result["python_peak_bytes"] is None
    assert result["counts"] == {}


def test_warmup_cannot_preapply_a_mutating_action(tmp_path: Path) -> None:
    fixture = tmp_path / "fixture"
    prepare_fixture(fixture, 1)
    request = prepare_case(fixture, tmp_path / "case", "approve")
    request["warmups"] = 1
    before = file_manifest(Path(request["workspace"]))
    with pytest.raises(ValueError, match="Mutating operations"):
        measure(request, "timing")
    assert file_manifest(Path(request["workspace"])) == before


def test_console_commands_keep_explicit_review_intent_and_exact_predecessor() -> None:
    request = {
        "workspace": "history",
        "operation": "supersede",
        "baseline_id": "baseline-exact",
        "predecessor": "review-exact",
    }
    command = console_arguments(request)
    assert command[:4] == ["evidence", "baseline", "supersede", "history"]
    assert command[4] == "baseline-exact"
    assert command[-2:] == ["--predecessor", "review-exact"]
    assert "--reviewer" in command and "--rationale" in command


@pytest.mark.parametrize(
    "operation,parameter",
    [
        ("import_attachment", "source"),
        ("create_revision", "semantics"),
        ("propose_baseline", "scope"),
    ],
)
def test_auxiliary_input_changes_invalidate_trial_pairing_before_measurement(
    operation: str,
    parameter: str,
    tmp_path: Path,
) -> None:
    fixture = tmp_path / "fixture"
    prepare_fixture(fixture, 1)
    request = prepare_case(fixture, tmp_path / "case", operation)
    auxiliary = Path(request[parameter])
    auxiliary.write_bytes(auxiliary.read_bytes() + b" ")
    with pytest.raises(ValueError, match="Trial inputs changed"):
        measure(request, "timing")


def test_migration_identity_binds_exact_source_bytes_not_absent_destination(tmp_path: Path) -> None:
    fixture = tmp_path / "fixture"
    prepare_fixture(fixture, 1)
    request = prepare_case(fixture, tmp_path / "case", "migrate")
    assert request["input_file_sha256"]["workspace/presence"] == "absent"
    assert any(name.startswith("source/snapshots/") for name in request["input_file_sha256"])
    source = Path(request["source"]) / "workspace.json"
    source.write_bytes(source.read_bytes() + b" ")
    with pytest.raises(ValueError, match="Trial inputs changed"):
        measure(request, "timing")


def test_independent_fixture_manifest_is_not_an_import_time_or_path_identity(
    tmp_path: Path,
) -> None:
    fixture = tmp_path / "fixture"
    prepare_fixture(fixture, 1)
    receipt = json.loads((fixture / "fixture.json").read_bytes())
    assert canonical(receipt["file_sha256"]) == canonical(file_manifest(fixture / "history"))
    changed = copy.deepcopy(receipt["file_sha256"])
    first = next(iter(changed))
    changed[first] = "0" * 64
    assert identity(changed) != receipt["workspace_manifest_sha256"]
