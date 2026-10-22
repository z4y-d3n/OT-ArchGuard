"""Bounded presentation geometry; never builds or changes the analytical graph."""

import heapq
import re
from collections.abc import Callable
from dataclasses import dataclass
from textwrap import wrap
from typing import Literal

from otarchguard.api import ValidatedArchitecture
from otarchguard.diagnostics import fail

INTERPRETATION = (
    "Arrows represent declared transitions, not necessarily permitted communication "
    "or verified physical connectivity."
)
type Phase = Literal["ingress", "egress"]
type Kind = Literal["transport", "forwarding"]


@dataclass(frozen=True, slots=True)
class Point:
    x: int
    y: int


@dataclass(frozen=True, slots=True)
class Rect:
    x: int
    y: int
    width: int
    height: int

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height


@dataclass(frozen=True, slots=True)
class Label:
    bounds: Rect
    full_text: str
    visible_text: str
    size: int = 13


@dataclass(frozen=True, slots=True)
class Anchor:
    interface_id: str
    phase: Phase
    point: Point


@dataclass(frozen=True, slots=True)
class InterfaceRow:
    interface_id: str
    bounds: Rect
    labels: tuple[Label, ...]
    ingress: Anchor
    egress: Anchor


@dataclass(frozen=True, slots=True)
class Attachment:
    asset_id: str
    owner_zone_id: str
    placement_zone_id: str
    boundary: bool
    bounds: Rect
    labels: tuple[Label, ...]
    interfaces: tuple[InterfaceRow, ...]


@dataclass(frozen=True, slots=True)
class ZoneBox:
    zone_id: str
    scope: str
    bounds: Rect
    labels: tuple[Label, ...]


@dataclass(frozen=True, slots=True)
class Transition:
    edge_id: str
    kind: Kind
    source: Anchor
    target: Anchor
    conduit_id: str | None
    points: tuple[Point, ...]
    label: Label
    key: Label


@dataclass(frozen=True, slots=True)
class DevicePlacement:
    asset_id: str
    owner_zone_id: str
    placement_zone_id: str
    interface_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Omissions:
    zone_ids: tuple[str, ...]
    asset_ids: tuple[str, ...]
    interface_ids: tuple[str, ...]
    edge_ids: tuple[str, ...]
    attachment_cards: int


@dataclass(frozen=True, slots=True)
class Layout:
    bounds: Rect
    mode: str
    requested_order: tuple[str, ...]
    effective_order: tuple[str, ...]
    zones: tuple[ZoneBox, ...]
    attachments: tuple[Attachment, ...]
    transitions: tuple[Transition, ...]
    device_map: tuple[DevicePlacement, ...]
    labels: tuple[Label, ...]
    omissions: Omissions
    limitations: tuple[str, ...]


def validate_zone_order(
    snapshots: tuple[ValidatedArchitecture, ...], requested: tuple[str, ...]
) -> None:
    """Comparison preferences use the union, with existing controlled diagnostics."""
    if len(set(requested)) != len(requested):
        fail("INVALID_VALUE", "$.zone_order", "Duplicate presentation zone IDs are not allowed.")
    known = {z.id for s in snapshots for z in s.model.zones}
    if any(identity not in known for identity in requested):
        fail("INVALID_REFERENCE", "$.zone_order", "Unknown presentation zone ID.")


def zone_order(snapshot: ValidatedArchitecture, requested: tuple[str, ...] = ()) -> tuple[str, ...]:
    """Kahn order; minimum stable ID breaks cycles and ties, including components.

    Only explicit cross-placement transitions affect this heuristic. Breaking a
    cycle is a drawing choice, never a declaration of reachability or trust.
    """
    model = snapshot.model
    adjacency: dict[str, set[str]] = {z.id: set() for z in model.zones}
    interfaces = {i.id: i.placement_zone_id for i in model.interfaces}
    pairs = [(e.source_interface_id, e.destination_interface_id) for e in model.transport_edges]
    pairs += [(e.ingress_interface_id, e.egress_interface_id) for e in model.forwarding_edges]
    for source, target in pairs:
        a, b = interfaces[source], interfaces[target]
        if a != b:
            adjacency[a].add(b)
    indegree = dict.fromkeys(adjacency, 0)
    for targets in adjacency.values():
        for target in targets:
            indegree[target] += 1
    remaining = set(adjacency)
    all_ids = sorted(remaining)
    heapq.heapify(all_ids)
    ready = sorted(z for z, degree in indegree.items() if degree == 0)
    heapq.heapify(ready)
    ordered: list[str] = []
    while remaining:
        identity = heapq.heappop(ready if ready else all_ids)
        if identity not in remaining:
            continue
        remaining.remove(identity)
        ordered.append(identity)
        for target in sorted(adjacency[identity]):
            indegree[target] -= 1
            if indegree[target] == 0 and target in remaining:
                heapq.heappush(ready, target)
    return tuple(z for z in requested if z in adjacency) + tuple(
        z for z in ordered if z not in requested
    )


def _label(x: int, y: int, width: int, value: str, size: int = 13) -> Label:
    # A conservative code-point budget, NOT measured glyph widths. No runtime
    # Unicode database: Python versions can classify the same scalar differently.
    # Clipping enforces the finite region with platform-dependent fallback fonts.
    budget = max(1, width // size)
    clean = " ".join(value.split())
    visible = clean if len(clean) <= budget else clean[: budget - 1] + "…"
    return Label(Rect(x, y, width, size + 8), value, visible, size)


def calculate_layout(
    snapshot: ValidatedArchitecture, summarized: bool, requested: tuple[str, ...] = ()
) -> Layout:
    """Calculate placement, anchors, routes, labels and bounds before serialization.

    Detailed routing is limited to the existing <=12/24/24/48 envelope. Each
    transition has separate vertical side tracks and a horizontal shelf below
    all cards in its zone interval. First-fit shelves conflict only when their
    spans overlap. There is no search through the analytical graph.
    """
    model = snapshot.model
    order = zone_order(snapshot, requested)
    visible_ids = {z.id for z in model.zones[:12]}
    visible = [z for z in order if z in visible_ids]
    zone_models = {z.id: z for z in model.zones}
    assets = {a.id: a for a in model.assets}
    interfaces = {i.id: i for i in model.interfaces}
    placements: dict[tuple[str, str], list[str]] = {}
    for interface in model.interfaces:
        placements.setdefault((interface.placement_zone_id, interface.asset_id), []).append(
            interface.id
        )
    for asset in model.assets:
        placements.setdefault((asset.zone_id, asset.id), [])
    devices = tuple(
        DevicePlacement(asset_id, assets[asset_id].zone_id, zone, tuple(sorted(ids)))
        for (zone, asset_id), ids in sorted(placements.items())
    )
    declared: list[tuple[str, Kind, str, str, str | None]] = (
        sorted(
            [
                (e.id, "transport", e.source_interface_id, e.destination_interface_id, e.conduit_id)
                for e in model.transport_edges
            ]
            + [
                (e.id, "forwarding", e.ingress_interface_id, e.egress_interface_id, e.conduit_id)
                for e in model.forwarding_edges
            ]
        )
        if not summarized
        else []
    )
    sides: dict[tuple[str, Phase], int] = {}
    for _, kind, source, target, _ in declared:
        phases: tuple[Phase, Phase] = (
            ("egress", "ingress") if kind == "transport" else ("ingress", "egress")
        )
        for identity, phase in zip((source, target), phases, strict=True):
            key = (interfaces[identity].placement_zone_id, phase)
            sides[key] = sides.get(key, 0) + 1
    zones: list[ZoneBox] = []
    cards: list[Attachment] = []
    anchors: dict[tuple[str, Phase], Anchor] = {}
    content_bottom: dict[str, int] = {}
    card_x: dict[str, int] = {}
    x = 40
    for identity in visible:
        zone = zone_models[identity]
        left = 40 + 8 * sides.get((identity, "ingress"), 0)
        right = 40 + 8 * sides.get((identity, "egress"), 0)
        zw = left + 280 + right
        card_x[identity] = x + left
        y = 242
        if not summarized:
            for placement in devices:
                if placement.placement_zone_id != identity:
                    continue
                asset = assets[placement.asset_id]
                cx = card_x[identity]
                height = 124 + max(1, len(placement.interface_ids)) * 48
                rows: list[InterfaceRow] = []
                for index, iid in enumerate(placement.interface_ids):
                    ry = y + 122 + index * 48
                    ingress = Anchor(iid, "ingress", Point(cx, ry + 16))
                    egress = Anchor(iid, "egress", Point(cx + 280, ry + 16))
                    anchors[iid, "ingress"], anchors[iid, "egress"] = ingress, egress
                    rows.append(
                        InterfaceRow(
                            iid,
                            Rect(cx + 10, ry, 260, 44),
                            (
                                _label(cx + 18, ry, 244, iid),
                                _label(cx + 18, ry + 21, 244, interfaces[iid].ipv4, 11),
                            ),
                            ingress,
                            egress,
                        )
                    )
                labels = [
                    _label(cx + 14, y + 12, 252, asset.name, 15),
                    _label(cx + 14, y + 39, 252, asset.id),
                    _label(cx + 14, y + 63, 252, f"Owner: {asset.zone_id}", 12),
                    _label(
                        cx + 14,
                        y + 87,
                        252,
                        "Same boundary asset" if asset.kind == "boundary_device" else "Endpoint",
                        11,
                    ),
                ]
                if not rows:
                    labels.append(_label(cx + 14, y + 128, 252, "No interface placed here", 12))
                cards.append(
                    Attachment(
                        asset.id,
                        asset.zone_id,
                        identity,
                        asset.kind == "boundary_device",
                        Rect(cx, y, 280, height),
                        tuple(labels),
                        tuple(rows),
                    )
                )
                y += height + 24
        content_bottom[identity] = y
        zones.append(
            ZoneBox(
                identity,
                zone.scope,
                Rect(x, 158, zw, y - 158 + 32),
                (
                    _label(x + 16, 172, zw - 32, zone.name, 16),
                    _label(x + 16, 205, zw - 32, f"{identity} · {zone.scope.upper()}", 12),
                ),
            )
        )
        x += zw + 36
    width = max(1100, x + 4)
    tracks: dict[tuple[str, Phase], int] = {}
    shelves: list[tuple[int, int, int]] = []
    routes: list[tuple[tuple[str, Kind, str, str, str | None], tuple[Point, ...], Label]] = []
    for number, edge in enumerate(declared, 1):
        _, kind, source, target, _ = edge
        sp: Phase = "egress" if kind == "transport" else "ingress"
        tp: Phase = "ingress" if kind == "transport" else "egress"
        a, b = anchors[source, sp], anchors[target, tp]
        gutters: list[int] = []
        for anchor in (a, b):
            placement_id = interfaces[anchor.interface_id].placement_zone_id
            key = placement_id, anchor.phase
            tracks[key] = tracks.get(key, 0) + 1
            direction = -1 if anchor.phase == "ingress" else 1
            gutters.append(anchor.point.x + direction * (16 + tracks[key] * 8))
        sg, tg = gutters
        lo, hi = sorted(
            (
                visible.index(interfaces[source].placement_zone_id),
                visible.index(interfaces[target].placement_zone_id),
            )
        )
        base = max(content_bottom[z] for z in visible[lo : hi + 1]) + 56
        lane = ((base + 35) // 36) * 36
        xmin, xmax = sorted(gutters)
        occupied = {ly for lx, rx, ly in shelves if not (xmax + 36 < lx or rx + 36 < xmin)}
        while lane in occupied:
            lane += 36
        shelves.append((xmin, xmax, lane))
        points: tuple[Point, ...] = (
            a.point,
            Point(sg, a.point.y),
            Point(sg, lane),
            Point(tg, lane),
            Point(tg, b.point.y),
            b.point,
        )
        routes.append(
            (edge, points, _label((xmin + xmax) // 2 - 14, lane - 25, 30, f"{number:02}", 11))
        )
    route_bottom = max([z.bounds.bottom for z in zones] + [y for _, _, y in shelves] + [280])
    key_top = route_bottom + 48
    transitions: list[Transition] = []
    for index, (edge, points, label) in enumerate(routes):
        identifier, kind, source, target, conduit = edge
        sp = "egress" if kind == "transport" else "ingress"
        tp = "ingress" if kind == "transport" else "egress"
        caption = f"{index + 1:02} · {kind} · {identifier}" + (
            f" · conduit {conduit}" if conduit else ""
        )
        key_label = _label(
            40 + index % 2 * ((width - 80) // 2),
            key_top + index // 2 * 28,
            (width - 100) // 2,
            caption,
            12,
        )
        transitions.append(
            Transition(
                identifier,
                kind,
                anchors[source, sp],
                anchors[target, tp],
                conduit,
                points,
                label,
                key_label,
            )
        )
    omissions = Omissions(
        tuple(z.id for z in model.zones[12:]) if summarized else (),
        tuple(a.id for a in model.assets) if summarized else (),
        tuple(i.id for i in model.interfaces) if summarized else (),
        tuple(
            sorted([e.id for e in model.transport_edges] + [e.id for e in model.forwarding_edges])
        )
        if summarized
        else (),
        len(devices) if summarized else 0,
    )
    limitations = (
        "Crossings and shared endpoint strokes are not junctions; routes may cross or overlap.",
        "Numbered routes use the edge key. Labels are shortened and clipped; "
        "full text is in titles and HTML evidence.",
        "Diagram proximity does not imply connectivity. "
        "Administrative ownership is not interface placement.",
    )
    footer = key_top + ((len(routes) + 1) // 2) * 28 + 12
    labels = [
        _label(
            40,
            14,
            width - 80,
            f"{'SUMMARY' if summarized else 'FULL'} schematic · {model.architecture_id}",
            20,
        ),
        _label(
            40,
            51,
            width - 80,
            "Arrows represent declared transitions, not necessarily permitted",
            12,
        ),
        _label(40, 73, width - 80, "communication or verified physical connectivity.", 12),
        _label(
            40,
            99,
            width - 80,
            "Declared placement only. Ports: ingress left, egress right. No implicit links.",
            12,
        ),
        _label(40, 125, width - 80, "Visible zone order: " + ", ".join(visible), 11),
    ]
    footer_values = [
        "Blue solid: transport. Purple dashed: explicit forwarding. "
        "Boundary cards reuse one asset ID.",
        f"Omitted: {omissions.attachment_cards} attachment cards; "
        f"{len(omissions.asset_ids)} assets; {len(omissions.interface_ids)} interfaces; "
        f"{len(omissions.edge_ids)} transitions; {len(omissions.zone_ids)} zones.",
        *limitations,
        "Structural declarations do not verify deployed connectivity. "
        "Finite model only; Security Levels unassessed.",
        "No conformity, safety or actual physical-network verification is claimed.",
    ]
    footer_y = footer
    for value in footer_values:
        for line in wrap(value, width=(width - 80) // 11):
            labels.append(_label(40, footer_y, width - 80, line, 11))
            footer_y += 26
    return Layout(
        Rect(0, 0, width, footer_y + 20),
        "summary" if summarized else "full",
        requested,
        order,
        tuple(zones),
        tuple(cards),
        tuple(transitions),
        devices,
        tuple(labels),
        omissions,
        limitations,
    )


def serialize_svg(layout: Layout, escape: Callable[[str], str], namespace: str = "") -> str:
    """Serialize frozen geometry only; namespaces isolate SVGs in comparisons."""
    if namespace and re.fullmatch(r"[a-z][a-z0-9_-]*", namespace) is None:
        raise ValueError("Invalid SVG namespace")
    prefix = namespace + "-" if namespace else ""
    parts: list[str] = []
    clips: list[str] = []
    label_index = 0

    def rect(r: Rect, attrs: str) -> str:
        return f'<rect x="{r.x}" y="{r.y}" width="{r.width}" height="{r.height}" {attrs}/>'

    def label(value: Label) -> str:
        nonlocal label_index
        label_index += 1
        clip_id = f"{prefix}label-{label_index}"
        clips.append(f'<clipPath id="{clip_id}">{rect(value.bounds, "")}</clipPath>')
        return (
            f'<g><title>{escape(value.full_text)}</title><text x="{value.bounds.x}" '
            f'y="{value.bounds.y + value.size + 2}" font-size="{value.size}" '
            f'clip-path="url(#{clip_id})">{escape(value.visible_text)}</text></g>'
        )

    parts.extend(label(value) for value in layout.labels)
    for zone in layout.zones:
        parts.append(
            f'<g data-zone-id="{escape(zone.zone_id)}"><title>Interface placement zone '
            f"{escape(zone.zone_id)}</title>"
        )
        fill = "#fff7ec" if zone.scope == "external" else "#edf5fa"
        parts.append(rect(zone.bounds, f'rx="12" fill="{fill}" stroke="#6b879b" stroke-width="2"'))
        parts.extend(label(value) for value in zone.labels)
        for card in layout.attachments:
            if card.placement_zone_id != zone.zone_id:
                continue
            parts.append(
                f'<g data-asset-id="{escape(card.asset_id)}" '
                f'data-placement-zone-id="{escape(card.placement_zone_id)}" '
                f'data-owner-zone-id="{escape(card.owner_zone_id)}">'
            )
            color = "#7946a0" if card.boundary else "#246c98"
            dash = 'stroke-dasharray="6 3"' if card.boundary else ""
            parts.append(
                rect(card.bounds, f'rx="8" fill="white" stroke="{color}" stroke-width="2" {dash}')
            )
            parts.extend(label(value) for value in card.labels)
            for row in card.interfaces:
                parts.append(f'<g data-interface-id="{escape(row.interface_id)}">')
                parts.extend(label(value) for value in row.labels)
                for anchor in (row.ingress, row.egress):
                    parts.append(
                        f'<circle cx="{anchor.point.x}" cy="{anchor.point.y}" r="5" '
                        f'data-interface-id="{escape(anchor.interface_id)}" '
                        f'data-phase="{anchor.phase}" fill="white" stroke="#246c98" '
                        f'stroke-width="2"><title>{escape(anchor.interface_id)} '
                        f"{anchor.phase}</title></circle>"
                    )
                parts.append("</g>")
            parts.append("</g>")
        parts.append("</g>")
    for edge in layout.transitions:
        points = edge.points
        commands = f"M{points[0].x},{points[0].y}" + "".join(
            f" H{b.x}" if a.y == b.y else f" V{b.y}"
            for a, b in zip(points, points[1:], strict=False)
        )
        marker = "forward" if edge.kind == "forwarding" else "transport"
        color = "#7946a0" if edge.kind == "forwarding" else "#246c98"
        dash = ' stroke-dasharray="8 4"' if edge.kind == "forwarding" else ""
        title = (
            f"{edge.edge_id}: {edge.source.interface_id} {edge.source.phase} → "
            f"{edge.target.interface_id} {edge.target.phase}; {edge.kind}; "
            f"conduit {edge.conduit_id or 'none'}"
        )
        parts.append(
            f'<g data-edge-id="{escape(edge.edge_id)}" data-kind="{edge.kind}" '
            f'data-source-interface-id="{escape(edge.source.interface_id)}" '
            f'data-target-interface-id="{escape(edge.target.interface_id)}" '
            f'data-source-phase="{edge.source.phase}" data-target-phase="{edge.target.phase}" '
            f'data-conduit-id="{escape(edge.conduit_id or "")}"><title>{escape(title)}</title>'
            f'<path d="{commands}" fill="none" stroke="{color}" stroke-width="2"{dash} '
            f'marker-end="url(#{prefix}{marker})"/>'
        )
        parts.extend((label(edge.label), label(edge.key), "</g>"))
    r = layout.bounds
    markers = "".join(
        f'<marker id="{prefix}{name}" markerWidth="9" markerHeight="8" refX="8" refY="4" '
        f'orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="{color}"/></marker>'
        for name, color in (("transport", "#246c98"), ("forward", "#7946a0"))
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{r.width}" height="{r.height}" '
        f'viewBox="0 0 {r.width} {r.height}" font-family="Arial, sans-serif" fill="#17334a" '
        'role="img" aria-label="Spatial architecture schematic with zone placement containers">'
        f"<title>Declared architecture. {escape(INTERPRETATION)}</title>"
        "<desc>Zone rectangles contain interface placements. Same asset ID means one device. "
        "Crossings are not junctions. "
        "Full declarations and omissions are in the report.</desc><defs>"
        + markers
        + "".join(clips)
        + "</defs>"
        + rect(r, 'fill="white"')
        + "".join(parts)
        + "</svg>"
    )


def spatial_svg(
    snapshot: ValidatedArchitecture,
    summarized: bool,
    escape: Callable[[str], str],
    *,
    requested: tuple[str, ...] = (),
    namespace: str = "",
) -> str:
    return serialize_svg(calculate_layout(snapshot, summarized, requested), escape, namespace)
