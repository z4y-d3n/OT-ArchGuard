"""Original literal corpus, independent safe-field oracle and provenance joins."""

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

from otarchguard.capture.protocols import enrich_capture, validate_enrichment
from tools.protocol_corpus import load_manifest, verify_file
from tools.v145_corpus import CAPTURE, DIRECTORY, SPECIFICATION, build, frame, verify

SPEC = json.loads(SPECIFICATION.read_text(encoding="utf-8"))
CASES = SPEC["cases"]
RECEIPT = DIRECTORY / "v145-tshark-receipt.json"


@pytest.fixture(scope="module")
def enrichment() -> dict[str, Any]:
    result = enrich_capture(CAPTURE)
    validate_enrichment(result)
    return result


def _independent_fields(case: dict[str, Any], row: dict[str, str]) -> dict[str, Any]:
    """Translate only selected reference fields, without invoking a product decoder.

    Wireshark exports Modbus exception FC without bit 7; the literal fixture
    separately specifies that bit. IEC APCI type is 0 for I and 1 for S.
    """
    family = case["protocol"]
    if family == "modbus_tcp":
        return {
            "transaction_id": int(row["mbtcp.trans_id"]),
            "function_code": int(row["modbus.func_code"])
            | (128 if case["expected_fields"]["exception_response"] else 0),
        }
    if family == "profinet_dcp":
        return {
            "frame_id": int(row["pn_rt.frame_id"]),
            "service_id": int(row["pn_dcp.service_id"]),
            "service_type": int(row["pn_dcp.service_type"]),
            "data_length": int(row["pn_dcp.data_length"]),
        }
    if family == "ethernet_ip":
        return {
            "encapsulation_command": int(row["enip.command"], 16),
            "cip_service": int(row["cip.service"], 16),
        }
    if family == "s7comm":
        result: dict[str, Any] = {"rosctr": int(row["s7comm.header.rosctr"])}
        if row["s7comm.param.func"]:
            result["function_code"] = int(row["s7comm.param.func"], 16)
        return result
    if family == "iec104":
        result = {"frame_format": {0: "I", 1: "S"}[int(row["iec60870_104.type"], 16)]}
        if row["iec60870_asdu.typeid"]:
            result["asdu_type"] = int(row["iec60870_asdu.typeid"])
        return result
    if family == "opcua_binary":
        return {
            "message_type": row["opcua.transport.type"],
            "chunk_type": row["opcua.transport.chunk"],
            "message_size": int(row["opcua.transport.size"]),
        }
    assert family == "dnp3"
    assert row["dnp3.hdr.CRC.incorrect"] == row["dnp3.data_chunk.CRC.incorrect"] == ""
    return {
        "link_function": int(row["dnp3.ctl.prifunc"]),
        "protocol_source": int(row["dnp3.src"]),
        "protocol_destination": int(row["dnp3.dst"]),
        "application_function": int(row["dnp3.al.func"]),
    }


@pytest.mark.parametrize("index,case", list(enumerate(CASES)), ids=[c["id"] for c in CASES])
def test_literal_wire_classification_and_independent_fields(
    enrichment: dict[str, Any], index: int, case: dict[str, Any]
) -> None:
    record = enrichment["records"][index]
    assert record["protocol"] == case["protocol"]
    assert record["status"] == case["expected_status"]
    assert record["reason"] == case["expected_reason"]
    assert record["message_category"] == case["expected_category"]
    assert record["fields"] == case["expected_fields"]
    assert record["record_offset"] == 0
    assert record["packet"]["index"] == index + 1
    assert record["vlans"] == ([37] if case["protocol"] == "profinet_dcp" else [])
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    row = receipt["packets"][index]
    assert int(row["frame.number"]) == index + 1
    assert int(row["frame.len"]) == record["packet"]["original_length"] == len(frame(case))
    wire = bytes.fromhex(case["wire_hex"])
    assert case["wire_bytes"] == len(wire)
    assert case["wire_sha256"] == hashlib.sha256(wire).hexdigest()
    if case["input_class"] == "supported_positive":
        for key, expected in _independent_fields(case, row).items():
            assert case["expected_fields"][key] == expected
            assert record["fields"][key] == expected
    else:
        assert record["fields"] == {} and record["message_category"] is None


def test_corpus_bytes_and_reference_receipt_identity() -> None:
    data = CAPTURE.read_bytes()
    assert data == build(SPEC)
    assert len(data) == 2460
    assert hashlib.sha256(data).hexdigest() == (
        "9035464f34c6d2b45c528678b1f1d2af87b4d428b6707c395564239bfe0de3c2"
    )
    assert verify()["capture_sha256"] == SPEC["capture_sha256"]
    manifest = load_manifest(DIRECTORY / "manifest.json")
    assert verify_file(manifest, "v145-equivalence", CAPTURE)["sha256"] == SPEC["capture_sha256"]
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    assert receipt["input_sha256"] == SPEC["capture_sha256"]
    assert receipt["input_bytes"] == len(data)
    assert receipt["tool_version"] == "TShark (Wireshark) 4.6.9 (v4.6.9-0-g2d548b197c75)."
    assert receipt["kind"] == "original_synthetic_only"
    assert receipt["stderr"] == ""
    assert len(receipt["packets"]) == len(CASES) == 28
    for preference in (
        "tcp.desegment_tcp_streams:FALSE",
        "enip.desegment:FALSE",
        "dnp3.desegment:FALSE",
    ):
        assert preference in receipt["arguments"]


def test_all_seven_family_denominators_and_order(enrichment: dict[str, Any]) -> None:
    assert len({case["id"] for case in CASES}) == len(CASES)
    expected = Counter(f"{case['protocol']}:{case['expected_status']}" for case in CASES)
    assert len(expected) == 21
    assert enrichment["counts"] == dict(expected)
    assert enrichment["packets_with_records"] == 28
    assert enrichment["skipped_packets"] == {}
    assert enrichment["capture"]["packets"] == 28
    references = [record["packet"] for record in enrichment["records"]]
    assert [reference["index"] for reference in references] == list(range(1, 29))
    assert [reference["offset"] for reference in references] == sorted(
        reference["offset"] for reference in references
    )


def test_hostile_application_strings_are_not_exported(enrichment: dict[str, Any]) -> None:
    assert b"<script>V145_PRIVATE_MARKER</script>" in CAPTURE.read_bytes()
    output = json.dumps(enrichment)
    assert "V145_PRIVATE_MARKER" not in output and "<script>" not in output
    assert "V145_PRIVATE_MARKER" not in RECEIPT.read_text(encoding="utf-8")


def test_original_synthetic_rights_and_expectation_separation() -> None:
    assert SPEC["tier"] == 1
    assert SPEC["redistribution"] == "original"
    assert SPEC["origin"] == "original_fictional_synthetic"
    assert SPEC["license"] == "Apache-2.0"
    assert all(case["expectation_reference"] for case in CASES)
    # The builder can be used without importing any product implementation.
    source = (Path(__file__).resolve().parents[1] / "tools/v145_corpus.py").read_text()
    assert "from otarchguard" not in source and "import otarchguard" not in source
