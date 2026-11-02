"""Actionable destination diagnostics for the fictional historical tutorials."""

import argparse
from pathlib import Path


def fresh_output(parser: argparse.ArgumentParser, output: Path) -> Path:
    """Check tutorial prerequisites without creating or replacing user files.

    The scenario still creates its destination exclusively. This preflight is
    guidance, not a replacement for publication checks or filesystem isolation.
    """
    output = output.absolute()
    if output.exists() or output.is_symlink():
        parser.error(
            "--output already exists; choose a fresh destination. Existing data is retained."
        )
    if not output.parent.is_dir():
        parser.error(
            "--output needs an existing parent directory; create the parent directory first."
        )
    return output
