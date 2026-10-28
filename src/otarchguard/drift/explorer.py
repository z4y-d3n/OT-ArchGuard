"""Source-reproduced historical presentation; never an independent drift authority."""

import hashlib
from dataclasses import replace
from pathlib import Path
from typing import Any

from otarchguard import explorer_html
from otarchguard.capture import display
from otarchguard.diagnostics import fail
from otarchguard.drift import explorer_bundle, explorer_render
from otarchguard.drift.contract import DRIFT_LIMITS
from otarchguard.drift.reports import _replay, _structure
from otarchguard.evidence import lifecycle
from otarchguard.evidence.attachments import canonical
from otarchguard.evidence.history import (
    HISTORY_LIMITS,
    _check_image,
    _evidence_limits,
    _read_bytes,
)
from otarchguard.evidence.paths import _check_read_path
from otarchguard.evidence.workspace import _decode, serialize

EXPLORER_VERSION = 1
RENDERER_VERSION = explorer_render.RENDERER_VERSION
_REPORT_LIMITS = replace(HISTORY_LIMITS, object_bytes=DRIFT_LIMITS.report_bytes)


def _report(path: Path) -> tuple[bytes, dict[str, Any]]:
    raw = _read_bytes(path, _REPORT_LIMITS)
    return raw, _structure(_decode(raw, _evidence_limits(_REPORT_LIMITS)))


def _renderer_identity() -> str:
    """Bind installed Python renderer sources, identically in source/wheel/sdist."""
    modules = (
        Path(__file__),
        Path(explorer_render.__file__),
        Path(explorer_bundle.__file__),
        Path(explorer_html.__file__),
        Path(display.__file__),
    )
    return hashlib.sha256(
        canonical({p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in modules})
    ).hexdigest()


def _identity(
    raw: bytes,
    report: dict[str, Any],
    verification: dict[str, Any],
    workspace_identity: str,
    page_size: int,
) -> dict[str, Any]:
    return {
        "historical_explorer_version": EXPLORER_VERSION,
        "renderer_version": RENDERER_VERSION,
        "renderer_sha256": _renderer_identity(),
        "report_sha256": hashlib.sha256(raw).hexdigest(),
        "report_bytes": len(raw),
        "drift_id": report["drift_id"],
        "drift_version": report["drift_version"],
        "engine_version": report["engine_version"],
        "comparability_policy_version": report["comparability_policy_version"],
        "baseline_id": report["inputs"]["baseline"]["baseline_id"],
        "recorded_approval_id": report["inputs"]["approval"]["review_id"],
        "workspace_inventory_sha256": workspace_identity,
        "generation_verification": verification,
        "options": {"page_size": page_size},
    }


def generate_explorer(
    workspace: Path, report_path: Path, output: Path, *, page_size: int = 50
) -> dict[str, Any]:
    """Replay exact existing sources once, render, audit, and publish a fresh site.

    No baseline/review/report is created or changed. Historical revoked reports
    remain supported, with the freshly checked authority prominently separated.
    The canonical drift metadata is included; original captures are never copied.
    """
    _check_read_path(output)
    if output.absolute().is_relative_to(workspace.absolute()):
        fail("HISTORICAL_PATH", "$", "Publish outside the immutable historical workspace.")
    raw, report = _report(report_path)
    image, validated = lifecycle._operation(workspace)
    verification = _replay(report, image, validated)
    source_identity = hashlib.sha256(canonical(image.files)).hexdigest()
    identity = _identity(raw, report, verification, source_identity, page_size)
    files = explorer_render.render(report, verification, page_size=page_size)
    files["report.json"] = raw
    files["verification.json"] = serialize(verification)

    def freshness() -> None:
        _check_image(workspace, image)
        if _read_bytes(report_path, _REPORT_LIMITS) != raw:
            fail("EVIDENCE_CHANGED", "$", "Drift report changed before Explorer publication.")

    result = explorer_bundle.publish(files, identity, output, before_publish=freshness)
    return {
        **result,
        "status": "PUBLISHED_SOURCE_REPRODUCED",
        "analytical_reproduction": True,
        "output": str(output.absolute()),
        "drift_id": report["drift_id"],
        "source_reproduction": verification,
    }


def verify_explorer(output: Path, *, workspace: Path | None = None) -> dict[str, Any]:
    """Check portable integrity, optionally reproduce against a fresh workspace.

    Fresh reproduction reports approval now; it never rewrites the immutable
    publication or authenticates the receipt's historical generation assertion.
    """
    integrity = explorer_bundle.verify_bundle(output)
    if workspace is None:
        return integrity
    raw, report = _report(output / "report.json")
    image, validated = lifecycle._operation(workspace)
    verification = _replay(report, image, validated)
    identity = integrity["identity"]
    receipt = _decode(
        _read_bytes(output / "verification.json", HISTORY_LIMITS),
        _evidence_limits(HISTORY_LIMITS),
    )
    expected_identity = _identity(
        raw,
        report,
        receipt,
        identity["workspace_inventory_sha256"],
        identity["options"]["page_size"],
    )
    if identity != expected_identity:
        fail("HISTORICAL_IDENTITY", "$", "Bundle identity does not bind the selected report.")
    expected = explorer_render.render(report, receipt, page_size=identity["options"]["page_size"])
    expected["report.json"] = raw
    expected["verification.json"] = serialize(receipt)
    if set(expected) != {p.name for p in output.iterdir()} - {"explorer-manifest.json"}:
        fail("HISTORICAL_RENDER", "$", "Bundle inventory differs from deterministic rendering.")
    for name, content in expected.items():
        if _read_bytes(output / name, HISTORY_LIMITS) != content:
            fail("HISTORICAL_RENDER", "$", "Bundle differs from deterministic rendering.")
    _check_image(workspace, image)
    if explorer_bundle.verify_bundle(output) != integrity:
        fail("EVIDENCE_CHANGED", "$", "Explorer changed during source verification.")
    return {
        **integrity,
        "analytical_reproduction": True,
        "source_reproduction": verification,
        "generation_authority_authenticated": False,
        "approval_snapshot_changed": receipt != verification,
    }
