"""Read-only, multipage offline Explorer over native declarations and retained evidence."""

import os
import tempfile
import time
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from otarchguard import __version__
from otarchguard.api import ValidatedArchitecture
from otarchguard.diagnostics import check_limit, fail
from otarchguard.diagrams import spatial_svg
from otarchguard.explorer_data import (
    EXPLORER_LIMITS,
    ProjectProvenance,
    load_model,
    load_provenance,
    page_id,
)
from otarchguard.explorer_html import CSS, SiteWriter, escape, link, table
from otarchguard.exposure import exposure_architecture
from otarchguard.ingestion.project import _no_links
from otarchguard.ingestion.reconciliation import catalog
from otarchguard.ingestion.records import StructuredCandidate
from otarchguard.intents import check_architecture
from otarchguard.reporting import diagram_summary
from otarchguard.trace import trace_architecture

NO_ANALYSIS = "No analytical result is available for this question or view."
COLLECTIONS = (
    "zones",
    "assets",
    "interfaces",
    "conduits",
    "transport_edges",
    "forwarding_edges",
    "services",
    "rules",
    "intents",
    "scenarios",
)
FAMILIES = {"zone": "zones", "asset": "assets", "interface": "interfaces"}
REFERENCES = {
    "zone_id": "zones",
    "zone_ids": "zones",
    "placement_zone_id": "zones",
    "asset_id": "assets",
    "asset_ids": "assets",
    "source_asset_id": "assets",
    "destination_asset_id": "assets",
    "origin_asset_ids": "assets",
    "external_asset_ids": "assets",
    "interface_id": "interfaces",
    "source_interface_id": "interfaces",
    "destination_interface_id": "interfaces",
    "ingress_interface_id": "interfaces",
    "egress_interface_id": "interfaces",
    "external_interface_id": "interfaces",
    "internal_interface_id": "interfaces",
    "service_id": "services",
    "destination_service_ids": "services",
    "conduit_id": "conduits",
    "required_intent_ids": "intents",
    "edge_id": "edges",
    "edge_ids": "edges",
    "allow_rule_ids": "rules",
    "deny_rule_ids": "rules",
}


def path(kind: str, identity: object) -> str:
    return page_id(kind, identity) + ".html"


def section(title: str, body: str) -> str:
    return "<section><h2>" + escape(title) + "</h2>" + body + "</section>"


@dataclass(frozen=True, slots=True)
class ExploreOptions:
    traces: tuple[tuple[str, str], ...] = ()
    check: bool = False
    scenarios: tuple[str, ...] = ()


class Explorer:
    def __init__(
        self,
        validated: ValidatedArchitecture,
        provenance: ProjectProvenance | None,
        writer: SiteWriter,
    ) -> None:
        self.validated = validated
        self.model = validated.model
        self.provenance = provenance
        self.writer = writer
        self.native: dict[tuple[str, str], dict[str, Any]] = {}
        self.native_paths: dict[tuple[str, str], str] = {}
        self.support: dict[tuple[str, str], list[str]] = defaultdict(list)
        self.candidate_groups: dict[str, list[str]] = defaultdict(list)
        self.candidate_decision: dict[str, str] = {}
        self.candidate_graph: dict[str, str] = {}
        self.graph_candidates: dict[tuple[str, str, str], list[str]] = defaultdict(list)
        self.graph_edges: dict[tuple[str, str, str], list[str]] = defaultdict(list)
        self.analysis_links: dict[tuple[str, str], list[tuple[str, str]]] = defaultdict(list)
        self.analysis_index: list[tuple[str, str]] = []
        self.services = {s.id: s for s in self.model.services}
        self.assets = {a.id: a for a in self.model.assets}
        self.interface_records = {i.id: i for i in self.model.interfaces}
        self.related: dict[tuple[str, str], set[tuple[str, str]]] = defaultdict(set)
        self.owned: dict[str, list[str]] = defaultdict(list)
        self.placed: dict[str, list[str]] = defaultdict(list)
        self.interfaces: dict[str, list[str]] = defaultdict(list)
        for collection in COLLECTIONS:
            for record in getattr(self.model, collection):
                key = collection, record.id
                self.native[key] = record.model_dump(mode="json")
                self.native_paths[key] = path("native", key)
                if collection in {"transport_edges", "forwarding_edges"}:
                    self.native_paths["edges", record.id] = self.native_paths[key]
        for asset in self.model.assets:
            self.owned[asset.zone_id].append(asset.id)
        for interface in self.model.interfaces:
            self.placed[interface.placement_zone_id].append(interface.id)
            self.interfaces[interface.asset_id].append(interface.id)
        # Index declaration references once; no per-asset scan of all evidence/edges.
        for key, fields in self.native.items():
            self._references(key, fields)
        self.candidates = catalog(provenance.catalog.sources) if provenance else {}
        self.identity = (
            {str(r["candidate_entity_id"]): r for r in provenance.identity_index}
            if provenance
            else {}
        )
        if provenance:
            for candidate_key, (_, candidate) in self.candidates.items():
                row = self.identity[candidate_key]
                if row["model_id"] is not None:
                    self.support[FAMILIES[candidate.entity], str(row["model_id"])].append(
                        candidate_key
                    )
                if isinstance(candidate, StructuredCandidate):
                    location = candidate.location
                    graph_key = (str(row["source_id"]), location.collection, location.record)
                    self.graph_candidates[graph_key].append(candidate_key)
                    self.candidate_graph[candidate_key] = path("node", graph_key)
            for group in (*provenance.catalog.proposals, *provenance.catalog.conflicts):
                for member in group.members:
                    self.candidate_groups[member].append(group.group_id)
            for decision in provenance.decisions.entities:
                target = path("decision", sorted(decision.members))
                for member in decision.members:
                    self.candidate_decision[member] = target
            for source in provenance.catalog.sources:
                graph = source.evidence.graph
                if graph:
                    for edge in graph.edges:
                        target = path("connector", [source.id, edge.scope_id, edge.element_id])
                        for endpoint in (edge.source, edge.destination):
                            if endpoint is not None:
                                self.graph_edges[source.id, edge.scope_id, endpoint].append(target)

    def _references(self, origin: tuple[str, str], value: object, field: str = "") -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                self._references(origin, child, key)
        elif isinstance(value, list):
            for child in value:
                self._references(origin, child, field)
        elif isinstance(value, str) and field in REFERENCES:
            family = REFERENCES[field]
            target = family, value
            if family == "edges":
                family = (
                    "transport_edges"
                    if ("transport_edges", value) in self.native
                    else "forwarding_edges"
                )
                target = family, value
            if target in self.native:
                self.related[target].add(origin)

    def value(self, value: object, field: str = "") -> str:
        if isinstance(value, dict):
            return (
                "<dl>"
                + "".join(
                    f"<dt>{escape(k)}</dt><dd>{self.value(v, k)}</dd>"
                    for k, v in sorted(value.items())
                )
                + "</dl>"
            )
        if isinstance(value, (tuple, list)):
            return "<ul>" + "".join(f"<li>{self.value(v, field)}</li>" for v in value) + "</ul>"
        target = self.native_paths.get((REFERENCES.get(field, ""), str(value)))
        return link(target, value) if target else escape("Not declared" if value is None else value)

    def listings(self, title: str, entries: list[tuple[str, str]], stem: str) -> str:
        """Paginate every unbounded collection, including reverse evidence references."""
        entries = sorted(set(entries), key=lambda row: (row[1], row[0]))
        count = max(
            1, (len(entries) + EXPLORER_LIMITS.index_rows - 1) // EXPLORER_LIMITS.index_rows
        )
        names = [stem + ("" if i == 0 else f"-{i + 1}") + ".html" for i in range(count)]
        for i, name in enumerate(names):
            navigation = (
                "<p>"
                + (link(names[i - 1], "Previous page") + " · " if i else "")
                + f"Page {i + 1} of {count}; {len(entries)} records"
                + (" · " + link(names[i + 1], "Next page") if i + 1 < count else "")
                + "</p>"
            )
            rows = [
                (link(p, label),)
                for p, label in entries[
                    i * EXPLORER_LIMITS.index_rows : (i + 1) * EXPLORER_LIMITS.index_rows
                ]
            ]
            self.writer.page(name, title, navigation + table(title, ("Record",), rows))
        return link(names[0], f"{title} ({len(entries)})")

    def references(self, title: str, entries: list[tuple[str, str]], identity: object) -> str:
        if len(entries) > EXPLORER_LIMITS.index_rows:
            return "<p>" + self.listings(title, entries, page_id("list", identity)) + "</p>"
        return table(title, ("Record",), [(link(p, label),) for p, label in sorted(set(entries))])

    def native_link(self, collection: str, identity: str) -> str:
        return link(self.native_paths[collection, identity], identity)

    def render_native(self) -> None:
        for key, fields in sorted(self.native.items()):
            collection, identity = key
            body = '<p class="notice">Owner-confirmed architecture · Declared only.</p>'
            body += section("Native declaration", self.value(fields))
            if collection == "zones":
                members = self.owned[identity]
                visible = members[: EXPLORER_LIMITS.diagram_nodes]
                body += (
                    '<ul class="cards">'
                    + "".join(
                        '<li data-native-asset-id="'
                        + escape(member)
                        + '">'
                        + self.native_link("assets", member)
                        + "<br>"
                        + escape(self.assets[member].name)
                        + "</li>"
                        for member in visible
                    )
                    + "</ul>"
                )
                body += (
                    f"<p>Zone cards: {len(visible)} of {len(members)} assets; "
                    f"{len(members) - len(visible)} omitted from this visual view. "
                    "Complete membership follows. Card proximity implies no connectivity.</p>"
                )
                body += section(
                    "Confirmed administrative members",
                    self.references(
                        "Assets owned by this zone",
                        [(self.native_paths["assets", a], a) for a in self.owned[identity]],
                        [key, "assets"],
                    ),
                )
                body += section(
                    "Interface placements",
                    self.references(
                        "Interfaces placed in this zone",
                        [(self.native_paths["interfaces", a], a) for a in self.placed[identity]],
                        [key, "interfaces"],
                    ),
                )
            if collection == "assets":
                body += section(
                    "Owned interfaces",
                    self.references(
                        "Interfaces owned by this asset",
                        [
                            (self.native_paths["interfaces", a], a)
                            for a in self.interfaces[identity]
                        ],
                        [key, "interfaces"],
                    ),
                )
            relations = sorted(self.related[key])
            # Include local interface relationships on zone and asset pages.
            interface_ids = (
                self.placed[identity]
                if collection == "zones"
                else self.interfaces[identity]
                if collection == "assets"
                else []
            )
            for interface_id in interface_ids:
                relations.extend(self.related["interfaces", interface_id])
            relations = sorted(set(relations))
            body += section(
                "Related native declarations",
                self.references(
                    "Explicit relationships, listeners and policy context",
                    [(self.native_paths[k], f"{k[0]} · {k[1]}") for k in relations],
                    [key, "related"],
                ),
            )
            edges = [k for k in relations if k[0] in {"transport_edges", "forwarding_edges"}]
            if edges:
                body += self.native_diagram(edges)
            members = self.support[key]
            body += section(
                "Supporting origins and contradictory observations",
                self.references(
                    "Source-qualified candidate observations",
                    [(path("candidate", m), m) for m in members],
                    [key, "evidence"],
                )
                if self.provenance
                else "<p>Source provenance unavailable: model-only Explorer.</p>",
            )
            body += self.analyses_for(key)
            self.writer.page(self.native_paths[key], f"{collection} · {identity}", body)

    def diagram(self, rows: list[tuple[str, str, str]], trust: str, title: str) -> str:
        limit = EXPLORER_LIMITS.diagram_edges
        visible: list[tuple[str, str, str]] = []
        endpoints: set[str] = set()
        for row in rows:
            planned = endpoints | {row[0], row[1]}
            if len(visible) >= limit or len(planned) > EXPLORER_LIMITS.diagram_nodes:
                break
            endpoints = planned
            visible.append(row)
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="900" '
            f'height="{70 * len(visible) + 40}" '
            f'viewBox="0 0 900 {70 * len(visible) + 40}" role="img" aria-label="{escape(title)}">'
            f"<title>{escape(title)}</title><desc>Each row is one explicit relationship. "
            "Line proximity creates no junction or permission. Full records follow in text.</desc>"
        )
        for i, (left, right, label) in enumerate(visible):
            y = 35 + i * 70
            svg += (
                f'<path class="diagram-line {trust}" d="M20 {y + 10} H870"/>'
                f'<text data-endpoint="source" x="20" y="{y}" '
                f'fill="#172d3e">{escape(left[:44])}</text>'
                f'<text data-endpoint="destination" x="465" y="{y}" '
                f'fill="#172d3e">{escape(right[:44])}</text>'
                f'<text x="20" y="{y + 35}" fill="#172d3e">{escape(label[:105])}</text>'
            )
        svg += "</svg>"
        return (
            (
                '<figure><div class="scroll" tabindex="0" role="region" aria-'
                'label="Relationship diagram">'
            )
            + svg
            + "</div><figcaption>"
            + escape(title)
            + f". Showing {len(visible)} of {len(rows)} relationships; "
            + f"{len(rows) - len(visible)} excluded from this diagram. "
            "Complete linked records remain in the textual list.</figcaption></figure>"
        )

    def native_diagram(self, edges: list[tuple[str, str]]) -> str:
        rows = []
        for key in edges:
            fields = self.native[key]
            a = fields.get("source_interface_id", fields.get("ingress_interface_id"))
            b = fields.get("destination_interface_id", fields.get("egress_interface_id"))
            rows.append(
                (
                    str(a),
                    str(b),
                    f"{key[1]} · {key[0]} · declared direction left to right; "
                    "no permission assertion",
                )
            )
        return self.diagram(rows, "declared", "Owner-declared transitions")

    def analyses_for(self, key: tuple[str, str]) -> str:
        return section(
            "Analytical results",
            self.references(
                "Exact results involving this entity",
                self.analysis_links[key],
                [key, "analysis"],
            )
            if self.analysis_links[key]
            else "<p>Not evaluated. " + NO_ANALYSIS + "</p>",
        )

    def render_analysis(self, options: ExploreOptions) -> None:
        check_limit(
            "explorer_analyses",
            len(options.traces) + len(options.scenarios) + int(options.check),
            EXPLORER_LIMITS.analyses,
        )
        # Explicit query regeneration is the only analysis input contract in version 1.
        for source, service in sorted(set(options.traces)):
            result = trace_architecture(self.validated, source, service)
            payload = asdict(result)
            name = path("analysis", ["trace", source, service])
            self.query_page(
                name, f"Exact trace · {source} → {service}", payload, [payload["scope"]]
            )
        if options.check:
            result_check = check_architecture(self.validated)
            name = path("analysis", "check")
            self.analysis_index.append((name, "Communication intent check"))
            rows = []
            for intent in result_check.intents:
                query_links = []
                for query in intent.queries:
                    target = path(
                        "analysis", ["check", intent.id, query.source_asset_id, query.service_id]
                    )
                    self.query_page(
                        target,
                        f"Intent {intent.id} · {query.source_asset_id} → {query.service_id}",
                        asdict(query),
                        [asdict(query)],
                    )
                    query_links.append((target, f"{query.source_asset_id} → {query.service_id}"))
                rows.append(
                    (
                        self.native_link("intents", intent.id),
                        escape(intent.kind),
                        escape("passed" if intent.passed else "failed"),
                        self.references("Evaluated queries", query_links, ["intent", intent.id]),
                    )
                )
            body = (
                "<p>Existing intent engine; finite declared initiation scope."
                " Empty intents establish no global security conclusion.</p>"
            )
            body += table(
                "Independent intent outcomes", ("Intent", "Kind", "Result", "Exact queries"), rows
            )
            if not rows:
                body += (
                    "<p>No intents were declared; no source/service queries evaluated. "
                    + NO_ANALYSIS
                    + "</p>"
                )
            body += self.value({k: v for k, v in asdict(result_check).items() if k != "intents"})
            self.writer.page(name, "Communication intent check", body)
        for scenario in sorted(set(options.scenarios)):
            exposure = exposure_architecture(self.validated, scenario)
            name = path("analysis", ["exposure", scenario])
            self.analysis_index.append((name, f"Exposure scenario · {scenario}"))
            queries = []
            for query in exposure.queries:
                target = path(
                    "analysis", ["exposure", scenario, query.source_asset_id, query.service_id]
                )
                self.query_page(
                    target,
                    f"Scenario {scenario} · {query.source_asset_id} → {query.service_id}",
                    asdict(query),
                    [asdict(query)],
                )
                queries.append((target, f"{query.source_asset_id} → {query.service_id}"))
            body = (
                "<p>Existing exposure engine; origin assumptions, not comprom"
                "ise or live traffic observations.</p>"
            )
            body += self.value(
                {k: v for k, v in asdict(exposure).items() if k not in {"queries", "intent_checks"}}
            )
            body += self.references("Evaluated scenario queries", queries, ["exposure", scenario])
            # Preserve independent intent outcomes from the existing exposure engine.
            body += section(
                "Independent intent outcomes", self.value(asdict(exposure.intent_checks))
            )
            self.writer.page(name, f"Exposure scenario · {scenario}", body)

    def query_page(
        self, name: str, title: str, payload: dict[str, Any], scopes: list[dict[str, Any]]
    ) -> None:
        self.analysis_index.append((name, title))
        for scope in scopes:
            service = self.services[scope["service_id"]]
            involved = {
                ("assets", scope["source_asset_id"]),
                ("assets", service.asset_id),
                ("interfaces", service.interface_id),
                ("services", service.id),
            }
            for interval in payload["intervals"]:
                if interval["witness"]:
                    for step in interval["witness"]["steps"]:
                        involved.add(("edges", step["edge_id"]))
                        for endpoint in (step["source"], step["target"]):
                            involved.add(("assets", endpoint["asset_id"]))
                            involved.add(("interfaces", endpoint["state"]["interface_id"]))
                            involved.add(("zones", endpoint["placement_zone_id"]))
            for collection, identity in tuple(involved):
                if collection == "assets":
                    involved.add(("zones", self.assets[identity].zone_id))
                elif collection == "interfaces":
                    involved.add(("zones", self.interface_records[identity].placement_zone_id))
            for key in sorted(involved):
                if key[0] == "edges":
                    key = (
                        "transport_edges"
                        if ("transport_edges", key[1]) in self.native
                        else "forwarding_edges",
                        key[1],
                    )
                self.analysis_links[key].append((name, title))
        body = (
            '<p class="notice">Analytical result · Regenerated by the exi'
            "sting exact engine for this model.</p>"
        )
        body += (
            "<p>Direction is original source to service-bound destination"
            ". Other pairs and ports are not evaluated. "
        )
        body += (
            "A negative interval applies only to this query under the dec"
            "lared model. No deployed connectivity, return traffic, risk "
            "or conformity is established.</p>"
        )
        body += self.value(
            {"model_sha256": self.validated.sha256, "engine_version": __version__, "query": payload}
        )
        witness_rows = []
        for interval in payload["intervals"]:
            if interval["witness"]:
                for step in interval["witness"]["steps"]:
                    witness_rows.append(
                        (
                            step["source"]["state"]["interface_id"],
                            step["target"]["state"]["interface_id"],
                            f"{step['edge_id']} · evaluated {interval['start']}–{interval['end']}",
                        )
                    )
            if interval["reachable"]:
                body += (
                    "<p>Allowed under the declared model for evaluated ports "
                    f"{interval['start']}–{interval['end']}.</p>"
                )
            else:
                body += (
                    "<p>No authorized path for evaluated ports "
                    f"{interval['start']}–{interval['end']}: "
                    f"{escape(interval['diagnostics']['reason'])}.</p>"
                )
        if witness_rows:
            body += self.diagram(witness_rows, "analytical", "Exact analytical witness steps")
        self.writer.page(name, title, body)

    def render_evidence(self) -> None:
        p = self.provenance
        if p is None:
            self.writer.page(
                "evidence.html",
                "Source evidence unavailable",
                (
                    "<p>Model-only Explorer. No provenance sidecar was supplied; "
                    "origins, conflicts and owner review history are unavailable."
                    "</p>"
                ),
            )
            return
        conflict_resolutions = {r.group_id: r for r in p.decisions.conflicts}
        for group in (*p.catalog.proposals, *p.catalog.conflicts):
            body = "<p>Documentary reconciliation proposal; never an automatic native identity.</p>"
            body += self.value(
                {k: v for k, v in group.model_dump(mode="json").items() if k != "members"}
            )
            body += self.references(
                "Group members",
                [(path("candidate", m), m) for m in group.members],
                ["group", group.group_id],
            )
            resolution = conflict_resolutions.get(group.group_id)
            if resolution:
                body += section(
                    "Owner conflict resolution", self.value(resolution.model_dump(mode="json"))
                )
            self.writer.page(
                path("group", group.group_id), f"Reconciliation group · {group.group_id}", body
            )
        for decision in p.decisions.entities:
            name = path("decision", sorted(decision.members))
            body = self.value(
                {k: v for k, v in decision.model_dump(mode="json").items() if k != "members"}
            )
            body += self.references(
                "Partition members and original aliases",
                [(path("candidate", m), m) for m in decision.members],
                ["decision", sorted(decision.members)],
            )
            first = decision.members[0]
            row = self.identity[first]
            if row["model_id"]:
                body += (
                    "<p>Authoritative entity: "
                    + self.native_link(
                        FAMILIES[self.candidates[first][1].entity], str(row["model_id"])
                    )
                    + "</p>"
                )
            self.writer.page(
                name, f"Owner decision · {decision.canonical_id or decision.decision}", body
            )
        for candidate_key, (source_id, candidate) in self.candidates.items():
            row = self.identity[candidate_key]
            body = (
                "<p>Documentary evidence · Candidate values are observations,"
                " including rejected alternatives.</p>"
            )
            body += (
                "<p>Source: "
                + link(path("source", source_id), source_id)
                + "; qualified candidate: <code>"
                + escape(candidate_key)
                + "</code></p>"
            )
            body += (
                '<section id="observation"><h2>Source observation</h2><p><code>'
                + escape(row["observation_id"])
                + "</code></p>"
            )
            rows = []
            for field in candidate.fields:
                raw = field.raw_value
                if isinstance(raw, (dict, list)):
                    raw = "[non-scalar selected value; inspect required correction]"
                rows.append(
                    (
                        escape(field.field),
                        self.value(raw),
                        escape(field.normalized_value),
                        escape(field.state),
                        escape(field.transformation),
                        self.value(
                            field.location.model_dump(mode="json") if field.location else None
                        ),
                    )
                )
            body += (
                table(
                    "Selected field provenance",
                    (
                        "Field",
                        "Original value",
                        "Normalized observation",
                        "Evidence state",
                        "Transformation",
                        "Source location",
                    ),
                    rows,
                )
                + "</section>"
            )
            body += self.value(
                {
                    "review_status": row["review_status"],
                    "original_proposed_id": row["proposed_canonical_identity"],
                    "ambiguities": candidate.ambiguities,
                }
            )
            if candidate_key in self.candidate_decision:
                body += (
                    "<p>"
                    + link(
                        self.candidate_decision[candidate_key],
                        "Owner partition, corrections and rationale",
                    )
                    + "</p>"
                )
            if row["model_id"]:
                body += (
                    "<p>Accepted native entity: "
                    + self.native_link(FAMILIES[candidate.entity], str(row["model_id"]))
                    + "</p>"
                )
            else:
                body += "<p>No native entity accepted from this candidate.</p>"
            body += self.references(
                "Reconciliation and conflict groups",
                [(path("group", g), g) for g in self.candidate_groups[candidate_key]],
                ["candidate", candidate_key],
            )
            if isinstance(candidate, StructuredCandidate):
                graph_key = (source_id, candidate.location.collection, candidate.location.record)
                if self._has_node(graph_key):
                    body += (
                        "<p>"
                        + link(
                            path("node", graph_key),
                            "Original graphical node and documentary connectors",
                        )
                        + "</p>"
                    )
            self.writer.page(path("candidate", candidate_key), f"Candidate · {candidate_key}", body)
        source_entries = []
        for source in p.catalog.sources:
            name = path("source", source.id)
            source_entries.append((name, source.id))
            document = source.evidence.source
            body = self.value(
                {
                    "source_id": source.id,
                    "document_identifier": document.source_id,
                    "format": document.format,
                    "source_sha256": document.sha256,
                }
            )
            body += (
                "<p>Only selected fields and graphical observations are proje"
                "cted. Original files, unmapped metadata, source paths, geome"
                "try and styles are excluded.</p>"
            )
            entries = [
                (path("candidate", key) + "#observation", key)
                for key, (sid, _) in self.candidates.items()
                if sid == source.id
            ]
            body += self.references(
                "Mapped observations and candidates", entries, ["source", source.id, "candidates"]
            )
            graph = source.evidence.graph
            if graph:
                nodes = []
                connectors = []
                for node in graph.nodes:
                    node_key = (source.id, node.scope_id, node.element_id)
                    target = path("node", node_key)
                    nodes.append((target, f"{node.scope_id} · {node.element_id} · {node.label}"))
                    node_body = self.value(
                        {
                            "source": source.id,
                            "scope": node.scope_id,
                            "element": node.element_id,
                            "label": node.label,
                            "kind": node.kind,
                            "parent": node.parent,
                        }
                    )
                    node_body += (
                        "<p>Graphical containment is documentary; it establishes no c"
                        "onfirmed security-zone membership.</p>"
                    )
                    node_body += self.references(
                        "Mapped node candidates",
                        [(path("candidate", c), c) for c in self.graph_candidates[node_key]],
                        ["node", node_key, "candidates"],
                    )
                    node_body += self.references(
                        "Documented only connectors",
                        [
                            (c, "Documentary connector " + c.removesuffix(".html"))
                            for c in self.graph_edges[node_key]
                        ],
                        ["node", node_key, "edges"],
                    )
                    self.writer.page(
                        target,
                        f"Graphical {node.kind} · {node.element_id}",
                        link(name, "Supporting source") + node_body,
                    )
                for edge in graph.edges:
                    edge_key = [source.id, edge.scope_id, edge.element_id]
                    target = path("connector", edge_key)
                    connectors.append((target, f"{edge.element_id} · {edge.label}"))
                    edge_body = (
                        "<p>Documented only. No corresponding native edge is inferred"
                        "; communication is unknown from this evidence.</p>"
                    )
                    edge_body += link(name, "Supporting source") + self.value(
                        edge.model_dump(mode="json")
                    )
                    for endpoint in (edge.source, edge.destination):
                        graph_key = (source.id, edge.scope_id, str(endpoint))
                        if self._has_node(graph_key):
                            edge_body += (
                                "<p>"
                                + link(path("node", graph_key), f"Documentary endpoint {endpoint}")
                                + "</p>"
                            )
                    edge_body += self.diagram(
                        [
                            (
                                edge.source or "Unresolved",
                                edge.destination or "Unresolved",
                                "Documented only · graph direction: " + edge.direction,
                            )
                        ],
                        "documentary",
                        "Documentary connector; direction is graphical evidence",
                    )
                    self.writer.page(target, f"Documented only · {edge.element_id}", edge_body)
                body += self.references(
                    "Graphical nodes and containers", nodes, [source.id, "nodes"]
                )
                body += self.references("Documentary connectors", connectors, [source.id, "edges"])
            acknowledgment = next(
                (a for a in p.decisions.acknowledgments if a.source_id == source.id), None
            )
            if acknowledgment:
                body += section(
                    "Owner evidence acknowledgment",
                    self.value(
                        {
                            "member_count": len(acknowledgment.members),
                            "set_sha256": acknowledgment.set_sha256,
                            "rationale": acknowledgment.rationale,
                        }
                    ),
                )
            self.writer.page(name, f"Source · {source.id}", body)
        self.listings("Source evidence", source_entries, "evidence")

    def _has_node(self, key: tuple[str, str, str]) -> bool:
        return key in self.node_keys

    @property
    def node_keys(self) -> set[tuple[str, str, str]]:
        # Cached once by render(), not rescanned per candidate.
        return self._node_keys

    def render(self, options: ExploreOptions) -> dict[str, object]:
        self._node_keys = (
            {
                (s.id, n.scope_id, n.element_id)
                for s in self.provenance.catalog.sources
                if s.evidence.graph
                for n in s.evidence.graph.nodes
            }
            if self.provenance
            else set()
        )
        self.writer.write("assets.css", CSS.encode("utf-8"))
        self.render_analysis(options)
        self.render_native()
        self.render_evidence()
        for family in ("zones", "assets", "interfaces"):
            self.listings(
                family.capitalize(),
                [
                    (p, f"{identity} · {self.native[family, identity].get('name', '')}")
                    for (collection, identity), p in self.native_paths.items()
                    if collection == family
                ],
                family,
            )
        self.listings(
            "Native declarations",
            [
                (self.native_paths[k], f"{k[0]} · {k[1]}")
                for k in self.native
                if k[0] not in {"zones", "assets", "interfaces"}
            ],
            "declarations",
        )
        if self.analysis_index:
            self.listings("Analytical results", self.analysis_index, "analysis")
        else:
            self.writer.page(
                "analysis.html",
                "Analytical results · Not evaluated",
                "<p>Not evaluated. " + NO_ANALYSIS + "</p>",
            )
        summary = diagram_summary(self.validated)
        svg = spatial_svg(
            self.validated, summary["mode"] == "summary", escape, namespace="overview"
        )
        # In Explorer, dashed relationship lines are reserved for documentary evidence.
        # Keep the accepted layout/geometry while rendering native forwarding solid.
        svg = svg.replace(' stroke-dasharray="8 4"', "")
        body = (
            "<p>"
            + escape(self.model.suc.name)
            + " · Revision "
            + escape(self.model.revision)
            + "</p>"
        )
        body += (
            "<p>Deterministic generation; Explorer contract 1; OT-ArchGuard "
            + escape(__version__)
            + ".</p>"
        )
        body += (
            '<ul class="cards">'
            + "".join(
                f"<li>{len(getattr(self.model, c))} {link(c + '.html', c)}</li>"
                for c in ("zones", "assets", "interfaces")
            )
            + "</ul>"
        )
        body += section(
            "Owner-declared relationships",
            self.value(
                {
                    "transport_edges": len(self.model.transport_edges),
                    "forwarding_edges": len(self.model.forwarding_edges),
                    "services": len(self.model.services),
                    "rules": len(self.model.rules),
                }
            )
            + "<p>"
            + link("declarations.html", "Inspect exact native declarations")
            + "</p>",
        )
        if self.provenance:
            p = self.provenance
            body += self.value(
                {
                    "sources": len(p.catalog.sources),
                    "reconciled_identities": sum(
                        len(d.members) > 1 and d.decision == "OWNER_CONFIRMED"
                        for d in p.decisions.entities
                    ),
                    "retained_documentary_conflicts": len(p.catalog.conflicts),
                    "unresolved_conflicts": sum(not c.resolved for c in p.decisions.conflicts),
                    "evidence_only_connectors": sum(
                        len(s.evidence.graph.edges) for s in p.catalog.sources if s.evidence.graph
                    ),
                }
            )
        else:
            body += (
                '<p class="notice">Model-only Explorer: source provenance una'
                "vailable. No origins or owner review history are fabricated."
                "</p>"
            )
        body += (
            "<p>"
            + link("analysis.html", f"Available analytical views ({len(set(self.analysis_index))})")
            + "</p>"
        )
        if not self.analysis_index:
            body += "<p>Not evaluated. " + NO_ANALYSIS + "</p>"
        body += section(
            "Bounded declared architecture overview",
            (
                '<figure><div class="scroll" tabindex="0" role="region" aria-'
                'label="Architecture schematic">'
            )
            + svg
            + "</div><figcaption>"
            + escape(summary["legend"])
            + "</figcaption></figure>",
        )
        body += (
            "<p>Diagram mode: "
            + escape(summary["mode"])
            + (
                ". Summary omits device/interface/edge detail; complete decla"
                "rations remain in linked indexes.</p>"
            )
        )
        if summary["mode"] == "summary":
            omitted = {key: len(value) for key, value in summary["omitted_from_diagram"].items()}
            body += self.value({"diagram_omission_counts": omitted})
        body += section(
            "Owner-declared system scope and limitations",
            self.value(self.model.suc.model_dump(mode="json")),
        )
        self.writer.page("index.html", self.model.architecture_id, body)
        return self.writer.finish(
            {
                "engine_version": __version__,
                "provenance_contract": "project-1" if self.provenance else "unavailable",
                "draft_sha256": self.provenance.draft_sha256 if self.provenance else None,
                "privacy": "local full-detail; selected evidence; local paths withheld",
                "diagram_mode": summary["mode"],
                "limits": asdict(EXPLORER_LIMITS),
            }
        )


def generate_explorer(
    architecture: Path,
    output: Path,
    *,
    provenance: Path | None = None,
    options: ExploreOptions | None = None,
) -> dict[str, object]:
    """Validate once, stage bounded files, audit the actual site, publish without overwrite.

    Timings are completion metadata only, excluded from deterministic site bytes.
    Local single-writer publication follows the ingestion bundle convention.
    """
    started = time.perf_counter()
    _no_links(output)
    if output.exists():
        fail("EXPLORER_OUTPUT", "$", "Output already exists; choose a fresh directory.")
    validated = load_model(architecture)
    sidecar = load_provenance(provenance, validated) if provenance else None
    loaded = time.perf_counter()
    try:
        with tempfile.TemporaryDirectory(
            dir=output.absolute().parent, prefix=".otarchguard-explorer-"
        ) as name:
            stage = Path(name)
            explorer = Explorer(validated, sidecar, SiteWriter(stage, validated.sha256))
            indexed = time.perf_counter()
            result = explorer.render(options or ExploreOptions())
            if output.exists() or output.is_symlink():
                fail("EXPLORER_OUTPUT", "$", "Output already exists; publication refused.")
            os.rename(stage, output)
    except OSError:
        fail("EXPLORER_OUTPUT", "$", "Cannot publish the complete local Explorer.")
    return {
        "status": "complete",
        "model_sha256": validated.sha256,
        "site": {k: v for k, v in result.items() if k != "files"},
        "timings_seconds": {
            "input_validation": loaded - started,
            "index_creation": indexed - loaded,
            "render_and_audit": time.perf_counter() - indexed,
            "total": time.perf_counter() - started,
        },
    }
