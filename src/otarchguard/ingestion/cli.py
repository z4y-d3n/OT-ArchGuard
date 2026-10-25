"""Additive CLI commands for offline, explicitly owner-reviewed imports."""

import json
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from typing import Annotated

import typer

from otarchguard.contract import RESOURCE_LIMITS, ExitCode
from otarchguard.diagnostics import ModelError, fail
from otarchguard.ingestion.records import ImportDraft, OwnerDecisions
from otarchguard.ingestion.tabular import DelimitedAdapter, read_regular
from otarchguard.ingestion.workflow import (
    create_draft,
    emit_artifacts,
    load_profile,
    load_record,
    review_summary,
    review_template,
    serialize,
    write_new_bundle,
    write_new_file,
)
from otarchguard.loading import load_bytes

app = typer.Typer(
    help="Import untrusted offline evidence; owner confirmation is required before analysis.",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
    add_completion=False,
)


def _execute(operation: Callable[[], dict[str, object]]) -> None:
    try:
        result = operation()
    except ModelError as error:
        for diagnostic in error.diagnostics:
            typer.echo(json.dumps(asdict(diagnostic), sort_keys=True, ensure_ascii=True), err=True)
        raise typer.Exit(ExitCode.ERROR) from None
    except Exception:
        typer.echo(
            json.dumps(
                {
                    "category": "execution_error",
                    "code": "IMPORT_INTERNAL",
                    "location": "$",
                    "message": "Import could not complete; no analysis result is available.",
                },
                sort_keys=True,
            ),
            err=True,
        )
        raise typer.Exit(ExitCode.ERROR) from None
    typer.echo(serialize(result).decode(), nl=False)


@app.command("inspect")
def inspect_source(
    source: Annotated[Path, typer.Argument(help="Local inventory, drawio or GraphML source.")],
    delimiter: Annotated[str | None, typer.Option("--delimiter")] = None,
    encoding: Annotated[str, typer.Option("--encoding")] = "utf-8-sig",
    adapter: Annotated[
        str | None,
        typer.Option(
            "--adapter",
            help="json, xlsx, netbox-offline-v1, drawio, graphml, txt, md, docx or pptx.",
        ),
    ] = None,
) -> None:
    """Report bounded table structure and limits; never generate a model."""

    def run() -> dict[str, object]:
        selected = adapter or source.suffix.lower().lstrip(".")
        if selected in {"txt", "md", "docx", "pptx"}:
            if delimiter is not None or encoding != "utf-8-sig":
                fail(
                    "IMPORT_OPTIONS",
                    "$",
                    "Document adapters use restricted UTF-8 structural parsing.",
                )
            from otarchguard.ingestion.documents import inspect_document

            return inspect_document(source, selected)
        if selected in {"pdf", "vsdx"}:
            fail(
                "IMPORT_DOCUMENT_UNSUPPORTED",
                "$",
                "PDF and VSDX are deferred; no approved runtime parser is configured.",
            )
        if selected in {"graphml", "drawio"}:
            if delimiter is not None or encoding != "utf-8-sig":
                fail("IMPORT_OPTIONS", "$", "Text-table options do not apply to graphical sources.")
            from otarchguard.ingestion.graphical import inspect_graph

            return inspect_graph(source, selected)
        if selected == "xml":
            fail("IMPORT_OPTIONS", "$", "Compatible XML requires --adapter drawio or graphml.")
        if selected in {"json", "netbox-offline-v1", "xlsx"}:
            if delimiter is not None or encoding != "utf-8-sig":
                fail(
                    "IMPORT_OPTIONS", "$", "Text-table options do not apply to structured sources."
                )
            if selected == "xlsx":
                from otarchguard.ingestion.xlsx import inspect_xlsx

                return inspect_xlsx(source)
            from otarchguard.ingestion.json_inventory import inspect_json

            return inspect_json(source, selected)
        if adapter is not None:
            fail("IMPORT_OPTIONS", "$", "Unknown structured adapter.")
        delimited = DelimitedAdapter()
        return delimited.inspect(delimited.read(source, delimiter=delimiter, encoding=encoding))

    _execute(run)


# Register after defining _execute: project commands share the established error contract.
from otarchguard.ingestion.project_cli import app as project_app  # noqa: E402

app.add_typer(project_app, name="project")


@app.command("preview")
def preview(
    source: Annotated[Path, typer.Argument()],
    profile: Annotated[
        Path,
        typer.Option(
            "--profile", help="Explicit version-1/2/3 mapping or documentary version-4 selection."
        ),
    ],
) -> None:
    """Show candidates, unmapped values, conflicts and required review without writing."""
    _execute(lambda: review_summary(create_draft(source, load_profile(profile))))


@app.command("map")
def map_source(
    source: Annotated[Path, typer.Argument()],
    profile: Annotated[Path, typer.Option("--profile")],
    output: Annotated[Path, typer.Option("--output", help="New draft JSON file.")],
) -> None:
    """Apply exact mappings and create a versioned evidence draft; refuse overwrite."""

    def run() -> dict[str, object]:
        draft = create_draft(source, load_profile(profile))
        write_new_file(output, serialize(draft))
        return review_summary(draft)

    _execute(run)


@app.command("review")
def review(
    draft: Annotated[Path, typer.Argument()],
    decisions: Annotated[
        Path | None, typer.Option("--decisions", help="Create an unresolved decisions template.")
    ] = None,
    context: Annotated[
        Path | None, typer.Option("--context", help="Owner-supplied remaining native model fields.")
    ] = None,
) -> None:
    """List evidence and actions; a generated template never confirms anything."""

    def run() -> dict[str, object]:
        evidence = load_record(draft, ImportDraft)
        if context is not None and decisions is None:
            fail("IMPORT_OPTIONS", "$", "--context requires --decisions.")
        if decisions is not None:
            template = review_template(evidence)
            if context is not None:
                value = load_bytes(read_regular(context, RESOURCE_LIMITS.input_bytes))
                if not isinstance(value, dict):
                    fail("IMPORT_CONTEXT", "$", "Owner model context must be a mapping.")
                template = template.model_copy(update={"model": value})
            write_new_file(decisions, serialize(template))
        return review_summary(evidence)

    _execute(run)


@app.command("emit")
def emit(
    draft: Annotated[Path, typer.Argument()],
    source: Annotated[
        Path, typer.Option("--source", help="Original source, verified against draft.")
    ],
    decisions: Annotated[Path, typer.Option("--decisions", help="Completed owner decisions.")],
    output: Annotated[
        Path, typer.Option("--output", help="New directory for model and provenance.")
    ],
) -> None:
    """Validate confirmed declarations and publish a complete local artifact bundle."""

    def run() -> dict[str, object]:
        evidence = load_record(draft, ImportDraft)
        owner = load_record(decisions, OwnerDecisions)
        artifacts = emit_artifacts(evidence, owner, source)
        write_new_bundle(output, artifacts)
        provenance = json.loads(artifacts["architecture.provenance.json"])
        return {
            "status": "valid",
            "schema_version": 1,
            "model_sha256": provenance["model_sha256"],
            "artifacts": sorted(artifacts),
            "scope": "Owner-declared structural consistency; no deployed reachability assertion.",
        }

    _execute(run)
