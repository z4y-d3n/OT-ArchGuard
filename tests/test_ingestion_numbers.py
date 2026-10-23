"""Exact numeric source/provenance contracts and independent remediation oracles."""

import hashlib
import json
import os
import subprocess
from dataclasses import replace
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any, cast
from xml.etree import ElementTree as ET

import pytest
import yaml
from pydantic import ValidationError

from otarchguard.api import validate_bytes
from otarchguard.diagnostics import ModelError
from otarchguard.ingestion.json_inventory import parse_json
from otarchguard.ingestion.numbers import NumericToken, numeric_text, parse_number
from otarchguard.ingestion.records import (
    ImportDraft,
    OwnerDecisions,
    StructuredCandidate,
    StructuredEvidenceField,
    StructuredProfile,
)
from otarchguard.ingestion.structured import STRUCTURED_LIMITS
from otarchguard.ingestion.workflow import (
    create_draft,
    draft_sha256,
    emit_artifacts,
    load_record,
    review_summary,
    review_template,
    serialize,
)
from otarchguard.ingestion.xlsx import read_workbook
from tools.synthetic_inventories import workbook_parts, zip_parts

TOKENS = [
    "0",
    "-0",
    "0.1",
    "0.10000000000000001",
    "1.0",
    "1.00",
    "1e3",
    "1e-400",
    "1e309",
    "1e-9999",
    "1.234567890123456789012345",
    "9007199254740993",
    "9007199254740993.0",
    "123456789012345678901234567890",
    "-0.1",
    "-1e-400",
    "-9007199254740993.0",
    "0.000000000000000000000001",
    "1e9999",
]


def numeric_profile(adapter: str = "json", expected: str = "number") -> StructuredProfile:
    return StructuredProfile.model_validate(
        {
            "profile_version": 2,
            "adapter": adapter,
            "tables": [
                {
                    "name": "assets",
                    "collection": "assets" if adapter == "xlsx" else "/assets",
                    "entity": "asset",
                    "fields": {
                        "id": {"path": "id" if adapter == "xlsx" else "/id"},
                        "role": {
                            "path": "role" if adapter == "xlsx" else "/role",
                            "value_type": expected,
                        },
                    },
                    "constants": {
                        "name": "Synthetic numeric sample",
                        "zone_id": "control",
                        "kind": "endpoint",
                        "scope": "internal",
                        "domain_classification": "iacs",
                        "safety_classification": "unassessed",
                        "criticality": "unspecified",
                    },
                }
            ],
        }
    )


def numeric_source(
    tmp_path: Path, token: str, adapter: str = "json", *, styled: bool = False
) -> Path:
    source = tmp_path / f"numeric.{adapter}"
    if adapter == "json":
        source.write_bytes(('{"assets":[{"id":"sample","role":' + token + "}]}").encode())
    else:
        parts = workbook_parts({"assets": [["id", "role"], ["sample", 0]]})
        tree = ET.fromstring(parts["xl/worksheets/sheet1.xml"])
        cell = tree[0][1][1]
        cell[0].text = token
        if styled:
            cell.set("s", "1")
        parts["xl/worksheets/sheet1.xml"] = ET.tostring(tree)
        source.write_bytes(zip_parts(parts))
    return source


def numeric_owner(draft: ImportDraft, minimal: dict[str, Any]) -> OwnerDecisions:
    context = dict(minimal)
    context.pop("assets")
    context["zones"] = [{**z, "safety_designation": "unassessed"} for z in minimal["zones"]]
    for key in (
        "interfaces",
        "conduits",
        "transport_edges",
        "forwarding_edges",
        "services",
        "rules",
        "intents",
        "scenarios",
    ):
        context[key] = []
    value = review_template(draft).model_dump(mode="json")
    value.update(
        model=context,
        model_confirmed=True,
        reviewer="Synthetic numeric owner",
        model_rationale="Reviewed exact synthetic source numeric tokens; inventory only.",
    )
    for resolution in value["resolutions"]:
        resolution.update(
            decision="OWNER_CONFIRMED", rationale="Reviewed exact token and category."
        )
    return OwnerDecisions.model_validate(value)


@pytest.mark.parametrize("token", TOKENS)
def test_json_numeric_fidelity_through_emission(
    tmp_path: Path,
    minimal: dict[str, Any],
    token: str,
) -> None:
    source = numeric_source(tmp_path, token)
    draft = create_draft(source, numeric_profile())
    candidate = draft.candidates[0]
    field = next(f for f in candidate.fields if f.field == "role")
    assert isinstance(field, StructuredEvidenceField)
    expected_category = "number" if any(c in token for c in ".eE") else "integer"
    assert field.source_value_type == expected_category
    assert field.normalized_value == token and field.state == "EXPLICIT_SOURCE_VALUE"
    assert field.location is not None and field.location.model_dump()["pointer"] == "/assets/0/role"
    if isinstance(field.raw_value, NumericToken):
        assert field.raw_value.numeric_token == token
        assert field.raw_value.numeric_category == expected_category
    else:
        assert type(field.raw_value) is int and str(field.raw_value) == token
    # Independent exact oracle; Decimal never enters evidence or native models.
    assert Decimal(field.normalized_value) == Decimal(token)
    assert draft.source.sha256 == hashlib.sha256(source.read_bytes()).hexdigest()
    assert serialize(create_draft(source, numeric_profile())) == serialize(draft)
    saved = tmp_path / "draft.json"
    saved.write_bytes(serialize(draft))
    reloaded = load_record(saved, ImportDraft)
    assert serialize(reloaded) == serialize(draft) and draft_sha256(reloaded) == draft_sha256(draft)
    artifacts = emit_artifacts(reloaded, numeric_owner(reloaded, minimal), source)
    snapshot = validate_bytes(artifacts["architecture.yaml"])
    assert snapshot.model.assets[0].role == token
    assert (
        not snapshot.model.transport_edges
        and not snapshot.model.forwarding_edges
        and not snapshot.model.rules
    )
    evidence = json.loads(artifacts["architecture.provenance.json"])
    reviewed = next(
        f for f in evidence["records"][0]["candidate"]["fields"] if f["field"] == "role"
    )
    assert (
        reviewed["normalized_value"] == token and reviewed["source_value_type"] == expected_category
    )
    if expected_category == "number" or token == "-0":
        assert reviewed["raw_value"] == {
            "numeric_token": token,
            "numeric_category": expected_category,
        }


@pytest.mark.parametrize("token", TOKENS)
def test_xlsx_raw_tokens_remain_exact_even_when_review_blocks(
    tmp_path: Path,
    minimal: dict[str, Any],
    token: str,
) -> None:
    source = numeric_source(tmp_path, token, "xlsx")
    draft = create_draft(source, numeric_profile("xlsx"))
    candidate = draft.candidates[0]
    assert isinstance(candidate, StructuredCandidate)
    field = next(f for f in candidate.fields if f.field == "role")
    raw_text = (
        field.raw_value.numeric_token
        if isinstance(field.raw_value, NumericToken)
        else str(field.raw_value)
    )
    assert raw_text == token
    saved = tmp_path / "draft.json"
    saved.write_bytes(serialize(draft))
    assert serialize(load_record(saved, ImportDraft)) == serialize(draft)
    owner = numeric_owner(draft, minimal)
    if "role" in candidate.required_corrections:
        assert field.state == "UNSUPPORTED" and field.normalized_value == ""
        with pytest.raises(ModelError):
            emit_artifacts(draft, owner, source)
        resolution = owner.resolutions[0].model_copy(
            update={"corrections": {"role": "Reviewed literal"}}
        )
        owner = owner.model_copy(update={"resolutions": (resolution,)})
        expected = "Reviewed literal"
    else:
        assert field.normalized_value == token
        expected = token
    artifacts = emit_artifacts(draft, owner, source)
    assert validate_bytes(artifacts["architecture.yaml"]).model.assets[0].role == expected
    original = next(
        f
        for f in json.loads(artifacts["architecture.provenance.json"])["records"][0]["candidate"][
            "fields"
        ]
        if f["field"] == "role"
    )
    if isinstance(field.raw_value, NumericToken):
        assert original["raw_value"]["numeric_token"] == token


@pytest.mark.parametrize("token", ["0.1", "1.00", "1e3", "-0"])
def test_styled_xlsx_numbers_always_require_correction(tmp_path: Path, token: str) -> None:
    draft = create_draft(
        numeric_source(tmp_path, token, "xlsx", styled=True), numeric_profile("xlsx")
    )
    candidate = draft.candidates[0]
    assert isinstance(candidate, StructuredCandidate) and "role" in candidate.required_corrections


@pytest.mark.parametrize(
    "token",
    [
        "NaN",
        "Infinity",
        "-Infinity",
        "+1",
        "01",
        ".1",
        "1.",
        "1e",
        "1e+",
        "1_0",
        "0x10",
        "--1",
        "١",
        "1e10000",
        "1e-10000",
        "1" * 65,
        "1e" + "9" * 62,
    ],
)
@pytest.mark.parametrize("adapter", ["json", "xlsx"])
def test_invalid_or_unbounded_numeric_tokens(tmp_path: Path, token: str, adapter: str) -> None:
    with pytest.raises(ModelError):
        create_draft(numeric_source(tmp_path, token, adapter), numeric_profile(adapter))


def test_numeric_token_budgets_and_compact_extremes() -> None:
    assert type(parse_number("9" * 64)) is int
    with pytest.raises(ModelError):
        parse_number("9" * 65)
    with pytest.raises(ModelError):
        parse_json(b"0.1", replace(STRUCTURED_LIMITS, number_characters=2))
    values = [parse_number(t) for t in ("1e9999", "1e-9999", "-0", "0.1")]
    for value in values:
        assert len(numeric_text(value)) <= 7
        if isinstance(value, NumericToken):
            assert len(serialize(value)) < 100


def test_null_boolean_integer_decimal_and_string_stay_distinct() -> None:
    values = parse_json(b'[null,false,true,0,-0,0.0,"0"]')
    assert isinstance(values, list)
    assert [type(v) for v in values] == [
        type(None),
        bool,
        bool,
        int,
        NumericToken,
        NumericToken,
        str,
    ]
    assert cast(NumericToken, values[4]).numeric_category == "integer"
    assert cast(NumericToken, values[5]).numeric_category == "number"


@pytest.mark.parametrize(
    "value_type,token,correct",
    [
        ("integer", "1.0", False),
        ("integer", "1e3", False),
        ("integer", "-0", True),
        ("integer", "true", False),
        ("number", "true", False),
        ("number", "null", False),
        ("number", '"0.1"', False),
        ("string", "0.1", False),
    ],
)
def test_numeric_mapping_has_no_type_coercion(
    tmp_path: Path, value_type: str, token: str, correct: bool
) -> None:
    candidate = create_draft(
        numeric_source(tmp_path, token), numeric_profile(expected=value_type)
    ).candidates[0]
    assert isinstance(candidate, StructuredCandidate)
    assert ("role" not in candidate.required_corrections) is correct


def test_tag_shaped_source_object_is_not_a_number(tmp_path: Path) -> None:
    candidate = create_draft(
        numeric_source(tmp_path, '{"numeric_token":"0.1","numeric_category":"number"}'),
        numeric_profile(),
    ).candidates[0]
    assert isinstance(candidate, StructuredCandidate) and "role" in candidate.required_corrections
    field = next(f for f in candidate.fields if f.field == "role")
    assert field.source_value_type == "object" and field.raw_value is None


@pytest.mark.parametrize(
    "token,category",
    [("0.1", "integer"), ("1", "number"), ("NaN", "number"), ("1e99999", "number")],
)
def test_pydantic_numeric_tags_validate_category_and_token(token: str, category: str) -> None:
    with pytest.raises(ValidationError):
        NumericToken.model_validate({"numeric_token": token, "numeric_category": category})


@pytest.mark.parametrize("value", [0.1, float("nan"), float("inf"), Decimal("0.1")])
def test_pydantic_evidence_refuses_float_or_decimal_instances(value: object) -> None:
    with pytest.raises(ValidationError):
        StructuredEvidenceField.model_validate(
            {
                "field": "role",
                "raw_value": value,
                "normalized_value": "0.1",
                "source_value_type": "number",
                "transformation": "exact",
                "state": "EXPLICIT_SOURCE_VALUE",
            }
        )


def test_decimal_context_cannot_round_evidence(tmp_path: Path) -> None:
    token = "1.234567890123456789012345"
    with localcontext() as context:
        context.prec = 2
        field = next(
            f
            for f in create_draft(numeric_source(tmp_path, token), numeric_profile())
            .candidates[0]
            .fields
            if f.field == "role"
        )
        assert field.normalized_value == token


def test_emission_quotes_owner_context_text_without_changing_native_types(
    tmp_path: Path, minimal: dict[str, Any]
) -> None:
    source = numeric_source(tmp_path, "1e3")
    draft = create_draft(source, numeric_profile())
    owner = numeric_owner(draft, minimal)
    owner.model["revision"] = "1e-400"
    artifacts = emit_artifacts(draft, owner, source)
    model = validate_bytes(artifacts["architecture.yaml"]).model
    assert model.revision == "1e-400" and model.schema_version == 1
    assert model.assets[0].role == "1e3"


def test_numeric_lexemes_do_not_collide_and_stale_review_fails(
    tmp_path: Path, minimal: dict[str, Any]
) -> None:
    ids = set()
    hashes = set()
    source = numeric_source(tmp_path, "0.1")
    first = create_draft(source, numeric_profile())
    owner = numeric_owner(first, minimal)
    for token in ("0.1", "0.10000000000000001", "1.0", "1.00", "1e0", "0", "-0"):
        numeric_source(tmp_path, token)
        draft = create_draft(source, numeric_profile())
        ids.add(draft.candidates[0].candidate_id)
        hashes.add(draft_sha256(draft))
    assert len(ids) == len(hashes) == 7
    with pytest.raises(ModelError) as error:
        emit_artifacts(first, owner, source)
    assert error.value.diagnostics[0].code == "IMPORT_SOURCE_CHANGED"
    with pytest.raises(ModelError) as error:
        emit_artifacts(draft, owner, source)
    assert error.value.diagnostics[0].code == "IMPORT_STALE_REVIEW"


def test_numeric_key_reordering_preserves_semantic_identity(tmp_path: Path) -> None:
    source = numeric_source(tmp_path, "0.10000000000000001")
    first = create_draft(source, numeric_profile())
    source.write_bytes(b'{"assets":[{"role":0.10000000000000001,"id":"sample"}]}')
    second = create_draft(source, numeric_profile())
    assert first.candidates[0].candidate_id == second.candidates[0].candidate_id
    assert draft_sha256(first) != draft_sha256(second)


def test_legacy_v2_drafts_are_explicitly_untrusted(tmp_path: Path, minimal: dict[str, Any]) -> None:
    source = numeric_source(tmp_path, "0.1")
    draft = create_draft(source, numeric_profile())
    decisions = numeric_owner(draft, minimal)
    legacy = draft.model_copy(update={"import_version": 2})
    path = tmp_path / "legacy.json"
    path.write_bytes(serialize(legacy))
    for operation in (
        lambda: load_record(path, ImportDraft),
        lambda: review_template(legacy),
        lambda: review_summary(legacy),
        lambda: emit_artifacts(legacy, decisions, source),
    ):
        with pytest.raises(ModelError) as error:
            operation()
        assert error.value.diagnostics[0].code == "IMPORT_LEGACY_DRAFT"


@pytest.mark.parametrize(
    "change",
    ["decimal_version", "numeric_confirmation", "numeric_correction", "numeric_native_port"],
)
def test_json_controls_do_not_coerce_numbers(
    tmp_path: Path, minimal: dict[str, Any], change: str
) -> None:
    draft = create_draft(numeric_source(tmp_path, "0.1"), numeric_profile())
    value = numeric_owner(draft, minimal).model_dump(mode="json")
    if change == "decimal_version":
        value["decisions_version"] = 1.0
    if change == "numeric_confirmation":
        value["model_confirmed"] = 1
    if change == "numeric_correction":
        value["resolutions"][0]["corrections"] = {"role": 0.1}
    if change == "numeric_native_port":
        value["model"]["services"] = [{"destination_ports": [{"start": 1.0, "end": 2}]}]
    path = tmp_path / "owner.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ModelError) as error:
        load_record(path, OwnerDecisions)
    assert error.value.diagnostics[0].code == "IMPORT_CONTROL"


def test_expanded_xml_names_charge_the_existing_text_budget(tmp_path: Path) -> None:
    parts = workbook_parts({"assets": [["id"], ["a"]]})
    uri = "urn:" + "a" * 1024
    parts["docProps/core.xml"] = ('<r xmlns:n="' + uri + '">' + "<n:x/>" * 3000 + "</r>").encode()
    source = tmp_path / "expanded.xlsx"
    source.write_bytes(zip_parts(parts))
    with pytest.raises(ModelError) as error:
        read_workbook(source)
    assert error.value.diagnostics[0].code == "LIMIT_EXCEEDED"
    assert "xlsx_xml_text" in error.value.diagnostics[0].message


@pytest.mark.parametrize("identity", ["01", "١", "4294967296"])
def test_conflicting_or_invalid_workbook_numeric_identities(tmp_path: Path, identity: str) -> None:
    parts = workbook_parts({"a": [["id"], ["a"]], "b": [["id"], ["b"]]})
    tree = ET.fromstring(parts["xl/workbook.xml"])
    tree[0][0].set("sheetId", "1")
    tree[0][1].set("sheetId", identity)
    parts["xl/workbook.xml"] = ET.tostring(tree)
    source = tmp_path / "identity.xlsx"
    source.write_bytes(zip_parts(parts))
    with pytest.raises(ModelError) as error:
        read_workbook(source)
    assert error.value.diagnostics[0].code == "IMPORT_XLSX_SHEET"


@pytest.mark.parametrize(
    "adapter,token",
    [
        ("json", "0.10000000000000001"),
        ("json", "1e-400"),
        ("json", "9007199254740993.0"),
        ("xlsx", "0.1"),
        ("xlsx", "1e-400"),
    ],
)
def test_installed_cli_numeric_review_round_trip(
    tmp_path: Path,
    minimal: dict[str, Any],
    installed_console: Path,
    adapter: str,
    token: str,
) -> None:
    source = numeric_source(tmp_path, token, adapter)
    profile = tmp_path / "profile.json"
    profile.write_bytes(serialize(numeric_profile(adapter)))
    draft_path = tmp_path / "draft.json"
    owner_path = tmp_path / "owner.json"
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

    invoke("import", "map", str(source), "--profile", str(profile), "--output", str(draft_path))
    invoke("import", "review", str(draft_path), "--decisions", str(owner_path))
    draft = load_record(draft_path, ImportDraft)
    owner = numeric_owner(draft, minimal)
    field = next(f for f in draft.candidates[0].fields if f.field == "role")
    assert isinstance(field.raw_value, NumericToken) and field.raw_value.numeric_token == token
    candidate = draft.candidates[0]
    if isinstance(candidate, StructuredCandidate) and "role" in candidate.required_corrections:
        owner_path.write_bytes(serialize(owner))
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
            == "IMPORT_CORRECTION"
        )
        assert not output.exists()
        owner = owner.model_copy(
            update={
                "resolutions": (
                    owner.resolutions[0].model_copy(
                        update={"corrections": {"role": "Owner corrected"}}
                    ),
                )
            }
        )
        expected = "Owner corrected"
    else:
        expected = token
    owner_path.write_bytes(serialize(owner))
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
    )
    invoke("validate", str(output / "architecture.yaml"))
    assert (
        yaml.safe_load((output / "architecture.yaml").read_text(encoding="utf-8"))["assets"][0][
            "role"
        ]
        == expected
    )
