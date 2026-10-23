"""Namespace-aware structural GraphML subset; all edges remain diagram evidence."""

from collections import Counter
from dataclasses import dataclass
from xml.etree import ElementTree as ET

from otarchguard.diagnostics import check_limit, fail
from otarchguard.ingestion.graphical import GraphDocument, bounded, identity
from otarchguard.ingestion.numbers import NumericToken, parse_number
from otarchguard.ingestion.records import GraphEdge, GraphNode, InventoryValue
from otarchguard.ingestion.structured import _PRIVATE
from otarchguard.ingestion.tabular import digest

NS = "http://graphml.graphdrawing.org/xmlns"


def tag(name: str) -> str:
    return "{" + NS + "}" + name


@dataclass(frozen=True)
class Key:
    target: str
    kind: str
    default: InventoryValue
    has_default: bool


def _scalar(element: ET.Element, kind: str, doc: GraphDocument) -> InventoryValue:
    if len(element):
        fail("IMPORT_GRAPH_UNSUPPORTED", "$", "GraphML extension/structured data is unsupported.")
    value = bounded(element.text or "", doc.limits)
    if kind == "string":
        return value
    if kind == "boolean":
        if value not in {"true", "false", "1", "0"}:
            fail("IMPORT_GRAPH_ATTRIBUTE", "$", "Invalid GraphML boolean.")
        return value in {"true", "1"}
    number = parse_number(value)
    if kind in {"int", "long"} and (
        isinstance(number, NumericToken) and number.numeric_category != "integer"
    ):
        fail("IMPORT_GRAPH_ATTRIBUTE", "$", "Integer GraphML key requires an integer token.")
    return number


def _boolean(value: str) -> bool:
    if value not in {"true", "false", "1", "0"}:
        fail("IMPORT_GRAPH_DIRECTION", "$", "GraphML directed override must be boolean.")
    return value in {"true", "1"}


def parse_graphml(root: ET.Element, doc: GraphDocument) -> None:
    if root.tag != tag("graphml"):
        fail("IMPORT_GRAPH_ROOT", "$", "Expected the GraphML root namespace.")
    allowed_tags = {
        tag(n) for n in ("graphml", "key", "default", "graph", "node", "edge", "data", "desc")
    }
    for element in root.iter():
        if element.tag not in allowed_tags:
            fail(
                "IMPORT_GRAPH_UNSUPPORTED",
                "$",
                "GraphML extensions, ports, hyperedges and locators are unsupported.",
            )
        allowed_attributes = {
            tag("graphml"): {"{http://www.w3.org/2001/XMLSchema-instance}schemaLocation"},
            tag("graph"): {"id", "edgedefault", "parse.nodeids", "parse.edgeids", "parse.order"},
            tag("key"): {"id", "for", "attr.name", "attr.type"},
            tag("node"): {"id"},
            tag("edge"): {"id", "source", "target", "directed"},
            tag("data"): {"key", "id"},
            tag("default"): set(),
            tag("desc"): set(),
        }[element.tag]
        if {"sourceport", "targetport"} & element.attrib.keys():
            fail("IMPORT_GRAPH_UNSUPPORTED", "$", "GraphML endpoint ports are unsupported.")
        if set(element.attrib) - allowed_attributes:
            doc.diagnostic("GRAPH_METADATA", "document", element.get("id", ""))
        if element.tag in {tag("data"), tag("default"), tag("desc")}:
            bounded(element.text or "", doc.limits)
            if len(element):
                fail(
                    "IMPORT_GRAPH_UNSUPPORTED",
                    "$",
                    "Structured GraphML data/description unsupported.",
                )
        if (
            element.text
            and element.tag not in {tag("data"), tag("default"), tag("desc")}
            and element.text.strip()
        ):
            fail("IMPORT_GRAPH_STRUCTURE", "$", "Unexpected GraphML structural text.")
        if element.tail and element.tail.strip():
            fail("IMPORT_GRAPH_STRUCTURE", "$", "Unexpected GraphML trailing text.")
    keys: dict[str, Key] = {}
    for element in root:
        if element.tag != tag("key"):
            if element.tag not in {tag("graph"), tag("desc")}:
                fail("IMPORT_GRAPH_STRUCTURE", "$", "Unsupported GraphML root child.")
            continue
        key = identity(element.get("id"), doc.limits)
        if key in keys:
            fail("IMPORT_GRAPH_DUPLICATE", "$", "Duplicate GraphML key ID.")
        check_limit("graph_keys", len(keys) + 1, 64)
        target, kind = element.get("for", "all"), element.get("attr.type", "string")
        if target not in {"all", "node", "edge", "graph"} or kind not in {
            "string",
            "boolean",
            "int",
            "long",
            "float",
            "double",
        }:
            fail("IMPORT_GRAPH_ATTRIBUTE", "$", "Unsupported GraphML key target/type.")
        defaults = [e for e in element if e.tag == tag("default")]
        if len(defaults) > 1 or any(e.tag not in {tag("default"), tag("desc")} for e in element):
            fail("IMPORT_GRAPH_STRUCTURE", "$", "Invalid GraphML key definition.")
        keys[key] = Key(
            target, kind, _scalar(defaults[0], kind, doc) if defaults else None, bool(defaults)
        )
        if _PRIVATE.search(element.get("attr.name", "")) or _PRIVATE.search(key):
            doc.private_keys.add(key)
    doc.keys.update(keys)

    def values(element: ET.Element, target: str) -> dict[str, InventoryValue]:
        result = {
            k: v.default for k, v in keys.items() if v.target in {target, "all"} and v.has_default
        }
        seen: set[str] = set()
        for child in element:
            if child.tag == tag("desc"):
                _scalar(child, "string", doc)
                continue
            if child.tag != tag("data"):
                fail(
                    "IMPORT_GRAPH_UNSUPPORTED",
                    "$",
                    "Nested graphs and non-scalar node/edge data are unsupported.",
                )
            key = child.get("key", "")
            if key not in keys or key in seen or keys[key].target not in {target, "all"}:
                fail(
                    "IMPORT_GRAPH_ATTRIBUTE",
                    "$",
                    "Unknown, duplicate or mismatched GraphML data key.",
                )
            seen.add(key)
            result[key] = _scalar(child, keys[key].kind, doc)
        return result

    graphs = [e for e in root if e.tag == tag("graph")]
    if not graphs:
        fail("IMPORT_GRAPH_STRUCTURE", "$", "At least one GraphML graph is required.")
    for graph in graphs:
        scope = identity(graph.get("id"), doc.limits)
        default = graph.get("edgedefault")
        if default not in {"directed", "undirected"}:
            fail(
                "IMPORT_GRAPH_DIRECTION", "$", "Explicit directed/undirected edgedefault required."
            )
        doc.page(scope, scope, "none")
        nodes = [e for e in graph if e.tag == tag("node")]
        edges = [e for e in graph if e.tag == tag("edge")]
        for child in graph:
            if child.tag not in {tag("node"), tag("edge"), tag("data"), tag("desc")}:
                fail("IMPORT_GRAPH_UNSUPPORTED", "$", "Unsupported GraphML graph structure.")
        graph_metadata = ET.Element(tag("graph"))
        graph_metadata.extend(e for e in graph if e.tag in {tag("data"), tag("desc")})
        values(graph_metadata, "graph")
        seen: set[str] = set()
        for node in nodes:
            node_id = identity(node.get("id"), doc.limits)
            if node_id in seen:
                fail("IMPORT_GRAPH_DUPLICATE", "$", "Duplicate GraphML node ID in graph.")
            seen.add(node_id)
            doc.node(
                GraphNode(scope_id=scope, element_id=node_id, kind="node", label=""),
                values(node, "node"),
            )
        node_ids = set(seen)
        occurrences: Counter[str] = Counter()
        # Compute anonymous edge identities from structure, independent of element order.
        for edge in edges:
            attributes = values(edge, "edge")
            source, destination = edge.get("source"), edge.get("target")
            if source is not None:
                identity(source, doc.limits)
            if destination is not None:
                identity(destination, doc.limits)
            override = edge.get("directed")
            direction = (
                default
                if override is None
                else ("directed" if _boolean(override) else "undirected")
            )
            edge_id = edge.get("id")
            if edge_id is None:
                key = digest(
                    [
                        source,
                        destination,
                        direction,
                        {
                            k: (v.model_dump() if isinstance(v, NumericToken) else v)
                            for k, v in sorted(attributes.items())
                        },
                    ]
                )
                occurrences[key] += 1
                edge_id = "anonymous_" + key + "_" + str(occurrences[key])
            identity(edge_id, doc.limits)
            if edge_id in seen:
                fail("IMPORT_GRAPH_DUPLICATE", "$", "Duplicate GraphML element/edge ID in graph.")
            seen.add(edge_id)
            doc.edge(
                GraphEdge(
                    scope_id=scope,
                    element_id=edge_id,
                    source=source,
                    destination=destination,
                    label="",
                    direction=direction,
                    direction_origin="graph_default" if override is None else "edge_override",
                    unresolved=tuple(
                        name
                        for name, endpoint in (("source", source), ("destination", destination))
                        if endpoint not in node_ids
                    ),
                ),
                attributes,
            )
