"""Versioned immutable import records; explicit evidence is never permission."""

from typing import Literal

from pydantic import Field, field_validator

from otarchguard.domain import Record
from otarchguard.loading import YamlValue

type EntityKind = Literal["asset", "zone", "interface", "connection"]
type EvidenceState = Literal[
    "EXPLICIT_SOURCE_VALUE",
    "STRUCTURALLY_DERIVED",
    "CANDIDATE_INFERENCE",
    "OWNER_CONFIRMED",
    "OWNER_REJECTED",
    "UNRESOLVED",
    "UNSUPPORTED",
]


class ImportRecord(Record):
    @field_validator(
        "profile_version", "import_version", "decisions_version", check_fields=False, mode="before"
    )
    @classmethod
    def integer_version(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("Integer version required")
        return value


class MappingProfile(ImportRecord):
    profile_version: Literal[1]
    entity: EntityKind
    fields: dict[str, str] = Field(min_length=1, max_length=64)
    constants: dict[str, str] = Field(default_factory=dict, max_length=64)
    delimiter: str | None = None
    encoding: Literal["utf-8-sig", "cp1252"] = "utf-8-sig"


class SourceDocument(ImportRecord):
    source_id: str
    sha256: str
    name: str
    format: Literal["csv", "tsv"]
    byte_count: int
    encoding: str
    delimiter: str


class SourceLocation(ImportRecord):
    row: int
    line_start: int
    line_end: int
    column: int
    header: str


class EvidenceField(ImportRecord):
    field: str
    raw_value: str
    normalized_value: str
    transformation: Literal["exact", "profile_constant"]
    state: EvidenceState
    location: SourceLocation | None = None


class ImportDiagnostic(ImportRecord):
    code: str
    row_id: str | None = None
    field: str | None = None
    message: str


class ImportCandidate(ImportRecord):
    candidate_id: str
    row_id: str
    entity: EntityKind
    state: EvidenceState = "UNRESOLVED"
    fields: tuple[EvidenceField, ...]
    unmapped: dict[str, str]
    ambiguities: tuple[str, ...]


class ImportConflict(ImportRecord):
    code: Literal["DUPLICATE_IDENTITY"] = "DUPLICATE_IDENTITY"
    identity: str
    candidate_ids: tuple[str, ...]


class ImportDraft(ImportRecord):
    import_version: Literal[1]
    source: SourceDocument
    profile: MappingProfile
    headers: tuple[str, ...]
    candidates: tuple[ImportCandidate, ...] = Field(max_length=1000)
    conflicts: tuple[ImportConflict, ...] = Field(max_length=1000)
    diagnostics: tuple[ImportDiagnostic, ...] = Field(max_length=200)


class OwnerResolution(ImportRecord):
    candidate_id: str
    decision: Literal["UNRESOLVED", "OWNER_CONFIRMED", "OWNER_REJECTED"]
    corrections: dict[str, str] = Field(default_factory=dict, max_length=64)
    rationale: str = ""


class OwnerDecisions(ImportRecord):
    decisions_version: Literal[1]
    draft_sha256: str
    reviewer: str
    model_confirmed: bool
    model_rationale: str
    model: dict[str, YamlValue]
    resolutions: tuple[OwnerResolution, ...] = Field(max_length=1000)
