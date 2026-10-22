"""Reject unsupported declarations and decode strict schema shape before references."""

from pydantic import ValidationError

from otarchguard.contract import RESOURCE_LIMITS, DiagnosticCategory, ResourceLimits
from otarchguard.diagnostics import check_limit, fail
from otarchguard.domain import ArchitectureSnapshot
from otarchguard.loading import YamlValue

_POLICY = {"source_ports", "source_interface_ids", "stateful", "rule_order"}
_FEATURES = {"sl_t", "sl_c", "sl_a", "nat", "vrf", "vlan", "proxy"}


def _preflight(value: YamlValue, path: str = "$") -> None:
    if value is None:
        fail("TYPE_MISMATCH", path, "Null values are forbidden; omit optional fields.")
    if isinstance(value, list):
        for index, item in enumerate(value):
            _preflight(item, f"{path}[{index}]")
    elif isinstance(value, dict):
        for key, child in value.items():
            field_path = f"{path}.{key}"
            unsupported: str | None = None
            if key in _POLICY:
                unsupported = "UNSUPPORTED_POLICY"
            elif key in _FEATURES:
                unsupported = "UNSUPPORTED_FEATURE"
            elif path.startswith("$.assets[") and (
                key in {"owner_zone_ids", "owner_conduit_id"}
                or (key == "zone_id" and isinstance(child, list))
            ):
                unsupported = "UNSUPPORTED_OWNERSHIP"
            elif path.startswith("$.conduits[") and key in {
                "transit_zone_ids",
                "protected_transit",
            }:
                unsupported = "UNSUPPORTED_CONDUIT"
            elif key == "protocol" and isinstance(child, str) and child not in {"tcp", "udp"}:
                unsupported = "UNSUPPORTED_PROTOCOL"
            elif key == "schema_version" and type(child) is int and child != 1:
                unsupported = "UNSUPPORTED_VERSION"
            if unsupported:
                fail(
                    unsupported,
                    field_path,
                    "Declaration is outside schema-v1 support.",
                    DiagnosticCategory.UNSUPPORTED_MODEL,
                )
            if path.startswith("$.conduits[") and key == "zone_ids" and isinstance(child, list):
                if all(isinstance(x, str) for x in child):
                    strings = [x for x in child if isinstance(x, str)]
                    if len(strings) > 2 and len(set(strings)) == len(strings):
                        fail(
                            "UNSUPPORTED_CONDUIT",
                            field_path,
                            "Only pairwise conduits are supported.",
                            DiagnosticCategory.UNSUPPORTED_MODEL,
                        )
            if key in {"source", "destination"} and path.startswith(("$.rules[", "$.intents[")):
                if (
                    not isinstance(child, dict)
                    or len(child) != 1
                    or not set(child)
                    <= {
                        "asset_ids",
                        "zone_ids",
                        "all_assets",
                    }
                ):
                    fail(
                        "INVALID_SELECTOR",
                        field_path,
                        "Select exactly one supported selector mode.",
                    )
            _preflight(child, field_path)


def _counts(value: YamlValue, limits: ResourceLimits) -> None:
    if not isinstance(value, dict):
        return
    for name in ("zones", "assets", "interfaces", "conduits", "services", "rules"):
        records = value.get(name)
        if isinstance(records, list):
            check_limit(name, len(records), getattr(limits, name), f"$.{name}")
    edges = 0
    for name in ("transport_edges", "forwarding_edges"):
        edge_records = value.get(name)
        if isinstance(edge_records, list):
            edges += len(edge_records)
    check_limit("edges", edges, limits.edges)
    suc = value.get("suc")
    if isinstance(suc, dict):
        for name, limit in (
            ("access_points", "access_points"),
            ("external_dependencies", "dependencies"),
        ):
            records = suc.get(name)
            if isinstance(records, list):
                check_limit(limit, len(records), getattr(limits, limit), f"$.suc.{name}")
    associations = 0
    rules = value.get("rules")
    if isinstance(rules, list):
        for rule in rules:
            if isinstance(rule, dict) and isinstance(rule.get("edge_ids"), list):
                ids = rule["edge_ids"]
                if isinstance(ids, list):
                    associations += len(ids)
                    check_limit(
                        "edge_rule_associations", associations, limits.edge_rule_associations
                    )


def parse_model(value: YamlValue, limits: ResourceLimits = RESOURCE_LIMITS) -> ArchitectureSnapshot:
    """Decode schema shape; cross-record validation is a separate mandatory step."""
    _counts(value, limits)
    _preflight(value)
    try:
        return ArchitectureSnapshot.model_validate(value)
    except ValidationError as error:
        item = error.errors(include_url=False, include_context=False, include_input=False)[0]
        parts = item["loc"]
        path = "$"
        for part in parts:
            if isinstance(part, int):
                path += f"[{part}]"
            elif part not in {
                "AssetSelector",
                "ZoneSelector",
                "AllAssetsSelector",
                "modeled_network",
                "unmodeled",
            }:
                path += f".{part}"
        kind = item["type"]
        if kind in {"union_tag_invalid", "union_tag_not_found"}:
            path += ".kind"
        code = {
            "missing": "MISSING_FIELD",
            "extra_forbidden": "UNKNOWN_FIELD",
            "invalid_id": "INVALID_ID",
            "invalid_value": "INVALID_VALUE",
            "invalid_selector": "INVALID_SELECTOR",
            "literal_error": "INVALID_VALUE",
            "union_tag_invalid": "INVALID_VALUE",
            "union_tag_not_found": "MISSING_FIELD",
            "too_short": "INVALID_VALUE",
        }.get(kind, "TYPE_MISMATCH")
        if "destination_ports" in parts and kind in {"greater_than_equal", "less_than_equal"}:
            code = "INVALID_PORT"
        if "source" in parts or "destination" in parts:
            if code not in {"MISSING_FIELD", "INVALID_ID"}:
                code = "INVALID_SELECTOR"
        fail(code, path, "Value does not satisfy the strict schema-v1 field contract.")
