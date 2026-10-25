"""Additive quality and complete architecture review commands."""

import json
from dataclasses import asdict
from pathlib import Path
from typing import Annotated

import typer

from otarchguard.contract import DiagnosticCategory, ExitCode
from otarchguard.diagnostics import Diagnostic, ModelError, fail
from otarchguard.quality import ReviewQuery, assess_quality, canonical
from otarchguard.review_explorer import generate_review


def _queries(values: list[str] | None) -> tuple[ReviewQuery, ...]:
    result = []
    for value in values or ():
        parts = value.split(":")
        if len(parts) != 2 or not all(parts):
            fail("INVALID_VALUE", "$", "Use --trace SOURCE_ASSET:SERVICE.")
        try:
            result.append(ReviewQuery(source_asset_id=parts[0], service_id=parts[1]))
        except ValueError:
            fail("INVALID_ID", "$", "Query must use schema-1 identifiers.")
    return tuple(result)


def _run(
    architecture: Path,
    output: Path | None,
    *,
    proposed: Path | None = None,
    provenance: Path | None = None,
    proposed_provenance: Path | None = None,
    profile: Path | None = None,
    proposed_profile: Path | None = None,
    mapping: Path | None = None,
    trace: list[str] | None = None,
) -> None:
    try:
        if output is None:
            typer.echo(
                canonical(
                    assess_quality(
                        architecture,
                        provenance=provenance,
                        profile=profile,
                        queries=_queries(trace),
                    )
                ).decode(),
                nl=False,
            )
            return
        result = generate_review(
            architecture,
            output,
            proposed=proposed,
            provenance=provenance,
            proposed_provenance=proposed_provenance,
            profile=profile,
            proposed_profile=proposed_profile,
            mapping=mapping,
            queries=_queries(trace),
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
            "Review could not complete; no successful partial report is available.",
        )
        typer.echo(json.dumps(asdict(diagnostic), sort_keys=True), err=True)
        raise typer.Exit(ExitCode.ERROR) from None
    typer.echo(json.dumps(result, sort_keys=True))


def quality(
    architecture: Annotated[Path, typer.Argument()],
    output: Annotated[
        Path | None, typer.Option("--output", help="Optional fresh local report directory.")
    ] = None,
    provenance: Annotated[Path | None, typer.Option("--provenance")] = None,
    profile: Annotated[Path | None, typer.Option("--profile")] = None,
    trace: Annotated[list[str] | None, typer.Option("--trace")] = None,
) -> None:
    """Assess declarations and explicit requirements; never produces a security score."""
    _run(architecture, output, provenance=provenance, profile=profile, trace=trace)


def compare_architecture(
    baseline: Annotated[Path, typer.Argument()],
    proposed: Annotated[Path, typer.Argument()],
    output: Annotated[Path, typer.Option("--output", help="Fresh offline comparison directory.")],
    baseline_provenance: Annotated[Path | None, typer.Option("--baseline-provenance")] = None,
    proposed_provenance: Annotated[Path | None, typer.Option("--proposed-provenance")] = None,
    baseline_profile: Annotated[Path | None, typer.Option("--baseline-profile")] = None,
    proposed_profile: Annotated[Path | None, typer.Option("--proposed-profile")] = None,
    mapping: Annotated[Path | None, typer.Option("--mapping")] = None,
    trace: Annotated[list[str] | None, typer.Option("--trace")] = None,
) -> None:
    """Compare native/evidence changes; optional exact traces use the existing engine."""
    _run(
        baseline,
        output,
        proposed=proposed,
        provenance=baseline_provenance,
        proposed_provenance=proposed_provenance,
        profile=baseline_profile,
        proposed_profile=proposed_profile,
        mapping=mapping,
        trace=trace,
    )
