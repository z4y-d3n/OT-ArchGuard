"""Independent finite reconciliation oracles over hand-written header observations."""

import copy
import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
import yaml

from otarchguard.api import ValidatedArchitecture, validate_bytes
from otarchguard.capture import reconciliation
from otarchguard.capture.contract import CAPTURE_LIMITS
from otarchguard.capture.explorer import generate_site
from otarchguard.capture.observations import analyze_capture
from otarchguard.capture.reconciliation import compare_capture, load_mapping, mapping_template
from otarchguard.diagnostics import ModelError
from tools.capture_workloads import plant_model, write_pcap


def snapshot(minimal: dict[str, Any]) -> ValidatedArchitecture:
    return validate_bytes(yaml.safe_dump(minimal).encode())


def flow(**changes: Any) -> dict[str, Any]:
    return {
        "id": "flow_a",
        "conversation_id": "conversation_a",
        "source_ip": "192.0.2.10",
        "destination_ip": "192.0.2.20",
        "source_port": 40000,
        "destination_port": 502,
        "transport": "tcp",
        "ip_version": 4,
        "status": "decoded",
        "samples": [{"index": 1, "offset": 24, "section": 0, "interface": 0}],
        "initiation_evidence": [{"index": 1, "offset": 24, "section": 0, "interface": 0}],
        **changes,
    }


def observations(*flows: dict[str, Any]) -> dict[str, Any]:
    addresses = sorted(
        {f[field] for f in flows for field in ("source_ip", "destination_ip") if f[field]}
    )
    result = {
        "observation_version": 2,
        "catalog_version": 1,
        "capture": {
            "sha256": "a" * 64,
            "capture_id": "a" * 64,
            "unknown_blocks": 0,
            "limitations": [],
        },
        "hosts": [
            {
                "id": "host_" + str(index),
                "ip": address,
                "ip_version": 6 if ":" in address else 4,
                "source_macs": [],
                "destination_macs": [],
                "packets": 1,
            }
            for index, address in enumerate(addresses)
        ],
        "flows": list(flows),
        "conversations": [],
        "coverage": {"complete_file_scan": True, "uninterpreted_packets": 0},
    }
    seal(result)
    return result


def seal(result: dict[str, Any]) -> None:
    result.pop("observations_sha256", None)
    result["observations_sha256"] = hashlib.sha256(
        json.dumps(result, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode()
    ).hexdigest()


def reviewed(obs: dict[str, Any], model: ValidatedArchitecture) -> dict[str, Any]:
    review = mapping_template(obs, model)
    for proposal in review["proposals"]:
        if proposal["candidates"]:
            candidate = proposal["candidates"][0]
            proposal.update(
                decision="ACCEPT",
                selected_asset_id=candidate["asset_id"],
                selected_interface_id=candidate["interface_id"],
                reviewer="Fictional owner",
                rationale="Reviewed the synthetic fixture identities within this capture scope.",
            )
    return review


def classification(obs: dict[str, Any], model: ValidatedArchitecture) -> str:
    return str(compare_capture(obs, model, reviewed(obs, model))["findings"][0]["classification"])


def test_pending_proposals_never_authorize_identity(minimal: dict[str, Any]) -> None:
    model, obs = snapshot(minimal), observations(flow())
    proposal = mapping_template(obs, model)
    assert all(p["decision"] == "PENDING" for p in proposal["proposals"])
    assert all(p["selected_asset_id"] is None for p in proposal["proposals"])
    result = compare_capture(obs, model, proposal)
    assert result["findings"][0]["classification"] == "OBSERVED_ENDPOINT_UNMAPPED"
    assert result["work"]["native_query_pairs"] == 0


@pytest.mark.parametrize("permitted", [True, False])
def test_native_reachable_and_unreachable_oracle(minimal: dict[str, Any], permitted: bool) -> None:
    if not permitted:
        minimal["rules"] = []
    model, obs = snapshot(minimal), observations(flow())
    result = compare_capture(obs, model, reviewed(obs, model))
    finding = result["findings"][0]
    assert finding["classification"] == (
        "OBSERVED_MODEL_REACHABLE" if permitted else "OBSERVED_MODEL_UNREACHABLE"
    )
    native = finding["native_result"]
    assert native["model_sha256"] == model.sha256
    assert native["observed_destination_port"] == 502
    interval = native["selected_interval"]
    assert interval["reachable"] is permitted
    if permitted:
        assert [step["edge_id"] for step in interval["witness"]["steps"]] == ["t_eng_plc"]
    else:
        assert interval["witness"] is None
        assert interval["diagnostics"]["reason"] == "no_permitted_path"
        assert interval["diagnostics"]["blocked_edges"][0]["reason"] == "missing_permit"
    assert result["declared_services_not_observed"] == []
    assert finding["capture_sha256"] == "a" * 64
    assert finding["samples"] == obs["flows"][0]["samples"]
    assert len(finding["association_decision_ids"]) == 2


@pytest.mark.parametrize(
    "changes,expected",
    [
        ({"destination_port": 8080}, "OBSERVED_SERVICE_UNDECLARED"),
        ({"source_ip": "192.0.2.99"}, "OBSERVED_ENDPOINT_UNMAPPED"),
        ({"initiation_evidence": []}, "OBSERVED_DIRECTION_UNCERTAIN"),
        ({"transport": "udp", "initiation_evidence": []}, "OBSERVED_DIRECTION_UNCERTAIN"),
        ({"ip_version": 6}, "OBSERVED_MODEL_UNSUPPORTED"),
        ({"transport": "arp", "initiation_evidence": []}, "OBSERVED_MODEL_UNSUPPORTED"),
        ({"status": "fragmented"}, "OBSERVED_MODEL_UNSUPPORTED"),
        ({"status": "truncated"}, "OBSERVED_MODEL_UNSUPPORTED"),
    ],
)
def test_uncertainty_is_never_success_or_blocking(
    minimal: dict[str, Any], changes: dict[str, Any], expected: str
) -> None:
    model, obs = snapshot(minimal), observations(flow(**changes))
    result = compare_capture(obs, model, reviewed(obs, model))
    assert result["findings"][0]["classification"] == expected
    assert result["findings"][0]["native_result"] is None
    assert result["work"]["native_query_pairs"] == 0


def test_opposite_syn_is_ambiguous_not_a_session(minimal: dict[str, Any]) -> None:
    model = snapshot(minimal)
    obs = observations(
        flow(),
        flow(
            id="flow_b",
            source_ip="192.0.2.20",
            destination_ip="192.0.2.10",
            source_port=502,
            destination_port=40000,
        ),
    )
    result = compare_capture(obs, model, reviewed(obs, model))
    assert {f["classification"] for f in result["findings"]} == {"OBSERVED_DIRECTION_UNCERTAIN"}
    assert result["work"]["native_query_pairs"] == 0


def test_multihomed_source_is_not_evaluated_from_another_interface(
    minimal: dict[str, Any],
) -> None:
    minimal["interfaces"].append(
        {
            "id": "eng_other",
            "asset_id": "eng",
            "placement_zone_id": "control",
            "ipv4": "198.51.100.10/24",
        }
    )
    model = snapshot(minimal)
    assert classification(observations(flow()), model) == "OBSERVED_MODEL_UNSUPPORTED"


def test_overlapping_services_require_review_not_arbitrary_selection(
    minimal: dict[str, Any],
) -> None:
    minimal["services"].append({**copy.deepcopy(minimal["services"][0]), "id": "svc_overlap"})
    model = snapshot(minimal)
    obs = observations(flow())
    result = compare_capture(obs, model, reviewed(obs, model))
    assert result["findings"][0]["classification"] == "EVIDENCE_AMBIGUOUS"
    assert result["findings"][0]["native_result"] is None


def test_explicit_rejection_is_retained_and_never_resolves_identity(
    minimal: dict[str, Any],
) -> None:
    model, obs = snapshot(minimal), observations(flow())
    review = reviewed(obs, model)
    review["proposals"][0].update(
        decision="REJECT",
        selected_asset_id=None,
        selected_interface_id=None,
        reviewer="Fictional owner",
        rationale="Address reuse cannot be resolved in this fixture.",
    )
    result = compare_capture(obs, model, review)
    assert result["findings"][0]["classification"] == "OBSERVED_ENDPOINT_UNMAPPED"
    assert result["association_decisions"][0]["decision"] == "REJECT"


def test_mac_multiplicity_does_not_assert_ip_ownership(minimal: dict[str, Any]) -> None:
    model, obs = snapshot(minimal), observations(flow())
    for host in obs["hosts"]:
        host["source_macs"] = ["00:11:22:33:44:55", "11:22:33:44:55:66"]
    seal(obs)
    assert classification(obs, model) == "OBSERVED_MODEL_REACHABLE"


def test_absence_is_finite_scope_not_blocking(minimal: dict[str, Any]) -> None:
    model, obs = snapshot(minimal), observations(flow(destination_port=8080))
    result = compare_capture(obs, model, reviewed(obs, model))
    absent = result["declared_services_not_observed"]
    assert [x["service_id"] for x in absent] == ["svc_plc"]
    assert absent[0]["classification"] == "DECLARED_SERVICE_NOT_OBSERVED"
    assert "does not establish blocking" in absent[0]["reason"]


@pytest.mark.parametrize(
    "binding", ["capture_sha256", "model_sha256", "observations_sha256", "candidates_sha256"]
)
def test_stale_bindings_are_rejected(minimal: dict[str, Any], binding: str) -> None:
    model, obs = snapshot(minimal), observations(flow())
    review = reviewed(obs, model)
    review[binding] = "f" * 64
    with pytest.raises(ModelError, match="processing failed"):
        compare_capture(obs, model, review)


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicate",
        "missing",
        "orphan",
        "candidate",
        "selection",
        "rationale",
        "contradiction",
        "extra",
        "boolean_version",
        "unknown_decision",
        "pending_text",
    ],
)
def test_invalid_owner_decisions_fail_closed(minimal: dict[str, Any], mutation: str) -> None:
    model, obs = snapshot(minimal), observations(flow())
    review = reviewed(obs, model)
    first = review["proposals"][0]
    if mutation == "duplicate":
        review["proposals"][1] = copy.deepcopy(first)
    elif mutation == "missing":
        review["proposals"].pop()
    elif mutation == "orphan":
        first["id"] = "orphan"
    elif mutation == "candidate":
        first["candidates"][0]["asset_id"] = "other"
    elif mutation == "selection":
        first["selected_asset_id"] = "other"
    elif mutation == "rationale":
        first["rationale"] = "  "
    elif mutation == "contradiction":
        first["decision"] = "REJECT"
    elif mutation == "extra":
        first["automatic"] = True
    elif mutation == "boolean_version":
        review["association_version"] = True
    elif mutation == "unknown_decision":
        first["decision"] = "AUTO_ACCEPT"
    elif mutation == "pending_text":
        review = mapping_template(obs, model)
        review["proposals"][0]["rationale"] = "Needs review"
    with pytest.raises(ModelError):
        compare_capture(obs, model, review)


@pytest.mark.parametrize(
    "payload",
    [
        b'{"association_version":1,"association_version":1}',
        b'{"x":NaN}',
        b'{"x":Infinity}',
        b"[]",
        b"\xff",
        b'{"x":',
        b'{"x":"\\ud800"}',
        b'{"x":' + b"[" * 33 + b"0" + b"]" * 33 + b"}",
    ],
)
def test_strict_bounded_decision_json(tmp_path: Path, payload: bytes) -> None:
    path = tmp_path / "review.json"
    path.write_bytes(payload)
    with pytest.raises(ModelError):
        load_mapping(path)


def test_mapping_loader_and_determinism(minimal: dict[str, Any], tmp_path: Path) -> None:
    model, obs = snapshot(minimal), observations(flow())
    review = reviewed(obs, model)
    path = tmp_path / "owner review ñ.json"
    path.write_text(json.dumps(review), encoding="utf-8")
    assert load_mapping(path) == review
    before = copy.deepcopy((obs, review, minimal))
    left = compare_capture(obs, model, review)
    right = compare_capture(obs, model, load_mapping(path))
    assert json.dumps(left, sort_keys=True) == json.dumps(right, sort_keys=True)
    assert (obs, review, minimal) == before
    review["proposals"].reverse()
    # Review order is canonical evidence identity, even if proposal lookup is order-independent.
    assert compare_capture(obs, model, review)["mapping_sha256"] != left["mapping_sha256"]


def test_changed_observation_contents_invalidate_review(minimal: dict[str, Any]) -> None:
    model, obs = snapshot(minimal), observations(flow())
    review = reviewed(obs, model)
    obs["flows"][0]["destination_port"] = 8080
    with pytest.raises(ModelError):
        compare_capture(obs, model, review)
    seal(obs)
    with pytest.raises(ModelError):
        compare_capture(obs, model, review)


@pytest.mark.parametrize("version", [True, 1.0, 3, "1"])
@pytest.mark.parametrize("field", ["observation_version", "catalog_version"])
def test_observation_version_types_are_exact(
    minimal: dict[str, Any], field: str, version: Any
) -> None:
    model, obs = snapshot(minimal), observations(flow())
    obs[field] = version
    seal(obs)
    with pytest.raises(ModelError):
        mapping_template(obs, model)


@pytest.mark.parametrize("incomplete", ["scan", "packets", "blocks", "snapshot"])
def test_incomplete_interpretation_suppresses_absence_findings(
    minimal: dict[str, Any], incomplete: str
) -> None:
    model, obs = snapshot(minimal), observations(flow(destination_port=8080))
    if incomplete == "scan":
        obs["coverage"]["complete_file_scan"] = False
    elif incomplete == "packets":
        obs["coverage"]["uninterpreted_packets"] = 1
    elif incomplete == "blocks":
        obs["capture"]["unknown_blocks"] = 1
    else:
        obs["capture"]["limitations"] = ["SNAPSHOT_TRUNCATED_PACKETS_PRESENT"]
    seal(obs)
    result = compare_capture(obs, model, reviewed(obs, model))
    assert result["declared_services_not_observed"] == []
    assert result["absence_assessment"]["status"] == "suppressed"
    assert any("suppressed" in limitation for limitation in result["limitations"])


def test_long_valid_owner_review_renders_with_aggregate_json(
    tmp_path: Path,
) -> None:
    capture = tmp_path / "synthetic.pcap"
    write_pcap(capture)
    obs = analyze_capture(capture)
    model = snapshot(plant_model())
    review = reviewed(obs, model)
    for proposal in review["proposals"]:
        if proposal["decision"] == "ACCEPT":
            proposal["rationale"] = "X" * 4096
    comparison = compare_capture(obs, model, review)
    result = generate_site(obs, tmp_path / "long-review-site", comparison)
    assert result["audit"]["broken_links"] == 0
    assert "X" * 4096 in (tmp_path / "long-review-site" / "associations.html").read_text()


@pytest.mark.parametrize("path", [r"\\server\share\review.json", "//server/share/review.json"])
def test_mapping_rejects_network_paths_before_filesystem_access(
    path: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    def touched_filesystem(self: Path) -> bool:
        raise AssertionError("Network path reached filesystem inspection")

    monkeypatch.setattr(Path, "is_symlink", touched_filesystem)
    with pytest.raises(ModelError):
        load_mapping(Path(path))


def test_mapping_rejects_junction_ancestors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "review.json"
    path.write_text("{}")

    def junction(self: Path) -> bool:
        return self == tmp_path

    monkeypatch.setattr(Path, "is_junction", junction)
    with pytest.raises(ModelError):
        load_mapping(path)


@pytest.mark.parametrize("dimension", ["queries", "comparison_work", "decisions"])
def test_comparison_budgets_abort_instead_of_publishing_partial(
    minimal: dict[str, Any], dimension: str
) -> None:
    model, obs = snapshot(minimal), observations(flow())
    limits = replace(CAPTURE_LIMITS, **{dimension: 0})
    with pytest.raises(ModelError) as caught:
        compare_capture(obs, model, reviewed(obs, model), limits)
    assert caught.value.diagnostics[0].category == "resource_limit"


def test_native_query_serialization_is_shared_across_observed_five_tuples(
    minimal: dict[str, Any],
) -> None:
    model = snapshot(minimal)
    obs = observations(
        flow(),
        flow(id="flow_b", conversation_id="conversation_b", source_port=40001),
    )
    result = compare_capture(obs, model, reviewed(obs, model))
    first, second = (finding["native_result"] for finding in result["findings"])
    assert first["query"] is second["query"]
    assert first["selected_interval"] is second["selected_interval"]
    assert first["selected_interval"] is first["query"]["intervals"][0]
    assert result["work"]["native_query_pairs"] == 1


def test_native_allocation_budget_is_checked_before_dataclass_expansion(
    minimal: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    model, obs = snapshot(minimal), observations(flow())

    def forbidden_expansion(value: object) -> dict[str, Any]:
        raise AssertionError("Native dataclass expanded before allocation preflight")

    monkeypatch.setattr(reconciliation, "asdict", forbidden_expansion)
    with pytest.raises(ModelError) as caught:
        compare_capture(
            obs, model, reviewed(obs, model), replace(CAPTURE_LIMITS, aggregation_bytes=1024)
        )
    assert "capture_native_evidence_bytes" in caught.value.diagnostics[0].message


def test_repeated_native_query_output_cannot_amplify_past_budget(minimal: dict[str, Any]) -> None:
    model = snapshot(minimal)
    obs = observations(
        *(
            flow(id=f"flow_{i}", conversation_id=f"conversation_{i}", source_port=40000 + i)
            for i in range(100)
        )
    )
    source_bytes = len(json.dumps(obs, sort_keys=True, ensure_ascii=True).encode())
    with pytest.raises(ModelError) as caught:
        compare_capture(
            obs,
            model,
            reviewed(obs, model),
            replace(CAPTURE_LIMITS, output_bytes=source_bytes * 2),
        )
    assert "capture_native_output_bytes" in caught.value.diagnostics[0].message
