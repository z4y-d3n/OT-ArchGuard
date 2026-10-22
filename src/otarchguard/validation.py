"""Structural declarations only: references, placement, SUC, metadata and intent scope."""

import ipaddress
import re
from collections.abc import Mapping
from typing import Protocol

from otarchguard.contract import DiagnosticCategory
from otarchguard.diagnostics import fail
from otarchguard.domain import (
    ArchitectureSnapshot,
    Asset,
    AssetSelector,
    CommunicationIntent,
    Conduit,
    ExposureScenario,
    ForwardingEdge,
    Interface,
    ModeledAccessPoint,
    PortInterval,
    Selector,
    Service,
    TransportEdge,
    Zone,
    ZoneSelector,
)
from otarchguard.normalization import normalize_ports


class Identified(Protocol):
    @property
    def id(self) -> str: ...


def _index[T: Identified](records: tuple[T, ...], path: str) -> dict[str, T]:
    result: dict[str, T] = {}
    for index, record in enumerate(records):
        if record.id in result:
            fail(
                "DUPLICATE_ID",
                f"{path}[{index}].id",
                "Identifier already exists in this entity kind.",
            )
        result[record.id] = record
    return result


def _ref[T: Identified](catalog: Mapping[str, T], identity: str, path: str) -> T:
    if identity not in catalog:
        fail("MISSING_REFERENCE", path, "Referenced entity does not exist in the required kind.")
    return catalog[identity]


def _distinct(values: tuple[str, ...], path: str) -> None:
    if len(set(values)) != len(values):
        fail("DUPLICATE_ITEM", path, "Set-like sequence contains duplicate items.")


def _references[T: Identified](
    values: tuple[str, ...], catalog: Mapping[str, T], path: str
) -> None:
    _distinct(values, path)
    for index, value in enumerate(values):
        _ref(catalog, value, f"{path}[{index}]")


def expand_selector(
    selector: Selector,
    assets: Mapping[str, Asset],
    zones: Mapping[str, Zone],
    path: str = "$",
) -> tuple[str, ...]:
    """Resolve administrative ownership, never interface attachments; reject vacuous sets."""
    if isinstance(selector, AssetSelector):
        _references(selector.asset_ids, assets, f"{path}.asset_ids")
        result = selector.asset_ids
    elif isinstance(selector, ZoneSelector):
        _references(selector.zone_ids, zones, f"{path}.zone_ids")
        selected = set(selector.zone_ids)
        result = tuple(a.id for a in assets.values() if a.zone_id in selected)
    else:
        result = tuple(assets)
    if not result:
        fail("INVALID_SELECTOR", path, "Selector must expand to at least one asset.")
    return tuple(sorted(result))


def _ports(intervals: tuple[PortInterval, ...], path: str) -> None:
    seen: set[tuple[int, int]] = set()
    for index, interval in enumerate(intervals):
        if interval.start > interval.end:
            fail("INVALID_PORT", f"{path}[{index}]", "Port interval start must not exceed end.")
        pair = (interval.start, interval.end)
        if pair in seen:
            fail("DUPLICATE_ITEM", path, "Repeated identical port interval.")
        seen.add(pair)


def _address(value: str, path: str) -> ipaddress.IPv4Interface:
    try:
        if ":" in value:
            ipaddress.IPv6Interface(value)
            fail(
                "UNSUPPORTED_ADDRESS_FAMILY",
                path,
                "IPv6 is outside schema-v1 support.",
                DiagnosticCategory.UNSUPPORTED_MODEL,
            )
        if re.fullmatch(r"[0-9]+(?:\.[0-9]+){3}/[0-9]{1,2}", value, re.ASCII) is None:
            raise ValueError
        address = ipaddress.IPv4Interface(value)
    except ValueError:
        fail(
            "INVALID_ADDRESS",
            path,
            "Expected an IPv4 host address with decimal prefix length 0–32.",
        )
    ip = address.ip
    if (
        ip.is_multicast
        or ip.is_unspecified
        or ip.is_loopback
        or int(ip) == 0xFFFFFFFF
        or (address.network.prefixlen < 31 and ip == address.network.broadcast_address)
    ):
        fail(
            "UNSUPPORTED_ADDRESS_KIND",
            path,
            "Only modeled IPv4 unicast addresses are supported.",
            DiagnosticCategory.UNSUPPORTED_MODEL,
        )
    return address


def edge_interfaces(edge: TransportEdge | ForwardingEdge) -> tuple[str, str]:
    if isinstance(edge, TransportEdge):
        return edge.source_interface_id, edge.destination_interface_id
    return edge.ingress_interface_id, edge.egress_interface_id


def _safety(snapshot: ArchitectureSnapshot) -> None:
    for index, zone in enumerate(snapshot.zones):
        path = f"$.zones[{index}]"
        values = {a.safety_classification for a in snapshot.assets if a.zone_id == zone.id}
        designation = zone.safety_designation
        mixed = {"safety_related", "non_safety"} <= values
        invalid = (
            (mixed and designation != "mixed_safety")
            or (not mixed and "unassessed" in values and designation != "unassessed")
            or (designation == "non_safety" and "safety_related" in values)
            or (designation == "safety" and "non_safety" in values)
            or (designation == "mixed_safety" and zone.mixed_safety_rationale is None)
            or (designation != "mixed_safety" and zone.mixed_safety_rationale is not None)
        )
        if invalid:
            fail(
                "SAFETY_INCONSISTENCY",
                path,
                "Safety designation/rationale conflicts with owned assets.",
            )


def validate_structure(snapshot: ArchitectureSnapshot) -> None:
    """Fail fast on fatal inconsistencies; never evaluate whether a path exists."""
    zones = _index(snapshot.zones, "$.zones")
    assets = _index(snapshot.assets, "$.assets")
    interfaces = _index(snapshot.interfaces, "$.interfaces")
    conduits = _index(snapshot.conduits, "$.conduits")
    services = _index(snapshot.services, "$.services")
    _index(snapshot.rules, "$.rules")
    intents = _index(snapshot.intents, "$.intents")
    _index(snapshot.scenarios, "$.scenarios")
    _index(snapshot.suc.access_points, "$.suc.access_points")
    _index(snapshot.suc.external_dependencies, "$.suc.external_dependencies")
    edges: dict[str, TransportEdge | ForwardingEdge] = {}
    edge_groups: tuple[tuple[str, tuple[TransportEdge | ForwardingEdge, ...]], ...] = (
        ("transport_edges", snapshot.transport_edges),
        ("forwarding_edges", snapshot.forwarding_edges),
    )
    for name, records in edge_groups:
        for index, edge in enumerate(records):
            if edge.id in edges:
                fail(
                    "DUPLICATE_ID",
                    f"$.{name}[{index}].id",
                    "Edge ID must be globally unique across both kinds.",
                )
            edges[edge.id] = edge
    for index, asset in enumerate(snapshot.assets):
        zone = _ref(zones, asset.zone_id, f"$.assets[{index}].zone_id")
        if asset.scope != zone.scope:
            fail(
                "SCOPE_MISMATCH",
                f"$.assets[{index}].scope",
                "Asset and owner zone must have equal scope.",
            )
    hosts: set[ipaddress.IPv4Address] = set()
    for index, interface in enumerate(snapshot.interfaces):
        path = f"$.interfaces[{index}]"
        asset = _ref(assets, interface.asset_id, f"{path}.asset_id")
        _ref(zones, interface.placement_zone_id, f"{path}.placement_zone_id")
        if asset.kind == "endpoint" and interface.placement_zone_id != asset.zone_id:
            fail(
                "INVALID_PLACEMENT",
                f"{path}.placement_zone_id",
                "Endpoint interface must use its owner zone.",
            )
        address = _address(interface.ipv4, f"{path}.ipv4")
        if address.ip in hosts:
            fail(
                "DUPLICATE_ADDRESS",
                f"{path}.ipv4",
                "IPv4 host address already exists in this address space.",
            )
        hosts.add(address.ip)
    _safety(snapshot)
    for index, conduit in enumerate(snapshot.conduits):
        path = f"$.conduits[{index}].zone_ids"
        _references(conduit.zone_ids, zones, path)
        if len(conduit.zone_ids) != 2:
            fail("INVALID_CONDUIT_PAIR", path, "Exactly two distinct zones are required.")
    for name, records in edge_groups:
        for index, edge in enumerate(records):
            path = f"$.{name}[{index}]"
            left_id, right_id = edge_interfaces(edge)
            left_field, right_field = (
                ("source_interface_id", "destination_interface_id")
                if isinstance(edge, TransportEdge)
                else ("ingress_interface_id", "egress_interface_id")
            )
            left = _ref(interfaces, left_id, f"{path}.{left_field}")
            right = _ref(interfaces, right_id, f"{path}.{right_field}")
            if isinstance(edge, TransportEdge):
                if left.asset_id == right.asset_id:
                    fail("INVALID_EDGE", path, "Transport must connect different assets.")
            else:
                if left_id == right_id:
                    fail(
                        "UNSUPPORTED_FORWARDING",
                        path,
                        "Same-interface hairpin forwarding is unsupported.",
                        DiagnosticCategory.UNSUPPORTED_MODEL,
                    )
                if (
                    left.asset_id != right.asset_id
                    or assets[left.asset_id].kind != "boundary_device"
                ):
                    fail(
                        "INVALID_EDGE",
                        path,
                        "Forwarding requires distinct interfaces of one boundary device.",
                    )
            pair = {left.placement_zone_id, right.placement_zone_id}
            edge_conduit: Conduit | None = None
            if edge.conduit_id is not None:
                edge_conduit = _ref(conduits, edge.conduit_id, f"{path}.conduit_id")
            if (len(pair) == 1 and edge_conduit is not None) or (
                len(pair) == 2 and (edge_conduit is None or set(edge_conduit.zone_ids) != pair)
            ):
                fail(
                    "INVALID_CONDUIT_PAIR",
                    f"{path}.conduit_id",
                    "Conduit must match the cross-placement pair; same-zone edges have none.",
                )
    for index, service in enumerate(snapshot.services):
        path = f"$.services[{index}]"
        _ref(assets, service.asset_id, f"{path}.asset_id")
        interface = _ref(interfaces, service.interface_id, f"{path}.interface_id")
        if interface.asset_id != service.asset_id:
            fail(
                "INVALID_SERVICE_BINDING",
                f"{path}.interface_id",
                "Listener interface must belong to its declared asset.",
            )
        _ports(service.destination_ports, f"{path}.destination_ports")
    for index, rule in enumerate(snapshot.rules):
        path = f"$.rules[{index}]"
        _references(rule.edge_ids, edges, f"{path}.edge_ids")
        expand_selector(rule.source, assets, zones, f"{path}.source")
        expand_selector(rule.destination, assets, zones, f"{path}.destination")
        _ports(rule.destination_ports, f"{path}.destination_ports")
    _access_points(snapshot, assets, zones, interfaces, edges)
    for index, dependency in enumerate(snapshot.suc.external_dependencies):
        path = f"$.suc.external_dependencies[{index}]"
        _references(dependency.external_asset_ids, assets, f"{path}.external_asset_ids")
        _references(dependency.required_intent_ids, intents, f"{path}.required_intent_ids")
        if any(assets[a].scope != "external" for a in dependency.external_asset_ids) or any(
            intents[i].kind != "required" for i in dependency.required_intent_ids
        ):
            fail(
                "INVALID_DEPENDENCY",
                path,
                "Dependencies reference external assets and required intents only.",
            )
    _intent_scopes(snapshot, assets, zones, services)


def _access_points(
    snapshot: ArchitectureSnapshot,
    assets: Mapping[str, Asset],
    zones: Mapping[str, Zone],
    interfaces: Mapping[str, Interface],
    edges: Mapping[str, TransportEdge | ForwardingEdge],
) -> None:
    crossing: set[str] = set()
    for edge in edges.values():
        left, right = (interfaces[i] for i in edge_interfaces(edge))
        if zones[left.placement_zone_id].scope != zones[right.placement_zone_id].scope:
            crossing.add(edge.id)
    covered: set[str] = set()
    for index, access in enumerate(snapshot.suc.access_points):
        if not isinstance(access, ModeledAccessPoint):
            continue
        path = f"$.suc.access_points[{index}]"
        external = _ref(interfaces, access.external_interface_id, f"{path}.external_interface_id")
        internal = _ref(interfaces, access.internal_interface_id, f"{path}.internal_interface_id")
        if (
            zones[external.placement_zone_id].scope != "external"
            or zones[internal.placement_zone_id].scope != "internal"
            or not any(assets[i.asset_id].scope == "internal" for i in (external, internal))
        ):
            fail(
                "INVALID_ACCESS_POINT",
                path,
                "Access-point placement sides/asset scope are inconsistent.",
            )
        _references(access.edge_ids, edges, f"{path}.edge_ids")
        for edge_id in access.edge_ids:
            if (
                set(edge_interfaces(edges[edge_id])) != {external.id, internal.id}
                or edge_id not in crossing
                or edge_id in covered
            ):
                fail(
                    "INVALID_ACCESS_POINT",
                    f"{path}.edge_ids",
                    "Crossing needs unique coverage of this exact interface pair.",
                )
            covered.add(edge_id)
    if covered != crossing:
        fail(
            "INVALID_ACCESS_POINT",
            "$.suc.access_points",
            "Every declared perimeter crossing needs exactly one access-point record.",
        )


def _intent_scopes(
    snapshot: ArchitectureSnapshot,
    assets: Mapping[str, Asset],
    zones: Mapping[str, Zone],
    services: Mapping[str, Service],
) -> None:
    origins_with_interfaces = {i.asset_id for i in snapshot.interfaces}
    # Compact interval index, never individual ports or paths. This checks only
    # contradictions in owner declarations; no edge permissions are evaluated.
    declared: dict[tuple[str, str], list[tuple[str, frozenset[str], tuple[PortInterval, ...]]]] = {}
    source_sets: dict[tuple[str, ...], frozenset[str]] = {}
    service_ports = {
        service.id: normalize_ports(service.destination_ports) for service in services.values()
    }
    scope_groups: tuple[tuple[str, tuple[CommunicationIntent | ExposureScenario, ...]], ...] = (
        ("intents", snapshot.intents),
        ("scenarios", snapshot.scenarios),
    )
    for name, scope_records in scope_groups:
        for index, record in enumerate(scope_records):
            path = f"$.{name}[{index}]"
            if isinstance(record, CommunicationIntent):
                origins = expand_selector(record.source, assets, zones, f"{path}.source")
            else:
                assert isinstance(record, ExposureScenario)
                _references(record.origin_asset_ids, assets, f"{path}.origin_asset_ids")
                origins = record.origin_asset_ids
            _references(record.destination_service_ids, services, f"{path}.destination_service_ids")
            if not set(origins) <= origins_with_interfaces:
                fail(
                    "EMPTY_QUERY_SCOPE",
                    path,
                    "Each selected origin asset needs a declared interface.",
                )
            selected = [services[s] for s in record.destination_service_ids]
            pairs = sum(len(origins) - int(s.asset_id in origins) for s in selected)
            if pairs == 0:
                fail(
                    "EMPTY_QUERY_SCOPE",
                    path,
                    "Scope must retain at least one inter-asset pair after self exclusion.",
                )
            if isinstance(record, CommunicationIntent):
                if origins not in source_sets:
                    source_sets[origins] = frozenset(origins)
                sources = source_sets[origins]
                for service in selected:
                    if len(sources) == 1 and service.asset_id in sources:
                        continue
                    entry = declared.setdefault((service.interface_id, service.protocol), [])
                    for kind, previous_sources, ports in entry:
                        if kind != record.kind and any(
                            source != service.asset_id and source in previous_sources
                            for source in sources
                        ):
                            if any(
                                a.start <= b.end and b.start <= a.end
                                for a in service_ports[service.id]
                                for b in ports
                            ):
                                fail(
                                    "CONTRADICTORY_INTENTS",
                                    path,
                                    "Required/prohibited endpoint and traffic scopes overlap.",
                                )
                    item = (record.kind, sources, service_ports[service.id])
                    if item not in entry:
                        entry.append(item)
