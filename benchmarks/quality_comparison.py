"""Fictional V12-06 complexity, one exact interface revision, bounded comparison output."""

import argparse
import json
import time
import tracemalloc
from pathlib import Path
from typing import Any

from otarchguard.explorer import generate_explorer
from otarchguard.explorer_data import load_model
from otarchguard.ingestion.project import create_project
from otarchguard.ingestion.project_review import emit_project
from otarchguard.review_explorer import generate_review
from tools.synthetic_explorer import explorer_workload
from tools.synthetic_projects import tutorial_decisions, write_json


def samples(output: Path) -> list[dict[str, Any]]:
    output.mkdir(parents=True, exist_ok=False)
    records = []
    for label, assets, interfaces, connectors, sources in (
        ("small", 20, 30, 40, 3),
        ("medium", 150, 200, 250, 5),
        ("larger", 500, 600, 750, 6),
    ):
        tick = time.perf_counter()
        work = output / label
        model, sidecar = explorer_workload(work, assets, interfaces, connectors, sources)
        payload = json.loads((work / "interfaces.json").read_text(encoding="utf-8"))
        payload["interfaces"][-1]["ip"] = "192.0.2.251/24"
        write_json(work / "interfaces.json", payload)
        manifest = next(
            p for p in work.glob("*.json") if '"project_version"' in p.read_text(encoding="utf-8")
        )
        draft = create_project(manifest)
        proposed = work / "proposed"
        proposed.mkdir()
        for name, data in emit_project(draft, tutorial_decisions(draft), manifest).items():
            (proposed / name).write_bytes(data)
        generated = time.perf_counter()
        options: dict[str, Any] = {
            "proposed": proposed / "architecture.yaml",
            "provenance": sidecar,
            "proposed_provenance": proposed / "architecture.provenance.json",
        }
        # Repeat real timings; allocation tracing is measured independently.
        results = [generate_review(model, work / ("site" + str(i)), **options) for i in range(3)]
        inventories = [
            {p.name: p.read_bytes() for p in (work / ("site" + str(i))).iterdir()} for i in range(3)
        ]
        assert inventories[0] == inventories[1] == inventories[2]
        tracemalloc.start()
        generate_review(model, work / "allocation-site", **options)
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        single = generate_explorer(model, work / "single-explorer", provenance=sidecar)
        review = json.loads((work / "site0/review.json").read_text(encoding="utf-8"))
        records.append(
            {
                "workload": label,
                "assets": assets,
                "interfaces": interfaces,
                "connectors": connectors,
                "sources": sources,
                "generation_seconds": generated - tick,
                "baseline_model_sha256": load_model(model).sha256,
                "samples": results,
                "peak_python_allocation_bytes": peak,
                "byte_identical": True,
                "comparison_records": len(review["changes"]),
                "quality_rules_evaluated": len(
                    {f["rule_id"] for f in review["quality_baseline"]["findings"]}
                ),
                "findings": len(review["quality_baseline"]["findings"])
                + len(review["quality_proposed"]["findings"]),
                "exact_queries_evaluated": len(review["analytical_results"]),
                "single_explorer": single,
            }
        )
        print(
            label, results[0]["site"]["html_pages"], results[0]["site"]["total_bytes"], flush=True
        )
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = samples(args.output.parent / args.output.stem)
    write_json(args.output, result)


if __name__ == "__main__":
    main()
