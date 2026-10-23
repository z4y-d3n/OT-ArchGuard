"""Explicit mapping, review and native-validated inventory emission."""

import json
import os
import re
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import cast

import yaml
from pydantic import ValidationError

from otarchguard.api import validate_bytes
from otarchguard.contract import RESOURCE_LIMITS
from otarchguard.diagnostics import check_limit, fail
from otarchguard.domain import Asset, Interface, Record, Zone
from otarchguard.ingestion.records import (
    EntityKind,
    EvidenceField,
    ImportCandidate,
    ImportConflict,
    ImportDiagnostic,
    ImportDraft,
    MappingProfile,
    OwnerDecisions,
    SourceLocation,
)
from otarchguard.ingestion.tabular import (
    IMPORT_LIMITS,
    DelimitedAdapter,
    SourceTable,
    digest,
    read_regular,
)
from otarchguard.loading import YamlValue, load_bytes

_MODELS: dict[str, type[Record]] = {"asset": Asset, "zone": Zone, "interface": Interface}
_COLLECTIONS = {"asset": "assets", "zone": "zones", "interface": "interfaces"}
_CONNECTION_FIELDS = {"id", "source", "destination", "direction", "label", "protocol"}


def serialize(value: Record | dict[str, object]) -> bytes:
    payload = value.model_dump(mode="json") if isinstance(value, Record) else value
    return (json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=True) + "\n").encode()


def load_record[T: Record](path: Path, record_type: type[T]) -> T:
    value = load_bytes(read_regular(path, RESOURCE_LIMITS.input_bytes))
    try:
        return record_type.model_validate(value)
    except (ValidationError, ValueError):
        fail("IMPORT_CONTROL", "$", "Invalid versioned import control document; see import docs.")


def _allowed(entity: EntityKind) -> set[str]:
    return set(_MODELS[entity].model_fields) if entity != "connection" else _CONNECTION_FIELDS


def _validate_profile(profile: MappingProfile, table: SourceTable) -> None:
    allowed = _allowed(profile.entity)
    if not (set(profile.fields) | set(profile.constants)) <= allowed:
        fail("IMPORT_MAPPING", "$", "Mapping contains fields outside the selected entity subset.")
    if set(profile.fields) & set(profile.constants):
        fail("IMPORT_MAPPING", "$", "A field cannot be both a column mapping and a constant.")
    if len(set(profile.fields.values())) != len(profile.fields):
        fail("IMPORT_MAPPING", "$", "Each source column can map to only one field.")
    if not set(profile.fields.values()) <= set(table.headers):
        fail("IMPORT_MAPPING", "$", "Mapped column is missing; header matching is exact.")
    if "id" not in profile.fields:
        fail("IMPORT_MAPPING", "$", "An explicit source column must supply the stable entity id.")
    for value in (*profile.constants.values(), *profile.fields.values()):
        check_limit("import_mapping_characters", len(value), IMPORT_LIMITS.field_characters)


def _field_problems(entity: EntityKind, fields: dict[str, str]) -> tuple[str, ...]:
    if entity == "connection":
        return (
            "Evidence-only connection: direction and authorization require separate declarations.",
        )
    try:
        _MODELS[entity].model_validate(fields)
    except ValidationError as error:
        names = sorted({str(e["loc"][0]) for e in error.errors()})
        return ("Missing or invalid native fields: " + ", ".join(names) + ".",)
    return ()


def _check_draft_envelope(draft: ImportDraft) -> None:
    """Generated JSON must fit the exact YAML loader budgets used by review/emit."""
    check_limit("import_draft_bytes", len(serialize(draft)), RESOURCE_LIMITS.input_bytes)

    def event_count(value: object, depth: int = 0) -> int:
        # JSON has one YAML scalar per key/value and two events per collection.
        # Stream/document start/end contribute another four events below.
        if isinstance(value, (dict, list)):
            depth += 1
            check_limit("nesting_depth", depth, RESOURCE_LIMITS.nesting_depth)
        if isinstance(value, dict):
            return 2 + sum(1 + event_count(child, depth) for child in value.values())
        if isinstance(value, list):
            return 2 + sum(event_count(child, depth) for child in value)
        return 1

    check_limit(
        "parser_events",
        4 + event_count(draft.model_dump(mode="json")),
        RESOURCE_LIMITS.parser_events,
    )


def map_table(table: SourceTable, profile: MappingProfile) -> ImportDraft:
    _validate_profile(profile, table)
    candidates: list[ImportCandidate] = []
    diagnostics: list[ImportDiagnostic] = []
    identities: dict[str, list[str]] = defaultdict(list)
    indexes = {name: i for i, name in enumerate(table.headers)}
    for row in table.rows:
        fields: list[EvidenceField] = []
        for field, header in sorted(profile.fields.items()):
            index = indexes[header]
            value = row.values[index]
            fields.append(
                EvidenceField(
                    field=field,
                    raw_value=value,
                    normalized_value=value,
                    transformation="exact",
                    state="EXPLICIT_SOURCE_VALUE",
                    location=SourceLocation(
                        row=row.row,
                        line_start=row.line_start,
                        line_end=row.line_end,
                        column=index + 1,
                        header=header,
                    ),
                )
            )
        fields.extend(
            EvidenceField(
                field=field,
                raw_value=value,
                normalized_value=value,
                transformation="profile_constant",
                state="CANDIDATE_INFERENCE",
            )
            for field, value in sorted(profile.constants.items())
        )
        fields.sort(key=lambda f: f.field)
        values = {field.field: field.normalized_value for field in fields}
        ambiguities = _field_problems(profile.entity, values)
        candidate_id = "candidate_" + digest(
            {
                "row_id": row.row_id,
                "entity": profile.entity,
                "fields": values,
                "profile": profile.model_dump(mode="json"),
            }
        )
        identities[values.get("id", "")].append(candidate_id)
        unmapped = {
            header: row.values[index]
            for header, index in indexes.items()
            if header not in profile.fields.values()
        }
        candidates.append(
            ImportCandidate(
                candidate_id=candidate_id,
                row_id=row.row_id,
                entity=profile.entity,
                fields=tuple(fields),
                unmapped=unmapped,
                ambiguities=ambiguities,
            )
        )
        for problem in ambiguities:
            diagnostics.append(
                ImportDiagnostic(
                    code="REVIEW_REQUIRED",
                    row_id=row.row_id,
                    message=problem,
                )
            )
        for header, value in zip(table.headers, row.values, strict=True):
            if value.lstrip().startswith(("=", "+", "-", "@")):
                diagnostics.append(
                    ImportDiagnostic(
                        code="FORMULA_LIKE_TEXT",
                        row_id=row.row_id,
                        field=header,
                        message="Inert text retained; review before copying to a spreadsheet.",
                    )
                )
        check_limit("import_diagnostics", len(diagnostics), IMPORT_LIMITS.diagnostics)
    conflicts = tuple(
        ImportConflict(identity=identity, candidate_ids=tuple(sorted(ids)))
        for identity, ids in sorted(identities.items())
        if len(ids) > 1
    )
    draft = ImportDraft(
        import_version=1,
        source=table.source,
        profile=profile,
        headers=table.headers,
        candidates=tuple(sorted(candidates, key=lambda c: c.candidate_id)),
        conflicts=conflicts,
        diagnostics=tuple(
            sorted(diagnostics, key=lambda d: (d.row_id or "", d.field or "", d.code))
        ),
    )
    _check_draft_envelope(draft)
    return draft


def create_draft(source: Path, profile: MappingProfile) -> ImportDraft:
    table = DelimitedAdapter().read(source, delimiter=profile.delimiter, encoding=profile.encoding)
    return map_table(table, profile)


def draft_sha256(draft: ImportDraft) -> str:
    return digest(draft.model_dump(mode="json"))


def review_template(draft: ImportDraft) -> OwnerDecisions:
    return OwnerDecisions.model_validate(
        {
            "decisions_version": 1,
            "draft_sha256": draft_sha256(draft),
            "reviewer": "",
            "model_confirmed": False,
            "model_rationale": "",
            "model": {},
            "resolutions": [
                {
                    "candidate_id": c.candidate_id,
                    "decision": "UNRESOLVED",
                    "corrections": {},
                    "rationale": "",
                }
                for c in draft.candidates
            ],
        }
    )


def review_summary(draft: ImportDraft) -> dict[str, object]:
    return {
        "import_version": 1,
        "draft_sha256": draft_sha256(draft),
        "state": "UNRESOLVED",
        "source": draft.source.model_dump(),
        "candidates": [c.model_dump(mode="json") for c in draft.candidates],
        "conflicts": [c.model_dump() for c in draft.conflicts],
        "diagnostics": [d.model_dump() for d in draft.diagnostics],
        "coverage": {
            "rows": len(draft.candidates),
            "mapped_fields_per_row": len(draft.profile.fields),
            "unmapped_columns": sorted(set(draft.headers) - set(draft.profile.fields.values())),
        },
        "required_actions": [
            "Confirm or reject every candidate, giving a rationale; correct incomplete fields.",
            "Resolve all duplicate identities by correction or rejection.",
            "Supply and confirm the remaining native model collections and SUC metadata.",
            "Connection candidates cannot be emitted; reject them explicitly in this gate.",
            "Emit with the original source; any source/draft change requires fresh review.",
        ],
    }


def emit_artifacts(draft: ImportDraft, decisions: OwnerDecisions, source: Path) -> dict[str, bytes]:
    """No writes until the original source, all decisions and the entire model validate."""
    reproduced = create_draft(source, draft.profile)
    if serialize(reproduced) != serialize(draft):
        fail("IMPORT_SOURCE_CHANGED", "$", "Source and draft disagree; map and review again.")
    if decisions.draft_sha256 != draft_sha256(draft):
        fail("IMPORT_STALE_REVIEW", "$", "Decisions do not bind this exact draft.")
    if (
        not decisions.model_confirmed
        or not decisions.reviewer.strip()
        or not decisions.model_rationale.strip()
    ):
        fail("IMPORT_REVIEW", "$", "Explicit reviewer, model confirmation and rationale required.")
    resolutions = {r.candidate_id: r for r in decisions.resolutions}
    if len(resolutions) != len(decisions.resolutions) or set(resolutions) != {
        c.candidate_id for c in draft.candidates
    }:
        fail("IMPORT_REVIEW", "$", "Exactly one decision is required for every candidate.")
    accepted: list[dict[str, str]] = []
    provenance: list[dict[str, object]] = []
    collection = _COLLECTIONS.get(draft.profile.entity)
    if collection is not None and collection in decisions.model:
        fail("IMPORT_REVIEW", "$", "Owner model context must omit the imported collection.")
    for candidate in draft.candidates:
        resolution = resolutions[candidate.candidate_id]
        if resolution.decision == "UNRESOLVED" or not resolution.rationale.strip():
            fail("IMPORT_UNRESOLVED", "$", "Every candidate needs a decision and rationale.")
        if not set(resolution.corrections) <= _allowed(candidate.entity):
            fail("IMPORT_CORRECTION", "$", "Correction names must be supported entity fields.")
        if resolution.decision == "OWNER_REJECTED" and resolution.corrections:
            fail("IMPORT_CORRECTION", "$", "Rejected candidates cannot contain corrections.")
        values = {f.field: f.normalized_value for f in candidate.fields}
        values.update(resolution.corrections)
        for value in values.values():
            check_limit("import_field_characters", len(value), IMPORT_LIMITS.field_characters)
        if resolution.decision == "OWNER_CONFIRMED":
            if candidate.entity == "connection":
                fail("IMPORT_RELATIONSHIP", "$", "Evidence-only connections cannot be promoted.")
            if _field_problems(candidate.entity, values):
                fail("IMPORT_CORRECTION", "$", "Confirmed entity still has missing/invalid fields.")
            accepted.append(values)
        provenance.append(
            {
                "candidate": candidate.model_dump(mode="json"),
                "resolution": resolution.model_dump(mode="json"),
                "model_collection": collection
                if resolution.decision == "OWNER_CONFIRMED"
                else None,
                "model_id": values.get("id") if resolution.decision == "OWNER_CONFIRMED" else None,
            }
        )
    if len({item["id"] for item in accepted}) != len(accepted):
        fail("IMPORT_CONFLICT", "$", "Confirmed identities still conflict; correct or reject.")
    model = dict(decisions.model)
    if collection is not None:
        model[collection] = cast(YamlValue, sorted(accepted, key=lambda a: a["id"]))
    data = yaml.safe_dump(model, allow_unicode=True, sort_keys=True).encode("utf-8")
    validated = validate_bytes(data)
    normalized_yaml = yaml.safe_dump(
        json.loads(validated.canonical_json),
        allow_unicode=True,
        sort_keys=True,
    ).encode("utf-8")
    # Verify the exact published bytes, not merely the pre-normalization structure.
    if validate_bytes(normalized_yaml).sha256 != validated.sha256:
        fail(
            "IMPORT_INTERNAL", "$", "Emitted model identity does not match validated declarations."
        )
    sidecar: dict[str, object] = {
        "import_version": 1,
        "draft_sha256": draft_sha256(draft),
        "source": draft.source.model_dump(),
        "profile": draft.profile.model_dump(mode="json"),
        "model_sha256": validated.sha256,
        "reviewer": decisions.reviewer,
        "model_rationale": decisions.model_rationale,
        "model_confirmed": True,
        "owner_declarations": decisions.model,
        "records": provenance,
        "conflicts": [c.model_dump() for c in draft.conflicts],
        "diagnostics": [d.model_dump() for d in draft.diagnostics],
        "scope": "Owner-declared architecture only; no deployed completeness or discovery claim.",
    }
    return {
        "architecture.yaml": normalized_yaml,
        "architecture.provenance.json": serialize(sidecar),
    }


def write_new_file(path: Path, data: bytes) -> None:
    """Atomic no-clobber rename on Windows, hard-link publication on POSIX."""
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent, prefix=".otarchguard-", delete=False
        ) as f:
            temporary = Path(f.name)
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        if os.name == "nt":
            # Windows rename refuses an existing destination, including a symlink.
            os.rename(temporary, path)
        else:
            os.link(temporary, path)
    except OSError:
        fail("IMPORT_OUTPUT", "$", "Cannot create output; existing files are never overwritten.")
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def write_new_bundle(path: Path, artifacts: dict[str, bytes]) -> None:
    """Stage the complete validated bundle beside its destination, then rename once."""
    if path.exists() or path.is_symlink():
        fail("IMPORT_OUTPUT", "$", "Output directory already exists; choose a new destination.")
    if set(artifacts) != {"architecture.yaml", "architecture.provenance.json"}:
        fail("IMPORT_OUTPUT", "$", "An emitted bundle must contain the two expected artifacts.")
    try:
        with tempfile.TemporaryDirectory(dir=path.parent, prefix=".otarchguard-") as staging:
            stage = Path(staging)
            for name, data in artifacts.items():
                if re.fullmatch(r"[a-z.]+", name) is None:
                    fail("IMPORT_OUTPUT", "$", "Invalid bundle artifact name.")
                with (stage / name).open("xb") as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
            if path.exists() or path.is_symlink():
                fail("IMPORT_OUTPUT", "$", "Output directory already exists.")
            os.rename(stage, path)
    except OSError:
        fail("IMPORT_OUTPUT", "$", "Cannot publish the complete local bundle.")
