"""Unordered original-endpoint policy with deny precedence on every explicit edge."""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from otarchguard.contract import ResourceLimits
from otarchguard.diagnostics import check_limit
from otarchguard.domain import ArchitectureSnapshot, ProtocolValue
from otarchguard.intervals import PortSet
from otarchguard.validation import expand_selector


@dataclass(frozen=True, slots=True)
class CompiledRule:
    id: str
    source: frozenset[str]
    destination: frozenset[str]
    protocol: ProtocolValue
    ports: PortSet
    effect: str


@dataclass(frozen=True, slots=True)
class Decision:
    allow_rule_ids: tuple[str, ...]
    deny_rule_ids: tuple[str, ...]

    @property
    def permitted(self) -> bool:
        return bool(self.allow_rule_ids) and not self.deny_rule_ids


@dataclass(slots=True)
class Work:
    limits: ResourceLimits
    state_edge_visits: int = 0
    edge_rule_atom_checks: int = 0

    def visit(self) -> None:
        self.state_edge_visits += 1
        check_limit("state_edge_visits", self.state_edge_visits, self.limits.state_edge_visits)

    def predicate(self) -> None:
        self.edge_rule_atom_checks += 1
        check_limit(
            "edge_rule_atom_checks", self.edge_rule_atom_checks, self.limits.edge_rule_atom_checks
        )


def compile_policy(
    model: ArchitectureSnapshot, limits: ResourceLimits
) -> Mapping[str, tuple[CompiledRule, ...]]:
    check_limit("rules", len(model.rules), limits.rules)
    associations = sum(len(rule.edge_ids) for rule in model.rules)
    check_limit("edge_rule_associations", associations, limits.edge_rule_associations)
    assets, zones = {a.id: a for a in model.assets}, {z.id: z for z in model.zones}
    by_edge: dict[str, list[CompiledRule]] = {}
    for rule in sorted(model.rules, key=lambda r: r.id):
        compiled = CompiledRule(
            rule.id,
            frozenset(expand_selector(rule.source, assets, zones)),
            frozenset(expand_selector(rule.destination, assets, zones)),
            rule.protocol,
            PortSet.from_intervals(rule.destination_ports),
            rule.effect,
        )
        for edge in rule.edge_ids:
            by_edge.setdefault(edge, []).append(compiled)
    return MappingProxyType({edge: tuple(items) for edge, items in by_edge.items()})


def decide(
    rules: tuple[CompiledRule, ...],
    source: str,
    destination: str,
    protocol: ProtocolValue,
    port: int,
    work: Work,
) -> Decision:
    allow: list[str] = []
    deny: list[str] = []
    for rule in rules:
        work.predicate()
        if (
            source in rule.source
            and destination in rule.destination
            and protocol == rule.protocol
            and rule.ports.contains(port)
        ):
            (allow if rule.effect == "allow" else deny).append(rule.id)
    return Decision(tuple(allow), tuple(deny))
