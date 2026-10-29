"""Offline analysis with optional deterministic local evidence reports."""

import json
from dataclasses import asdict
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any

import typer
from typer.core import TyperCommand

from otarchguard import __version__
from otarchguard.api import ValidatedArchitecture, validate_file
from otarchguard.capture.cli import app as capture_app
from otarchguard.comparison import compare_architectures, compare_files
from otarchguard.contract import DiagnosticCategory, ExitCode
from otarchguard.diagnostics import Diagnostic, ModelError, fail
from otarchguard.evidence.cli import app as evidence_app
from otarchguard.explorer import ExploreOptions, generate_explorer
from otarchguard.exposure import QueryScope, exposure_architecture, exposure_file
from otarchguard.ingestion.cli import app as import_app
from otarchguard.intents import check_architecture, check_file
from otarchguard.reporting import (
    Analysis,
    ReportKind,
    build_report,
    html_report,
    json_report,
    write_report,
)
from otarchguard.review_cli import compare_architecture, quality
from otarchguard.trace import trace_file
from otarchguard.trace_reporting import trace_html, trace_json


class ReportFormat(StrEnum):
    JSON = "json"
    HTML = "html"


class TraceCommand(TyperCommand):
    """Keep expected trace parser errors inside the structured diagnostic boundary."""

    def parse_args(self, ctx: Any, args: list[str]) -> list[str]:
        try:
            return super().parse_args(ctx, args)
        except Exception as error:
            # Typer versions may vendor their parser. Usage errors consistently
            # carry native exit 2; help/interrupt/internal exceptions propagate.
            if getattr(error, "exit_code", None) != ExitCode.ERROR:
                raise
            command = (
                ctx.info_name
                if ctx.info_name in {"trace", "explore", "quality", "compare-architecture"}
                else "trace"
            )
            diagnostic = Diagnostic(
                DiagnosticCategory.INVALID_INPUT,
                "INVALID_VALUE",
                f"$.{command}_options",
                f"Invalid {command} options; see otarchguard {command} --help.",
            )
            typer.echo(json.dumps(asdict(diagnostic), sort_keys=True), err=True)
            raise typer.Exit(ExitCode.ERROR) from None


def _presentation_options(
    output: Path | None, format: ReportFormat, zone_order: tuple[str, ...]
) -> None:
    if zone_order and (output is None or format != ReportFormat.HTML):
        fail("INVALID_VALUE", "$.zone_order", "--zone-order requires an HTML --report.")


def _report(
    output: Path | None,
    format: ReportFormat,
    kind: ReportKind,
    inputs: tuple[Path, ...],
    result: Analysis = None,
    zone_order: tuple[str, ...] = (),
    *,
    snapshots: tuple[ValidatedArchitecture, ...] = (),
) -> None:
    _presentation_options(output, format, zone_order)
    if output is None:
        return
    # Reuse the completed immutable inputs actually evaluated by this invocation.
    # build_report still checks kind, arity and every result/model hash binding.
    report = build_report(kind, snapshots, result)
    data = (
        json_report(report)
        if format == ReportFormat.JSON
        else html_report(report, snapshots, zone_order=zone_order, analysis=result)
    )
    write_report(output, data, inputs)


app = typer.Typer(
    help="Offline IT/OT tool.\n\nValidate declarations and check initiation intents.",
    no_args_is_help=True,
    invoke_without_command=True,
    pretty_exceptions_enable=False,
    add_completion=False,
)
app.add_typer(import_app, name="import")
app.add_typer(capture_app, name="capture")
app.add_typer(evidence_app, name="evidence")
app.command("quality", cls=TraceCommand)(quality)
app.command("compare-architecture", cls=TraceCommand)(compare_architecture)


@app.command(cls=TraceCommand)
def explore(
    architecture: Annotated[Path, typer.Argument(help="Validated schema-1 model input.")],
    output: Annotated[Path, typer.Option("--output", help="Fresh local Explorer directory.")],
    provenance: Annotated[Path | None, typer.Option("--provenance")] = None,
    trace_query: Annotated[
        list[str] | None,
        typer.Option("--trace", help="Explicit source-asset:service query; repeatable."),
    ] = None,
    check: Annotated[bool, typer.Option("--check", help="Evaluate declared intents.")] = False,
    scenario: Annotated[
        list[str] | None,
        typer.Option("--scenario", help="Evaluate this declared exposure scenario."),
    ] = None,
) -> None:
    """Generate an offline, read-only multipage Architecture Explorer. No server or JavaScript."""
    try:
        queries: list[tuple[str, str]] = []
        for query in trace_query or ():
            parts = query.split(":")
            if len(parts) != 2 or not all(parts):
                fail("INVALID_VALUE", "$.explore", "Use --trace SOURCE_ASSET:SERVICE.")
            queries.append((parts[0], parts[1]))
        result = generate_explorer(
            architecture,
            output,
            provenance=provenance,
            options=ExploreOptions(tuple(queries), check, tuple(scenario or ())),
        )
    except ModelError as error:
        for diagnostic in error.diagnostics:
            typer.echo(json.dumps(asdict(diagnostic), sort_keys=True, ensure_ascii=True), err=True)
        raise typer.Exit(ExitCode.ERROR) from None
    except Exception:
        diagnostic = Diagnostic(
            DiagnosticCategory.EXECUTION_ERROR,
            "INTERNAL_ERROR",
            "$",
            "Explorer could not complete; no new site is available.",
        )
        typer.echo(json.dumps(asdict(diagnostic), sort_keys=True), err=True)
        raise typer.Exit(ExitCode.ERROR) from None
    typer.echo(json.dumps(result, sort_keys=True, ensure_ascii=True))


@app.command(cls=TraceCommand)
def trace(
    ctx: typer.Context,
    architecture: Annotated[Path, typer.Argument(help="Local schema-1 architecture YAML.")],
    source: Annotated[str, typer.Option("--source", help="Original source asset ID.")],
    service: Annotated[str, typer.Option("--service", help="Declared destination service ID.")],
    destination: Annotated[
        str | None, typer.Option("--destination", help="Assert the service's destination asset.")
    ] = None,
    policy_evidence: Annotated[bool, typer.Option("--policy-evidence")] = False,
    report: Annotated[Path | None, typer.Option("--report")] = None,
    report_format: Annotated[ReportFormat, typer.Option("--report-format")] = ReportFormat.HTML,
) -> None:
    """Trace one exact service-port union; completed unreachable queries also exit 0."""
    try:
        if (
            report is None
            and getattr(ctx.get_parameter_source("report_format"), "name", None) == "COMMANDLINE"
        ):
            fail("INVALID_VALUE", "$.trace_options", "--report-format requires --report.")
        result = trace_file(
            architecture,
            source,
            service,
            destination_asset_id=destination,
            policy_evidence=policy_evidence,
        )
        serialized = trace_json(result)
        if report is not None:
            data = serialized if report_format == ReportFormat.JSON else trace_html(result)
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
            "Trace could not complete; no result is available.",
        )
        typer.echo(json.dumps(asdict(diagnostic), sort_keys=True), err=True)
        raise typer.Exit(ExitCode.ERROR) from None
    typer.echo(serialized, nl=False)


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
    zone_order: Annotated[
        list[str] | None,
        typer.Option("--zone-order", help="HTML presentation zone ID; repeat in preferred order."),
    ] = None,
) -> None:
    """Validate schema, references and structural declarations; print a model hash."""
    try:
        _presentation_options(report, report_format, tuple(zone_order or ()))
        result = validate_file(architecture)
        if report is not None:
            envelope = build_report("validation", (result,))
            data = (
                json_report(envelope)
                if report_format == ReportFormat.JSON
                else html_report(envelope, (result,), zone_order=tuple(zone_order or ()))
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
    zone_order: Annotated[
        list[str] | None,
        typer.Option("--zone-order", help="HTML presentation zone ID; repeat in preferred order."),
    ] = None,
) -> None:
    """Check required/prohibited initiation intents with interval and path evidence."""
    try:
        snapshots = (validate_file(architecture),) if report is not None else ()
        result = check_architecture(snapshots[0]) if snapshots else check_file(architecture)
        payload = {"engine_version": __version__, "schema_version": 1, **asdict(result)}
        serialized = json.dumps(payload, sort_keys=True)
        _report(
            report,
            report_format,
            "check",
            (architecture,),
            result,
            tuple(zone_order or ()),
            snapshots=snapshots,
        )
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
    zone_order: Annotated[
        list[str] | None,
        typer.Option("--zone-order", help="HTML presentation zone ID; repeat in preferred order."),
    ] = None,
) -> None:
    """Evaluate a declared finite exposure scenario and all communication intents."""
    try:
        snapshots = (validate_file(architecture),) if report is not None else ()
        result = (
            exposure_architecture(snapshots[0], scenario)
            if snapshots
            else exposure_file(architecture, scenario)
        )
        serialized = json.dumps(
            {"engine_version": __version__, "schema_version": 1, **asdict(result)}, sort_keys=True
        )
        _report(
            report,
            report_format,
            "exposure",
            (architecture,),
            result,
            tuple(zone_order or ()),
            snapshots=snapshots,
        )
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
    zone_order: Annotated[
        list[str] | None,
        typer.Option("--zone-order", help="HTML presentation zone ID; repeat in preferred order."),
    ] = None,
) -> None:
    """Compare common stable definitions; keep inventory and intent changes separate."""
    try:
        scope = (
            QueryScope(tuple(origin or ()), tuple(service or ()))
            if origin is not None or service is not None
            else None
        )
        snapshots = (
            tuple(validate_file(path) for path in (baseline, proposed))
            if report is not None
            else ()
        )
        result = (
            compare_architectures(snapshots[0], snapshots[1], scenario, scope=scope)
            if snapshots
            else compare_files(baseline, proposed, scenario, scope=scope)
        )
        serialized = json.dumps(
            {"engine_version": __version__, "schema_version": 1, **asdict(result)}, sort_keys=True
        )
        _report(
            report,
            report_format,
            "comparison",
            (baseline, proposed),
            result,
            tuple(zone_order or ()),
            snapshots=snapshots,
        )
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
