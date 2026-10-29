"""V14-05 composed wire-to-history trust boundaries, without external captures.

Literal fictional MBAP bytes and independent PCAP packing are the input oracle.
These tests exercise consumer composition rather than treating hashes, parser
recognition or local reviewer text as evidence of operational success.
"""

import copy
import hashlib
import json
import shutil
import struct
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import pytest

from otarchguard.capture.observations import analyze_capture
from otarchguard.capture.protocols import enrich_capture
from otarchguard.capture.protocols.contract import ENRICHMENT_LIMITS
from otarchguard.diagnostics import ModelError
from otarchguard.drift import explorer, explorer_bundle, explorer_render, reports
from otarchguard.drift.engine import compare
from otarchguard.evidence import history, lifecycle


def _json(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("ascii")
        + b"\n"
    )


def _inventory(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def _capture(*, linktype: int = 1, incomplete: bool = False) -> bytes:
    # Two complete FC6 ADUs. Register address/value are deliberately private.
    payload = bytes.fromhex("0001000000060106cafe13370002000000060106cafe1337")
    if incomplete:
        payload = payload[:9]
    tcp = struct.pack("!HHIIBBHHH", 41000, 502, 1, 0, 0x50, 0x18, 1024, 0, 0)
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
    frame = bytes.fromhex("0200000000200200000000100800") + ip + tcp + payload
    # Unsupported containers intentionally retain the same recognizable inner
    # bytes; an implementation must not bypass an unknown link-layer envelope.
    return (
        struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, linktype)
        + struct.pack("<IIII", 1_700_000_000, 1, len(frame), len(frame))
        + frame
    )


@dataclass
class Workflow:
    root: Path
    workspace: Path
    baseline: str
    approval: str
    scope: dict[str, Any]
    revisions: dict[str, dict[str, Any]]
    snapshots: dict[str, str]
    enrichments: dict[str, dict[str, Any]]

    def context(self, name: str) -> dict[str, Any]:
        return {
            "context_version": 1,
            "pairs": [
                {
                    "reference_analysis_id": self.revisions["supported"]["analysis_id"],
                    "candidate_analysis_id": self.revisions[name]["analysis_id"],
                    "candidate_scope": copy.deepcopy(self.scope),
                    "alignment": "asserted",
                    "rationale": "Fictional finite-byte comparison only",
                    "native_queries": [],
                }
            ],
        }

    def report(self, name: str) -> dict[str, Any]:
        return compare(
            self.workspace,
            self.baseline,
            [self.revisions[name]["analysis_id"]],
            self.context(name),
        )


@pytest.fixture(scope="module")
def wire_history(tmp_path_factory: pytest.TempPathFactory) -> Workflow:
    root = tmp_path_factory.mktemp("v145-wire-history")
    workspace = root / "history"
    history.initialize_history(workspace)
    snapshots: dict[str, str] = {}
    revisions: dict[str, dict[str, Any]] = {}
    enrichments: dict[str, dict[str, Any]] = {}
    for name, linktype, incomplete in (
        ("supported", 1, False),
        ("null", 0, False),
        ("sll", 113, False),
        ("unknown", 147, False),
        ("incomplete", 1, True),
    ):
        capture = root / (name + ".pcap")
        capture.write_bytes(_capture(linktype=linktype, incomplete=incomplete))
        observations = root / (name + "-observations.json")
        observations.write_bytes(_json(analyze_capture(capture)))
        sid = history.add_collection(workspace, observations)["snapshot_id"]
        snapshots[name] = sid
        enrichment = enrich_capture(capture)
        enrichments[name] = enrichment
        source = root / (name + "-enrichment.json")
        source.write_bytes(_json(enrichment))
        attachment = lifecycle.import_attachment(workspace, sid, "enrichment", source)
        revisions[name] = lifecycle.create_revision(
            workspace, sid, enrichment=attachment["attachment"]["attachment_id"]
        )["analysis"]
    narrowed = enrich_capture(
        root / "supported.pcap", limits=replace(ENRICHMENT_LIMITS, records_per_packet=1)
    )
    source = root / "narrowed-enrichment.json"
    source.write_bytes(_json(narrowed))
    aid = lifecycle.import_attachment(workspace, snapshots["supported"], "enrichment", source)[
        "attachment"
    ]["attachment_id"]
    enrichments["narrowed"] = narrowed
    snapshots["narrowed"] = snapshots["supported"]
    revisions["narrowed"] = lifecycle.create_revision(
        workspace, snapshots["supported"], enrichment=aid
    )["analysis"]
    scope = {
        "environment": "Fictional V14-05 corpus",
        "purpose": "Wire-to-history boundary verification",
        "coverage": "One fictional packet; loss and sensor authenticity unknown",
        "uncertainties": ["Visibility outside selected bytes is unknown"],
        "vantage_points": ["Unverified fictional sensor assertion"],
        "protocols": ["modbus_tcp"],
    }
    scope_path = root / "scope.json"
    scope_path.write_bytes(_json(scope))
    baseline = lifecycle.propose_baseline(
        workspace, scope_path, [revisions["supported"]["analysis_id"]]
    )["baseline"]["baseline_id"]
    approval = lifecycle.record_review(
        workspace, baseline, "approve", "Fictional reviewer", "Finite invented reference only"
    )["review"]["review_id"]
    return Workflow(root, workspace, baseline, approval, scope, revisions, snapshots, enrichments)


@pytest.fixture
def local_history(wire_history: Workflow, tmp_path: Path) -> Workflow:
    workspace = tmp_path / "history"
    shutil.copytree(wire_history.workspace, workspace)
    return replace(wire_history, workspace=workspace)


def _publish_report(case: Workflow, name: str, path: Path) -> None:
    reports.publish(case.report(name), path, case.workspace)


def test_supported_wire_provenance_and_privacy_survive_all_consumers(
    wire_history: Workflow,
    tmp_path: Path,
) -> None:
    case = wire_history
    capture_sha = hashlib.sha256((case.root / "supported.pcap").read_bytes()).hexdigest()
    enrichment = case.enrichments["supported"]
    assert enrichment["capture_sha256"] == capture_sha
    assert enrichment["counts"] == {"modbus_tcp:STRUCTURALLY_VALID": 2}
    assert [r["record_offset"] for r in enrichment["records"]] == [0, 12]
    assert [r["packet"]["index"] for r in enrichment["records"]] == [1, 1]
    assert all(r["message_category"] == "write_type" for r in enrichment["records"])
    assert all(
        set(r["fields"])
        == {
            "transaction_id",
            "protocol_id",
            "unit_id",
            "function_code",
            "exception_response",
            "adu_length",
        }
        for r in enrichment["records"]
    )
    assert case.revisions["supported"]["capture_sha256"] == capture_sha
    before = _inventory(case.workspace)
    path = tmp_path / "supported.json"
    _publish_report(case, "supported", path)
    site = tmp_path / "site"
    generated = explorer.generate_explorer(case.workspace, path, site)
    verified = explorer.verify_explorer(site, workspace=case.workspace)
    assert generated["source_reproduction"]["canonical_reproduction"] is True
    assert verified["source_reproduction"]["currently_approved_reference"] is True
    assert (site / "report.json").read_bytes() == path.read_bytes()
    assert _inventory(case.workspace) == before
    assert not any(p.suffix in {".pcap", ".pcapng"} for p in site.iterdir())
    assert not any(b"cafe1337" in data.lower() for data in _inventory(site).values())


@pytest.mark.parametrize("name,linktype", [("null", 0), ("sll", 113), ("unknown", 147)])
def test_unsupported_outer_bytes_remain_unassessed_through_historical_html(
    wire_history: Workflow,
    tmp_path: Path,
    name: str,
    linktype: int,
) -> None:
    case = wire_history
    enrichment = case.enrichments[name]
    assert enrichment["records"] == [] and enrichment["counts"] == {}
    assert enrichment["skipped_packets"] == {"LINKTYPE_UNSUPPORTED": 1}
    state = lifecycle.load_state(case.workspace)
    snapshot = state["snapshots"][case.snapshots[name]]
    assert snapshot["observations"]["coverage"]["uninterpreted_packets"] == 1
    assert snapshot["observations"]["capture"]["interfaces"][0]["linktype"] == linktype
    path = tmp_path / (name + ".json")
    _publish_report(case, name, path)
    report = reports.read_report(path)
    dimensions = {
        r["dimension"]: r for r in report["comparisons"][0]["comparability"]["dimensions"]
    }
    assert dimensions["linktypes"]["result"] == "PARTIALLY_COMPARABLE"
    assert dimensions["packet_interpretation"]["result"] == "PARTIALLY_COMPARABLE"
    site = tmp_path / "unsupported-site"
    explorer.generate_explorer(case.workspace, path, site)
    assert explorer.verify_explorer(site, workspace=case.workspace)["analytical_reproduction"]
    html = b"\n".join(p.read_bytes() for p in site.glob("*.html"))
    assert b"LINKTYPE UNSUPPORTED" in html and b"PARTIALLY_COMPARABLE" in html
    assert b"LINKTYPE_UNSUPPORTED" in (site / "report.json").read_bytes()
    assert b"Unsupported linktypes cannot provide negative communication evidence." in html


def test_incomplete_application_metadata_does_not_acquire_positive_fields_in_history(
    wire_history: Workflow,
    tmp_path: Path,
) -> None:
    case = wire_history
    record = case.enrichments["incomplete"]["records"][0]
    assert record["status"] == "TRUNCATED" and record["fields"] == {}
    assert record["message_category"] is None
    path = tmp_path / "incomplete.json"
    _publish_report(case, "incomplete", path)
    report = reports.read_report(path)
    findings = report["comparisons"][0]["findings"]
    candidate_metadata = [
        f
        for f in findings
        if f["category"] == "PROTOCOL_METADATA_DIFFERENCE" and f["candidate"] is not None
    ]
    assert candidate_metadata
    assert any(b"TRUNCATED" in _json(f) for f in candidate_metadata)
    assert reports.verify_report(case.workspace, path)["canonical_reproduction"] is True
    explorer.generate_explorer(case.workspace, path, tmp_path / "incomplete-site")
    assert b"TRUNCATED" in b"".join(
        p.read_bytes() for p in (tmp_path / "incomplete-site").glob("*.html")
    )


def test_same_capture_narrower_limits_change_interpretation_and_withhold_protocol_delta(
    wire_history: Workflow,
    tmp_path: Path,
) -> None:
    case = wire_history
    first, second = (case.revisions[name] for name in ("supported", "narrowed"))
    assert first["capture_sha256"] == second["capture_sha256"]
    assert case.snapshots["supported"] == case.snapshots["narrowed"]
    assert first["analysis_id"] != second["analysis_id"]
    assert case.enrichments["narrowed"]["counts"] == {"modbus_tcp:UNSUPPORTED_VARIANT": 1}
    path = tmp_path / "reinterpretation.json"
    _publish_report(case, "narrowed", path)
    report = reports.read_report(path)
    pair = report["comparisons"][0]
    assert any(f["subtype"] == "PROTOCOL_SEMANTICS_CHANGED" for f in pair["findings"])
    assert not any(f["category"] == "PROTOCOL_METADATA_DIFFERENCE" for f in pair["findings"])
    assert report["summary"]["distinct_physical_collections"] == 1
    assert reports.verify_report(case.workspace, path)["canonical_reproduction"] is True
    site = tmp_path / "reinterpretation-site"
    explorer.generate_explorer(case.workspace, path, site)
    html = b"".join(p.read_bytes() for p in site.glob("*.html"))
    assert b"operational protocol comparison is withheld." in html
    assert b"The same physical collection is selected twice." in html


def test_reinterpreted_revision_can_supersede_but_never_inherit_approval(
    local_history: Workflow,
    tmp_path: Path,
) -> None:
    case = local_history
    path = tmp_path / "before.json"
    _publish_report(case, "narrowed", path)
    original = path.read_bytes()
    site = tmp_path / "before-site"
    explorer.generate_explorer(case.workspace, path, site)
    before = _inventory(site)
    scope_path = tmp_path / "scope.json"
    scope_path.write_bytes(_json(case.scope))
    bid = lifecycle.propose_baseline(
        case.workspace, scope_path, [case.revisions["narrowed"]["analysis_id"]]
    )["baseline"]["baseline_id"]
    assert lifecycle.show_object(case.workspace, "baselines", bid)["status"] == "PROPOSED"
    lifecycle.record_review(
        case.workspace,
        bid,
        "supersede",
        "Fictional reviewer",
        "Explicit alternate interpretation",
        predecessor=case.approval,
    )
    verified = explorer.verify_explorer(site, workspace=case.workspace)
    assert verified["approval_snapshot_changed"] is True
    assert verified["source_reproduction"]["current_baseline_status"] == "SUPERSEDED"
    assert verified["source_reproduction"]["currently_approved_reference"] is False
    assert _inventory(site) == before and path.read_bytes() == original
    with pytest.raises(ModelError):
        case.report("narrowed")


@pytest.mark.parametrize("change", ["review", "unselected_attachment", "selected_snapshot"])
def test_source_changes_after_replay_prevent_completion_even_after_rendering(
    local_history: Workflow,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    change: str,
) -> None:
    case = local_history
    path = tmp_path / "before.json"
    _publish_report(case, "supported", path)
    original = explorer_render.render

    def changed(*args: Any, **kwargs: Any) -> dict[str, bytes]:
        files = original(*args, **kwargs)
        if change == "review":
            lifecycle.record_review(
                case.workspace,
                case.baseline,
                "revoke",
                "Fictional reviewer",
                "Authority changed during rendering",
                predecessor=case.approval,
            )
        elif change == "unselected_attachment":
            aid = case.revisions["sll"]["components"]["enrichment"]["attachment_id"]
            target = case.workspace / "attachments" / (aid + ".json")
            target.write_bytes(target.read_bytes() + b" ")
        else:
            sid = case.snapshots["supported"]
            target = case.workspace / "snapshots" / (sid + ".json")
            target.write_bytes(target.read_bytes() + b" ")
        return files

    monkeypatch.setattr(explorer_render, "render", changed)
    site = tmp_path / "changed-site"
    with pytest.raises(ModelError) as error:
        explorer.generate_explorer(case.workspace, path, site)
    assert error.value.diagnostics[0].code == "EVIDENCE_CHANGED"
    assert not (site / explorer_bundle.MANIFEST).exists()


def test_fresh_source_verification_checks_unselected_dependencies_after_prior_success(
    local_history: Workflow,
    tmp_path: Path,
) -> None:
    case = local_history
    path = tmp_path / "report.json"
    _publish_report(case, "supported", path)
    site = tmp_path / "site"
    explorer.generate_explorer(case.workspace, path, site)
    assert explorer.verify_explorer(site, workspace=case.workspace)["analytical_reproduction"]
    aid = case.revisions["sll"]["components"]["enrichment"]["attachment_id"]
    target = case.workspace / "attachments" / (aid + ".json")
    target.unlink()
    # Portable bytes still have internal integrity; fresh source acquisition must
    # independently reject the now-incomplete *whole* historical inventory.
    assert explorer.verify_explorer(site)["analytical_reproduction"] is False
    with pytest.raises(ModelError):
        explorer.verify_explorer(site, workspace=case.workspace)


def test_cross_capture_enrichment_rejection_publishes_no_attachment_or_revision(
    local_history: Workflow,
) -> None:
    case = local_history
    before = _inventory(case.workspace)
    with pytest.raises(ModelError):
        lifecycle.import_attachment(
            case.workspace,
            case.snapshots["incomplete"],
            "enrichment",
            case.root / "supported-enrichment.json",
        )
    assert _inventory(case.workspace) == before


def test_exact_bundle_byte_ceiling_accepts_and_one_byte_less_rejects_entire_workflow(
    wire_history: Workflow,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = wire_history
    path = tmp_path / "report.json"
    _publish_report(case, "supported", path)
    explorer.generate_explorer(case.workspace, path, tmp_path / "measured")
    expected = _inventory(tmp_path / "measured")
    exact = sum(len(data) for data in expected.values())
    monkeypatch.setattr(
        explorer_bundle, "BUNDLE_LIMITS", replace(explorer_bundle.BUNDLE_LIMITS, total_bytes=exact)
    )
    explorer.generate_explorer(case.workspace, path, tmp_path / "exact")
    assert _inventory(tmp_path / "exact") == expected
    monkeypatch.setattr(
        explorer_bundle,
        "BUNDLE_LIMITS",
        replace(explorer_bundle.BUNDLE_LIMITS, total_bytes=exact - 1),
    )
    with pytest.raises(ModelError) as error:
        explorer.generate_explorer(case.workspace, path, tmp_path / "rejected")
    assert error.value.diagnostics[0].code == "LIMIT_EXCEEDED"
    assert not (tmp_path / "rejected").exists()


def test_rehashed_generation_assertion_does_not_authenticate_current_authority(
    local_history: Workflow,
    tmp_path: Path,
) -> None:
    case = local_history
    path = tmp_path / "report.json"
    _publish_report(case, "supported", path)
    site = tmp_path / "original"
    explorer.generate_explorer(case.workspace, path, site)
    identity = copy.deepcopy(explorer.verify_explorer(site)["identity"])
    receipt = identity["generation_verification"]
    assert receipt["currently_approved_reference"] is True
    lifecycle.record_review(
        case.workspace,
        case.baseline,
        "revoke",
        "Fictional reviewer",
        "Retire reference",
        predecessor=case.approval,
    )
    # A self-consistent third-party bundle can repeat any historical generation
    # assertion. The source-dependent verifier must expose the actual authority.
    files = explorer_render.render(reports.read_report(path), receipt, page_size=50)
    files["report.json"] = path.read_bytes()
    files["verification.json"] = (site / "verification.json").read_bytes()
    forged = tmp_path / "repeated-assertion"
    explorer_bundle.publish(files, identity, forged, before_publish=lambda: None)
    result = explorer.verify_explorer(forged, workspace=case.workspace)
    assert result["generation_authority_authenticated"] is False
    assert result["approval_snapshot_changed"] is True
    assert result["source_reproduction"]["current_baseline_status"] == "REVOKED"
    assert result["source_reproduction"]["currently_approved_reference"] is False
