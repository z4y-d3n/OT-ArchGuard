"""Trusted test declarations; production loading is exercised separately."""

import os
import sysconfig
from pathlib import Path
from typing import Any, cast

import pytest
import yaml


@pytest.fixture
def installed_console() -> Path:
    """Use this interpreter's install scheme, never a PATH or module fallback."""
    executable = Path(sysconfig.get_path("scripts")) / (
        "otarchguard.exe" if os.name == "nt" else "otarchguard"
    )
    assert executable.is_file(), f"Installed console launcher missing: {executable}"
    return executable


@pytest.fixture
def minimal() -> dict[str, Any]:
    return cast(
        dict[str, Any],
        yaml.safe_load(
            (Path(__file__).parent / "fixtures/minimal-valid.yaml").read_text(encoding="utf-8")
        ),
    )


@pytest.fixture
def boundary() -> dict[str, Any]:
    return cast(
        dict[str, Any],
        yaml.safe_load(
            (Path(__file__).parent / "fixtures/boundary-device.yaml").read_text(encoding="utf-8")
        ),
    )
