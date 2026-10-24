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


class GraphProfile(ImportRecord):
    profile_version: Literal[3]
    adapter: Literal["graphml", "drawio"]
    scopes: tuple[str, ...] = Field(min_length=1, max_length=16)
    tables: tuple[TableMapping, ...] = Field(min_length=1, max_length=3)
    connections: Literal["evidence_only"]
    unknown_policy: Literal["diagnose"]


class DocumentProfile(ImportRecord):
    profile_version: Literal[4]
    adapter: Literal["txt", "md", "docx", "pptx"]
    select: tuple[str, ...] = Field(min_length=1, max_length=64)
    tables: tuple[TableMapping, ...] = Field(default=(), max_length=16)


class SourceDocument(ImportRecord):
    source_id: str
    sha256: str
    name: str
    format: Literal["csv", "tsv", "json", "xlsx", "graphml", "drawio", "txt", "md", "docx", "pptx"]
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


class GraphPage(ImportRecord):
    scope_id: str
    name: str
    compression: Literal["none", "raw-deflate"]


class GraphNode(ImportRecord):
    scope_id: str
    element_id: str
    kind: Literal["node", "group", "text", "layer"]
    label: str
    parent: str | None = None
    geometry: dict[str, str] = Field(default_factory=dict, max_length=8)
    styles: dict[str, str] = Field(default_factory=dict, max_length=16)


class GraphEdge(ImportRecord):
    scope_id: str
    element_id: str
    source: str | None
    destination: str | None
    label: str
    direction: str
    direction_origin: Literal["graph_default", "edge_override", "arrowheads"]
    parent: str | None = None
    unresolved: tuple[str, ...] = ()
    relationship: Literal["diagram_evidence_only"] = "diagram_evidence_only"


class GraphEvidence(ImportRecord):
    adapter: Literal["graphml", "drawio"]
    subset_version: Literal[1] = 1
    pages: tuple[GraphPage, ...] = Field(max_length=16)
    nodes: tuple[GraphNode, ...] = Field(max_length=1000)
    edges: tuple[GraphEdge, ...] = Field(max_length=1000)
    keys: tuple[str, ...] = Field(max_length=64)
    expanded_bytes: int
    selected_scopes: tuple[str, ...]


class ImportConflict(ImportRecord):
    code: Literal["DUPLICATE_IDENTITY", "DUPLICATE_NAME", "REUSED_ADDRESS"] = "DUPLICATE_IDENTITY"
    identity: str
    candidate_ids: tuple[str, ...]


class DocumentObservation(ImportRecord):
    observation_id: str
    category: Literal["heading", "paragraph", "list", "fenced_text", "table_cell", "slide_text"]
    text: str = Field(max_length=4096)
    location: StructuredLocation


class DocumentEvidence(ImportRecord):
    subset_version: Literal[1] = 1
    observations: tuple[DocumentObservation, ...] = Field(max_length=4000)
    summary: dict[str, int] = Field(max_length=16)

    @model_validator(mode="after")
    def located_identity(self) -> Self:
        from otarchguard.ingestion.tabular import _safe_text, digest

        identities = [o.observation_id for o in self.observations]
        if len(set(identities)) != len(identities):
            raise ValueError("Duplicate document observation identity")
        if self.summary.get("selected_observations") != len(self.observations):
            raise ValueError("Document coverage summary differs from retained observations")
        for observation in self.observations:
            expected = "observation_" + digest(
                [observation.location.model_dump(), observation.category]
            )
            if observation.observation_id != expected:
                raise ValueError("Document observation identity and location disagree")
            _safe_text(observation.text)
        return self


class ImportDraft(ImportRecord):
    import_version: Literal[1, 2, 3, 4, 5]
    source: SourceDocument
    profile: MappingProfile | StructuredProfile | GraphProfile | DocumentProfile
    headers: tuple[str, ...]
    candidates: tuple[ImportCandidate | StructuredCandidate, ...] = Field(max_length=1000)
    conflicts: tuple[ImportConflict, ...] = Field(max_length=1000)
    diagnostics: tuple[ImportDiagnostic, ...] = Field(max_length=200)
    graph: GraphEvidence | None = Field(default=None, exclude_if=lambda value: value is None)
    document: DocumentEvidence | None = Field(default=None, exclude_if=lambda value: value is None)

    @model_validator(mode="after")
    def graph_contract(self) -> Self:
        if (self.import_version == 5) != isinstance(self.profile, DocumentProfile):
            raise ValueError("Document profiles require draft version 5")
        if (self.import_version == 5) != (self.document is not None):
            raise ValueError("Document drafts require documentary observations")
        if (self.import_version == 4) != isinstance(self.profile, GraphProfile):
            raise ValueError("Graph profiles require draft version 4")
        if (self.import_version == 4) != (self.graph is not None):
            raise ValueError("Graph drafts require graphical evidence")
        return self


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
