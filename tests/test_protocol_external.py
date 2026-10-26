"""Offline verification of reviewed external references and acquisition boundaries.

No test requires network, TShark, or third-party capture bytes. The committed
receipts are execution evidence; they do not manufacture fresh interoperability.
"""

import copy
import hashlib
import json
import struct
import urllib.request
from pathlib import Path
from typing import Any

import pytest

from tools import protocol_external
from tools.protocol_corpus import load_manifest

CORPUS = Path(__file__).parent / "fixtures" / "protocol-corpus"


def _reviewed() -> dict[str, Any]:
    return load_manifest(CORPUS / "manifest.json")


def test_reviewed_external_bytes_have_exact_independent_reference_joins() -> None:
    manifest = _reviewed()
    external = {
        e["original_filename"]: e
        for e in manifest["entries"]
        if e["review_status"] == "approved_external"
    }
    reference = json.loads((CORPUS / "external-tshark-receipts.json").read_text())
    product = json.loads((CORPUS / "external-product-receipts.json").read_text())
    assert reference["receipt_version"] == product["receipt_version"] == 1
    assert len(external) == len(reference["captures"]) == len(product["captures"]) == 8
    for receipt in reference["captures"] + product["captures"]:
        entry = external[receipt["filename"]]
        assert receipt.get("input_sha256", receipt.get("sha256")) == entry["sha256"]
        assert receipt["size_bytes"] == entry["size_bytes"]
        assert receipt["tool_version"].startswith("TShark (Wireshark) 4.6.7")
        assert entry["tier"] == 3
        assert entry["redistribution"] == "unknown"
        assert entry["sensitivity_review"] == "reviewed"


def test_actual_positive_and_unsupported_receipts_stay_distinct() -> None:
    product = json.loads((CORPUS / "external-product-receipts.json").read_text())
    captures = product["captures"]
    assert sum(c["positive_records"] for c in captures) == 615
    assert sum(c["selected_field_comparisons"] for c in captures) == 2194
    assert all(c["mismatches"] == [] for c in captures)
    assert sum(c["status"] == "FIELDS_MATCH" for c in captures) == 5
    unsupported = [c for c in captures if c["status"] == "UNSUPPORTED_OUTER_LINKTYPE"]
    assert len(unsupported) == 3
    assert all(
        c["positive_records"] == 0 and c["product_skipped"]["LINKTYPE_UNSUPPORTED"] > 0
        for c in unsupported
    )
    opc = next(c for c in captures if c["filename"] == "opcua_with-gap_with-handshake.pcap")
    assert opc["product_counts"]["opcua_binary:TRUNCATED"] == 3
    dnp = next(c for c in captures if c["filename"] == "dnp3_example.pcap")
    assert dnp["product_counts"]["dnp3:UNSUPPORTED_VARIANT"] == 469


def test_reference_receipts_are_bounded_and_never_export_application_values() -> None:
    receipts = json.loads((CORPUS / "external-tshark-receipts.json").read_text())
    permitted = {
        "frame.number",
        "frame.protocols",
        "tcp.len",
        "enip.command",
        "cip.service",
        "s7comm.header.rosctr",
        "s7comm.param.func",
        "opcua.transport.type",
        "opcua.transport.chunk",
        "opcua.transport.size",
        "dnp3.ctl.prifunc",
        "dnp3.ctl.secfunc",
        "dnp3.src",
        "dnp3.dst",
        "dnp3.al.func",
        "dnp3.hdr.CRC.incorrect",
        "dnp3.data_chunk.CRC.incorrect",
    }
    for receipt in receipts["captures"]:
        assert set(receipt["fields"]) == permitted
        assert len(receipt["positive_examples"]) <= 16
        assert len(receipt["negative_examples"]) <= 8
        assert "tcp.desegment_tcp_streams:FALSE" in receipt["arguments"]
        for row in receipt["positive_examples"] + receipt["negative_examples"]:
            assert set(row) == permitted
            assert max(map(len, row.values())) < 512


def test_allowlist_is_exactly_the_reviewed_manifest_subset() -> None:
    entries = [e for e in _reviewed()["entries"] if e["review_status"] == "approved_external"]
    assert set(protocol_external.REVIEWED) == {e["id"] for e in entries}
    assert protocol_external._entries(_reviewed(), [e["id"] for e in entries]) == entries


def test_acquisition_needs_opt_in_before_any_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden(*args: Any) -> bytes:
        pytest.fail("Network must not be attempted")

    monkeypatch.setattr(protocol_external, "_fetch", forbidden)
    with pytest.raises(ValueError, match="allow-network"):
        protocol_external.acquire(_reviewed(), ["cisa-snap7"], tmp_path)


@pytest.mark.parametrize(
    "identities",
    [[], ["cisa-snap7"] * 2, ["absent"], ["wireshark-dcp-candidate"], ["cisa-snap7"] * 9],
)
def test_acquisition_rejects_unapproved_or_unbounded_selection(
    tmp_path: Path, identities: list[str]
) -> None:
    with pytest.raises(ValueError):
        protocol_external.acquire(_reviewed(), identities, tmp_path, allow_network=True)


@pytest.mark.parametrize(
    "field,value",
    [("source_url", "https://example.com/unknown.pcap"), ("sha256", "a" * 64), ("size_bytes", 1)],
)
def test_manifest_mutation_cannot_authorize_a_new_download(
    tmp_path: Path, field: str, value: Any
) -> None:
    manifest = copy.deepcopy(_reviewed())
    next(e for e in manifest["entries"] if e["id"] == "cisa-snap7")[field] = value
    with pytest.raises(ValueError, match="allowlist"):
        protocol_external.acquire(manifest, ["cisa-snap7"], tmp_path, allow_network=True)


def test_existing_capture_is_preserved_before_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "snap7.pcap"
    target.write_bytes(b"original local evidence")

    def forbidden(*args: Any) -> bytes:
        pytest.fail("Existing destinations must be checked before network")

    monkeypatch.setattr(protocol_external, "_fetch", forbidden)
    with pytest.raises(ValueError, match="overwrite"):
        protocol_external.acquire(_reviewed(), ["cisa-snap7"], tmp_path, allow_network=True)
    assert target.read_bytes() == b"original local evidence"


def test_wrong_hash_does_not_publish_partial_capture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(protocol_external, "_fetch", lambda url, size: b"wrong bytes")
    with pytest.raises(ValueError, match="SHA-256"):
        protocol_external.acquire(_reviewed(), ["cisa-snap7"], tmp_path, allow_network=True)
    assert list(tmp_path.iterdir()) == []


def test_success_uses_no_replace_publication_and_removes_staging(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A separate original empty PCAP exercises the publisher without copying any
    # external bytes. The test-only allowlist is explicit and hash-pinned.
    data = struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1)
    manifest = copy.deepcopy(_reviewed())
    entry = next(e for e in manifest["entries"] if e["id"] == "cisa-snap7")
    entry.update(sha256=hashlib.sha256(data).hexdigest(), size_bytes=len(data))
    monkeypatch.setitem(
        protocol_external.REVIEWED, entry["id"], (entry["source_url"], entry["sha256"], len(data))
    )
    monkeypatch.setattr(protocol_external, "_fetch", lambda url, size: data)
    result = protocol_external.acquire(manifest, [entry["id"]], tmp_path, allow_network=True)
    assert result[0]["status"] == "integrity_verified"
    assert result[0]["redistribution"] == "unknown"
    assert (tmp_path / "snap7.pcap").read_bytes() == data
    assert len(list(tmp_path.iterdir())) == 1


def test_redirects_fail_closed() -> None:
    with pytest.raises(ValueError, match="redirects"):
        protocol_external._NoRedirect().redirect_request(
            urllib.request.Request("https://raw.githubusercontent.com/file"),
            None,
            302,
            "redirect",
            {},
            "https://unreviewed.example/file",
        )
