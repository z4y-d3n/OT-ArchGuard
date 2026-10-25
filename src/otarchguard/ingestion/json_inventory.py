"""Strict, bounded UTF-8 JSON inventories; paths and adapter selection are explicit."""

import hashlib
import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import cast

from otarchguard.diagnostics import check_limit, fail
from otarchguard.ingestion.numbers import NumericToken, parse_number
from otarchguard.ingestion.records import (
    ImportDiagnostic,
    ImportDraft,
    SourceDocument,
    StructuredLocation,
    StructuredProfile,
)
from otarchguard.ingestion.records import InventoryValue as YamlValue
from otarchguard.ingestion.structured import (
    STRUCTURED_LIMITS,
    ExtractedRow,
    StructuredLimits,
    Value,
    lookup,
    map_extracted,
    pointer_parts,
    pointer_token,
    validate_profile,
)
from otarchguard.ingestion.tabular import _safe_text, read_regular


def parse_json(data: bytes, limits: StructuredLimits = STRUCTURED_LIMITS) -> YamlValue:
    check_limit("import_bytes", len(data), limits.source_bytes)
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        fail("IMPORT_JSON", "$", "JSON must be strict UTF-8 without a BOM.")
    # Bound nesting before the recursive standard parser allocates a tree.
    depth = 0
    quoted = escaped = False
    for character in text:
        if quoted:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                quoted = False
        elif character == '"':
            quoted = True
        elif character in "[{":
            depth += 1
            check_limit("json_depth", depth, limits.depth)
        elif character in "]}":
            depth -= 1

    def pairs(items: list[tuple[str, YamlValue]]) -> dict[str, YamlValue]:
        check_limit("json_fields", len(items), limits.fields)
        result: dict[str, YamlValue] = {}
        for key, value in items:
            if key in result:
                fail("IMPORT_JSON_DUPLICATE", "$", "Duplicate JSON object key.")
            result[key] = value
        return result

    def number(value: str) -> int | NumericToken:
        return parse_number(value, limits.number_characters)

    def invalid(value: str) -> YamlValue:
        fail("IMPORT_JSON_NUMBER", "$", "Nonstandard JSON numbers are forbidden.")

    try:
        document = cast(
            YamlValue,
            json.loads(
                text,
                object_pairs_hook=pairs,
                parse_int=number,
                parse_float=number,
                parse_constant=invalid,
            ),
        )
    except (ValueError, RecursionError):
        fail("IMPORT_JSON", "$", "Malformed strict UTF-8 JSON document.")
    scalars = 0
    containers = 0
    stack = [document]
    while stack:
        value = stack.pop()
        if isinstance(value, dict):
            containers += 1
            stack.extend(value.keys())
            stack.extend(value.values())
        elif isinstance(value, list):
            containers += 1
            check_limit("json_array_items", len(value), limits.records)
            stack.extend(value)
        else:
            scalars += 1
            if isinstance(value, str):
                _safe_text(value)
                check_limit("json_text", len(value), limits.text)
        check_limit("json_scalars", scalars, limits.scalars)
        check_limit("json_containers", containers, limits.scalars)
    return document


def read_json(path: Path) -> tuple[SourceDocument, YamlValue]:
    if path.suffix.lower() != ".json":
        fail("IMPORT_FORMAT", "$", "JSON adapters require a .json source.")
    data = read_regular(path, STRUCTURED_LIMITS.source_bytes)
    document = parse_json(data)
    sha = hashlib.sha256(data).hexdigest()
    return SourceDocument(
        source_id=f"src_{sha}",
        sha256=sha,
        name=path.name,
        format="json",
        byte_count=len(data),
        encoding="utf-8",
        delimiter="",
    ), document


def extract_json(
    document: YamlValue,
    profile: StructuredProfile,
) -> dict[str, tuple[ExtractedRow, ...]]:
    validate_profile(profile)
    tables: dict[str, tuple[ExtractedRow, ...]] = {}
    count = 0
    for table in profile.tables:
        records, missing = lookup(document, table.collection)
        if missing or not isinstance(records, list):
            fail("IMPORT_COLLECTION", table.name, "Select an existing JSON array with a pointer.")
        extracted: list[ExtractedRow] = []
        for index, record in enumerate(records):
            count += 1
            check_limit("import_records", count, STRUCTURED_LIMITS.records)
            if not isinstance(record, dict):
                fail("IMPORT_JSON_RECORD", table.name, "Inventory array records must be objects.")
            pointer = f"{table.collection}/{index}"
            location = StructuredLocation(
                collection=table.collection, record=pointer, pointer=pointer
            )
            values: dict[str, Value] = {}
            for name, mapping in table.fields.items():
                raw, absent = lookup(record, mapping.path)
                values[name] = Value(
                    raw,
                    location.model_copy(update={"pointer": pointer + mapping.path}),
                    missing=absent,
                )
            mapped_roots = {
                pointer_parts(f.path)[0] for f in table.fields.values() if pointer_parts(f.path)
            }
            extracted.append(ExtractedRow(location, values, len(set(record) - mapped_roots)))
        tables[table.name] = tuple(extracted)
    if count == 0:
        fail("IMPORT_EMPTY", "$", "No records in selected JSON collections.")
    return tables


def create_json_draft(path: Path, profile: StructuredProfile) -> ImportDraft:
    source, document = read_json(path)
    diagnostics: list[ImportDiagnostic] = []
    if profile.adapter == "netbox-offline-v1":
        from otarchguard.ingestion.netbox import validate_netbox

        diagnostics = validate_netbox(document, profile)
    tables = extract_json(document, profile)
    if profile.adapter == "netbox-offline-v1":
        from otarchguard.ingestion.netbox import assigned_addresses

        tables = assigned_addresses(document, profile, tables)
    return map_extracted(source, profile, tables, diagnostics)


def inspect_json(path: Path, adapter: str = "json") -> dict[str, object]:
    source, document = read_json(path)
    diagnostics: list[ImportDiagnostic] = []
    if adapter == "netbox-offline-v1":
        from otarchguard.ingestion.netbox import validate_netbox

        diagnostics = validate_netbox(document, None)
    # Values and unknown keys may be sensitive. Report structure counts, not metadata.
    collections: list[dict[str, object]] = []
    if isinstance(document, list):
        collections.append({"pointer": "", "records": len(document)})
    elif isinstance(document, dict):
        collections.append(
            {
                "pointer": "",
                "object_fields": len(document),
                "array_collections": sum(isinstance(v, list) for v in document.values()),
            }
        )
        for key, value in sorted(document.items()):
            if isinstance(value, list) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", key):
                from otarchguard.ingestion.structured import _PRIVATE

                if not _PRIVATE.search(key):
                    collections.append({"pointer": "/" + pointer_token(key), "records": len(value)})
    else:
        fail("IMPORT_JSON", "$", "Inventory root must be an object or array.")
    return {
        "import_version": 2,
        "source": source.model_dump(),
        "collections": collections,
        "adapter": adapter,
        "diagnostics": [d.model_dump() for d in diagnostics],
        "supported_adapters": ["json", "netbox-offline-v1"],
        "limits": asdict(STRUCTURED_LIMITS),
        "warnings": ["Select collections explicitly by RFC 6901 pointer; unknown values excluded."],
    }
