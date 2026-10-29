"""Independent exact-selection, collection alignment and relocation properties."""

import copy
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from otarchguard.diagnostics import ModelError
from otarchguard.drift.engine import compare
from otarchguard.drift.reports import publish, summarize, verify_report
from otarchguard.evidence import lifecycle
from tools.drift_walkthrough import canonical, comparison_context, prepare


def _baseline(
    selection: dict[str, Any],
    name: str,
    members: list[str],
    scope: dict[str, Any],
    *,
    kind: str = "evidence",
    model: str | None = None,
) -> str:
    workspace = Path(selection["workspace"])
    path = workspace.parent / (name + "-scope.json")
    path.write_bytes(canonical(scope))
    proposal = lifecycle.propose_baseline(workspace, path, members, kind, model)["baseline"]
    lifecycle.record_review(
        workspace,
        proposal["baseline_id"],
        "approve",
        "Fictional alignment reviewer",
        "Only this exact fictional collection set and declared scope are approved",
    )
    return str(proposal["baseline_id"])


@pytest.fixture(scope="module")
def alignment_case(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    selected = prepare(tmp_path_factory.mktemp("drift-alignments") / "fictional-source")
    periods = selected["periods"]
    reference, candidate = periods["reference"]["analysis_id"], periods["candidate"]["analysis_id"]
    multi_scope = selected["scope"] | {"purpose": "Fictional two-collection reference"}
    selected["multi_scope"] = multi_scope
    selected["multi_baseline"] = _baseline(
        selected,
        "multi",
        [reference, candidate],
        multi_scope,
    )
    strict_scope = selected["scope"] | {
        "purpose": "Explicit equivalent finite-scan metadata comparison",
        "uncertainties": [],
    }
    selected["strict_scope"] = strict_scope
    selected["strict_baseline"] = _baseline(selected, "strict", [reference], strict_scope)
    architecture_scope = selected["scope"] | {"purpose": "Exact declared architecture comparison"}
    selected["architecture_baseline"] = _baseline(
        selected,
        "architecture",
        [],
        architecture_scope,
        kind="architecture",
        model=periods["reference"]["model_id"],
    )
    return selected


def _multi_context(selected: dict[str, Any]) -> dict[str, Any]:
    periods, scope = selected["periods"], selected["multi_scope"]
    first = comparison_context(
        periods["reference"]["analysis_id"], periods["candidate"]["analysis_id"], scope
    )
    second = comparison_context(
        periods["candidate"]["analysis_id"], periods["incomplete"]["analysis_id"], scope
    )
    return {"context_version": 1, "pairs": first["pairs"] + second["pairs"]}


def test_multiple_collections_require_exact_nonduplicated_explicit_pairs(
    alignment_case: dict[str, Any],
) -> None:
    selected = alignment_case
    periods = selected["periods"]
    candidates = [periods["incomplete"]["analysis_id"], periods["candidate"]["analysis_id"]]
    report = compare(
        Path(selected["workspace"]),
        selected["multi_baseline"],
        candidates,
        _multi_context(selected),
    )
    assert report["summary"]["aligned_pairs"] == 2
    assert report["summary"]["distinct_physical_collections"] == 3
    assert report["unaligned_findings"] == []
    assert {
        (p["reference_analysis_id"], p["candidate_analysis_id"]) for p in report["comparisons"]
    } == {
        (periods["reference"]["analysis_id"], periods["candidate"]["analysis_id"]),
        (periods["candidate"]["analysis_id"], periods["incomplete"]["analysis_id"]),
    }


def test_unpaired_collections_abstain_without_arbitrary_matches(
    alignment_case: dict[str, Any],
) -> None:
    selected = alignment_case
    periods = selected["periods"]
    report = compare(
        Path(selected["workspace"]),
        selected["multi_baseline"],
        [periods["incomplete"]["analysis_id"]],
        {"context_version": 1, "pairs": []},
    )
    assert report["comparisons"] == []
    findings = report["unaligned_findings"]
    assert len(findings) == 3
    assert {f["subtype"] for f in findings} == {"UNALIGNED_COLLECTION"}
    assert [f["key"] for f in findings].count("reference") == 2
    assert [f["key"] for f in findings].count("candidate") == 1
    assert {f["comparability"] for f in findings} == {"INDETERMINATE"}


def test_exact_reference_subset_retains_full_baseline_membership(
    alignment_case: dict[str, Any],
) -> None:
    selected, periods = alignment_case, alignment_case["periods"]
    reference, candidate = periods["reference"]["analysis_id"], periods["candidate"]["analysis_id"]
    context = comparison_context(reference, candidate, selected["multi_scope"])
    report = compare(
        Path(selected["workspace"]),
        selected["multi_baseline"],
        [candidate],
        context,
        reference_members=[reference],
    )
    assert len(report["inputs"]["baseline"]["members"]) == 2
    assert [s["analysis_id"] for s in report["inputs"]["reference_sources"]] == [reference]
    assert report["unaligned_findings"] == []


@pytest.mark.parametrize("mode", ["qualified", "descriptive"])
def test_unresolved_pair_retains_description_without_asserted_alignment(
    alignment_case: dict[str, Any],
    mode: str,
) -> None:
    selected, periods = alignment_case, alignment_case["periods"]
    reference, candidate = periods["reference"]["analysis_id"], periods["candidate"]["analysis_id"]
    context = comparison_context(reference, candidate, selected["strict_scope"])
    context["pairs"][0]["alignment"] = "unresolved"
    report = compare(
        Path(selected["workspace"]),
        selected["strict_baseline"],
        [candidate],
        context,
        mode=mode,
    )
    assert report["comparisons"][0]["comparability"]["communication_metadata"] == "INDETERMINATE"
    assert any(
        f["subtype"] == "REFERENCE_ONLY_OBSERVATION" for f in report["comparisons"][0]["findings"]
    )
    if mode == "descriptive":
        assert report["summary"]["interpretation"] == "Descriptive finite-dataset differences."


def test_strict_rejects_unresolved_or_missing_alignment_and_accepts_equivalent_scope(
    alignment_case: dict[str, Any],
) -> None:
    selected, periods = alignment_case, alignment_case["periods"]
    workspace = Path(selected["workspace"])
    reference, candidate = periods["reference"]["analysis_id"], periods["candidate"]["analysis_id"]
    context = comparison_context(reference, candidate, selected["strict_scope"])
    accepted = compare(workspace, selected["strict_baseline"], [candidate], context, mode="strict")
    assert accepted["comparisons"][0]["comparability"]["communication_metadata"] == "COMPARABLE"
    context["pairs"][0]["alignment"] = "unresolved"
    with pytest.raises(ModelError):
        compare(workspace, selected["strict_baseline"], [candidate], context, mode="strict")
    with pytest.raises(ModelError):
        compare(
            workspace,
            selected["strict_baseline"],
            [candidate],
            {"context_version": 1, "pairs": []},
            mode="strict",
        )


@pytest.mark.parametrize(
    "attack",
    ["duplicate-pair", "two-candidate-interpretations", "duplicate-reference", "foreign-reference"],
)
def test_invalid_or_duplicated_collection_selections_fail_closed(
    alignment_case: dict[str, Any],
    attack: str,
) -> None:
    selected, periods = alignment_case, alignment_case["periods"]
    reference, candidate = periods["reference"]["analysis_id"], periods["candidate"]["analysis_id"]
    context = comparison_context(reference, candidate, selected["scope"])
    candidates, references = [candidate], [reference]
    if attack == "duplicate-pair":
        context["pairs"].append(copy.deepcopy(context["pairs"][0]))
    elif attack == "two-candidate-interpretations":
        candidates = [reference, periods["decoder_one"]["analysis_id"]]
        context = {"context_version": 1, "pairs": []}
    elif attack == "duplicate-reference":
        references = [reference, reference]
    else:
        references = [candidate]
        context = {"context_version": 1, "pairs": []}
    with pytest.raises(ModelError):
        compare(
            Path(selected["workspace"]),
            selected["baseline_id"],
            candidates,
            context,
            reference_members=references,
        )


def test_architecture_baseline_requires_exact_candidate_model_and_no_capture_guess(
    alignment_case: dict[str, Any],
) -> None:
    selected, periods = alignment_case, alignment_case["periods"]
    workspace = Path(selected["workspace"])
    context = {"context_version": 1, "pairs": []}
    with pytest.raises(ModelError):
        compare(workspace, selected["architecture_baseline"], [], context)
    report = compare(
        workspace,
        selected["architecture_baseline"],
        [],
        context,
        candidate_model=periods["candidate"]["model_id"],
    )
    assert report["comparisons"] == []
    models = report["inputs"]["selected_models"]
    assert models["reference"]["attachment_id"] == periods["reference"]["model_id"]
    assert models["candidate"]["attachment_id"] == periods["candidate"]["model_id"]
    assert models["reference"]["model_sha256"] == report["inputs"]["baseline"]["model_sha256"]
    assert models["reference"]["model_sha256"] != models["candidate"]["model_sha256"]
    assert any(
        f["category"] == "DECLARED_ARCHITECTURE_CHANGE" for f in report["architecture_findings"]
    )
    assert report["summary"]["distinct_physical_collections"] == 0


def test_workspace_relocation_and_context_reordering_preserve_exact_identity(
    alignment_case: dict[str, Any],
    tmp_path: Path,
) -> None:
    selected, periods = alignment_case, alignment_case["periods"]
    workspace = Path(selected["workspace"])
    candidates = [periods["incomplete"]["analysis_id"], periods["candidate"]["analysis_id"]]
    context = _multi_context(selected)
    original_context = copy.deepcopy(context)
    report = compare(workspace, selected["multi_baseline"], candidates, context)
    reordered = copy.deepcopy(context)
    reordered["pairs"].reverse()
    reordered = json.loads(json.dumps(reordered, sort_keys=True))
    destination = tmp_path / "relocated-history"
    shutil.copytree(workspace, destination)
    relocated = compare(
        destination, selected["multi_baseline"], list(reversed(candidates)), reordered
    )
    assert canonical(report) == canonical(relocated)
    assert report["drift_id"] == relocated["drift_id"]
    assert context == original_context


@pytest.mark.parametrize("review_new_baseline", [False, True])
def test_unrelated_later_baseline_does_not_change_recorded_report_reproduction(
    alignment_case: dict[str, Any],
    tmp_path: Path,
    review_new_baseline: bool,
) -> None:
    selected, periods = alignment_case, alignment_case["periods"]
    workspace = tmp_path / "independent-history"
    shutil.copytree(Path(selected["workspace"]), workspace)
    reference, candidate = periods["reference"]["analysis_id"], periods["candidate"]["analysis_id"]
    context = comparison_context(reference, candidate, selected["scope"])
    report = compare(workspace, selected["baseline_id"], [candidate], context)
    destination = tmp_path / "recorded-drift.json"
    publish(report, destination, workspace)
    original = destination.read_bytes()
    scope_path = tmp_path / "later-scope.json"
    scope_path.write_bytes(
        canonical(
            selected["scope"]
            | {
                "purpose": "A separately selected later fictional review scope",
            }
        )
    )
    baseline = lifecycle.propose_baseline(workspace, scope_path, [candidate])["baseline"]
    if review_new_baseline:
        lifecycle.record_review(
            workspace,
            baseline["baseline_id"],
            "approve",
            "Another fictional reviewer",
            "Independent approval created after the recorded report frontier",
        )
    verification = verify_report(workspace, destination)
    assert verification["canonical_reproduction"] is True
    assert verification["current_baseline_status"] == "APPROVED"
    assert verification["currently_approved_reference"] is True
    assert verification["review_graph_changed"] is review_new_baseline
    assert destination.read_bytes() == original


@pytest.mark.parametrize("attack", ["inputs", "summary", "comparisons", "baseline"])
def test_self_hashed_malformed_summary_returns_controlled_diagnostic(
    alignment_case: dict[str, Any],
    attack: str,
) -> None:
    selected, periods = alignment_case, alignment_case["periods"]
    reference, candidate = periods["reference"]["analysis_id"], periods["candidate"]["analysis_id"]
    report = compare(
        Path(selected["workspace"]),
        selected["baseline_id"],
        [candidate],
        comparison_context(reference, candidate, selected["scope"]),
    )
    if attack == "inputs":
        report["inputs"] = {}
    elif attack == "summary":
        report["summary"] = {}
    elif attack == "comparisons":
        report["comparisons"] = [None]
    else:
        report["inputs"]["baseline"] = "not a baseline object"
    body = {k: v for k, v in report.items() if k != "drift_id"}
    report["drift_id"] = (
        "drift-"
        + hashlib.sha256(
            canonical(
                {
                    "domain": "otarchguard.drift.v1",
                    "value": body,
                }
            )
        ).hexdigest()
    )
    with pytest.raises(ModelError) as error:
        summarize(report)
    assert error.value.diagnostics[0].code == "DRIFT_REPORT"
