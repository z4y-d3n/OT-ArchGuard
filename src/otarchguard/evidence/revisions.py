"""Canonical analytical revisions, separate from physical capture and review IDs.

The semantics manifest identifies the selected local validation/replay semantics.
Frozen observation-v2 metadata does not attest the original producer's source or
parser limits. That unknown provenance remains explicit rather than fabricated.
"""

import hashlib
from collections.abc import Mapping
from dataclasses import asdict
from importlib.resources import files
from typing import Any

from otarchguard import NATIVE_ENGINE_VERSION
from otarchguard.capture.contract import CAPTURE_LIMITS
from otarchguard.capture.protocols.contract import ENRICHMENT_LIMITS
from otarchguard.contract import RESOURCE_LIMITS
from otarchguard.diagnostics import fail
from otarchguard.evidence.attachments import (
    KINDS,
    _clone,
    canonical,
    object_digest,
    validate_attachment,
)
from otarchguard.evidence.observations import identity
from otarchguard.evidence.workspace import validate_snapshot

_SOURCES = (
    "__init__.py",
    "api.py",
    "contract.py",
    "diagnostics.py",
    "domain.py",
    "loading.py",
    "parsing.py",
    "validation.py",
    "normalization.py",
    "reachability.py",
    "graph.py",
    "policy.py",
    "policy_evidence.py",
    "intervals.py",
    "capture/contract.py",
    "capture/parser.py",
    "capture/observations.py",
    "capture/reconciliation.py",
    "capture/protocols/__init__.py",
    "capture/protocols/contract.py",
    "capture/protocols/packet.py",
    "capture/protocols/validation.py",
    "capture/protocols/header_validation.py",
    "capture/protocols/modbus.py",
    "capture/protocols/dcp.py",
    "capture/protocols/enip.py",
    "capture/protocols/s7comm.py",
    "capture/protocols/iec104.py",
    "capture/protocols/opcua.py",
    "capture/protocols/dnp3.py",
    "evidence/observations.py",
    "evidence/workspace.py",
    "evidence/attachments.py",
    "evidence/revisions.py",
)
REVISION_LIMITATIONS = [
    "One revision is an interpretation of one physical collection, not independent corroboration.",
    "Integrity and consistency do not establish capture authenticity or reviewer authority.",
    "The manifest identifies selected local validation/replay semantics; "
    "original producer provenance is unattested.",
    "Missing components are explicit; no baseline approval or coverage completeness is inferred.",
    "Historical drift and architecture deviation analysis are not performed.",
]


def _require(condition: bool, message: str) -> None:
    if not condition:
        fail("EVIDENCE_REVISION", "$", message)


def implementation_identities() -> dict[str, str]:
    """Fixed implementation inventory, with paths relative to the installed package."""
    package = files("otarchguard")
    try:
        return {
            name: hashlib.sha256(package.joinpath(name).read_bytes()).hexdigest()
            for name in _SOURCES
        }
    except (OSError, TypeError):
        fail("EVIDENCE_SEMANTICS", "$", "Cannot verify the selected implementation inventory.")


def build_semantics(
    snapshot: dict[str, Any],
    attachments: Mapping[str, dict[str, Any]] | None = None,
    *,
    require_complete_scan: bool = False,
    require_reviewed_mapping: bool = False,
) -> dict[str, Any]:
    """Record actual bounded consumer configuration, without invented producer facts."""
    _require(
        type(require_complete_scan) is bool and type(require_reviewed_mapping) is bool,
        "Analysis options must be exact booleans.",
    )
    components = attachments or {}
    enrichment = components.get("enrichment")
    return {
        "semantics_version": 1,
        "identity_scope": "selected-local-validation-and-native-replay",
        "original_producer_provenance": "unattested-by-frozen-metadata-contracts",
        "implementation_support_policy": (
            "exact-selected-source-inventory; unknown implementations require "
            "an explicit compatible consumer"
        ),
        "observation_version": 2,
        "capture_version": 1,
        "catalog_version": 1,
        "native_schema_version": 1,
        "native_engine_version": NATIVE_ENGINE_VERSION,
        "native_comparison_version": 1,
        "association_version": 1,
        "enrichment_version": enrichment["payload"]["enrichment_version"] if enrichment else None,
        "decoder_version": enrichment["payload"]["decoder_version"] if enrichment else None,
        "implementation_sha256": implementation_identities(),
        "capture_validation_limits": asdict(CAPTURE_LIMITS),
        "native_validation_limits": asdict(RESOURCE_LIMITS),
        "enrichment_validation_limits": asdict(ENRICHMENT_LIMITS),
        "selected_enrichment_limits": enrichment["payload"]["limits"] if enrichment else None,
        "parser_mode": "metadata-only-passive-no-reassembly",
        "original_capture_parameters": None,
        "analysis_options": {
            "require_complete_scan": require_complete_scan,
            "require_reviewed_mapping": require_reviewed_mapping,
        },
    }


def _validated_components(
    snapshot: dict[str, Any], attachments: Mapping[str, dict[str, Any]]
) -> dict[str, Any]:
    _require(set(attachments) <= set(KINDS), "Unsupported analytical component.")
    components: dict[str, Any] = {kind: None for kind in KINDS}
    components["policy"] = None
    dependencies = {
        kind: value for kind, value in attachments.items() if kind in {"model", "mapping"}
    }
    for kind, attachment in attachments.items():
        _require(attachment.get("kind") == kind, "Analytical component type mismatch.")
        validate_attachment(attachment, snapshot, dependencies)
        components[kind] = {
            "attachment_id": attachment["attachment_id"],
            "sha256": attachment["component_sha256"],
        }
    return components


def build_revision(
    snapshot: dict[str, Any],
    attachments: Mapping[str, dict[str, Any]] | None = None,
    semantics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Bind validated inputs and enforce every selected analytical requirement."""
    try:
        validate_snapshot(snapshot)
        selected = attachments or {}
        components = _validated_components(snapshot, selected)
        if semantics is None:
            semantics = build_semantics(snapshot, selected)
        else:
            semantics = _clone(semantics)
        options = semantics["analysis_options"]
        _require(
            type(options) is dict
            and set(options) == {"require_complete_scan", "require_reviewed_mapping"},
            "Unsupported analysis options.",
        )
        expected = build_semantics(snapshot, selected, **options)
        _require(
            canonical(semantics) == canonical(expected),
            "Unsupported or inconsistent producer semantics; "
            "a source digest alone grants no authority.",
        )
        observations = snapshot["observations"]
        if options["require_complete_scan"]:
            _require(
                observations["coverage"]["complete_file_scan"] is True
                and observations["capture"]["unknown_blocks"] == 0,
                "The selected analysis requires a complete supported container scan.",
            )
        if options["require_reviewed_mapping"]:
            mapping = selected.get("mapping")
            _require(
                mapping is not None, "The selected analysis requires an owner-reviewed mapping."
            )
            assert mapping is not None
            _require(
                all(p["decision"] != "PENDING" for p in mapping["payload"]["proposals"]),
                "The selected analysis forbids pending association decisions.",
            )
        result = {
            "analysis_version": 1,
            "capture_sha256": snapshot["capture_sha256"],
            "observations_sha256": snapshot["observations_sha256"],
            "components": components,
            "producer_semantics": semantics,
            "producer_semantics_sha256": object_digest(
                "otarchguard.producer-semantics.v1", semantics
            ),
            "limitations": list(REVISION_LIMITATIONS),
        }
        result["analysis_id"] = "analysis-" + object_digest("otarchguard.analysis", result)
        return _clone(result)
    except (
        ValueError,
        KeyError,
        TypeError,
        AttributeError,
        IndexError,
        OverflowError,
        RecursionError,
    ):
        fail("EVIDENCE_REVISION", "$", "Invalid, stale or unsupported analytical revision inputs.")


def validate_revision(
    revision: dict[str, Any],
    snapshot: dict[str, Any],
    attachments: Mapping[str, dict[str, Any]] | None = None,
) -> None:
    """Require complete current supported semantics and exact validated dependencies."""
    try:
        revision = _clone(revision)
        _require(
            type(revision.get("analysis_version")) is int
            and revision["analysis_version"] == 1
            and identity(revision.get("analysis_id"), "analysis-"),
            "Unsupported analytical revision version or identity.",
        )
        expected = build_revision(snapshot, attachments, revision["producer_semantics"])
        _require(
            canonical(revision) == canonical(expected),
            "Analytical revision metadata or identity mismatch.",
        )
    except (
        ValueError,
        KeyError,
        TypeError,
        AttributeError,
        IndexError,
        OverflowError,
        RecursionError,
    ):
        fail("EVIDENCE_REVISION", "$", "Invalid, stale or unsupported analytical revision.")
