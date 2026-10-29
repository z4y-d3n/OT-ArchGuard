"""Independent attachment joins, native replay and hostile rehashing cases."""

import copy
import hashlib
import json
import struct
from pathlib import Path
from typing import Any

import pytest

from otarchguard.capture.observations import analyze_capture
from otarchguard.capture.protocols import enrich_capture, validate_enrichment
from otarchguard.diagnostics import ModelError
from otarchguard.evidence.attachments import (
    build_attachment,
    canonical,
    model_architecture,
    validate_attachment,
)
from otarchguard.evidence.workspace import build_snapshot
from tools.capture_workloads import plant_model

FIXTURES = Path(__file__).parent / "fixtures/capture-contract-v2/supported"


def fixture(name: str) -> dict[str, Any]:
    result = json.loads((FIXTURES / (name + ".json")).read_bytes())
    assert isinstance(result, dict)
    return result


def sealed(value: dict[str, Any], key: str, domain: str = "") -> dict[str, Any]:
    body = {k: v for k, v in value.items() if k != key}
    if domain:
        body = {"domain": domain, "value": body}
    sha = hashlib.sha256(
        json.dumps(body, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode()
    ).hexdigest()
    value[key] = ("attachment-" if key == "attachment_id" else "") + sha
    return value


def captured(tmp_path: Path, source_port: int = 40000) -> tuple[dict[str, Any], dict[str, Any]]:
    # An independently specified Modbus request in Ethernet/IPv4/TCP. No packet
    # construction or decoding code from the product defines these bytes.
    data = bytes.fromhex("000100000006010300000001")
    ethernet = bytes.fromhex("0200000000200200000000100800")
    ipv4 = bytes.fromhex("450000340001000040060000c000020ac0000214")
    tcp = struct.pack("!HHIIBBHHH", source_port, 502, 1, 0, 0x50, 0x18, 1024, 0, 0)
    frame = ethernet + ipv4 + tcp + data
    path = tmp_path / "fictional.pcap"
    path.write_bytes(
        struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1)
        + struct.pack("<IIII", 1700000000, 0, len(frame), len(frame))
        + frame
    )
    return build_snapshot(analyze_capture(path)), enrich_capture(path)


def test_model_uses_native_validation_and_canonical_identity() -> None:
    snapshot = build_snapshot(fixture("observations"))
    model = build_attachment("model", plant_model(), snapshot)
    assert model["component_sha256"] == fixture("mapping")["model_sha256"]
    assert model_architecture(model).sha256 == model["component_sha256"]
    assert "schema_version" in model["payload"]
    validate_attachment(model, snapshot)
    # YAML presentation and comments do not create a different model meaning.
    yaml_source = json.dumps(plant_model()).encode() + b"\n# comment\n"
    assert build_attachment("model", yaml_source, snapshot) == model


def test_complete_mapping_and_comparison_replay_exact_frozen_outputs() -> None:
    snapshot = build_snapshot(fixture("observations"))
    model = build_attachment("model", plant_model(), snapshot)
    mapping = build_attachment("mapping", fixture("mapping"), snapshot, {"model": model})
    comparison = build_attachment(
        "comparison", fixture("comparison"), snapshot, {"model": model, "mapping": mapping}
    )
    assert mapping["component_sha256"] == fixture("comparison")["mapping_sha256"]
    assert comparison["dependencies"] == {
        "model": model["attachment_id"],
        "mapping": mapping["attachment_id"],
    }
    validate_attachment(comparison, snapshot, {"model": model, "mapping": mapping})


@pytest.mark.parametrize("kind", ["mapping", "comparison"])
def test_reviewed_dependencies_cannot_be_absent(kind: str) -> None:
    with pytest.raises(ModelError):
        build_attachment(kind, fixture(kind), build_snapshot(fixture("observations")))


@pytest.mark.parametrize(
    "field", ["capture_sha256", "observations_sha256", "model_sha256", "candidates_sha256"]
)
def test_rehashed_mapping_cannot_rebind_source_facts(field: str) -> None:
    snapshot = build_snapshot(fixture("observations"))
    model = build_attachment("model", plant_model(), snapshot)
    mapping = fixture("mapping")
    mapping[field] = "f" * 64
    with pytest.raises(ModelError):
        build_attachment("mapping", mapping, snapshot, {"model": model})


@pytest.mark.parametrize(
    "mutation",
    ["identity", "candidate", "status", "reviewer", "rationale", "duplicate", "missing", "bool"],
)
def test_mapping_review_constraints_survive_rehashed_import(mutation: str) -> None:
    snapshot = build_snapshot(fixture("observations"))
    model = build_attachment("model", plant_model(), snapshot)
    mapping = fixture("mapping")
    accepted = next(p for p in mapping["proposals"] if p["decision"] == "ACCEPT")
    if mutation == "identity":
        accepted["selected_interface_id"] = "other"
    elif mutation == "candidate":
        accepted["candidates"] = []
    elif mutation == "status":
        accepted["decision"] = "APPROVED"
    elif mutation in {"reviewer", "rationale"}:
        accepted[mutation] = ""
    elif mutation == "duplicate":
        mapping["proposals"].append(mapping["proposals"][0])
    elif mutation == "missing":
        mapping["proposals"].pop()
    else:
        mapping["association_version"] = True
    with pytest.raises(ModelError):
        build_attachment("mapping", mapping, snapshot, {"model": model})


@pytest.mark.parametrize(
    "mutation",
    [
        "classification",
        "finding_reference",
        "association",
        "model",
        "work",
        "absence",
        "version",
        "extra",
    ],
)
def test_comparison_requires_full_native_replay_not_only_hashes(mutation: str) -> None:
    snapshot = build_snapshot(fixture("observations"))
    model = build_attachment("model", plant_model(), snapshot)
    mapping = build_attachment("mapping", fixture("mapping"), snapshot, {"model": model})
    comparison = fixture("comparison")
    if mutation == "classification":
        comparison["findings"][0]["classification"] = "OBSERVED_MODEL_REACHABLE"
        comparison["findings"][0]["reason"] = "Invented success"
    elif mutation == "finding_reference":
        comparison["findings"][0]["flow_id"] = "flow-" + "e" * 64
    elif mutation == "association":
        comparison["association_decisions"] = []
    elif mutation == "model":
        comparison["model_sha256"] = "d" * 64
    elif mutation == "work":
        comparison["work"]["native_query_pairs"] += 1
    elif mutation == "absence":
        comparison["absence_assessment"]["status"] = "complete_sensor_coverage"
    elif mutation == "version":
        comparison["comparison_version"] = True
    else:
        comparison["payload"] = "unreviewed secret"
    with pytest.raises(ModelError):
        build_attachment("comparison", comparison, snapshot, {"model": model, "mapping": mapping})


@pytest.mark.parametrize("decoder", [1, 2])
@pytest.mark.parametrize("observation_bound", [False, True])
def test_enrichment_decoder_contracts_allow_null_and_exact_explicit_join(
    tmp_path: Path, decoder: int, observation_bound: bool
) -> None:
    snapshot, enrichment = captured(tmp_path)
    enrichment["decoder_version"] = decoder
    if decoder == 1:
        enrichment["supported_protocols"] = ["modbus_tcp", "profinet_dcp"]
    if observation_bound:
        enrichment["observations_sha256"] = snapshot["observations_sha256"]
    sealed(enrichment, "enrichment_sha256")
    attachment = build_attachment("enrichment", enrichment, snapshot)
    assert attachment["payload"]["observations_sha256"] == enrichment["observations_sha256"]
    validate_attachment(attachment, snapshot)


@pytest.mark.parametrize(
    "mutation",
    [
        "capture",
        "observations",
        "packets",
        "interface",
        "offset",
        "timestamp",
        "endpoint",
        "port",
        "vlans",
        "status",
        "privacy",
        "bool",
        "digest",
    ],
)
def test_rehashed_enrichment_cannot_join_inconsistent_evidence(
    tmp_path: Path, mutation: str
) -> None:
    snapshot, enrichment = captured(tmp_path)
    record = enrichment["records"][0]
    if mutation == "capture":
        enrichment["capture_sha256"] = "a" * 64
        enrichment["capture"]["sha256"] = enrichment["capture"]["capture_id"] = "a" * 64
    elif mutation == "observations":
        enrichment["observations_sha256"] = "a" * 64
    elif mutation == "packets":
        enrichment["capture"]["packets"] += 1
        enrichment["skipped_packets"]["invented"] = 1
    elif mutation == "interface":
        record["packet"]["interface"] += 1
    elif mutation == "offset":
        record["packet"]["offset"] += 1
    elif mutation == "timestamp":
        record["packet"]["timestamp"]["ticks"] += 1
    elif mutation == "endpoint":
        record["source_ip"] = "192.0.2.11"
    elif mutation == "port":
        record["destination_port"] = 20000
    elif mutation == "vlans":
        record["vlans"] = [100]
    elif mutation == "status":
        record["status"] = "APPROVED"
    elif mutation == "privacy":
        record["fields"]["process_value"] = 123
    elif mutation == "bool":
        enrichment["decoder_version"] = True
    sealed(enrichment, "enrichment_sha256")
    if mutation == "digest":
        enrichment["enrichment_sha256"] = "0" * 64
    with pytest.raises(ModelError):
        build_attachment("enrichment", enrichment, snapshot)


@pytest.mark.parametrize(
    "invalid",
    [{1: "numeric key"}, {"bad": (1, 2)}, {"bad": 1.0}, {"bad": "\ud800"}, {"bad": "x" * 4097}],
)
def test_direct_api_never_silently_coerces_ambiguous_json(invalid: dict[str, Any]) -> None:
    with pytest.raises(ModelError):
        build_attachment("mapping", invalid, build_snapshot(fixture("observations")))


@pytest.mark.parametrize("version", [True, 2, "1", None])
def test_unknown_attachment_versions_rejected_even_after_rehash(version: object) -> None:
    snapshot = build_snapshot(fixture("observations"))
    attachment = build_attachment("model", plant_model(), snapshot)
    attachment["attachment_version"] = version
    sealed(attachment, "attachment_id", "otarchguard.attachment")
    with pytest.raises(ModelError):
        validate_attachment(attachment, snapshot)


def test_stored_payload_rehash_cannot_create_unvalidated_model() -> None:
    snapshot = build_snapshot(fixture("observations"))
    attachment = build_attachment("model", plant_model(), snapshot)
    altered = copy.deepcopy(attachment)
    altered["payload"]["assets"][0]["id"] = "UNKNOWN"
    sealed(altered, "attachment_id", "otarchguard.attachment")
    with pytest.raises(ModelError):
        validate_attachment(altered, snapshot)
    assert canonical(attachment) != canonical(altered)


def test_attachment_payloads_are_not_mutable_aliases(tmp_path: Path) -> None:
    snapshot, enrichment = captured(tmp_path)
    attachment = build_attachment("enrichment", enrichment, snapshot)
    enrichment["records"].clear()
    assert attachment["payload"]["records"]


def test_self_consistent_protocol_cannot_override_default_decoder_precedence(
    tmp_path: Path,
) -> None:
    snapshot, enrichment = captured(tmp_path, source_port=44818)
    record = enrichment["records"][0]
    assert record["protocol"] == "modbus_tcp"
    record.update(
        protocol="ethernet_ip",
        status="PORT_HINT",
        message_category=None,
        fields={},
        recognition_method="PORT_ASSOCIATION",
        reason="NO_APPLICATION_BYTES",
    )
    enrichment["counts"] = {"ethernet_ip:PORT_HINT": 1}
    sealed(enrichment, "enrichment_sha256")
    validate_enrichment(enrichment)
    with pytest.raises(ModelError):
        build_attachment("enrichment", enrichment, snapshot)


def test_structural_size_must_fit_after_outer_headers(tmp_path: Path) -> None:
    snapshot, enrichment = captured(tmp_path)
    enrichment["records"][0]["fields"]["adu_length"] = 30
    sealed(enrichment, "enrichment_sha256")
    validate_enrichment(enrichment)
    with pytest.raises(ModelError):
        build_attachment("enrichment", enrichment, snapshot)
