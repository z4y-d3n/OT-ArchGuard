"""Exact protocol/port atoms for requested listeners, with no per-port expansion."""

from bisect import bisect_right
from collections.abc import Iterable
from dataclasses import dataclass

from otarchguard.contract import ResourceLimits
from otarchguard.diagnostics import check_limit
from otarchguard.domain import (
    ArchitectureSnapshot,
    EnforcementRule,
    PortInterval,
    ProtocolValue,
    Service,
)
from otarchguard.normalization import normalize_ports


@dataclass(frozen=True, slots=True)
class PortSet:
    intervals: tuple[tuple[int, int], ...]
    starts: tuple[int, ...]

    @classmethod
    def from_intervals(cls, intervals: tuple[PortInterval, ...]) -> "PortSet":
        pairs = tuple((p.start, p.end) for p in normalize_ports(intervals))
        return cls(pairs, tuple(p[0] for p in pairs))

    def contains(self, port: int) -> bool:
        index = bisect_right(self.starts, port) - 1
        return index >= 0 and port <= self.intervals[index][1]


def partition(
    model: ArchitectureSnapshot,
    service_ids: frozenset[str],
    limits: ResourceLimits,
    *,
    peers: tuple[ArchitectureSnapshot, ...] = (),
) -> dict[ProtocolValue, tuple[PortInterval, ...]]:
    result: dict[ProtocolValue, tuple[PortInterval, ...]] = {}
    total = 0
    protocols: tuple[ProtocolValue, ...] = ("tcp", "udp")
    for protocol in protocols:
        boundaries = {1, 65536}
        requested: list[PortInterval] = []
        items: list[Service | EnforcementRule] = []
        for snapshot in (model, *peers):
            items.extend(snapshot.services)
            items.extend(snapshot.rules)
        declarations: Iterable[tuple[str, tuple[PortInterval, ...]]] = (
            (item.protocol, item.destination_ports) for item in items
        )
        for item_protocol, ports in declarations:
            if item_protocol == protocol:
                for interval in ports:
                    boundaries.update((interval.start, interval.end + 1))
        for service in model.services:
            if service.id in service_ids and service.protocol == protocol:
                requested.extend(service.destination_ports)
        requested_set = PortSet.from_intervals(tuple(requested))
        ordered = sorted(boundaries)
        atoms: list[PortInterval] = []
        for low, upper in zip(ordered, ordered[1:], strict=False):
            if requested_set.contains(low):
                total += 1
                check_limit("protocol_port_atoms", total, limits.protocol_port_atoms)
                atoms.append(PortInterval(start=low, end=upper - 1))
        result[protocol] = tuple(atoms)
    return result
