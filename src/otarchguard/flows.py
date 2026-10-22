"""Exact normalized interval observations and set operations, independent of atom IDs."""

from dataclasses import dataclass

from otarchguard.domain import PortInterval, ProtocolValue
from otarchguard.normalization import normalize_ports
from otarchguard.reachability import QueryResult


@dataclass(frozen=True, order=True, slots=True)
class FlowInterval:
    source_asset_id: str
    destination_asset_id: str
    service_id: str
    protocol: ProtocolValue
    start: int
    end: int


type FlowKey = tuple[str, str, str, ProtocolValue]


def key(flow: FlowInterval) -> FlowKey:
    return (flow.source_asset_id, flow.destination_asset_id, flow.service_id, flow.protocol)


def merge(flows: tuple[FlowInterval, ...]) -> tuple[FlowInterval, ...]:
    groups: dict[FlowKey, list[PortInterval]] = {}
    for flow in flows:
        groups.setdefault(key(flow), []).append(PortInterval(start=flow.start, end=flow.end))
    return tuple(
        FlowInterval(*identity, interval.start, interval.end)
        for identity, intervals in sorted(groups.items())
        for interval in normalize_ports(tuple(intervals))
    )


def observations(
    queries: tuple[QueryResult, ...], reachable: bool = True
) -> tuple[FlowInterval, ...]:
    return merge(
        tuple(
            FlowInterval(
                q.source_asset_id, q.destination_asset_id, q.service_id, q.protocol, i.start, i.end
            )
            for q in queries
            for i in q.intervals
            if i.reachable == reachable
        )
    )


def difference(
    left: tuple[FlowInterval, ...], right: tuple[FlowInterval, ...]
) -> tuple[FlowInterval, ...]:
    right_groups: dict[FlowKey, list[FlowInterval]] = {}
    for flow in merge(right):
        right_groups.setdefault(key(flow), []).append(flow)
    result: list[FlowInterval] = []
    for flow in merge(left):
        start = flow.start
        for removed in right_groups.get(key(flow), []):
            if removed.end < start:
                continue
            if removed.start > flow.end:
                break
            if start < removed.start:
                result.append(FlowInterval(*key(flow), start, removed.start - 1))
            start = max(start, removed.end + 1)
            if start > flow.end:
                break
        if start <= flow.end:
            result.append(FlowInterval(*key(flow), start, flow.end))
    return tuple(result)


def intersection(
    left: tuple[FlowInterval, ...], right: tuple[FlowInterval, ...]
) -> tuple[FlowInterval, ...]:
    return difference(left, difference(left, right))
