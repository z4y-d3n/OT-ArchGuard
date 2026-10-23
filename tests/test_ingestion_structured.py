"""Independent structured-inventory, mapping, reference and review contracts."""

import json
import os
import subprocess
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import pytest
import yaml
from pydantic import ValidationError
from typer.testing import CliRunner

from otarchguard.api import validate_bytes
from otarchguard.cli import app
from otarchguard.diagnostics import ModelError
from otarchguard.ingestion.json_inventory import inspect_json, parse_json
from otarchguard.ingestion.numbers import NumericToken
from otarchguard.ingestion.records import (
    ImportDraft,
    OwnerDecisions,
    StructuredCandidate,
    StructuredProfile,
)
from otarchguard.ingestion.structured import STRUCTURED_LIMITS, lookup
from otarchguard.ingestion.workflow import (
    create_draft,
    draft_sha256,
    emit_artifacts,
    load_profile,
    load_record,
    review_template,
    serialize,
)
from otarchguard.trace import trace_architecture
from tools.synthetic_inventories import workbook_parts, zip_parts


def fixture_profile(adapter: str = "json") -> StructuredProfile:
    def field(path: str, target: str | None = None) -> dict[str, Any]:
        return {"path": path, **({"reference": {"table": target}} if target else {})}

    assets = {
        "id": field("/id"),
        "name": field("/name"),
        "role": field("/role"),
        "zone_id": field("/zone", "zones"),
    }
    zones = {"id": field("/id"), "name": field("/name")}
    interfaces = {
        "id": field("/id"),
        "asset_id": field("/asset", "assets"),
        "placement_zone_id": field("/zone", "zones"),
        "ipv4": field("/ip"),
    }
    tables: list[dict[str, Any]] = [
        {
            "name": "assets",
            "collection": "/assets",
            "entity": "asset",
            "fields": assets,
            "constants": {
                "kind": "endpoint",
                "scope": "internal",
                "domain_classification": "iacs",
                "safety_classification": "unassessed",
                "criticality": "unspecified",
            },
        },
        {
            "name": "zones",
            "collection": "/zones",
            "entity": "zone",
            "fields": zones,
            "constants": {
                "purpose": "Synthetic",
                "scope": "internal",
                "grouping_rationale": "Owner",
                "safety_designation": "unassessed",
            },
        },
        {
            "name": "interfaces",
            "collection": "/interfaces",
            "entity": "interface",
            "fields": interfaces,
        },
    ]
    if adapter == "xlsx":
        for table in tables:
            table["collection"] = str(table["collection"])[1:]
            for value in table["fields"].values():
                value["path"] = value["path"][1:]
    return StructuredProfile.model_validate(
        {"profile_version": 2, "adapter": adapter, "tables": tables}
    )


def fixture_data() -> dict[str, Any]:
    return {
        "assets": [
            {"id": "eng", "name": "Engineering", "role": "Workstation", "zone": "control"},
            {"id": "plc", "name": "PLC", "role": "Control", "zone": "control"},
        ],
        "zones": [{"id": "control", "name": "Control"}],
        "interfaces": [
            {"id": "if_eng", "asset": "eng", "zone": "control", "ip": "10.0.0.1/24"},
            {"id": "if_plc", "asset": "plc", "zone": "control", "ip": "10.0.0.2/24"},
        ],
    }


def fixture_source(
    tmp_path: Path, adapter: str = "json", data: dict[str, Any] | None = None
) -> Path:
    value = fixture_data() if data is None else data
    source = tmp_path / ("inventory.xlsx" if adapter == "xlsx" else "inventory.json")
    if adapter == "xlsx":
        tables = {
            k: [list(rows[0]), *[list(r.values()) for r in rows]] for k, rows in value.items()
        }
        source.write_bytes(zip_parts(workbook_parts(tables)))
    else:
        source.write_text(json.dumps(value), encoding="utf-8")
    return source


def confirmed(draft: ImportDraft, minimal: dict[str, Any]) -> OwnerDecisions:
    template = review_template(draft).model_dump(mode="json")
    context = dict(minimal)
    for collection in ("assets", "zones", "interfaces"):
        context.pop(collection)
    for collection in (
        "transport_edges",
        "forwarding_edges",
        "rules",
        "intents",
        "scenarios",
        "conduits",
        "services",
    ):
        context[collection] = []
    template.update(
        reviewer="Synthetic owner",
        model_confirmed=True,
        model_rationale="Reviewed synthetic inventory only",
        model=context,
    )
    for resolution in template["resolutions"]:
        resolution.update(
            decision="OWNER_CONFIRMED", rationale="Reviewed individual synthetic record"
        )
    return OwnerDecisions.model_validate(template)


@pytest.mark.parametrize("adapter", ["json", "xlsx"])
def test_multicollection_review_native_validation_and_provenance(
    tmp_path: Path,
    minimal: dict[str, Any],
    adapter: str,
) -> None:
    source = fixture_source(tmp_path, adapter)
    draft = create_draft(source, fixture_profile(adapter))
    assert len(draft.candidates) == 5 and not draft.conflicts
    assert all(isinstance(c, StructuredCandidate) for c in draft.candidates)
    assert all(c.state == "UNRESOLVED" for c in draft.candidates)
    artifacts = emit_artifacts(draft, confirmed(draft, minimal), source)
    snapshot = validate_bytes(artifacts["architecture.yaml"])
    assert {a.id for a in snapshot.model.assets} == {"eng", "plc"}
    assert {i.ipv4 for i in snapshot.model.interfaces} == {"10.0.0.1/24", "10.0.0.2/24"}
    assert not snapshot.model.transport_edges and not snapshot.model.rules
    evidence = json.loads(artifacts["architecture.provenance.json"])
    assert evidence["model_sha256"] == snapshot.sha256
    for record in evidence["records"]:
        assert record["model_collection"] in {"assets", "zones", "interfaces"}
        assert record["candidate"]["location"]["collection"]
    interface = next(c for c in draft.candidates if c.entity == "interface")
    assert isinstance(interface, StructuredCandidate) and len(interface.references) == 2
    assert all(r.target_candidate_id for r in interface.references)
    field = next(f for f in interface.fields if f.field == "asset_id")
    assert field.location is not None
    if adapter == "json":
        assert field.location.model_dump()["pointer"].startswith("/interfaces/")
    else:
        assert (
            field.location.model_dump()["cell"] == "B2"
            or field.location.model_dump()["cell"] == "B3"
        )
    assert serialize(create_draft(source, fixture_profile(adapter))) == serialize(draft)
    assert emit_artifacts(draft, confirmed(draft, minimal), source) == artifacts
    saved = tmp_path / "draft.json"
    saved.write_bytes(serialize(draft))
    assert serialize(load_record(saved, ImportDraft)) == serialize(draft)


@pytest.mark.parametrize(
    "content",
    [
        b'{"x":1,"x":2}',
        b'{"x":{"a":1,"a":2}}',
        b"[NaN]",
        b"[Infinity]",
        b"[-Infinity]",
        b"[1e10000]",
        b"[" + b"9" * 65 + b"]",
        b"[[[[[[[[[[[[[[[[[[[[[[[[[0]]]]]]]]]]]]]]]]]]]]]]]]]",
        b'{"x":"\\ud800"}',
        b'{"\\udfff":1}',
        b'{"x":"\\u0000"}',
        b"\xff",
        b"\xef\xbb\xbf[]",
        b'{"x":01}',
        b'{"x":1,}',
        b"[] trailing",
        b"//comment\n[]",
        b"[" + b"0," * 1000 + b"0]",
        b'{"x":"' + b"a" * 4097 + b'"}',
    ],
    ids=[
        "duplicate",
        "nested_duplicate",
        "nan",
        "inf",
        "neg_inf",
        "exponent_budget",
        "large_int",
        "depth",
        "surrogate",
        "key_surrogate",
        "null_char",
        "encoding",
        "bom",
        "number",
        "trailing_comma",
        "trailing_text",
        "comment",
        "array",
        "string",
    ],
)
def test_strict_json_adversarial(content: bytes) -> None:
    with pytest.raises(ModelError):
        parse_json(content)


@pytest.mark.parametrize(
    "change", ["source_bytes", "depth", "records", "fields", "scalars", "text", "number_characters"]
)
def test_json_independent_resource_ceilings(change: str) -> None:
    with pytest.raises(ModelError):
        parse_json(
            b'{"records":[{"id":"one","other":123}]}', replace(STRUCTURED_LIMITS, **{change: 0})
        )


@pytest.mark.parametrize(
    "value,expected,needs_correction",
    [
        ("001", "001", False),
        (None, "", True),
        ("", "", False),
        ([], "", True),
        (True, "", True),
        (123, "", True),
        ({}, "", True),
    ],
)
def test_json_distinguishes_value_types(
    tmp_path: Path,
    value: Any,
    expected: str,
    needs_correction: bool,
) -> None:
    data = fixture_data()
    data["assets"][0]["name"] = value
    draft = create_draft(fixture_source(tmp_path, data=data), fixture_profile())
    candidate = next(
        c
        for c in draft.candidates
        if c.entity == "asset"
        and any(f.normalized_value == "eng" for f in c.fields if f.field == "id")
    )
    assert isinstance(candidate, StructuredCandidate)
    field = next(f for f in candidate.fields if f.field == "name")
    assert field.normalized_value == expected
    assert ("name" in candidate.required_corrections) is needs_correction
    if type(value) not in {dict, list}:
        assert type(field.raw_value) is type(value) and field.raw_value == value


def test_missing_value_is_distinct_from_null(tmp_path: Path) -> None:
    data = fixture_data()
    del data["assets"][0]["name"]
    draft = create_draft(fixture_source(tmp_path, data=data), fixture_profile())
    assert any("Missing mapped value" in d.message for d in draft.diagnostics)


def test_key_order_and_excluded_metadata_preserve_semantic_identity(tmp_path: Path) -> None:
    source = fixture_source(tmp_path)
    original = create_draft(source, fixture_profile())
    data = fixture_data()
    data["assets"][0].update(password="DO_NOT_ECHO_SECRET", notes="DO_NOT_ECHO_NOTES")
    source.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")
    changed = create_draft(source, fixture_profile())
    assert [c.candidate_id for c in original.candidates] == [
        c.candidate_id for c in changed.candidates
    ]
    assert draft_sha256(original) != draft_sha256(changed)
    assert b"DO_NOT_ECHO" not in serialize(changed)
    assert b"DO_NOT_ECHO" not in serialize(inspect_json(source))


def test_json_array_order_is_relevant(tmp_path: Path) -> None:
    source = fixture_source(tmp_path)
    original = create_draft(source, fixture_profile())
    data = fixture_data()
    data["assets"].reverse()
    source.write_text(json.dumps(data), encoding="utf-8")
    changed = create_draft(source, fixture_profile())
    assert {c.candidate_id for c in original.candidates if c.entity == "asset"} != {
        c.candidate_id for c in changed.candidates if c.entity == "asset"
    }


def test_sheet_order_does_not_change_candidates(tmp_path: Path) -> None:
    source = fixture_source(tmp_path, "xlsx")
    original = create_draft(source, fixture_profile("xlsx"))
    source = fixture_source(tmp_path, "xlsx", dict(reversed(list(fixture_data().items()))))
    changed = create_draft(source, fixture_profile("xlsx"))
    assert [c.candidate_id for c in original.candidates] == [
        c.candidate_id for c in changed.candidates
    ]
    assert draft_sha256(original) != draft_sha256(changed)


@pytest.mark.parametrize("adapter", ["json", "xlsx"])
def test_source_mutation_and_stale_review(
    tmp_path: Path, minimal: dict[str, Any], adapter: str
) -> None:
    source = fixture_source(tmp_path, adapter)
    first = create_draft(source, fixture_profile(adapter))
    owner = confirmed(first, minimal)
    data = fixture_data()
    data["assets"][0]["role"] = "Changed"
    fixture_source(tmp_path, adapter, data)
    with pytest.raises(ModelError) as error:
        emit_artifacts(first, owner, source)
    second = create_draft(source, fixture_profile(adapter))
    assert error.value.diagnostics[0].code == "IMPORT_SOURCE_CHANGED"
    with pytest.raises(ModelError) as error:
        emit_artifacts(second, owner, source)
    assert error.value.diagnostics[0].code == "IMPORT_STALE_REVIEW"


@pytest.mark.parametrize(
    "change", ["missing_target", "duplicate_id", "duplicate_name", "reused_ip"]
)
def test_conflict_diagnostics_and_missing_references(tmp_path: Path, change: str) -> None:
    data = fixture_data()
    if change == "missing_target":
        data["interfaces"][0]["asset"] = "absent"
    if change == "duplicate_id":
        data["assets"][1]["id"] = "eng"
    if change == "duplicate_name":
        data["assets"][1]["name"] = "Engineering"
    if change == "reused_ip":
        data["interfaces"][1]["ip"] = "10.0.0.1/24"
    draft = create_draft(fixture_source(tmp_path, data=data), fixture_profile())
    if change == "missing_target":
        assert any(d.code == "UNRESOLVED_REFERENCE" for d in draft.diagnostics)
    else:
        expected = {
            "duplicate_id": "DUPLICATE_IDENTITY",
            "duplicate_name": "DUPLICATE_NAME",
            "reused_ip": "REUSED_ADDRESS",
        }[change]
        assert any(c.code == expected for c in draft.conflicts)


def test_reference_rename_requires_dependent_correction(
    tmp_path: Path, minimal: dict[str, Any]
) -> None:
    source = fixture_source(tmp_path)
    draft = create_draft(source, fixture_profile())
    value = confirmed(draft, minimal).model_dump(mode="json")
    candidate = next(
        c
        for c in draft.candidates
        if c.entity == "asset"
        and any(f.field == "id" and f.normalized_value == "eng" for f in c.fields)
    )
    next(r for r in value["resolutions"] if r["candidate_id"] == candidate.candidate_id)[
        "corrections"
    ] = {"id": "eng_new"}
    with pytest.raises(ModelError) as error:
        emit_artifacts(draft, OwnerDecisions.model_validate(value), source)
    assert error.value.diagnostics[0].code == "IMPORT_REFERENCE"
    interface = next(
        c
        for c in draft.candidates
        if c.entity == "interface"
        and any(f.field == "asset_id" and f.normalized_value == "eng" for f in c.fields)
    )
    next(r for r in value["resolutions"] if r["candidate_id"] == interface.candidate_id)[
        "corrections"
    ] = {"asset_id": "eng_new"}
    artifacts = emit_artifacts(draft, OwnerDecisions.model_validate(value), source)
    assert "eng_new" in {a.id for a in validate_bytes(artifacts["architecture.yaml"]).model.assets}
    assert b"eng_new" in artifacts["architecture.provenance.json"]


@pytest.mark.parametrize("path", ["/password", "/nested/api_token", "/notes", "/URL"])
def test_private_mappings_rejected(tmp_path: Path, path: str) -> None:
    profile = fixture_profile().model_dump(mode="json")
    profile["tables"][0]["fields"]["name"]["path"] = path
    with pytest.raises(ModelError) as error:
        create_draft(fixture_source(tmp_path), StructuredProfile.model_validate(profile))
    assert error.value.diagnostics[0].code == "IMPORT_PRIVATE_FIELD"


@pytest.mark.parametrize("change", ["unknown_key", "version", "formula", "wrong_type"])
def test_profile_typos_rejected(change: str) -> None:
    profile = fixture_profile().model_dump(mode="json")
    if change == "unknown_key":
        profile["tables"][0]["fieldz"] = {}
    if change == "version":
        profile["profile_version"] = True
    if change == "formula":
        profile["tables"][0]["formula_policy"] = "trust_cache"
    if change == "wrong_type":
        profile["tables"][0]["fields"]["id"]["value_type"] = "automatic"
    with pytest.raises(ValidationError):
        StructuredProfile.model_validate(profile)


@pytest.mark.parametrize("path", ["id", "/bad~2path", "#fragment"])
def test_bad_pointers_rejected(path: str) -> None:
    with pytest.raises(ModelError):
        lookup({}, path)


def test_escaped_pointers_and_array_elements() -> None:
    assert lookup({"a/b": {"~c": ["zero", "one"]}}, "/a~1b/~0c/1") == ("one", False)
    assert lookup(["zero"], "/01") == (None, True)


@pytest.mark.parametrize("adapter", ["json", "xlsx"])
def test_connection_evidence_never_grants_reachability(
    tmp_path: Path,
    minimal: dict[str, Any],
    adapter: str,
) -> None:
    source = fixture_source(tmp_path, adapter)
    draft = create_draft(source, fixture_profile(adapter))
    owner = confirmed(draft, minimal).model_dump(mode="json")
    owner["model"]["services"] = [
        {
            "id": "svc_plc",
            "asset_id": "plc",
            "interface_id": "if_plc",
            "protocol": "tcp",
            "destination_ports": [{"start": 502, "end": 502}],
        }
    ]
    result = validate_bytes(
        emit_artifacts(draft, OwnerDecisions.model_validate(owner), source)["architecture.yaml"]
    )
    assert all(not i.reachable for i in trace_architecture(result, "eng", "svc_plc").intervals)


def test_structured_cli_control_flow(tmp_path: Path) -> None:
    source = fixture_source(tmp_path)
    profile = tmp_path / "profile.json"
    profile.write_bytes(serialize(fixture_profile()))
    assert load_profile(profile) == fixture_profile()
    runner = CliRunner()
    for args in (["inspect", str(source)], ["preview", str(source), "--profile", str(profile)]):
        result = runner.invoke(app, ["import", *args])
        assert result.exit_code == 0, result.output
    draft = tmp_path / "draft.json"
    assert (
        runner.invoke(
            app, ["import", "map", str(source), "--profile", str(profile), "--output", str(draft)]
        ).exit_code
        == 0
    )
    decisions = tmp_path / "owner.json"
    assert (
        runner.invoke(
            app, ["import", "review", str(draft), "--decisions", str(decisions)]
        ).exit_code
        == 0
    )
    output = tmp_path / "accepted"
    result = runner.invoke(
        app,
        [
            "import",
            "emit",
            str(draft),
            "--source",
            str(source),
            "--decisions",
            str(decisions),
            "--output",
            str(output),
        ],
    )
    assert result.exit_code == 2 and not output.exists() and "IMPORT_REVIEW" in result.stderr


def netbox_fixture() -> tuple[dict[str, Any], StructuredProfile]:
    data: dict[str, Any] = {
        "export_format": "otarchguard-netbox-offline",
        "export_version": 1,
        "devices": [
            {
                "id": 1,
                "name": "PLC",
                "role": {"id": 1, "name": "Control"},
                "site": {"id": 8, "name": "Plant"},
            }
        ],
        "interfaces": [
            {"id": 10, "name": "eth0", "device": {"id": 1}, "untagged_vlan": {"id": 20}}
        ],
        "ip_addresses": [
            {
                "id": 100,
                "address": "10.0.0.2/24",
                "assigned_object_id": 10,
                "assigned_object_type": "dcim.interface",
            }
        ],
        "vlans": [{"id": 20, "vid": 100, "name": "Inventory only"}],
        "prefixes": [{"id": 30, "prefix": "10.0.0.0/24", "vlan": {"id": 20}}],
        "cables": [
            {
                "id": 40,
                "a_terminations": [{"object_type": "unsupported"}],
                "b_terminations": [],
                "label": "Documented only",
            }
        ],
    }
    profile = fixture_profile().model_dump(mode="json")
    profile["adapter"] = "netbox-offline-v1"
    profile["tables"] = [t for t in profile["tables"] if t["name"] != "zones"]
    assets, interfaces = profile["tables"]
    assets["collection"] = "/devices"
    assets["fields"]["id"].update(value_type="integer", prefix="dev_")
    assets["fields"]["role"]["path"] = "/role/name"
    assets["fields"].pop("zone_id")
    assets["constants"]["zone_id"] = "control"
    interfaces["fields"]["id"].update(value_type="integer", prefix="if_")
    interfaces["fields"]["asset_id"].update(path="/device/id", value_type="integer", prefix="dev_")
    interfaces["fields"].pop("placement_zone_id")
    interfaces["constants"]["placement_zone_id"] = "control"
    interfaces["fields"]["ipv4"].update(path="/@assigned_ipv4", normalize="ipv4_interface")
    return data, StructuredProfile.model_validate(profile)


def test_netbox_assigned_addresses_provenance_and_privacy(
    tmp_path: Path, minimal: dict[str, Any]
) -> None:
    data, profile = netbox_fixture()
    data["devices"][0].update(api_token="SECRET_TOKEN", comments="SECRET_NOTES")
    source = fixture_source(tmp_path, data=data)
    draft = create_draft(source, profile)
    assert len(draft.candidates) == 2 and b"SECRET_" not in serialize(draft)
    interface = next(c for c in draft.candidates if c.entity == "interface")
    address = next(f for f in interface.fields if f.field == "ipv4")
    assert address.raw_value == "10.0.0.2/24" and address.normalized_value == "10.0.0.2/24"
    assert address.location is not None
    assert address.location.model_dump()["pointer"] == "/ip_addresses/0/address"
    owner = confirmed(draft, minimal).model_dump(mode="json")
    owner["model"]["zones"] = [
        {
            "id": "control",
            "name": "Control",
            "scope": "internal",
            "purpose": "Synthetic",
            "grouping_rationale": "Owner",
            "safety_designation": "unassessed",
        }
    ]
    artifacts = emit_artifacts(draft, OwnerDecisions.model_validate(owner), source)
    snapshot = validate_bytes(artifacts["architecture.yaml"])
    assert snapshot.model.interfaces[0].asset_id == "dev_1"
    assert not snapshot.model.rules and not snapshot.model.transport_edges
    assert b"SECRET_" not in artifacts["architecture.provenance.json"]
    assert any(d.code == "UNSUPPORTED_CABLE_RELATIONSHIP" for d in draft.diagnostics)


@pytest.mark.parametrize(
    "change",
    [
        "version",
        "bool_version",
        "unknown",
        "missing_device",
        "duplicate_device",
        "duplicate_interface",
        "missing_assignment",
        "wrong_type",
        "ipv6",
        "reused_ip",
        "multiple_ip",
        "prefix",
        "vlan",
        "tagged_duplicate",
        "conflicting_vlan",
        "nested",
        "incomplete",
    ],
)
def test_netbox_adversarial_contract(tmp_path: Path, change: str) -> None:
    data, profile = netbox_fixture()
    if change == "version":
        data["export_version"] = 2
    if change == "bool_version":
        data["export_version"] = True
    if change == "unknown":
        data["virtual_machines"] = []
    if change == "missing_device":
        data["devices"] = []
    if change == "duplicate_device":
        data["devices"].append(dict(data["devices"][0]))
    if change == "duplicate_interface":
        data["interfaces"].append(dict(data["interfaces"][0]))
    if change == "missing_assignment":
        data["ip_addresses"][0]["assigned_object_id"] = 99
    if change == "wrong_type":
        data["ip_addresses"][0]["assigned_object_type"] = "virtualization.vminterface"
    if change == "ipv6":
        data["ip_addresses"][0]["address"] = "2001:db8::1/64"
    if change == "reused_ip":
        data["interfaces"].append({"id": 11, "device": {"id": 1}})
        data["ip_addresses"].append(
            {**data["ip_addresses"][0], "id": 101, "assigned_object_id": 11}
        )
    if change == "multiple_ip":
        data["ip_addresses"].append(
            {**data["ip_addresses"][0], "id": 101, "address": "10.0.0.3/24"}
        )
    if change == "prefix":
        data["prefixes"][0]["prefix"] = "10.0.0.1/24"
    if change == "vlan":
        data["vlans"][0]["vid"] = True
    if change == "tagged_duplicate":
        data["interfaces"][0]["tagged_vlans"] = [{"id": 20}, {"id": 20}]
    if change == "conflicting_vlan":
        data["interfaces"][0]["tagged_vlans"] = [{"id": 20}]
    if change == "nested":
        data["devices"][0]["role"] = {"id": 1, "unsafe": {}}
    if change == "incomplete":
        del data["devices"][0]["id"]
    with pytest.raises(ModelError):
        create_draft(fixture_source(tmp_path, data=data), profile)


@pytest.mark.parametrize(
    "normalize,source_value,expected",
    [("trim", "  PLC  ", "PLC"), ("lower", "PLC", "plc"), ("upper", "plc", "PLC")],
)
def test_declarative_transformation(
    tmp_path: Path, normalize: str, source_value: str, expected: str
) -> None:
    data = fixture_data()
    data["assets"][0]["name"] = source_value
    profile = fixture_profile().model_dump(mode="json")
    profile["tables"][0]["fields"]["name"]["normalize"] = normalize
    draft = create_draft(
        fixture_source(tmp_path, data=data), StructuredProfile.model_validate(profile)
    )
    assert any(
        f.field == "name" and f.normalized_value == expected and normalize in f.transformation
        for c in draft.candidates
        for f in c.fields
    )


def test_number_and_boolean_explicit_types_round_trip(tmp_path: Path) -> None:
    data = fixture_data()
    data["assets"][0]["role"] = 1.25
    data["assets"][1]["role"] = True
    profile = fixture_profile().model_dump(mode="json")
    profile["tables"][0]["fields"]["role"]["value_type"] = "number"
    draft = create_draft(
        fixture_source(tmp_path, data=data), StructuredProfile.model_validate(profile)
    )
    assert any(
        isinstance(f.raw_value, NumericToken)
        and f.raw_value.numeric_token == "1.25"
        and f.normalized_value == "1.25"
        for c in draft.candidates
        for f in c.fields
    )
    assert any(
        isinstance(c, StructuredCandidate) and "role" in c.required_corrections
        for c in draft.candidates
    )
    saved = tmp_path / "draft.json"
    saved.write_bytes(serialize(draft))
    assert serialize(load_record(saved, ImportDraft)) == serialize(draft)


@pytest.mark.parametrize("adapter", ["json", "xlsx", "netbox-offline-v1"])
def test_installed_structured_full_workflow(
    tmp_path: Path,
    minimal: dict[str, Any],
    installed_console: Path,
    adapter: str,
) -> None:
    data, mapping = (
        netbox_fixture()
        if adapter == "netbox-offline-v1"
        else (fixture_data(), fixture_profile(adapter))
    )
    source = fixture_source(tmp_path, adapter, data)
    profile_path = tmp_path / "mapping.json"
    profile_path.write_bytes(serialize(mapping))
    draft_path, owner_path = tmp_path / "draft.json", tmp_path / "owner.json"
    output = tmp_path / "accepted"

    def invoke(*args: str, expected: int = 0) -> dict[str, Any]:
        result = subprocess.run(
            [str(installed_console), *args],
            cwd=tmp_path,
            capture_output=True,
            env={**os.environ, "NO_COLOR": "1", "TERM": "dumb"},
            timeout=30,
        )
        assert result.returncode == expected, result.stderr.decode()
        return cast(dict[str, Any], json.loads(result.stdout if expected == 0 else result.stderr))

    invoke("import", "inspect", str(source))
    invoke("import", "preview", str(source), "--profile", str(profile_path))
    invoke(
        "import", "map", str(source), "--profile", str(profile_path), "--output", str(draft_path)
    )
    invoke("import", "review", str(draft_path), "--decisions", str(owner_path))
    draft = load_record(draft_path, ImportDraft)
    value = confirmed(draft, minimal).model_dump(mode="json")
    if adapter == "netbox-offline-v1":
        value["model"]["zones"] = [
            {
                "id": "control",
                "name": "Control",
                "scope": "internal",
                "purpose": "Synthetic",
                "grouping_rationale": "Owner",
                "safety_designation": "unassessed",
            }
        ]
    owner_path.write_text(json.dumps(value), encoding="utf-8")
    result = invoke(
        "import",
        "emit",
        str(draft_path),
        "--source",
        str(source),
        "--decisions",
        str(owner_path),
        "--output",
        str(output),
    )
    assert (
        invoke("validate", str(output / "architecture.yaml"))["model_sha256"]
        == result["model_sha256"]
    )
    assert (
        invoke(
            "import",
            "emit",
            str(draft_path),
            "--source",
            str(source),
            "--decisions",
            str(owner_path),
            "--output",
            str(output),
            expected=2,
        )["code"]
        == "IMPORT_OUTPUT"
    )


@pytest.mark.parametrize("adapter", ["json", "xlsx"])
def test_duplicate_entity_emission_requires_resolution(
    tmp_path: Path,
    minimal: dict[str, Any],
    adapter: str,
) -> None:
    data = fixture_data()
    data["assets"].append(dict(data["assets"][0]))
    source = fixture_source(tmp_path, adapter, data)
    draft = create_draft(source, fixture_profile(adapter))
    owner = confirmed(draft, minimal)
    assert any(c.code == "DUPLICATE_IDENTITY" for c in draft.conflicts)
    initial = owner.model_dump(mode="json")
    for resolution in initial["resolutions"]:
        candidate = next(
            c for c in draft.candidates if c.candidate_id == resolution["candidate_id"]
        )
        if (
            isinstance(candidate, StructuredCandidate)
            and "asset_id" in candidate.required_corrections
        ):
            resolution["corrections"] = {"asset_id": "eng"}
    owner = OwnerDecisions.model_validate(initial)
    with pytest.raises(ModelError) as error:
        emit_artifacts(draft, owner, source)
    assert error.value.diagnostics[0].code == "IMPORT_CONFLICT"
    value = owner.model_dump(mode="json")
    duplicate = next(c for c in draft.conflicts if c.code == "DUPLICATE_IDENTITY")
    for resolution in value["resolutions"]:
        if resolution["candidate_id"] == duplicate.candidate_ids[0]:
            resolution["decision"] = "OWNER_REJECTED"
        candidate = next(
            c for c in draft.candidates if c.candidate_id == resolution["candidate_id"]
        )
        if (
            isinstance(candidate, StructuredCandidate)
            and "asset_id" in candidate.required_corrections
        ):
            resolution["corrections"] = {"asset_id": "eng"}
    snapshot = validate_bytes(
        emit_artifacts(draft, OwnerDecisions.model_validate(value), source)["architecture.yaml"]
    )
    assert len(snapshot.model.assets) == 2


def test_cyclic_reference_profile_rejected(tmp_path: Path) -> None:
    profile = fixture_profile().model_dump(mode="json")
    profile["tables"][0]["fields"]["zone_id"]["reference"]["table"] = "interfaces"
    with pytest.raises(ModelError) as error:
        create_draft(fixture_source(tmp_path), StructuredProfile.model_validate(profile))
    assert error.value.diagnostics[0].code == "IMPORT_MAPPING"


@pytest.mark.parametrize("adapter", ["json", "xlsx"])
def test_evidence_only_connections_cannot_be_confirmed(
    tmp_path: Path, minimal: dict[str, Any], adapter: str
) -> None:
    source = tmp_path / ("links.xlsx" if adapter == "xlsx" else "links.json")
    if adapter == "xlsx":
        source.write_bytes(
            zip_parts(workbook_parts({"Links": [["id", "from", "to"], ["c", "eng", "plc"]]}))
        )
    else:
        source.write_text('[{"id":"c","from":"eng","to":"plc"}]', encoding="utf-8")
    fields = {"id": {"path": "id"}, "source": {"path": "from"}, "destination": {"path": "to"}}
    if adapter == "json":
        for field in fields.values():
            field["path"] = "/" + field["path"]
    profile = StructuredProfile.model_validate(
        {
            "profile_version": 2,
            "adapter": adapter,
            "tables": [
                {
                    "name": "links",
                    "collection": "Links" if adapter == "xlsx" else "",
                    "entity": "connection",
                    "fields": fields,
                }
            ],
        }
    )
    draft = create_draft(source, profile)
    owner = confirmed(draft, minimal).model_copy(update={"model": minimal})
    with pytest.raises(ModelError) as error:
        emit_artifacts(draft, owner, source)
    assert error.value.diagnostics[0].code == "IMPORT_RELATIONSHIP"
    resolution = owner.resolutions[0].model_copy(update={"decision": "OWNER_REJECTED"})
    accepted = emit_artifacts(
        draft, owner.model_copy(update={"resolutions": (resolution,)}), source
    )
    assert (
        validate_bytes(accepted["architecture.yaml"]).model
        == validate_bytes(yaml.safe_dump(minimal).encode()).model
    )


@pytest.mark.parametrize("cached", [False, True])
def test_formula_requires_correction_before_emission(
    tmp_path: Path, minimal: dict[str, Any], cached: bool
) -> None:
    from xml.etree import ElementTree as ET

    from tools.synthetic_inventories import S

    data = fixture_data()
    tables = {k: [list(rows[0]), *[list(r.values()) for r in rows]] for k, rows in data.items()}
    package = workbook_parts(tables)
    sheet = ET.fromstring(package["xl/worksheets/sheet1.xml"])
    cell = sheet[0][1][1]
    cell.clear()
    cell.set("r", "B2")
    ET.SubElement(cell, f"{{{S}}}f").text = "1+1"
    if cached:
        ET.SubElement(cell, f"{{{S}}}v").text = "2"
    package["xl/worksheets/sheet1.xml"] = ET.tostring(sheet)
    source = tmp_path / "formula.xlsx"
    source.write_bytes(zip_parts(package))
    draft = create_draft(source, fixture_profile("xlsx"))
    owner = confirmed(draft, minimal)
    with pytest.raises(ModelError) as error:
        emit_artifacts(draft, owner, source)
    assert error.value.diagnostics[0].code == "IMPORT_CORRECTION"
    candidate = next(
        c
        for c in draft.candidates
        if isinstance(c, StructuredCandidate) and "name" in c.required_corrections
    )
    value = owner.model_dump(mode="json")
    next(r for r in value["resolutions"] if r["candidate_id"] == candidate.candidate_id)[
        "corrections"
    ] = {"name": "Reviewed literal"}
    artifacts = emit_artifacts(draft, OwnerDecisions.model_validate(value), source)
    assert "Reviewed literal" in {
        a.name for a in validate_bytes(artifacts["architecture.yaml"]).model.assets
    }
    assert json.loads(artifacts["architecture.provenance.json"])["records"]


def test_json_top_level_list_and_typed_boolean(tmp_path: Path) -> None:
    profile = fixture_profile().model_dump(mode="json")
    profile["tables"] = [profile["tables"][0]]
    table = profile["tables"][0]
    table["collection"] = ""
    table["fields"]["zone_id"].pop("reference")
    table["fields"]["role"]["value_type"] = "boolean"
    records = fixture_data()["assets"]
    records[0]["role"] = True
    records[1]["role"] = False
    source = tmp_path / "list.json"
    source.write_text(json.dumps(records), encoding="utf-8")
    draft = create_draft(source, StructuredProfile.model_validate(profile))
    assert {
        f.normalized_value for c in draft.candidates for f in c.fields if f.field == "role"
    } == {"true", "false"}


def test_json_diagnostics_and_control_event_limits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from otarchguard.contract import RESOURCE_LIMITS

    source = fixture_source(tmp_path)
    draft = create_draft(source, fixture_profile())
    path = tmp_path / "draft.json"
    path.write_bytes(serialize(draft))
    monkeypatch.setattr(
        "otarchguard.ingestion.workflow.RESOURCE_LIMITS", replace(RESOURCE_LIMITS, parser_events=20)
    )
    with pytest.raises(ModelError) as error:
        load_record(path, ImportDraft)
    assert error.value.diagnostics[0].code == "LIMIT_EXCEEDED"
