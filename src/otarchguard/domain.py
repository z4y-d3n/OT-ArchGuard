"""Strict immutable schema-v1 records. Use parsing/validation APIs for untrusted input."""

import re
from typing import Annotated, Literal, get_origin

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)
from pydantic_core import PydanticCustomError

from otarchguard.contract import ID_PATTERN


def _id(value: str) -> str:
    if re.fullmatch(ID_PATTERN, value) is None:
        raise PydanticCustomError("invalid_id", "Invalid identifier")
    return value


def _text(value: str) -> str:
    if not value.strip():
        raise PydanticCustomError("invalid_value", "Nonempty text required")
    return value


type Id = Annotated[str, AfterValidator(_id)]
type Text = Annotated[str, AfterValidator(_text)]
type ScopeValue = Literal["internal", "external"]
type ProtocolValue = Literal["tcp", "udp"]


class Record(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid", validate_default=True)

    @model_validator(mode="before")
    @classmethod
    def yaml_sequences(cls, value: object) -> object:
        """The sole representation conversion: YAML sequence → immutable tuple."""
        if isinstance(value, dict):
            return {
                key: tuple(child)
                if isinstance(child, list)
                and key in cls.model_fields
                and get_origin(cls.model_fields[key].annotation) is tuple
                else child
                for key, child in value.items()
            }
        return value


class PortInterval(Record):
    start: int = Field(ge=1, le=65535)
    end: int = Field(ge=1, le=65535)


class AssetSelector(Record):
    asset_ids: tuple[Id, ...] = Field(min_length=1)


class ZoneSelector(Record):
    zone_ids: tuple[Id, ...] = Field(min_length=1)


class AllAssetsSelector(Record):
    all_assets: Literal[True]

    @field_validator("all_assets", mode="before")
    @classmethod
    def boolean_true(cls, value: object) -> object:
        if value is not True:
            raise PydanticCustomError("invalid_selector", "Literal boolean true required")
        return value


def _selector(value: object) -> object:
    if isinstance(value, dict):
        models: dict[str, type[Record]] = {
            "asset_ids": AssetSelector,
            "zone_ids": ZoneSelector,
            "all_assets": AllAssetsSelector,
        }
        if len(value) == 1:
            model = models.get(next(iter(value)))
            if model is not None:
                return model.model_validate(value)
    return value


type Selector = Annotated[
    AssetSelector | ZoneSelector | AllAssetsSelector, BeforeValidator(_selector)
]


class Zone(Record):
    id: Id
    name: Text
    purpose: Text
    scope: ScopeValue
    grouping_rationale: Text
    safety_designation: Literal["non_safety", "safety", "mixed_safety", "unassessed"]
    mixed_safety_rationale: Text | None = None


class Asset(Record):
    id: Id
    name: Text
    role: Text
    zone_id: Id
    kind: Literal["endpoint", "boundary_device"]
    scope: ScopeValue
    domain_classification: Literal["business", "iacs", "unassessed"]
    safety_classification: Literal["safety_related", "non_safety", "unassessed"]
    criticality: Literal["unspecified", "low", "medium", "high", "critical"]


class Interface(Record):
    id: Id
    asset_id: Id
    placement_zone_id: Id
    ipv4: str


class Conduit(Record):
    id: Id
    name: Text
    purpose: Text
    common_security_needs: Text
    zone_ids: tuple[Id, ...]


class TransportEdge(Record):
    id: Id
    source_interface_id: Id
    destination_interface_id: Id
    conduit_id: Id | None = None


class ForwardingEdge(Record):
    id: Id
    ingress_interface_id: Id
    egress_interface_id: Id
    conduit_id: Id | None = None


class Service(Record):
    id: Id
    asset_id: Id
    interface_id: Id
    protocol: ProtocolValue
    destination_ports: tuple[PortInterval, ...] = Field(min_length=1)


class EnforcementRule(Record):
    id: Id
    edge_ids: tuple[Id, ...] = Field(min_length=1)
    source: Selector
    destination: Selector
    protocol: ProtocolValue
    destination_ports: tuple[PortInterval, ...] = Field(min_length=1)
    effect: Literal["allow", "deny"]


class CommunicationIntent(Record):
    id: Id
    kind: Literal["required", "prohibited"]
    source: Selector
    destination_service_ids: tuple[Id, ...] = Field(min_length=1)


class ExposureScenario(Record):
    id: Id
    origin_asset_ids: tuple[Id, ...] = Field(min_length=1)
    destination_service_ids: tuple[Id, ...] = Field(min_length=1)
    description: Text | None = None


class ModeledAccessPoint(Record):
    id: Id
    kind: Literal["modeled_network"]
    description: Text
    external_interface_id: Id
    internal_interface_id: Id
    edge_ids: tuple[Id, ...] = Field(min_length=1)


class UnmodeledAccessPoint(Record):
    id: Id
    kind: Literal["unmodeled"]
    description: Text


type AccessPoint = Annotated[ModeledAccessPoint | UnmodeledAccessPoint, Field(discriminator="kind")]


class ExternalDependency(Record):
    id: Id
    description: Text
    external_asset_ids: tuple[Id, ...]
    required_intent_ids: tuple[Id, ...]


class SUC(Record):
    id: Id
    name: Text
    purpose: Text
    controlled_process: Text
    boundary_description: Text
    completeness_assertion: Text
    access_points: tuple[AccessPoint, ...]
    external_dependencies: tuple[ExternalDependency, ...]


class ArchitectureSnapshot(Record):
    schema_version: Literal[1]
    architecture_id: Id
    revision: Text
    suc: SUC
    zones: tuple[Zone, ...] = Field(min_length=1)
    assets: tuple[Asset, ...] = Field(min_length=1)
    interfaces: tuple[Interface, ...]
    conduits: tuple[Conduit, ...]
    transport_edges: tuple[TransportEdge, ...]
    forwarding_edges: tuple[ForwardingEdge, ...]
    services: tuple[Service, ...]
    rules: tuple[EnforcementRule, ...]
    intents: tuple[CommunicationIntent, ...]
    scenarios: tuple[ExposureScenario, ...]

    @field_validator("schema_version", mode="before")
    @classmethod
    def integer_version(cls, value: object) -> object:
        if type(value) is not int:
            raise PydanticCustomError("type_mismatch", "Integer schema version required")
        return value
