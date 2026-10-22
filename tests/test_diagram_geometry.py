"""Independent geometry oracles: SVG coordinates are checked against raw declarations."""

import random
import re
import xml.etree.ElementTree as ET
from copy import deepcopy
from dataclasses import FrozenInstanceError
from typing import Any

import pytest
import yaml

from otarchguard.api import ValidatedArchitecture, validate_bytes
from otarchguard.diagrams import INTERPRETATION, calculate_layout, zone_order
from otarchguard.reporting import architecture_svg, build_report, diagram_summary, html_report

NS = "{http://www.w3.org/2000/svg}"
type Box = tuple[int, int, int, int]
type XY = tuple[int, int]


def topology(
    minimal: dict[str, Any], zones: int, assets: int, pairs: list[tuple[int, int]]
) -> dict[str, Any]:
    """Original synthetic declarations, independent of the production geometry."""
    data = deepcopy(minimal)
    data["zones"] = [
        {**minimal["zones"][0], "id": f"z{i}", "name": f"Zone {i}"} for i in range(zones)
    ]
    data["assets"] = [
        {**minimal["assets"][0], "id": f"a{i}", "zone_id": f"z{i % zones}"} for i in range(assets)
    ]
    data["interfaces"] = [
        {
            "id": f"i{i}",
            "asset_id": f"a{i}",
            "placement_zone_id": f"z{i % zones}",
            "ipv4": f"192.0.2.{i + 1}/24",
        }
        for i in range(assets)
    ]
    data["transport_edges"] = []
    conduits: dict[tuple[int, int], dict[str, Any]] = {}
    for index, (a, b) in enumerate(pairs):
        edge: dict[str, Any] = {
            "id": f"e{index:02}",
            "source_interface_id": f"i{a}",
            "destination_interface_id": f"i{b}",
        }
        za, zb = sorted((a % zones, b % zones))
        if za != zb:
            conduits[za, zb] = {
                "id": f"c{za}_{zb}",
                "name": "Declared pair",
                "purpose": "Synthetic",
                "common_security_needs": "Unassessed",
                "zone_ids": [f"z{za}", f"z{zb}"],
            }
            edge["conduit_id"] = f"c{za}_{zb}"
        data["transport_edges"].append(edge)
    data["conduits"] = list(conduits.values())
    for collection in ("forwarding_edges", "rules", "intents", "services", "scenarios"):
        data[collection] = []
    data["suc"]["access_points"] = []
    data["suc"]["external_dependencies"] = []
    return data


def validated(data: dict[str, Any]) -> ValidatedArchitecture:
    return validate_bytes(yaml.safe_dump(data, allow_unicode=True).encode())


def box(element: ET.Element) -> Box:
    a = element.attrib
    return int(a["x"]), int(a["y"]), int(a["width"]), int(a["height"])


def contains(outer: Box, inner: Box) -> bool:
    x, y, w, h = outer
    a, b, c, d = inner
    return x <= a and y <= b and a + c <= x + w and b + d <= y + h


def intersects(a: Box, b: Box) -> bool:
    x, y, w, h = a
    p, q, r, s = b
    return x < p + r and p < x + w and y < q + s and q < y + h


def penetrates(a: XY, b: XY, obstacle: Box) -> bool:
    """Open rectangle interior vs axis-aligned segment; endpoints may touch borders."""
    x, y, w, h = obstacle
    if a[0] == b[0]:
        lo, hi = sorted((a[1], b[1]))
        return x < a[0] < x + w and max(lo, y) < min(hi, y + h)
    assert a[1] == b[1], (a, b)
    lo, hi = sorted((a[0], b[0]))
    return y < a[1] < y + h and max(lo, x) < min(hi, x + w)


def points(path: str) -> list[XY]:
    tokens = re.findall(r"([MHV])(-?\d+)(?:,(-?\d+))?", path)
    assert "".join(m[0] for m in tokens) == "MHVHVH"
    result: list[XY] = []
    for command, x, y in tokens:
        if command == "M":
            result.append((int(x), int(y)))
        elif command == "H":
            result.append((int(x), result[-1][1]))
        else:
            result.append((result[-1][0], int(x)))
    return result


def check_geometry(data: dict[str, Any], preference: tuple[str, ...] = ()) -> None:
    model = validated(data)
    svg = ET.fromstring(architecture_svg(model, zone_order=preference))
    bounds = (0, 0, int(svg.attrib["width"]), int(svg.attrib["height"]))
    cards: list[Box] = []
    ports: dict[tuple[str, str], XY] = {}
    raw_interfaces = {i["id"]: i for i in data["interfaces"]}
    for zone in svg.findall(f"{NS}g[@data-zone-id]"):
        rectangle = zone.find(f"{NS}rect")
        assert rectangle is not None
        zone_box = box(rectangle)
        assert contains(bounds, zone_box)
        for card in zone.findall(f"{NS}g[@data-asset-id]"):
            rectangle = card.find(f"{NS}rect")
            assert rectangle is not None
            card_box = box(rectangle)
            assert contains(zone_box, card_box)
            assert not any(intersects(card_box, other) for other in cards)
            cards.append(card_box)
            for port in card.findall(f".//{NS}circle"):
                identity, phase = port.attrib["data-interface-id"], port.attrib["data-phase"]
                raw = raw_interfaces[identity]
                assert raw["asset_id"] == card.attrib["data-asset-id"]
                assert raw["placement_zone_id"] == zone.attrib["data-zone-id"]
                xy = int(port.attrib["cx"]), int(port.attrib["cy"])
                assert xy[0] == card_box[0] + (0 if phase == "ingress" else card_box[2])
                assert card_box[1] < xy[1] < card_box[1] + card_box[3]
                assert (identity, phase) not in ports
                ports[identity, phase] = xy
    assert set(ports) == {(i, p) for i in raw_interfaces for p in ("ingress", "egress")}
    raw_edges = {
        e["id"]: (
            e["source_interface_id"],
            "egress",
            e["destination_interface_id"],
            "ingress",
            "transport",
            e.get("conduit_id", ""),
        )
        for e in data["transport_edges"]
    }
    raw_edges.update(
        {
            e["id"]: (
                e["ingress_interface_id"],
                "ingress",
                e["egress_interface_id"],
                "egress",
                "forwarding",
                e.get("conduit_id", ""),
            )
            for e in data["forwarding_edges"]
        }
    )
    wires = svg.findall(f"{NS}g[@data-edge-id]")
    assert {e.attrib["data-edge-id"] for e in wires} == set(raw_edges)
    assert len(wires) == len(raw_edges)
    paths: set[str] = set()
    for wire in wires:
        source, sp, target, tp, kind, conduit = raw_edges[wire.attrib["data-edge-id"]]
        assert wire.attrib["data-source-interface-id"] == source
        assert wire.attrib["data-target-interface-id"] == target
        assert wire.attrib["data-source-phase"] == sp and wire.attrib["data-target-phase"] == tp
        assert wire.attrib["data-kind"] == kind and wire.attrib["data-conduit-id"] == conduit
        path = wire.find(f"{NS}path")
        assert (
            path is not None
            and path.attrib["marker-end"]
            == f"url(#{'transport' if kind == 'transport' else 'forward'})"
        )
        route = points(path.attrib["d"])
        assert route[0] == ports[source, sp] and route[-1] == ports[target, tp]
        assert path.attrib["d"] not in paths  # parallel and reverse routes stay distinct
        paths.add(path.attrib["d"])
        for a, b in zip(route, route[1:], strict=False):
            assert a[0] == b[0] or a[1] == b[1]
            assert contains(bounds, (a[0], a[1], 0, 0))
            assert not any(penetrates(a, b, obstacle) for obstacle in cards)
        assert (route[-2][0] < route[-1][0]) == (tp == "ingress")
    # Circles are state anchors only; crossing/junction markers must not appear.
    assert len(svg.findall(f".//{NS}circle")) == len(ports)
    layout = calculate_layout(model, False, preference)
    labels = [*layout.labels, *(label for z in layout.zones for label in z.labels)]
    labels += [label for c in layout.attachments for label in c.labels]
    labels += [label for c in layout.attachments for i in c.interfaces for label in i.labels]
    labels += [label for e in layout.transitions for label in (e.label, e.key)]
    for label in labels:
        r = label.bounds
        assert contains(bounds, (r.x, r.y, r.width, r.height))
    for transition in layout.transitions:
        for label in (transition.label, transition.key):
            r = label.bounds
            assert not any(intersects((r.x, r.y, r.width, r.height), c) for c in cards)
    assert INTERPRETATION in "".join(svg.itertext())
    assert "not junctions" in "".join(svg.itertext())


def test_label_budget_is_independent_of_runtime_unicode_database(minimal: dict[str, Any]) -> None:
    # U+0897 is unassigned in Unicode 15, a combining mark in Unicode 16.
    # The display policy counts every scalar conservatively, without UCD lookup.
    minimal["assets"][0]["name"] = "A" + "\u0897" * 30 + "Z"
    layout = calculate_layout(validated(minimal), False)
    label = next(c for c in layout.attachments if c.asset_id == "eng").labels[0]
    assert label.visible_text == "A" + "\u0897" * 14 + "…"
    assert label.full_text == minimal["assets"][0]["name"]


@pytest.mark.parametrize("seed", range(24))
def test_fixed_seed_irregular_topologies(minimal: dict[str, Any], seed: int) -> None:
    rng = random.Random(seed)
    zones = rng.randint(1, 5)
    count = rng.randint(max(zones, 2), 10)
    pairs = [(a, b) for a, b in [rng.sample(range(count), 2) for _ in range(rng.randint(0, 40))]]
    check_geometry(topology(minimal, zones, count, pairs))


def test_boundary_forwarding_and_ownership_only(boundary: dict[str, Any]) -> None:
    # All fw interfaces are placed elsewhere: the owner-only card has no port.
    owner = next(a["zone_id"] for a in boundary["assets"] if a["id"] == "fw")
    boundary["zones"].append({**boundary["zones"][0], "id": "owner_only", "scope": "internal"})
    for asset in boundary["assets"]:
        if asset["id"] == "fw":
            asset["zone_id"] = "owner_only"
    assert owner != "owner_only"
    check_geometry(boundary, ("owner_only",))
    layout = calculate_layout(validated(boundary), False)
    attachments = [a for a in layout.attachments if a.asset_id == "fw"]
    assert len(attachments) >= 3
    assert all(a.owner_zone_id == "owner_only" for a in attachments)
    assert not next(a for a in attachments if a.placement_zone_id == "owner_only").interfaces
    with pytest.raises(FrozenInstanceError):
        layout.mode = "changed"  # type: ignore[misc]


def test_empty_edges_and_no_interfaces(minimal: dict[str, Any]) -> None:
    data = topology(minimal, 3, 2, [])
    data["interfaces"] = []
    check_geometry(data)


@pytest.mark.parametrize("defect", ["endpoint", "direction", "phantom-junction", "bounds"])
def test_independent_oracle_detects_corrupt_svg(
    minimal: dict[str, Any], monkeypatch: pytest.MonkeyPatch, defect: str
) -> None:
    data = topology(minimal, 2, 2, [(0, 1)])
    svg = ET.fromstring(architecture_svg(validated(data)))
    path = svg.find(f"{NS}g[@data-edge-id]/{NS}path")
    assert path is not None
    if defect == "endpoint":
        path.attrib["d"] = re.sub(r"^M\d+,", "M0,", path.attrib["d"])
    elif defect == "direction":
        path.attrib["marker-end"] = "url(#forward)"
    elif defect == "phantom-junction":
        ET.SubElement(svg, f"{NS}circle", {"cx": "0", "cy": "0", "r": "3"})
    else:
        svg.attrib["width"] = "1"
    monkeypatch.setattr(__name__ + ".architecture_svg", lambda *a, **kw: ET.tostring(svg).decode())
    with pytest.raises(AssertionError):
        check_geometry(data)


def test_zone_topology_order_and_cycle_fallback(minimal: dict[str, Any]) -> None:
    path = validated(topology(minimal, 4, 4, [(2, 0), (0, 1)]))
    assert zone_order(path) == ("z2", "z0", "z1", "z3")
    cycle = validated(topology(minimal, 4, 4, [(2, 0), (0, 2)]))
    assert zone_order(cycle) == ("z1", "z3", "z0", "z2")
    assert zone_order(path, ("z3", "z1")) == ("z3", "z1", "z2", "z0")


@pytest.mark.parametrize(
    "dimension,threshold",
    [("zones", 12), ("assets", 24), ("interfaces", 24), ("transport_edges", 48)],
)
@pytest.mark.parametrize("above", [0, 1])
def test_exact_summary_boundaries(
    minimal: dict[str, Any], dimension: str, threshold: int, above: int
) -> None:
    count = threshold + above
    data = topology(minimal, count if dimension == "zones" else 1, 2, [])
    if dimension == "assets":
        data["assets"] += [{**data["assets"][0], "id": f"extra{i}"} for i in range(count - 2)]
    elif dimension == "interfaces":
        data["interfaces"] += [
            {**data["interfaces"][0], "id": f"extra{i}", "ipv4": f"198.51.100.{i + 1}/24"}
            for i in range(count - 2)
        ]
    elif dimension == "transport_edges":
        data = topology(minimal, 1, 2, [(0, 1)] * count)
    model = validated(data)
    summary = diagram_summary(model)
    assert summary["mode"] == ("summary" if above else "full")
    layout = calculate_layout(model, bool(above))
    if above:
        assert not layout.attachments and not layout.transitions
        assert len(layout.omissions.interface_ids) == len(data["interfaces"])
        assert len(layout.omissions.edge_ids) == len(data["transport_edges"])
        assert len(layout.omissions.asset_ids) == len(data["assets"])
        assert len(layout.omissions.zone_ids) == max(0, len(data["zones"]) - 12)
        assert layout.omissions.attachment_cards == len(data["assets"])
        html = html_report(build_report("validation", (model,)), (model,)).decode()
        assert "Omitted connections are not absent connections" in html
        assert "Omitted attachment cards" in html
    else:
        check_geometry(data)


@pytest.mark.parametrize(
    "name",
    [
        "Español: acción",
        "中文 العربية Ω 😀 𐀀",
        "e\u0301" * 150,
        '<svg onload="x"> & \' </text>' * 12,
    ],
)
def test_finite_long_unicode_label_regions(minimal: dict[str, Any], name: str) -> None:
    data = topology(minimal, 2, 3, [(0, 1), (1, 0), (0, 1)])
    data["assets"][0]["name"] = name
    data["zones"][0]["name"] = name
    long_id = "i" * 64
    data["interfaces"][0]["id"] = long_id
    for edge in data["transport_edges"]:
        for field in ("source_interface_id", "destination_interface_id"):
            if edge[field] == "i0":
                edge[field] = long_id
    data["transport_edges"][0]["id"] = "e" * 64
    model = validated(data)
    check_geometry(data)
    svg = architecture_svg(model)
    text = "".join(ET.fromstring(svg).itertext())
    assert name in text and long_id in text
    assert architecture_svg(model) == svg
    layout = calculate_layout(model, False)
    assert any(
        label.visible_text != label.full_text
        for card in layout.attachments
        for label in card.labels
    )
