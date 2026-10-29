"""Bounded industrial header metadata, independently versioned from observations."""

import hashlib
import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any

from otarchguard.capture.contract import CAPTURE_LIMITS, CaptureLimits, Packet
from otarchguard.capture.observations import _reference
from otarchguard.capture.parser import scan_capture
from otarchguard.capture.protocols.contract import (
    ENRICHMENT_LIMITS,
    EnrichmentLimits,
    EnrichmentRecord,
    ProtocolView,
    Status,
)
from otarchguard.capture.protocols.dcp import decode_dcp
from otarchguard.capture.protocols.dnp3 import decode_dnp3
from otarchguard.capture.protocols.enip import decode_enip
from otarchguard.capture.protocols.iec104 import decode_iec104
from otarchguard.capture.protocols.modbus import decode_modbus
from otarchguard.capture.protocols.opcua import decode_opcua
from otarchguard.capture.protocols.packet import packet_view
from otarchguard.capture.protocols.s7comm import decode_s7comm
from otarchguard.diagnostics import check_limit

__all__ = [
    "ENRICHMENT_LIMITS",
    "EnrichmentLimits",
    "EnrichmentRecord",
    "ProtocolView",
    "Status",
    "decode",
    "enrich_capture",
    "validate_enrichment",
]

LEGACY_PROTOCOLS = ("modbus_tcp", "profinet_dcp")
SUPPORTED_PROTOCOLS = LEGACY_PROTOCOLS + ("ethernet_ip", "s7comm", "iec104", "opcua_binary", "dnp3")
_LIMITATIONS = (
    "Independent header metadata; frozen observations and owner approvals are not changed.",
    "Structural validation is not authenticity, authorization or successful command execution.",
    "No application values, network access, reassembly or speculative offset matching.",
    "Packet/record counts are observations; duplicates and multi-interface copies "
    "are not deduplicated.",
    "Seven documented header subsets; TCP standard ports and Layer-2 PROFINET DCP only.",
    "IPv6 extension headers and unsupported outer frames remain unassessed.",
)


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def decode(
    view: ProtocolView,
    limits: EnrichmentLimits = ENRICHMENT_LIMITS,
) -> tuple[EnrichmentRecord, ...]:
    """Decode only at offset zero; no protocol search or retained packet state."""
    if view.transport == "tcp":
        # Preserve legacy Modbus precedence; never search arbitrary payload offsets.
        for decoder in (
            decode_modbus,
            decode_enip,
            decode_s7comm,
            decode_iec104,
            decode_opcua,
            decode_dnp3,
        ):
            result = decoder(view, limits)
            if result:
                return result
        return ()
    return decode_dcp(view, limits)


def enrich_capture(
    path: Path,
    *,
    limits: EnrichmentLimits = ENRICHMENT_LIMITS,
    capture_limits: CaptureLimits = CAPTURE_LIMITS,
) -> dict[str, Any]:
    """Read one capture and return canonical, metadata-only enrichment contract 1.

    Nothing is published during scanning. File provenance comes from the original
    bounded scan; a failure cannot return a valid partial enrichment artifact.
    """
    records: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    skipped: Counter[str] = Counter()
    packet_count = 0
    retained_bytes = 0

    def consume(packet: Packet) -> None:
        nonlocal packet_count, retained_bytes
        located = packet_view(packet, capture_limits)
        if located.view is None:
            skipped[located.reason or "UNASSESSED"] += 1
            return
        decoded = decode(located.view, limits)
        if not decoded:
            skipped["NO_SUPPORTED_PROTOCOL_CANDIDATE"] += 1
            return
        packet_count += 1
        for result in decoded:
            check_limit("enrichment_records", len(records) + 1, limits.records)
            item = {
                "protocol": result.protocol,
                "recognition_method": result.recognition_method,
                "status": result.status.value,
                "message_category": result.message_category,
                "fields": dict(result.fields),
                "record_offset": result.record_offset,
                "reason": result.reason,
                "limitations": list(result.limitations),
                "packet": _reference(packet),
                "source_ip": located.source_ip,
                "destination_ip": located.destination_ip,
                "source_port": located.view.source_port,
                "destination_port": located.view.destination_port,
                "vlans": list(located.vlans),
            }
            retained_bytes += len(_canonical(item))
            check_limit("enrichment_metadata_bytes", retained_bytes, limits.output_bytes)
            records.append(item)
            counts[result.protocol + ":" + result.status.value] += 1

    capture = scan_capture(path, consume, capture_limits)
    report: dict[str, Any] = {
        "enrichment_version": 1,
        "decoder_version": 2,
        "capture_sha256": capture["sha256"],
        "capture": capture,
        "observations_sha256": None,
        "supported_protocols": list(SUPPORTED_PROTOCOLS),
        "records": records,
        "counts": dict(sorted(counts.items())),
        "packets_with_records": packet_count,
        "skipped_packets": dict(sorted(skipped.items())),
        "limits": asdict(limits),
        "limitations": list(_LIMITATIONS),
    }
    report["enrichment_sha256"] = digest(report)
    output = json.dumps(report, sort_keys=True, ensure_ascii=True, indent=2, allow_nan=False) + "\n"
    check_limit("enrichment_output_bytes", len(output.encode("utf-8")), limits.output_bytes)
    return report


def validate_enrichment(value: dict[str, Any]) -> None:
    """Validate finite v1 metadata before consumption; hashes are not authenticity."""
    from otarchguard.capture.protocols.validation import validate

    validate(value)
