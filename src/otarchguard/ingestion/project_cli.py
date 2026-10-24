"""One local CLI workflow for multi-source evidence and owner-reviewed declarations."""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Literal

import typer

from otarchguard.ingestion.project import (
    create_project,
    load_project_record,
    project_limits,
    protected_output,
)
from otarchguard.ingestion.project_records import EntityDecision, ProjectDecisions, ProjectDraft
from otarchguard.ingestion.project_review import (
    acknowledge_connectors,
    connector_sets,
    emit_project,
    project_summary,
    project_template,
    resolve_entity,
    review_markdown,
)
from otarchguard.ingestion.tabular import digest
from otarchguard.ingestion.workflow import serialize, write_new_bundle, write_new_file

app = typer.Typer(
    help="Reconcile multiple offline documents with explicit owner review.",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
    add_completion=False,
)


def _execute(operation: Callable[[], dict[str, object]]) -> None:
    # Lazy import keeps either CLI module independently importable.
    from otarchguard.ingestion.cli import _execute as execute

    execute(operation)


@app.command("init")
def init_project(output: Annotated[Path, typer.Option("--output")] = Path("project.json")) -> None:
    """Write a manifest starter; register explicit sources and profiles before mapping."""

    def run() -> dict[str, object]:
        write_new_file(
            output,
            serialize(
                {
                    "project_version": 1,
                    "project_id": "my-import-project",
                    "sources": [
                        {
                            "id": "assets",
                            "path": "assets.csv",
                            "adapter": "csv",
                            "profile": "assets-profile.yaml",
                        }
                    ],
                    "aliases": [],
                    "preferred_sources": {},
                    "model_context": None,
                }
            ),
        )
        return {
            "status": "manifest starter created",
            "next": "Register local sources, profiles and owner model context.",
        }

    _execute(run)


@app.command("inspect")
def inspect_project(manifest: Annotated[Path, typer.Argument()]) -> None:
    """Validate all registrations and report the bounded source inventory."""

    def run() -> dict[str, object]:
        draft = create_project(manifest)
        return {
            **project_summary(draft),
            "limits": project_limits(),
            "source_inventory": [
                {
                    "id": s.id,
                    "path": s.path,
                    "adapter": next(
                        entry.adapter for entry in draft.manifest.sources if entry.id == s.id
                    ),
                    "sha256": s.evidence.source.sha256,
                    "candidates": len(s.evidence.candidates),
                    "profile_sha256": s.profile_sha256,
                }
                for s in draft.sources
            ],
        }

    _execute(run)


@app.command("preview")
def preview_project(manifest: Annotated[Path, typer.Argument()]) -> None:
    """Report documentation coverage, proposed identity groups and blocking conflicts."""

    def run() -> dict[str, object]:
        draft = create_project(manifest)
        return {
            **project_summary(draft),
            "proposals": [p.model_dump() for p in draft.proposals],
            "conflicts": [c.model_dump() for c in draft.conflicts],
        }

    _execute(run)


@app.command("map")
def map_project(
    manifest: Annotated[Path, typer.Argument()],
    output: Annotated[Path, typer.Option("--output")],
) -> None:
    """Create one versioned catalog and reconciliation draft without confirming entities."""

    def run() -> dict[str, object]:
        protected_output(manifest, (output,))
        draft = create_project(manifest)
        write_new_file(output, serialize(draft))
        return project_summary(draft)

    _execute(run)


@app.command("review")
def review_project(
    draft: Annotated[Path, typer.Argument()],
    decisions: Annotated[Path | None, typer.Option("--decisions")] = None,
    report: Annotated[Path | None, typer.Option("--report")] = None,
    group: Annotated[str | None, typer.Option("--group")] = None,
) -> None:
    """Create unresolved decisions and a conflict-first Markdown report; inspect one group."""

    def run() -> dict[str, object]:
        evidence = load_project_record(draft, ProjectDraft)
        markdown = review_markdown(evidence, group)
        if decisions:
            write_new_file(decisions, serialize(project_template(evidence)))
        if report:
            write_new_file(report, markdown)
        return {**project_summary(evidence), **({"review": markdown.decode()} if group else {})}

    _execute(run)


@app.command("acknowledge")
def acknowledge(
    draft: Annotated[Path, typer.Argument()],
    decisions: Annotated[Path, typer.Option("--decisions")],
    source: Annotated[str, typer.Option("--source")],
    reviewer: Annotated[str, typer.Option("--reviewer")],
    rationale: Annotated[str, typer.Option("--rationale")],
    output: Annotated[Path, typer.Option("--output")],
) -> None:
    """Explicitly acknowledge one exact source connector set as evidence-only."""

    def run() -> dict[str, object]:
        evidence = load_project_record(draft, ProjectDraft)
        owner = load_project_record(decisions, ProjectDecisions)
        updated = acknowledge_connectors(evidence, owner, source, reviewer, rationale)
        write_new_file(output, serialize(updated))
        members = connector_sets(evidence)[source]
        return {
            "status": "evidence-only",
            "source": source,
            "count": len(members),
            "members": list(members),
            "set_sha256": digest(members),
            "model_confirmed": updated.model_confirmed,
        }

    _execute(run)


@app.command("emit")
def emit(
    draft: Annotated[Path, typer.Argument()],
    manifest: Annotated[Path, typer.Option("--project")],
    decisions: Annotated[Path, typer.Option("--decisions")],
    output: Annotated[Path, typer.Option("--output")],
) -> None:
    """Reproduce all inputs, verify owner resolutions and publish one validated model bundle."""

    def run() -> dict[str, object]:
        protected_output(manifest, (output,))
        evidence = load_project_record(draft, ProjectDraft)
        owner = load_project_record(decisions, ProjectDecisions)
        artifacts = emit_project(evidence, owner, manifest)
        write_new_bundle(output, artifacts)
        provenance = json.loads(artifacts["architecture.provenance.json"])
        return {
            "status": "valid",
            "schema_version": 1,
            "model_sha256": provenance["model_sha256"],
            "artifacts": sorted(artifacts),
            "scope": "Owner-declared architecture; no deployed completeness assertion.",
        }

    _execute(run)


@app.command("resolve")
def resolve(
    draft: Annotated[Path, typer.Argument()],
    decisions: Annotated[Path, typer.Option("--decisions")],
    member: Annotated[list[str], typer.Option("--member")],
    canonical_id: Annotated[str, typer.Option("--canonical-id")],
    reviewer: Annotated[str, typer.Option("--reviewer")],
    rationale: Annotated[str, typer.Option("--rationale")],
    output: Annotated[Path, typer.Option("--output")],
    decision: Annotated[
        Literal["OWNER_CONFIRMED", "OWNER_REJECTED", "EVIDENCE_ONLY"], typer.Option("--decision")
    ] = "OWNER_CONFIRMED",
    field_source: Annotated[list[str] | None, typer.Option("--field-source")] = None,
    correction: Annotated[list[str] | None, typer.Option("--set")] = None,
    reference: Annotated[list[str] | None, typer.Option("--reference")] = None,
) -> None:
    """Resolve one explicitly selected identity partition; reset whole-model confirmation."""

    def fields(items: list[str] | None) -> dict[str, str]:
        from otarchguard.diagnostics import fail

        result: dict[str, str] = {}
        for item in items or []:
            name, separator, value = item.partition("=")
            if not separator or not name or name in result:
                fail("PROJECT_FIELDS", "$", "Use distinct field=value options.")
            result[name] = value
        return result

    def run() -> dict[str, object]:
        evidence = load_project_record(draft, ProjectDraft)
        owner = load_project_record(decisions, ProjectDecisions)
        resolution = EntityDecision(
            members=tuple(sorted(member)),
            decision=decision,
            canonical_id=canonical_id,
            field_sources=fields(field_source),
            corrections=fields(correction),
            references=fields(reference),
            rationale=rationale,
        )
        updated = resolve_entity(evidence, owner, resolution, reviewer)
        write_new_file(output, serialize(updated))
        return {
            "status": decision,
            "resolution": resolution.model_dump(mode="json"),
            "model_confirmed": False,
            "draft_sha256": updated.draft_sha256,
        }

    _execute(run)
