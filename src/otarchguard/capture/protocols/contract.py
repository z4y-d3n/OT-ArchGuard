"""Independent version-1, shallow protocol-header enrichment contract.

Views are transient. Records contain only allowlisted header scalars, never bytes.
Structure is not authenticity, authorization, session success or asset ownership.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal


class Status(StrEnum):
    PORT_HINT = "PORT_HINT"
    ETHERTYPE_HINT = "ETHERTYPE_HINT"
    STRUCTURALLY_VALID = "STRUCTURALLY_VALID"
    TRUNCATED = "TRUNCATED"
    MALFORMED = "MALFORMED"
    UNSUPPORTED_VARIANT = "UNSUPPORTED_VARIANT"


@dataclass(frozen=True, slots=True)
class EnrichmentLimits:
    """Hard ceilings; excess output fails without publishing a partial artifact."""

    view_bytes: int = 16_384
    records_per_packet: int = 8
    dcp_blocks: int = 64
    records: int = 20_000
    output_bytes: int = 16 * 1024 * 1024

    def __post_init__(self) -> None:
        ceilings = (
            (self.view_bytes, 16_384),
            (self.records_per_packet, 8),
            (self.dcp_blocks, 64),
            (self.records, 20_000),
            (self.output_bytes, 16 * 1024 * 1024),
        )
        if any(type(v) is not int or not 1 <= v <= maximum for v, maximum in ceilings):
            raise ValueError(
                "Enrichment limits must be positive integers within contract ceilings."
            )


ENRICHMENT_LIMITS = EnrichmentLimits()


@dataclass(frozen=True, slots=True)
class ProtocolView:
    """One complete supported transport payload or Ethernet protocol data view.

    The caller must validate outer framing first. No stream/session state exists.
    The packet adapter is the normal capture entry point. Nonstandard Modbus ports
    require an explicit inspect_modbus choice, never a search for byte offsets.
    """

    data: bytes
    transport: Literal["tcp", "ethernet"]
    source_port: int | None = None
    destination_port: int | None = None
    ethertype: int | None = None
    inspect_modbus: bool = False


HeaderValue = int | str | bool


@dataclass(frozen=True, slots=True)
class EnrichmentRecord:
    protocol: str
    recognition_method: str
    status: Status
    message_category: str | None = None
    fields: tuple[tuple[str, HeaderValue], ...] = ()
    record_offset: int = 0
    reason: str | None = None
    limitations: tuple[str, ...] = ()


def record(
    protocol: str,
    method: str,
    status: Status,
    *,
    offset: int = 0,
    reason: str | None = None,
    category: str | None = None,
    fields: tuple[tuple[str, HeaderValue], ...] = (),
    limitations: tuple[str, ...] = (),
) -> EnrichmentRecord:
    return EnrichmentRecord(protocol, method, status, category, fields, offset, reason, limitations)
