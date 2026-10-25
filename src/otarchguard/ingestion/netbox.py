"""Versioned offline export subset. No API client, live discovery or policy inference."""

import ipaddress
from collections import defaultdict

from otarchguard.diagnostics import check_limit, fail
from otarchguard.ingestion.records import ImportDiagnostic, StructuredLocation, StructuredProfile
from otarchguard.ingestion.records import InventoryValue as YamlValue
from otarchguard.ingestion.structured import STRUCTURED_LIMITS, ExtractedRow, Value

_FIELDS = {
    "devices": {"id", "name", "role", "site", "location"},
    "interfaces": {"id", "name", "device", "untagged_vlan", "tagged_vlans"},
    "ip_addresses": {"id", "address", "assigned_object_id", "assigned_object_type"},
    "prefixes": {"id", "prefix", "vlan"},
    "vlans": {"id", "vid", "name"},
    "cables": {"id", "a_terminations", "b_terminations", "label"},
}


def _identity(value: YamlValue) -> str:
    if type(value) not in (str, int) or value == "":
        fail("IMPORT_NETBOX_ID", "$", "Stable string or integer export id required.")
    return str(value)


def _reference(value: YamlValue) -> str:
    if (
        isinstance(value, dict)
        and set(value) <= {"id", "name", "display", "slug"}
        and "id" in value
    ):
        return _identity(value["id"])
    fail(
        "IMPORT_NETBOX_REFERENCE", "$", "Reference must contain an explicit id and allowed labels."
    )


def _records(document: dict[str, YamlValue], key: str) -> list[dict[str, YamlValue]]:
    value = document.get(key, [])
    if not isinstance(value, list) or not all(isinstance(v, dict) for v in value):
        fail("IMPORT_NETBOX_SHAPE", "$", "Export collections must be arrays of objects.")
    return [v for v in value if isinstance(v, dict)]


def validate_netbox(value: YamlValue, profile: StructuredProfile | None) -> list[ImportDiagnostic]:
    if (
        not isinstance(value, dict)
        or value.get("export_format") != "otarchguard-netbox-offline"
        or type(value.get("export_version")) is not int
        or value.get("export_version") != 1
    ):
        fail("IMPORT_NETBOX_VERSION", "$", "Require otarchguard-netbox-offline export_version 1.")
    if set(value) - (set(_FIELDS) | {"export_format", "export_version"}):
        fail("IMPORT_NETBOX_COLLECTION", "$", "Unknown export collections are unsupported.")
    if profile and any(
        t.collection not in {"/devices", "/interfaces", "/cables"} for t in profile.tables
    ):
        fail("IMPORT_NETBOX_MAPPING", "$", "Map devices, interfaces or evidence-only cables.")
    expected = {"/devices": "asset", "/interfaces": "interface", "/cables": "connection"}
    if profile and any(t.entity != expected[t.collection] for t in profile.tables):
        fail("IMPORT_NETBOX_MAPPING", "$", "Export collection has a fixed inventory entity kind.")
    diagnostics: list[ImportDiagnostic] = []
    collections = {key: _records(value, key) for key in _FIELDS}
    ids: dict[str, set[str]] = {}
    count = 0
    for key, records in collections.items():
        ids[key] = set()
        for record in records:
            count += 1
            check_limit("netbox_records", count, STRUCTURED_LIMITS.records)
            identity = _identity(record.get("id"))
            if identity in ids[key]:
                fail("IMPORT_NETBOX_DUPLICATE", "$", "Duplicate export ids are ambiguous.")
            ids[key].add(identity)
            if set(record) - _FIELDS[key]:
                diagnostics.append(
                    ImportDiagnostic(
                        code="EXCLUDED_METADATA",
                        message=f"{key}: unsupported metadata values excluded; no values echoed.",
                    )
                )
            for field, child in record.items():
                if field in _FIELDS[key] and isinstance(child, (dict, list)):
                    if field not in {
                        "device",
                        "role",
                        "site",
                        "location",
                        "untagged_vlan",
                        "tagged_vlans",
                        "vlan",
                        "a_terminations",
                        "b_terminations",
                    }:
                        fail("IMPORT_NETBOX_SHAPE", "$", "Unsupported nested inventory field.")
            check_limit("import_diagnostics", len(diagnostics), STRUCTURED_LIMITS.diagnostics)
    for record in collections["devices"]:
        if not isinstance(record.get("name"), str) or not record["name"]:
            fail("IMPORT_NETBOX_DEVICE", "$", "Device name is required.")
        for field in ("role", "site", "location"):
            if isinstance(record.get(field), dict):
                _reference(record[field])
    for record in collections["vlans"]:
        vid = record.get("vid")
        if type(vid) is not int or not 1 <= vid <= 4094:
            fail("IMPORT_NETBOX_VLAN", "$", "VLAN vid must be an integer from 1 to 4094.")
    for record in collections["interfaces"]:
        if _reference(record.get("device")) not in ids["devices"]:
            fail("IMPORT_NETBOX_REFERENCE", "$", "Interface references a missing device.")
        untagged = record.get("untagged_vlan")
        tags = record.get("tagged_vlans", [])
        if not isinstance(tags, list):
            fail("IMPORT_NETBOX_VLAN", "$", "tagged_vlans must be an array of id references.")
        tag_ids = [_reference(t) for t in tags]
        if len(set(tag_ids)) != len(tag_ids) or not set(tag_ids) <= ids["vlans"]:
            fail("IMPORT_NETBOX_VLAN", "$", "Duplicate or unresolved tagged VLAN references.")
        if untagged is not None:
            untagged_id = _reference(untagged)
            if untagged_id not in ids["vlans"] or untagged_id in tag_ids:
                fail("IMPORT_NETBOX_VLAN", "$", "Conflicting or unresolved VLAN assignment.")
    addresses: set[str] = set()
    assignments: set[str] = set()
    for record in collections["ip_addresses"]:
        if record.get("assigned_object_type") != "dcim.interface":
            fail("IMPORT_NETBOX_ASSIGNMENT", "$", "Only dcim.interface assignments are supported.")
        interface = _identity(record.get("assigned_object_id"))
        if interface not in ids["interfaces"]:
            fail("IMPORT_NETBOX_REFERENCE", "$", "Address references a missing interface.")
        try:
            address = ipaddress.IPv4Interface(str(record.get("address")))
        except ValueError:
            fail(
                "IMPORT_NETBOX_ADDRESS",
                "$",
                "An IPv4 address/prefix is required; IPv6 unsupported.",
            )
        if str(address.ip) in addresses or interface in assignments:
            fail(
                "IMPORT_NETBOX_ADDRESS",
                "$",
                "Reused address or multiple addresses on one interface.",
            )
        addresses.add(str(address.ip))
        assignments.add(interface)
    for record in collections["prefixes"]:
        try:
            ipaddress.IPv4Network(str(record.get("prefix")), strict=True)
        except ValueError:
            fail("IMPORT_NETBOX_PREFIX", "$", "Canonical IPv4 network prefix required.")
        if record.get("vlan") is not None and _reference(record["vlan"]) not in ids["vlans"]:
            fail("IMPORT_NETBOX_VLAN", "$", "Prefix references a missing VLAN.")
    if collections["prefixes"] or collections["vlans"]:
        diagnostics.append(
            ImportDiagnostic(
                code="INVENTORY_METADATA_ONLY",
                message="Prefixes/VLANs are inventory only; no zones or policy inferred.",
            )
        )
    if collections["cables"]:
        diagnostics.append(
            ImportDiagnostic(
                code="UNSUPPORTED_CABLE_RELATIONSHIP",
                message="Cable terminations excluded; cable candidates remain evidence only.",
            )
        )
    if set(ids["interfaces"]) - assignments:
        diagnostics.append(
            ImportDiagnostic(
                code="MISSING_ADDRESS_ASSOCIATION",
                message="Some interfaces lack IPv4; literal correction/rejection required.",
            )
        )
    check_limit("import_diagnostics", len(diagnostics), STRUCTURED_LIMITS.diagnostics)
    return diagnostics


def assigned_addresses(
    document: YamlValue,
    profile: StructuredProfile,
    tables: dict[str, tuple[ExtractedRow, ...]],
) -> dict[str, tuple[ExtractedRow, ...]]:
    """Explicit /@assigned_ipv4 projection, with the actual address record pointer."""
    if not isinstance(document, dict):
        fail("IMPORT_NETBOX_SHAPE", "$", "Export object required.")
    assignments: dict[str, list[tuple[int, dict[str, YamlValue]]]] = defaultdict(list)
    for index, record in enumerate(_records(document, "ip_addresses")):
        assignments[_identity(record.get("assigned_object_id"))].append((index, record))
    for table in profile.tables:
        projected = [name for name, f in table.fields.items() if f.path == "/@assigned_ipv4"]
        if not projected:
            continue
        if table.collection != "/interfaces" or projected != ["ipv4"]:
            fail("IMPORT_NETBOX_MAPPING", "$", "Assigned IPv4 projection maps interface ipv4 only.")
        original = _records(document, "interfaces")
        rows: list[ExtractedRow] = []
        for index, row in enumerate(tables[table.name]):
            matches = assignments.get(_identity(original[index].get("id")), [])
            values = dict(row.values)
            if len(matches) == 1:
                number, address = matches[0]
                pointer = f"/ip_addresses/{number}/address"
                values["ipv4"] = Value(
                    address["address"],
                    StructuredLocation(
                        collection="/ip_addresses",
                        record=f"/ip_addresses/{number}",
                        pointer=pointer,
                    ),
                    rule="unique_assigned_object_id_to_interface_id",
                )
            rows.append(ExtractedRow(row.location, values, row.omitted))
        tables[table.name] = tuple(rows)
    return tables
