"""Fictional transitional OPC fixtures, using explicit ECMA-376 part structures.

These are structural parser fixtures, not evidence of Office rendering fidelity.
No external converter, runtime dependency, macro or production data is used.
"""

import io
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
P = "http://schemas.openxmlformats.org/presentationml/2006/main"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
REL = "http://schemas.openxmlformats.org/package/2006/relationships"
CT = "http://schemas.openxmlformats.org/package/2006/content-types"
MAIN = "application/vnd.openxmlformats-officedocument."


def package(parts: dict[str, str]) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        for name, text in sorted(parts.items()):
            info = zipfile.ZipInfo(name, (2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, text.encode("utf-8"))
    return stream.getvalue()


def base(main: str, kind: str, extra: str = "") -> dict[str, str]:
    return {
        "[Content_Types].xml": f'<Types xmlns="{CT}">'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Default Extension="rels" '
        'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        f'<Override PartName="/{main}" ContentType="{MAIN}{kind}"/>{extra}</Types>',
        "_rels/.rels": f'<Relationships xmlns="{REL}">'
        f'<Relationship Id="office" Type="{R}/officeDocument" Target="{main}"/>'
        "</Relationships>",
    }


def docx_parts(label: str = "TCP 502 allowed") -> dict[str, str]:
    parts = base("word/document.xml", "wordprocessingml.document.main+xml")

    def paragraph(value: str) -> str:
        return '<w:p><w:r><w:t xml:space="preserve">' + escape(value) + "</w:t></w:r></w:p>"

    rows = [["id", "name", "zone"], ["eng", "Engineering Station", "alternate"]]
    table = (
        "<w:tbl><w:tblPr/><w:tblGrid/>"
        + "".join(
            "<w:tr>" + "".join("<w:tc>" + paragraph(cell) + "</w:tc>" for cell in row) + "</w:tr>"
            for row in rows
        )
        + "</w:tbl>"
    )
    parts["word/document.xml"] = (
        f'<w:document xmlns:w="{W}"><w:body>'
        '<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Inventory</w:t></w:r></w:p>'
        '<w:p><w:r><w:t xml:space="preserve"> A </w:t></w:r><w:r><w:t>B</w:t></w:r>'
        "<w:r><w:tab/><w:t>C</w:t><w:br/><w:t>D</w:t></w:r></w:p>"
        + paragraph(label)
        + table
        + "<w:sectPr/></w:body></w:document>"
    )
    return parts


def pptx_parts(label: str = "Firewall → PLC; TCP 502 allowed") -> dict[str, str]:
    overrides = "".join(
        f'<Override PartName="/ppt/slides/slide{i}.xml" '
        f'ContentType="{MAIN}presentationml.slide+xml"/>'
        for i in (1, 2)
    )
    parts = base("ppt/presentation.xml", "presentationml.presentation.main+xml", overrides)
    parts["ppt/presentation.xml"] = (
        f'<p:presentation xmlns:p="{P}" xmlns:r="{R}"><p:sldIdLst>'
        '<p:sldId id="257" r:id="second"/><p:sldId id="256" r:id="first"/>'
        "</p:sldIdLst></p:presentation>"
    )
    parts["ppt/_rels/presentation.xml.rels"] = (
        f'<Relationships xmlns="{REL}">'
        f'<Relationship Id="first" Type="{R}/slide" Target="slides/slide1.xml"/>'
        f'<Relationship Id="second" Type="{R}/slide" Target="slides/slide2.xml"/>'
        "</Relationships>"
    )

    def paragraph(value: str) -> str:
        return "<a:p><a:r><a:t>" + escape(value) + "</a:t></a:r></a:p>"

    for i in (1, 2):
        text = "Second slide in document order" if i == 1 else label
        table = (
            '<p:graphicFrame><p:nvGraphicFramePr><p:cNvPr id="4" name="Inventory"/>'
            "</p:nvGraphicFramePr><a:graphic>"
            '<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/table">'
            "<a:tbl><a:tblPr/><a:tblGrid/>"
        )
        for row in [["id", "name", "zone"], ["eng", "Engineering Station", "alternate"]]:
            table += (
                '<a:tr h="100">'
                + "".join(
                    "<a:tc><a:txBody>" + paragraph(c) + "</a:txBody><a:tcPr/></a:tc>" for c in row
                )
                + "</a:tr>"
            )
        table += "</a:tbl></a:graphicData></a:graphic></p:graphicFrame>"
        parts[f"ppt/slides/slide{i}.xml"] = (
            f'<p:sld xmlns:p="{P}" xmlns:a="{A}"><p:cSld><p:spTree><p:nvGrpSpPr/><p:grpSpPr/>'
            '<p:sp><p:nvSpPr><p:cNvPr id="2" name="Text"/></p:nvSpPr><p:txBody>'
            + paragraph(text)
            + "</p:txBody></p:sp>"
            '<p:cxnSp><p:nvCxnSpPr><p:cNvPr id="3" name="Arrow"/></p:nvCxnSpPr><p:spPr/></p:cxnSp>'
            + (table if i == 2 else "")
            + "</p:spTree></p:cSld></p:sld>"
        )
    return parts


def write_documents(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=False)
    (root / "notes.txt").write_text(
        "Engineering Station 10.0.0.1\nTCP 502 allowed\nid=eng\n"
        "name=Engineering Station\nzone=alternate\n",
        encoding="utf-8",
        newline="\n",
    )
    (root / "notes.md").write_text(
        "# Inventory\nHistorical notes; TCP 502 allowed\n- Maintenance connection\n"
        "```html\n<script>alert(1)</script>\n```\n"
        "|id|name|zone|\n|---|---|---|\n|eng|Engineering Station|alternate|\n",
        encoding="utf-8",
        newline="\n",
    )
    (root / "inventory.docx").write_bytes(package(docx_parts()))
    (root / "architecture.pptx").write_bytes(package(pptx_parts()))
