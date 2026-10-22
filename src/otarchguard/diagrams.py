"""Deterministic spatial SVG layout of declared placements and explicit transitions."""

from collections.abc import Callable
from textwrap import wrap

from otarchguard.api import ValidatedArchitecture
from otarchguard.domain import Asset, Interface


def spatial_svg(
    snapshot: ValidatedArchitecture, summarized: bool, escape: Callable[[str], str]
) -> str:
    """Draw placement containers, asset attachments and state-specific routed arrows.

    Attachment copies of a boundary asset are not separate assets. No line is
    generated for common ownership, shared placement, addresses or conduits.
    """
    model = snapshot.model
    zones = sorted(model.zones[:12], key=lambda zone: (zone.scope != "external", zone.id))
    width = max(1100, len(zones) * 360 + 40)
    zone_width = 1020 if len(zones) == 1 else 320
    # Each port has distinct ingress/egress anchors; neither connects implicitly.
    anchors: dict[tuple[str, str], tuple[int, int, int]] = {}
    zone_shapes: list[str] = []
    nodes: list[str] = []
    zone_bottoms: dict[str, int] = {}

    def text(x: int, y: int, value: str, *, size: int = 14, color: str = "#17334a") -> str:
        return (
            f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}">'
            f"<title>{escape(value)}</title>{escape(value)}</text>"
        )

    def label(x: int, y: int, value: str, *, limit: int = 29, lines: int = 2) -> str:
        segments = wrap(value, width=limit, break_long_words=True, break_on_hyphens=False) or [""]
        visible = segments[:lines]
        if len(segments) > lines:
            visible[-1] = visible[-1][: limit - 1] + "…"
        return (
            f"<g><title>{escape(value)}</title>"
            + "".join(text(x, y + index * 17, segment) for index, segment in enumerate(visible))
            + "</g>"
        )

    def icon(x: int, y: int, boundary: bool) -> str:
        if boundary:
            return (
                f'<path d="M{x}, {y} l24,0 l0,17 l-12,10 l-12,-10 z" '
                'fill="#eee4fb" stroke="#7946a0" stroke-width="2"/>'
                f'<path d="M{x + 6},{y + 8} h12 m-12,7 h12" stroke="#7946a0"/>'
            )
        return (
            f'<rect x="{x}" y="{y}" width="26" height="18" rx="2" '
            'fill="#dfeff8" stroke="#246c98" stroke-width="2"/>'
            f'<path d="M{x + 13},{y + 18} v7 m-9,0 h18" stroke="#246c98" stroke-width="2"/>'
        )

    # Group by placement first, then owning asset. An interface-free asset remains
    # visible in its owner zone without a network attachment or generated port.
    groups: dict[str, list[tuple[Asset, tuple[Interface, ...]]]] = {}
    for zone in zones:
        groups[zone.id] = []
        for asset in () if summarized else model.assets:
            placed = tuple(
                i
                for i in model.interfaces
                if i.asset_id == asset.id and i.placement_zone_id == zone.id
            )
            if placed or (
                asset.zone_id == zone.id
                and not any(i.asset_id == asset.id for i in model.interfaces)
            ):
                groups[zone.id].append((asset, placed))
            elif asset.zone_id == zone.id and not any(
                i.asset_id == asset.id and i.placement_zone_id == zone.id for i in model.interfaces
            ):
                # Administrative owner with all interfaces elsewhere: no phantom port.
                groups[zone.id].append((asset, ()))

    same_zone_counts = {z.id: 0 for z in zones}
    interfaces = {i.id: i for i in model.interfaces}
    transitions = (
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
    for _, _, source, target, _ in transitions:
        zone_id = interfaces[source].placement_zone_id
        if zone_id == interfaces[target].placement_zone_id:
            same_zone_counts[zone_id] += 1

    for zone_index, zone in enumerate(zones):
        x = 40 + zone_index * 360
        columns = 3 if len(zones) == 1 else 1
        bottoms = [170] * columns
        if not summarized:
            for index, (asset, placed) in enumerate(groups[zone.id]):
                col = index % columns
                nx = x + 40 + col * 320
                ny = bottoms[col]
                height = 116 + max(1, len(placed)) * 47
                bottom = ny + height
                bottoms[col] = bottom + 36
                attachment = asset.kind == "boundary_device"
                nodes.append(
                    f'<g data-asset-id="{escape(asset.id)}" '
                    f'data-placement-zone-id="{escape(zone.id)}" '
                    f'data-owner-zone-id="{escape(asset.zone_id)}">'
                    f"<title>{escape(asset.name)}; owner {escape(asset.zone_id)}; "
                    f"attachment placement {escape(zone.id)}</title>"
                    f'<rect x="{nx}" y="{ny}" width="240" height="{height}" rx="10" '
                    f'fill="white" stroke="{"#7946a0" if attachment else "#246c98"}" '
                    f'stroke-width="2"{(' stroke-dasharray="6 3"' if attachment else "")}/>'
                )
                nodes += [
                    icon(nx + 12, ny + 14, attachment),
                    label(nx + 49, ny + 27, asset.name, limit=22),
                    label(nx + 12, ny + 68, asset.id, limit=25, lines=1),
                    label(nx + 12, ny + 87, f"Owner: {asset.zone_id}", limit=27, lines=1),
                    text(
                        nx + 12,
                        ny + 104,
                        "Boundary attachment (same asset ID)" if attachment else "Endpoint",
                        size=11,
                    ),
                ]
                if not placed:
                    nodes.append(text(nx + 12, ny + 136, "No interface placed here", size=12))
                for port_index, interface in enumerate(placed):
                    py = ny + 128 + port_index * 47
                    nodes.append(f'<g data-interface-id="{escape(interface.id)}">')
                    nodes += [
                        label(nx + 20, py, interface.id, limit=24, lines=1),
                        text(nx + 20, py + 17, interface.ipv4, size=11),
                    ]
                    for phase, px, gutter in (
                        ("ingress", nx, nx - 20),
                        ("egress", nx + 240, nx + 260),
                    ):
                        anchors[interface.id, phase] = (px, py - 4, gutter)
                        nodes.append(
                            f'<circle cx="{px}" cy="{py - 4}" r="5" '
                            f'data-interface-id="{escape(interface.id)}" data-phase="{phase}" '
                            'fill="white" stroke="#246c98" stroke-width="2">'
                            f"<title>{escape(interface.id)} {phase}</title></circle>"
                        )
                    nodes.append("</g>")
                nodes.append("</g>")
        content_bottom = max(bottoms) if not summarized else 210
        zone_bottom = content_bottom + same_zone_counts[zone.id] * 34 + 45
        zone_bottoms[zone.id] = zone_bottom
        zone_shapes.append(
            f'<g data-zone-id="{escape(zone.id)}">'
            f"<title>{escape(zone.name)} — interface placement boundary</title>"
            f'<rect x="{x}" y="90" width="{zone_width}" height="{zone_bottom - 90}" '
            f'rx="16" fill="{"#fff7ec" if zone.scope == "external" else "#edf5fa"}" '
            'stroke="#6b879b" stroke-width="2"/>'
            + label(x + 16, 118, zone.name, limit=32, lines=1)
            + label(x + 16, 143, f"{zone.id} · {zone.scope.upper()}", limit=34, lines=1)
            + (text(x + 16, 185, "SUMMARY — attachments omitted", size=12) if summarized else "")
        )
        # Nodes are true SVG descendants of their placement zone container.
        zone_shapes.extend(nodes)
        nodes = []
        zone_shapes.append("</g>")

    max_bottom = max(zone_bottoms.values(), default=280)
    cross_index = 0
    local_indices = dict.fromkeys(zone_bottoms, 0)
    wires: list[str] = []
    for identifier, kind, source, target, conduit in transitions:
        source_phase, target_phase = (
            ("egress", "ingress") if kind == "transport" else ("ingress", "egress")
        )
        sx, sy, sg = anchors[source, source_phase]
        tx, ty, tg = anchors[target, target_phase]
        source_zone = interfaces[source].placement_zone_id
        target_zone = interfaces[target].placement_zone_id
        if source_zone == target_zone:
            local_indices[source_zone] += 1
            lane_y = zone_bottoms[source_zone] - 30 - (local_indices[source_zone] - 1) * 34
        else:
            cross_index += 1
            lane_y = max_bottom + cross_index * 38
        color = "#7946a0" if kind == "forwarding" else "#246c98"
        dash = ' stroke-dasharray="8 4"' if kind == "forwarding" else ""
        marker = "forward" if kind == "forwarding" else "transport"
        wires.append(
            f'<g data-edge-id="{escape(identifier)}" data-kind="{kind}" '
            f'data-source-interface-id="{escape(source)}" '
            f'data-target-interface-id="{escape(target)}">'
            f"<title>{escape(identifier)}: {escape(source)} {source_phase} → "
            f"{escape(target)} {target_phase}; {kind}; conduit {escape(conduit or 'none')}; "
            "declaration only, not a permitted-path assertion</title>"
            f'<path d="M{sx},{sy} H{sg} V{lane_y} H{tg} V{ty} H{tx}" '
            f'fill="none" stroke="{color}" stroke-width="2"{dash} '
            f'marker-end="url(#{marker})"/>'
        )
        lx = min(sg, tg) + 8
        caption = identifier + (f" · {conduit}" if conduit else "")
        wires.append(
            f'<rect x="{lx - 3}" y="{lane_y - 18}" width="{min(440, len(caption) * 7 + 12)}" '
            'height="19" rx="3" fill="white" fill-opacity="0.95"/>'
        )
        wires.append(label(lx, lane_y - 4, caption, limit=60, lines=1))
        wires.append("</g>")
    height = max_bottom + cross_index * 38 + 150
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="Arial, sans-serif" '
        'role="img" aria-label="Spatial architecture schematic with zone placement containers">',
        "<title>Architecture schematic: zones, assets, interfaces and declared edges</title>",
        '<defs><marker id="transport" markerWidth="9" markerHeight="8" refX="8" refY="4" '
        'orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#246c98"/></marker>'
        '<marker id="forward" markerWidth="9" markerHeight="8" refX="8" refY="4" '
        'orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#7946a0"/></marker></defs>',
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="white"/>',
        text(
            40,
            28,
            f"{'SUMMARY' if summarized else 'FULL'} schematic — {model.architecture_id}",
            size=20,
        ),
        text(
            40,
            53,
            "Zones enclose interface placements. Owner zone is labeled on each asset.",
            size=13,
        ),
        *zone_shapes,
        *wires,
        text(
            40,
            height - 95,
            "Blue solid arrows: transport · Purple dashed arrows: explicit internal forwarding.",
            size=13,
        ),
        text(
            40,
            height - 73,
            "Ports: ingress left, egress right. Crossings are not junctions. No implicit links.",
            size=13,
        ),
        text(
            40,
            height - 51,
            "Dashed shield cards: attachments of one boundary asset, with the same owner label.",
            size=13,
        ),
        text(
            40,
            height - 29,
            "Conduits label edges only; full pairwise declarations and omissions are in evidence.",
            size=13,
        ),
        "</svg>",
    ]
    return "".join(parts)
