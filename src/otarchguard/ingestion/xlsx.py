"""Restricted transitional OOXML inventory reader, bounded before tree allocation.

No extraction, Office automation, style interpretation, formula execution or fetching.
Unknown package parts fail closed; this is intentionally not a general Office parser.
"""

import hashlib
import io
import posixpath
import re
import stat
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree as ET
from xml.parsers import expat

from otarchguard.diagnostics import check_limit, fail
from otarchguard.ingestion.numbers import excel_magnitude_ambiguous, parse_number
from otarchguard.ingestion.records import (
    ImportDiagnostic,
    ImportDraft,
    SourceDocument,
    StructuredLocation,
    StructuredProfile,
)
from otarchguard.ingestion.records import InventoryValue as YamlValue
from otarchguard.ingestion.structured import ExtractedRow, Value, map_extracted, validate_profile
from otarchguard.ingestion.tabular import _safe_text, read_regular

_S = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_P = "http://schemas.openxmlformats.org/package/2006/relationships"
_C = "http://schemas.openxmlformats.org/package/2006/content-types"
_PART = re.compile(
    r"\[Content_Types\]\.xml|_rels/\.rels|docProps/(?:core|app)\.xml|"
    r"xl/(?:workbook\.xml|_rels/workbook\.xml\.rels|sharedStrings\.xml|styles\.xml|"
    r"theme/theme[0-9]+\.xml|worksheets/sheet[0-9]+\.xml|"
    r"worksheets/_rels/sheet[0-9]+\.xml\.rels)"
)


@dataclass(frozen=True, slots=True)
class WorkbookLimits:
    source_bytes: int = 1024 * 1024
    uncompressed_bytes: int = 8 * 1024 * 1024
    members: int = 128
    ratio: int = 100
    xml_depth: int = 24
    xml_elements: int = 150_000
    xml_text: int = 2 * 1024 * 1024
    shared_strings: int = 32_000
    sheets: int = 16
    rows: int = 1001  # Includes header; maximum data candidates remains 1,000.
    columns: int = 64
    cells: int = 32_000
    text: int = 4096
    diagnostics: int = 200


WORKBOOK_LIMITS = WorkbookLimits()


class _XmlBudget:
    def __init__(self, limits: WorkbookLimits) -> None:
        self.limits = limits
        self.elements = 0
        self.characters = 0

    def parse(self, data: bytes) -> ET.Element:
        # UTF-8 only prevents alternate-encoding bypasses of lexical security checks.
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            fail("IMPORT_XLSX_XML", "$", "OOXML parts must use UTF-8.")
        declaration = re.match(r"<\?xml\s+[^?]*encoding=['\"]([^'\"]+)", text)
        if declaration and declaration[1].lower() not in {"utf-8", "utf8"}:
            fail("IMPORT_XLSX_XML", "$", "Only UTF-8 XML is supported.")
        _safe_text(text)
        builder = ET.TreeBuilder()
        parser = expat.ParserCreate(namespace_separator="}")
        depth = 0

        def name(value: str) -> str:
            return "{" + value if "}" in value else value

        def start(tag: str, attributes: dict[str, str]) -> None:
            nonlocal depth
            depth += 1
            self.elements += 1
            check_limit("xlsx_xml_depth", depth, self.limits.xml_depth)
            check_limit("xlsx_xml_elements", self.elements, self.limits.xml_elements)
            check_limit("xlsx_xml_attributes", len(attributes), 64)
            check_limit("xlsx_xml_name", len(tag), self.limits.text)
            self.characters += len(tag)
            for key, value in attributes.items():
                _safe_text(value)
                check_limit("xlsx_xml_name", len(key), self.limits.text)
                check_limit("xlsx_text", len(value), self.limits.text)
                self.characters += len(key) + len(value)
            check_limit("xlsx_xml_text", self.characters, self.limits.xml_text)
            builder.start(name(tag), {name(k): v for k, v in attributes.items()})

        def namespace(prefix: str | None, uri: str | None) -> None:
            prefix, uri = prefix or "", uri or ""
            _safe_text(uri)
            check_limit("xlsx_xml_name", len(prefix), self.limits.text)
            check_limit("xlsx_xml_name", len(uri), self.limits.text)
            self.characters += len(prefix) + len(uri)
            check_limit("xlsx_xml_text", self.characters, self.limits.xml_text)

        def end(tag: str) -> None:
            nonlocal depth
            builder.end(name(tag))
            depth -= 1

        def characters(value: str) -> None:
            _safe_text(value)
            self.characters += len(value)
            check_limit("xlsx_xml_text", self.characters, self.limits.xml_text)
            builder.data(value)

        def forbidden(*args: object) -> None:
            fail("IMPORT_XLSX_XML", "$", "DTD, entities and processing instructions are forbidden.")

        parser.StartElementHandler = start
        parser.StartNamespaceDeclHandler = namespace
        parser.EndElementHandler = end
        parser.CharacterDataHandler = characters
        parser.StartDoctypeDeclHandler = forbidden
        parser.EntityDeclHandler = forbidden
        parser.ExternalEntityRefHandler = lambda *args: 0
        parser.ProcessingInstructionHandler = forbidden
        try:
            parser.Parse(text, True)
            return builder.close()
        except (expat.ExpatError, ValueError):
            fail("IMPORT_XLSX_XML", "$", "Malformed or unsupported OOXML XML part.")


def _coordinate(value: str, limits: WorkbookLimits) -> tuple[int, int]:
    match = re.fullmatch(r"([A-Z]{1,3})([1-9][0-9]{0,6})", value)
    if match is None:
        fail("IMPORT_XLSX_CELL", "$", "Explicit A1 cell coordinates required.")
    column = 0
    for letter in match[1]:
        column = column * 26 + ord(letter) - 64
    row = int(match[2])
    check_limit("xlsx_rows", row, limits.rows)
    check_limit("xlsx_columns", column, limits.columns)
    return row, column


@dataclass(frozen=True, slots=True)
class Sheet:
    name: str
    identity: str
    hidden: bool
    cells: dict[tuple[int, int], Value]


@dataclass(frozen=True, slots=True)
class Workbook:
    source: SourceDocument
    sheets: tuple[Sheet, ...]
    diagnostics: tuple[ImportDiagnostic, ...]


def read_workbook(path: Path, limits: WorkbookLimits = WORKBOOK_LIMITS) -> Workbook:
    if path.suffix.lower() != ".xlsx":
        fail("IMPORT_FORMAT", "$", "Restricted workbook adapter requires .xlsx.")
    data = read_regular(path, limits.source_bytes)
    budget = _XmlBudget(limits)
    diagnostics: list[ImportDiagnostic] = []

    def diagnostic(code: str, message: str, location: str | None = None) -> None:
        diagnostics.append(ImportDiagnostic(code=code, message=message, field=location))
        check_limit("import_diagnostics", len(diagnostics), limits.diagnostics)

    parts: dict[str, ET.Element] = {}
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            members = archive.infolist()
            check_limit("xlsx_members", len(members), limits.members)
            seen: set[str] = set()
            uncompressed = 0
            for member in members:
                member_path = PurePosixPath(member.filename)
                name = member.filename
                mode = member.external_attr >> 16
                if (
                    name.casefold() in seen
                    or member.orig_filename != name
                    or member_path.is_absolute()
                    or ".." in member_path.parts
                    or "\\" in name
                    or ":" in name
                    or (stat.S_IFMT(mode) not in {0, stat.S_IFREG, stat.S_IFDIR})
                    or member.flag_bits & 1
                    or member.compress_type not in {0, 8}
                ):
                    fail("IMPORT_XLSX_ARCHIVE", "$", "Unsafe, duplicate or special ZIP member.")
                seen.add(name.casefold())
                if member.is_dir():
                    if member.file_size != 0:
                        fail("IMPORT_XLSX_ARCHIVE", "$", "Directory entries must be empty.")
                    if name not in {
                        "_rels/",
                        "docProps/",
                        "xl/",
                        "xl/_rels/",
                        "xl/worksheets/",
                        "xl/worksheets/_rels/",
                        "xl/theme/",
                    }:
                        fail("IMPORT_XLSX_PART", "$", "Unsupported workbook package directory.")
                    continue
                if _PART.fullmatch(name) is None:
                    fail(
                        "IMPORT_XLSX_PART",
                        "$",
                        "Unsupported package part (macros/objects excluded).",
                    )
                uncompressed += member.file_size
                check_limit("xlsx_uncompressed_bytes", uncompressed, limits.uncompressed_bytes)
                check_limit(
                    "xlsx_compression_ratio",
                    member.file_size,
                    max(1, member.compress_size) * limits.ratio,
                )
            # Validate every member, including unselected sheets and unused XML.
            for member in members:
                if not member.is_dir():
                    with archive.open(member) as stream:
                        payload = stream.read(limits.uncompressed_bytes + 1)
                    if len(payload) != member.file_size:
                        fail("IMPORT_XLSX_ARCHIVE", "$", "Archive member size mismatch.")
                    parts[member.filename] = budget.parse(payload)
    except (zipfile.BadZipFile, OSError, RuntimeError, NotImplementedError):
        fail("IMPORT_XLSX_ARCHIVE", "$", "Corrupt or unsupported workbook container.")
    if (
        not {"[Content_Types].xml", "_rels/.rels", "xl/workbook.xml", "xl/_rels/workbook.xml.rels"}
        <= parts.keys()
    ):
        fail("IMPORT_XLSX_PART", "$", "Missing workbook package manifests.")
    types = parts["[Content_Types].xml"]
    if types.tag != f"{{{_C}}}Types":
        fail("IMPORT_XLSX_PART", "$", "Invalid content-types manifest.")
    content_type_names: set[str] = set()
    workbook_type = False
    for entry in types:
        if entry.tag not in {f"{{{_C}}}Default", f"{{{_C}}}Override"}:
            fail("IMPORT_XLSX_PART", "$", "Unsupported content-types entry.")
        content_type = entry.get("ContentType", "")
        if "macro" in content_type.casefold() or "vba" in content_type.casefold():
            fail("IMPORT_XLSX_PART", "$", "Macro-bearing containers are forbidden.")
        type_key = entry.get("PartName", entry.get("Extension", ""))
        if type_key in content_type_names:
            fail("IMPORT_XLSX_PART", "$", "Duplicate content-types entry.")
        content_type_names.add(type_key)
        if type_key == "/xl/workbook.xml":
            workbook_type = content_type == (
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"
            )
    if not workbook_type:
        fail(
            "IMPORT_XLSX_PART", "$", "Only transitional non-macro spreadsheet workbooks supported."
        )
    relationships: dict[str, dict[str, tuple[str, str]]] = {}
    for part_name, element in sorted(parts.items()):
        if not part_name.endswith(".rels"):
            continue
        if element.tag != f"{{{_P}}}Relationships":
            fail("IMPORT_XLSX_RELATIONSHIP", "$", "Invalid relationship manifest.")
        links: dict[str, tuple[str, str]] = {}
        for relation in element:
            identity, target, kind = (relation.get(k, "") for k in ("Id", "Target", "Type"))
            if relation.tag != f"{{{_P}}}Relationship" or not identity or identity in links:
                fail("IMPORT_XLSX_RELATIONSHIP", "$", "Conflicting relationship identities.")
            if relation.get("TargetMode") == "External":
                diagnostic(
                    "EXTERNAL_RELATIONSHIP",
                    "External relationship excluded; target not retained or fetched.",
                    part_name,
                )
                links[identity] = ("", kind)
                continue
            if relation.get("TargetMode") not in {None, "Internal"}:
                fail("IMPORT_XLSX_RELATIONSHIP", "$", "Unsupported relationship mode.")
            if (
                not target
                or "\\" in target
                or ":" in target
                or "%" in target
                or ".." in PurePosixPath(target).parts
            ):
                fail("IMPORT_XLSX_RELATIONSHIP", "$", "Unsafe internal relationship target.")
            base = "" if part_name == "_rels/.rels" else part_name.split("/_rels/")[0]
            resolved = (
                posixpath.normpath(posixpath.join(base, target))
                if not target.startswith("/")
                else target[1:]
            )
            if resolved not in parts:
                fail("IMPORT_XLSX_RELATIONSHIP", "$", "Internal relationship target is missing.")
            allowed_kinds = {
                _R + "/" + k
                for k in (
                    "officeDocument",
                    "worksheet",
                    "styles",
                    "sharedStrings",
                    "theme",
                    "extended-properties",
                    "hyperlink",
                )
            }
            allowed_kinds.add(
                "http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties"
            )
            if kind not in allowed_kinds:
                fail("IMPORT_XLSX_RELATIONSHIP", "$", "Unsupported internal relationship type.")
            fixed_targets = {
                _R + "/officeDocument": "xl/workbook.xml",
                _R + "/styles": "xl/styles.xml",
                _R + "/sharedStrings": "xl/sharedStrings.xml",
            }
            if kind in fixed_targets and resolved != fixed_targets[kind]:
                fail("IMPORT_XLSX_RELATIONSHIP", "$", "Relationship type and target disagree.")
            links[identity] = (resolved, kind)
        relationships[part_name] = links
    if (
        sum(
            v == ("xl/workbook.xml", _R + "/officeDocument")
            for v in relationships["_rels/.rels"].values()
        )
        != 1
    ):
        fail("IMPORT_XLSX_RELATIONSHIP", "$", "One internal workbook relationship required.")
    strings: list[str] = []
    if "xl/sharedStrings.xml" in parts:
        shared = parts["xl/sharedStrings.xml"]
        if shared.tag != f"{{{_S}}}sst":
            fail("IMPORT_XLSX_STRINGS", "$", "Invalid shared string table.")
        for item in shared:
            if item.tag != f"{{{_S}}}si":
                fail("IMPORT_XLSX_STRINGS", "$", "Unsupported shared string structure.")
            value = "".join(t.text or "" for t in item.iter(f"{{{_S}}}t"))
            check_limit("xlsx_text", len(value), limits.text)
            strings.append(value)
            check_limit("xlsx_shared_strings", len(strings), limits.shared_strings)
    workbook = parts["xl/workbook.xml"]
    if workbook.tag != f"{{{_S}}}workbook":
        fail("IMPORT_XLSX_PART", "$", "Unsupported workbook namespace.")
    if any(
        child.tag
        not in {
            f"{{{_S}}}{t}"
            for t in (
                "workbookPr",
                "bookViews",
                "sheets",
                "calcPr",
                "fileVersion",
                "externalReferences",
            )
        }
        for child in workbook
    ):
        fail(
            "IMPORT_XLSX_CONSTRUCT",
            "$",
            "Unsupported workbook construct (including defined names).",
        )
    sheets = workbook.find(f"{{{_S}}}sheets")
    if sheets is None or not len(sheets):
        fail("IMPORT_XLSX_SHEET", "$", "Workbook has no worksheets.")
    check_limit("xlsx_sheets", len(sheets), limits.sheets)
    names: set[str] = set()
    identities: set[int] = set()
    targets: set[str] = set()
    result: list[Sheet] = []
    count = 0
    for sheet in sheets:
        name, identity = sheet.get("name", ""), sheet.get("sheetId", "")
        identity_key = int(identity) if re.fullmatch(r"[0-9]{1,10}", identity) else -1
        target, kind = relationships["xl/_rels/workbook.xml.rels"].get(
            sheet.get(f"{{{_R}}}id", ""), ("", "")
        )
        if (
            sheet.tag != f"{{{_S}}}sheet"
            or not name
            or not 0 <= identity_key <= 0xFFFFFFFF
            or name.casefold() in names
            or identity_key in identities
            or target in targets
            or kind != _R + "/worksheet"
            or not target.startswith("xl/worksheets/sheet")
            or target not in parts
        ):
            fail(
                "IMPORT_XLSX_SHEET",
                "$",
                "Invalid, duplicate or unsupported sheet identity/relationship.",
            )
        names.add(name.casefold())
        identities.add(identity_key)
        targets.add(target)
        hidden = sheet.get("state", "visible") != "visible"
        if hidden:
            diagnostic(
                "HIDDEN_SHEET",
                "Hidden worksheet present; selection still requires an explicit profile.",
                name,
            )
        worksheet = parts[target]
        if worksheet.tag != f"{{{_S}}}worksheet":
            fail("IMPORT_XLSX_SHEET", "$", "Only worksheets are supported.")
        allowed_tags = {
            "worksheet",
            "dimension",
            "sheetData",
            "row",
            "c",
            "v",
            "f",
            "is",
            "t",
            "r",
            "rPr",
            "b",
            "i",
            "u",
            "sz",
            "color",
            "rFont",
            "family",
            "scheme",
            "charset",
            "vertAlign",
            "sheetViews",
            "sheetView",
            "selection",
            "pane",
            "sheetFormatPr",
            "cols",
            "col",
            "mergeCells",
            "mergeCell",
            "hyperlinks",
            "hyperlink",
            "pageMargins",
            "autoFilter",
            "sheetPr",
            "outlinePr",
            "pageSetUpPr",
            "tabColor",
        }
        if any(e.tag not in {f"{{{_S}}}{t}" for t in allowed_tags} for e in worksheet.iter()):
            fail("IMPORT_XLSX_CONSTRUCT", "$", "Unsupported worksheet construct.")
        dimension = worksheet.find(f"{{{_S}}}dimension")
        if dimension is not None:
            for coordinate in dimension.get("ref", "").split(":"):
                _coordinate(coordinate, limits)
        merges: list[tuple[int, int, int, int]] = []
        for merged in worksheet.iter(f"{{{_S}}}mergeCell"):
            coords = merged.get("ref", "").split(":")
            if len(coords) != 2:
                fail("IMPORT_XLSX_CELL", "$", "Invalid merged range.")
            first, last = (_coordinate(c, limits) for c in coords)
            if first[0] > last[0] or first[1] > last[1]:
                fail("IMPORT_XLSX_CELL", "$", "Invalid merged range ordering.")
            merges.append((*first, *last))
            diagnostic(
                "MERGED_CELLS",
                "Merged range present; mapped cells require literal correction.",
                f"{name}!{merged.get('ref', '')}",
            )
        cells: dict[tuple[int, int], Value] = {}
        sheet_data = worksheet.findall(f"{{{_S}}}sheetData")
        if len(sheet_data) != 1:
            fail("IMPORT_XLSX_SHEET", "$", "Exactly one sheetData element required.")
        row_numbers: set[int] = set()
        for row in sheet_data[0]:
            number = row.get("r", "")
            if re.fullmatch(r"[1-9][0-9]{0,3}", number) is None or int(number) in row_numbers:
                fail("IMPORT_XLSX_CELL", "$", "Explicit unique worksheet row numbers required.")
            row_number = int(number)
            row_numbers.add(row_number)
            check_limit("xlsx_rows", row_number, limits.rows)
            for cell in row:
                coordinate = cell.get("r", "")
                key = _coordinate(coordinate, limits)
                if cell.tag != f"{{{_S}}}c" or key in cells or key[0] != row_number:
                    fail("IMPORT_XLSX_CELL", "$", "Conflicting or misplaced cell coordinate.")
                count += 1
                check_limit("xlsx_cells", count, limits.cells)
                formula, cached = cell.findall(f"{{{_S}}}f"), cell.findall(f"{{{_S}}}v")
                inline = cell.findall(f"{{{_S}}}is")
                if len(formula) > 1 or len(cached) > 1 or len(inline) > 1 or (cached and inline):
                    fail("IMPORT_XLSX_CELL", "$", "Duplicate or conflicting cell value elements.")
                if any(
                    child.tag not in {f"{{{_S}}}f", f"{{{_S}}}v", f"{{{_S}}}is"} for child in cell
                ):
                    fail("IMPORT_XLSX_CELL", "$", "Unsupported direct cell content.")
                raw: YamlValue = None
                issue: str | None = None
                text_value = cached[0].text or "" if cached else ""
                kind = cell.get("t", "n")
                if not formula and (
                    (inline and kind != "inlineStr") or (cached and kind == "inlineStr")
                ):
                    fail("IMPORT_XLSX_CELL", "$", "Cell type and value representation disagree.")
                if formula:
                    issue = "Formula cell; literal correction required (cached value excluded)."
                    diagnostic(
                        "FORMULA_CELL",
                        "Formula detected; cache "
                        + ("present" if cached else "absent")
                        + "; no evaluation or automatic acceptance.",
                        f"{name}!{coordinate}",
                    )
                elif kind == "inlineStr":
                    raw = (
                        "".join(t.text or "" for t in inline[0].iter(f"{{{_S}}}t"))
                        if inline
                        else ""
                    )
                elif kind == "s":
                    if (
                        not text_value.isdigit()
                        or len(text_value) > 8
                        or int(text_value) >= len(strings)
                    ):
                        fail("IMPORT_XLSX_STRINGS", "$", "Invalid shared string reference.")
                    raw = strings[int(text_value)]
                elif kind == "b":
                    if text_value not in {"0", "1"}:
                        fail("IMPORT_XLSX_CELL", "$", "Boolean cells require 0 or 1.")
                    raw = text_value == "1"
                elif kind == "n" and text_value:
                    if (
                        len(text_value) > 64
                        or re.fullmatch(
                            r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?", text_value
                        )
                        is None
                    ):
                        fail("IMPORT_XLSX_NUMBER", "$", "Finite bounded numeric cell required.")
                    raw = parse_number(text_value)
                    if excel_magnitude_ambiguous(raw):
                        issue = (
                            "Numeric magnitude outside Excel range; literal correction required."
                        )
                    if "s" in cell.attrib or sum(c.isdigit() for c in text_value) > 15:
                        issue = "Styled/precision-sensitive number; literal correction required."
                elif kind == "n" and not text_value:
                    raw = None
                else:
                    issue = "Unsupported date/error/string-cache cell type; correction required."
                if any(a <= key[0] <= c and b <= key[1] <= d for a, b, c, d in merges):
                    issue = "Merged cell; literal correction required."
                if isinstance(raw, str):
                    check_limit("xlsx_text", len(raw), limits.text)
                location = StructuredLocation(
                    collection=name,
                    record=str(key[0]),
                    sheet=name,
                    sheet_id=identity,
                    cell=coordinate,
                )
                cells[key] = Value(raw, location, issue=issue)
        result.append(Sheet(name, identity, hidden, cells))
    if {p for p in parts if re.fullmatch(r"xl/worksheets/sheet[0-9]+\.xml", p)} != targets:
        fail("IMPORT_XLSX_SHEET", "$", "Orphan worksheet parts are unsupported.")
    sha = hashlib.sha256(data).hexdigest()
    return Workbook(
        SourceDocument(
            source_id=f"src_{sha}",
            sha256=sha,
            name=path.name,
            format="xlsx",
            byte_count=len(data),
            encoding="utf-8",
            delimiter="",
        ),
        tuple(result),
        tuple(diagnostics),
    )


def create_xlsx_draft(path: Path, profile: StructuredProfile) -> ImportDraft:
    validate_profile(profile)
    workbook = read_workbook(path)
    sheets = {s.name: s for s in workbook.sheets}
    tables: dict[str, tuple[ExtractedRow, ...]] = {}
    for table in profile.tables:
        if table.collection not in sheets:
            fail("IMPORT_XLSX_SELECTION", table.name, "Select an exact existing worksheet name.")
        sheet = sheets[table.collection]
        headers: dict[str, int] = {}
        for (row, column), value in sorted(sheet.cells.items()):
            if row != table.header_row:
                continue
            if not isinstance(value.raw, str) or not value.raw.strip() or value.issue:
                fail("IMPORT_XLSX_HEADER", table.name, "Headers must be nonempty literal text.")
            if (
                value.raw.strip().casefold() in {h.strip().casefold() for h in headers}
                or value.raw == "<<"
            ):
                fail("IMPORT_XLSX_HEADER", table.name, "Duplicate/equivalent/reserved header.")
            headers[value.raw] = column
        if not headers or not {f.path for f in table.fields.values()} <= headers.keys():
            fail(
                "IMPORT_XLSX_HEADER", table.name, "Mapped header missing; exact matching required."
            )
        if any(r > table.header_row and c not in headers.values() for r, c in sheet.cells):
            fail("IMPORT_XLSX_HEADER", table.name, "Data cells require a literal column header.")
        rows: list[ExtractedRow] = []
        for number in sorted({r for r, _ in sheet.cells if r > table.header_row}):
            values: dict[str, Value] = {}
            for field, mapping in table.fields.items():
                column = headers[mapping.path]
                fallback = StructuredLocation(
                    collection=sheet.name,
                    record=str(number),
                    sheet=sheet.name,
                    sheet_id=sheet.identity,
                    cell=_column_name(column) + str(number),
                )
                values[field] = sheet.cells.get(
                    (number, column), Value(None, fallback, missing=True)
                )
            location = StructuredLocation(
                collection=sheet.name, record=str(number), sheet=sheet.name, sheet_id=sheet.identity
            )
            rows.append(ExtractedRow(location, values, len(headers) - len(table.fields)))
        tables[table.name] = tuple(rows)
    if not any(tables.values()):
        fail("IMPORT_EMPTY", "$", "Selected worksheets contain no records.")
    return map_extracted(workbook.source, profile, tables, list(workbook.diagnostics))


def _column_name(column: int) -> str:
    result = ""
    while column:
        column, remainder = divmod(column - 1, 26)
        result = chr(65 + remainder) + result
    return result


def inspect_xlsx(path: Path) -> dict[str, object]:
    workbook = read_workbook(path)
    return {
        "import_version": 2,
        "source": workbook.source.model_dump(),
        "adapter": "xlsx",
        "subset": "restricted-transitional-inventory-v1",
        "collections": [
            {"name": s.name, "sheet_id": s.identity, "hidden": s.hidden, "cells": len(s.cells)}
            for s in workbook.sheets
        ],
        "diagnostics": [d.model_dump() for d in workbook.diagnostics],
        "limits": asdict(WORKBOOK_LIMITS),
    }
