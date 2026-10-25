"""Bounded Explorer input and read-only provenance verification. No source reimport."""

import json
import re
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from otarchguard.api import ValidatedArchitecture, validate_bytes
from otarchguard.contract import RESOURCE_LIMITS
from otarchguard.diagnostics import check_limit, fail
from otarchguard.domain import Record
from otarchguard.ingestion.json_inventory import parse_json
from otarchguard.ingestion.project import PROJECT_LIMITS, _no_links, project_digest
from otarchguard.ingestion.project_records import ProjectDecisions, ProjectDraft
from otarchguard.ingestion.project_review import reviewed_project_artifacts
from otarchguard.ingestion.reconciliation import catalog, reconcile
from otarchguard.ingestion.structured import StructuredLimits
from otarchguard.ingestion.tabular import digest, read_regular


@dataclass(frozen=True, slots=True)
class ExplorerLimits:
    sidecar_bytes: int = 40 * 1024 * 1024
    pages: int = 24000
    page_bytes: int = 1024 * 1024
    total_bytes: int = 256 * 1024 * 1024
    text_characters: int = 4096
    index_rows: int = 60
    diagram_nodes: int = 20
    diagram_edges: int = 32
    analyses: int = 16


EXPLORER_LIMITS = ExplorerLimits()


class ProjectProvenance(Record):
    project_provenance_version: int
    draft_sha256: str
    model_sha256: str
    catalog: ProjectDraft
    decisions: ProjectDecisions
    identity_index: list[dict[str, str | None]]
    declarations: list[dict[str, object]]
    scope: str


def load_model(path: Path) -> ValidatedArchitecture:
    _no_links(path)
    return validate_bytes(read_regular(path, RESOURCE_LIMITS.input_bytes))


def load_provenance(path: Path, model: ValidatedArchitecture) -> ProjectProvenance:
    """Fail closed on explicit incompatible, stale or internally inconsistent evidence."""
    _no_links(path)
    value = parse_json(
        read_regular(path, EXPLORER_LIMITS.sidecar_bytes),
        StructuredLimits(
            source_bytes=EXPLORER_LIMITS.sidecar_bytes,
            depth=PROJECT_LIMITS.depth,
            records=PROJECT_LIMITS.control_events,
            scalars=PROJECT_LIMITS.control_events,
            text=4096,
        ),
    )
    if (
        not isinstance(value, dict)
        or type(value.get("project_provenance_version")) is not int
        or value["project_provenance_version"] != 1
    ):
        fail("EXPLORER_PROVENANCE", "$", "Explorer requires project provenance version 1.")
    try:
        sidecar = ProjectProvenance.model_validate(value)
    except (ValidationError, ValueError):
        fail("EXPLORER_PROVENANCE", "$", "Malformed project provenance sidecar.")
    if sidecar.model_sha256 != model.sha256:
        fail("EXPLORER_IDENTITY", "$", "Provenance does not bind this native model.")
    draft = sidecar.catalog
    if draft.manifest_sha256 != digest(draft.manifest.model_dump(mode="json")):
        fail("EXPLORER_IDENTITY", "$", "Catalog manifest digest differs.")
    if sidecar.draft_sha256 != project_digest(draft):
        fail("EXPLORER_IDENTITY", "$", "Provenance catalog digest differs.")
    source_ids = [s.id for s in draft.sources]
    if len(set(source_ids)) != len(source_ids) or set(source_ids) != {
        s.id for s in draft.manifest.sources
    }:
        fail("EXPLORER_PROVENANCE", "$", "Source registrations differ from the catalog.")
    for source in draft.sources:
        sha = source.evidence.source.sha256
        if re.fullmatch(r"[0-9a-f]{64}", sha) is None:
            fail("EXPLORER_PROVENANCE", "$", "Invalid source digest.")
        if source.evidence.source.source_id != "src_" + sha:
            fail("EXPLORER_PROVENANCE", "$", "Source identity and digest disagree.")
        if len({c.row_id for c in source.evidence.candidates}) != len(source.evidence.candidates):
            fail("EXPLORER_PROVENANCE", "$", "Duplicate observation identity.")
    catalog(draft.sources)  # Independently reject duplicate qualified candidates.
    proposals, conflicts = reconcile(draft.sources, draft.manifest)
    if proposals != draft.proposals or conflicts != draft.conflicts:
        fail("EXPLORER_PROVENANCE", "$", "Retained reconciliation groups differ.")
    artifacts = reviewed_project_artifacts(draft, sidecar.decisions)
    expected = json.loads(artifacts["architecture.provenance.json"])
    if expected != sidecar.model_dump(mode="json"):
        fail("EXPLORER_PROVENANCE", "$", "Provenance indexes or declarations differ from review.")
    if validate_bytes(artifacts["architecture.yaml"]).sha256 != model.sha256:
        fail("EXPLORER_IDENTITY", "$", "Reviewed declarations differ from native architecture.")
    return sidecar


def page_id(kind: str, identity: object) -> str:
    """Full, case/normalization-independent digest; imported labels never form paths."""
    if re.fullmatch(r"[a-z]+", kind) is None:
        raise ValueError("Renderer-controlled page kind required")
    return kind + "-" + digest([kind, identity])


def check_text(value: str) -> None:
    check_limit("explorer_text_characters", len(value), EXPLORER_LIMITS.text_characters)
    if any(
        (ord(c) < 32 and c not in "\t\r\n") or 127 <= ord(c) <= 159 or 0xD800 <= ord(c) <= 0xDFFF
        for c in value
    ):
        fail("EXPLORER_TEXT", "$", "Unsupported control or surrogate character in display text.")
