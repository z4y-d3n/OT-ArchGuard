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
from otarchguard.evidence.history import (
    add_collection,
    initialize_history,
    migrate_workspace,
    workspace_version,
)
from otarchguard.evidence.lifecycle import (
    create_revision,
    import_attachment,
    list_baselines,
    list_history,
    list_revisions,
    propose_baseline,
    record_review,
    show_object,
    validate_state,
    verify_lifecycle,
)
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


def _execute(
    operation: Callable[[], dict[str, Any]],
    render: Callable[[dict[str, Any]], str] | None = None,
) -> None:
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
    typer.echo(render(result) if render else serialize(result).decode(), nl=render is not None)


@app.command("init", cls=EvidenceCommand)
def initialize(
    workspace: Annotated[Path, typer.Argument(help="New local workspace directory.")],
    version: Annotated[
        int, typer.Option(help="Explicit workspace version: legacy 1 or history 2.")
    ] = 1,
) -> None:
    """Create an empty workspace without replacing an existing directory."""

    def operation() -> dict[str, Any]:
        if version not in {1, 2}:
            from otarchguard.diagnostics import fail

            fail("EVIDENCE_WORKSPACE", "$", "Use workspace version 1 or 2.")
        return initialize_workspace(workspace) if version == 1 else initialize_history(workspace)

    _execute(operation)


@app.command("add", cls=EvidenceCommand)
def add(
    workspace: Annotated[Path, typer.Argument(help="Existing local evidence workspace.")],
    observations: Annotated[Path, typer.Argument(help="Validated v2 observations.json metadata.")],
    label: Annotated[
        str, typer.Option(help="Optional descriptive label; never an evidence identity.")
    ] = "",
) -> None:
    """Import metadata; repeated capture SHA preserves the first snapshot and label."""
    _execute(
        lambda: (
            add_snapshot(workspace, observations, label)
            if workspace_version(workspace) == 1
            else add_collection(workspace, observations, label, validate_state)
        )
    )


@app.command("list", cls=EvidenceCommand)
def list_evidence(workspace: Annotated[Path, typer.Argument()]) -> None:
    """Validate the workspace and list deterministic snapshot summaries."""
    _execute(
        lambda: (
            list_snapshots(workspace)
            if workspace_version(workspace) == 1
            else list_history(workspace)
        )
    )


@app.command("show", cls=EvidenceCommand)
def show(
    workspace: Annotated[Path, typer.Argument()], snapshot_id: Annotated[str, typer.Argument()]
) -> None:
    """Read an exact immutable snapshot, including original observation metadata."""
    _execute(
        lambda: (
            show_snapshot(workspace, snapshot_id)
            if workspace_version(workspace) == 1
            else show_object(workspace, "snapshots", snapshot_id)
        )
    )


@app.command("verify", cls=EvidenceCommand)
def verify(workspace: Annotated[Path, typer.Argument()]) -> None:
    """Verify metadata hashes and structural joins; original capture is not reopened."""
    _execute(
        lambda: (
            verify_workspace(workspace)
            if workspace_version(workspace) == 1
            else verify_lifecycle(workspace)
        )
    )


@app.command("migrate", cls=EvidenceCommand)
def migrate(
    source: Annotated[Path, typer.Argument()], destination: Annotated[Path, typer.Argument()]
) -> None:
    """Validate v1 and copy exact snapshot bytes to a fresh workspace-v2 destination."""
    _execute(lambda: migrate_workspace(source, destination))


@app.command("attach", cls=EvidenceCommand)
def attach(
    workspace: Annotated[Path, typer.Argument()],
    snapshot_id: Annotated[str, typer.Argument()],
    kind: Annotated[str, typer.Argument(help="enrichment, model, mapping or comparison.")],
    source: Annotated[Path, typer.Argument(help="Native YAML model or supported producer JSON.")],
    model: Annotated[str | None, typer.Option(help="Exact model attachment dependency.")] = None,
    mapping: Annotated[
        str | None, typer.Option(help="Exact mapping attachment dependency.")
    ] = None,
) -> None:
    """Import a bounded validated attachment without modifying the original snapshot."""
    _execute(lambda: import_attachment(workspace, snapshot_id, kind, source, model, mapping))


revision_app = typer.Typer(
    cls=EvidenceGroup,
    no_args_is_help=True,
    add_completion=False,
    help="Immutable analytical revisions of exact physical collections.",
)
baseline_app = typer.Typer(
    cls=EvidenceGroup,
    no_args_is_help=True,
    add_completion=False,
    help="Explicit baseline proposals and locally asserted human decisions.",
)
app.add_typer(revision_app, name="revision")
app.add_typer(baseline_app, name="baseline")


@revision_app.command("create", cls=EvidenceCommand)
def revision_create(
    workspace: Annotated[Path, typer.Argument()],
    snapshot_id: Annotated[str, typer.Argument()],
    enrichment: Annotated[str | None, typer.Option()] = None,
    model: Annotated[str | None, typer.Option()] = None,
    mapping: Annotated[str | None, typer.Option()] = None,
    comparison: Annotated[str | None, typer.Option()] = None,
    semantics: Annotated[
        Path | None, typer.Option(help="Exact supported producer-semantics manifest.")
    ] = None,
) -> None:
    """Create an exact revision; repeated identical inputs are idempotent."""
    _execute(
        lambda: create_revision(
            workspace, snapshot_id, enrichment, model, mapping, comparison, semantics
        )
    )


@revision_app.command("list", cls=EvidenceCommand)
def revision_list(
    workspace: Annotated[Path, typer.Argument()],
    capture: Annotated[
        str | None, typer.Option(help="Filter by exact physical capture SHA-256.")
    ] = None,
) -> None:
    """List validated revisions in deterministic identity order, not chronology."""
    _execute(lambda: list_revisions(workspace, capture))


@revision_app.command("show", cls=EvidenceCommand)
def revision_show(
    workspace: Annotated[Path, typer.Argument()], analysis_id: Annotated[str, typer.Argument()]
) -> None:
    """Inspect one exact revision and its producer semantics."""
    _execute(lambda: show_object(workspace, "analyses", analysis_id))


@baseline_app.command("propose", cls=EvidenceCommand)
def baseline_propose(
    workspace: Annotated[Path, typer.Argument()],
    scope: Annotated[
        Path,
        typer.Argument(
            help="JSON environment, purpose, coverage, uncertainties, vantage_points and protocols."
        ),
    ],
    revision: Annotated[
        list[str] | None, typer.Option(help="Repeat for each exact selected analysis ID.")
    ] = None,
    kind: Annotated[str, typer.Option(help="evidence or architecture.")] = "evidence",
    model: Annotated[str | None, typer.Option(help="Exact validated model attachment.")] = None,
) -> None:
    """Select immutable evidence and explicit scope; proposal is never approval."""
    _execute(lambda: propose_baseline(workspace, scope, revision or [], kind, model))


def _readable_baseline(value: dict[str, Any]) -> str:
    scope = value["scope"]
    lines = [
        f"Baseline: {value['baseline_id']}",
        f"Kind: {value['kind']}  Status: {value['status']}",
        f"Environment: {scope['environment']}",
        f"Purpose: {scope['purpose']}",
        f"Coverage assertion: {scope['coverage']}",
        f"Uncertainties: {', '.join(scope['uncertainties']) or 'Unknown / not asserted'}",
        f"Vantage points: {', '.join(scope['vantage_points']) or 'Unknown / not asserted'}",
        f"Protocols: {', '.join(scope['protocols']) or 'Unknown / not asserted'}",
        f"Model attachment: {value['model_attachment_id'] or 'Absent'}",
    ]
    lines.extend(
        f"Collection {m['capture_sha256']} -> {m['analysis_id']}" for m in value["members"]
    )
    lines.extend(
        f"Decision {r['review_id']}: {r['decision']} by {r['reviewer']}; "
        f"{r['rationale']}; predecessor {r['predecessor']}"
        for r in value["review_history"]
    )
    lines.extend(value["limitations"])
    lines.append(value["pending_action"])
    return "\n".join(lines)


@baseline_app.command("review", cls=EvidenceCommand)
@baseline_app.command("show", cls=EvidenceCommand)
def baseline_show(
    workspace: Annotated[Path, typer.Argument()],
    baseline_id: Annotated[str, typer.Argument()],
    text: Annotated[bool, typer.Option(help="Bounded readable summary for human review.")] = False,
) -> None:
    """Inspect exact membership, scope, limitations and decision history."""
    _execute(
        lambda: show_object(workspace, "baselines", baseline_id),
        _readable_baseline if text else None,
    )


@baseline_app.command("list", cls=EvidenceCommand)
def baseline_list(workspace: Annotated[Path, typer.Argument()]) -> None:
    """List proposals and derived review states, including historical decisions."""
    _execute(lambda: list_baselines(workspace))


@baseline_app.command("approve", cls=EvidenceCommand)
def baseline_approve(
    workspace: Annotated[Path, typer.Argument()],
    baseline_id: Annotated[str, typer.Argument()],
    reviewer: Annotated[str, typer.Option(help="Required local reviewer assertion.")],
    rationale: Annotated[str, typer.Option(help="Required human rationale.")],
) -> None:
    """Explicitly APPROVE the exact baseline under its declared scope."""
    _execute(lambda: record_review(workspace, baseline_id, "approve", reviewer, rationale))


@baseline_app.command("reject", cls=EvidenceCommand)
def baseline_reject(
    workspace: Annotated[Path, typer.Argument()],
    baseline_id: Annotated[str, typer.Argument()],
    reviewer: Annotated[str, typer.Option()],
    rationale: Annotated[str, typer.Option()],
) -> None:
    """Explicitly REJECT the exact proposal, preserving it and the decision."""
    _execute(lambda: record_review(workspace, baseline_id, "reject", reviewer, rationale))


@baseline_app.command("revoke", cls=EvidenceCommand)
def baseline_revoke(
    workspace: Annotated[Path, typer.Argument()],
    baseline_id: Annotated[str, typer.Argument()],
    predecessor: Annotated[str, typer.Option(help="Exact active approval review ID.")],
    reviewer: Annotated[str, typer.Option()],
    rationale: Annotated[str, typer.Option()],
) -> None:
    """Explicitly REVOKE an exact approval without deleting its history."""
    _execute(
        lambda: record_review(workspace, baseline_id, "revoke", reviewer, rationale, predecessor)
    )


@baseline_app.command("supersede", cls=EvidenceCommand)
def baseline_supersede(
    workspace: Annotated[Path, typer.Argument()],
    baseline_id: Annotated[str, typer.Argument(help="New baseline proposal under the same scope.")],
    predecessor: Annotated[str, typer.Option(help="Exact active prior approval review ID.")],
    reviewer: Annotated[str, typer.Option()],
    rationale: Annotated[str, typer.Option()],
) -> None:
    """Explicitly APPROVE a successor and supersede its exact prior approval."""
    _execute(
        lambda: record_review(workspace, baseline_id, "supersede", reviewer, rationale, predecessor)
    )
