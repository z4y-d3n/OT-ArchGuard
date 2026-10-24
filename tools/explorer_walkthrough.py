"""Execute shipped Explorer onboarding with a real noneditable installed console."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sysconfig
from pathlib import Path

import otarchguard
from otarchguard.explorer_html import audit_site

ROOT = Path(__file__).resolve().parents[1]


def walkthrough(output: Path) -> dict[str, object]:
    if Path(otarchguard.__file__).resolve().is_relative_to(ROOT / "src"):
        raise RuntimeError("Installed distribution required")
    output.mkdir(parents=True, exist_ok=False)
    shutil.copytree(ROOT / "examples/import-studio/projects/mixed", output / "project")
    shutil.copyfile(ROOT / "tests/fixtures/boundary-device.yaml", output / "native.yaml")
    console = Path(sysconfig.get_path("scripts")) / (
        "otarchguard.exe" if os.name == "nt" else "otarchguard"
    )
    commands = []

    def run(args: list[str], expected: int = 0) -> None:
        result = subprocess.run([str(console), *args], cwd=output, capture_output=True, timeout=120)
        assert result.returncode == expected, result.stdout + result.stderr
        commands.append(
            {
                "arguments": args,
                "exit_code": result.returncode,
                "stdout_sha256": hashlib.sha256(result.stdout).hexdigest(),
                "stderr_sha256": hashlib.sha256(result.stderr).hexdigest(),
            }
        )

    prefix = ["import", "project"]
    run([*prefix, "map", "project/project.json", "--output", "draft.json"])
    run(
        [
            *prefix,
            "emit",
            "draft.json",
            "--project",
            "project/project.json",
            "--decisions",
            "project/tutorial-decisions.json",
            "--output",
            "accepted",
        ]
    )
    before = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (output / "accepted").iterdir()
    }
    # Park all raw inputs: visualization operates only on the two accepted artifacts.
    (output / "project").rename(output / "parked-source")
    explore = [
        "explore",
        "accepted/architecture.yaml",
        "--provenance",
        "accepted/architecture.provenance.json",
        "--output",
        "explorer",
    ]
    run(explore)
    run(explore, 2)
    run(
        [
            "explore",
            "native.yaml",
            "--output",
            "analytical-explorer",
            "--trace",
            "it:svc_jump",
            "--trace",
            "it:svc_plc",
            "--check",
            "--scenario",
            "support_scope",
        ]
    )
    after = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (output / "accepted").iterdir()
    }
    assert before == after
    return {
        "status": "passed",
        "module": otarchguard.__file__,
        "commands": commands,
        "outside_checkout": not output.resolve().is_relative_to(ROOT),
        "accepted_inputs_unchanged": before == after,
        "raw_sources_parked": True,
        "provenance_site": audit_site(output / "explorer"),
        "analytical_site": audit_site(output / "analytical-explorer"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = walkthrough(args.output.resolve())
    (args.output / "walkthrough.json").write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print("Installed Explorer walkthrough passed")


if __name__ == "__main__":
    main()
