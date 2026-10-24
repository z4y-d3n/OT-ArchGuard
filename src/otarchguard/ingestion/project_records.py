"""Versioned project contracts, separate from every single-source import version."""

from typing import Literal

from pydantic import Field, field_validator

from otarchguard.domain import Id, Record
from otarchguard.ingestion.records import ImportDraft
from otarchguard.loading import YamlValue

type Adapter = Literal[
    "csv",
    "tsv",
    "json",
    "xlsx",
    "netbox-offline-v1",
    "drawio",
    "graphml",
    "txt",
    "md",
    "docx",
    "pptx",
]


class ProjectRecord(Record):
    @field_validator(
        "project_version",
        "project_draft_version",
        "project_decisions_version",
        check_fields=False,
        mode="before",
    )
    @classmethod
    def version_integer(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("Integer version required")
        return value


class ProjectSource(ProjectRecord):
    id: Id
    path: str = Field(min_length=1, max_length=256)
    adapter: Adapter
    profile: str = Field(min_length=1, max_length=256)


class Alias(ProjectRecord):
    members: tuple[str, ...] = Field(min_length=2, max_length=128)
    rationale: str = Field(min_length=1, max_length=4096)


class ProjectManifest(ProjectRecord):
    project_version: Literal[1]
    project_id: Id
    sources: tuple[ProjectSource, ...] = Field(min_length=1, max_length=16)
    model_context: str | None = Field(default=None, max_length=256)
    aliases: tuple[Alias, ...] = Field(default=(), max_length=256)
    preferred_sources: dict[str, str] = Field(default_factory=dict, max_length=32)


class CatalogSource(ProjectRecord):
    id: Id
    path: str
    profile_path: str
    profile_sha256: str
    evidence: ImportDraft


class MatchGroup(ProjectRecord):
    group_id: str
    category: Literal[
        "EXPLICIT_ID_MATCH", "OWNER_DECLARED_ALIAS", "EXACT_ATTRIBUTE_MATCH", "CONFLICT"
    ]
    code: str
    field: str
    value: str
    members: tuple[str, ...]
    differences: tuple[str, ...] = ()
    explanation: str


class ProjectDraft(ProjectRecord):
    project_draft_version: Literal[1]
    manifest: ProjectManifest
    manifest_sha256: str
    sources: tuple[CatalogSource, ...]
    context: dict[str, YamlValue]
    context_sha256: str | None
    proposals: tuple[MatchGroup, ...]
    conflicts: tuple[MatchGroup, ...]
    accounting: dict[str, int]


class EntityDecision(ProjectRecord):
    members: tuple[str, ...] = Field(min_length=1, max_length=5000)
    decision: Literal["UNRESOLVED", "OWNER_CONFIRMED", "OWNER_REJECTED", "EVIDENCE_ONLY"]
    canonical_id: str = Field(default="", max_length=64)
    field_sources: dict[str, str] = Field(default_factory=dict, max_length=64)
    corrections: dict[str, str] = Field(default_factory=dict, max_length=64)
    references: dict[str, str] = Field(default_factory=dict, max_length=3)
    rationale: str = Field(default="", max_length=4096)


class ConflictDecision(ProjectRecord):
    group_id: str
    resolved: bool = False
    rationale: str = Field(default="", max_length=4096)


class EvidenceAcknowledgment(ProjectRecord):
    source_id: Id
    members: tuple[str, ...] = Field(min_length=1, max_length=8000)
    set_sha256: str
    rationale: str = Field(min_length=1, max_length=4096)


class ProjectDecisions(ProjectRecord):
    project_decisions_version: Literal[1]
    draft_sha256: str
    reviewer: str = Field(default="", max_length=256)
    model_confirmed: bool = False
    model_rationale: str = Field(default="", max_length=4096)
    entities: tuple[EntityDecision, ...] = Field(max_length=5000)
    conflicts: tuple[ConflictDecision, ...] = Field(max_length=4096)
    acknowledgments: tuple[EvidenceAcknowledgment, ...] = Field(default=(), max_length=16)
