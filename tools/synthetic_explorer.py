"""Fixed fictional Explorer workloads, never inferred production owner decisions."""

import json
import shutil
from pathlib import Path
from xml.etree import ElementTree as ET

from otarchguard.ingestion.project import create_project
from otarchguard.ingestion.project_review import emit_project
from tools.synthetic_projects import synthetic_project, tutorial_decisions, write_json


def explorer_workload(
    root: Path,
    assets: int,
    interfaces: int,
    connectors: int,
    sources: int,
    *,
    hostile: bool = False,
) -> tuple[Path, Path]:
    manifest = synthetic_project(
        root,
        count=assets,
        contradictory=False,
        formats=("xlsx", "json", "graph") if sources == 3 else ("csv", "xlsx", "json", "graph"),
    )
    configuration = json.loads(manifest.read_text(encoding="utf-8"))
    interface_path = root / "interfaces.json"
    data = json.loads(interface_path.read_text(encoding="utf-8"))
    for i in range(interfaces - assets):
        data["interfaces"].append(
            {
                "id": f"if_extra_{i}",
                "asset": f"n{i % assets}",
                "zone": "control",
                "ip": f"10.1.{i // 250}.{i % 250 + 1}/16",
            }
        )
    write_json(interface_path, data)
    topology = root / "topology.drawio"
    graph = ET.fromstring(topology.read_text(encoding="utf-8"))
    graph_root = graph.find(".//mxGraphModel/root")
    assert graph_root is not None
    for i in range(connectors - assets + 1):
        ET.SubElement(
            graph_root,
            "mxCell",
            {
                "id": f"extra_edge_{i}",
                "edge": "1",
                "parent": "1",
                "source": f"n{i % assets}",
                "target": f"n{(i + 7) % assets}",
                "value": "Repeated documentary label" if hostile else "Synthetic connection",
            },
        )
    if hostile:
        for node in graph_root.findall("mxCell"):
            if node.get("vertex") == "1":
                node.set("value", "Repeated <svg onload='alert(1)'> label " + "x" * 1000)
    topology.write_text(ET.tostring(graph, encoding="unicode"), encoding="utf-8", newline="\n")
    for i in range(max(0, sources - len(configuration["sources"]))):
        filename = f"supplement-{i}.csv"
        shutil.copyfile(root / "metadata.csv", root / filename)
        configuration["sources"].append(
            {
                "id": f"supplement-{i}",
                "path": filename,
                "adapter": "csv",
                "profile": "metadata-profile.json",
            }
        )
    write_json(manifest, configuration)
    draft = create_project(manifest)
    owner = tutorial_decisions(draft)
    if hostile:
        owner = owner.model_copy(
            update={
                "entities": tuple(
                    d.model_copy(update={"rationale": "Synthetic conflict rationale " + "x" * 3000})
                    for d in owner.entities
                )
            }
        )
    artifacts = emit_project(draft, owner, manifest)
    accepted = root / "accepted"
    accepted.mkdir(exist_ok=False)
    for name, value in artifacts.items():
        (accepted / name).write_bytes(value)
    return accepted / "architecture.yaml", accepted / "architecture.provenance.json"
