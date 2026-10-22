"""Controlled diagnostics shared by loading, validation and CLI boundaries."""

from dataclasses import dataclass
from typing import NoReturn

from otarchguard.contract import DiagnosticCategory


@dataclass(frozen=True, slots=True)
class Diagnostic:
    category: DiagnosticCategory
    code: str
    location: str
    message: str
    line: int | None = None
    column: int | None = None


class ModelError(Exception):
    """A fatal error; never an analysis result or successful partial model."""

    def __init__(self, *diagnostics: Diagnostic) -> None:
        self.diagnostics = tuple(sorted(diagnostics, key=lambda d: (d.location, d.code)))
        super().__init__("Architecture processing failed")


def fail(
    code: str,
    location: str,
    message: str,
    category: DiagnosticCategory = DiagnosticCategory.INVALID_INPUT,
    *,
    line: int | None = None,
    column: int | None = None,
) -> NoReturn:
    raise ModelError(Diagnostic(category, code, location, message, line, column))


def check_limit(name: str, observed: int, maximum: int, location: str = "$") -> None:
    if observed > maximum:
        fail(
            "LIMIT_EXCEEDED",
            location,
            f"{name}: maximum {maximum}, observed/planned {observed}.",
            DiagnosticCategory.RESOURCE_LIMIT,
        )
