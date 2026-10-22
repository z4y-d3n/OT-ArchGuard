"""Explicit interface-state graph; no inferred links, routes or relays."""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal

from otarchguard.contract import ResourceLimits
from otarchguard.diagnostics import check_limit
from otarchguard.domain import ArchitectureSnapshot


@dataclass(frozen=True, order=True, slots=True)
class State:
    interface_id: str
    phase: Literal["egress", "ingress"]


@dataclass(frozen=True, slots=True)
class Edge:
    id: str
    source: State
    target: State
    kind: Literal["transport", "forwarding"]
    conduit_id: str | None


@dataclass(frozen=True, slots=True)
class StateGraph:
    adjacency: Mapping[State, tuple[Edge, ...]]
    edges: Mapping[str, Edge]
    origins: Mapping[str, tuple[State, ...]]


def build_graph(model: ArchitectureSnapshot, limits: ResourceLimits) -> StateGraph:
    check_limit("interfaces", len(model.interfaces), limits.interfaces)
    check_limit("edges", len(model.transport_edges) + len(model.forwarding_edges), limits.edges)
    adjacency: dict[State, list[Edge]] = {}
    origins: dict[str, list[State]] = {a.id: [] for a in model.assets}
    for interface in model.interfaces:
        phases: tuple[Literal["egress", "ingress"], ...] = ("egress", "ingress")
        for phase in phases:
            state = State(interface.id, phase)
            adjacency[state] = []
            if phase == "egress":
                origins[interface.asset_id].append(state)
    edges: dict[str, Edge] = {}
    for transport in model.transport_edges:
        edge = Edge(
            transport.id,
            State(transport.source_interface_id, "egress"),
            State(transport.destination_interface_id, "ingress"),
            "transport",
            transport.conduit_id,
        )
        edges[edge.id] = edge
        adjacency[edge.source].append(edge)
    for forwarding in model.forwarding_edges:
        edge = Edge(
            forwarding.id,
            State(forwarding.ingress_interface_id, "ingress"),
            State(forwarding.egress_interface_id, "egress"),
            "forwarding",
            forwarding.conduit_id,
        )
        edges[edge.id] = edge
        adjacency[edge.source].append(edge)
    return StateGraph(
        MappingProxyType(
            {
                state: tuple(sorted(items, key=lambda e: (e.target, e.id)))
                for state, items in adjacency.items()
            }
        ),
        MappingProxyType(edges),
        MappingProxyType({asset: tuple(sorted(states)) for asset, states in origins.items()}),
    )
