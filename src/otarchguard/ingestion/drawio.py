"""Bounded diagrams.net core models, including canonical raw-DEFLATE pages."""

import base64
import binascii
import re
import zlib
from typing import Literal
from urllib.parse import unquote_to_bytes
from xml.etree import ElementTree as ET

from otarchguard.diagnostics import check_limit, fail
from otarchguard.ingestion.graphical import GraphDocument, bounded, identity
from otarchguard.ingestion.records import GraphEdge, GraphNode, InventoryValue
from otarchguard.ingestion.structured import _PRIVATE
from otarchguard.ingestion.xml_safe import XmlBudget

_STYLE = {
    "shape",
    "rounded",
    "whiteSpace",
    "html",
    "startArrow",
    "endArrow",
    "edgeStyle",
    "container",
    "collapsible",
    "verticalAlign",
    "align",
    "fillColor",
    "strokeColor",
}
_SHAPES = {"rectangle", "ellipse", "cylinder", "cloud", "swimlane"}
_ARROWS = {
    "none",
    "classic",
    "block",
    "open",
    "oval",
    "diamond",
    "thinDiamond",
    "blockThin",
    "openThin",
}


def inflate_page(payload: str, doc: GraphDocument) -> bytes:
    # No whitespace normalization: accept only the documented canonical Base64 form.
    check_limit("drawio_compressed_text", len(payload), doc.limits.source_bytes)
    try:
        encoded = payload.encode("ascii")
        compressed = base64.b64decode(encoded, validate=True)
        if base64.b64encode(compressed) != encoded:
            raise ValueError
    except (UnicodeEncodeError, binascii.Error, ValueError):
        fail("IMPORT_DRAWIO_BASE64", "$", "Invalid/noncanonical diagrams.net Base64.")
    check_limit("drawio_compressed_bytes", len(compressed), doc.limits.source_bytes)
    inflater = zlib.decompressobj(-15)
    chunks: list[bytes] = []
    size = 0
    try:
        for start in range(0, len(compressed), 4096):
            if inflater.eof:
                fail(
                    "IMPORT_DRAWIO_DEFLATE",
                    "$",
                    "Trailing/concatenated compressed streams forbidden.",
                )
            ceiling = min(
                doc.limits.page_bytes - size, doc.limits.expanded_bytes - doc.expanded_bytes - size
            )
            chunk = inflater.decompress(compressed[start : start + 4096], max(1, ceiling + 1))
            size += len(chunk)
            check_limit("drawio_page_bytes", size, doc.limits.page_bytes)
            check_limit(
                "drawio_expanded_bytes", doc.expanded_bytes + size, doc.limits.expanded_bytes
            )
            chunks.append(chunk)
            if inflater.unused_data or inflater.unconsumed_tail:
                fail(
                    "IMPORT_DRAWIO_DEFLATE", "$", "Trailing data or unconsumed compressed payload."
                )
        if not inflater.eof:
            fail("IMPORT_DRAWIO_DEFLATE", "$", "Incomplete raw-DEFLATE stream.")
    except zlib.error:
        fail("IMPORT_DRAWIO_DEFLATE", "$", "Corrupt/unsupported raw-DEFLATE payload.")
    doc.expanded_bytes += size
    text = b"".join(chunks)
    if re.search(rb"%(?![0-9a-fA-F]{2})", text) or re.search(rb"[^A-Za-z0-9%_.!~*'()\-]", text):
        fail("IMPORT_DRAWIO_PERCENT", "$", "Invalid encodeURIComponent percent encoding.")
    try:
        inner = unquote_to_bytes(text).decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        fail("IMPORT_DRAWIO_PERCENT", "$", "Decoded page is not strict UTF-8.")
    return inner.encode("utf-8")


def _styles(value: str, doc: GraphDocument, scope: str, cell_id: str) -> dict[str, str]:
    result: dict[str, str] = {}
    unknown = external = False
    for item in value.split(";"):
        if not item:
            continue
        key, separator, val = item.partition("=")
        if key in {"group", "swimlane", "text"} and not separator:
            key, val = "shape", key
        if key == "shape" and ("stencil" in val or val.startswith("data:")):
            fail("IMPORT_GRAPH_UNSUPPORTED", "$", "Embedded/complex stencil payloads unsupported.")
        if key in {"image", "link", "imageData", "backgroundImage"} or any(
            v in val.lower() for v in ("://", "data:", "javascript:", "file:")
        ):
            external = True
            continue
        if key not in _STYLE or (key == "shape" and val not in _SHAPES | {"group", "text"}):
            unknown = True
            continue
        if key in result:
            fail("IMPORT_DRAWIO_STYLE", "$", "Duplicate supported style key is ambiguous.")
        if key in {"startArrow", "endArrow"} and val not in _ARROWS:
            fail("IMPORT_DRAWIO_STYLE", "$", "Unsupported arrowhead direction indicator.")
        result[key] = val
    if unknown:
        doc.diagnostic("GRAPH_STYLE", scope, cell_id)
    if external:
        doc.diagnostic("GRAPH_EXTERNAL", scope, cell_id)
    return result


def parse_model(model: ET.Element, scope: str, doc: GraphDocument) -> None:
    if model.tag != "mxGraphModel" or len(model) != 1 or model[0].tag != "root":
        fail("IMPORT_GRAPH_ROOT", "$", "Expected mxGraphModel containing one root.")
    for element in model.iter():
        if (element.text or "").strip() or (element.tail or "").strip():
            fail("IMPORT_GRAPH_STRUCTURE", "$", "Unexpected draw.io structural text.")
    cells: dict[str, tuple[ET.Element, str, dict[str, InventoryValue]]] = {}
    for item in model[0]:
        custom: dict[str, InventoryValue] = {}
        label = item.get("value", "")
        cell = item
        cell_id = item.get("id")
        if item.tag in {"object", "UserObject"}:
            if len(item) != 1 or item[0].tag != "mxCell":
                fail("IMPORT_GRAPH_UNSUPPORTED", "$", "Object wrapper must contain one mxCell.")
            cell = item[0]
            if cell.get("id") is not None and cell.get("id") != cell_id:
                fail("IMPORT_GRAPH_DUPLICATE", "$", "Conflicting wrapper/cell IDs.")
            label = item.get("label", item.get("value", cell.get("value", "")))
            for key, value in item.attrib.items():
                if key not in {"id", "label", "value"}:
                    if _PRIVATE.search(key):
                        doc.private_keys.add(key)
                    if key.lower() in {"link", "href", "image"}:
                        doc.diagnostic("GRAPH_EXTERNAL", scope, cell_id or "")
                    else:
                        custom[key] = value
                        doc.keys.add(key)
                        check_limit("graph_keys", len(doc.keys), 64)
        elif item.tag != "mxCell":
            fail("IMPORT_GRAPH_UNSUPPORTED", "$", "Unsupported draw.io root element.")
        name = identity(cell_id, doc.limits)
        if name in cells:
            fail("IMPORT_GRAPH_DUPLICATE", "$", "Duplicate draw.io cell ID within page.")
        check_limit("drawio_cells", len(cells) + 1, doc.limits.nodes + doc.limits.edges)
        bounded(label, doc.limits)
        if "<" in label or ">" in label:
            doc.diagnostic("GRAPH_MARKUP", scope, name)
        if any(k in cell.attrib for k in ("link", "href", "image")):
            doc.diagnostic("GRAPH_EXTERNAL", scope, name)
        if cell.get("visible") == "0" or cell.get("locked") == "1":
            doc.diagnostic("GRAPH_VISIBILITY", scope, name)
        if any(
            k
            not in {
                "id",
                "value",
                "parent",
                "vertex",
                "edge",
                "source",
                "target",
                "style",
                "visible",
                "locked",
                "link",
                "href",
                "image",
                "connectable",
            }
            for k in cell.attrib
        ):
            doc.diagnostic("GRAPH_METADATA", scope, name)
        if cell.get("vertex", "0") not in {"0", "1"} or cell.get("edge", "0") not in {"0", "1"}:
            fail("IMPORT_GRAPH_STRUCTURE", "$", "Invalid draw.io vertex/edge flag.")
        if cell.get("vertex") == "1" and cell.get("edge") == "1":
            fail("IMPORT_GRAPH_STRUCTURE", "$", "Cell cannot be both vertex and edge.")
        cells[name] = cell, label, custom
    # Iterative containment validation bounds chains and rejects cycles, including nonvertices.
    parents = {name: cell.get("parent") for name, (cell, _, _) in cells.items()}
    for name, parent in parents.items():
        chain = {name}
        while parent is not None:
            if parent not in cells or parent in chain:
                fail("IMPORT_GRAPH_PARENT", "$", "Missing or cyclic graphical parent.")
            chain.add(parent)
            check_limit("graph_parent_depth", len(chain), doc.limits.xml_depth)
            parent = parents[parent]
    vertex_ids = {name for name, (cell, _, _) in cells.items() if cell.get("vertex") == "1"}
    containers = {p for p in parents.values() if p in vertex_ids}
    for name, (cell, label, custom) in sorted(cells.items()):
        style = _styles(cell.get("style", ""), doc, scope, name)
        geometry: dict[str, str] = {}
        for child in cell:
            if child.tag != "mxGeometry" or geometry:
                fail("IMPORT_GRAPH_UNSUPPORTED", "$", "Only one mxGeometry is supported per cell.")
            if set(child.attrib) - {"x", "y", "width", "height", "relative", "as"}:
                fail("IMPORT_GRAPH_UNSUPPORTED", "$", "Unsupported geometry attributes.")
            geometry = dict(child.attrib)
            for point in child:
                if (
                    point.tag == "mxPoint"
                    and not len(point)
                    and set(point.attrib) <= {"x", "y", "as"}
                ):
                    continue
                if (
                    point.tag == "Array"
                    and point.get("as") == "points"
                    and all(
                        p.tag == "mxPoint" and not len(p) and set(p.attrib) <= {"x", "y"}
                        for p in point
                    )
                ):
                    continue
                fail("IMPORT_GRAPH_UNSUPPORTED", "$", "Unsupported geometry content.")
        if cell.get("edge") == "1":
            source, destination = cell.get("source"), cell.get("target")
            for endpoint in (source, destination):
                if endpoint is not None:
                    identity(endpoint, doc.limits)
            # Absence is retained as unspecified: no default arrowhead is guessed.
            direction = (
                "start="
                + style.get("startArrow", "unspecified")
                + ";end="
                + style.get("endArrow", "unspecified")
            )
            doc.edge(
                GraphEdge(
                    scope_id=scope,
                    element_id=name,
                    label=label,
                    source=source,
                    destination=destination,
                    parent=cell.get("parent"),
                    direction=direction,
                    direction_origin="arrowheads",
                    unresolved=tuple(
                        k
                        for k, v in (("source", source), ("destination", destination))
                        if v not in vertex_ids
                    ),
                ),
                custom,
            )
        else:
            kind: Literal["layer", "group", "text", "node"] = (
                "layer"
                if name not in vertex_ids
                else "group"
                if (
                    name in containers
                    or style.get("shape") in {"group", "swimlane"}
                    or style.get("container") == "1"
                )
                else "text"
                if style.get("shape") == "text"
                else "node"
            )
            if kind == "layer" and cell.get("parent") is not None and name != "1":
                doc.diagnostic("GRAPH_LAYER", scope, name)
            doc.node(
                GraphNode(
                    scope_id=scope,
                    element_id=name,
                    kind=kind,
                    label=label,
                    parent=cell.get("parent"),
                    geometry=geometry,
                    styles=style,
                ),
                custom,
            )


def parse_drawio(root: ET.Element, doc: GraphDocument, budget: XmlBudget) -> None:
    if root.tag == "mxGraphModel":
        doc.page("standalone", "standalone", "none")
        doc.expanded_bytes = doc.source.byte_count
        check_limit("drawio_page_bytes", doc.expanded_bytes, doc.limits.page_bytes)
        parse_model(root, "standalone", doc)
        return
    if root.tag != "mxfile" or root.get("compressed") not in {None, "true", "false"}:
        fail("IMPORT_GRAPH_ROOT", "$", "Expected a supported diagrams.net mxfile.")
    if root.get("plugins") or root.get("libraries"):
        fail("IMPORT_GRAPH_UNSUPPORTED", "$", "Plugins and embedded libraries are unsupported.")
    if not len(root):
        fail("IMPORT_GRAPH_STRUCTURE", "$", "mxfile must contain diagram pages.")
    for page in root:
        if page.tag != "diagram":
            fail("IMPORT_GRAPH_UNSUPPORTED", "$", "Only diagram children are supported in mxfile.")
        scope = identity(page.get("id"), doc.limits)
        if len(page):
            if len(page) != 1 or page[0].tag != "mxGraphModel" or (page.text or "").strip():
                fail("IMPORT_GRAPH_STRUCTURE", "$", "Expected one uncompressed mxGraphModel.")
            if root.get("compressed") == "true":
                fail("IMPORT_GRAPH_STRUCTURE", "$", "Compression declaration disagrees with page.")
            doc.page(scope, page.get("name", ""), "none")
            size = len(ET.tostring(page[0], encoding="utf-8"))
            check_limit("drawio_page_bytes", size, doc.limits.page_bytes)
            doc.expanded_bytes += size
            model = page[0]
        else:
            if root.get("compressed") == "false":
                fail(
                    "IMPORT_GRAPH_STRUCTURE", "$", "Compressed page contradicts mxfile declaration."
                )
            doc.page(scope, page.get("name", ""), "raw-deflate")
            model = budget.parse(inflate_page(page.text or "", doc))
        check_limit("drawio_expanded_bytes", doc.expanded_bytes, doc.limits.expanded_bytes)
        parse_model(model, scope, doc)
