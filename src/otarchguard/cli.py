"""Offline analysis with optional deterministic local evidence reports."""

import json
from dataclasses import asdict
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer

from otarchguard import __version__
from otarchguard.api import validate_file
from otarchguard.comparison import compare_files
from otarchguard.contract import DiagnosticCategory, ExitCode
from otarchguard.diagnostics import Diagnostic, ModelError
from otarchguard.exposure import QueryScope, exposure_file
from otarchguard.intents import check_file
from otarchguard.reporting import (
    Analysis,
    ReportKind,
    build_report,
    html_report,
    json_report,
    write_report,
)


class ReportFormat(StrEnum):
    JSON = "json"
    HTML = "html"


def _report(
    output: Path | None,
    format: ReportFormat,
    kind: ReportKind,
    inputs: tuple[Path, ...],
    result: Analysis = None,
) -> None:
    if output is None:
        return
    snapshots = tuple(validate_file(path) for path in inputs)
    report = build_report(kind, snapshots, result)
    data = json_report(report) if format == ReportFormat.JSON else html_report(report, snapshots)
    write_report(output, data, inputs)


app = typer.Typer(
    help="Offline IT/OT tool.\n\nValidate declarations and check initiation intents.",
    no_args_is_help=True,
    invoke_without_command=True,
    pretty_exceptions_enable=False,
    add_completion=False,
)


@app.callback()
def main(
    version: Annotated[bool, typer.Option("--version", help="Show package version.")] = False,
) -> None:
    """Validate declarations and check intents within the supported initiation model."""
    if version:
        typer.echo(__version__)
        raise typer.Exit(ExitCode.SUCCESS)


@app.command()
def validate(
    architecture: Annotated[Path, typer.Argument(help="Local architecture YAML path.")],
    report: Annotated[
        Path | None, typer.Option("--report", help="Local report output path.")
    ] = None,
    report_format: Annotated[ReportFormat, typer.Option("--report-format")] = ReportFormat.HTML,
) -> None:
    """Validate schema, references and structural declarations; print a model hash."""
    try:
        result = validate_file(architecture)
        if report is not None:
            envelope = build_report("validation", (result,))
            data = (
                json_report(envelope)
                if report_format == ReportFormat.JSON
                else html_report(envelope, (result,))
            )
            write_report(report, data, (architecture,))
    except ModelError as error:
        for diagnostic in error.diagnostics:
            typer.echo(json.dumps(asdict(diagnostic), sort_keys=True, ensure_ascii=True), err=True)
        raise typer.Exit(ExitCode.ERROR) from None
    except Exception:
        diagnostic = Diagnostic(
            DiagnosticCategory.EXECUTION_ERROR,
            "INTERNAL_ERROR",
            "$",
            "Validation could not complete; no valid result is available.",
        )
        typer.echo(json.dumps(asdict(diagnostic), sort_keys=True), err=True)
        raise typer.Exit(ExitCode.ERROR) from None
    typer.echo(
        json.dumps(
            {
                "status": "valid",
                "schema_version": result.model.schema_version,
                "engine_version": __version__,
                "model_sha256": result.sha256,
                "scope": "Declared structural consistency only; no path or compliance evaluation.",
            },
            sort_keys=True,
        )
    )


@app.command()
def check(
    architecture: Annotated[Path, typer.Argument(help="Local architecture YAML path.")],
    report: Annotated[
        Path | None, typer.Option("--report", help="Local report output path.")
    ] = None,
    report_format: Annotated[ReportFormat, typer.Option("--report-format")] = ReportFormat.HTML,
) -> None:
    """Check required/prohibited initiation intents with interval and path evidence."""
    try:
        result = check_file(architecture)
        payload = {"engine_version": __version__, "schema_version": 1, **asdict(result)}
        serialized = json.dumps(payload, sort_keys=True)
        _report(report, report_format, "check", (architecture,), result)
    except ModelError as error:
        for diagnostic in error.diagnostics:
            typer.echo(json.dumps(asdict(diagnostic), sort_keys=True, ensure_ascii=True), err=True)
        raise typer.Exit(ExitCode.ERROR) from None
    except Exception:
        diagnostic = Diagnostic(
            DiagnosticCategory.EXECUTION_ERROR,
            "INTERNAL_ERROR",
            "$",
            "Intent checking could not complete; no result is available.",
        )
        typer.echo(json.dumps(asdict(diagnostic), sort_keys=True), err=True)
        raise typer.Exit(ExitCode.ERROR) from None
    typer.echo(serialized)
    raise typer.Exit(ExitCode.SUCCESS if result.passed else ExitCode.FAILED_INTENTS)


@app.command()
def exposure(
    architecture: Annotated[Path, typer.Argument(help="Local architecture YAML path.")],
    scenario: Annotated[str, typer.Option("--scenario", help="Declared scenario ID.")],
    report: Annotated[
        Path | None, typer.Option("--report", help="Local report output path.")
    ] = None,
    report_format: Annotated[ReportFormat, typer.Option("--report-format")] = ReportFormat.HTML,
) -> None:
    """Evaluate a declared finite exposure scenario and all communication intents."""
    try:
        result = exposure_file(architecture, scenario)
        serialized = json.dumps(
            {"engine_version": __version__, "schema_version": 1, **asdict(result)}, sort_keys=True
        )
        _report(report, report_format, "exposure", (architecture,), result)
    except ModelError as error:
        for diagnostic in error.diagnostics:
            typer.echo(json.dumps(asdict(diagnostic), sort_keys=True), err=True)
        raise typer.Exit(ExitCode.ERROR) from None
    except Exception:
        diagnostic = Diagnostic(
            DiagnosticCategory.EXECUTION_ERROR,
            "INTERNAL_ERROR",
            "$",
            "Exposure evaluation could not complete; no result is available.",
        )
        typer.echo(json.dumps(asdict(diagnostic), sort_keys=True), err=True)
        raise typer.Exit(ExitCode.ERROR) from None
    typer.echo(serialized)
    raise typer.Exit(ExitCode.SUCCESS if result.passed else ExitCode.FAILED_INTENTS)


@app.command()
def compare(
    baseline: Annotated[Path, typer.Argument(help="Local baseline YAML path.")],
    proposed: Annotated[Path, typer.Argument(help="Local proposed YAML path.")],
    scenario: Annotated[
        str | None, typer.Option("--scenario", help="Common declared scenario ID.")
    ] = None,
    origin: Annotated[
        list[str] | None,
        typer.Option("--origin", help="Explicit common origin ID; repeat for a set."),
    ] = None,
    service: Annotated[
        list[str] | None,
        typer.Option("--service", help="Explicit common listener ID; repeat for a set."),
    ] = None,
    report: Annotated[
        Path | None, typer.Option("--report", help="Local report output path.")
    ] = None,
    report_format: Annotated[ReportFormat, typer.Option("--report-format")] = ReportFormat.HTML,
) -> None:
    """Compare common stable definitions; keep inventory and intent changes separate."""
    try:
        scope = (
            QueryScope(tuple(origin or ()), tuple(service or ()))
            if origin is not None or service is not None
            else None
        )
        result = compare_files(baseline, proposed, scenario, scope=scope)
        serialized = json.dumps(
            {"engine_version": __version__, "schema_version": 1, **asdict(result)}, sort_keys=True
        )
        _report(report, report_format, "comparison", (baseline, proposed), result)
    except ModelError as error:
        for diagnostic in error.diagnostics:
            typer.echo(json.dumps(asdict(diagnostic), sort_keys=True), err=True)
        raise typer.Exit(ExitCode.ERROR) from None
    except Exception:
        diagnostic = Diagnostic(
            DiagnosticCategory.EXECUTION_ERROR,
            "INTERNAL_ERROR",
            "$",
            "Comparison could not complete; no result is available.",
        )
        typer.echo(json.dumps(asdict(diagnostic), sort_keys=True), err=True)
        raise typer.Exit(ExitCode.ERROR) from None
    typer.echo(serialized)
    raise typer.Exit(ExitCode.SUCCESS if result.passed else ExitCode.FAILED_INTENTS)
