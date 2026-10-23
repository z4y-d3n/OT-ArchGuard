"""Versioned immutable import records; explicit evidence is never permission."""

from typing import Literal, Self

from pydantic import Field, field_validator, model_validator

from otarchguard.domain import Record
from otarchguard.ingestion.numbers import NumericToken
from otarchguard.loading import YamlValue

type EntityKind = Literal["asset", "zone", "interface", "connection"]
type InventoryValue = (
    None | bool | int | NumericToken | str | list[InventoryValue] | dict[str, InventoryValue]
)
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


class ReferenceMapping(ImportRecord):
    table: str


class FieldMapping(ImportRecord):
    path: str
    value_type: Literal["string", "integer", "number", "boolean"] = "string"
    normalize: Literal["exact", "trim", "lower", "upper", "ipv4_interface"] = "exact"
    missing: Literal["review", "error"] = "review"
    prefix: str = Field(default="", max_length=64)
    reference: ReferenceMapping | None = None


class TableMapping(ImportRecord):
    name: str = Field(min_length=1, max_length=128)
    collection: str = Field(max_length=256)
    entity: EntityKind
    header_row: int = Field(default=1, ge=1, le=1001)
    fields: dict[str, FieldMapping] = Field(min_length=1, max_length=64)
    constants: dict[str, str] = Field(default_factory=dict, max_length=64)
    formula_policy: Literal["require_correction"] = "require_correction"


class StructuredProfile(ImportRecord):
    profile_version: Literal[2]
    adapter: Literal["json", "xlsx", "netbox-offline-v1"]
    tables: tuple[TableMapping, ...] = Field(min_length=1, max_length=16)


class SourceDocument(ImportRecord):
    source_id: str
    sha256: str
    name: str
    format: Literal["csv", "tsv", "json", "xlsx"]
    byte_count: int
    encoding: str
    delimiter: str


class SourceLocation(ImportRecord):
    row: int
    line_start: int
    line_end: int
    column: int
    header: str


class StructuredLocation(ImportRecord):
    collection: str
    record: str
    pointer: str | None = None
    sheet: str | None = None
    sheet_id: str | None = None
    cell: str | None = None


class EvidenceField(ImportRecord):
    field: str
    raw_value: InventoryValue
    normalized_value: str
    transformation: str
    state: EvidenceState
    location: SourceLocation | StructuredLocation | None = None

    @field_validator("raw_value", mode="before")
    @classmethod
    def numeric_evidence(cls, value: object) -> object:
        if isinstance(value, dict) and set(value) == {"numeric_token", "numeric_category"}:
            return NumericToken.model_validate(value)
        return value


class StructuredEvidenceField(EvidenceField):
    source_value_type: Literal[
        "missing",
        "null",
        "string",
        "integer",
        "number",
        "boolean",
        "array",
        "object",
        "formula",
        "profile_constant",
    ]

    @model_validator(mode="after")
    def numeric_category_matches(self) -> Self:
        if self.source_value_type in {"integer", "number"}:
            category = (
                "integer"
                if type(self.raw_value) is int
                else self.raw_value.numeric_category
                if isinstance(self.raw_value, NumericToken)
                else None
            )
            if category != self.source_value_type:
                raise ValueError("Numeric evidence must retain its actual source category")
        return self


class ReferenceEvidence(ImportRecord):
    field: str
    table: str
    source_identity: str
    target_candidate_id: str | None


class StructuredCandidate(ImportRecord):
    candidate_id: str
    row_id: str
    entity: EntityKind
    state: EvidenceState = "UNRESOLVED"
    fields: tuple[StructuredEvidenceField, ...]
    unmapped: dict[str, str]
    ambiguities: tuple[str, ...]
    table: str
    location: StructuredLocation
    required_corrections: tuple[str, ...] = ()
    references: tuple[ReferenceEvidence, ...] = ()


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
    code: Literal["DUPLICATE_IDENTITY", "DUPLICATE_NAME", "REUSED_ADDRESS"] = "DUPLICATE_IDENTITY"
    identity: str
    candidate_ids: tuple[str, ...]


class ImportDraft(ImportRecord):
    import_version: Literal[1, 2, 3]
    source: SourceDocument
    profile: MappingProfile | StructuredProfile
    headers: tuple[str, ...]
    candidates: tuple[ImportCandidate | StructuredCandidate, ...] = Field(max_length=1000)
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
