"""Evidence, identity, review and native-model contracts for the first import gate."""

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from otarchguard.api import validate_bytes
from otarchguard.diagnostics import ModelError
from otarchguard.ingestion.records import (
    ImportDraft,
    MappingProfile,
    OwnerDecisions,
    SourceLocation,
)
from otarchguard.ingestion.tabular import DelimitedAdapter, ImportLimits
from otarchguard.ingestion.workflow import (
    create_draft,
    draft_sha256,
    emit_artifacts,
    load_record,
    map_table,
    review_summary,
    review_template,
    serialize,
    write_new_bundle,
    write_new_file,
)
from otarchguard.trace import trace_architecture

EXAMPLES = Path(__file__).resolve().parents[1] / "examples/import-studio"


@pytest.fixture
def profile() -> MappingProfile:
    return load_record(EXAMPLES / "assets-profile.yaml", MappingProfile)


@pytest.fixture
def source(tmp_path: Path) -> Path:
    path = tmp_path / "assets.csv"
    path.write_bytes((EXAMPLES / "assets.csv").read_bytes())
    return path


def owner(draft: ImportDraft, context: dict[str, Any] | None = None) -> OwnerDecisions:
    value = review_template(draft).model_dump(mode="json")
    value.update(
        {
            "reviewer": "Synthetic tutorial owner",
            "model_confirmed": True,
            "model_rationale": "Finite inventory reviewed; no communication declared.",
            "model": context
            if context is not None
            else yaml.safe_load((EXAMPLES / "model-context.yaml").read_text(encoding="utf-8")),
        }
    )
    for resolution in value["resolutions"]:
        resolution.update(decision="OWNER_CONFIRMED", rationale="Verified synthetic row.")
    return OwnerDecisions.model_validate(value)


def assert_code(error: pytest.ExceptionInfo[ModelError], code: str) -> None:
    assert error.value.diagnostics[0].code == code


def test_actual_inventory_and_provenance(source: Path, profile: MappingProfile) -> None:
    draft = create_draft(source, profile)
    assert draft.source.sha256 == hashlib.sha256(source.read_bytes()).hexdigest()
    assert draft.source.name == "assets.csv" and not draft.conflicts
    assert len(draft.candidates) == 2
    assert all(c.state == "UNRESOLVED" for c in draft.candidates)
    controller = next(
        c for c in draft.candidates if c.unmapped["Inventory note"].startswith("Label")
    )
    field = next(f for f in controller.fields if f.field == "id")
    assert field.raw_value == field.normalized_value == "plc"
    assert field.state == "EXPLICIT_SOURCE_VALUE"
    assert isinstance(field.location, SourceLocation)
    assert (field.location.row, field.location.column, field.location.line_start) == (2, 1, 3)
    constant = next(f for f in controller.fields if f.field == "kind")
    assert constant.state == "CANDIDATE_INFERENCE" and constant.location is None
    assert controller.unmapped == {"Inventory note": "Label, with quoted comma"}
    artifacts = emit_artifacts(draft, owner(draft), source)
    model = validate_bytes(artifacts["architecture.yaml"])
    assert {a.id for a in model.model.assets} == {"eng", "plc"}
    for name in ("interfaces", "transport_edges", "forwarding_edges", "services", "rules"):
        assert not getattr(model.model, name)
    provenance = json.loads(artifacts["architecture.provenance.json"])
    assert provenance["model_sha256"] == model.sha256
    assert provenance["draft_sha256"] == draft_sha256(draft)
    assert {r["model_id"] for r in provenance["records"]} == {"eng", "plc"}
    assert str(source.parent).encode() not in artifacts["architecture.provenance.json"]


def test_repeated_import_and_emission_are_identical(source: Path, profile: MappingProfile) -> None:
    first, second = create_draft(source, profile), create_draft(source, profile)
    assert serialize(first) == serialize(second)
    assert emit_artifacts(first, owner(first), source) == emit_artifacts(
        second, owner(second), source
    )


def test_row_order_preserves_candidates_and_model_requires_new_review(
    source: Path, profile: MappingProfile
) -> None:
    first = create_draft(source, profile)
    first_model = emit_artifacts(first, owner(first), source)["architecture.yaml"]
    original = source.read_text(encoding="utf-8").splitlines()
    source.write_text("\n".join([original[0], *reversed(original[1:])]) + "\n", encoding="utf-8")
    second = create_draft(source, profile)
    assert [c.candidate_id for c in first.candidates] == [c.candidate_id for c in second.candidates]
    assert draft_sha256(first) != draft_sha256(second)
    with pytest.raises(ModelError) as error:
        emit_artifacts(second, owner(first), source)
    assert_code(error, "IMPORT_STALE_REVIEW")
    # Reordering evidence does not change accepted native inventory identity.
    assert emit_artifacts(second, owner(second), source)["architecture.yaml"] == first_model


def test_profile_property_order_is_irrelevant(source: Path, profile: MappingProfile) -> None:
    value = profile.model_dump()
    value["fields"] = dict(reversed(list(profile.fields.items())))
    alternate = MappingProfile.model_validate(value)
    assert serialize(create_draft(source, profile)) == serialize(create_draft(source, alternate))


def test_template_is_unconfirmed_and_review_lists_coverage(
    source: Path, profile: MappingProfile
) -> None:
    draft = create_draft(source, profile)
    template = review_template(draft)
    assert not template.model_confirmed
    assert all(r.decision == "UNRESOLVED" for r in template.resolutions)
    summary = review_summary(draft)
    assert summary["coverage"] == {
        "rows": 2,
        "mapped_fields_per_row": 4,
        "unmapped_columns": ["Inventory note"],
    }
    with pytest.raises(ModelError) as error:
        emit_artifacts(draft, template, source)
    assert_code(error, "IMPORT_REVIEW")


@pytest.mark.parametrize("change", ["source", "draft", "hash"])
def test_changed_evidence_refuses_emission(
    source: Path, profile: MappingProfile, change: str
) -> None:
    draft = create_draft(source, profile)
    decisions = owner(draft)
    if change == "source":
        source.write_bytes(source.read_bytes().replace(b"Controller", b"Router"))
    elif change == "draft":
        draft = draft.model_copy(update={"headers": ("tampered",)})
    else:
        decisions = decisions.model_copy(update={"draft_sha256": "0" * 64})
    with pytest.raises(ModelError) as error:
        emit_artifacts(draft, decisions, source)
    assert_code(error, "IMPORT_STALE_REVIEW" if change == "hash" else "IMPORT_SOURCE_CHANGED")


@pytest.mark.parametrize("change", ["missing", "unknown", "duplicate", "unresolved", "no_reason"])
def test_incomplete_or_invalid_decisions_refused(
    source: Path, profile: MappingProfile, change: str
) -> None:
    draft = create_draft(source, profile)
    value = owner(draft).model_dump(mode="json")
    if change == "missing":
        value["resolutions"].pop()
    elif change == "unknown":
        value["resolutions"][0]["candidate_id"] = "unknown"
    elif change == "duplicate":
        value["resolutions"].append(value["resolutions"][0])
    elif change == "unresolved":
        value["resolutions"][0]["decision"] = "UNRESOLVED"
    else:
        value["resolutions"][0]["rationale"] = "  "
    with pytest.raises(ModelError):
        emit_artifacts(draft, OwnerDecisions.model_validate(value), source)


@pytest.mark.parametrize("resolution", ["reject", "correct"])
def test_duplicate_identity_requires_explicit_resolution(
    source: Path, profile: MappingProfile, resolution: str
) -> None:
    source.write_bytes(source.read_bytes().replace(b"plc,Synthetic", b"eng,Synthetic"))
    draft = create_draft(source, profile)
    assert len(draft.conflicts) == 1 and draft.conflicts[0].identity == "eng"
    with pytest.raises(ModelError) as error:
        emit_artifacts(draft, owner(draft), source)
    assert_code(error, "IMPORT_CONFLICT")
    value = owner(draft).model_dump(mode="json")
    if resolution == "reject":
        value["resolutions"][0]["decision"] = "OWNER_REJECTED"
    else:
        value["resolutions"][0]["corrections"] = {"id": "corrected"}
    artifacts = emit_artifacts(draft, OwnerDecisions.model_validate(value), source)
    model = validate_bytes(artifacts["architecture.yaml"])
    assert len(model.model.assets) == (1 if resolution == "reject" else 2)
    evidence = json.loads(artifacts["architecture.provenance.json"])
    assert evidence["conflicts"] and evidence["records"][0]["resolution"]["rationale"]


def test_identical_rows_remain_separate_conflicting_evidence(
    source: Path, profile: MappingProfile
) -> None:
    lines = source.read_bytes().splitlines(keepends=True)
    source.write_bytes(b"".join([*lines, lines[1]]))
    draft = create_draft(source, profile)
    assert len(draft.candidates) == 3 and len(draft.conflicts) == 1
    assert len({c.candidate_id for c in draft.candidates}) == 3


def test_missing_fields_preserved_and_correctable(source: Path, profile: MappingProfile) -> None:
    source.write_bytes(source.read_bytes().replace(b"plc,Synthetic controller", b"plc,"))
    draft = create_draft(source, profile)
    assert any(d.code == "REVIEW_REQUIRED" for d in draft.diagnostics)
    assert any(c.ambiguities for c in draft.candidates)
    with pytest.raises(ModelError):
        emit_artifacts(draft, owner(draft), source)
    value = owner(draft).model_dump(mode="json")
    target = next(c.candidate_id for c in draft.candidates if c.ambiguities)
    next(r for r in value["resolutions"] if r["candidate_id"] == target)["corrections"] = {
        "name": "Owner corrected controller"
    }
    assert emit_artifacts(draft, OwnerDecisions.model_validate(value), source)


def test_no_silent_whitespace_enum_or_numeric_coercion(tmp_path: Path) -> None:
    source = tmp_path / "inventory.csv"
    source.write_text("id,name,kind\n01, spaced ,ENDPOINT\n", encoding="utf-8")
    profile = MappingProfile(
        profile_version=1, entity="asset", fields={"id": "id", "name": "name", "kind": "kind"}
    )
    draft = create_draft(source, profile)
    assert {f.field: f.normalized_value for f in draft.candidates[0].fields} == {
        "id": "01",
        "name": " spaced ",
        "kind": "ENDPOINT",
    }
    assert draft.candidates[0].ambiguities


def test_native_validator_is_authoritative(source: Path, profile: MappingProfile) -> None:
    draft = create_draft(source, profile)
    value = owner(draft).model_dump(mode="json")
    value["model"]["zones"] = []
    with pytest.raises(ModelError):
        emit_artifacts(draft, OwnerDecisions.model_validate(value), source)
    value["model"] = owner(draft).model_dump(mode="json")["model"]
    value["model"]["assets"] = []
    with pytest.raises(ModelError) as error:
        emit_artifacts(draft, OwnerDecisions.model_validate(value), source)
    assert_code(error, "IMPORT_REVIEW")


def test_inventory_does_not_create_permission(
    source: Path, profile: MappingProfile, minimal: dict[str, Any]
) -> None:
    context = dict(minimal)
    context.pop("assets")
    context["rules"] = []
    context["zones"][0]["safety_designation"] = "unassessed"
    draft = create_draft(source, profile)
    artifacts = emit_artifacts(draft, owner(draft, context), source)
    snapshot = validate_bytes(artifacts["architecture.yaml"])
    result = trace_architecture(snapshot, "eng", "svc_plc")
    assert result.intervals and all(not interval.reachable for interval in result.intervals)


def test_connection_is_evidence_only(tmp_path: Path, minimal: dict[str, Any]) -> None:
    source = tmp_path / "links.csv"
    source.write_text("id,from,to\nl1,eng,plc\n", encoding="utf-8")
    profile = MappingProfile(
        profile_version=1,
        entity="connection",
        fields={"id": "id", "source": "from", "destination": "to"},
    )
    draft = create_draft(source, profile)
    assert draft.candidates[0].ambiguities
    with pytest.raises(ModelError) as error:
        emit_artifacts(draft, owner(draft, minimal), source)
    assert_code(error, "IMPORT_RELATIONSHIP")


@pytest.mark.parametrize("kind", ["zone", "interface"])
def test_other_inventory_entity_kinds(tmp_path: Path, minimal: dict[str, Any], kind: str) -> None:
    collection = "zones" if kind == "zone" else "interfaces"
    entries = minimal.pop(collection)
    source = tmp_path / "table.csv"
    with source.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, list(entries[0]))
        writer.writeheader()
        writer.writerows(entries)
    profile = MappingProfile.model_validate(
        {
            "profile_version": 1,
            "entity": kind,
            "fields": {k: k for k in entries[0]},
        }
    )
    draft = create_draft(source, profile)
    artifacts = emit_artifacts(draft, owner(draft, minimal), source)
    assert validate_bytes(artifacts["architecture.yaml"])


@pytest.mark.parametrize(
    "mapping",
    [
        {"id": "missing"},
        {"id": "Asset ID", "wrong": "Role"},
        {"id": "Asset ID", "name": "Asset ID"},
        {"name": "Display Name"},
    ],
)
def test_rejected_mappings(source: Path, mapping: dict[str, str]) -> None:
    profile = MappingProfile(profile_version=1, entity="asset", fields=mapping)
    with pytest.raises(ModelError) as error:
        create_draft(source, profile)
    assert_code(error, "IMPORT_MAPPING")


@pytest.mark.parametrize(
    "text",
    [
        "",
        "id,id\na,b\n",
        "id, ID \na,b\n",
        "id,\na,b\n",
        "id,name\na\n",
        'id,name\na,"unterminated\n',
        'id,name\na,ba"re\n',
        'id,name\na,"ok"x\n',
        "id,name\n",
        "id,name\n\n",
        "id,name\n,\n",
        "id,name\na,b,c\n",
        "id,<<\na,b\n",
    ],
)
def test_malformed_tables_are_rejected(tmp_path: Path, text: str) -> None:
    source = tmp_path / "bad.csv"
    source.write_text(text, encoding="utf-8")
    with pytest.raises(ModelError):
        DelimitedAdapter().read(source)


@pytest.mark.parametrize("data", [b"id\na\x00", b"id\na\xff", b"PK\x03\x04\x00", b"id\n\x1b[31m"])
def test_binary_and_malformed_unicode_rejected(tmp_path: Path, data: bytes) -> None:
    source = tmp_path / "binary.csv"
    source.write_bytes(data)
    with pytest.raises(ModelError):
        DelimitedAdapter().read(source)


def test_bom_tsv_multiline_and_exact_locations(tmp_path: Path) -> None:
    source = tmp_path / "assets.tsv"
    source.write_bytes('\ufeffid\tlabel\r\na\t"Célula\nTwo lines"\r\nb\t"A ""quote"""\r\n'.encode())
    table = DelimitedAdapter().read(source)
    assert table.headers == ("id", "label")
    assert table.rows[0].values == ("a", "Célula\nTwo lines")
    assert (table.rows[0].line_start, table.rows[0].line_end, table.rows[1].line_start) == (2, 3, 4)
    assert table.rows[1].values[1] == 'A "quote"'


def test_explicit_encoding_delimiter_and_suffix(tmp_path: Path) -> None:
    source = tmp_path / "source.csv"
    source.write_bytes("id;label\na;Célula\n".encode("cp1252"))
    with pytest.raises(ModelError):
        DelimitedAdapter().read(source)
    table = DelimitedAdapter().read(source, delimiter=";", encoding="cp1252")
    assert table.rows[0].values == ("a", "Célula")
    with pytest.raises(ModelError):
        DelimitedAdapter().read(source, encoding="guess")
    source = tmp_path / "source.xlsx"
    source.write_bytes(b"id\na\n")
    with pytest.raises(ModelError) as error:
        DelimitedAdapter().read(source)
    assert_code(error, "IMPORT_FORMAT")


@pytest.mark.parametrize("delimiter", ["", "ab", '"', "\n", "\x00", "\x1b", "\ud800"])
def test_hostile_delimiters(source: Path, delimiter: str) -> None:
    with pytest.raises(ModelError):
        DelimitedAdapter().read(source, delimiter=delimiter)


@pytest.mark.parametrize(
    "limits",
    [
        ImportLimits(source_bytes=10),
        ImportLimits(rows=1),
        ImportLimits(columns=2),
        ImportLimits(cells=5),
        ImportLimits(field_characters=5),
    ],
)
def test_resource_ceilings(source: Path, limits: ImportLimits) -> None:
    with pytest.raises(ModelError) as error:
        DelimitedAdapter(limits).read(source)
    assert_code(error, "LIMIT_EXCEEDED")


def test_formula_like_text_stays_inert_and_diagnostic_overflow_is_bounded(tmp_path: Path) -> None:
    source = tmp_path / "formula.csv"
    source.write_text('id,name\na,"=HYPERLINK(""https://invalid.example"")"\n', encoding="utf-8")
    profile = MappingProfile(profile_version=1, entity="asset", fields={"id": "id", "name": "name"})
    draft = create_draft(source, profile)
    assert any(d.code == "FORMULA_LIKE_TEXT" for d in draft.diagnostics)
    raw_value = draft.candidates[0].fields[1].raw_value
    assert isinstance(raw_value, str) and "HYPERLINK" in raw_value
    source.write_text("id\n" + "\n".join(f"a{i}" for i in range(201)), encoding="utf-8")
    profile = MappingProfile(profile_version=1, entity="asset", fields={"id": "id"})
    with pytest.raises(ModelError) as error:
        create_draft(source, profile)
    assert_code(error, "LIMIT_EXCEEDED")


@pytest.mark.parametrize(
    "text",
    [
        "profile_version: 1\nprofile_version: 1\n",
        "!!python/object/apply:os.system [echo unsafe]",
        "x: &a [*a]",
        "[" * 40 + "]" * 40,
        '{"profile_version": true,"entity":"asset","fields":{"id":"id"}}',
    ],
)
def test_hostile_control_documents_are_rejected(tmp_path: Path, text: str) -> None:
    path = tmp_path / "profile.yaml"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ModelError):
        load_record(path, MappingProfile)


def test_import_version_is_strict_and_extra_fields_forbidden() -> None:
    with pytest.raises(ValidationError):
        MappingProfile.model_validate(
            {"profile_version": True, "entity": "asset", "fields": {"id": "id"}}
        )
    with pytest.raises(ValidationError):
        MappingProfile.model_validate(
            {"profile_version": 1, "entity": "asset", "fields": {"id": "id"}, "extra": 1}
        )


def test_special_file_and_symlink_rejected(tmp_path: Path) -> None:
    with pytest.raises(ModelError):
        DelimitedAdapter().read(tmp_path / "absent.csv")
    directory = tmp_path / "directory.csv"
    directory.mkdir()
    with pytest.raises(ModelError):
        DelimitedAdapter().read(directory)


def test_leaf_symlink_refused_before_read(source: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "is_symlink", lambda self: self == source)
    with pytest.raises(ModelError) as error:
        DelimitedAdapter().read(source)
    assert_code(error, "IMPORT_FILE")


def test_column_order_and_source_directory_do_not_change_candidate_identity(
    source: Path, profile: MappingProfile, tmp_path: Path
) -> None:
    original = create_draft(source, profile)
    with source.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.reader(stream))
    destination = tmp_path / "other directory"
    destination.mkdir()
    reordered = destination / source.name
    with reordered.open("w", encoding="utf-8", newline="") as stream:
        csv.writer(stream).writerows(reversed(row) for row in rows)
    alternate = create_draft(reordered, profile)
    assert [c.candidate_id for c in original.candidates] == [
        c.candidate_id for c in alternate.candidates
    ]


@pytest.mark.parametrize(
    "content",
    [
        b"id\n" + b"x" * 4097 + b"\n",
        b"id\n" + b"x\n" * 1001,
        b",".join(f"h{i}".encode() for i in range(65)) + b"\n" + b",".join([b"v"] * 65),
        b"id\n" + b"x" * (1024 * 1024),
    ],
    ids=["field", "rows", "columns", "bytes"],
)
def test_actual_default_resource_limits(tmp_path: Path, content: bytes) -> None:
    before = csv.field_size_limit()
    path = tmp_path / "excessive.csv"
    path.write_bytes(content)
    with pytest.raises(ModelError) as error:
        DelimitedAdapter().read(path)
    assert_code(error, "LIMIT_EXCEEDED")
    assert csv.field_size_limit() == before


def test_generated_draft_must_fit_review_parser_event_budget(tmp_path: Path) -> None:
    source = tmp_path / "fully_mapped.csv"
    fields = [
        "id",
        "name",
        "role",
        "zone_id",
        "kind",
        "scope",
        "domain_classification",
        "safety_classification",
        "criticality",
    ]
    with source.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(fields)
        writer.writerows(
            [
                f"a{i}",
                "Controller",
                "Control",
                "control",
                "endpoint",
                "internal",
                "iacs",
                "unassessed",
                "unspecified",
            ]
            for i in range(1000)
        )
    profile = MappingProfile(profile_version=1, entity="asset", fields={f: f for f in fields})
    with pytest.raises(ModelError) as error:
        create_draft(source, profile)
    assert_code(error, "LIMIT_EXCEEDED")
    assert "parser_events" in error.value.diagnostics[0].message


def test_atomic_file_no_overwrite_and_cleanup(tmp_path: Path) -> None:
    output = tmp_path / "draft.json"
    write_new_file(output, b"first")
    with pytest.raises(ModelError):
        write_new_file(output, b"second")
    assert output.read_bytes() == b"first"
    assert not list(tmp_path.glob(".otarchguard-*"))


def test_bundle_publication_and_overwrite_preservation(
    source: Path, profile: MappingProfile, tmp_path: Path
) -> None:
    draft = create_draft(source, profile)
    artifacts = emit_artifacts(draft, owner(draft), source)
    output = tmp_path / "bundle"
    write_new_bundle(output, artifacts)
    assert {p.name for p in output.iterdir()} == set(artifacts)
    with pytest.raises(ModelError):
        write_new_bundle(output, artifacts)
    assert {p.name: p.read_bytes() for p in output.iterdir()} == artifacts
    assert not list(tmp_path.glob(".otarchguard-*"))


def test_failed_bundle_publish_cleans_staging(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def denied(*args: object) -> None:
        raise OSError("synthetic filesystem failure")

    monkeypatch.setattr("otarchguard.ingestion.workflow.os.rename", denied)
    with pytest.raises(ModelError):
        write_new_bundle(
            tmp_path / "output",
            {
                "architecture.yaml": b"model",
                "architecture.provenance.json": b"evidence",
            },
        )
    assert not (tmp_path / "output").exists()
    assert not list(tmp_path.glob(".otarchguard-*"))


def test_path_traversal_bundle_name_refused(tmp_path: Path) -> None:
    with pytest.raises(ModelError):
        write_new_bundle(tmp_path / "bundle", {"../escape": b"bad"})
    assert not (tmp_path / "escape").exists()


def test_read_draft_round_trip(source: Path, profile: MappingProfile, tmp_path: Path) -> None:
    draft = create_draft(source, profile)
    output = tmp_path / "draft.json"
    write_new_file(output, serialize(draft))
    assert serialize(load_record(output, ImportDraft)) == serialize(draft)
    assert map_table(DelimitedAdapter().read(source), profile) == draft
