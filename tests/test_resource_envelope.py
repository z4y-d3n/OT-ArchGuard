"""Exact entity/work ceilings and benchmark semantics; timing assertions live outside pytest."""

from dataclasses import replace
from typing import Any

import pytest
import yaml

from benchmarks.workloads import source_bytes
from otarchguard.api import validate_bytes
from otarchguard.contract import RESOURCE_LIMITS
from otarchguard.diagnostics import ModelError
from otarchguard.exposure import exposure_bytes
from otarchguard.policy import Work


@pytest.mark.parametrize(
    "field,collection",
    [
        ("assets", "assets"),
        ("interfaces", "interfaces"),
        ("rules", "rules"),
        ("services", "services"),
        ("zones", "zones"),
        ("conduits", "conduits"),
        ("access_points", "access_points"),
        ("dependencies", "external_dependencies"),
        ("edges", "edges"),
        ("edge_rule_associations", "associations"),
    ],
)
def test_exact_declaration_ceiling_and_one_over(
    boundary: dict[str, Any], field: str, collection: str
) -> None:
    source = yaml.safe_dump(boundary).encode()
    if collection in {"access_points", "external_dependencies"}:
        count = len(boundary["suc"][collection])
    elif collection == "edges":
        count = len(boundary["transport_edges"]) + len(boundary["forwarding_edges"])
    elif collection == "associations":
        count = sum(len(r["edge_ids"]) for r in boundary["rules"])
    else:
        count = len(boundary[collection])
    validate_bytes(source, replace(RESOURCE_LIMITS, **{field: count}))
    validate_bytes(source, replace(RESOURCE_LIMITS, **{field: count + 1}))
    with pytest.raises(ModelError) as caught:
        validate_bytes(source, replace(RESOURCE_LIMITS, **{field: count - 1}))
    assert caught.value.diagnostics[0].category == "resource_limit"
    assert field in caught.value.diagnostics[0].message


@pytest.mark.parametrize("field", ["state_edge_visits", "edge_rule_atom_checks"])
def test_actual_work_counter_exact_ceiling(field: str) -> None:
    work = Work(replace(RESOURCE_LIMITS, **{field: 3}))
    operation = work.visit if field == "state_edge_visits" else work.predicate
    for _ in range(3):
        operation()
    with pytest.raises(ModelError) as caught:
        operation()
    assert field in caught.value.diagnostics[0].message


def test_nfr05_fixture_has_the_approved_sizes_and_nontrivial_paths() -> None:
    source = source_bytes()
    assert source == source_bytes()
    validated = validate_bytes(source)
    model = validated.model
    assert (
        len(model.assets),
        len(model.interfaces),
        len(model.transport_edges) + len(model.forwarding_edges),
        len(model.rules),
        len(model.services),
        len(model.scenarios[0].origin_asset_ids),
    ) == (200, 400, 1200, 200, 25, 10)
    assert len(model.forwarding_edges) == 40 and len(model.transport_edges) == 1160
    result = exposure_bytes(source, "scope")
    assert result.atom_queries == 300  # scenario 250 + independent required checks 50
    assert result.observations
    assert any(
        interval.witness and len(interval.witness.steps) >= 3
        for query in result.queries
        for interval in query.intervals
    )


@pytest.mark.parametrize("profile", ["dense-policy", "interval-heavy"])
def test_pathological_workloads_are_explicit_errors_not_unreachable(profile: str) -> None:
    with pytest.raises(ModelError) as caught:
        exposure_bytes(source_bytes(profile), "scope")
    assert caught.value.diagnostics[0].category == "resource_limit"
    assert caught.value.diagnostics[0].code == "LIMIT_EXCEEDED"
