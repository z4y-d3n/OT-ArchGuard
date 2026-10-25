"""Adversarial rehashed evidence must retain structural provenance, not just hashes."""

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from tools.read_capture_evidence import digest, load_bundle, read_json, validate_observations

FIXTURES = Path(__file__).parent / "fixtures/capture-contract-v2"


def bundle() -> dict[str, Any]:
    return {
        name: json.loads((FIXTURES / "supported" / (name + ".json")).read_bytes())
        for name in ("observations", "mapping", "comparison")
    }


def publish(directory: Path, value: dict[str, Any]) -> Path:
    """Update all outer integrity bindings so the structural check is exercised."""
    obs, mapping, comparison = (value[k] for k in ("observations", "mapping", "comparison"))
    obs["observations_sha256"] = digest(
        {k: v for k, v in obs.items() if k != "observations_sha256"}
    )
    mapping["observations_sha256"] = comparison["observations_sha256"] = obs["observations_sha256"]
    decisions = {"decision", "selected_asset_id", "selected_interface_id", "reviewer", "rationale"}
    id_changes = {}
    cores = []
    for proposal in mapping["proposals"]:
        core = {k: v for k, v in proposal.items() if k not in decisions and k != "id"}
        previous_id = proposal["id"]
        proposal["id"] = "association_" + digest(core)
        id_changes[previous_id] = proposal["id"]
        cores.append({"id": proposal["id"], **core})
    mapping["candidates_sha256"] = digest(cores)
    comparison["association_decisions"] = copy.deepcopy(mapping["proposals"])
    for finding in comparison["findings"]:
        finding["association_decision_ids"] = [
            id_changes.get(identity, identity) for identity in finding["association_decision_ids"]
        ]
    comparison["mapping_sha256"] = digest(mapping)
    for name, document in value.items():
        (directory / (name + ".json")).write_text(json.dumps(document), encoding="utf-8")
    return directory


@pytest.mark.parametrize("mutation", ["wrong_ip", "duplicate_host", "missing_host"])
def test_rehashed_mapping_must_partition_hosts_and_match_addresses(
    tmp_path: Path, mutation: str
) -> None:
    value = bundle()
    proposals = value["mapping"]["proposals"]
    if mutation == "wrong_ip":
        proposals[0]["observed_ip"] = "198.51.100.99"
    elif mutation == "duplicate_host":
        proposals[1]["host_id"] = proposals[0]["host_id"]
    else:
        proposals.pop()
    with pytest.raises(ValueError, match="Association (address|host partition)"):
        load_bundle(publish(tmp_path, value))


def test_rehashed_finding_cannot_reference_another_flows_packet_samples(tmp_path: Path) -> None:
    value = bundle()
    findings = value["comparison"]["findings"]
    first = findings[0]
    other = next(f for f in findings if f["samples"] != first["samples"])
    first["samples"] = copy.deepcopy(other["samples"])
    with pytest.raises(ValueError, match="sample provenance"):
        load_bundle(publish(tmp_path, value))


def test_existing_but_unrelated_owner_decision_is_not_valid_endpoint_provenance(
    tmp_path: Path,
) -> None:
    value = bundle()
    finding = next(f for f in value["comparison"]["findings"] if f["association_decision_ids"])
    unrelated = next(
        p["id"]
        for p in value["mapping"]["proposals"]
        if p["id"] not in finding["association_decision_ids"]
    )
    finding["association_decision_ids"] = [unrelated]
    with pytest.raises(ValueError, match="endpoint decision"):
        load_bundle(publish(tmp_path, value))


@pytest.mark.parametrize(
    "field,value",
    [
        ("captured_length", -1),
        ("original_length", 0),
        ("captured_length", 262145),
        ("original_length", True),
    ],
)
def test_packet_sample_length_constraints_survive_rehashing(
    tmp_path: Path, field: str, value: object
) -> None:
    documents = bundle()
    sample = documents["observations"]["flows"][0]["samples"][0]
    sample[field] = value
    with pytest.raises(ValueError, match="packet lengths"):
        load_bundle(publish(tmp_path, documents))


@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("opcode", True, "opcode"),
        ("operation", "reply", "operation/opcode"),
        ("ethernet_delivery", "unicast", "delivery"),
        ("ethernet_source_mac", "02:00:00:00:00:99", "Ethernet observation"),
        ("target_hardware_address", "invalid", "hardware field"),
        ("sender_protocol_address", "192.0.2.99", "legacy field"),
    ],
)
def test_arp_structural_semantics_survive_rehashing(
    tmp_path: Path, field: str, value: object, reason: str
) -> None:
    documents = bundle()
    flow = next(f for f in documents["observations"]["flows"] if f["arp"])
    flow["arp"][field] = value
    with pytest.raises(ValueError, match=reason):
        load_bundle(publish(tmp_path, documents))


def test_host_cannot_be_added_solely_from_an_arp_target_reference(tmp_path: Path) -> None:
    value = bundle()
    # A provenance role invented on an otherwise valid host is not supported by
    # any observed packet, even after the observation checksum is recomputed.
    value["observations"]["hosts"][0]["observation_roles"] = ["arp_target"]
    with pytest.raises(ValueError, match="Host provenance"):
        load_bundle(publish(tmp_path, value))


@pytest.mark.parametrize("field", ["hosts", "flows", "conversations", "coverage", "capture"])
def test_wrong_observation_container_types_raise_value_error(field: str) -> None:
    observations = bundle()["observations"]
    observations[field] = None
    observations["observations_sha256"] = digest(
        {k: v for k, v in observations.items() if k != "observations_sha256"}
    )
    with pytest.raises(ValueError):
        validate_observations(observations)


def test_unknown_optional_fields_and_classifications_remain_available(tmp_path: Path) -> None:
    value = bundle()
    value["observations"]["future_optional"] = {"example": "preserve"}
    value["comparison"]["findings"][0]["classification"] = "FUTURE_CLASSIFICATION"
    actual = load_bundle(publish(tmp_path, value))
    assert actual["observations"]["future_optional"] == {"example": "preserve"}
    assert actual["comparison"]["findings"][0]["classification"] == "FUTURE_CLASSIFICATION"


@pytest.mark.parametrize(
    "path", [r"\\server\share\observations.json", "//server/share/observations.json"]
)
def test_network_path_rejected_before_any_filesystem_access(
    path: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden(self: Path) -> bool:
        raise AssertionError("Network path reached filesystem inspection")

    monkeypatch.setattr(Path, "is_symlink", forbidden)
    with pytest.raises(ValueError, match="Network filesystem"):
        read_json(Path(path))


@pytest.mark.parametrize("kind", ["is_symlink", "is_junction"])
def test_linked_parent_rejected_before_file_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    path = tmp_path / "observations.json"
    path.write_text("{}", encoding="utf-8")

    def linked(self: Path) -> bool:
        return self == tmp_path

    monkeypatch.setattr(Path, kind, linked)
    with pytest.raises(ValueError, match="Linked evidence"):
        read_json(path)


def test_directory_is_not_treated_as_regular_evidence(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="regular local file"):
        read_json(tmp_path)
