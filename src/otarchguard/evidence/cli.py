"""Offline metadata-only evidence workspace commands."""

import json
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from typing import Annotated, Any

import typer
from typer.core import TyperCommand, TyperGroup

from otarchguard.contract import DiagnosticCategory, ExitCode
from otarchguard.diagnostics import Diagnostic, ModelError
from otarchguard.evidence.workspace import (
    add_snapshot,
    initialize_workspace,
    list_snapshots,
    serialize,
    show_snapshot,
    verify_workspace,
)


def _option_error(error: Exception) -> None:
    if getattr(error, "exit_code", None) != ExitCode.ERROR:
        raise error
    diagnostic = Diagnostic(
        DiagnosticCategory.INVALID_INPUT,
        "INVALID_VALUE",
        "$.evidence_options",
        "Invalid evidence options; see evidence --help.",
    )
    typer.echo(json.dumps(asdict(diagnostic), sort_keys=True), err=True)
    raise typer.Exit(ExitCode.ERROR) from None


class EvidenceCommand(TyperCommand):
    def parse_args(self, ctx: Any, args: list[str]) -> list[str]:
        try:
            return super().parse_args(ctx, args)
        except Exception as error:
            _option_error(error)
            raise AssertionError("unreachable") from None


class EvidenceGroup(TyperGroup):
    def parse_args(self, ctx: Any, args: list[str]) -> list[str]:
        try:
            return super().parse_args(ctx, args)
        except Exception as error:
            _option_error(error)
            raise AssertionError("unreachable") from None

    def resolve_command(self, ctx: Any, args: list[str]) -> tuple[str | None, Any, list[str]]:
        try:
            return super().resolve_command(ctx, args)
        except Exception as error:
            _option_error(error)
            raise AssertionError("unreachable") from None


app = typer.Typer(
    cls=EvidenceGroup,
    no_args_is_help=True,
    add_completion=False,
    pretty_exceptions_enable=False,
    help="Local immutable evidence metadata. Integrity is not authenticity or owner approval.",
)


def _execute(operation: Callable[[], dict[str, Any]]) -> None:
    try:
        result = operation()
    except ModelError as error:
        for diagnostic in error.diagnostics:
            typer.echo(json.dumps(asdict(diagnostic), sort_keys=True, ensure_ascii=True), err=True)
        raise typer.Exit(ExitCode.ERROR) from None
    except Exception:
        diagnostic = Diagnostic(
            DiagnosticCategory.EXECUTION_ERROR,
            "EVIDENCE_INTERNAL",
            "$",
            "Evidence processing could not complete; no result is available.",
        )
        typer.echo(json.dumps(asdict(diagnostic), sort_keys=True), err=True)
        raise typer.Exit(ExitCode.ERROR) from None
    typer.echo(serialize(result).decode(), nl=False)


@app.command("init", cls=EvidenceCommand)
def initialize(
    workspace: Annotated[Path, typer.Argument(help="New local workspace directory.")],
) -> None:
    """Create an empty workspace without replacing an existing directory."""
    _execute(lambda: initialize_workspace(workspace))


@app.command("add", cls=EvidenceCommand)
def add(
    workspace: Annotated[Path, typer.Argument(help="Existing local evidence workspace.")],
    observations: Annotated[Path, typer.Argument(help="Validated v2 observations.json metadata.")],
    label: Annotated[
        str, typer.Option(help="Optional descriptive label; never an evidence identity.")
    ] = "",
) -> None:
    """Import metadata; repeated capture SHA preserves the first snapshot and label."""
    _execute(lambda: add_snapshot(workspace, observations, label))


@app.command("list", cls=EvidenceCommand)
def list_evidence(workspace: Annotated[Path, typer.Argument()]) -> None:
    """Validate the workspace and list deterministic snapshot summaries."""
    _execute(lambda: list_snapshots(workspace))


@app.command("show", cls=EvidenceCommand)
def show(
    workspace: Annotated[Path, typer.Argument()], snapshot_id: Annotated[str, typer.Argument()]
) -> None:
    """Read an exact immutable snapshot, including original observation metadata."""
    _execute(lambda: show_snapshot(workspace, snapshot_id))


@app.command("verify", cls=EvidenceCommand)
def verify(workspace: Annotated[Path, typer.Argument()]) -> None:
    """Verify metadata hashes and structural joins; original capture is not reopened."""
    _execute(lambda: verify_workspace(workspace))
