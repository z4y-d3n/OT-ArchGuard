"""Run the fictional capture tutorial through a regular installed console, offline."""

import argparse
import json
import os
import subprocess
import sysconfig
from pathlib import Path
from typing import Any

import yaml

from tools.capture_workloads import plant_model, write_pcap, write_pcapng


def walkthrough(output: Path) -> dict[str, Any]:
    output.mkdir(exist_ok=False)
    write_pcap(output / "plant.pcap")
    write_pcapng(output / "plant.pcapng", extended=True)
    model = output / "architecture.yaml"
    model.write_text(yaml.safe_dump(plant_model(), sort_keys=False), encoding="utf-8")
    console = Path(sysconfig.get_path("scripts")) / (
        "otarchguard.exe" if os.name == "nt" else "otarchguard"
    )

    def run(*args: str) -> dict[str, Any]:
        child = subprocess.run([str(console), "capture", *args], capture_output=True, timeout=120)
        if child.returncode or child.stderr:
            raise RuntimeError(
                f"Installed capture command failed: {child.stderr.decode(errors='replace')}"
            )
        result: dict[str, Any] = json.loads(child.stdout)
        return result

    inspections = [run("inspect", str(output / name)) for name in ("plant.pcap", "plant.pcapng")]
    run("analyze", str(output / "plant.pcapng"), "--output", str(output / "observed"))
    pending = output / "pending.json"
    run("map", str(output / "plant.pcapng"), "--model", str(model), "--output", str(pending))
    review = json.loads(pending.read_bytes())
    for proposal in review["proposals"]:
        if len(proposal["candidates"]) == 1:
            candidate = proposal["candidates"][0]
            proposal.update(
                decision="ACCEPT",
                selected_asset_id=candidate["asset_id"],
                selected_interface_id=candidate["interface_id"],
                reviewer="fictional_fixture_author",
                rationale="Fictional deterministic fixture identity; not a real owner decision.",
            )
    reviewed = output / "fictional-reviewed.json"
    reviewed.write_text(json.dumps(review, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    run(
        "compare",
        str(output / "plant.pcapng"),
        "--model",
        str(model),
        "--mapping",
        str(reviewed),
        "--output",
        str(output / "comparison"),
    )
    comparison = json.loads((output / "comparison/comparison.json").read_bytes())
    actual = {f["classification"] for f in comparison["findings"]}
    expected = {
        "OBSERVED_MODEL_REACHABLE",
        "OBSERVED_MODEL_UNREACHABLE",
        "OBSERVED_SERVICE_UNDECLARED",
        "OBSERVED_ENDPOINT_UNMAPPED",
        "OBSERVED_DIRECTION_UNCERTAIN",
        "OBSERVED_MODEL_UNSUPPORTED",
    }
    if not expected <= actual:
        raise AssertionError(f"Independent demonstration oracle missing {expected - actual}")
    result = {
        "status": "passed",
        "fictional_only": True,
        "inspections": inspections,
        "expected_classifications": sorted(expected),
        "actual_classifications": sorted(actual),
        "comparison_entrypoint": "comparison/index.html",
    }
    (output / "walkthrough.json").write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(walkthrough(args.output), sort_keys=True))


if __name__ == "__main__":
    main()
