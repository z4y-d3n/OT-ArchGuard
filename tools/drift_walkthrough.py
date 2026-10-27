"""Reproduce a fictional, offline historical comparison from installed APIs.

All packets, models and reviewer assertions are invented. This demonstration
opens no sockets, retains no external capture, and confers no operational trust.
"""

import argparse
import copy
import hashlib
import ipaddress
import json
import struct
from pathlib import Path
from typing import Any

from otarchguard.api import validate_file
from otarchguard.capture.observations import analyze_capture
from otarchguard.capture.protocols import enrich_capture
from otarchguard.capture.reconciliation import compare_capture, mapping_template
from otarchguard.diagnostics import ModelError
from otarchguard.evidence import lifecycle
from otarchguard.evidence.history import add_collection, initialize_history


def canonical(value: object) -> bytes:
    """Independent JSON spelling used by the demonstration's identity oracle."""
    return json.dumps(
        value, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False
    ).encode("ascii")


def _write(path: Path, value: object) -> None:
    path.write_bytes(canonical(value) + b"\n")


def fictional_model(*, candidate: bool = False) -> dict[str, Any]:
    """A single invented segment and three explicitly declared endpoint assets."""
    addresses = {"eng": "192.0.2.10", "hmi": "192.0.2.11", "plc": "192.0.2.20"}
    model: dict[str, Any] = {
        "schema_version": 1,
        "architecture_id": "fictional_drift_laboratory",
        "revision": "candidate" if candidate else "reference",
        "suc": {
            "id": "laboratory",
            "name": "Fictional historical comparison",
            "purpose": "Reproducible offline teaching evidence",
            "controlled_process": "No real industrial process",
            "boundary_description": "One declared laboratory segment",
            "completeness_assertion": "Fictional inventory only",
            "access_points": [],
            "external_dependencies": [],
        },
        "zones": [
            {
                "id": "control",
                "name": "Control",
                "purpose": "Invented supervision",
                "scope": "internal",
                "grouping_rationale": "Teaching example",
                "safety_designation": "non_safety",
            }
        ],
        "assets": [
            {
                "id": name,
                "name": name,
                "role": name,
                "zone_id": "control",
                "kind": "endpoint",
                "scope": "internal",
                "domain_classification": "iacs",
                "safety_classification": "non_safety",
                "criticality": "medium",
            }
            for name in addresses
        ],
        "interfaces": [
            {
                "id": name + "_net",
                "asset_id": name,
                "placement_zone_id": "control",
                "ipv4": address + "/24",
            }
            for name, address in addresses.items()
        ],
        "conduits": [],
        "transport_edges": [
            {
                "id": name + "_plc",
                "source_interface_id": name + "_net",
                "destination_interface_id": "plc_net",
            }
            for name in ("eng", "hmi")
        ],
        "forwarding_edges": [],
        "services": [
            {
                "id": "svc_plc",
                "asset_id": "plc",
                "interface_id": "plc_net",
                "protocol": "tcp",
                "destination_ports": [{"start": 502, "end": 502}],
            }
        ],
        "rules": [
            {
                "id": "allow_" + name,
                "edge_ids": [name + "_plc"],
                "source": {"asset_ids": [name]},
                "destination": {"asset_ids": ["plc"]},
                "protocol": "tcp",
                "destination_ports": [{"start": 502, "end": 502}],
                "effect": "allow",
            }
            for name in (("hmi",) if candidate else ("eng", "hmi"))
        ],
        "intents": [],
        "scenarios": [],
    }
    if candidate:
        model["services"].append(
            {
                "id": "svc_maintenance",
                "asset_id": "plc",
                "interface_id": "plc_net",
                "protocol": "tcp",
                "destination_ports": [{"start": 102, "end": 102}],
            }
        )
    return model


def write_fictional_capture(
    path: Path,
    *,
    candidate: bool = False,
    incomplete: bool = False,
    scale: int = 1,
    repetitions: int = 1,
) -> None:
    """Independent literal MBAP/PDU fixtures, without product packet constructors.

    The common tuple changes from read-type to write-type header metadata.
    Engineering is reference-only; an unowned address is candidate-only.
    Additional distinct source ports provide a bounded cardinality benchmark.
    """
    if type(scale) is not int or not 1 <= scale <= 512:
        raise ValueError("Fictional capture scale must be 1..512")
    if type(repetitions) is not int or not 1 <= repetitions <= 256:
        raise ValueError("Fictional packet repetitions must be 1..256")
    relationships = [("192.0.2.11", 41000, 6 if candidate else 3)]
    relationships.append(
        ("192.0.2.99" if candidate else "192.0.2.10", 43000 if candidate else 42000, 3)
    )
    for index in range(1, scale):
        relationships.append(("192.0.2.11", 41000 + index, 3))
    frames: list[bytes] = []
    for source, port, function in relationships:
        # Function 3: read one register; function 6: write-type header shape.
        # The decoder must never export the address or application value bytes.
        pdu = bytes.fromhex("00010000000601") + bytes([function]) + bytes.fromhex("00000001")
        tcp = struct.pack("!HHIIBBHHH", port, 502, 1, 0, 0x50, 2, 1024, 0, 0)
        ipv4 = struct.pack(
            "!BBHHHBBH4s4s",
            0x45,
            0,
            20 + len(tcp) + len(pdu),
            1,
            0,
            64,
            6,
            0,
            ipaddress.IPv4Address(source).packed,
            ipaddress.IPv4Address("192.0.2.20").packed,
        )
        frames.append(bytes.fromhex("0200000000200200000000100800") + ipv4 + tcp + pdu)
    frames *= repetitions
    if incomplete:
        frames.append(bytes.fromhex("02000000002002000000001088b5") + b"fictional opaque frame")
    with path.open("xb") as stream:
        stream.write(struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1))
        for index, frame in enumerate(frames):
            stream.write(
                struct.pack(
                    "<IIII",
                    1_700_000_100 if candidate else 1_700_000_000,
                    index,
                    len(frame),
                    len(frame),
                )
            )
            stream.write(frame)


def comparison_context(reference: str, candidate: str, scope: dict[str, Any]) -> dict[str, Any]:
    return {
        "context_version": 1,
        "pairs": [
            {
                "reference_analysis_id": reference,
                "candidate_analysis_id": candidate,
                "candidate_scope": copy.deepcopy(scope),
                "alignment": "asserted",
                "rationale": "Fictional owner asserts the same laboratory observation point",
                "native_queries": [{"source_asset_id": "eng", "service_id": "svc_plc"}],
            }
        ],
    }


def prepare(
    output: Path,
    *,
    scale: int = 1,
    variations: bool = True,
    repetitions: int = 1,
) -> dict[str, Any]:
    """Create explicit validated source artifacts; preparation is not timed."""
    output.mkdir(exist_ok=False)
    workspace = output / "history"
    initialize_history(workspace)
    scope = {
        "environment": "Entirely fictional laboratory",
        "purpose": "Finite historical comparison teaching evidence",
        "coverage": "Selected fictional packets only; continuous visibility unknown",
        "uncertainties": ["Capture authenticity unattested", "Packet loss unknown"],
        "vantage_points": ["Fictional segment mirror"],
        "protocols": ["modbus_tcp"],
    }
    scope_path = output / "scope.json"
    _write(scope_path, scope)
    periods: dict[str, Any] = {}
    names = ["reference", "candidate"] + (["incomplete"] if variations else [])
    for name in names:
        candidate = name != "reference"
        capture = output / (name + ".pcap")
        write_fictional_capture(
            capture,
            candidate=candidate,
            incomplete=name == "incomplete",
            scale=scale,
            repetitions=repetitions,
        )
        observations = analyze_capture(capture)
        observations_path = output / (name + "-observations.json")
        _write(observations_path, observations)
        snapshot_id = add_collection(
            workspace, observations_path, "Fictional " + name, lifecycle.validate_state
        )["snapshot_id"]
        model_path = output / (name + "-model.yaml")
        _write(model_path, fictional_model(candidate=candidate))
        validated = validate_file(model_path)
        model = lifecycle.import_attachment(workspace, snapshot_id, "model", model_path)[
            "attachment"
        ]
        enrichment = enrich_capture(capture)
        enrichment_path = output / (name + "-enrichment.json")
        _write(enrichment_path, enrichment)
        enriched = lifecycle.import_attachment(
            workspace, snapshot_id, "enrichment", enrichment_path
        )["attachment"]
        mapping = mapping_template(observations, validated)
        for item in mapping["proposals"]:
            item["reviewer"] = "Fictional owner"
            item["rationale"] = "Invented laboratory identities only"
            if len(item["candidates"]) == 1:
                selected = item["candidates"][0]
                item.update(
                    decision="ACCEPT",
                    selected_asset_id=selected["asset_id"],
                    selected_interface_id=selected["interface_id"],
                )
            else:
                item["decision"] = "REJECT"
        mapping_path = output / (name + "-mapping.json")
        _write(mapping_path, mapping)
        mapped = lifecycle.import_attachment(
            workspace, snapshot_id, "mapping", mapping_path, model=model["attachment_id"]
        )["attachment"]
        comparison_path = output / (name + "-comparison.json")
        _write(comparison_path, compare_capture(observations, validated, mapping))
        assessed = lifecycle.import_attachment(
            workspace,
            snapshot_id,
            "comparison",
            comparison_path,
            model=model["attachment_id"],
            mapping=mapped["attachment_id"],
        )["attachment"]
        analysis = lifecycle.create_revision(
            workspace,
            snapshot_id,
            enrichment=enriched["attachment_id"],
            model=model["attachment_id"],
            mapping=mapped["attachment_id"],
            comparison=assessed["attachment_id"],
        )["analysis"]
        periods[name] = {
            "snapshot_id": snapshot_id,
            "analysis_id": analysis["analysis_id"],
            "model_id": model["attachment_id"],
            "enrichment": enrichment,
            "mapping_id": mapped["attachment_id"],
            "comparison_id": assessed["attachment_id"],
        }
    baseline = lifecycle.propose_baseline(
        workspace,
        scope_path,
        [periods["reference"]["analysis_id"]],
        model=periods["reference"]["model_id"],
    )["baseline"]
    approval = lifecycle.record_review(
        workspace,
        baseline["baseline_id"],
        "approve",
        "Fictional owner",
        "Only this invented finite reference and exact scope are selected",
    )["review"]
    if variations:
        legacy = copy.deepcopy(periods["reference"]["enrichment"])
        legacy["decoder_version"] = 1
        legacy["supported_protocols"] = ["modbus_tcp", "profinet_dcp"]
        legacy["enrichment_sha256"] = hashlib.sha256(
            canonical({k: v for k, v in legacy.items() if k != "enrichment_sha256"})
        ).hexdigest()
        legacy_path = output / "reference-decoder-one.json"
        _write(legacy_path, legacy)
        old = lifecycle.import_attachment(
            workspace, periods["reference"]["snapshot_id"], "enrichment", legacy_path
        )["attachment"]
        alternate = lifecycle.create_revision(
            workspace,
            periods["reference"]["snapshot_id"],
            enrichment=old["attachment_id"],
            model=periods["reference"]["model_id"],
            mapping=periods["reference"]["mapping_id"],
            comparison=periods["reference"]["comparison_id"],
        )["analysis"]
        periods["decoder_one"] = {"analysis_id": alternate["analysis_id"]}
    selection = {
        "workspace": str(workspace),
        "baseline_id": baseline["baseline_id"],
        "approval_id": approval["review_id"],
        "scope": scope,
        "periods": {
            k: {key: value for key, value in v.items() if key != "enrichment"}
            for k, v in periods.items()
        },
    }
    _write(output / "selection.json", selection)
    return selection


def scenario(output: Path) -> dict[str, Any]:
    from otarchguard.drift.engine import compare
    from otarchguard.drift.reports import publish, summarize, verify_report

    selected = prepare(output)
    workspace = Path(selected["workspace"])
    reference = selected["periods"]["reference"]["analysis_id"]
    candidate = selected["periods"]["candidate"]["analysis_id"]
    context = comparison_context(reference, candidate, selected["scope"])
    _write(output / "context.json", context)
    before = {
        p.relative_to(workspace).as_posix(): p.read_bytes()
        for p in workspace.rglob("*")
        if p.is_file()
    }
    report = compare(workspace, selected["baseline_id"], [candidate], context)
    observed = report["comparisons"][0]["findings"]
    communication_subtypes = {
        f["subtype"] for f in observed if f["category"] == "OBSERVED_COMMUNICATION_DIFFERENCE"
    }
    if communication_subtypes != {
        "OBSERVED_IN_BOTH",
        "REFERENCE_ONLY_OBSERVATION",
        "CANDIDATE_ONLY_OBSERVATION",
    }:
        raise AssertionError("Literal directional communication oracle disagrees")
    if not any(
        f["category"] == "NATIVE_ASSESSMENT_DIFFERENCE" and f["subtype"] == "REACHABILITY_CHANGED"
        for f in observed
    ):
        raise AssertionError("The independently specified declared policy change was not assessed")
    if not any(f["category"] == "PROTOCOL_METADATA_DIFFERENCE" for f in observed):
        raise AssertionError("The literal read-type/write-type header change was not represented")
    if report["comparisons"][0]["comparability"]["asset_continuity"] != "INDETERMINATE":
        raise AssertionError("Changed models and unowned candidate address acquired continuity")
    repeated = compare(workspace, selected["baseline_id"], [candidate], context)
    if canonical(report) != canonical(repeated):
        raise AssertionError("Identical selected evidence did not reproduce byte-identical results")
    body = {k: v for k, v in report.items() if k != "drift_id"}
    oracle = (
        "drift-"
        + hashlib.sha256(canonical({"domain": "otarchguard.drift.v1", "value": body})).hexdigest()
    )
    if report["drift_id"] != oracle:
        raise AssertionError("Independent canonical drift identity oracle disagrees")
    report_path = output / "drift.json"
    publish(report, report_path, workspace)
    original_report_bytes = report_path.read_bytes()
    verified = verify_report(workspace, report_path)
    (output / "summary.txt").write_text(summarize(report), encoding="utf-8")
    variations: dict[str, Any] = {}
    for name in ("incomplete", "decoder_one"):
        aid = selected["periods"][name]["analysis_id"]
        variation = compare(
            workspace,
            selected["baseline_id"],
            [aid],
            comparison_context(reference, aid, selected["scope"]),
        )
        assessed = variation["comparisons"][0]["comparability"]
        if name == "decoder_one":
            if assessed["independent_collections"] is not False:
                raise AssertionError(
                    "One capture with two decoder revisions became independent evidence"
                )
            if not any(
                f["category"] == "ANALYTICAL_INTERPRETATION_DIFFERENCE"
                and f["subtype"] == "PROTOCOL_SEMANTICS_CHANGED"
                for f in variation["comparisons"][0]["findings"]
            ):
                raise AssertionError("Decoder change was not separated from physical observations")
        elif not any(
            d["dimension"] == "packet_interpretation" and d["result"] == "PARTIALLY_COMPARABLE"
            for d in assessed["dimensions"]
        ):
            raise AssertionError("Opaque candidate packet did not reduce capture comparability")
        publish(variation, output / (name + "-drift.json"), workspace)
        variations[name] = {"drift_id": variation["drift_id"], "summary": variation["summary"]}
    after = {
        p.relative_to(workspace).as_posix(): p.read_bytes()
        for p in workspace.rglob("*")
        if p.is_file()
    }
    if before != after:
        raise AssertionError("A drift operation modified historical source artifacts")
    lifecycle.record_review(
        workspace,
        selected["baseline_id"],
        "revoke",
        "Fictional owner",
        "Retire this teaching reference",
        predecessor=selected["approval_id"],
    )
    try:
        compare(workspace, selected["baseline_id"], [candidate], context)
    except ModelError:
        revoked_rejected = True
    else:
        raise AssertionError("Revoked reference retained current approval authority")
    if report_path.read_bytes() != original_report_bytes:
        raise AssertionError("Revocation rewrote the earlier report")
    receipt = {
        "status": "passed",
        "fictional_only": True,
        "drift_id": report["drift_id"],
        "byte_identical_reproduction": True,
        "independent_identity_oracle": True,
        "workspace_unchanged_by_comparison": True,
        "revoked_reference_rejected": revoked_rejected,
        "verification_before_revocation": verified,
        "verification_after_revocation": verify_report(workspace, report_path),
        "variations": variations,
        "summary": report["summary"],
        "source_selection": selected,
    }
    _write(output / "walkthrough.json", receipt)
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    receipt = scenario(args.output.absolute())
    print(
        json.dumps({"status": receipt["status"], "drift_id": receipt["drift_id"]}, sort_keys=True)
    )


if __name__ == "__main__":
    main()
