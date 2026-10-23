"""Small deterministic synthetic OOXML writer for tests/examples, never an importer."""

import io
import zipfile
from collections.abc import Mapping, Sequence
from xml.etree import ElementTree as ET

S = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
P = "http://schemas.openxmlformats.org/package/2006/relationships"
C = "http://schemas.openxmlformats.org/package/2006/content-types"


def workbook_parts(tables: Mapping[str, Sequence[Sequence[object]]]) -> dict[str, bytes]:
    workbook = ET.Element(f"{{{S}}}workbook")
    sheets = ET.SubElement(workbook, f"{{{S}}}sheets")
    relationships = ET.Element(f"{{{P}}}Relationships")
    root_links = ET.Element(f"{{{P}}}Relationships")
    ET.SubElement(
        root_links,
        f"{{{P}}}Relationship",
        Id="root",
        Type=R + "/officeDocument",
        Target="xl/workbook.xml",
    )
    types = ET.Element(f"{{{C}}}Types")
    ET.SubElement(
        types,
        f"{{{C}}}Default",
        Extension="rels",
        ContentType="application/vnd.openxmlformats-package.relationships+xml",
    )
    ET.SubElement(types, f"{{{C}}}Default", Extension="xml", ContentType="application/xml")
    ET.SubElement(
        types,
        f"{{{C}}}Override",
        PartName="/xl/workbook.xml",
        ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml",
    )
    parts: dict[str, bytes] = {}
    # Stable names/ids across sheet presentation-order changes.
    ids = {name: number for number, name in enumerate(sorted(tables), 1)}
    for name, rows in tables.items():
        number = ids[name]
        ET.SubElement(
            sheets,
            f"{{{S}}}sheet",
            name=name,
            sheetId=str(number),
            attrib={f"{{{R}}}id": f"r{number}"},
        )
        ET.SubElement(
            relationships,
            f"{{{P}}}Relationship",
            Id=f"r{number}",
            Type=R + "/worksheet",
            Target=f"worksheets/sheet{number}.xml",
        )
        ET.SubElement(
            types,
            f"{{{C}}}Override",
            PartName=f"/xl/worksheets/sheet{number}.xml",
            ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml",
        )
        sheet = ET.Element(f"{{{S}}}worksheet")
        sheet_data = ET.SubElement(sheet, f"{{{S}}}sheetData")
        for row_number, values in enumerate(rows, 1):
            row = ET.SubElement(sheet_data, f"{{{S}}}row", r=str(row_number))
            for column, value in enumerate(values, 1):
                letter = ""
                while column:
                    column, remainder = divmod(column - 1, 26)
                    letter = chr(65 + remainder) + letter
                cell = ET.SubElement(row, f"{{{S}}}c", r=letter + str(row_number))
                if isinstance(value, str):
                    cell.set("t", "inlineStr")
                    ET.SubElement(ET.SubElement(cell, f"{{{S}}}is"), f"{{{S}}}t").text = value
                elif type(value) is bool:
                    cell.set("t", "b")
                    ET.SubElement(cell, f"{{{S}}}v").text = "1" if value else "0"
                elif type(value) in {float, int}:
                    ET.SubElement(cell, f"{{{S}}}v").text = str(value)
        parts[f"xl/worksheets/sheet{number}.xml"] = ET.tostring(sheet)
    parts.update(
        {
            "[Content_Types].xml": ET.tostring(types),
            "_rels/.rels": ET.tostring(root_links),
            "xl/workbook.xml": ET.tostring(workbook),
            "xl/_rels/workbook.xml.rels": ET.tostring(relationships),
        }
    )
    return parts


def zip_parts(parts: Mapping[str, bytes], *, compression: int = zipfile.ZIP_STORED) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=compression) as archive:
        for name, data in sorted(parts.items()):
            info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = compression
            archive.writestr(info, data)
    return stream.getvalue()
