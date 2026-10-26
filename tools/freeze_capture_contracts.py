"""Reproduce fictional golden evidence; never update checked-in expectations implicitly."""

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from otarchguard.api import validate_bytes
from otarchguard.capture.observations import analyze_capture
from otarchguard.capture.reconciliation import compare_capture, mapping_template
from otarchguard.ingestion.workflow import serialize
from tools.capture_workloads import plant_model, write_pcapng
from tools.read_capture_evidence import load_bundle


def freeze(output: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=False)
    model = validate_bytes(yaml.safe_dump(plant_model(), sort_keys=False).encode())
    manifest: dict[str, Any] = {"fixture_version": 1, "fictional_only": True, "cases": {}}
    for case, extended in (("supported", False), ("limited", True)):
        directory = output / case
        directory.mkdir()
        capture = directory / "synthetic.pcapng"
        write_pcapng(capture, extended=extended)
        observations = analyze_capture(capture)
        mapping = mapping_template(observations, model)
        for proposal in mapping["proposals"]:
            if len(proposal["candidates"]) == 1:
                candidate = proposal["candidates"][0]
                proposal.update(
                    decision="ACCEPT",
                    selected_asset_id=candidate["asset_id"],
                    selected_interface_id=candidate["interface_id"],
                    reviewer="fictional-contract-author",
                    rationale="Synthetic fixture assertion only; no operational identity approval.",
                )
        comparison = compare_capture(observations, model, mapping)
        files = {}
        for name, document in (
            ("observations", observations),
            ("mapping", mapping),
            ("comparison", comparison),
        ):
            data = serialize(document)
            (directory / (name + ".json")).write_bytes(data)
            files[name + ".json"] = hashlib.sha256(data).hexdigest()
        # Retain only evidence contracts; consumers must work without the capture.
        capture.unlink()
        load_bundle(directory)
        manifest["cases"][case] = {
            "files": files,
            "capture_sha256": observations["capture"]["sha256"],
            "observations_sha256": observations["observations_sha256"],
            "model_sha256": model.sha256,
        }
    (output / "manifest.json").write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(freeze(args.output), sort_keys=True))


if __name__ == "__main__":
    main()
