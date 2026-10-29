"""Independent acceptance of benchmark pairing, outcomes and fixture identity."""

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from benchmarks.history_performance import (
    AXIS_PARAMETERS,
    _relocate,
    assert_expected_outcome,
    compare_samples,
    summarize,
    workload_operations,
)
from otarchguard.capture.observations import analyze_capture
from otarchguard.capture.protocols import enrich_capture
from otarchguard.capture.reconciliation import mapping_template
from otarchguard.evidence.attachments import build_attachment, model_architecture
from otarchguard.evidence.history import initialize_history, read_history
from otarchguard.evidence.revisions import build_revision
from otarchguard.evidence.workspace import build_snapshot, serialize
from tools.capture_workloads import plant_model
from tools.history_performance_worker import (
    canonical,
    console_arguments,
    file_manifest,
    identity,
    measure,
    prepare_case,
    prepare_fanout_fixture,
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


def test_fresh_write_guards_reject_equal_noop_results_in_api_and_console() -> None:
    for operation in (
        "import_attachment",
        "create_revision",
        "propose_baseline",
        "approve",
        "reject",
        "supersede",
        "revoke",
    ):
        for mode in ("timing", "console"):
            measured: dict[str, Any] = {
                "mode": mode,
                "outcome": {"exit_code": 0, "result": {"status": "ALREADY_PRESENT"}},
                "exit_code": 0,
                "stdout": '{"status":"ALREADY_PRESENT"}',
                "stderr": "",
            }
            with pytest.raises(ValueError, match="required ADDED"):
                assert_expected_outcome(operation, measured)
            measured["outcome"]["result"]["status"] = "ADDED"
            measured["stdout"] = '{"status":"ADDED"}'
            assert_expected_outcome(operation, measured)


def test_reuse_guard_requires_a_real_noop_in_api_and_console() -> None:
    for mode in ("timing", "console"):
        measured: dict[str, Any] = {
            "mode": mode,
            "outcome": {"exit_code": 0, "result": {"status": "ADDED"}},
            "exit_code": 0,
            "stdout": '{"status":"ADDED"}',
            "stderr": "",
        }
        with pytest.raises(ValueError, match="required ALREADY_PRESENT"):
            assert_expected_outcome("reuse_revision", measured)
        measured["outcome"]["result"]["status"] = "ALREADY_PRESENT"
        measured["stdout"] = '{"status":"ALREADY_PRESENT"}'
        assert_expected_outcome("reuse_revision", measured)


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


def test_axis_design_isolates_review_depth_baselines_and_unreferenced_attachments() -> None:
    assert sorted(
        d for r, d, b, m, p, c in AXIS_PARAMETERS if (r, b, m, p, c) == (64, 64, 0, 1, 64)
    ) == [
        0,
        16,
        32,
        64,
    ]
    assert sorted(
        b for r, d, b, m, p, c in AXIS_PARAMETERS if (r, d, m, p, c) == (64, 0, 0, 1, 64)
    ) == [
        0,
        16,
        32,
        64,
    ]
    assert sorted(
        m for r, d, b, m, p, c in AXIS_PARAMETERS if (r, d, b, p, c) == (0, 0, 0, 1, 0)
    ) == [
        16,
        64,
        128,
    ]
    assert sorted(
        r for r, d, b, m, p, c in AXIS_PARAMETERS if (d, b, m, p, c) == (0, 0, 0, 1, 128)
    ) == [16, 64, 128]


def test_axis_operation_selection_does_not_expand_collection_or_mutating_workflows() -> None:
    operations = ("verify", "approve", "list_collections")
    axis = ("verify", "review_state")
    assert workload_operations("workflow", operations, axis) == operations
    assert workload_operations("collections-16", operations, axis) == ("verify", "list_collections")
    assert workload_operations("axis-r64-d32-b64-m0-p1", operations, axis) == axis
    assert workload_operations("collections-0", ("verify", "review_state"), axis) == ("verify",)


def test_review_depth_fixture_changes_only_review_records_at_fixed_baseline_count(
    tmp_path: Path,
) -> None:
    left = tmp_path / "depth-one"
    right = tmp_path / "depth-two"
    first = prepare_fixture(left, 1, 2, 1, baselines=2)
    second = prepare_fixture(right, 1, 2, 2, baselines=2)
    assert first["verification"]["baselines"] == second["verification"]["baselines"] == 2
    assert first["verification"]["reviews"] == 1
    assert second["verification"]["reviews"] == 2
    first_files = {
        k: v for k, v in file_manifest(left / "history").items() if not k.startswith("reviews/")
    }
    second_files = {
        k: v for k, v in file_manifest(right / "history").items() if not k.startswith("reviews/")
    }
    assert first_files == second_files


def test_revision_axis_holds_exact_model_catalog_and_snapshot_bytes(tmp_path: Path) -> None:
    left, right = tmp_path / "one", tmp_path / "two"
    first = prepare_fixture(left, 1, 1, model_catalog=2)
    second = prepare_fixture(right, 1, 2, model_catalog=2)
    assert first["verification"]["attachments"] == second["verification"]["attachments"] == 2
    assert first["verification"]["analyses"] == 2
    assert second["verification"]["analyses"] == 3
    first_files = {
        k: v for k, v in file_manifest(left / "history").items() if not k.startswith("analyses/")
    }
    second_files = {
        k: v for k, v in file_manifest(right / "history").items() if not k.startswith("analyses/")
    }
    assert first_files == second_files


def dense_template(
    tmp_path: Path,
) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    capture = Path(__file__).parent / "fixtures/protocol-corpus/synthetic-industrial.pcap"
    observations = analyze_capture(capture)
    snapshot = build_snapshot(observations, "Fictional fan-out template")
    template = tmp_path / "template"
    initialize_history(template)
    model = build_attachment("model", plant_model(), snapshot)
    mapping = mapping_template(observations, model_architecture(model))
    for proposal in mapping["proposals"]:
        proposal["reviewer"] = "Fictional template reviewer"
        proposal["rationale"] = "Synthetic test only"
        if proposal["candidates"]:
            selected = proposal["candidates"][0]
            proposal.update(
                decision="ACCEPT",
                selected_asset_id=selected["asset_id"],
                selected_interface_id=selected["interface_id"],
            )
        else:
            proposal["decision"] = "REJECT"
    reviewed = build_attachment("mapping", mapping, snapshot, {"model": model})
    enrichment = build_attachment("enrichment", enrich_capture(capture), snapshot)
    for folder, value, key in (
        ("snapshots", snapshot, "snapshot_id"),
        ("attachments", model, "attachment_id"),
        ("attachments", reviewed, "attachment_id"),
        ("attachments", enrichment, "attachment_id"),
    ):
        (template / folder / (value[key] + ".json")).write_bytes(serialize(value))
    return template, snapshot, model


def test_fanout_fixture_keeps_exact_model_capture_and_valid_distinct_replay_joins(
    tmp_path: Path,
) -> None:
    template, snapshot, model = dense_template(tmp_path)
    before = file_manifest(template)
    one = prepare_fanout_fixture(tmp_path / "fanout-one", template, 1)
    two = prepare_fanout_fixture(tmp_path / "fanout-two", template, 2)
    assert file_manifest(template) == before
    assert one["model_attachment_id"] == two["model_attachment_id"] == model["attachment_id"]
    assert one["capture_sha256"] == two["capture_sha256"] == snapshot["capture_sha256"]
    assert one["verification"]["analyses"] == 1 and two["verification"]["analyses"] == 2
    assert two["verification"]["attachments"] == 6
    assert all(two["file_sha256"].get(k) == v for k, v in one["file_sha256"].items())
    state = read_history(tmp_path / "fanout-two/history")
    comparisons = [a for a in state["attachments"].values() if a["kind"] == "comparison"]
    assert len(comparisons) == 2
    for comparison in comparisons:
        selected_mapping = state["attachments"][comparison["dependencies"]["mapping"]]
        assert selected_mapping["dependencies"]["model"] == model["attachment_id"]
        assert comparison["payload"]["mapping_sha256"] == selected_mapping["component_sha256"]


def test_dense_reuse_prepares_exact_missing_model_only_revision_before_timing(
    tmp_path: Path,
) -> None:
    template, snapshot, model = dense_template(tmp_path)
    fixture = tmp_path / "dense"
    prepare_fanout_fixture(fixture, template, 1)
    source_before = file_manifest(fixture / "history")
    expected = build_revision(snapshot, {"model": model})
    assert expected["analysis_id"] not in read_history(fixture / "history")["analyses"]
    request = prepare_case(fixture, tmp_path / "reuse", "reuse_revision")
    assert request["analysis_id"] == expected["analysis_id"]
    case = Path(request["workspace"])
    assert expected["analysis_id"] in read_history(case)["analyses"]
    case_before = file_manifest(case)
    result = run_operation(request)
    assert result["exit_code"] == 0
    assert result["result"]["status"] == "ALREADY_PRESENT"
    assert result["result"]["analysis"] == expected
    assert file_manifest(case) == case_before
    assert file_manifest(fixture / "history") == source_before


def test_unreferenced_attachment_axis_keeps_exact_physical_and_analytical_inputs(
    tmp_path: Path,
) -> None:
    bare = tmp_path / "bare"
    models = tmp_path / "models"
    first = prepare_fixture(bare, 1)
    second = prepare_fixture(models, 1, unreferenced_models=2)
    assert first["verification"]["analyses"] == second["verification"]["analyses"] == 1
    assert (
        first["verification"]["physical_collections"]
        == second["verification"]["physical_collections"]
        == 1
    )
    assert second["verification"]["attachments"] == 2
    first_files = file_manifest(bare / "history")
    second_files = {
        k: v
        for k, v in file_manifest(models / "history").items()
        if not k.startswith("attachments/")
    }
    assert first_files == second_files
