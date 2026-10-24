"""Execute shipped fictional project onboarding with the installed native console."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sysconfig
import time
from pathlib import Path

import otarchguard
from otarchguard.api import validate_bytes
from otarchguard.contract import RESOURCE_LIMITS
from otarchguard.graph import build_graph

ROOT = Path(__file__).resolve().parents[1]


def walkthrough(output: Path) -> dict[str, object]:
    if Path(otarchguard.__file__).resolve().is_relative_to(ROOT / "src"):
        raise RuntimeError("Installed distribution required; no source-tree fallback")
    output.mkdir(parents=True, exist_ok=False)
    shutil.copytree(ROOT / "examples/import-studio/projects/mixed", output / "project")
    console = Path(sysconfig.get_path("scripts")) / (
        "otarchguard.exe" if os.name == "nt" else "otarchguard"
    )
    records = []

    def run(arguments: list[str], expected: int = 0) -> None:
        started = time.perf_counter()
        result = subprocess.run(
            [str(console), *arguments], cwd=output / "project", capture_output=True, timeout=90
        )
        assert result.returncode == expected, result.stdout + result.stderr
        records.append(
            {
                "arguments": arguments,
                "exit_code": result.returncode,
                "expected": expected,
                "seconds": time.perf_counter() - started,
                "stdout_sha256": hashlib.sha256(result.stdout).hexdigest(),
                "stderr_sha256": hashlib.sha256(result.stderr).hexdigest(),
            }
        )

    prefix = ["import", "project"]
    run([*prefix, "inspect", "project.json"])
    run([*prefix, "preview", "project.json"])
    run([*prefix, "map", "project.json", "--output", "draft.json"])
    run([*prefix, "review", "draft.json", "--decisions", "decisions.json", "--report", "review.md"])
    run(
        [
            *prefix,
            "acknowledge",
            "draft.json",
            "--decisions",
            "decisions.json",
            "--source",
            "topology",
            "--reviewer",
            "Synthetic owner",
            "--rationale",
            "Inventory-only documentary connectors",
            "--output",
            "acknowledged.json",
        ]
    )
    run(
        [
            *prefix,
            "emit",
            "draft.json",
            "--project",
            "project.json",
            "--decisions",
            "acknowledged.json",
            "--output",
            "unresolved",
        ],
        2,
    )
    assert not (output / "project/unresolved").exists()
    emission = [
        *prefix,
        "emit",
        "draft.json",
        "--project",
        "project.json",
        "--decisions",
        "tutorial-decisions.json",
        "--output",
        "accepted",
    ]
    run(emission)
    run(emission, 2)
    run(["validate", "accepted/architecture.yaml"])
    data = (output / "project/accepted/architecture.yaml").read_bytes()
    validated = validate_bytes(data)
    assert (
        len(validated.model.assets) == 6 and not build_graph(validated.model, RESOURCE_LIMITS).edges
    )
    source = output / "project/topology.drawio"
    source.write_bytes(source.read_bytes().replace(b"Cable evidence", b"Changed cable evidence", 1))
    run(
        [
            *prefix,
            "emit",
            "draft.json",
            "--project",
            "project.json",
            "--decisions",
            "tutorial-decisions.json",
            "--output",
            "stale",
        ],
        2,
    )
    assert not (output / "project/stale").exists()
    return {
        "status": "passed",
        "commands": records,
        "model_sha256": validated.sha256,
        "module": otarchguard.__file__,
        "network_edges": 0,
        "source_mutation_rejected": True,
        "unresolved_rejected": True,
        "overwrite_rejected": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = walkthrough(args.output.resolve())
    (args.output / "walkthrough.json").write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print("Installed project walkthrough passed")


if __name__ == "__main__":
    main()
