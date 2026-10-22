"""Vocabulary/document agreement; not architecture validation."""

import re
from dataclasses import FrozenInstanceError, fields
from enum import StrEnum
from pathlib import Path

import pytest

from otarchguard import contract

SCHEMA = Path(__file__).resolve().parents[1] / "docs" / "yaml-schema-v1.md"


@pytest.mark.parametrize(
    "vocabulary",
    [
        contract.Protocol,
        contract.AssetKind,
        contract.Scope,
        contract.DomainClassification,
        contract.SafetyClassification,
        contract.SafetyDesignation,
        contract.Criticality,
        contract.RuleEffect,
        contract.IntentKind,
        contract.AccessPointKind,
        contract.DiagnosticCategory,
    ],
)
def test_vocabulary_is_documented(vocabulary: type[StrEnum]) -> None:
    document = SCHEMA.read_text(encoding="utf-8")
    for item in vocabulary:
        assert item.value in document


def test_resource_limits_match_documented_numbers() -> None:
    document = SCHEMA.read_text(encoding="utf-8")
    for field in fields(contract.RESOURCE_LIMITS):
        value = getattr(contract.RESOURCE_LIMITS, field.name)
        assert f"| `{field.name}` | {value:,}" in document
        with pytest.raises(FrozenInstanceError):
            setattr(contract.RESOURCE_LIMITS, field.name, 0)


def test_schema_identity_and_exit_contract() -> None:
    assert contract.SCHEMA_VERSION == 1
    assert tuple(contract.ExitCode) == (0, 1, 2)
    assert re.fullmatch(contract.ID_PATTERN, "a" + "0" * 63)
    for invalid in ("", "Upper", "a" * 65, "1id", "a.b", "a\n"):
        assert re.fullmatch(contract.ID_PATTERN, invalid) is None
