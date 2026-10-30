"""Independent wire-to-history release checks for hints and split application bytes.

Literal headers below are fictional. Expected categories follow the supported
contract, not generated decoder output. No TCP state is provided to enrichment.
"""

import json
import struct
from pathlib import Path
from typing import Any, cast

import pytest

from otarchguard.capture.observations import analyze_capture
from otarchguard.capture.protocols import enrich_capture
from otarchguard.diagnostics import ModelError
from otarchguard.drift import reports
from otarchguard.evidence import history, lifecycle, revisions


def _json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode() + b"\n"


def _tcp(payload: bytes, port: int, *, sequence: int = 1, syn: bool = False) -> bytes:
    tcp = struct.pack("!HHIIBBHHH", 42000, port, sequence, 0, 0x50, 2 if syn else 24, 1024, 0, 0)
    ip = struct.pack(
        "!BBHHHBBH4s4s",
        0x45,
        0,
        40 + len(payload),
        1,
        0,
        64,
        6,
        0,
        bytes([192, 0, 2, 10]),
        bytes([192, 0, 2, 20]),
    )
    return bytes.fromhex("0200000000200200000000100800") + ip + tcp + payload


def _capture(path: Path, frames: list[bytes]) -> None:
    path.write_bytes(
        struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1)
        + b"".join(
            struct.pack("<IIII", 1700000000, i, len(frame), len(frame)) + frame
            for i, frame in enumerate(frames)
        )
    )


def _analysis(workspace: Path, path: Path, frames: list[bytes]) -> dict[str, Any]:
    _capture(path, frames)
    observed = path.with_suffix(".observations.json")
    observed.write_bytes(_json(analyze_capture(path)))
    sid = history.add_collection(workspace, observed)["snapshot_id"]
    enriched = path.with_suffix(".enrichment.json")
    enriched.write_bytes(_json(enrich_capture(path)))
    aid = lifecycle.import_attachment(workspace, sid, "enrichment", enriched)["attachment"][
        "attachment_id"
    ]
    return cast(
        dict[str, Any], lifecycle.create_revision(workspace, sid, enrichment=aid)["analysis"]
    )


def _compare(workspace: Path, root: Path, reference: str, candidate: str) -> dict[str, Any]:
    scope = {
        "environment": "Fictional finite release audit",
        "purpose": "Metadata boundaries",
        "coverage": "Selected files only; sensor loss unknown",
        "uncertainties": [],
        "vantage_points": ["Fictional asserted sensor"],
        "protocols": ["tcp"],
    }
    scope_path = root / "scope.json"
    scope_path.write_bytes(_json(scope))
    bid = lifecycle.propose_baseline(workspace, scope_path, [reference])["baseline"]["baseline_id"]
    lifecycle.record_review(workspace, bid, "approve", "Fictional reviewer", "Finite bytes only")
    context = {
        "context_version": 1,
        "pairs": [
            {
                "reference_analysis_id": reference,
                "candidate_analysis_id": candidate,
                "candidate_scope": scope,
                "alignment": "asserted",
                "rationale": "Finite audit",
                "native_queries": [],
            }
        ],
    }
    path = root / "report.json"
    report = reports.generate_report(workspace, bid, [candidate], context, path)
    assert reports.verify_report(workspace, path)["canonical_reproduction"] is True
    return report


def test_seven_hints_remain_nonpositive_after_attachment_revision_and_drift(tmp_path: Path) -> None:
    workspace = tmp_path / "history"
    history.initialize_history(workspace)
    ports = [502, 44818, 102, 2404, 4840, 20000]
    # DCP FrameID alone lacks the twelve-byte DCP header. TCP SYNs have no
    # application bytes. Neither form supplies positive structural recognition.
    dcp = bytes.fromhex("0200000000200200000000108892fefd")
    frames = [_tcp(b"", port, syn=True) for port in ports] + [dcp]
    first = _analysis(workspace, tmp_path / "first.pcap", frames)
    second = _analysis(workspace, tmp_path / "second.pcap", frames * 2)
    report = _compare(workspace, tmp_path, first["analysis_id"], second["analysis_id"])
    findings = report["comparisons"][0]["findings"]
    metadata = [
        f
        for f in findings
        if f["category"] == "PROTOCOL_METADATA_DIFFERENCE"
        and f["subtype"] == "RECORD_COUNTS_CHANGED"
    ]
    assert {f["key"]["protocol"] for f in metadata} == {
        "modbus_tcp",
        "ethernet_ip",
        "s7comm",
        "iec104",
        "opcua_binary",
        "dnp3",
        "profinet_dcp",
    }
    assert {f["key"]["status"] for f in metadata} == {"PORT_HINT", "TRUNCATED"}
    assert all(f["key"]["header_metadata"] == {} for f in metadata)
    assert all(f["key"]["message_category"] is None for f in metadata)
    assert all(f["reference"]["record_count"] == 1 for f in metadata)
    assert all(f["candidate"]["record_count"] == 2 for f in metadata)
    assert all(
        any(
            "successful commands" in s or "successful" in s or "success" in s
            for s in f["limitations"]
        )
        for f in metadata
    )


@pytest.mark.parametrize("reverse", [False, True])
def test_split_modbus_tcp_segments_never_reassemble_in_historical_metadata(
    tmp_path: Path,
    reverse: bool,
) -> None:
    workspace = tmp_path / "history"
    history.initialize_history(workspace)
    # Complete MBAP + FC6 ADU; six-byte/tail fragments intentionally have
    # consecutive TCP sequence numbers. Capture order does not grant reassembly.
    adu = bytes.fromhex("0001000000060106cafe1337")
    full = _analysis(workspace, tmp_path / "full.pcap", [_tcp(adu, 502)])
    segments = [_tcp(adu[:6], 502), _tcp(adu[6:], 502, sequence=7)]
    split = _analysis(workspace, tmp_path / "split.pcap", segments[::-1] if reverse else segments)
    enriched = json.loads((tmp_path / "split.enrichment.json").read_bytes())
    assert enriched["counts"] == {"modbus_tcp:TRUNCATED": 2}
    assert all(r["fields"] == {} and r["message_category"] is None for r in enriched["records"])
    report = _compare(workspace, tmp_path, full["analysis_id"], split["analysis_id"])
    findings = [
        f
        for f in report["comparisons"][0]["findings"]
        if f["category"] == "PROTOCOL_METADATA_DIFFERENCE"
        and f["subtype"] == "CANDIDATE_ONLY_METADATA"
    ]
    assert len(findings) == 1
    assert findings[0]["key"]["status"] == "TRUNCATED"
    assert findings[0]["key"]["header_metadata"] == {}
    assert findings[0]["candidate"]["record_count"] == 2
    assert b"cafe1337" not in _json(report).lower()


def test_unknown_init_source_identity_rejects_workspace_without_rewriting_history(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / "history"
    history.initialize_history(workspace)
    analysis = _analysis(workspace, tmp_path / "capture.pcap", [_tcp(b"", 502, syn=True)])
    before = {p.relative_to(workspace): p.read_bytes() for p in workspace.rglob("*") if p.is_file()}
    identities = revisions.implementation_identities()
    changed = dict(identities)
    changed["__init__.py"] = "0" * 64
    assert identities["__init__.py"] != changed["__init__.py"]
    with monkeypatch.context() as patch:
        patch.setattr(revisions, "implementation_identities", lambda: changed)
        with pytest.raises(ModelError) as error:
            lifecycle.load_state(workspace)
        assert error.value.diagnostics[0].code == "EVIDENCE_REVISION"
        # Storage integrity remains independently verifiable. It does not
        # authorize interpretation under an unknown consumer implementation.
        assert history.verify_history(workspace)["status"] == "VERIFIED_OBJECT_INTEGRITY"
    assert lifecycle.load_state(workspace)["analyses"][analysis["analysis_id"]] == analysis
    assert {
        p.relative_to(workspace): p.read_bytes() for p in workspace.rglob("*") if p.is_file()
    } == before
