"""Bounded exact initiation reachability with deterministic BFS and witness replay."""

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass

from otarchguard.api import ValidatedArchitecture
from otarchguard.contract import RESOURCE_LIMITS, DiagnosticCategory, ResourceLimits
from otarchguard.diagnostics import check_limit, fail
from otarchguard.domain import ArchitectureSnapshot, PortInterval, ProtocolValue
from otarchguard.graph import Edge, State, build_graph
from otarchguard.intervals import PortSet, partition
from otarchguard.policy import Decision, Work, compile_policy, decide


@dataclass(frozen=True, slots=True)
class Endpoint:
    state: State
    asset_id: str
    placement_zone_id: str
    ipv4: str


@dataclass(frozen=True, slots=True)
class WitnessStep:
    edge_id: str
    kind: str
    source: Endpoint
    target: Endpoint
    conduit_id: str | None
    allow_rule_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Witness:
    snapshot_sha256: str
    source_asset_id: str
    destination_asset_id: str
    service_id: str
    protocol: ProtocolValue
    start: int
    end: int
    steps: tuple[WitnessStep, ...]


@dataclass(frozen=True, slots=True)
class BlockedEdge:
    edge_id: str
    reason: str
    allow_rule_ids: tuple[str, ...]
    deny_rule_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class UnreachableDiagnostics:
    reason: str
    structural_path_exists: bool
    blocked_edges: tuple[BlockedEdge, ...]
    blocked_edge_count: int
    truncated: bool
    limitation: str = "Frontier evidence is not a unique root cause or a guaranteed fix."


@dataclass(frozen=True, slots=True)
class IntervalResult:
    start: int
    end: int
    reachable: bool
    witness: Witness | None
    diagnostics: UnreachableDiagnostics | None


@dataclass(frozen=True, slots=True)
class QueryResult:
    source_asset_id: str
    destination_asset_id: str
    service_id: str
    protocol: ProtocolValue
    intervals: tuple[IntervalResult, ...]


class ReachabilityEngine:
    """Run-local state/caches; accepts only a fully validated model from api.py."""

    def __init__(
        self,
        validated: ValidatedArchitecture,
        service_ids: frozenset[str] | None = None,
        limits: ResourceLimits = RESOURCE_LIMITS,
        *,
        partition_peers: tuple[ArchitectureSnapshot, ...] = (),
    ) -> None:
        self.validated = validated
        self.model = validated.model
        self.limits = limits
        self.services = {s.id: s for s in self.model.services}
        self.requested = service_ids if service_ids is not None else frozenset(self.services)
        if not self.requested <= self.services.keys():
            fail("MISSING_REFERENCE", "$", "Requested listener does not exist.")
        self.atoms = partition(self.model, self.requested, limits, peers=partition_peers)
        port_sets = {
            identity: PortSet.from_intervals(self.services[identity].destination_ports)
            for identity in self.requested
        }
        self.service_atoms = {
            identity: tuple(
                a
                for a in self.atoms[self.services[identity].protocol]
                if port_sets[identity].contains(a.start)
            )
            for identity in sorted(self.requested)
        }
        self.graph = build_graph(self.model, limits)
        self.policy = compile_policy(self.model, limits)
        self.interfaces = {i.id: i for i in self.model.interfaces}
        self.associations = sum(len(r.edge_ids) for r in self.model.rules)
        self.queries_reserved = 0
        self.work = Work(limits)

    def ensure_capacity(self, queries: int) -> None:
        """Prospective upper bounds checked before query products/search allocation."""
        states_edges = len(self.graph.adjacency) + len(self.graph.edges)
        check_limit("state_edge_visits", queries * 3 * states_edges, self.limits.state_edge_visits)
        check_limit(
            "edge_rule_atom_checks", queries * self.associations, self.limits.edge_rule_atom_checks
        )

    def _reserve(self, queries: int) -> None:
        self.ensure_capacity(self.queries_reserved + queries)
        self.queries_reserved += queries

    def evaluate(
        self,
        source_asset_id: str,
        service_id: str,
        *,
        interval_observer: Callable[[IntervalResult], None] | None = None,
    ) -> QueryResult:
        """Evaluate exactly; an optional consumer may reject before retaining each interval.

        The observer cannot replace results or change search/policy semantics. A
        raised exception aborts the query before the next atom is evaluated.
        """
        if source_asset_id not in self.graph.origins or service_id not in self.requested:
            fail(
                "MISSING_REFERENCE",
                "$",
                "Query origin/listener does not exist in this run's scope.",
            )
        service = self.services[service_id]
        if source_asset_id == service.asset_id:
            fail(
                "UNSUPPORTED_QUERY",
                "$",
                "Standalone self-asset queries are outside this model.",
                DiagnosticCategory.UNSUPPORTED_MODEL,
            )
        if not self.graph.origins[source_asset_id]:
            fail("EMPTY_QUERY_SCOPE", "$", "Query origin needs at least one declared interface.")
        atoms = self.service_atoms[service_id]
        self._reserve(len(atoms))
        results: list[IntervalResult] = []
        for atom in atoms:
            result = self._atom(source_asset_id, service_id, atom)
            if interval_observer is not None:
                interval_observer(result)
            results.append(result)
        return QueryResult(
            source_asset_id, service.asset_id, service_id, service.protocol, tuple(results)
        )

    def _decisions(self, source: str, service_id: str, port: int) -> Callable[[Edge], Decision]:
        service = self.services[service_id]
        cache: dict[str, Decision] = {}

        def decision(edge: Edge) -> Decision:
            if edge.id not in cache:
                cache[edge.id] = decide(
                    self.policy.get(edge.id, ()),
                    source,
                    service.asset_id,
                    service.protocol,
                    port,
                    self.work,
                )
            return cache[edge.id]

        return decision

    def _search(
        self,
        source: str,
        goal: State,
        permitted: Callable[[Edge], bool],
    ) -> tuple[tuple[Edge, ...] | None, set[State]]:
        starts = self.graph.origins[source]
        queue = deque(starts)
        predecessors: dict[State, Edge | None] = dict.fromkeys(starts)
        while queue:
            current = queue.popleft()
            self.work.visit()
            if current == goal:
                path: list[Edge] = []
                while (edge := predecessors[current]) is not None:
                    path.append(edge)
                    current = edge.source
                return tuple(reversed(path)), set(predecessors)
            for edge in self.graph.adjacency[current]:
                self.work.visit()
                if permitted(edge) and edge.target not in predecessors:
                    predecessors[edge.target] = edge
                    queue.append(edge.target)
        return None, set(predecessors)

    def _endpoint(self, state: State) -> Endpoint:
        interface = self.interfaces[state.interface_id]
        return Endpoint(state, interface.asset_id, interface.placement_zone_id, interface.ipv4)

    def _step(self, edge: Edge, decision: Decision) -> WitnessStep:
        return WitnessStep(
            edge.id,
            edge.kind,
            self._endpoint(edge.source),
            self._endpoint(edge.target),
            edge.conduit_id,
            decision.allow_rule_ids,
        )

    def _atom(self, source: str, service_id: str, atom: PortInterval) -> IntervalResult:
        service = self.services[service_id]
        goal = State(service.interface_id, "ingress")
        decisions = self._decisions(source, service_id, atom.start)
        blocked: dict[str, BlockedEdge] = {}

        def permitted(edge: Edge) -> bool:
            decision = decisions(edge)
            if not decision.permitted:
                blocked[edge.id] = BlockedEdge(
                    edge.id,
                    "explicit_deny" if decision.deny_rule_ids else "missing_permit",
                    decision.allow_rule_ids,
                    decision.deny_rule_ids,
                )
            return decision.permitted

        path, visited = self._search(source, goal, permitted)
        if path is not None:
            witness = Witness(
                self.validated.sha256,
                source,
                service.asset_id,
                service_id,
                service.protocol,
                atom.start,
                atom.end,
                tuple(self._step(edge, decisions(edge)) for edge in path),
            )
            if not self._replay(witness, decisions):
                fail(
                    "INTERNAL_ERROR",
                    "$",
                    "Generated witness failed replay; no result is available.",
                    DiagnosticCategory.EXECUTION_ERROR,
                )
            return IntervalResult(atom.start, atom.end, True, witness, None)
        structural, _ = self._search(source, goal, lambda edge: True)
        frontier = tuple(
            blocked[key] for key in sorted(blocked) if self.graph.edges[key].target not in visited
        )
        sample = frontier[: self.limits.diagnostic_edges_per_query]
        diagnostic = UnreachableDiagnostics(
            "no_structural_path" if structural is None else "no_permitted_path",
            structural is not None,
            sample,
            len(frontier),
            len(sample) < len(frontier),
        )
        return IntervalResult(atom.start, atom.end, False, None, diagnostic)

    def _replay(self, witness: Witness, decisions: Callable[[Edge], Decision]) -> bool:
        service = self.services.get(witness.service_id)
        if (
            service is None
            or witness.snapshot_sha256 != self.validated.sha256
            or witness.source_asset_id not in self.graph.origins
            or witness.source_asset_id == service.asset_id
            or witness.destination_asset_id != service.asset_id
            or witness.protocol != service.protocol
            or not any(
                (a.start, a.end) == (witness.start, witness.end)
                for a in self.service_atoms.get(service.id, ())
            )
            or not witness.steps
        ):
            return False
        current = witness.steps[0].source.state
        if current not in self.graph.origins[witness.source_asset_id]:
            return False
        for step in witness.steps:
            self.work.visit()
            edge = self.graph.edges.get(step.edge_id)
            if edge is None or edge.source != current:
                return False
            decision = decisions(edge)
            if not decision.permitted or step != self._step(edge, decision):
                return False
            current = edge.target
        return current == State(service.interface_id, "ingress")

    def replay(self, witness: Witness) -> bool:
        """Verify endpoints, interval, continuity, provenance and permissions anew."""
        self._reserve(1)
        if witness.service_id not in self.requested:
            return False
        return self._replay(
            witness, self._decisions(witness.source_asset_id, witness.service_id, witness.start)
        )


def evaluate_query(
    validated: ValidatedArchitecture,
    source_asset_id: str,
    service_id: str,
    limits: ResourceLimits = RESOURCE_LIMITS,
) -> QueryResult:
    return ReachabilityEngine(validated, frozenset({service_id}), limits).evaluate(
        source_asset_id, service_id
    )
