"""Located, inert documentary observations and explicitly mapped simple tables.

This is a restricted structural reader, not an Office renderer, Markdown engine,
hostname detector or network inference system. Every candidate requires review.
"""

import hashlib
import posixpath
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal
from xml.etree import ElementTree as ET

from otarchguard.diagnostics import check_limit, fail
from otarchguard.ingestion.ooxml import read_parts
from otarchguard.ingestion.records import (
    DocumentEvidence,
    DocumentObservation,
    DocumentProfile,
    ImportDiagnostic,
    ImportDraft,
    SourceDocument,
    StructuredLocation,
)
from otarchguard.ingestion.structured import (
    ExtractedRow,
    Value,
    map_extracted,
    pointer_parts,
    validate_profile,
)
from otarchguard.ingestion.tabular import _safe_text, digest, read_regular
from otarchguard.ingestion.xml_safe import XmlBudget

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
P = "http://schemas.openxmlformats.org/presentationml/2006/main"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
REL = "http://schemas.openxmlformats.org/package/2006/relationships"
CT = "http://schemas.openxmlformats.org/package/2006/content-types"
MAIN = "application/vnd.openxmlformats-officedocument."
DOC_PARTS = re.compile(
    r"\[Content_Types\]\.xml|_rels/\.rels|docProps/(?:core|app)\.xml|"
    r"word/(?:document|styles|settings|numbering|fontTable|webSettings|footnotes|endnotes|"
    r"header[0-9]+|footer[0-9]+)\.xml|word/_rels/document\.xml\.rels|word/theme/theme[0-9]+\.xml"
)
PPT_PARTS = re.compile(
    r"\[Content_Types\]\.xml|_rels/\.rels|docProps/(?:core|app)\.xml|"
    r"ppt/(?:presentation|presProps|viewProps|tableStyles)\.xml|ppt/_rels/presentation\.xml\.rels|"
    r"ppt/(?:slides/slide|slideLayouts/slideLayout|slideMasters/slideMaster)[0-9]+\.xml|"
    r"ppt/(?:slides/_rels/slide|slideLayouts/_rels/slideLayout|slideMasters/_rels/slideMaster)[0-9]+\.xml\.rels|"
    r"ppt/theme/theme[0-9]+\.xml"
)


@dataclass(frozen=True, slots=True)
class DocumentLimits:
    source_bytes: int = 1024 * 1024
    uncompressed_bytes: int = 8 * 1024 * 1024
    members: int = 256
    ratio: int = 100
    xml_depth: int = 32
    xml_elements: int = 150_000
    xml_text: int = 2 * 1024 * 1024
    text: int = 4096
    lines: int = 4000
    observations: int = 4000
    paragraphs: int = 2000
    tables: int = 64
    cells: int = 4000
    slides: int = 128


DOCUMENT_LIMITS = DocumentLimits()
type Category = Literal["heading", "paragraph", "list", "fenced_text", "table_cell", "slide_text"]


class Reader:
    def __init__(self, profile: DocumentProfile, limits: DocumentLimits) -> None:
        self.profile = profile
        self.limits = limits
        self.observations: list[DocumentObservation] = []
        self.diagnostics: list[ImportDiagnostic] = []
        self.tables: dict[str, list[list[tuple[str, StructuredLocation]]]] = {}
        self.counts = dict(paragraphs=0, tables=0, cells=0, slides=0)
        self.collections: set[str] = set()

    def selected(self, collection: str) -> bool:
        self.collections.add(collection)
        return "*" in self.profile.select or collection in self.profile.select

    def diagnostic(self, code: str, location: str) -> None:
        item = ImportDiagnostic(
            code=code,
            field=location,
            message=(
                "Unsupported content excluded from documentary evidence; "
                "no complete rendering claimed."
            ),
        )
        if item not in self.diagnostics:
            check_limit("document_diagnostics", len(self.diagnostics) + 1, 200)
            self.diagnostics.append(item)

    def count(self, name: str) -> None:
        self.counts[name] += 1
        check_limit("document_" + name, self.counts[name], getattr(self.limits, name))

    def add(self, text: str, category: Category, location: StructuredLocation) -> None:
        check_limit("document_text", len(text), self.limits.text)
        _safe_text(text)
        if text and self.selected(location.collection):
            check_limit(
                "document_observations", len(self.observations) + 1, self.limits.observations
            )
            self.observations.append(
                DocumentObservation(
                    observation_id="observation_" + digest([location.model_dump(), category]),
                    category=category,
                    text=text,
                    location=location,
                )
            )

    def table(self, name: str, rows: list[list[tuple[str, StructuredLocation]]]) -> None:
        self.count("tables")
        self.selected(name)
        self.tables[name] = rows
        for row in rows:
            for text, location in row:
                self.count("cells")
                self.add(text, "table_cell", location)

    def text(self, data: bytes) -> None:
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            fail(
                "IMPORT_DOCUMENT_ENCODING",
                "$",
                "Document text must use UTF-8, optionally with BOM.",
            )
        _safe_text(text)
        lines = text.splitlines(keepends=True)
        check_limit("document_lines", len(lines), self.limits.lines)
        fence: str | None = None
        table_number = 0
        i = 0
        keys: list[tuple[str, str, StructuredLocation]] = []
        while i < len(lines):
            # Preserve exact selected text except its physical CR/LF separator.
            line = lines[i].removesuffix("\n").removesuffix("\r")
            check_limit("document_line_text", len(line), self.limits.text)
            location = StructuredLocation(
                collection="text", record=f"line:{i + 1}", pointer=f"/lines/{i + 1}"
            )
            category: Category = "paragraph"
            if self.profile.adapter == "md":
                marker = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
                if fence:
                    category = "fenced_text"
                    if (
                        marker
                        and marker[1][0] == fence[0]
                        and len(marker[1]) >= len(fence)
                        and not line.strip().strip(fence[0])
                    ):
                        fence = None
                elif marker:
                    fence = marker[1]
                    category = "fenced_text"
                elif re.match(r"^ {0,3}#{1,6} ", line):
                    category = "heading"
                elif re.match(r"^\s*(?:[-+*]|[0-9]+[.)]) ", line):
                    category = "list"
                elif (
                    "|" in line
                    and i + 1 < len(lines)
                    and re.fullmatch(
                        r"\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*", lines[i + 1]
                    )
                ):
                    table_number += 1
                    name = f"table:{table_number}"
                    rows = []
                    j = i
                    while j < len(lines) and "|" in lines[j]:
                        value = lines[j].rstrip("\r\n")
                        check_limit("document_line_text", len(value), self.limits.text)
                        if "\\" in value or "`" in value:
                            fail(
                                "IMPORT_DOCUMENT_TABLE",
                                name,
                                "Escaped pipes and code spans in Markdown tables are unsupported.",
                            )
                        if j != i + 1:
                            selected = value
                            if selected.lstrip().startswith("|"):
                                selected = selected[selected.index("|") + 1 :]
                            if selected.rstrip().endswith("|"):
                                selected = selected[: selected.rindex("|")]
                            cells = selected.split("|")
                            rows.append(
                                [
                                    (
                                        cell,
                                        StructuredLocation(
                                            collection=name, record=f"line:{j + 1}/cell:{k + 1}"
                                        ),
                                    )
                                    for k, cell in enumerate(cells)
                                ]
                            )
                        j += 1
                    if len({len(row) for row in rows}) > 1:
                        fail(
                            "IMPORT_DOCUMENT_TABLE", name, "Ragged Markdown tables are unsupported."
                        )
                    self.table(name, rows)
                    i = j
                    continue
                elif "|" in line:
                    self.diagnostic("DOCUMENT_TABLE_AS_TEXT", f"line:{i + 1}")
            self.count("paragraphs")
            self.add(line, category, location)
            key_values_requested = "key-values" in self.profile.select or any(
                t.collection == "key-values" for t in self.profile.tables
            )
            if self.profile.adapter == "txt" and key_values_requested and "=" in line:
                key, value = line.split("=", 1)
                keys.append((key, value, location))
            i += 1
        if fence:
            self.diagnostic("DOCUMENT_UNCLOSED_FENCE", "text")
        if keys:
            if len({key for key, _, _ in keys}) != len(keys):
                fail(
                    "IMPORT_DOCUMENT_TABLE",
                    "key-values",
                    "Duplicate key-value keys are unsupported.",
                )
            self.selected("key-values")
            keys = [
                (key, value, loc.model_copy(update={"collection": "key-values"}))
                for key, value, loc in keys
            ]
            for key, value, loc in keys:
                self.add(key + "=" + value, "paragraph", loc)
            self.tables["key-values"] = [
                [(key, loc) for key, _, loc in keys],
                [(value, loc) for _, value, loc in keys],
            ]

    def ooxml(self, data: bytes) -> None:
        docx = self.profile.adapter == "docx"
        allowed = DOC_PARTS if docx else PPT_PARTS
        directories = (
            {"_rels/", "docProps/", "word/", "word/_rels/", "word/theme/"}
            if docx
            else {
                "_rels/",
                "docProps/",
                "ppt/",
                "ppt/_rels/",
                "ppt/theme/",
                *{f"ppt/{name}/" for name in ("slides", "slideLayouts", "slideMasters")},
                *{f"ppt/{name}/_rels/" for name in ("slides", "slideLayouts", "slideMasters")},
            }
        )
        parts = read_parts(
            data,
            self.limits,
            XmlBudget(self.limits, prefix="document", code="IMPORT_DOCUMENT_XML"),
            allowed,
            directories,
            prefix="document",
        )
        main = "word/document.xml" if docx else "ppt/presentation.xml"
        if not {"[Content_Types].xml", "_rels/.rels", main} <= parts.keys():
            fail("IMPORT_DOCUMENT_PART", "$", "Incomplete OPC package.")
        self.content_types(parts, main, docx)
        relationships = self.relationships(parts, main)
        for name in parts:
            if (
                name not in {main, "[Content_Types].xml"}
                and not name.endswith(".rels")
                and not re.fullmatch(r"ppt/slides/slide[0-9]+\.xml", name)
            ):
                self.diagnostic("DOCUMENT_PART_EXCLUDED", name)
        if docx:
            self.word(parts[main])
        else:
            self.presentation(parts, relationships)

    def content_types(self, parts: dict[str, ET.Element], main: str, docx: bool) -> None:
        types = parts["[Content_Types].xml"]
        if types.tag != f"{{{CT}}}Types":
            fail("IMPORT_DOCUMENT_PART", "$", "Malformed content types.")
        seen: set[str] = set()
        overrides: dict[str, str] = {}
        defaults: dict[str, str] = {}
        for item in types:
            override = item.tag == f"{{{CT}}}Override"
            if not override and item.tag != f"{{{CT}}}Default":
                fail("IMPORT_DOCUMENT_PART", "$", "Unknown content type entry.")
            key = item.get("PartName" if override else "Extension", "")
            kind = item.get("ContentType", "")
            if (
                not key
                or key.casefold() in seen
                or any(token in kind.lower() for token in ("macro", "vba", "ole", "activex"))
            ):
                fail("IMPORT_DOCUMENT_PART", "$", "Invalid, duplicate or active content type.")
            seen.add(key.casefold())
            if override:
                if not key.startswith("/") or key[1:] not in parts:
                    fail("IMPORT_DOCUMENT_PART", "$", "Dangling content-type override.")
                overrides[key[1:]] = kind
            else:
                if (key, kind) not in {
                    ("xml", "application/xml"),
                    ("rels", "application/vnd.openxmlformats-package.relationships+xml"),
                }:
                    fail("IMPORT_DOCUMENT_PART", "$", "Unsupported content-type default.")
                defaults[key] = kind
        expected = MAIN + (
            "wordprocessingml.document.main+xml" if docx else "presentationml.presentation.main+xml"
        )
        if overrides.get(main) != expected:
            fail("IMPORT_DOCUMENT_PART", main, "Only transitional, non-macro documents supported.")
        for name in parts:
            if name == "[Content_Types].xml":
                continue
            kind = overrides.get(name, defaults.get(name.rsplit(".", 1)[-1], ""))
            if not kind or not (
                kind.startswith(MAIN)
                or kind
                in {
                    "application/xml",
                    "application/vnd.openxmlformats-package.relationships+xml",
                    "application/vnd.openxmlformats-package.core-properties+xml",
                }
            ):
                fail("IMPORT_DOCUMENT_PART", name, "Missing or unsupported part content type.")
            if (
                re.fullmatch(r"ppt/slides/slide[0-9]+\.xml", name)
                and kind != MAIN + "presentationml.slide+xml"
            ):
                fail("IMPORT_DOCUMENT_PART", name, "Slide content type mismatch.")

    def relationships(
        self, parts: dict[str, ET.Element], main: str
    ) -> dict[str, dict[str, tuple[str, str]]]:
        result: dict[str, dict[str, tuple[str, str]]] = {}
        for name, root in parts.items():
            if not name.endswith(".rels"):
                continue
            if root.tag != f"{{{REL}}}Relationships":
                fail("IMPORT_DOCUMENT_RELATIONSHIP", name, "Invalid relationships part.")
            links: dict[str, tuple[str, str]] = {}
            for item in root:
                identity, target, kind = (item.get(key, "") for key in ("Id", "Target", "Type"))
                if (
                    item.tag != f"{{{REL}}}Relationship"
                    or not identity
                    or identity in links
                    or item.get("TargetMode") not in {None, "Internal"}
                ):
                    fail(
                        "IMPORT_DOCUMENT_RELATIONSHIP",
                        name,
                        "External, duplicate or malformed relationships forbidden.",
                    )
                if not target or any(c in target for c in "\\:%?#") or target.startswith("//"):
                    fail("IMPORT_DOCUMENT_RELATIONSHIP", name, "Unsafe relationship target.")
                base = "" if name == "_rels/.rels" else name.split("/_rels/")[0]
                resolved = (
                    posixpath.normpath(posixpath.join(base, target))
                    if not target.startswith("/")
                    else target[1:]
                )
                if (
                    resolved not in parts
                    or resolved.endswith(".rels")
                    or resolved == "[Content_Types].xml"
                ):
                    fail(
                        "IMPORT_DOCUMENT_RELATIONSHIP",
                        name,
                        "Missing or invalid relationship target.",
                    )
                suffix = kind.removeprefix(R + "/")
                allowed = {
                    "officeDocument",
                    "extended-properties",
                    "styles",
                    "settings",
                    "numbering",
                    "fontTable",
                    "webSettings",
                    "theme",
                    "header",
                    "footer",
                    "footnotes",
                    "endnotes",
                    "slide",
                    "slideLayout",
                    "slideMaster",
                    "presProps",
                    "viewProps",
                    "tableStyles",
                }
                core = REL + "/metadata/core-properties"
                if (not kind.startswith(R + "/") or suffix not in allowed) and kind != core:
                    fail("IMPORT_DOCUMENT_RELATIONSHIP", name, "Unsupported relationship type.")
                if suffix == "officeDocument" and (name != "_rels/.rels" or resolved != main):
                    fail(
                        "IMPORT_DOCUMENT_RELATIONSHIP", name, "Main document relationship mismatch."
                    )
                if suffix == "slide" and (
                    name != "ppt/_rels/presentation.xml.rels"
                    or not re.fullmatch(r"ppt/slides/slide[0-9]+\.xml", resolved)
                ):
                    fail(
                        "IMPORT_DOCUMENT_RELATIONSHIP", name, "Slide relationship context mismatch."
                    )
                if resolved == main and suffix != "officeDocument":
                    fail(
                        "IMPORT_DOCUMENT_RELATIONSHIP",
                        name,
                        "Cyclic main-document relationship forbidden.",
                    )
                links[identity] = (resolved, kind)
            result[name] = links
        if (
            sum(value == (main, R + "/officeDocument") for value in result["_rels/.rels"].values())
            != 1
        ):
            fail("IMPORT_DOCUMENT_RELATIONSHIP", "$", "One internal main document required.")
        return result

    def word_text(self, paragraph: ET.Element) -> str:
        chunks = []
        for node in paragraph.iter():
            if node.tag in {
                f"{{{W}}}{name}"
                for name in (
                    "ins",
                    "del",
                    "moveFrom",
                    "moveTo",
                    "fldSimple",
                    "fldChar",
                    "instrText",
                    "altChunk",
                    "object",
                    "sdt",
                )
            }:
                fail(
                    "IMPORT_DOCUMENT_CONSTRUCT",
                    "word/document.xml",
                    "Tracked changes, fields, objects and content controls unsupported.",
                )
            if node.tag == f"{{{W}}}t":
                chunks.append(node.text or "")
            elif node.tag == f"{{{W}}}tab":
                chunks.append("\t")
            elif node.tag in {f"{{{W}}}br", f"{{{W}}}cr"}:
                chunks.append("\n")
            elif node.tag == f"{{{W}}}noBreakHyphen":
                chunks.append("\u2011")
            elif node.tag == f"{{{W}}}softHyphen":
                chunks.append("\u00ad")
            elif node.tag == f"{{{W}}}ptab":
                fail(
                    "IMPORT_DOCUMENT_CONSTRUCT", "word/document.xml", "Positional tabs unsupported."
                )
            elif node.tag in {
                f"{{{W}}}{name}"
                for name in (
                    "footnoteReference",
                    "endnoteReference",
                    "commentReference",
                )
            }:
                self.diagnostic("DOCUMENT_REFERENCE_EXCLUDED", "word/document.xml")
            elif node.tag in {f"{{{W}}}drawing", f"{{{W}}}pict"}:
                fail(
                    "IMPORT_DOCUMENT_CONSTRUCT",
                    "word/document.xml",
                    "Drawing text and images unsupported.",
                )
        text = "".join(chunks)
        check_limit("document_text", len(text), self.limits.text)
        return text

    def word(self, root: ET.Element) -> None:
        if any(not node.tag.startswith("{" + W + "}") for node in root.iter()):
            fail(
                "IMPORT_DOCUMENT_CONSTRUCT",
                "word/document.xml",
                "Foreign inline XML and alternate content unsupported.",
            )
        forbidden = {
            f"{{{W}}}{name}"
            for name in (
                "ins",
                "del",
                "moveFrom",
                "moveTo",
                "fldSimple",
                "fldChar",
                "instrText",
                "delText",
                "altChunk",
                "object",
                "sdt",
                "drawing",
                "pict",
                "sym",
                "pPrChange",
                "rPrChange",
                "tblPrChange",
                "tcPrChange",
                "trPrChange",
                "sectPrChange",
                "gridBefore",
                "gridAfter",
            )
        }
        if any(node.tag in forbidden for node in root.iter()):
            fail(
                "IMPORT_DOCUMENT_CONSTRUCT",
                "word/document.xml",
                "Tracked changes, dynamic fields, objects and complex layout unsupported.",
            )
        body = root.find(f"{{{W}}}body")
        if root.tag != f"{{{W}}}document" or body is None:
            fail("IMPORT_DOCUMENT_PART", "$", "Invalid Word document structure.")
        self.selected("word/document.xml")
        for child in body:
            if child.tag == f"{{{W}}}p":
                self.count("paragraphs")
                style = child.find(f"{{{W}}}pPr/{{{W}}}pStyle")
                heading = style is not None and re.fullmatch(
                    r"Heading[1-9]", style.get(f"{{{W}}}val", "")
                )
                self.add(
                    self.word_text(child),
                    "heading" if heading else "paragraph",
                    StructuredLocation(
                        collection="word/document.xml",
                        record=f"paragraph:{self.counts['paragraphs']}",
                    ),
                )
            elif child.tag == f"{{{W}}}tbl":
                name = f"word/document.xml/table:{self.counts['tables'] + 1}"
                rows = []
                if any(
                    node.tag not in {f"{{{W}}}tblPr", f"{{{W}}}tblGrid", f"{{{W}}}tr"}
                    for node in child
                ):
                    fail("IMPORT_DOCUMENT_TABLE", name, "Unsupported table structure.")
                for r, row in enumerate(child.findall(f"{{{W}}}tr"), 1):
                    cells = []
                    if any(node.tag not in {f"{{{W}}}trPr", f"{{{W}}}tc"} for node in row):
                        fail("IMPORT_DOCUMENT_TABLE", name, "Unsupported row structure.")
                    for c, cell in enumerate(row.findall(f"{{{W}}}tc"), 1):
                        if any(node.tag not in {f"{{{W}}}tcPr", f"{{{W}}}p"} for node in cell):
                            fail("IMPORT_DOCUMENT_TABLE", name, "Unsupported cell structure.")
                        if any(
                            node.tag
                            in {
                                f"{{{W}}}gridSpan",
                                f"{{{W}}}vMerge",
                                f"{{{W}}}hMerge",
                                f"{{{W}}}tbl",
                            }
                            for node in cell.iter()
                        ):
                            fail(
                                "IMPORT_DOCUMENT_TABLE",
                                name,
                                "Nested or merged tables unsupported.",
                            )
                        paragraphs = cell.findall(f"{{{W}}}p")
                        for _ in paragraphs:
                            self.count("paragraphs")
                        value = "\n".join(self.word_text(p) for p in paragraphs)
                        cells.append(
                            (value, StructuredLocation(collection=name, record=f"row:{r}/cell:{c}"))
                        )
                    rows.append(cells)
                self.table(name, rows)
            elif child.tag == f"{{{W}}}sectPr":
                self.diagnostic("DOCUMENT_LAYOUT_EXCLUDED", "word/document.xml/sectPr")
            else:
                fail(
                    "IMPORT_DOCUMENT_CONSTRUCT",
                    "word/document.xml",
                    "Unsupported Word body content.",
                )

    def presentation(
        self, parts: dict[str, ET.Element], relationships: dict[str, dict[str, tuple[str, str]]]
    ) -> None:
        root = parts["ppt/presentation.xml"]
        if root.tag != f"{{{P}}}presentation":
            fail("IMPORT_DOCUMENT_PART", "$", "Invalid presentation structure.")
        ordered = root.find(f"{{{P}}}sldIdLst")
        if ordered is None:
            fail("IMPORT_DOCUMENT_PART", "$", "Explicit slide order required.")
        seen: set[str] = set()
        ids: set[int] = set()
        for entry in ordered:
            self.count("slides")
            identity = entry.get("id", "")
            numeric_id = int(identity) if re.fullmatch(r"[0-9]{1,10}", identity) else -1
            target, kind = relationships.get("ppt/_rels/presentation.xml.rels", {}).get(
                entry.get(f"{{{R}}}id", ""), ("", "")
            )
            if (
                entry.tag != f"{{{P}}}sldId"
                or not 256 <= numeric_id <= 2_147_483_647
                or numeric_id in ids
                or target in seen
                or kind != R + "/slide"
            ):
                fail("IMPORT_DOCUMENT_RELATIONSHIP", "$", "Invalid slide identities or order.")
            seen.add(target)
            ids.add(numeric_id)
            slide = parts[target]
            tree = slide.find(f"{{{P}}}cSld/{{{P}}}spTree")
            if slide.tag != f"{{{P}}}sld" or tree is None:
                fail("IMPORT_DOCUMENT_PART", target, "Invalid slide structure.")
            collection = f"slide:{identity}"
            self.selected(collection)
            shapes: set[int] = set()
            for shape in tree:
                if shape.tag in {f"{{{P}}}nvGrpSpPr", f"{{{P}}}grpSpPr"}:
                    continue
                properties = shape.find(f".//{{{P}}}cNvPr")
                shape_id = properties.get("id", "") if properties is not None else ""
                shape_number = int(shape_id) if re.fullmatch(r"[0-9]{1,10}", shape_id) else -1
                if not 1 <= shape_number <= 4_294_967_295 or shape_number in shapes:
                    fail(
                        "IMPORT_DOCUMENT_CONSTRUCT",
                        target,
                        "Unique slide-local shape IDs required.",
                    )
                shapes.add(shape_number)
                prefix = f"{target}/order:{self.counts['slides']}/shape:{shape_id}"
                if shape.tag == f"{{{P}}}sp":
                    for i, paragraph in enumerate(shape.findall(f"{{{P}}}txBody/{{{A}}}p"), 1):
                        self.count("paragraphs")
                        self.add(
                            self.slide_text(paragraph),
                            "slide_text",
                            StructuredLocation(
                                collection=collection, record=f"{prefix}/paragraph:{i}"
                            ),
                        )
                elif shape.tag == f"{{{P}}}graphicFrame":
                    table = shape.find(f"{{{A}}}graphic/{{{A}}}graphicData/{{{A}}}tbl")
                    if table is None:
                        self.diagnostic("DOCUMENT_GRAPHIC_EXCLUDED", prefix)
                        continue
                    name = f"{collection}/table:{shape_id}"
                    rows = []
                    for r, row in enumerate(table.findall(f"{{{A}}}tr"), 1):
                        cells = []
                        for c, cell in enumerate(row.findall(f"{{{A}}}tc"), 1):
                            if any(
                                cell.get(key) not in {None, "0", "1"}
                                for key in ("gridSpan", "rowSpan")
                            ) or any(
                                cell.get(key) not in {None, "0"} for key in ("hMerge", "vMerge")
                            ):
                                fail(
                                    "IMPORT_DOCUMENT_TABLE",
                                    name,
                                    "Merged slide tables unsupported.",
                                )
                            paragraphs = cell.findall(f"{{{A}}}txBody/{{{A}}}p")
                            for _ in paragraphs:
                                self.count("paragraphs")
                            value = "\n".join(self.slide_text(p) for p in paragraphs)
                            cells.append(
                                (
                                    value,
                                    StructuredLocation(
                                        collection=name, record=f"{prefix}/row:{r}/cell:{c}"
                                    ),
                                )
                            )
                        rows.append(cells)
                    self.table(name, rows)
                else:
                    self.diagnostic("DOCUMENT_SHAPE_EXCLUDED", prefix)
        if seen != {n for n in parts if re.fullmatch(r"ppt/slides/slide[0-9]+\.xml", n)}:
            fail("IMPORT_DOCUMENT_PART", "$", "Unreferenced slide parts unsupported.")

    def slide_text(self, paragraph: ET.Element) -> str:
        if any(
            node.tag
            not in {
                f"{{{A}}}{name}"
                for name in (
                    "pPr",
                    "endParaRPr",
                    "r",
                    "br",
                )
            }
            for node in paragraph
        ):
            fail("IMPORT_DOCUMENT_CONSTRUCT", "$", "Unsupported slide paragraph content.")
        for run in paragraph.findall(f"{{{A}}}r"):
            if any(node.tag not in {f"{{{A}}}rPr", f"{{{A}}}t"} for node in run):
                fail("IMPORT_DOCUMENT_CONSTRUCT", "$", "Unsupported slide text run content.")
        chunks = []
        for node in paragraph.iter():
            if node.tag == f"{{{A}}}fld":
                fail("IMPORT_DOCUMENT_CONSTRUCT", "$", "Dynamic slide fields unsupported.")
            if node.tag == f"{{{A}}}t":
                chunks.append(node.text or "")
            elif node.tag == f"{{{A}}}br":
                chunks.append("\n")
        value = "".join(chunks)
        check_limit("document_text", len(value), self.limits.text)
        return value


def create_document_draft(
    path: Path, profile: DocumentProfile, limits: DocumentLimits = DOCUMENT_LIMITS
) -> ImportDraft:
    from otarchguard.ingestion.project import _no_links

    _no_links(path)
    if path.suffix.lower() != "." + profile.adapter:
        fail(
            "IMPORT_FORMAT",
            "$",
            "Document adapter and extension must agree; PDF/VSDX are deferred.",
        )
    validate_profile(profile)
    for selection in profile.select:
        _safe_text(selection)
        check_limit("document_selector_text", len(selection), 256)
    if any(table.entity not in {"asset", "zone", "interface"} for table in profile.tables):
        fail(
            "IMPORT_DOCUMENT_MAPPING",
            "$",
            "Documents can propose only asset, zone or interface candidates.",
        )
    data = read_regular(path, limits.source_bytes)
    reader = Reader(profile, limits)
    if profile.adapter in {"txt", "md"}:
        reader.text(data)
    else:
        reader.ooxml(data)
    if len(set(profile.select)) != len(profile.select) or (
        "*" in profile.select and len(profile.select) != 1
    ):
        fail(
            "IMPORT_DOCUMENT_SELECTION",
            "$",
            "Use distinct exact collections or a single explicit *.",
        )
    if "*" not in profile.select and not set(profile.select) <= reader.collections:
        fail("IMPORT_DOCUMENT_SELECTION", "$", "A selected document collection is absent.")
    tables: dict[str, tuple[ExtractedRow, ...]] = {}
    for mapping in profile.tables:
        rows = reader.tables.get(mapping.collection)
        if (
            rows is None
            or not reader.selected(mapping.collection)
            or mapping.header_row > len(rows)
        ):
            fail(
                "IMPORT_DOCUMENT_MAPPING",
                mapping.name,
                "Select an existing simple table and header row.",
            )
        headers = [text for text, _ in rows[mapping.header_row - 1]]
        if len(set(headers)) != len(headers) or not headers or any(not h for h in headers):
            fail(
                "IMPORT_DOCUMENT_TABLE",
                mapping.name,
                "Unique nonempty exact table headers required.",
            )
        extracted = []
        for index, row in enumerate(rows[mapping.header_row :], mapping.header_row + 1):
            if len(row) != len(headers):
                fail("IMPORT_DOCUMENT_TABLE", mapping.name, "Rectangular simple tables required.")
            values = {}
            for field, spec in mapping.fields.items():
                names = pointer_parts(spec.path)
                if len(names) != 1 or names[0] not in headers:
                    fail(
                        "IMPORT_DOCUMENT_MAPPING",
                        mapping.name,
                        "Map a single exact header with /escaped-header.",
                    )
                text, location = row[headers.index(names[0])]
                values[field] = Value(
                    text,
                    location,
                    rule="document_key_value_rhs"
                    if mapping.collection == "key-values"
                    else "document_table_cell",
                )
            extracted.append(
                ExtractedRow(
                    StructuredLocation(collection=mapping.collection, record=f"row:{index}"),
                    values,
                    len(headers) - len(values),
                )
            )
        tables[mapping.name] = tuple(extracted)
    sha = hashlib.sha256(data).hexdigest()
    source = SourceDocument(
        source_id="src_" + sha,
        sha256=sha,
        name=path.name,
        format=profile.adapter,
        byte_count=len(data),
        encoding="utf-8",
        delimiter="",
    )
    document = DocumentEvidence(
        observations=tuple(reader.observations),
        summary={
            **reader.counts,
            "selected_observations": len(reader.observations),
            "unsupported_diagnostics": len(reader.diagnostics),
            "mapped_tables": len(profile.tables),
        },
    )
    return map_extracted(source, profile, tables, reader.diagnostics, document=document)


def inspect_document(path: Path, adapter: str) -> dict[str, object]:
    profile = DocumentProfile.model_validate(dict(profile_version=4, adapter=adapter, select=["*"]))
    draft = create_document_draft(path, profile)
    assert draft.document is not None
    return {
        "source": draft.source.model_dump(),
        "subset_version": 1,
        "summary": draft.document.summary,
        "limits": asdict(DOCUMENT_LIMITS),
        "diagnostics": [d.model_dump() for d in draft.diagnostics],
        "selected_locations": [o.location.model_dump() for o in draft.document.observations[:20]],
        "preview": [o.model_dump() for o in draft.document.observations[:10]],
        "scope": "Located documentary text only; no inferred declarations or permissions. "
        "No rendered page numbers or OCR.",
    }
