"""Strict report replay and standalone atomic no-overwrite publication."""

from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

from otarchguard.diagnostics import check_limit, fail
from otarchguard.drift.contract import DRIFT_LIMITS, DRIFT_VERSION, DriftLimits
from otarchguard.drift.engine import _build
from otarchguard.evidence import lifecycle
from otarchguard.evidence.attachments import _clone, canonical, object_digest
from otarchguard.evidence.history import HISTORY_LIMITS, _check_image, _HistoryImage, read_document
from otarchguard.evidence.paths import _check_read_path
from otarchguard.evidence.validation import _ValidationContext
from otarchguard.evidence.workspace import _local, _publish, serialize

_FIELDS = {
    "drift_version",
    "engine_version",
    "comparability_policy_version",
    "implementation_sha256",
    "inputs",
    "options",
    "comparisons",
    "unaligned_findings",
    "architecture_findings",
    "summary",
    "limits",
    "resource_usage",
    "limitations",
    "reproduction",
    "drift_id",
}


def _structure(value: dict[str, Any]) -> dict[str, Any]:
    value = _clone(value)
    if (
        set(value) != _FIELDS
        or type(value["drift_version"]) is not int
        or value["drift_version"] != DRIFT_VERSION
    ):
        fail("DRIFT_VERSION", "$", "Unsupported report version or fields.")
    body = {k: v for k, v in value.items() if k != "drift_id"}
    if value["drift_id"] != "drift-" + object_digest("otarchguard.drift.v1", body):
        fail("DRIFT_INTEGRITY", "$", "Comparison report identity mismatch.")
    check_limit("drift_report_bytes", len(serialize(value)), DRIFT_LIMITS.report_bytes)
    return value


def read_report(path: Path) -> dict[str, Any]:
    """Check bounded JSON and content identity only; this grants no analytical authority."""
    return _structure(
        read_document(path, replace(HISTORY_LIMITS, object_bytes=DRIFT_LIMITS.report_bytes))
    )


def _replay(
    report: dict[str, Any],
    image: _HistoryImage,
    validated: _ValidationContext,
) -> dict[str, Any]:
    report = _structure(report)
    try:
        selected_limits = report["limits"]
        if type(selected_limits) is not dict or set(selected_limits) != set(asdict(DRIFT_LIMITS)):
            fail("DRIFT_LIMIT", "$", "Unsupported comparison limit contract.")
        for name, maximum in asdict(DRIFT_LIMITS).items():
            value = selected_limits[name]
            if type(value) is not int or not 0 < value <= maximum:
                fail("DRIFT_LIMIT", "$", "Report limits may only narrow supported ceilings.")
        options = report["options"]
        if type(options) is not dict or set(options) != {
            "mode",
            "reference_members",
            "candidates",
            "candidate_model",
            "context",
        }:
            fail("DRIFT_INPUT", "$", "Unsupported comparison options.")
        expected = _build(
            image,
            validated,
            report["inputs"]["baseline"]["baseline_id"],
            options["candidates"],
            options["context"],
            mode=options["mode"],
            reference_members=options["reference_members"],
            candidate_model=options["candidate_model"],
            limits=DriftLimits(**selected_limits),
            review_frontier=report["inputs"]["review_frontier"],
        )
    except (KeyError, TypeError, ValueError, AttributeError, IndexError, RecursionError):
        fail("DRIFT_REPORT", "$", "Malformed comparison report or unsupported dependencies.")
    if canonical(report) != canonical(expected):
        fail(
            "DRIFT_REPRODUCTION",
            "$",
            "Report does not reproduce from exact validated source dependencies.",
        )
    bid = expected["inputs"]["baseline"]["baseline_id"]
    current_status = validated.statuses[bid]
    return {
        "status": "REPRODUCIBLE_HISTORICAL_REPORT",
        "drift_id": report["drift_id"],
        "structure_valid": True,
        "source_dependencies_available": True,
        "canonical_reproduction": True,
        "recorded_baseline_status": "APPROVED",
        "current_baseline_status": current_status,
        "currently_approved_reference": current_status == "APPROVED",
        "review_graph_changed": report["inputs"]["review_frontier"]
        != sorted(validated._state["reviews"]),
        "authority": (
            "Review graph is an unauthenticated local assertion; "
            "report creation time is not attested."
        ),
    }


def verify_report(workspace: Path, path: Path) -> dict[str, Any]:
    report = read_report(path)
    image, validated = lifecycle._operation(workspace)
    return _replay(report, image, validated)


def inspect_report(workspace: Path, path: Path) -> dict[str, Any]:
    report = read_report(path)
    image, validated = lifecycle._operation(workspace)
    return {"verification": _replay(report, image, validated), "report": report}


def _destination(path: Path, workspace: Path) -> None:
    _local(path)
    _check_read_path(path.parent)
    if path.suffix != ".json" or not path.parent.is_dir():
        fail("DRIFT_PATH", "$", "Use a JSON report path in an existing local directory.")
    if path.absolute().is_relative_to(workspace.absolute()):
        fail("DRIFT_PATH", "$", "Publish reports outside the historical workspace.")
    if path.exists():
        fail("EVIDENCE_EXISTS", "$", "Report destination must be fresh.")


def publish(report: dict[str, Any], path: Path, workspace: Path) -> dict[str, Any]:
    """Replay caller-supplied report content before publishing with current authority."""
    report = _structure(report)
    _destination(path, workspace)
    image, validated = lifecycle._operation(workspace)
    verification = _replay(report, image, validated)
    if not verification["currently_approved_reference"]:
        fail("DRIFT_APPROVAL", "$", "A new publication requires a currently approved reference.")
    _check_image(workspace, image)
    _publish(path, serialize(report))
    return {"status": "PUBLISHED", "drift_id": report["drift_id"], "bytes": len(serialize(report))}


def generate_report(
    workspace: Path,
    baseline_id: str,
    candidates: list[str],
    context: dict[str, Any],
    output: Path,
    *,
    mode: str = "qualified",
    reference_members: list[str] | None = None,
    candidate_model: str | None = None,
) -> dict[str, Any]:
    """Acquire once, compare, check original bytes again, then atomically publish."""
    _destination(output, workspace)
    image, validated = lifecycle._operation(workspace)
    report = _build(
        image,
        validated,
        baseline_id,
        candidates,
        context,
        mode=mode,
        reference_members=reference_members,
        candidate_model=candidate_model,
    )
    _check_image(workspace, image)
    _publish(output, serialize(report))
    return report


def _summary_text(report: dict[str, Any]) -> str:
    inputs = report["inputs"]
    lines = [
        "HISTORICAL EVIDENCE COMPARISON",
        "Baseline: " + inputs["baseline"]["baseline_id"],
        "Recorded approval: " + inputs["approval"]["review_id"],
        "Scope: " + inputs["baseline"]["scope"]["environment"],
        "Mode: " + report["options"]["mode"],
        "Aligned pairs: " + str(report["summary"]["aligned_pairs"]),
    ]
    for index, pair in enumerate(report["comparisons"][:64], 1):
        assessment = pair["comparability"]
        lines.append(
            f"Pair {index}: communication={assessment['communication_metadata']}; "
            f"protocol={assessment['protocol_metadata']}; "
            f"asset continuity={assessment['asset_continuity']}"
        )
    for category, count in sorted(report["summary"]["categories"].items()):
        lines.append(f"{category}: {count}")
    lines.append(report["summary"]["interpretation"])
    lines.append(
        f"Records: differences={report['summary']['difference_records']}; "
        f"unchanged support={report['summary']['unchanged_support_records']}; "
        f"abstentions={report['summary']['abstentions']}"
    )
    lines.extend("Limitation: " + item for item in report["limitations"])
    return "\n".join(lines)


def summarize(report: dict[str, Any]) -> str:
    """Bounded deterministic text; verify sources before presenting current authority."""
    try:
        return _summary_text(_structure(report))
    except (KeyError, TypeError, ValueError, AttributeError, IndexError, RecursionError):
        fail("DRIFT_REPORT", "$", "Malformed comparison report summary.")
