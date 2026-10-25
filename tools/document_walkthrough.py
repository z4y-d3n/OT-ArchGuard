"""Installed CLI demonstration for known fictional documents and mixed-source review."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sysconfig
from pathlib import Path

import otarchguard
from otarchguard.api import validate_bytes
from otarchguard.explorer_html import audit_site
from otarchguard.ingestion.project import create_project
from otarchguard.ingestion.workflow import serialize
from tools.synthetic_projects import tutorial_decisions, write_json

ROOT = Path(__file__).resolve().parents[1]


def walkthrough(output: Path) -> dict[str, object]:
    if Path(otarchguard.__file__).resolve().is_relative_to(ROOT / "src"):
        raise RuntimeError("A regular installed distribution is required")
    output.mkdir(parents=True, exist_ok=False)
    shutil.copytree(ROOT / "examples/import-studio/projects/mixed", output / "project")
    root = output / "project"
    documents = ROOT / "examples/import-studio/documents"
    for source in documents.iterdir():
        if source.suffix in {".txt", ".md", ".docx", ".pptx", ".json"}:
            shutil.copyfile(source, root / source.name)
    manifest = root / "project.json"
    config = json.loads(manifest.read_text(encoding="utf-8"))
    for adapter, filename in (
        ("txt", "notes.txt"),
        ("md", "notes.md"),
        ("docx", "inventory.docx"),
        ("pptx", "architecture.pptx"),
    ):
        config["sources"].append(
            dict(
                id="document-" + adapter,
                path=filename,
                adapter=adapter,
                profile=adapter + "-profile.json",
            )
        )
    write_json(manifest, config)
    console = Path(sysconfig.get_path("scripts")) / (
        "otarchguard.exe" if os.name == "nt" else "otarchguard"
    )
    commands = []

    def run(arguments: list[str], expected: int = 0) -> None:
        result = subprocess.run(
            [str(console), *arguments], cwd=output, capture_output=True, timeout=120
        )
        assert result.returncode == expected, result.stdout + result.stderr
        commands.append(
            dict(
                arguments=arguments,
                exit_code=result.returncode,
                stdout_sha256=hashlib.sha256(result.stdout).hexdigest(),
                stderr_sha256=hashlib.sha256(result.stderr).hexdigest(),
            )
        )

    for adapter, filename in (
        ("txt", "notes.txt"),
        ("md", "notes.md"),
        ("docx", "inventory.docx"),
        ("pptx", "architecture.pptx"),
    ):
        run(["import", "inspect", "project/" + filename])
        run(
            [
                "import",
                "preview",
                "project/" + filename,
                "--profile",
                "project/" + adapter + "-profile.json",
            ]
        )
    prefix = ["import", "project"]
    run([*prefix, "inspect", "project/project.json"])
    run([*prefix, "preview", "project/project.json"])
    run([*prefix, "map", "project/project.json", "--output", "draft.json"])
    run([*prefix, "review", "draft.json", "--decisions", "unresolved.json"])
    draft = create_project(manifest)
    # Explicit fictional-owner decisions for this shipped fixture only.
    # This demonstration is never a production review/accept-all operation.
    (output / "owner.json").write_bytes(serialize(tutorial_decisions(draft)))
    emission = [
        *prefix,
        "emit",
        "draft.json",
        "--project",
        "project/project.json",
        "--decisions",
        "owner.json",
        "--output",
        "accepted",
    ]
    run(emission)
    accepted = output / "accepted"
    native = validate_bytes((accepted / "architecture.yaml").read_bytes()).model
    assert not native.transport_edges and not native.forwarding_edges and not native.rules
    source = root / "notes.txt"
    source.write_bytes(source.read_bytes() + b"\nChanged after owner review.\n")
    run([*emission[:-1], "stale-refused"], 2)
    root.rename(output / "parked-documents")
    run(
        [
            "explore",
            "accepted/architecture.yaml",
            "--provenance",
            "accepted/architecture.provenance.json",
            "--output",
            "explorer",
        ]
    )
    return dict(
        status="passed",
        commands=commands,
        sources=len(draft.sources),
        document_observations=sum(
            len(s.evidence.document.observations) for s in draft.sources if s.evidence.document
        ),
        source_changes_refused=True,
        original_documents_parked=True,
        no_invented_permissions=True,
        site=audit_site(output / "explorer"),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = walkthrough(args.output.resolve())
    write_json(args.output / "walkthrough.json", result)
    print("Installed documentary walkthrough passed")


if __name__ == "__main__":
    main()
