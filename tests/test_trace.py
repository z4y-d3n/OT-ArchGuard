"""Trace adapters checked against raw declaration per-port and witness oracles."""

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
import yaml
from test_reachability_oracle import oracle, replay_raw, synthetic

from otarchguard.api import validate_bytes
from otarchguard.contract import RESOURCE_LIMITS
from otarchguard.diagnostics import ModelError
from otarchguard.trace import trace_architecture, trace_bytes, trace_file
from otarchguard.trace_reporting import trace_html, trace_json


@pytest.mark.parametrize("seed", range(36))
def test_trace_raw_graph_port_and_witness_oracles(minimal: dict[str, Any], seed: int) -> None:
    raw = synthetic(minimal, seed)
    # Explicit disjoint union, including boundaries absent from the policy rules.
    for service in raw["services"]:
        service["destination_ports"] = [{"start": 1, "end": 3}, {"start": 5, "end": 8}]
    data = yaml.safe_dump(raw).encode()
    for source in ("eng", "gwa"):
        for service in ("svc_plc", "svc_udp"):
            result = trace_bytes(data, source, service)
            ports = [p for i in result.intervals for p in range(i.start, i.end + 1)]
            assert ports == [1, 2, 3, 5, 6, 7, 8]  # order, coverage, no overlaps
            assert result.work.query_atoms == len(result.intervals)
            for interval in result.intervals:
                assert interval.protocol == result.scope.protocol
                assert all(
                    interval.reachable == oracle(raw, source, service, port)
                    for port in range(interval.start, interval.end + 1)
                )
                if interval.reachable:
                    assert interval.witness is not None and interval.diagnostics is None
                    assert interval.witness.snapshot_sha256 == result.model_sha256
                    assert interval.witness.protocol == result.scope.protocol
                    assert (interval.witness.start, interval.witness.end) == (
                        interval.start,
                        interval.end,
                    )
                    replay_raw(raw, interval.witness)
                else:
                    assert interval.witness is None and interval.diagnostics is not None
                    structural = {
                        **raw,
                        "rules": [
                            {
                                "id": "all",
                                "edge_ids": [
                                    e["id"]
                                    for e in raw["transport_edges"] + raw["forwarding_edges"]
                                ],
                                "source": {"all_assets": True},
                                "destination": {"all_assets": True},
                                "protocol": result.scope.protocol,
                                "effect": "allow",
                                "destination_ports": [{"start": 1, "end": 8}],
                            }
                        ],
                    }
                    assert interval.diagnostics.structural_path_exists == oracle(
                        structural, source, service, interval.start
                    )
            assert trace_json(result) == trace_json(trace_bytes(data, source, service))
            assert b'"passed"' not in trace_json(result)


def test_trace_api_and_destination_binding(minimal: dict[str, Any], tmp_path: Path) -> None:
    data = yaml.safe_dump(minimal).encode()
    path = tmp_path / "model.yaml"
    path.write_bytes(data)
    snap = validate_bytes(data)
    result = trace_architecture(snap, "eng", "svc_plc", destination_asset_id="plc")
    assert result == trace_bytes(data, "eng", "svc_plc") == trace_file(path, "eng", "svc_plc")
    assert result.model_sha256 == snap.sha256
    assert result.scope.destination_interface_id == "plc_net"
    assert result.intervals[0].reachable
    payload = json.loads(trace_json(result))
    assert payload["trace_version"] == 1 and not payload["intents_assessed"]
    assert payload["policy_evidence"] == {"status": "not_requested"}
    assert trace_html(result) == trace_html(trace_file(path, "eng", "svc_plc"))


@pytest.mark.parametrize(
    ("source", "service", "destination", "code"),
    [
        ("unknown", "svc_plc", None, "MISSING_REFERENCE"),
        ("eng", "unknown", None, "MISSING_REFERENCE"),
        ("eng", "svc_plc", "unknown", "MISSING_REFERENCE"),
        ("eng", "svc_plc", "eng", "SCOPE_MISMATCH"),
        ("plc", "svc_plc", None, "UNSUPPORTED_QUERY"),
        ("bad id", "svc_plc", None, "INVALID_ID"),
        ("eng", "TCP", None, "INVALID_ID"),
        ("eng", "svc_plc", "<bad>", "INVALID_ID"),
    ],
)
def test_trace_invalid_scope(
    minimal: dict[str, Any], source: str, service: str, destination: str | None, code: str
) -> None:
    with pytest.raises(ModelError) as error:
        trace_bytes(
            yaml.safe_dump(minimal).encode(), source, service, destination_asset_id=destination
        )
    assert error.value.diagnostics[0].code == code


def test_trace_limits_and_no_interface(minimal: dict[str, Any]) -> None:
    data = yaml.safe_dump(minimal).encode()
    for limits in (
        replace(RESOURCE_LIMITS, input_bytes=1),
        replace(RESOURCE_LIMITS, protocol_port_atoms=0),
        replace(RESOURCE_LIMITS, state_edge_visits=0),
        replace(RESOURCE_LIMITS, edge_rule_atom_checks=0),
    ):
        with pytest.raises(ModelError) as error:
            trace_bytes(data, "eng", "svc_plc", limits)
        assert error.value.diagnostics[0].category == "resource_limit"
    minimal["assets"].append({**minimal["assets"][0], "id": "alone"})
    with pytest.raises(ModelError) as error:
        trace_bytes(yaml.safe_dump(minimal).encode(), "alone", "svc_plc")
    assert error.value.diagnostics[0].code == "EMPTY_QUERY_SCOPE"


def test_frontier_and_structure(minimal: dict[str, Any]) -> None:
    def run() -> Any:
        return trace_bytes(yaml.safe_dump(minimal).encode(), "eng", "svc_plc").intervals[0]

    minimal["rules"] = []
    blocked = run()
    assert blocked.diagnostics.reason == "no_permitted_path"
    assert blocked.diagnostics.blocked_edges[0].reason == "missing_permit"
    minimal["rules"] = [
        {
            "id": "deny",
            "edge_ids": ["t_eng_plc"],
            "source": {"all_assets": True},
            "destination": {"all_assets": True},
            "protocol": "tcp",
            "effect": "deny",
            "destination_ports": [{"start": 502, "end": 502}],
        }
    ]
    assert run().diagnostics.blocked_edges[0].reason == "explicit_deny"
    result = trace_bytes(
        yaml.safe_dump(minimal).encode(),
        "eng",
        "svc_plc",
        replace(RESOURCE_LIMITS, diagnostic_edges_per_query=0),
    )
    diagnostic = result.intervals[0].diagnostics
    assert diagnostic and diagnostic.truncated and diagnostic.blocked_edge_count == 1
    assert diagnostic.blocked_edges == ()
    minimal["rules"] = []
    minimal["transport_edges"] = []
    assert run().diagnostics.reason == "no_structural_path"


def test_oracles_detect_deliberate_mutations(minimal: dict[str, Any]) -> None:
    result = trace_bytes(yaml.safe_dump(minimal).encode(), "eng", "svc_plc")
    interval = result.intervals[0]
    with pytest.raises(AssertionError):
        assert (not interval.reachable) == oracle(minimal, "eng", "svc_plc", interval.start)
    witness = interval.witness
    assert witness
    with pytest.raises(AssertionError):
        replay_raw(
            minimal,
            replace(
                witness,
                steps=(
                    replace(witness.steps[0], allow_rule_ids=("fabricated",)),
                    *witness.steps[1:],
                ),
            ),
        )


def test_multiple_frontiers_and_reachable_denied_alternative(minimal: dict[str, Any]) -> None:
    minimal["transport_edges"].append({**minimal["transport_edges"][0], "id": "t_other"})
    minimal["rules"] = []
    data = yaml.safe_dump(minimal).encode()
    result = trace_bytes(
        data, "eng", "svc_plc", replace(RESOURCE_LIMITS, diagnostic_edges_per_query=1)
    )
    diagnostic = result.intervals[0].diagnostics
    assert diagnostic and diagnostic.blocked_edge_count == 2 and diagnostic.truncated
    assert [e.edge_id for e in diagnostic.blocked_edges] == ["t_eng_plc"]
    minimal["rules"] = [
        {
            "id": "deny",
            "edge_ids": ["t_eng_plc"],
            "source": {"all_assets": True},
            "destination": {"all_assets": True},
            "protocol": "tcp",
            "effect": "deny",
            "destination_ports": [{"start": 502, "end": 502}],
        },
        {
            "id": "allow",
            "edge_ids": ["t_other"],
            "source": {"all_assets": True},
            "destination": {"all_assets": True},
            "protocol": "tcp",
            "effect": "allow",
            "destination_ports": [{"start": 502, "end": 502}],
        },
    ]
    reachable = trace_bytes(yaml.safe_dump(minimal).encode(), "eng", "svc_plc").intervals[0]
    assert reachable.reachable and reachable.diagnostics is None
    assert reachable.witness and reachable.witness.steps[0].edge_id == "t_other"
    # Reverse-only declarations provide no inferred reverse path.
    minimal["rules"] = []
    minimal["transport_edges"] = [
        {"id": "reverse", "source_interface_id": "plc_net", "destination_interface_id": "eng_net"}
    ]
    reverse = trace_bytes(yaml.safe_dump(minimal).encode(), "eng", "svc_plc").intervals[0]
    assert reverse.diagnostics and not reverse.diagnostics.structural_path_exists
