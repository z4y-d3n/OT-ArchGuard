"""Independent cross-protocol artifact, provenance, privacy and rejection tests."""

import copy
import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from otarchguard.capture.observations import analyze_capture
from otarchguard.capture.protocols import (
    ENRICHMENT_LIMITS,
    SUPPORTED_PROTOCOLS,
    ProtocolView,
    Status,
    decode,
    digest,
    enrich_capture,
    validate_enrichment,
)
from otarchguard.cli import app
from otarchguard.diagnostics import ModelError
from tools.protocol_workloads import TCP_MESSAGES, capture, seven_frames, tcp_frame


def report(tmp_path: Path) -> dict[str, Any]:
    return enrich_capture(capture(tmp_path / "seven.pcap", seven_frames()))


def rehash(value: dict[str, Any]) -> None:
    value["enrichment_sha256"] = digest(
        {k: v for k, v in value.items() if k != "enrichment_sha256"}
    )


def test_seven_protocols_complete_capture_exact_provenance_and_frozen_observations(
    tmp_path: Path,
) -> None:
    path = capture(tmp_path / "seven.pcap", seven_frames())
    before = analyze_capture(path)
    original = path.read_bytes()
    first = enrich_capture(path)
    validate_enrichment(first)
    assert first == enrich_capture(path)
    assert first["decoder_version"] == 2 and first["enrichment_version"] == 1
    assert set(first["supported_protocols"]) == set(SUPPORTED_PROTOCOLS)
    assert {r["protocol"] for r in first["records"]} == set(SUPPORTED_PROTOCOLS)
    assert all(r["status"] == "STRUCTURALLY_VALID" for r in first["records"])
    assert [r["packet"]["index"] for r in first["records"]] == list(range(1, 8))
    assert first["capture_sha256"] == hashlib.sha256(original).hexdigest()
    assert first["packets_with_records"] == 7 and first["skipped_packets"] == {}
    assert before == analyze_capture(path) and path.read_bytes() == original


@pytest.mark.parametrize("protocol,port,payload", TCP_MESSAGES)
def test_cross_protocol_ports_never_create_false_structural_positive(
    protocol: str, port: int, payload: bytes
) -> None:
    for other, other_port, _ in TCP_MESSAGES:
        if other == protocol:
            continue
        records = decode(ProtocolView(payload, "tcp", 42000, other_port))
        assert not any(r.status == Status.STRUCTURALLY_VALID for r in records)
    assert decode(ProtocolView(payload, "tcp", 42000, 42001)) == ()
    assert decode(ProtocolView(payload, "tcp", port, 42000))[0].protocol == protocol


@pytest.mark.parametrize("protocol,port,payload", TCP_MESSAGES)
@pytest.mark.parametrize("mode", ["fragmented", "capture_truncated", "linktype"])
def test_outer_rejection_preserves_abstention(
    protocol: str, port: int, payload: bytes, mode: str, tmp_path: Path
) -> None:
    path = capture(
        tmp_path / "outer.pcap",
        [tcp_frame(payload, port, fragments=0x2000 if mode == "fragmented" else 0)],
        linktype=147 if mode == "linktype" else 1,
        truncate=mode == "capture_truncated",
    )
    value = enrich_capture(path)
    validate_enrichment(value)
    assert value["records"] == [] and value["packets_with_records"] == 0
    assert sum(value["skipped_packets"].values()) == 1


@pytest.mark.parametrize("index", range(7))
@pytest.mark.parametrize("mutation", ["payload", "category", "bool", "version"])
def test_rehashed_unsafe_metadata_fails_closed(index: int, mutation: str, tmp_path: Path) -> None:
    value = report(tmp_path)
    item = value["records"][index]
    if mutation == "payload":
        item["fields"]["raw_payload"] = "SECRET"
    elif mutation == "category":
        item["message_category"] = "executed_write"
    elif mutation == "bool":
        numeric = next(k for k, v in item["fields"].items() if type(v) is int)
        item["fields"][numeric] = True
    else:
        value["decoder_version"] = 1
    rehash(value)
    with pytest.raises(ValueError):
        validate_enrichment(value)


def test_legacy_decoder_one_artifact_still_consumable_and_new_protocols_rejected(
    tmp_path: Path,
) -> None:
    value = report(tmp_path)
    legacy = copy.deepcopy(value)
    legacy["decoder_version"] = 1
    legacy["supported_protocols"] = ["modbus_tcp", "profinet_dcp"]
    legacy["records"] = [legacy["records"][0], legacy["records"][6]]
    legacy["counts"] = {"modbus_tcp:STRUCTURALLY_VALID": 1, "profinet_dcp:STRUCTURALLY_VALID": 1}
    legacy["packets_with_records"] = 2
    legacy["skipped_packets"] = {"NO_SUPPORTED_PROTOCOL_CANDIDATE": 5}
    rehash(legacy)
    validate_enrichment(legacy)
    legacy["records"][0] = value["records"][1]
    rehash(legacy)
    with pytest.raises(ValueError):
        validate_enrichment(legacy)


def test_aggregate_limit_failure_never_publishes_partial_cli_artifact(tmp_path: Path) -> None:
    path = capture(tmp_path / "many.pcap", seven_frames())
    with pytest.raises(ModelError):
        enrich_capture(path, limits=replace(ENRICHMENT_LIMITS, records=6))
    # CLI's own fatal parse path also publishes neither stdout nor destination.
    bad = tmp_path / "bad.pcap"
    bad.write_bytes(path.read_bytes()[:-1])
    output = tmp_path / "forbidden.json"
    result = CliRunner().invoke(app, ["capture", "enrich", str(bad), "--output", str(output)])
    assert result.exit_code == 2 and not result.stdout and not output.exists()


def test_safe_output_has_only_header_scalars_and_no_approval(tmp_path: Path) -> None:
    value = report(tmp_path)
    for item in value["records"]:
        assert all(type(v) in {str, bool, int} for v in item["fields"].values())
        assert not {"payload", "approved", "owner", "authorization"} & item.keys()
    assert "PRIVATE!" not in json.dumps(value)
