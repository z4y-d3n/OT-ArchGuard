"""Bounded CSV/TSV adapter. No sniffing, formula evaluation or implicit typing."""

import csv
import hashlib
import io
import json
import os
import stat
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal, Protocol

from otarchguard.diagnostics import check_limit, fail
from otarchguard.ingestion.records import SourceDocument


@dataclass(frozen=True, slots=True)
class ImportLimits:
    source_bytes: int = 1024 * 1024
    rows: int = 1000
    columns: int = 64
    cells: int = 32_000
    field_characters: int = 4096
    diagnostics: int = 200


IMPORT_LIMITS = ImportLimits()


@dataclass(frozen=True, slots=True)
class AdapterCapabilities:
    format: str
    extensions: tuple[str, ...]
    subset_version: int
    evidence_only: bool
    constraints: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TableRow:
    row_id: str
    row: int
    line_start: int
    line_end: int
    values: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SourceTable:
    source: SourceDocument
    headers: tuple[str, ...]
    rows: tuple[TableRow, ...]


class FormatAdapter(Protocol):
    capabilities: AdapterCapabilities

    def read(
        self, path: Path, *, delimiter: str | None = None, encoding: str = "utf-8-sig"
    ) -> SourceTable: ...


def digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode()
    ).hexdigest()


def read_regular(path: Path, maximum: int) -> bytes:
    """Reject special files before opening; bound reads even if a regular file grows."""
    try:
        if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode):
            fail("IMPORT_FILE", "$", "Import input must be a local regular, non-symlink file.")
        with path.open("rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                fail("IMPORT_FILE", "$", "Import input must be a regular file.")
            data = stream.read(maximum + 1)
    except OSError:
        fail("IMPORT_READ", "$", "Cannot read the local import input.")
    check_limit("import_bytes", len(data), maximum)
    return data


def _safe_text(value: str) -> None:
    if any(
        (ord(c) < 32 and c not in "\t\r\n") or 127 <= ord(c) <= 159 or 0xD800 <= ord(c) <= 0xDFFF
        for c in value
    ):
        fail("IMPORT_TEXT", "$", "Binary, control and surrogate characters are forbidden.")


def _quoted_syntax(source: str, delimiter: str) -> None:
    """csv strict mode still allows quotes inside bare fields; reject that ambiguity."""
    state = "start"
    for character in source:
        if state == "quoted":
            if character == '"':
                state = "closed"
        elif state == "closed":
            if character == '"':
                state = "quoted"
            elif character == delimiter or character in "\r\n":
                state = "start"
            else:
                fail("IMPORT_CSV", "$", "Unexpected text after a closing quote.")
        elif character == '"':
            if state != "start":
                fail("IMPORT_CSV", "$", "Quotes inside bare fields must be escaped and quoted.")
            state = "quoted"
        elif character == delimiter or character in "\r\n":
            state = "start"
        else:
            state = "bare"
    if state == "quoted":
        fail("IMPORT_CSV", "$", "Unterminated quoted field.")


class DelimitedAdapter:
    capabilities = AdapterCapabilities(
        "delimited",
        (".csv", ".tsv"),
        1,
        True,
        ("one explicit header", "no formula evaluation", "no type coercion", "bounded text"),
    )

    def __init__(self, limits: ImportLimits = IMPORT_LIMITS) -> None:
        self.limits = limits

    def read(
        self, path: Path, *, delimiter: str | None = None, encoding: str = "utf-8-sig"
    ) -> SourceTable:
        extension = path.suffix.lower()
        if extension not in self.capabilities.extensions:
            fail("IMPORT_FORMAT", "$", "Gate V12-01 accepts only CSV and TSV source files.")
        if encoding not in {"utf-8-sig", "cp1252"}:
            fail("IMPORT_ENCODING", "$", "Select utf-8-sig or cp1252 explicitly.")
        delimiter = delimiter if delimiter is not None else ("\t" if extension == ".tsv" else ",")
        if (
            len(delimiter) != 1
            or delimiter in '"\r\n'
            or (ord(delimiter) < 32 and delimiter != "\t")
            or not delimiter.isprintable()
            and delimiter != "\t"
        ):
            fail("IMPORT_DELIMITER", "$", "Delimiter must be one printable character or tab.")
        data = read_regular(path, self.limits.source_bytes)
        try:
            source = data.decode(encoding)
        except UnicodeDecodeError:
            fail("IMPORT_ENCODING", "$", "Input cannot be decoded with the selected encoding.")
        _safe_text(source)
        _quoted_syntax(source, delimiter)
        rows: list[TableRow] = []
        occurrences: Counter[str] = Counter()
        reader = csv.reader(io.StringIO(source, newline=""), delimiter=delimiter, strict=True)
        try:
            header = next(reader, None)
            if not header or any(not h.strip() for h in header):
                fail("IMPORT_HEADER", "$", "Exactly one nonempty header row is required.")
            if "<<" in header:
                fail(
                    "IMPORT_HEADER", "$", "The reserved control-document header << is unsupported."
                )
            check_limit("import_columns", len(header), self.limits.columns)
            if len({h.strip().casefold() for h in header}) != len(header):
                fail("IMPORT_HEADER", "$", "Duplicate or equivalent column names are forbidden.")
            for h in header:
                check_limit("import_field_characters", len(h), self.limits.field_characters)
            previous_line = reader.line_num
            for number, values in enumerate(reader, 1):
                check_limit("import_rows", number, self.limits.rows)
                check_limit("import_cells", number * len(header), self.limits.cells)
                if len(values) != len(header):
                    fail("IMPORT_ROW", f"$.rows[{number}]", "Row width must match the header.")
                if all(not value.strip() for value in values):
                    fail("IMPORT_ROW", f"$.rows[{number}]", "Empty data rows are forbidden.")
                for value in values:
                    check_limit("import_field_characters", len(value), self.limits.field_characters)
                # Header order and physical row order do not determine logical identity.
                row_digest = digest(dict(zip(header, values, strict=True)))
                occurrences[row_digest] += 1
                rows.append(
                    TableRow(
                        f"row_{row_digest}_{occurrences[row_digest]}",
                        number,
                        previous_line + 1,
                        reader.line_num,
                        tuple(values),
                    )
                )
                previous_line = reader.line_num
        except csv.Error:
            fail("IMPORT_CSV", "$", "Malformed CSV or parser field ceiling exceeded.")
        if not rows:
            fail("IMPORT_EMPTY", "$", "The inventory has no data rows.")
        sha = hashlib.sha256(data).hexdigest()
        format_name: Literal["csv", "tsv"] = "tsv" if extension == ".tsv" else "csv"
        return SourceTable(
            SourceDocument(
                source_id=f"src_{sha}",
                sha256=sha,
                name=path.name,
                format=format_name,
                byte_count=len(data),
                encoding=encoding,
                delimiter=delimiter,
            ),
            tuple(header),
            tuple(rows),
        )

    def inspect(self, table: SourceTable) -> dict[str, object]:
        return {
            "import_version": 1,
            "source": table.source.model_dump(),
            "capabilities": asdict(self.capabilities),
            "limits": asdict(self.limits),
            "collections": [{"name": "table", "headers": table.headers, "rows": len(table.rows)}],
            "warnings": ["Table structure only; no model or permission has been confirmed."],
        }
