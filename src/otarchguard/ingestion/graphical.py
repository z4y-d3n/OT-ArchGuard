"""Shared bounded graphical evidence and projection into structured mapping."""

import hashlib
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

from otarchguard.diagnostics import check_limit, fail
from otarchguard.ingestion.records import (
    GraphEdge,
    GraphEvidence,
    GraphNode,
    GraphPage,
    GraphProfile,
    ImportDiagnostic,
    ImportDraft,
    InventoryValue,
    SourceDocument,
    StructuredLocation,
)
from otarchguard.ingestion.structured import (
    ExtractedRow,
    Value,
    lookup,
    map_extracted,
    pointer_parts,
    pointer_token,
    validate_profile,
)
from otarchguard.ingestion.tabular import AdapterCapabilities, digest, read_regular
from otarchguard.ingestion.xml_safe import XmlBudget


@dataclass(frozen=True, slots=True)
class GraphLimits:
    source_bytes: int = 1024 * 1024
    page_bytes: int = 2 * 1024 * 1024
    expanded_bytes: int = 8 * 1024 * 1024
    pages: int = 16
    nodes: int = 1000
    edges: int = 1000
    text: int = 4096
    identity: int = 128
    xml_depth: int = 24
    xml_elements: int = 150_000
    xml_text: int = 8 * 1024 * 1024
    diagnostics: int = 200


GRAPH_LIMITS = GraphLimits()


@dataclass
class GraphDocument:
    source: SourceDocument
    limits: GraphLimits
    pages: list[GraphPage] = field(default_factory=list)
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)
    attributes: dict[tuple[str, str], dict[str, InventoryValue]] = field(default_factory=dict)
    keys: set[str] = field(default_factory=set)
    private_keys: set[str] = field(default_factory=set)
    diagnostics: list[ImportDiagnostic] = field(default_factory=list)
    expanded_bytes: int = 0

    def diagnostic(self, code: str, scope: str, element: str = "") -> None:
        check_limit("graph_diagnostics", len(self.diagnostics) + 1, self.limits.diagnostics)
        self.diagnostics.append(
            ImportDiagnostic(
                code=code,
                field=scope + "/" + element,
                message={
                    "GRAPH_DANGLING": "Unresolved graphical endpoint; no target is guessed.",
                    "GRAPH_EXTERNAL": "Resource omitted; no fetching or execution.",
                    "GRAPH_STYLE": "Unsupported style metadata omitted; no role inference.",
                    "GRAPH_MARKUP": "Label contains inert markup; no rendering is performed.",
                    "GRAPH_LAYER": "Additional graphical layer retained as evidence only.",
                    "GRAPH_VISIBILITY": "Hidden/locked graphical element requires owner review.",
                    "GRAPH_METADATA": "Unselected metadata omitted; source digest still binds it.",
                }[code],
            )
        )

    def page(self, scope: str, name: str, compression: Literal["none", "raw-deflate"]) -> None:
        identity(scope, self.limits)
        bounded(name, self.limits)
        if scope in {p.scope_id for p in self.pages}:
            fail("IMPORT_GRAPH_DUPLICATE", "$", "Duplicate page/graph ID.")
        check_limit("graph_pages", len(self.pages) + 1, self.limits.pages)
        self.pages.append(GraphPage(scope_id=scope, name=name, compression=compression))

    def node(self, node: GraphNode, attributes: dict[str, InventoryValue]) -> None:
        check_limit("graph_nodes", len(self.nodes) + 1, self.limits.nodes)
        self.nodes.append(node)
        self.attributes[node.scope_id, node.element_id] = attributes

    def edge(self, edge: GraphEdge, attributes: dict[str, InventoryValue]) -> None:
        check_limit("graph_edges", len(self.edges) + 1, self.limits.edges)
        self.edges.append(edge)
        self.attributes[edge.scope_id, edge.element_id] = attributes

    def finish(self) -> None:
        for edge in self.edges:
            if edge.unresolved:
                self.diagnostic("GRAPH_DANGLING", edge.scope_id, edge.element_id)

    def evidence(self, scopes: tuple[str, ...]) -> GraphEvidence:
        return GraphEvidence(
            adapter=self.source.format,  # type: ignore[arg-type]
            pages=tuple(sorted(self.pages, key=lambda p: p.scope_id)),
            nodes=tuple(
                sorted(
                    (n for n in self.nodes if n.scope_id in scopes),
                    key=lambda n: (n.scope_id, n.element_id),
                )
            ),
            edges=tuple(
                sorted(
                    (e for e in self.edges if e.scope_id in scopes),
                    key=lambda e: (e.scope_id, e.element_id),
                )
            ),
            keys=tuple(sorted(self.keys)),
            expanded_bytes=self.expanded_bytes,
            selected_scopes=tuple(sorted(scopes)),
        )


def bounded(value: str, limits: GraphLimits) -> str:
    check_limit("graph_text", len(value), limits.text)
    return value


def identity(value: str | None, limits: GraphLimits) -> str:
    if not value or not value.strip():
        fail("IMPORT_GRAPH_ID", "$", "Explicit nonempty graph/page/element IDs required.")
    check_limit("graph_identity", len(value), limits.identity)
    return value


def read_graph(path: Path, adapter: str, limits: GraphLimits = GRAPH_LIMITS) -> GraphDocument:
    if adapter not in {"drawio", "graphml"}:
        fail("IMPORT_FORMAT", "$", "Select drawio or graphml explicitly for compatible XML.")
    if path.suffix.lower() not in {".xml", ".drawio" if adapter == "drawio" else ".graphml"}:
        fail("IMPORT_FORMAT", "$", "Source extension disagrees with graphical adapter.")
    data = read_regular(path, limits.source_bytes)
    sha = hashlib.sha256(data).hexdigest()
    source = SourceDocument.model_validate(
        dict(
            source_id="src_" + sha,
            sha256=sha,
            name=path.name,
            format=adapter,
            byte_count=len(data),
            encoding="utf-8",
            delimiter="",
        )
    )
    document = GraphDocument(source, limits)
    budget = XmlBudget(limits)
    root = budget.parse(data)
    if adapter == "graphml":
        from otarchguard.ingestion.graphml import parse_graphml

        document.expanded_bytes = len(data)
        parse_graphml(root, document)
    else:
        from otarchguard.ingestion.drawio import parse_drawio

        parse_drawio(root, document, budget)
    document.finish()
    return document


def capabilities(adapter: str) -> AdapterCapabilities:
    return AdapterCapabilities(
        adapter,
        ("." + adapter, ".xml"),
        1,
        True,
        ("explicit scopes/fields", "no network semantics", "bounded XML"),
    )


def inspect_graph(path: Path, adapter: str) -> dict[str, object]:
    doc = read_graph(path, adapter)
    return {
        "source": doc.source.model_dump(),
        "capabilities": asdict(capabilities(adapter)),
        "limits": asdict(doc.limits),
        "pages": [p.model_dump() for p in sorted(doc.pages, key=lambda p: p.scope_id)],
        "nodes": len(doc.nodes),
        "groups": sum(n.kind == "group" for n in doc.nodes),
        "node_kinds": {
            k: sum(n.kind == k for n in doc.nodes) for k in sorted({n.kind for n in doc.nodes})
        },
        "edges": len(doc.edges),
        "directions": {
            k: sum(e.direction == k for e in doc.edges)
            for k in sorted({e.direction for e in doc.edges})
        },
        "keys": sorted(doc.keys),
        "expanded_bytes": doc.expanded_bytes,
        "diagnostics": [
            d.model_dump() for d in sorted(doc.diagnostics, key=lambda d: (d.field or "", d.code))
        ],
        "scope": "Graphical relationships are evidence only; they grant no reachability.",
    }


def create_graph_draft(path: Path, profile: GraphProfile) -> ImportDraft:
    validate_profile(profile)
    if len(set(profile.scopes)) != len(profile.scopes):
        fail("IMPORT_MAPPING", "$", "Select each scope only once.")
    for table in profile.tables:
        expected = {"nodes": "asset", "groups": "zone", "edges": "connection"}
        if expected.get(table.collection) != table.entity:
            fail(
                "IMPORT_MAPPING",
                "$",
                "nodes/assets, groups/zones, edges/evidence-only connections required.",
            )
        for mapping in table.fields.values():
            parts = pointer_parts(mapping.path)
            if parts not in [
                (k,)
                for k in (
                    "id",
                    "scoped_id",
                    "label",
                    "parent",
                    "source",
                    "destination",
                    "direction",
                )
            ] and not (len(parts) == 2 and parts[0] == "attributes"):
                fail("IMPORT_MAPPING", "$", "Unsupported graphical field path.")
    doc = read_graph(path, profile.adapter)
    if not set(profile.scopes) <= {p.scope_id for p in doc.pages}:
        fail("IMPORT_GRAPH_SCOPE", "$", "Selected page/graph ID is absent.")
    tables: dict[str, tuple[ExtractedRow, ...]] = {}
    for table in profile.tables:
        elements: list[GraphNode | GraphEdge] = (
            list(doc.edges)
            if table.collection == "edges"
            else [
                n
                for n in doc.nodes
                if n.kind == ("group" if table.collection == "groups" else "node")
            ]
        )
        rows: list[ExtractedRow] = []
        for element in sorted(elements, key=lambda e: (e.scope_id, e.element_id)):
            if element.scope_id not in profile.scopes:
                continue
            location = StructuredLocation(
                collection=element.scope_id,
                record=element.element_id,
                pointer="/" + table.collection + "/" + pointer_token(element.element_id),
            )
            data: dict[str, InventoryValue] = {
                "id": element.element_id,
                "scoped_id": "g_" + digest([element.scope_id, element.element_id])[:62],
                "label": element.label,
                "parent": element.parent,
                "attributes": doc.attributes[element.scope_id, element.element_id],
            }
            if isinstance(element, GraphEdge):
                data.update(
                    source=element.source,
                    destination=element.destination,
                    direction=element.direction,
                )
            values: dict[str, Value] = {}
            for name, mapping in table.fields.items():
                raw, missing = lookup(data, mapping.path)
                values[name] = Value(
                    raw,
                    location.model_copy(
                        update={"pointer": (location.pointer or "") + mapping.path}
                    ),
                    missing=missing,
                    rule="graph_evidence_only",
                )
            selected = {
                pointer_parts(m.path)[1]
                for m in table.fields.values()
                if pointer_parts(m.path)[0] == "attributes"
            }
            if selected & doc.private_keys:
                fail(
                    "IMPORT_PRIVATE_FIELD", "$", "Sensitive graphical attribute names are excluded."
                )
            omitted = len(set(doc.attributes[element.scope_id, element.element_id]) - selected)
            rows.append(ExtractedRow(location, values, omitted))
        tables[table.name] = tuple(rows)
    return map_extracted(
        doc.source, profile, tables, doc.diagnostics, graph=doc.evidence(profile.scopes)
    )
