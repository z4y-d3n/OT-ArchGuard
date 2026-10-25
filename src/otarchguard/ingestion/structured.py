"""Shared bounded structured-source extraction and explicit mapping, without I/O output."""

import ipaddress
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import cast

from otarchguard.diagnostics import check_limit, fail
from otarchguard.ingestion.numbers import NumericToken, numeric_text
from otarchguard.ingestion.records import (
    DocumentEvidence,
    DocumentProfile,
    GraphEvidence,
    GraphProfile,
    ImportCandidate,
    ImportConflict,
    ImportDiagnostic,
    ImportDraft,
    ReferenceEvidence,
    SourceDocument,
    StructuredCandidate,
    StructuredEvidenceField,
    StructuredLocation,
    StructuredProfile,
)
from otarchguard.ingestion.records import InventoryValue as YamlValue
from otarchguard.ingestion.tabular import IMPORT_LIMITS, _safe_text, digest

# Excluded even if explicitly requested. Unknown values never enter a new-format draft.
_PRIVATE = re.compile(
    r"password|passwd|secret|token|credential|authorization|api.?key|private.?key|notes|comments|url",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class StructuredLimits:
    source_bytes: int = 1024 * 1024
    depth: int = 24
    records: int = 1000
    fields: int = 64
    scalars: int = 32_000
    text: int = 4096
    number_characters: int = 64
    diagnostics: int = 200


STRUCTURED_LIMITS = StructuredLimits()


@dataclass(frozen=True, slots=True)
class Value:
    raw: YamlValue
    location: StructuredLocation
    missing: bool = False
    issue: str | None = None
    rule: str = "source"


@dataclass(frozen=True, slots=True)
class ExtractedRow:
    location: StructuredLocation
    values: dict[str, Value]
    omitted: int


def pointer_parts(pointer: str) -> tuple[str, ...]:
    if pointer == "":
        return ()
    if not pointer.startswith("/") or re.search(r"~(?![01])", pointer):
        fail("IMPORT_POINTER", "$", "Use an RFC 6901 pointer: empty root or /escaped/path.")
    return tuple(p.replace("~1", "/").replace("~0", "~") for p in pointer[1:].split("/"))


def pointer_token(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def lookup(value: YamlValue, pointer: str) -> tuple[YamlValue, bool]:
    current = value
    for part in pointer_parts(pointer):
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif (
            isinstance(current, list)
            and re.fullmatch(r"0|[1-9][0-9]*", part)
            and len(part) < 8
            and int(part) < len(current)
        ):
            current = current[int(part)]
        else:
            return None, True
    return current, False


def validate_profile(profile: StructuredProfile | GraphProfile | DocumentProfile) -> None:
    from otarchguard.ingestion.workflow import _allowed

    names = [t.name for t in profile.tables]
    if len(set(names)) != len(names):
        fail("IMPORT_MAPPING", "$", "Table mapping names must be unique.")
    if len({t.collection for t in profile.tables}) != len(profile.tables):
        fail("IMPORT_MAPPING", "$", "Select a collection or sheet only once per profile.")
    for table in profile.tables:
        if "id" not in table.fields or table.fields["id"].reference is not None:
            fail("IMPORT_MAPPING", table.name, "An explicit non-reference source id is required.")
        if not (set(table.fields) | set(table.constants)) <= _allowed(table.entity):
            fail("IMPORT_MAPPING", table.name, "Unsupported native field for this entity.")
        if set(table.fields) & set(table.constants):
            fail("IMPORT_MAPPING", table.name, "A mapped field cannot also be a constant.")
        if len({f.path for f in table.fields.values()}) != len(table.fields):
            fail("IMPORT_MAPPING", table.name, "Duplicate mapped source fields are forbidden.")
        if profile.adapter not in {"xlsx", "drawio", "graphml", "txt", "md", "docx", "pptx"}:
            pointer_parts(table.collection)
        for field in table.fields.values():
            if profile.adapter != "xlsx":
                pointer_parts(field.path)
            if _PRIVATE.search(field.path):
                fail(
                    "IMPORT_PRIVATE_FIELD", table.name, "Sensitive/free-form metadata is excluded."
                )
            if field.reference is not None and field.reference.table not in names:
                fail("IMPORT_MAPPING", table.name, "Reference target table is not selected.")
            if field.reference is not None:
                native_field = next(k for k, v in table.fields.items() if v is field)
                target = next(t for t in profile.tables if t.name == field.reference.table)
                expected = {
                    ("asset", "zone_id"): "zone",
                    ("interface", "asset_id"): "asset",
                    ("interface", "placement_zone_id"): "zone",
                }
                if expected.get((table.entity, native_field)) != target.entity:
                    fail(
                        "IMPORT_MAPPING",
                        table.name,
                        "Reference field/target entity combination unsupported.",
                    )
            _safe_text(field.path)
            check_limit("import_field_characters", len(field.path), IMPORT_LIMITS.field_characters)
        for value in table.constants.values():
            _safe_text(value)
            check_limit("import_field_characters", len(value), IMPORT_LIMITS.field_characters)
            if "://" in value and "@" in value:
                fail("IMPORT_PRIVATE_FIELD", table.name, "Authenticated URLs are excluded.")


def map_extracted(
    source: SourceDocument,
    profile: StructuredProfile | GraphProfile | DocumentProfile,
    tables: dict[str, tuple[ExtractedRow, ...]],
    diagnostics: list[ImportDiagnostic],
    *,
    graph: GraphEvidence | None = None,
    document: DocumentEvidence | None = None,
) -> ImportDraft:
    from otarchguard.ingestion.workflow import _check_draft_envelope, _field_problems

    validate_profile(profile)
    candidates: list[StructuredCandidate] = []
    occurrences: Counter[str] = Counter()
    for table in sorted(profile.tables, key=lambda t: t.name):
        for row in tables[table.name]:
            fields: list[StructuredEvidenceField] = []
            required: list[str] = []
            problems: list[str] = []
            for name, mapping in sorted(table.fields.items()):
                value = row.values[name]
                raw = value.raw
                if isinstance(raw, str) and "://" in raw and "@" in raw:
                    fail("IMPORT_PRIVATE_FIELD", table.name, "Authenticated URLs are excluded.")
                issue = value.issue
                expected = {"string": str, "integer": int, "number": int, "boolean": bool}
                expected_type = expected[mapping.value_type]
                type_ok = type(raw) is expected_type
                if isinstance(raw, NumericToken):
                    type_ok = mapping.value_type == "number" or (
                        mapping.value_type == "integer" and raw.numeric_category == "integer"
                    )
                if value.missing and mapping.missing == "error":
                    fail("IMPORT_MISSING_FIELD", table.name, "Required mapped field is absent.")
                if value.missing:
                    issue = "Missing mapped value; supply a literal correction."
                elif not type_ok:
                    issue = "Value type differs from profile (null/containers are not text)."
                normalized = ""
                if type_ok:
                    normalized = (
                        numeric_text(raw)
                        if isinstance(raw, NumericToken) or type(raw) is int
                        else str(raw).lower()
                        if type(raw) is bool
                        else str(raw)
                    )
                    if mapping.normalize == "trim":
                        normalized = normalized.strip()
                    elif mapping.normalize == "lower":
                        normalized = normalized.lower()
                    elif mapping.normalize == "upper":
                        normalized = normalized.upper()
                    elif mapping.normalize == "ipv4_interface":
                        try:
                            if "/" not in normalized:
                                raise ValueError
                            normalized = str(ipaddress.IPv4Interface(normalized))
                        except ValueError:
                            issue = "Invalid IPv4 interface; IPv6 is unsupported."
                if type_ok and not issue:
                    normalized = mapping.prefix + normalized
                if issue:
                    required.append(name)
                    problems.append(f"{name}: {issue}")
                    normalized = ""
                fields.append(
                    StructuredEvidenceField.model_validate(
                        dict(
                            field=name,
                            raw_value=raw if not isinstance(raw, (dict, list)) or not raw else None,
                            normalized_value=normalized,
                            transformation=(
                                f"{value.rule}:{mapping.value_type}:"
                                f"{mapping.normalize}:prefix={mapping.prefix}"
                            ),
                            state="UNSUPPORTED" if issue else "EXPLICIT_SOURCE_VALUE",
                            location=value.location,
                            source_value_type=(
                                "missing"
                                if value.missing
                                else "formula"
                                if value.issue and value.issue.startswith("Formula")
                                else raw.numeric_category
                                if isinstance(raw, NumericToken)
                                else {
                                    str: "string",
                                    bool: "boolean",
                                    int: "integer",
                                    list: "array",
                                    dict: "object",
                                    type(None): "null",
                                }[type(raw)]
                            ),
                        )
                    )
                )
            fields.extend(
                StructuredEvidenceField(
                    field=name,
                    raw_value=value,
                    normalized_value=value,
                    transformation="profile_constant",
                    state="CANDIDATE_INFERENCE",
                    source_value_type="profile_constant",
                )
                for name, value in sorted(table.constants.items())
            )
            fields.sort(key=lambda f: f.field)
            values = {f.field: f.normalized_value for f in fields}
            problems.extend(_field_problems(table.entity, values))
            # Locations/source bytes/unknown fields are excluded. Array index is deliberately
            # included: this contract does not assert that arbitrary array order is irrelevant.
            semantic = {
                "table": table.name,
                "record": [row.location.collection, row.location.record]
                if isinstance(profile, GraphProfile)
                else row.location.record
                if profile.adapter != "xlsx"
                else None,
                "fields": [f.model_dump(exclude={"location"}) for f in fields],
                "profile": table.model_dump(mode="json"),
            }
            key = digest(semantic)
            occurrences[key] += 1
            row_id = f"row_{key}_{occurrences[key]}"
            candidate = StructuredCandidate(
                candidate_id="candidate_" + digest([row_id, table.entity]),
                row_id=row_id,
                entity=table.entity,
                fields=tuple(fields),
                unmapped={"excluded_field_count": str(row.omitted)} if row.omitted else {},
                ambiguities=tuple(problems),
                table=table.name,
                location=row.location,
                required_corrections=tuple(sorted(required)),
            )
            candidates.append(candidate)
            for problem in problems:
                diagnostics.append(
                    ImportDiagnostic(code="REVIEW_REQUIRED", row_id=row_id, message=problem)
                )
            check_limit("import_diagnostics", len(diagnostics), STRUCTURED_LIMITS.diagnostics)
            check_limit("import_candidates", len(candidates), STRUCTURED_LIMITS.records)

    # Resolve only explicit source identities, with a typed table target; never names/IPs.
    indexes: dict[tuple[str, str], list[StructuredCandidate]] = defaultdict(list)
    mappings = {t.name: t for t in profile.tables}
    for candidate in candidates:
        identity = next(f.normalized_value for f in candidate.fields if f.field == "id")
        if identity:
            indexes[candidate.table, identity].append(candidate)
    resolved: list[StructuredCandidate] = []
    for candidate in candidates:
        references: list[ReferenceEvidence] = []
        required = list(candidate.required_corrections)
        problems = list(candidate.ambiguities)
        for field, mapping in sorted(mappings[candidate.table].fields.items()):
            if mapping.reference is None:
                continue
            identity = next(f.normalized_value for f in candidate.fields if f.field == field)
            matches = indexes.get((mapping.reference.table, identity), [])
            target = matches[0] if len(matches) == 1 else None
            references.append(
                ReferenceEvidence(
                    field=field,
                    table=mapping.reference.table,
                    source_identity=_reference_text(
                        next(f.raw_value for f in candidate.fields if f.field == field)
                    ),
                    target_candidate_id=target.candidate_id if target else None,
                )
            )
            if target is None:
                required.append(field)
                problems.append(f"{field}: unresolved or ambiguous within-source reference.")
                diagnostics.append(
                    ImportDiagnostic(
                        code="UNRESOLVED_REFERENCE",
                        row_id=candidate.row_id,
                        field=field,
                        message=problems[-1],
                    )
                )
        resolved.append(
            candidate.model_copy(
                update={
                    "references": tuple(references),
                    "required_corrections": tuple(sorted(set(required))),
                    "ambiguities": tuple(problems),
                }
            )
        )
    conflicts: list[ImportConflict] = []
    for field, code in (
        ("id", "DUPLICATE_IDENTITY"),
        ("name", "DUPLICATE_NAME"),
        ("ipv4", "REUSED_ADDRESS"),
    ):
        groups: dict[tuple[str, str], list[str]] = defaultdict(list)
        for candidate in resolved:
            grouped_value = next(
                (f.normalized_value for f in candidate.fields if f.field == field), ""
            )
            if grouped_value and field == "ipv4":
                try:
                    grouped_value = str(ipaddress.IPv4Interface(grouped_value).ip)
                except ValueError:
                    pass  # Native validation rejects invalid confirmed addresses.
            if grouped_value:
                groups[candidate.entity, grouped_value].append(candidate.candidate_id)
        for (_, identity), ids in sorted(groups.items()):
            if len(ids) > 1:
                conflicts.append(
                    ImportConflict.model_validate(
                        {
                            "code": code,
                            "identity": identity,
                            "candidate_ids": sorted(ids),
                        }
                    )
                )
    check_limit("import_diagnostics", len(diagnostics), STRUCTURED_LIMITS.diagnostics)
    draft = ImportDraft(
        import_version=5 if document is not None else 4 if graph is not None else 3,
        graph=graph,
        document=document,
        source=source,
        profile=profile,
        headers=tuple(sorted(t.collection for t in profile.tables)),
        candidates=cast(
            tuple[ImportCandidate | StructuredCandidate, ...],
            tuple(sorted(resolved, key=lambda c: c.candidate_id)),
        ),
        conflicts=tuple(conflicts),
        diagnostics=tuple(
            sorted(diagnostics, key=lambda d: (d.row_id or "", d.field or "", d.code, d.message))
        ),
    )
    _check_draft_envelope(draft)
    return draft


def _reference_text(value: YamlValue) -> str:
    return value.numeric_token if isinstance(value, NumericToken) else str(value)
