"""Finite enrichment-v1 metadata validation, without opening a packet capture."""

import ipaddress
import json
from dataclasses import asdict
from typing import Any

from otarchguard.capture.protocols import LEGACY_PROTOCOLS, SUPPORTED_PROTOCOLS, digest
from otarchguard.capture.protocols.contract import ENRICHMENT_LIMITS, Status
from otarchguard.capture.protocols.header_validation import validate_header

_FIELDS = {
    "modbus_tcp": {
        "transaction_id",
        "protocol_id",
        "unit_id",
        "function_code",
        "exception_response",
        "adu_length",
    },
    "profinet_dcp": {"frame_id", "service_id", "service_type", "data_length", "blocks"},
}
_CATEGORIES = {
    "modbus_tcp": {
        "read_type",
        "write_type",
        "diagnostic_type",
        "read_write_type",
        "exception_response",
    },
    "profinet_dcp": {"get", "set", "identify"},
}
_DENOMINATORS = {base**exponent for base in (2, 10) for exponent in range(128)}


def _require(condition: bool) -> None:
    if not condition:
        raise ValueError("Invalid or unsupported protocol enrichment artifact.")


def _integer(value: object, maximum: int = 2**64 - 1) -> bool:
    return type(value) is int and 0 <= value <= maximum


def _sha(value: object) -> bool:
    return (
        isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)
    )


def _texts(value: object, maximum: int = 32) -> bool:
    return (
        isinstance(value, list)
        and len(value) <= maximum
        and all(isinstance(v, str) and len(v) <= 512 for v in value)
    )


def _ip(value: object) -> bool:
    if value is None:
        return True
    if not isinstance(value, str) or len(value) > 45:
        return False
    try:
        return str(ipaddress.ip_address(value)) == value
    except ValueError:
        return False


def _positive(item: dict[str, Any]) -> None:
    protocol, fields = item["protocol"], item["fields"]
    _require(item["recognition_method"] == "HEADER_STRUCTURE")
    if protocol not in LEGACY_PROTOCOLS:
        _require(item["reason"] is None and isinstance(item["message_category"], str))
        validate_header(protocol, fields, item["message_category"])
        return
    _require(item["reason"] is None and item["message_category"] in _CATEGORIES[protocol])
    _require(set(fields) == _FIELDS[protocol])
    if protocol == "modbus_tcp":
        _require(all(_integer(fields[k], 65535) for k in {"transaction_id", "protocol_id"}))
        _require(fields["protocol_id"] == 0)
        _require(all(_integer(fields[k], 255) for k in {"unit_id", "function_code"}))
        _require(type(fields["exception_response"]) is bool)
        _require(_integer(fields["adu_length"], 260) and fields["adu_length"] >= 8)
        code = fields["function_code"]
        _require((code & 0x7F) in {1, 2, 3, 4, 5, 6, 8, 15, 16, 22, 23})
        _require(fields["exception_response"] == bool(code & 128))
        category = (
            "exception_response"
            if code & 128
            else (
                "read_type"
                if code in {1, 2, 3, 4}
                else "diagnostic_type"
                if code == 8
                else "read_write_type"
                if code == 23
                else "write_type"
            )
        )
        _require(item["message_category"] == category)
    else:
        _require(all(_integer(v, 65535) for v in fields.values()))
        frame, service, kind = fields["frame_id"], fields["service_id"], fields["service_type"]
        _require(kind in {0, 1, 5} and service in {3, 4, 5})
        _require(
            (frame == 0xFEFD and service in {3, 4})
            or (frame == 0xFEFE and service == 5 and kind == 0)
            or (frame == 0xFEFF and service == 5 and kind in {1, 5})
        )
        _require(item["message_category"] == {3: "get", 4: "set", 5: "identify"}[service])
        _require(fields["blocks"] <= ENRICHMENT_LIMITS.dcp_blocks)
        _require(fields["data_length"] % 2 == 0)


def validate(value: dict[str, Any]) -> None:
    try:
        _validate(value)
    except (KeyError, TypeError, OverflowError, RecursionError) as error:
        raise ValueError("Invalid or unsupported protocol enrichment artifact.") from error


def _validate(value: dict[str, Any]) -> None:
    _require(type(value) is dict)
    _require(
        set(value)
        == {
            "enrichment_version",
            "decoder_version",
            "capture_sha256",
            "capture",
            "observations_sha256",
            "supported_protocols",
            "records",
            "counts",
            "packets_with_records",
            "skipped_packets",
            "limits",
            "limitations",
            "enrichment_sha256",
        }
    )
    _require(
        type(value["limits"]) is dict and set(value["limits"]) == set(asdict(ENRICHMENT_LIMITS))
    )
    for name, maximum in asdict(ENRICHMENT_LIMITS).items():
        _require(_integer(value["limits"][name], maximum) and value["limits"][name] > 0)
    limits = value["limits"]
    _require(
        len(
            (
                json.dumps(value, sort_keys=True, ensure_ascii=True, indent=2, allow_nan=False)
                + "\n"
            ).encode()
        )
        <= limits["output_bytes"]
    )
    _require(type(value["enrichment_version"]) is int and value["enrichment_version"] == 1)
    _require(type(value["decoder_version"]) is int and value["decoder_version"] in {1, 2})
    _require(_sha(value["enrichment_sha256"]) and _sha(value["capture_sha256"]))
    _require(
        digest({k: v for k, v in value.items() if k != "enrichment_sha256"})
        == value["enrichment_sha256"]
    )
    _require(value["observations_sha256"] is None)
    protocols = LEGACY_PROTOCOLS if value["decoder_version"] == 1 else SUPPORTED_PROTOCOLS
    _require(value["supported_protocols"] == list(protocols))
    _require(_texts(value["limitations"]))
    capture = value["capture"]
    _require(type(capture) is dict)
    _require(
        set(capture)
        == {
            "capture_version",
            "capture_id",
            "sha256",
            "size_bytes",
            "format",
            "interfaces",
            "packets",
            "captured_bytes",
            "original_bytes",
            "blocks",
            "unknown_blocks",
            "limitations",
        }
    )
    _require(type(capture["capture_version"]) is int and capture["capture_version"] == 1)
    _require(capture["sha256"] == capture["capture_id"] == value["capture_sha256"])
    _require(capture["format"] in {"pcap", "pcapng"})
    _require(
        all(
            _integer(capture[k])
            for k in (
                "size_bytes",
                "packets",
                "captured_bytes",
                "original_bytes",
                "blocks",
                "unknown_blocks",
            )
        )
    )
    _require(_texts(capture["limitations"]))
    _require(type(capture["interfaces"]) is list and len(capture["interfaces"]) <= 256)
    interfaces: dict[tuple[int, int], dict[str, Any]] = {}
    for interface in capture["interfaces"]:
        _require(type(interface) is dict)
        _require(
            set(interface)
            == {
                "section",
                "interface",
                "linktype",
                "snaplen",
                "timestamp_denominator",
                "timestamp_offset_seconds",
            }
        )
        _require(
            all(_integer(interface[k]) for k in ("section", "interface", "linktype", "snaplen"))
        )
        _require(
            type(interface["timestamp_denominator"]) is int
            and interface["timestamp_denominator"] in _DENOMINATORS
        )
        _require(
            type(interface["timestamp_offset_seconds"]) is int
            and -(2**63) <= interface["timestamp_offset_seconds"] < 2**63
        )
        pair = (interface["section"], interface["interface"])
        _require(pair not in interfaces)
        interfaces[pair] = interface
    _require(type(value["records"]) is list and len(value["records"]) <= limits["records"])
    counts: dict[str, int] = {}
    packet_ids: set[int] = set()
    prior = (0, -1)
    refs: dict[int, dict[str, Any]] = {}
    packet_record_counts: dict[int, int] = {}
    for item in value["records"]:
        _require(type(item) is dict)
        _require(
            set(item)
            == {
                "protocol",
                "recognition_method",
                "status",
                "message_category",
                "fields",
                "record_offset",
                "reason",
                "limitations",
                "packet",
                "source_ip",
                "destination_ip",
                "source_port",
                "destination_port",
                "vlans",
            }
        )
        protocol = item["protocol"]
        _require(protocol in protocols and type(item["fields"]) is dict)
        _require(item["status"] in {s.value for s in Status})
        _require(
            item["recognition_method"]
            in {"HEADER_STRUCTURE", "ETHERTYPE", "PORT_ASSOCIATION", "EXPLICIT_PROTOCOL_SELECTION"}
        )
        _require(_integer(item["record_offset"], limits["view_bytes"]))
        _require(_texts(item["limitations"]))
        _require(_ip(item["source_ip"]) and _ip(item["destination_ip"]))
        _require(
            all(
                v is None or _integer(v, 65535)
                for v in (item["source_port"], item["destination_port"])
            )
        )
        _require(
            type(item["vlans"]) is list
            and len(item["vlans"]) <= 2
            and all(_integer(v, 4095) for v in item["vlans"])
        )
        if item["status"] == Status.STRUCTURALLY_VALID:
            _positive(item)
        else:
            _require(item["fields"] == {} and item["message_category"] is None)
            _require(isinstance(item["reason"], str) and 0 < len(item["reason"]) <= 128)
            _require(item["recognition_method"] != "HEADER_STRUCTURE")
        ref = item["packet"]
        _require(type(ref) is dict)
        _require(
            set(ref)
            == {
                "index",
                "offset",
                "section",
                "interface",
                "captured_length",
                "original_length",
                "timestamp",
            }
        )
        _require(
            all(
                _integer(ref[k])
                for k in (
                    "index",
                    "offset",
                    "section",
                    "interface",
                    "captured_length",
                    "original_length",
                )
            )
        )
        _require(0 < ref["index"] <= capture["packets"] and ref["offset"] < capture["size_bytes"])
        _require(ref["captured_length"] == ref["original_length"])
        _require(ref["offset"] + ref["captured_length"] <= capture["size_bytes"])
        _require(item["record_offset"] <= ref["captured_length"])
        if item["status"] == Status.STRUCTURALLY_VALID:
            if protocol not in LEGACY_PROTOCOLS:
                size = validate_header(protocol, item["fields"], item["message_category"])
            else:
                size = (
                    item["fields"]["adu_length"]
                    if protocol == "modbus_tcp"
                    else 12 + item["fields"]["data_length"]
                )
            _require(item["record_offset"] + size <= ref["captured_length"])
            _require(item["record_offset"] + size <= limits["view_bytes"])
            if protocol == "profinet_dcp":
                _require(item["fields"]["blocks"] <= limits["dcp_blocks"])
        _require((ref["section"], ref["interface"]) in interfaces)
        interface = interfaces[(ref["section"], ref["interface"])]
        stamp = ref["timestamp"]
        if stamp is not None:
            _require(
                type(stamp) is dict and set(stamp) == {"ticks", "denominator", "offset_seconds"}
            )
            _require(
                type(stamp) is dict
                and _integer(stamp["ticks"])
                and type(stamp["denominator"]) is int
                and stamp["denominator"] == interface["timestamp_denominator"]
                and type(stamp["offset_seconds"]) is int
                and stamp["offset_seconds"] == interface["timestamp_offset_seconds"]
            )
        key = (ref["index"], item["record_offset"])
        _require(key > prior)
        prior = key
        if ref["index"] in refs:
            _require(ref == refs[ref["index"]])
        refs[ref["index"]] = ref
        packet_ids.add(ref["index"])
        packet_record_counts[ref["index"]] = packet_record_counts.get(ref["index"], 0) + 1
        _require(packet_record_counts[ref["index"]] <= limits["records_per_packet"])
        counter = protocol + ":" + item["status"]
        counts[counter] = counts.get(counter, 0) + 1
    _require(type(value["counts"]) is dict and value["counts"] == counts)
    _require(all(_integer(n) for n in value["counts"].values()))
    _require(
        _integer(value["packets_with_records"]) and value["packets_with_records"] == len(packet_ids)
    )
    _require(type(value["skipped_packets"]) is dict and len(value["skipped_packets"]) <= 64)
    _require(
        all(
            isinstance(k, str) and len(k) <= 128 and _integer(v)
            for k, v in value["skipped_packets"].items()
        )
    )
    _require(sum(value["skipped_packets"].values()) + len(packet_ids) == capture["packets"])
