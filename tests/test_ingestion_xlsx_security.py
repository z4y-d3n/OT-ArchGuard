"""Hostile OOXML fixtures exercise archive, XML, value and review boundaries."""

import io
import zipfile
from contextlib import nullcontext
from dataclasses import replace
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from otarchguard.diagnostics import ModelError
from otarchguard.ingestion.records import StructuredCandidate, StructuredProfile
from otarchguard.ingestion.workflow import create_draft
from otarchguard.ingestion.xlsx import WORKBOOK_LIMITS, read_workbook
from tools.synthetic_inventories import P, R, S, workbook_parts, zip_parts


def parts() -> dict[str, bytes]:
    return workbook_parts({"Inventory": [["id", "name"], ["a", "Controller"]]})


def source(tmp_path: Path, value: dict[str, bytes]) -> Path:
    path = tmp_path / "inventory.xlsx"
    path.write_bytes(zip_parts(value))
    return path


def profile() -> StructuredProfile:
    return StructuredProfile.model_validate(
        {
            "profile_version": 2,
            "adapter": "xlsx",
            "tables": [
                {
                    "name": "assets",
                    "collection": "Inventory",
                    "entity": "asset",
                    "fields": {"id": {"path": "id"}, "name": {"path": "name"}},
                }
            ],
        }
    )


@pytest.mark.parametrize(
    "name",
    [
        "../secret.xml",
        "/xl/workbook.xml",
        "xl/../workbook.xml",
        "xl\\unsafe.xml",
        "C:/secret.xml",
        "xl/vbaProject.bin",
        "xl/embeddings/object.bin",
        "xl/externalLinks/externalLink1.xml",
        "xl/comments/comment1.xml",
        "./xl/workbook.xml",
    ],
)
def test_forbidden_parts(tmp_path: Path, name: str) -> None:
    value = parts()
    value[name] = b"<x/>"
    with pytest.raises(ModelError):
        read_workbook(source(tmp_path, value))


@pytest.mark.parametrize("duplicate", ["exact", "case", "symlink"])
def test_duplicate_or_special_archive_members(tmp_path: Path, duplicate: str) -> None:
    value = parts()
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        for name, data in value.items():
            archive.writestr(name, data)
        name = "xl/workbook.xml" if duplicate == "exact" else "XL/WORKBOOK.XML"
        info = zipfile.ZipInfo(name)
        if duplicate == "symlink":
            info.external_attr = 0o120777 << 16
        with pytest.warns(UserWarning) if duplicate == "exact" else nullcontext():
            archive.writestr(info, b"<x/>")
    path = tmp_path / "bad.xlsx"
    path.write_bytes(stream.getvalue())
    with pytest.raises(ModelError):
        read_workbook(path)


@pytest.mark.parametrize(
    "xml",
    [
        b'<!DOCTYPE x [<!ENTITY a "expanded">]><x>&a;</x>',
        b'<!DOCTYPE x SYSTEM "file:///private"><x/>',
        b"<?unsafe execute?><x/>",
        b"<x>" * 25 + b"</x>" * 25,
        b"<x>\xff</x>",
        b"<x>&#x85;</x>",
        b"<x>",
        b'<?xml version="1.0" encoding="UTF-16"?><x/>',
    ],
)
def test_hostile_xml_in_even_unused_parts(tmp_path: Path, xml: bytes) -> None:
    value = parts()
    value["docProps/core.xml"] = xml
    with pytest.raises(ModelError):
        read_workbook(source(tmp_path, value))


@pytest.mark.parametrize(
    "limit",
    [
        "source_bytes",
        "uncompressed_bytes",
        "members",
        "ratio",
        "xml_depth",
        "xml_elements",
        "xml_text",
        "sheets",
        "rows",
        "columns",
        "cells",
        "text",
    ],
)
def test_workbook_resource_ceilings(tmp_path: Path, limit: str) -> None:
    with pytest.raises(ModelError):
        read_workbook(source(tmp_path, parts()), replace(WORKBOOK_LIMITS, **{limit: 0}))


def test_zip_bomb_before_xml(tmp_path: Path) -> None:
    value = parts()
    value["docProps/core.xml"] = b"<x>" + b"a" * 100_000 + b"</x>"
    path = tmp_path / "compressed.xlsx"
    path.write_bytes(zip_parts(value, compression=zipfile.ZIP_DEFLATED))
    with pytest.raises(ModelError) as error:
        read_workbook(path)
    assert "compression_ratio" in error.value.diagnostics[0].message


@pytest.mark.parametrize(
    "change",
    [
        "missing_target",
        "traversal",
        "duplicate_id",
        "wrong_kind",
        "duplicate_sheet_id",
        "duplicate_sheet_name",
        "sheet_external",
        "macro_content",
        "dimension",
        "cell_count",
        "cell_duplicate",
        "row_mismatch",
        "unknown_construct",
        "bad_shared_index",
    ],
)
def test_workbook_structure_rejection(tmp_path: Path, change: str) -> None:
    value = parts()
    links = ET.fromstring(value["xl/_rels/workbook.xml.rels"])
    workbook = ET.fromstring(value["xl/workbook.xml"])
    sheet = ET.fromstring(value["xl/worksheets/sheet1.xml"])
    if change == "missing_target":
        links[0].set("Target", "worksheets/sheet99.xml")
    if change == "traversal":
        links[0].set("Target", "../private.xml")
    if change == "duplicate_id":
        links.append(ET.fromstring(ET.tostring(links[0])))
    if change == "wrong_kind":
        links[0].set("Type", R + "/oleObject")
    if change.startswith("duplicate_sheet"):
        copy = ET.fromstring(ET.tostring(workbook[0][0]))
        if change == "duplicate_sheet_id":
            copy.set("name", "Other")
        else:
            copy.set("sheetId", "2")
        workbook[0].append(copy)
    if change == "sheet_external":
        links[0].set("TargetMode", "External")
    if change == "macro_content":
        value["[Content_Types].xml"] = value["[Content_Types].xml"].replace(
            b"spreadsheetml.sheet.main", b"macroEnabled.main"
        )
    if change == "dimension":
        ET.SubElement(sheet, f"{{{S}}}dimension", ref="A1:XFD1048576")
    if change == "cell_count":
        for number in range(3, 1002):
            row = ET.SubElement(sheet[0], f"{{{S}}}row", r=str(number))
            for column in range(1, 34):
                # A-AZ coordinates within column ceiling.
                name = chr(64 + column) if column <= 26 else "A" + chr(64 + column - 26)
                ET.SubElement(row, f"{{{S}}}c", r=f"{name}{number}")
    if change == "cell_duplicate":
        sheet[0][0].append(ET.fromstring(ET.tostring(sheet[0][0][0])))
    if change == "row_mismatch":
        sheet[0][0][0].set("r", "A2")
    if change == "unknown_construct":
        ET.SubElement(sheet, f"{{{S}}}oleObjects")
    if change == "bad_shared_index":
        cell = sheet[0][1][1]
        cell.clear()
        cell.set("r", "B2")
        cell.set("t", "s")
        ET.SubElement(cell, f"{{{S}}}v").text = "1"
    value["xl/_rels/workbook.xml.rels"] = ET.tostring(links)
    value["xl/workbook.xml"] = ET.tostring(workbook)
    value["xl/worksheets/sheet1.xml"] = ET.tostring(sheet)
    with pytest.raises(ModelError):
        read_workbook(source(tmp_path, value))


@pytest.mark.parametrize("cached", [False, True])
def test_formulas_never_use_cache(tmp_path: Path, cached: bool) -> None:
    value = parts()
    sheet = ET.fromstring(value["xl/worksheets/sheet1.xml"])
    cell = sheet[0][1][1]
    cell.clear()
    cell.set("r", "B2")
    cell.set("t", "str")
    ET.SubElement(cell, f"{{{S}}}f").text = 'WEBSERVICE("https://invalid.example")'
    if cached:
        ET.SubElement(cell, f"{{{S}}}v").text = "STALE_CACHE"
    value["xl/worksheets/sheet1.xml"] = ET.tostring(sheet)
    draft = create_draft(source(tmp_path, value), profile())
    candidate = draft.candidates[0]
    assert isinstance(candidate, StructuredCandidate) and "name" in candidate.required_corrections
    field = next(f for f in candidate.fields if f.field == "name")
    assert field.raw_value is None and field.normalized_value == ""
    assert any(
        d.code == "FORMULA_CELL" and ("present" if cached else "absent") in d.message
        for d in draft.diagnostics
    )


def test_hidden_merged_and_external_relationship_diagnostics(tmp_path: Path) -> None:
    value = parts()
    workbook = ET.fromstring(value["xl/workbook.xml"])
    workbook[0][0].set("state", "hidden")
    value["xl/workbook.xml"] = ET.tostring(workbook)
    sheet = ET.fromstring(value["xl/worksheets/sheet1.xml"])
    ET.SubElement(ET.SubElement(sheet, f"{{{S}}}mergeCells"), f"{{{S}}}mergeCell", ref="B2:C2")
    value["xl/worksheets/sheet1.xml"] = ET.tostring(sheet)
    links = ET.Element(f"{{{P}}}Relationships")
    ET.SubElement(
        links,
        f"{{{P}}}Relationship",
        Id="external",
        TargetMode="External",
        Type=R + "/hyperlink",
        Target="https://user:SECRET@invalid.example",
    )
    value["xl/worksheets/_rels/sheet1.xml.rels"] = ET.tostring(links)
    draft = create_draft(source(tmp_path, value), profile())
    assert {"HIDDEN_SHEET", "MERGED_CELLS", "EXTERNAL_RELATIONSHIP"} <= {
        d.code for d in draft.diagnostics
    }
    assert "SECRET" not in str(draft.model_dump())
    candidate = draft.candidates[0]
    assert isinstance(candidate, StructuredCandidate) and "name" in candidate.required_corrections


@pytest.mark.parametrize("raw", [1, 1.25, True, None])
def test_no_implicit_identifier_coercion(tmp_path: Path, raw: object) -> None:
    value = workbook_parts({"Inventory": [["id", "name"], [raw, "Controller"]]})
    candidate = create_draft(source(tmp_path, value), profile()).candidates[0]
    assert isinstance(candidate, StructuredCandidate) and "id" in candidate.required_corrections


def test_shared_strings_and_limits(tmp_path: Path) -> None:
    value = parts()
    sheet = ET.fromstring(value["xl/worksheets/sheet1.xml"])
    cell = sheet[0][1][1]
    cell.clear()
    cell.set("r", "B2")
    cell.set("t", "s")
    ET.SubElement(cell, f"{{{S}}}v").text = "0"
    value["xl/worksheets/sheet1.xml"] = ET.tostring(sheet)
    value["xl/sharedStrings.xml"] = f'<sst xmlns="{S}"><si><t>001</t></si></sst>'.encode()
    path = source(tmp_path, value)
    assert read_workbook(path).sheets[0].cells[2, 2].raw == "001"
    with pytest.raises(ModelError):
        read_workbook(path, replace(WORKBOOK_LIMITS, shared_strings=0))
    value["xl/sharedStrings.xml"] = f'<sst xmlns="{S}"><si><t>{"x" * 4097}</t></si></sst>'.encode()
    with pytest.raises(ModelError):
        read_workbook(source(tmp_path, value))


@pytest.mark.parametrize("payload", [b"not a zip", b"PK\x03\x04bad"])
def test_corrupt_containers(tmp_path: Path, payload: bytes) -> None:
    path = tmp_path / "bad.xlsx"
    path.write_bytes(payload)
    with pytest.raises(ModelError):
        read_workbook(path)


@pytest.mark.parametrize("change", ["styled", "precision", "date", "error"])
def test_ambiguous_cell_values_require_correction(tmp_path: Path, change: str) -> None:
    value = parts()
    sheet = ET.fromstring(value["xl/worksheets/sheet1.xml"])
    cell = sheet[0][1][1]
    cell.clear()
    cell.set("r", "B2")
    ET.SubElement(cell, f"{{{S}}}v").text = "1234567890123456" if change == "precision" else "45000"
    if change == "styled":
        cell.set("s", "1")
    if change == "date":
        cell.set("t", "d")
    if change == "error":
        cell.set("t", "e")
    value["xl/worksheets/sheet1.xml"] = ET.tostring(sheet)
    configured = profile().model_dump(mode="json")
    configured["tables"][0]["fields"]["name"]["value_type"] = "number"
    candidate = create_draft(
        source(tmp_path, value), StructuredProfile.model_validate(configured)
    ).candidates[0]
    assert isinstance(candidate, StructuredCandidate) and "name" in candidate.required_corrections


def test_explicit_second_header_row(tmp_path: Path) -> None:
    value = workbook_parts({"Inventory": [["Title"], ["id", "name"], ["a", "Controller"]]})
    configured = profile().model_dump(mode="json")
    configured["tables"][0]["header_row"] = 2
    draft = create_draft(source(tmp_path, value), StructuredProfile.model_validate(configured))
    assert len(draft.candidates) == 1


def test_actual_backslash_member_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "backslash.xlsx"
    path.write_bytes(zip_parts(parts()).replace(b"xl/workbook.xml", b"xl\\workbook.xml"))
    with pytest.raises(ModelError):
        read_workbook(path)


def test_unmapped_formula_diagnostic_retains_exact_location(tmp_path: Path) -> None:
    value = parts()
    sheet = ET.fromstring(value["xl/worksheets/sheet1.xml"])
    cell = sheet[0][1][1]
    cell.clear()
    cell.set("r", "B2")
    ET.SubElement(cell, f"{{{S}}}f").text = "1+1"
    value["xl/worksheets/sheet1.xml"] = ET.tostring(sheet)
    configured = profile().model_dump(mode="json")
    configured["tables"][0]["fields"].pop("name")
    draft = create_draft(source(tmp_path, value), StructuredProfile.model_validate(configured))
    diagnostic = next(d for d in draft.diagnostics if d.code == "FORMULA_CELL")
    assert diagnostic.field == "Inventory!B2" and "absent" in diagnostic.message
