"""Read frozen evidence without importing the analyzer or reopening capture bytes.

This development contract probe is not a historical-analysis product. Hashes
verify integrity, never creator authenticity or the truth of owner assertions.
Unknown optional fields and classification strings are preserved verbatim.
"""

import argparse
import hashlib
import ipaddress
import json
import re
import stat
from fractions import Fraction
from pathlib import Path, PureWindowsPath
from typing import Any, cast


def digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode()
    ).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def integer(value: object, minimum: int = 0) -> bool:
    return type(value) is int and value >= minimum


def identity(value: object, prefix: str = "") -> bool:
    return isinstance(value, str) and re.fullmatch(prefix + r"[0-9a-f]{64}", value) is not None


def read_json(path: Path) -> dict[str, Any]:
    require(
        not str(path).startswith(("\\\\", "//"))
        and not PureWindowsPath(path).drive.startswith("\\\\"),
        "Network filesystem paths are outside offline evidence scope",
    )
    for ancestor in (path, *path.parents):
        require(
            not ancestor.is_symlink() and not ancestor.is_junction(),
            "Linked evidence paths are forbidden",
        )
    require(stat.S_ISREG(path.stat().st_mode), "Evidence must be a regular local file")
    with path.open("rb") as stream:
        data = stream.read(64 * 1024 * 1024 + 1)
    require(len(data) <= 64 * 1024 * 1024, "Evidence exceeds contract byte budget")
    text = data.decode("utf-8")
    depth = 0
    quoted = escaped = False
    for character in text:
        if quoted:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                quoted = False
        elif character == '"':
            quoted = True
        elif character in "[{":
            depth += 1
            require(depth <= 64, "Evidence nesting exceeds consumer budget")
        elif character in "]}":
            depth -= 1

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            require(key not in result, "Duplicate JSON key")
            result[key] = value
        return result

    def constant(value: str) -> None:
        raise ValueError("Nonstandard JSON constant: " + value)

    result = json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
    require(isinstance(result, dict), "Expected evidence object")
    return result  # type: ignore[no-any-return]


def _stamp(value: object) -> None:
    if value is not None:
        require(isinstance(value, str), "Timestamp must be rational text or null")
        require(re.fullmatch(r"-?\d+/[1-9]\d*", str(value)) is not None, "Invalid timestamp")
        Fraction(str(value))


def _list(value: object, maximum: int, description: str) -> list[Any]:
    require(isinstance(value, list) and len(value) <= maximum, "Invalid " + description)
    return cast(list[Any], value)


def _mac(value: object) -> bool:
    return (
        isinstance(value, str) and re.fullmatch(r"[0-9a-f]{2}(:[0-9a-f]{2}){5}", value) is not None
    )


def _macs(value: object) -> list[Any]:
    values = _list(value, 256, "MAC observations")
    require(all(_mac(v) for v in values) and values == sorted(set(values)), "Invalid MAC set")
    return values


def _address(value: object, version: object) -> None:
    if value is not None:
        require(isinstance(value, str), "Invalid address type")
        address = ipaddress.ip_address(str(value))
        require(str(address) == value and address.version == version, "Invalid address family")


def _arp(flow: dict[str, Any]) -> None:
    arp = flow["arp"]
    if arp is None:
        require(
            flow["transport"] != "arp" or flow["source_ip"] is flow["destination_ip"] is None,
            "Incomplete ARP cannot supply protocol addresses",
        )
        return
    require(isinstance(arp, dict) and flow["transport"] == "arp", "Invalid ARP evidence type")
    require(
        type(arp["metadata_version"]) is int and arp["metadata_version"] == 1,
        "Unsupported ARP metadata",
    )
    require(integer(arp["opcode"]) and arp["opcode"] <= 65535, "Invalid ARP opcode")
    expected_operation = {1: "request", 2: "reply"}.get(arp["opcode"], "unsupported")
    require(arp["operation"] == expected_operation, "ARP operation/opcode mismatch")
    require(
        arp["sender_protocol_address"] == flow["source_ip"]
        and arp["target_protocol_address"] == flow["destination_ip"]
        and flow["ip_version"] == 4
        and flow["source_ip"] is not None
        and flow["destination_ip"] is not None,
        "ARP legacy field binding mismatch",
    )
    for name in (
        "sender_hardware_address",
        "target_hardware_address",
        "ethernet_source_mac",
        "ethernet_destination_mac",
    ):
        require(_mac(arp[name]), "Invalid ARP hardware field")
    require(
        flow["source_macs"] == [arp["ethernet_source_mac"]]
        and flow["destination_macs"] == [arp["ethernet_destination_mac"]],
        "ARP Ethernet observation mismatch",
    )
    destination = arp["ethernet_destination_mac"]
    delivery = (
        "broadcast"
        if destination == "ff:ff:ff:ff:ff:ff"
        else "multicast"
        if int(destination[:2], 16) & 1
        else "unicast"
    )
    require(arp["ethernet_delivery"] == delivery, "ARP delivery mismatch")
    require(
        flow["source_port"] is flow["destination_port"] is None
        and flow["initiation_packets"] == 0
        and (expected_operation != "unsupported" or flow["status"] != "decoded"),
        "ARP supplied unsupported transport or identity evidence",
    )


def _validate_observations(observations: dict[str, Any]) -> None:
    require(
        type(observations.get("observation_version")) is int
        and observations["observation_version"] == 2,
        "Unsupported observation version; v1 requires regeneration, never reinterpretation",
    )
    require(
        type(observations.get("catalog_version")) is int and observations["catalog_version"] == 1,
        "Unsupported protocol catalog",
    )
    require(
        observations.get("observations_sha256")
        == digest({k: v for k, v in observations.items() if k != "observations_sha256"}),
        "Observation integrity mismatch",
    )
    capture = observations["capture"]
    require(isinstance(capture, dict), "Invalid capture metadata")
    require(
        type(capture["capture_version"]) is int and capture["capture_version"] == 1,
        "Unsupported capture metadata version",
    )
    require(
        identity(capture["sha256"]) and capture["capture_id"] == capture["sha256"],
        "Invalid capture identity",
    )
    interface_records = _list(capture["interfaces"], 256, "interface inventory")
    require(
        integer(capture["packets"])
        and capture["packets"] <= 1_000_000
        and integer(capture["size_bytes"]),
        "Invalid capture counters",
    )
    for interface in interface_records:
        require(
            isinstance(interface, dict)
            and integer(interface["section"])
            and integer(interface["interface"]),
            "Invalid interface reference",
        )
    interfaces = {(i["section"], i["interface"]) for i in interface_records}
    require(len(interfaces) == len(capture["interfaces"]) <= 256, "Invalid interface inventory")
    hosts = _list(observations["hosts"], 20_000, "host inventory")
    require(len({h["id"] for h in hosts}) == len(hosts), "Duplicate host identity")
    for host in hosts:
        require(isinstance(host, dict), "Invalid host record")
        require(
            type(host["ip_version"]) is int and host["ip_version"] in {4, 6}, "Invalid host family"
        )
        _address(host["ip"], host["ip_version"])
        require(
            host["ip"] is not None and integer(host["packets"], 1), "Invalid host address/count"
        )
        require(
            host["id"] == "host-" + digest([host["ip_version"], host["ip"]]),
            "Invalid host identity",
        )
        require(
            isinstance(host["observation_roles"], list) and bool(host["observation_roles"]),
            "Host provenance missing",
        )
        _macs(host["source_macs"])
        _macs(host["destination_macs"])
    flows = _list(observations["flows"], 50_000, "flow inventory")
    by_id = {flow["id"]: flow for flow in flows}
    require(len(by_id) == len(flows), "Duplicate flow identity")
    expected_hosts: dict[str, dict[str, Any]] = {}
    for flow in flows:
        require(isinstance(flow, dict), "Invalid flow record")
        require(
            flow["ip_version"] is None
            or type(flow["ip_version"]) is int
            and flow["ip_version"] in {4, 6},
            "Invalid flow address family",
        )
        for direction in ("source", "destination"):
            _address(flow[direction + "_ip"], flow["ip_version"])
            port = flow[direction + "_port"]
            require(port is None or integer(port) and port <= 65535, "Invalid port")
            _macs(flow[direction + "_macs"])
        require(
            flow["status"] in {"decoded", "truncated", "malformed", "fragmented", "unsupported"}
            and flow["transport"] in {"tcp", "udp", "icmp", "icmpv6", "arp", "unknown"}
            and integer(flow["linktype"]),
            "Invalid flow protocol/status",
        )
        vlans = _list(flow["vlans"], 2, "VLAN evidence")
        require(all(integer(v) and v <= 4095 for v in vlans), "Invalid VLAN ID")
        _arp(flow)
        endpoints = [
            (flow[k + "_ip"] or "", flow[k + "_port"] if flow[k + "_port"] is not None else -1)
            for k in ("source", "destination")
        ]
        core = [
            endpoints,
            flow["transport"],
            flow["ip_version"],
            flow["vlans"],
            flow["status"],
            flow["linktype"],
        ]
        group = [sorted(endpoints), flow["transport"], flow["ip_version"], flow["vlans"]]
        arp = flow["arp"]
        if arp is not None:
            core.append(arp)
            group.append(arp)
        if not flow["source_ip"] and not flow["destination_ip"]:
            group.append(flow["linktype"])
        require(flow["id"] == "flow-" + digest(core), "Invalid flow identity")
        require(
            flow["conversation_id"] == "conversation-" + digest(group),
            "Invalid conversation reference",
        )
        require(
            integer(flow["packets"], 1) and flow["packets"] <= capture["packets"],
            "Invalid packet count",
        )
        samples = _list(flow["samples"], 8, "packet samples")
        initiations = _list(flow["initiation_evidence"], 8, "initiation samples")
        require(
            integer(flow["samples_omitted"])
            and integer(flow["initiation_evidence_omitted"])
            and integer(flow["initiation_packets"])
            and flow["initiation_packets"] <= flow["packets"],
            "Invalid sample counts",
        )
        require(
            flow["samples_omitted"] + len(flow["samples"]) == flow["packets"],
            "Sample denominator mismatch",
        )
        require(
            flow["initiation_evidence_omitted"] + len(flow["initiation_evidence"])
            == flow["initiation_packets"],
            "Initiation denominator mismatch",
        )
        for stamp in (flow["first_timestamp"], flow["last_timestamp"]):
            _stamp(stamp)
        for sample_list in (samples, initiations):
            require(
                len({s["index"] for s in sample_list}) == len(sample_list),
                "Duplicate packet sample",
            )
        for sample in samples + initiations:
            require(isinstance(sample, dict), "Invalid packet sample")
            require(
                integer(sample["section"])
                and integer(sample["interface"])
                and (sample["section"], sample["interface"]) in interfaces,
                "Orphaned packet interface",
            )
            require(
                integer(sample["index"], 1)
                and sample["index"] <= capture["packets"]
                and integer(sample["offset"])
                and sample["offset"] < capture["size_bytes"],
                "Invalid packet reference",
            )
            require(
                integer(sample["captured_length"])
                and sample["captured_length"] <= 262_144
                and integer(sample["original_length"])
                and sample["captured_length"] <= sample["original_length"],
                "Invalid packet lengths",
            )
            stamp = sample["timestamp"]
            if stamp is not None:
                require(
                    integer(stamp["ticks"])
                    and integer(stamp["denominator"], 1)
                    and type(stamp["offset_seconds"]) is int,
                    "Invalid exact timestamp",
                )
        host_evidence = [
            (flow["source_ip"], flow["source_macs"], "source_macs", "packet_source"),
            (
                flow["destination_ip"],
                flow["destination_macs"],
                "destination_macs",
                "packet_destination",
            ),
        ]
        if flow["transport"] == "arp":
            host_evidence = (
                [
                    (
                        flow["source_ip"],
                        flow["source_macs"],
                        "source_macs",
                        "arp_" + arp["operation"] + "_sender",
                    )
                ]
                if flow["status"] == "decoded"
                and arp is not None
                and flow["source_ip"] != "0.0.0.0"
                else []
            )
        for address, macs, field, role in host_evidence:
            if address is not None:
                evidence = expected_hosts.setdefault(
                    address,
                    {"packets": 0, "source_macs": set(), "destination_macs": set(), "roles": set()},
                )
                evidence["packets"] += flow["packets"]
                evidence[field].update(macs)
                evidence["roles"].add(role)
    require({h["ip"] for h in hosts} == set(expected_hosts), "Host evidence partition mismatch")
    for host in hosts:
        expected = expected_hosts[host["ip"]]
        require(
            host["packets"] == expected["packets"]
            and host["source_macs"] == sorted(expected["source_macs"])
            and host["destination_macs"] == sorted(expected["destination_macs"])
            and host["observation_roles"] == sorted(expected["roles"]),
            "Host provenance differs from flow evidence",
        )
    groups = _list(observations["conversations"], 50_000, "conversation inventory")
    require(len({g["id"] for g in groups}) == len(groups) <= 50_000, "Duplicate conversation")
    grouped_ids: list[str] = []
    for group in groups:
        members = group["flow_ids"]
        require(
            all(f in by_id and by_id[f]["conversation_id"] == group["id"] for f in members),
            "Orphaned conversation member",
        )
        require(
            group["packets"] == sum(by_id[f]["packets"] for f in members),
            "Conversation count mismatch",
        )
        grouped_ids.extend(members)
    require(sorted(grouped_ids) == sorted(by_id), "Conversation partition mismatch")
    coverage = observations["coverage"]
    require(
        all(
            integer(coverage[k])
            for k in (
                "packets",
                "decoded",
                "truncated",
                "malformed",
                "fragmented",
                "unsupported",
                "interpreted_packets",
                "uninterpreted_packets",
            )
        ),
        "Invalid coverage counters",
    )
    require(
        sum(flow["packets"] for flow in flows) == capture["packets"] == coverage["packets"],
        "Capture denominator mismatch",
    )
    require(
        sum(coverage[k] for k in ("decoded", "truncated", "malformed", "fragmented", "unsupported"))
        == coverage["packets"],
        "Coverage denominator mismatch",
    )
    require(
        coverage["interpreted_packets"] + coverage["uninterpreted_packets"] == coverage["packets"],
        "Interpretation denominator mismatch",
    )
    require(
        coverage["interpreted_packets"] == coverage["decoded"], "Interpretation status mismatch"
    )
    for status in ("decoded", "truncated", "malformed", "fragmented", "unsupported"):
        require(
            coverage[status] == sum(f["packets"] for f in flows if f["status"] == status),
            "Coverage status mismatch",
        )


def validate_observations(observations: dict[str, Any]) -> None:
    """Reject malformed frozen observations with a consistent exception type."""
    try:
        _validate_observations(observations)
    except (
        KeyError,
        TypeError,
        AttributeError,
        IndexError,
        ZeroDivisionError,
        OverflowError,
    ) as error:
        raise ValueError("Invalid observation structure: " + str(error)) from error


def load_bundle(directory: Path) -> dict[str, Any]:
    """Validate three independently versioned artifacts and preserve their contents."""
    try:
        observations = read_json(directory / "observations.json")
        mapping = read_json(directory / "mapping.json")
        comparison = read_json(directory / "comparison.json")
        validate_observations(observations)
        for document, version in (
            (mapping, "association_version"),
            (comparison, "comparison_version"),
        ):
            require(
                type(document.get(version)) is int and document[version] == 1,
                "Unsupported " + version,
            )
            require(
                document["capture_sha256"] == observations["capture"]["sha256"]
                and document["observations_sha256"] == observations["observations_sha256"]
                and identity(document["model_sha256"]),
                "Evidence binding mismatch",
            )
        require(mapping["model_sha256"] == comparison["model_sha256"], "Model binding mismatch")
        require(comparison["mapping_sha256"] == digest(mapping), "Mapping integrity mismatch")
        decisions = {
            "decision",
            "selected_asset_id",
            "selected_interface_id",
            "reviewer",
            "rationale",
        }
        proposals = _list(mapping["proposals"], 20_000, "association proposals")
        require(all(isinstance(p, dict) for p in proposals), "Invalid proposal record")
        cores = [{k: v for k, v in p.items() if k not in decisions} for p in proposals]
        require(mapping["candidates_sha256"] == digest(cores), "Candidate integrity mismatch")
        require(
            comparison["association_decisions"] == mapping["proposals"],
            "Comparison decisions differ from owner assertions",
        )
        proposal_ids = set()
        hosts = {h["id"]: h for h in observations["hosts"]}
        require(
            len(proposals) == len(hosts) and {p["host_id"] for p in proposals} == set(hosts),
            "Association host partition mismatch",
        )
        by_ip: dict[str, dict[str, Any]] = {}
        for proposal, core in zip(proposals, cores, strict=True):
            require(
                proposal["id"]
                == "association_" + digest({k: v for k, v in core.items() if k != "id"}),
                "Invalid association identity",
            )
            require(
                proposal["id"] not in proposal_ids and proposal["host_id"] in hosts,
                "Duplicate or orphaned association",
            )
            proposal_ids.add(proposal["id"])
            require(
                proposal["observed_ip"] == hosts[proposal["host_id"]]["ip"],
                "Association address differs from referenced host",
            )
            by_ip[proposal["observed_ip"]] = proposal
            candidates = _list(proposal["candidates"], 20_000, "association candidates")
            require(
                all(
                    isinstance(c, dict)
                    and isinstance(c["asset_id"], str)
                    and isinstance(c["interface_id"], str)
                    for c in candidates
                ),
                "Invalid association candidate",
            )
            require(proposal["decision"] in {"PENDING", "ACCEPT", "REJECT"}, "Unknown decision")
            if proposal["decision"] == "ACCEPT":
                require(
                    {
                        "asset_id": proposal["selected_asset_id"],
                        "interface_id": proposal["selected_interface_id"],
                    }
                    in proposal["candidates"],
                    "Accepted identity is outside original candidates",
                )
            else:
                require(
                    proposal["selected_asset_id"] is None
                    and proposal["selected_interface_id"] is None,
                    "Unaccepted selection",
                )
            require(
                all(isinstance(proposal[k], str) for k in ("reviewer", "rationale")),
                "Invalid review assertion",
            )
            require(
                all(proposal[k].strip() for k in ("reviewer", "rationale"))
                if proposal["decision"] != "PENDING"
                else proposal["reviewer"] == proposal["rationale"] == "",
                "Incomplete review",
            )
        flows = {f["id"]: f for f in observations["flows"]}
        findings = _list(comparison["findings"], 50_000, "comparison findings")
        require(
            sorted(f["flow_id"] for f in findings) == sorted(flows),
            "Findings must cover every flow exactly once",
        )
        for finding in findings:
            flow = flows[finding["flow_id"]]
            require(
                finding["conversation_id"] == flows[finding["flow_id"]]["conversation_id"]
                and finding["capture_sha256"] == mapping["capture_sha256"]
                and finding["model_sha256"] == mapping["model_sha256"],
                "Finding provenance mismatch",
            )
            require(
                finding["association_decision_ids"]
                == [
                    by_ip[flow[k]]["id"]
                    for k in ("source_ip", "destination_ip")
                    if flow[k] in by_ip
                ],
                "Finding endpoint decision mismatch",
            )
            require(finding["samples"] == flow["samples"], "Finding sample provenance mismatch")
            require(
                isinstance(finding["classification"], str) and bool(finding["classification"]),
                "Invalid classification",
            )
            native = finding["native_result"]
            if native is not None:
                require(
                    isinstance(native, dict)
                    and native["model_sha256"] == mapping["model_sha256"]
                    and native["observed_destination_port"] == flow["destination_port"]
                    and isinstance(native["selected_interval"], dict)
                    and native["selected_interval"] in native["query"]["intervals"],
                    "Native evidence provenance mismatch",
                )
        return {"observations": observations, "mapping": mapping, "comparison": comparison}
    except (
        KeyError,
        TypeError,
        AttributeError,
        IndexError,
        ZeroDivisionError,
        OverflowError,
    ) as error:
        raise ValueError("Invalid evidence structure: " + str(error)) from error


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    bundle = load_bundle(args.directory)
    print(
        json.dumps(
            {
                "status": "passed",
                "observation_version": 2,
                "capture_sha256": bundle["observations"]["capture"]["sha256"],
                "model_sha256": bundle["mapping"]["model_sha256"],
                "flows": len(bundle["observations"]["flows"]),
                "classifications": sorted(
                    {f["classification"] for f in bundle["comparison"]["findings"]}
                ),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
