"""Normalization/hash invariance without port partitioning or graph analysis."""

import json
import random
from copy import deepcopy
from typing import Any

import pytest
import yaml

from otarchguard.api import validate_bytes
from otarchguard.normalization import canonical_bytes, model_hash


def encode(data: dict[str, Any]) -> bytes:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True).encode("utf-8")


def shuffled(value: Any, generator: random.Random) -> Any:
    if isinstance(value, dict):
        keys = list(value)
        generator.shuffle(keys)
        return {key: shuffled(value[key], generator) for key in keys}
    if isinstance(value, list):
        result = [shuffled(child, generator) for child in value]
        generator.shuffle(result)
        return result
    return value


def test_order_whitespace_and_comment_invariance(boundary: dict[str, Any]) -> None:
    original = validate_bytes(encode(boundary))
    for seed in range(6):
        data = shuffled(boundary, random.Random(seed))
        source = b"# no semantic effect\n---\n" + encode(data) + b"...\n"
        result = validate_bytes(source)
        assert result.canonical_json == original.canonical_json
        assert result.sha256 == original.sha256
    assert canonical_bytes(original.model) == original.canonical_json
    assert model_hash(original.model) == original.sha256


def test_intervals_merge_and_preserve_boundary_ports(minimal: dict[str, Any]) -> None:
    minimal["services"][0]["destination_ports"] = [{"start": 1, "end": 65535}]
    original = validate_bytes(encode(minimal))
    minimal["services"][0]["destination_ports"] = [
        {"start": 60000, "end": 65535},
        {"start": 1, "end": 500},
        {"start": 500, "end": 59999},
    ]
    result = validate_bytes(encode(minimal))
    assert result.sha256 == original.sha256
    interval = result.model.services[0].destination_ports
    assert [(p.start, p.end) for p in interval] == [(1, 65535)]


@pytest.mark.parametrize("field", ["revision", "architecture_id"])
def test_snapshot_metadata_changes_hash(minimal: dict[str, Any], field: str) -> None:
    original = validate_bytes(encode(minimal))
    minimal[field] = "changed"
    assert validate_bytes(encode(minimal)).sha256 != original.sha256


@pytest.mark.parametrize(
    "field",
    [
        "id",
        "name",
        "purpose",
        "controlled_process",
        "boundary_description",
        "completeness_assertion",
    ],
)
def test_suc_metadata_is_preserved_in_hash(minimal: dict[str, Any], field: str) -> None:
    original = validate_bytes(encode(minimal))
    minimal["suc"][field] = "changed"
    assert validate_bytes(encode(minimal)).sha256 != original.sha256


def test_prose_and_unknown_classification_remain_verbatim(minimal: dict[str, Any]) -> None:
    minimal["suc"]["purpose"] = "  Declared propósito \n"
    minimal["assets"][0]["domain_classification"] = "unassessed"
    result = validate_bytes(encode(minimal))
    decoded = json.loads(result.canonical_json)
    assert decoded["suc"]["purpose"] == "  Declared propósito \n"
    assert decoded["assets"][0]["domain_classification"] == "unassessed"
    assert not any(
        key in result.canonical_json for key in (b"timestamp", b"absolute_path", b"sl_t")
    )


def test_distinct_selector_modes_remain_explicit(minimal: dict[str, Any]) -> None:
    original = validate_bytes(encode(minimal))
    alternate = deepcopy(minimal)
    alternate["rules"][0]["source"] = {"zone_ids": ["control"]}
    result = validate_bytes(encode(alternate))
    assert result.sha256 != original.sha256
    assert b'"zone_ids":["control"]' in result.canonical_json
