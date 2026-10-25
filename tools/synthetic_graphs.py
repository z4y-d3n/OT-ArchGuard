"""Independent synthetic industrial graph fixtures; no private source material."""

import base64
import json
import zlib
from pathlib import Path
from urllib.parse import quote
from xml.etree import ElementTree as ET

from otarchguard.ingestion.records import GraphProfile

DEVICES = (
    ("eng", "Engineering workstation", "Engineering"),
    ("fw", "Industrial firewall", "Boundary"),
    ("sw", "Managed switch", "Switch"),
    ("plc", "PLC", "Controller"),
    ("hmi", "HMI", "Operator"),
    ("hist", "Historian", "Historian"),
)


def sub(element: ET.Element, name: str, /, **attributes: str) -> ET.Element:
    return ET.SubElement(element, name, attributes)


def compressed_model(xml: str) -> str:
    compressor = zlib.compressobj(wbits=-15)
    return base64.b64encode(
        compressor.compress(quote(xml, safe="~()*!.'-").encode()) + compressor.flush()
    ).decode()


def model_xml(count: int = 6) -> str:
    model = ET.Element("mxGraphModel")
    root = sub(model, "root")
    sub(root, "mxCell", id="0")
    sub(root, "mxCell", id="1", parent="0")
    for group in ("area_a", "area_b"):
        sub(
            root,
            "mxCell",
            id=group,
            value="Synthetic area",
            vertex="1",
            parent="1",
            style="swimlane;container=1;",
        )
    for i in range(count):
        name, label, role = DEVICES[i] if count == 6 else (f"n{i}", f"Synthetic {i}", "Device")
        wrapper = sub(root, "object", id=name, label=label, role=role)
        cell = sub(wrapper, "mxCell", vertex="1", parent="area_a" if i % 2 == 0 else "area_b")
        sub(
            cell,
            "mxGeometry",
            x=str(i * 100),
            y="20",
            width="80",
            height="40",
            **{"as": "geometry"},
        )
    ids = [d[0] for d in DEVICES] if count == 6 else [f"n{i}" for i in range(count)]
    for i in range(max(0, count - 1)):
        sub(
            root,
            "mxCell",
            id=f"e{i}",
            edge="1",
            parent="1",
            source=ids[i],
            target=ids[i + 1],
            value="Cable evidence",
            style="endArrow=classic;",
        )
    return ET.tostring(model, encoding="unicode")


def drawio_xml(*, compressed: bool = False, pages: int = 1, count: int = 6) -> str:
    root = ET.Element("mxfile")
    for i in range(pages):
        page = sub(root, "diagram", id=f"page{i + 1}", name="Synthetic topology")
        xml = model_xml(count)
        if compressed:
            page.text = compressed_model(xml)
        else:
            page.append(ET.fromstring(xml))
    return ET.tostring(root, encoding="unicode")


def graphml_xml(*, directed: bool = True, count: int = 6) -> str:
    root = ET.Element("graphml", xmlns="http://graphml.graphdrawing.org/xmlns")
    for key in ("label", "role"):
        sub(root, "key", id=key, **{"for": "node", "attr.name": key, "attr.type": "string"})
    numeric_key = sub(root, "key", id="load", **{"for": "node", "attr.type": "double"})
    sub(numeric_key, "default").text = "0.10000000000000001"
    graph = sub(root, "graph", id="plant", edgedefault="directed" if directed else "undirected")
    ids: list[str] = []
    for i in range(count):
        name, label, role = DEVICES[i] if count == 6 else (f"n{i}", f"Synthetic {i}", "Device")
        ids.append(name)
        node = sub(graph, "node", id=name)
        sub(node, "data", key="label").text = label
        sub(node, "data", key="role").text = role
    for i in range(max(0, count - 1)):
        sub(
            graph,
            "edge",
            id=f"e{i}",
            source=ids[i],
            target=ids[i + 1],
            **({"directed": "true"} if not directed and i == 0 else {}),
        )
    return ET.tostring(root, encoding="unicode")


def graph_profile(adapter: str, *, pages: int = 1, edges: bool = False) -> GraphProfile:
    tables: list[dict[str, object]] = [
        {
            "name": "assets",
            "collection": "nodes",
            "entity": "asset",
            "fields": {
                "id": {"path": "/scoped_id"},
                "name": {"path": "/label" if adapter == "drawio" else "/attributes/label"},
                "role": {"path": "/attributes/role"},
            },
            "constants": {
                "zone_id": "control",
                "kind": "endpoint",
                "scope": "internal",
                "domain_classification": "iacs",
                "safety_classification": "unassessed",
                "criticality": "unspecified",
            },
        }
    ]
    if edges:
        tables.append(
            {
                "name": "connections",
                "collection": "edges",
                "entity": "connection",
                "fields": {"id": {"path": "/scoped_id"}, "direction": {"path": "/direction"}},
            }
        )
    return GraphProfile.model_validate(
        {
            "profile_version": 3,
            "adapter": adapter,
            "scopes": [f"page{i + 1}" for i in range(pages)] if adapter == "drawio" else ["plant"],
            "tables": tables,
            "connections": "evidence_only",
            "unknown_policy": "diagnose",
        }
    )


def write_examples(directory: Path) -> None:
    for name, text in {
        "industrial.drawio": drawio_xml(),
        "multipage.drawio": drawio_xml(compressed=True, pages=2),
        "directed.graphml": graphml_xml(),
        "undirected.graphml": graphml_xml(directed=False),
    }.items():
        (directory / name).write_text(text + "\n", encoding="utf-8", newline="\n")
    for adapter in ("drawio", "graphml"):
        (directory / f"{adapter}-profile.json").write_text(
            json.dumps(graph_profile(adapter).model_dump(mode="json"), indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )


if __name__ == "__main__":
    write_examples(Path("examples/import-studio"))
