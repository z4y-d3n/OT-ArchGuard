"""Schema vocabulary and provisional ceilings.

The normative project serialization contract is docs/yaml-schema-v1.md.
Loading, entity, association and graph/evaluation work limits are enforced.
"""

from dataclasses import dataclass
from enum import IntEnum, StrEnum
from typing import Final

SCHEMA_VERSION: Final = 1
ID_PATTERN: Final = r"[a-z][a-z0-9_-]{0,63}"


class ExitCode(IntEnum):
    SUCCESS = 0
    FAILED_INTENTS = 1
    ERROR = 2


class DiagnosticCategory(StrEnum):
    INVALID_INPUT = "invalid_input"
    UNSUPPORTED_MODEL = "unsupported_model"
    RESOURCE_LIMIT = "resource_limit"
    IO_ERROR = "io_error"
    EXECUTION_ERROR = "execution_error"
    NOT_IMPLEMENTED = "not_implemented"


class Protocol(StrEnum):
    TCP = "tcp"
    UDP = "udp"


class AssetKind(StrEnum):
    ENDPOINT = "endpoint"
    BOUNDARY_DEVICE = "boundary_device"


class Scope(StrEnum):
    INTERNAL = "internal"
    EXTERNAL = "external"


class DomainClassification(StrEnum):
    BUSINESS = "business"
    IACS = "iacs"
    UNASSESSED = "unassessed"


class SafetyClassification(StrEnum):
    SAFETY_RELATED = "safety_related"
    NON_SAFETY = "non_safety"
    UNASSESSED = "unassessed"


class SafetyDesignation(StrEnum):
    NON_SAFETY = "non_safety"
    SAFETY = "safety"
    MIXED_SAFETY = "mixed_safety"
    UNASSESSED = "unassessed"


class Criticality(StrEnum):
    UNSPECIFIED = "unspecified"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RuleEffect(StrEnum):
    ALLOW = "allow"
    DENY = "deny"


class IntentKind(StrEnum):
    REQUIRED = "required"
    PROHIBITED = "prohibited"


class AccessPointKind(StrEnum):
    MODELED_NETWORK = "modeled_network"
    UNMODELED = "unmodeled"


@dataclass(frozen=True)
class ResourceLimits:
    """Conservative rejection ceilings; not measured capacity."""

    input_bytes: int = 5 * 1024 * 1024
    nesting_depth: int = 32
    parser_events: int = 200_000
    assets: int = 1_000
    interfaces: int = 2_000
    edges: int = 5_000
    rules: int = 5_000
    services: int = 1_000
    zones: int = 1_000
    conduits: int = 5_000
    access_points: int = 5_000
    dependencies: int = 1_000
    protocol_port_atoms: int = 2_048
    state_edge_visits: int = 50_000_000
    edge_rule_associations: int = 500_000
    edge_rule_atom_checks: int = 50_000_000
    diagnostic_edges_per_query: int = 20


RESOURCE_LIMITS: Final = ResourceLimits()
