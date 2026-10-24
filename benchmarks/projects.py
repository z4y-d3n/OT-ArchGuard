"""Bounded synthetic reconciliation samples; timings are observations, not promises."""

import argparse
import json
import shutil
import time
import tracemalloc
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from otarchguard.diagnostics import ModelError
from otarchguard.ingestion.project import create_project, load_project_record
from otarchguard.ingestion.project_records import ProjectDraft
from otarchguard.ingestion.project_review import emit_project, project_template
from otarchguard.ingestion.workflow import create_draft, serialize
from tools.synthetic_projects import synthetic_project, tutorial_decisions, write_json


def samples(root: Path) -> list[dict[str, Any]]:
    root.mkdir(parents=True, exist_ok=False)
    results = []
    for name, count, source_count, interfaces, edges in [
        ("small", 20, 3, 30, 40),
        ("medium", 150, 5, 200, 250),
        ("larger", 500, 6, 600, 750),
    ]:
        directory = root / name
        path = synthetic_project(
            directory,
            count=count,
            contradictory=False,
            formats=("xlsx", "json", "graph")
            if source_count == 3
            else ("csv", "xlsx", "json", "graph"),
        )
        manifest = json.loads(path.read_text())
        interface_path = directory / "interfaces.json"
        inventory = json.loads(interface_path.read_text())
        for i in range(interfaces - count):
            inventory["interfaces"].append(
                {
                    "id": f"if_extra_{i}",
                    "asset": f"n{i % count}",
                    "zone": "control",
                    "ip": f"10.1.{i // 250}.{i % 250 + 1}/16",
                }
            )
        write_json(interface_path, inventory)
        graph_path = directory / "topology.drawio"
        graph = ET.fromstring(graph_path.read_text())
        graph_root = graph.find(".//mxGraphModel/root")
        assert graph_root is not None
        for i in range(edges - count + 1):
            ET.SubElement(
                graph_root,
                "mxCell",
                {
                    "id": f"extra_edge_{i}",
                    "edge": "1",
                    "parent": "1",
                    "source": f"n{i % count}",
                    "target": f"n{(i + 7) % count}",
                    "value": "Synthetic documentary connection",
                },
            )
        graph_path.write_text(ET.tostring(graph, encoding="unicode"), encoding="utf-8")
        for i in range(max(0, source_count - len(manifest["sources"]))):
            target = f"supplement-{i}.csv"
            shutil.copyfile(directory / "metadata.csv", directory / target)
            manifest["sources"].append(
                {
                    "id": f"supplement-{i}",
                    "path": target,
                    "adapter": "csv",
                    "profile": "metadata-profile.json",
                }
            )
        write_json(path, manifest)
        record: dict[str, Any] = {
            "workload": name,
            "logical_assets": count,
            "sources": source_count,
        }
        started = time.perf_counter()
        try:
            draft = create_project(path)
            record["aggregate_map_seconds"] = time.perf_counter() - started
            record["per_source_map_seconds"] = {}
            for source in draft.sources:
                tick = time.perf_counter()
                create_draft(directory / source.path, source.evidence.profile)
                record["per_source_map_seconds"][source.id] = time.perf_counter() - tick
            tick = time.perf_counter()
            data = serialize(draft)
            record["serialization_seconds"] = time.perf_counter() - tick
            record["draft_bytes"] = len(data)
            control = directory / "draft.json"
            control.write_bytes(data)
            tick = time.perf_counter()
            assert load_project_record(control, ProjectDraft) == draft
            record["draft_validation_seconds"] = time.perf_counter() - tick
            record["template_bytes"] = len(serialize(project_template(draft)))
            record["accounting"] = draft.accounting
            tick = time.perf_counter()
            artifacts = emit_project(draft, tutorial_decisions(draft), path)
            record["emission_seconds"] = time.perf_counter() - tick
            record["sidecar_bytes"] = len(artifacts["architecture.provenance.json"])
            record["declarations_per_second"] = count / record["emission_seconds"]
            assert artifacts == emit_project(draft, tutorial_decisions(draft), path)
            record["deterministic"] = True
            record["status"] = "passed"
        except ModelError as error:
            record.update(
                status="bounded rejection",
                seconds=time.perf_counter() - started,
                diagnostics=[
                    {"code": d.code, "location": d.location, "message": d.message}
                    for d in error.diagnostics
                ],
            )
        results.append(record)
    path = synthetic_project(root / "adversarial-labels", count=150, contradictory=False)
    profile_path = path.parent / "metadata-profile.json"
    profile = json.loads(profile_path.read_text())
    del profile["fields"]["name"]
    profile["constants"]["name"] = "Repeated label"
    write_json(profile_path, profile)
    started = time.perf_counter()
    dense = create_project(path)
    results.append(
        {
            "workload": "adversarial-labels",
            "seconds": time.perf_counter() - started,
            "accounting": dense.accounting,
            "maximum_group_members": max(len(g.members) for g in dense.proposals),
            "status": "bounded groups; no merges",
        }
    )
    path = synthetic_project(root / "allocation-sample", count=20, contradictory=False)
    tracemalloc.start()
    create_project(path)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    results.append(
        {
            "workload": "allocation-sample",
            "logical_assets": 20,
            "peak_python_allocations_bytes": peak,
            "scope": "tracemalloc, not RSS/native memory",
        }
    )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = samples(args.output.with_suffix(""))
    write_json(args.output, {"samples": result})
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
