"""Capture CLI: independent evidence, explicit review, original-model evaluation."""

import json
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path, PureWindowsPath
from typing import Annotated, Any

import typer
from typer.core import TyperCommand, TyperGroup

from otarchguard.capture.contract import CAPTURE_LIMITS
from otarchguard.capture.explorer import fresh_destination, generate_site, write_mapping
from otarchguard.capture.observations import analyze_capture
from otarchguard.capture.parser import scan_capture
from otarchguard.capture.protocols import enrich_capture
from otarchguard.capture.reconciliation import compare_capture, load_mapping, mapping_template
from otarchguard.contract import DiagnosticCategory, ExitCode
from otarchguard.diagnostics import Diagnostic, ModelError, fail
from otarchguard.explorer_data import load_model
from otarchguard.ingestion.workflow import serialize, write_new_file


def _option_error(error: Exception) -> None:
    if getattr(error, "exit_code", None) != ExitCode.ERROR:
        raise error
    diagnostic = Diagnostic(
        DiagnosticCategory.INVALID_INPUT,
        "INVALID_VALUE",
        "$.capture_options",
        "Invalid capture options; see capture --help.",
    )
    typer.echo(json.dumps(asdict(diagnostic), sort_keys=True), err=True)
    raise typer.Exit(ExitCode.ERROR) from None


class CaptureCommand(TyperCommand):
    def parse_args(self, ctx: Any, args: list[str]) -> list[str]:
        try:
            return super().parse_args(ctx, args)
        except Exception as error:
            _option_error(error)
            raise AssertionError("unreachable") from None


class CaptureGroup(TyperGroup):
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
    cls=CaptureGroup,
    no_args_is_help=True,
    add_completion=False,
    pretty_exceptions_enable=False,
    help="Passive local PCAP evidence. Observations never authorize communications.",
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
            "CAPTURE_INTERNAL",
            "$",
            "Capture processing could not complete; no result is available.",
        )
        typer.echo(json.dumps(asdict(diagnostic), sort_keys=True), err=True)
        raise typer.Exit(ExitCode.ERROR) from None
    typer.echo(serialize(result).decode(), nl=False)


def _local(path: Path) -> Path:
    if str(path).startswith(("\\\\", "//")) or PureWindowsPath(path).drive.startswith("\\\\"):
        fail("CAPTURE_PATH", "$", "Only local filesystem paths are supported.")
    return path


@app.command("inspect", cls=CaptureCommand)
def inspect_capture(
    capture: Annotated[Path, typer.Argument(help="Local PCAP/PCAPNG; detected by header bytes.")],
) -> None:
    """Validate every record and report interfaces/limits; no model comparison."""

    def run() -> dict[str, Any]:
        return {
            "capture_version": 1,
            "capture": scan_capture(capture),
            "resource_ceilings": asdict(CAPTURE_LIMITS),
            "status": "complete",
        }

    _execute(run)


@app.command("enrich", cls=CaptureCommand)
def enrich(
    capture: Annotated[
        Path, typer.Argument(help="Local capture; bounded industrial headers only.")
    ],
    output: Annotated[
        Path | None, typer.Option("--output", help="Optional fresh enrichment JSON file.")
    ] = None,
) -> None:
    """Emit independent protocol metadata; existing observations and approvals are unchanged."""

    def run() -> dict[str, Any]:
        if output is not None:
            fresh_destination(output)
        result = enrich_capture(capture)
        if output is not None:
            write_new_file(output, serialize(result))
        return result

    _execute(run)


@app.command("analyze", cls=CaptureCommand)
def analyze(
    capture: Annotated[Path, typer.Argument(help="Local capture; payloads are never exported.")],
    output: Annotated[Path, typer.Option("--output", help="Fresh local evidence-site directory.")],
) -> None:
    """Decode bounded metadata, aggregate records and publish an offline evidence site."""

    def run() -> dict[str, Any]:
        fresh_destination(output)
        return generate_site(analyze_capture(capture), output)

    _execute(run)


@app.command("map", cls=CaptureCommand)
def propose_mapping(
    capture: Annotated[Path, typer.Argument(help="Local capture; identity proposals only.")],
    model: Annotated[Path, typer.Option("--model", help="Authoritative schema-1 YAML model.")],
    output: Annotated[Path, typer.Option("--output", help="Fresh association-decision JSON file.")],
) -> None:
    """Propose exact IPv4 interface candidates, all pending explicit owner review."""

    def run() -> dict[str, Any]:
        fresh_destination(output)
        observations = analyze_capture(capture)
        template = mapping_template(observations, load_model(_local(model)))
        write_mapping(output, template, CAPTURE_LIMITS)
        return {
            "association_version": 1,
            "capture_sha256": observations["capture"]["sha256"],
            "proposals": len(template["proposals"]),
            "status": "pending_review",
        }

    _execute(run)


@app.command("compare", cls=CaptureCommand)
def compare(
    capture: Annotated[Path, typer.Argument(help="Original locally stored capture.")],
    model: Annotated[Path, typer.Option("--model", help="Validated declaration, never modified.")],
    mapping: Annotated[Path, typer.Option("--mapping", help="Evidence-bound reviewed decisions.")],
    output: Annotated[
        Path, typer.Option("--output", help="Fresh local comparison-site directory.")
    ],
) -> None:
    """Compare justified TCP initiations; discrepancies and uncertainties exit 0."""

    def run() -> dict[str, Any]:
        fresh_destination(output)
        observations = analyze_capture(capture)
        validated = load_model(_local(model))
        review = load_mapping(_local(mapping))
        comparison = compare_capture(observations, validated, review)
        return generate_site(observations, output, comparison, mapping=review)

    _execute(run)
