"""Reproducible Explorer sizes, timings, allocation peaks and repeated-byte audits."""

import argparse
import hashlib
import json
import tracemalloc
from pathlib import Path
from typing import Any

from otarchguard.explorer import generate_explorer
from tools.synthetic_explorer import explorer_workload


def inventory(root: Path) -> dict[str, str]:
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in root.iterdir()}


def samples(root: Path) -> list[dict[str, Any]]:
    root.mkdir(parents=True, exist_ok=False)
    results = []
    for name, assets, interfaces, connectors, sources in (
        ("small", 20, 30, 40, 3),
        ("medium", 150, 200, 250, 5),
        ("larger", 500, 600, 750, 6),
        ("adversarial", 150, 200, 250, 5),
    ):
        work = root / name
        model, sidecar = explorer_workload(
            work,
            assets,
            interfaces,
            connectors,
            sources,
            hostile=name == "adversarial",
        )
        result = generate_explorer(model, work / "site", provenance=sidecar)
        repeated = generate_explorer(model, work / "repeat", provenance=sidecar)
        assert inventory(work / "site") == inventory(work / "repeat")
        results.append(
            {
                "workload": name,
                "assets": assets,
                "interfaces": interfaces,
                "documentary_connectors": connectors,
                "sources": sources,
                "provenance_bytes": sidecar.stat().st_size,
                "first": result,
                "repeat_seconds": repeated["timings_seconds"],
                "byte_identical": True,
            }
        )
        print(name, result["site"], flush=True)
    # Separate traced-allocation samples: tracing overhead is excluded from timing samples.
    for name in ("small", "medium", "larger"):
        work = root / name
        tracemalloc.start()
        generate_explorer(
            work / "accepted/architecture.yaml",
            work / "allocation-site",
            provenance=work / "accepted/architecture.provenance.json",
        )
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        next(r for r in results if r["workload"] == name)["peak_python_allocation_bytes"] = peak
        print(name, "allocation peak", peak, flush=True)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    records = samples(args.output.parent / args.output.stem)
    args.output.write_text(json.dumps(records, sort_keys=True, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
