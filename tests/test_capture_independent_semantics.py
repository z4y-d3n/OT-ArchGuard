"""Independent Reviewer B corpus: hand-packed captures and a finite reference oracle.

The writer does not import the production capture fixture generator. The oracle
describes a single directed edge with a permit set; it does not call the native
engine, partitioner, or policy evaluator to obtain expected conclusions.
"""

import copy
import hashlib
import ipaddress
import struct
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

import pytest
import yaml

from otarchguard.api import ValidatedArchitecture, validate_bytes
from otarchguard.capture.contract import CAPTURE_LIMITS
from otarchguard.capture.observations import analyze_capture
from otarchguard.capture.reconciliation import compare_capture, mapping_template
from otarchguard.diagnostics import ModelError
from otarchguard.reachability import evaluate_query


def _tcp(
    port: int = 502,
    flags: int = 2,
    *,
    source: str = "192.0.2.10",
    destination: str = "192.0.2.20",
    sport: int = 41000,
    fragment: int = 0,
) -> bytes:
    transport = struct.pack("!HHIIBBHHH", sport, port, 123, 0, 80, flags, 4096, 0, 0)
    return _ipv4(source, destination, 6, transport, fragment)


def _ipv4(source: str, destination: str, protocol: int, body: bytes, fragment: int = 0) -> bytes:
    # Checksum is deliberately zero: the capture product explicitly does not
    # validate checksums because offload may leave them unfinished at a sensor.
    ip = struct.pack(
        "!BBHHHBBH4s4s",
        69,
        0,
        20 + len(body),
        123,
        fragment,
        64,
        protocol,
        0,
        ipaddress.IPv4Address(source).packed,
        ipaddress.IPv4Address(destination).packed,
    )
    return bytes.fromhex("0200000000200200000000100800") + ip + body


def _pcap(path: Path, frames: list[bytes], linktype: int = 1) -> dict[str, Any]:
    records = [struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, linktype)]
    for index, frame in enumerate(frames):
        records.append(struct.pack("<IIII", 1700000000, index, len(frame), len(frame)))
        records.append(frame)
    path.write_bytes(b"".join(records))
    return analyze_capture(path)


def _pcapng_two_interfaces(path: Path, frame: bytes) -> dict[str, Any]:
    def block(kind: int, body: bytes) -> bytes:
        return struct.pack("<II", kind, len(body) + 12) + body + struct.pack("<I", len(body) + 12)

    records = [block(0x0A0D0D0A, struct.pack("<IHHq", 0x1A2B3C4D, 1, 0, -1))]
    records.extend([block(1, struct.pack("<HHI", 1, 0, 65535))] * 2)
    for interface in (0, 1):
        records.append(
            block(
                6,
                struct.pack("<IIIII", interface, 0, interface + 1, len(frame), len(frame))
                + frame
                + bytes((-len(frame)) % 4),
            )
        )
    path.write_bytes(b"".join(records))
    return analyze_capture(path)


def _snapshot(model: dict[str, Any]) -> ValidatedArchitecture:
    return validate_bytes(yaml.safe_dump(model).encode())


def _accept(observations: dict[str, Any], model: ValidatedArchitecture) -> dict[str, Any]:
    review = mapping_template(observations, model)
    for proposal in review["proposals"]:
        if len(proposal["candidates"]) == 1:
            candidate = proposal["candidates"][0]
            proposal.update(
                decision="ACCEPT",
                selected_asset_id=candidate["asset_id"],
                selected_interface_id=candidate["interface_id"],
                reviewer="Independent synthetic owner",
                rationale="Exact interface manually selected for this finite synthetic capture.",
            )
    return review


def _single_edge_oracle(port: int, *, has_edge: bool, permitted_ports: set[int]) -> bool:
    return has_edge and port in permitted_ports


@pytest.mark.parametrize("has_edge", [False, True])
@pytest.mark.parametrize("permitted", [False, True])
@pytest.mark.parametrize("port", [501, 502, 503])
def test_independent_port_sensitive_reference_corpus(
    tmp_path: Path, minimal: dict[str, Any], has_edge: bool, permitted: bool, port: int
) -> None:
    minimal["services"][0]["destination_ports"] = [{"start": 501, "end": 503}]
    if not has_edge:
        minimal["transport_edges"] = []
        minimal["rules"] = []
    elif not permitted:
        minimal["rules"] = []
    model = _snapshot(minimal)
    path = tmp_path / "oracle.pcap"
    observations = _pcap(path, [_tcp(port)])
    original_bytes, original_model = path.read_bytes(), model.canonical_json
    review = _accept(observations, model)
    result = compare_capture(observations, model, review)
    finding = result["findings"][0]
    expected = _single_edge_oracle(
        port, has_edge=has_edge, permitted_ports={502} if permitted else set()
    )
    assert finding["classification"] == (
        "OBSERVED_MODEL_REACHABLE" if expected else "OBSERVED_MODEL_UNREACHABLE"
    )
    native = finding["native_result"]
    assert native["selected_interval"]["reachable"] is expected
    assert native["observed_destination_port"] == port
    assert native["selected_interval"]["start"] <= port <= native["selected_interval"]["end"]
    assert native["query"] == asdict(evaluate_query(model, "eng", "svc_plc"))
    if expected:
        witness = native["selected_interval"]["witness"]
        assert witness["snapshot_sha256"] == model.sha256
        assert [step["edge_id"] for step in witness["steps"]] == ["t_eng_plc"]
    else:
        assert native["selected_interval"]["witness"] is None
        assert native["selected_interval"]["diagnostics"]["reason"] == (
            "no_permitted_path" if has_edge else "no_structural_path"
        )
    assert finding["capture_sha256"] == hashlib.sha256(original_bytes).hexdigest()
    assert finding["samples"][0]["index"] == 1
    assert len(finding["association_decision_ids"]) == 2
    assert path.read_bytes() == original_bytes and model.canonical_json == original_model


def test_cache_selects_each_observed_port_from_shared_query(
    tmp_path: Path, minimal: dict[str, Any]
) -> None:
    minimal["services"][0]["destination_ports"] = [{"start": 501, "end": 503}]
    model = _snapshot(minimal)
    observations = _pcap(tmp_path / "ports.pcap", [_tcp(port) for port in (501, 502, 503)])
    result = compare_capture(observations, model, _accept(observations, model))
    by_port = {f["native_result"]["observed_destination_port"]: f for f in result["findings"]}
    assert result["work"]["native_query_pairs"] == 1
    for port, finding in by_port.items():
        assert finding["native_result"]["selected_interval"]["reachable"] is (port == 502)
        assert finding["classification"] == (
            "OBSERVED_MODEL_REACHABLE" if port == 502 else "OBSERVED_MODEL_UNREACHABLE"
        )
    assert len({id(f["native_result"]["query"]) for f in by_port.values()}) == 1


@pytest.mark.parametrize(
    "name,frames,linktype,expected",
    [
        ("initial_syn", [_tcp()], 1, "OBSERVED_MODEL_REACHABLE"),
        ("syn_ack_only", [_tcp(flags=18)], 1, "OBSERVED_DIRECTION_UNCERTAIN"),
        ("midstream", [_tcp(flags=16)], 1, "OBSERVED_DIRECTION_UNCERTAIN"),
        ("reset", [_tcp(flags=4)], 1, "OBSERVED_DIRECTION_UNCERTAIN"),
        ("syn_reset", [_tcp(flags=6)], 1, "OBSERVED_DIRECTION_UNCERTAIN"),
        (
            "udp",
            [_ipv4("192.0.2.10", "192.0.2.20", 17, struct.pack("!HHHH", 41000, 502, 8, 0))],
            1,
            "OBSERVED_DIRECTION_UNCERTAIN",
        ),
        ("undeclared", [_tcp(port=504)], 1, "OBSERVED_SERVICE_UNDECLARED"),
        ("unknown_source", [_tcp(source="198.51.100.2")], 1, "OBSERVED_ENDPOINT_UNMAPPED"),
        (
            "unknown_destination",
            [_tcp(destination="198.51.100.2")],
            1,
            "OBSERVED_ENDPOINT_UNMAPPED",
        ),
        ("fragment", [_tcp(fragment=8192)], 1, "OBSERVED_MODEL_UNSUPPORTED"),
        ("truncated", [_tcp()[:-1]], 1, "OBSERVED_MODEL_UNSUPPORTED"),
        ("unknown_linktype", [_tcp()], 147, "OBSERVED_MODEL_UNSUPPORTED"),
        (
            "arp",
            [
                bytes.fromhex("ffffffffffff02000000001008060001080006040001020000000010")
                + bytes.fromhex("c000020a000000000000c0000214")
            ],
            1,
            "OBSERVED_MODEL_UNSUPPORTED",
        ),
        (
            "ipv6",
            [
                bytes.fromhex("02000000002002000000001086dd")
                + struct.pack(
                    "!IHBB16s16s",
                    6 << 28,
                    8,
                    17,
                    64,
                    ipaddress.IPv6Address("2001:db8::10").packed,
                    ipaddress.IPv6Address("2001:db8::20").packed,
                )
                + struct.pack("!HHHH", 41000, 502, 8, 0)
            ],
            1,
            "OBSERVED_MODEL_UNSUPPORTED",
        ),
    ],
)
def test_independent_raw_classification_and_evidence(
    tmp_path: Path,
    minimal: dict[str, Any],
    name: str,
    frames: list[bytes],
    linktype: int,
    expected: str,
) -> None:
    model = _snapshot(minimal)
    observations = _pcap(tmp_path / f"{name}.pcap", frames, linktype)
    result = compare_capture(observations, model, _accept(observations, model))
    finding = result["findings"][0]
    assert finding["classification"] == expected
    assert bool(finding["native_result"]) is (expected == "OBSERVED_MODEL_REACHABLE")
    assert finding["samples"][0]["offset"] == 24
    assert finding["samples"][0]["captured_length"] == len(frames[0])
    assert finding["model_sha256"] == model.sha256
    if name in {"fragment", "truncated", "unknown_linktype"}:
        assert observations["flows"][0]["destination_port"] is None
        assert observations["flows"][0]["initiation_evidence"] == []
        assert result["absence_assessment"]["status"] == "suppressed"
    if name == "initial_syn":
        assert observations["flows"][0]["protocol_hints"] == [
            {"protocol": "Modbus/TCP", "level": "PORT_HINT", "port": 502}
        ]
        assert any("does not establish authorization" in x for x in result["limitations"])


def test_declared_destination_interface_must_match_observed_address(
    tmp_path: Path, minimal: dict[str, Any]
) -> None:
    minimal["interfaces"].append(
        {
            "id": "plc_other",
            "asset_id": "plc",
            "placement_zone_id": "control",
            "ipv4": "192.0.2.21/24",
        }
    )
    minimal["services"][0]["interface_id"] = "plc_other"
    model = _snapshot(minimal)
    observations = _pcap(tmp_path / "interface.pcap", [_tcp()])
    result = compare_capture(observations, model, _accept(observations, model))
    assert result["findings"][0]["classification"] == "OBSERVED_SERVICE_UNDECLARED"
    assert result["work"]["native_query_pairs"] == 0
    assert [s["service_id"] for s in result["declared_services_not_observed"]] == ["svc_plc"]


def test_duplicate_sensor_copies_are_counted_without_strengthening_conclusions(
    tmp_path: Path, minimal: dict[str, Any]
) -> None:
    model = _snapshot(minimal)
    observations = _pcapng_two_interfaces(tmp_path / "two-sensors.pcapng", _tcp())
    result = compare_capture(observations, model, _accept(observations, model))
    assert len(observations["flows"]) == 1
    observed = observations["flows"][0]
    assert observed["packets"] == observed["initiation_packets"] == 2
    assert observed["interfaces"] == ["0:0", "0:1"]
    assert result["work"]["native_query_pairs"] == 1
    assert result["findings"][0]["classification"] == "OBSERVED_MODEL_REACHABLE"
    assert any("sensor visibility" in text for text in result["limitations"])


def test_no_traffic_is_only_finite_capture_absence(tmp_path: Path, minimal: dict[str, Any]) -> None:
    model = _snapshot(minimal)
    observations = _pcap(tmp_path / "empty.pcap", [])
    result = compare_capture(observations, model, _accept(observations, model))
    assert result["findings"] == []
    assert result["absence_assessment"]["status"] == "scoped"
    absent = result["declared_services_not_observed"][0]
    assert absent["classification"] == "DECLARED_SERVICE_NOT_OBSERVED"
    assert "does not establish blocking" in absent["reason"]
    assert "no visibility completeness is asserted" in result["absence_scope"]


@pytest.mark.parametrize("decision", ["PENDING", "REJECT"])
def test_unaccepted_owner_identity_never_runs_evaluator(
    tmp_path: Path, minimal: dict[str, Any], decision: str
) -> None:
    model = _snapshot(minimal)
    observations = _pcap(tmp_path / "owner.pcap", [_tcp()])
    review = mapping_template(observations, model)
    if decision == "REJECT":
        for proposal in review["proposals"]:
            proposal.update(
                decision=decision, reviewer="Reviewer B", rationale="DHCP reuse unresolved"
            )
    result = compare_capture(observations, model, review)
    assert result["findings"][0]["classification"] == "OBSERVED_ENDPOINT_UNMAPPED"
    assert result["work"]["native_query_pairs"] == 0


@pytest.mark.parametrize("mutation", ["capture", "model", "candidate", "host", "control"])
def test_review_cannot_transfer_to_changed_evidence_or_review_controls(
    tmp_path: Path, minimal: dict[str, Any], mutation: str
) -> None:
    model = _snapshot(minimal)
    observations = _pcap(tmp_path / "binding.pcap", [_tcp()])
    review = _accept(observations, model)
    if mutation == "capture":
        observations = _pcap(tmp_path / "changed.pcap", [_tcp(), _tcp()])
    elif mutation == "model":
        minimal["revision"] = "changed"
        model = _snapshot(minimal)
    elif mutation == "candidate":
        review["proposals"][0]["candidates"] = []
    elif mutation == "host":
        review["proposals"][0]["host_id"] = "another_observation"
    else:
        review["proposals"][0]["reviewer"] = "bad\u0085reviewer"
    with pytest.raises(ModelError):
        compare_capture(observations, model, review)


def test_native_resource_failure_aborts_whole_comparison(
    tmp_path: Path, minimal: dict[str, Any]
) -> None:
    # Two hosts x two interfaces and one flow x one service fit work=4; the
    # native preflight (3 * (two states + one edge)) must then reject.
    model = _snapshot(minimal)
    observations = _pcap(tmp_path / "resource.pcap", [_tcp()])
    original = copy.deepcopy(observations)
    with pytest.raises(ModelError) as caught:
        compare_capture(
            observations,
            model,
            _accept(observations, model),
            replace(CAPTURE_LIMITS, comparison_work=4),
        )
    assert caught.value.diagnostics[0].category == "resource_limit"
    assert "state_edge_visits" in caught.value.diagnostics[0].message
    assert observations == original


def test_duplicate_declared_addresses_are_rejected_before_mapping(minimal: dict[str, Any]) -> None:
    minimal["interfaces"][1]["ipv4"] = minimal["interfaces"][0]["ipv4"]
    with pytest.raises(ModelError) as caught:
        _snapshot(minimal)
    assert caught.value.diagnostics[0].code == "DUPLICATE_ADDRESS"


def test_multihomed_source_is_not_evaluated_from_unobserved_interface(
    tmp_path: Path, minimal: dict[str, Any]
) -> None:
    minimal["interfaces"].append(
        {
            "id": "eng_other",
            "asset_id": "eng",
            "placement_zone_id": "control",
            "ipv4": "198.51.100.10/24",
        }
    )
    model = _snapshot(minimal)
    observations = _pcap(tmp_path / "multihomed.pcap", [_tcp()])
    result = compare_capture(observations, model, _accept(observations, model))
    assert result["findings"][0]["classification"] == "OBSERVED_MODEL_UNSUPPORTED"
    assert result["findings"][0]["native_result"] is None
    assert result["work"]["native_query_pairs"] == 0


def test_familiar_source_port_is_not_an_observed_destination_service(
    tmp_path: Path, minimal: dict[str, Any]
) -> None:
    model = _snapshot(minimal)
    observations = _pcap(tmp_path / "source-port.pcap", [_tcp(port=41000, sport=502)])
    result = compare_capture(observations, model, _accept(observations, model))
    assert observations["flows"][0]["protocol_hints"][0]["level"] == "PORT_HINT"
    assert result["findings"][0]["classification"] == "OBSERVED_SERVICE_UNDECLARED"
    assert result["work"]["native_query_pairs"] == 0


def test_two_syn_directions_in_one_tuple_never_assert_a_single_initiator(
    tmp_path: Path, minimal: dict[str, Any]
) -> None:
    model = _snapshot(minimal)
    observations = _pcap(
        tmp_path / "two-directions.pcap",
        [
            _tcp(),
            _tcp(source="192.0.2.20", destination="192.0.2.10", sport=502, port=41000),
        ],
    )
    result = compare_capture(observations, model, _accept(observations, model))
    assert observations["conversations"][0]["initiation_direction"] == "conflicting_syn"
    assert {f["classification"] for f in result["findings"]} == {"OBSERVED_DIRECTION_UNCERTAIN"}
    assert result["work"]["native_query_pairs"] == 0


def test_address_reuse_and_transit_macs_remain_owner_uncertainties(
    tmp_path: Path, minimal: dict[str, Any]
) -> None:
    # Two different frame-source MACs with the same IPv4 source could reflect
    # transit capture, DHCP reuse, spoofing, or duplication. No cause is inferred.
    first = _tcp()
    second = first[:6] + bytes.fromhex("020000000099") + first[12:]
    observations = _pcap(tmp_path / "reuse.pcap", [first, second])
    source = next(h for h in observations["hosts"] if h["ip"] == "192.0.2.10")
    assert source["source_macs"] == ["02:00:00:00:00:10", "02:00:00:00:00:99"]
    assert source["packets"] == 2
    model = _snapshot(minimal)
    pending = mapping_template(observations, model)
    assert all(p["decision"] == "PENDING" for p in pending["proposals"])
    assert compare_capture(observations, model, pending)["work"]["native_query_pairs"] == 0
    accepted = compare_capture(observations, model, _accept(observations, model))
    assert any("NAT, DHCP" in text for text in accepted["limitations"])
    assert any("never establish IP ownership" in text for text in accepted["limitations"])
