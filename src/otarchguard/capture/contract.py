"""Version-1 capture budgets and transient packet records, separate from YAML limits."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CaptureLimits:
    """Conservative rejection budgets, not demonstrated throughput guarantees.

    packet_bytes bounds retained captured bytes, not a packet's reported wire length.
    PCAPNG block buffers are independently bounded; metadata is never exported.
    """

    file_bytes: int = 512 * 1024 * 1024
    packet_bytes: int = 262_144
    packets: int = 1_000_000
    blocks: int = 2_000_000
    block_bytes: int = 262_144 + 65_536 + 64
    interfaces: int = 256
    metadata_bytes: int = 65_536
    hosts: int = 20_000
    flows: int = 50_000
    conversations: int = 50_000
    aggregation_bytes: int = 64 * 1024 * 1024
    output_bytes: int = 64 * 1024 * 1024
    pages: int = 2048
    rows_per_page: int = 100
    decisions: int = 20_000
    queries: int = 128
    comparison_work: int = 5_000_000
    packet_samples: int = 8
    ipv6_extensions: int = 8


CAPTURE_LIMITS = CaptureLimits()


@dataclass(frozen=True, slots=True)
class Timestamp:
    """Original unsigned ticks and exact resolution, with signed whole-second offset."""

    ticks: int
    denominator: int
    offset_seconds: int = 0


@dataclass(frozen=True, slots=True)
class Packet:
    """Transient frame; consumers must not export its raw payload.

    index is one-based; offset identifies the record/block header in the file.
    section and interface are zero-based, with interface local to its section.
    """

    index: int
    offset: int
    section: int
    interface: int
    linktype: int
    timestamp: Timestamp | None
    captured_length: int
    original_length: int
    data: bytes
    link_errors: bool = False
    offloaded: bool = False
