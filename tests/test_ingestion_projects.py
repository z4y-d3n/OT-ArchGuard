"""Independent project workflow oracles: partitions, stale evidence and native analysis."""

import json
import shutil
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from otarchguard.api import validate_bytes
from otarchguard.cli import app
from otarchguard.contract import RESOURCE_LIMITS
from otarchguard.diagnostics import ModelError
from otarchguard.graph import build_graph
from otarchguard.ingestion import project, project_review
from otarchguard.ingestion.project import (
    check_project_envelope,
    create_project,
    load_manifest,
    load_project_record,
    project_digest,
    project_path,
    protected_output,
)
from otarchguard.ingestion.project_records import ProjectDecisions, ProjectDraft
from otarchguard.ingestion.project_review import (
    acknowledge_connectors,
    connector_sets,
    emit_project,
    project_summary,
    project_template,
    resolve_entity,
    review_markdown,
)
from otarchguard.ingestion.reconciliation import catalog
from otarchguard.ingestion.workflow import _declaration_yaml, serialize, write_new_bundle
from otarchguard.trace import trace_architecture
from tools.synthetic_projects import synthetic_project, tutorial_decisions, write_json


@pytest.fixture
def manifest(tmp_path: Path) -> Path:
    return synthetic_project(tmp_path / "project")


def change(path: Path, mutate: Any) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    mutate(payload)
    write_json(path, payload)


def error_code(operation: Any, code: str) -> None:
    with pytest.raises(ModelError) as caught:
        operation()
    assert caught.value.diagnostics[0].code == code


def test_shipped_project_review_matches_exact_checked_out_fixture(tmp_path: Path) -> None:
    """Exercise the saved review, rather than generate new decisions for the current bytes."""
    shipped = Path(__file__).resolve().parents[1] / "examples/import-studio/projects/mixed"
    copied = tmp_path / "project"
    shutil.copytree(shipped, copied)
    path = copied / "project.json"
    draft = create_project(path)
    owner = load_project_record(copied / "tutorial-decisions.json", ProjectDecisions)
    assert project_digest(draft) == owner.draft_sha256
    artifacts = emit_project(draft, owner, path)
    model = validate_bytes(artifacts["architecture.yaml"]).model
    assert len(model.assets) == 6
    assert not model.transport_edges and not model.forwarding_edges and not model.rules

    # Byte changes still invalidate review even when parsed CSV values are identical.
    source = copied / "metadata.csv"
    original = source.read_bytes()
    assert b"\r\n" not in original
    source.write_bytes(original.replace(b"\n", b"\r\n"))
    changed = create_project(path)
    assert project_digest(changed) != owner.draft_sha256
    error_code(lambda: emit_project(changed, owner, path), "PROJECT_STALE_REVIEW")


@pytest.mark.parametrize(
    "graph,formats",
    [
        ("drawio", ("xlsx", "graph")),
        ("graphml", ("json", "graph")),
        ("drawio", ("csv", "xlsx", "json", "graph")),
        ("graphml", ("csv", "xlsx", "json", "graph")),
    ],
)
def test_heterogeneous_native_emission(
    tmp_path: Path, graph: str, formats: tuple[str, ...]
) -> None:
    path = synthetic_project(tmp_path, graph=graph, formats=formats)
    draft = create_project(path)
    owner = tutorial_decisions(draft)
    artifacts = emit_project(draft, owner, path)
    validated = validate_bytes(artifacts["architecture.yaml"])
    assert len(validated.model.assets) == 6
    assert not build_graph(validated.model, RESOURCE_LIMITS).edges
    sidecar = json.loads(artifacts["architecture.provenance.json"])
    assert len(sidecar["catalog"]["sources"]) == len(formats)
    assert sidecar["model_sha256"] == validated.sha256
    assert len(sidecar["identity_index"]) == draft.accounting["candidates"]
    assert not validated.model.rules and not validated.model.transport_edges
    assert artifacts == emit_project(draft, owner, path)


def test_catalog_keeps_all_observations_and_owner_conflict_resolution(manifest: Path) -> None:
    draft = create_project(manifest)
    assert len(catalog(draft.sources)) == 26
    assert len(draft.conflicts) == 1 and "zone_id" in draft.conflicts[0].differences
    assert all(c.state == "UNRESOLVED" for _, c in catalog(draft.sources).values())
    owner = tutorial_decisions(draft)
    artifacts = emit_project(draft, owner, manifest)
    model = validate_bytes(artifacts["architecture.yaml"]).model
    assert all(a.zone_id == "control" for a in model.assets)
    sidecar = artifacts["architecture.provenance.json"]
    assert b'"alternate"' in sidecar and b'"field_sources"' in sidecar
    assert len(json.loads(sidecar)["decisions"]["entities"]) == 14
    # Neither an unresolved template nor a preferred source confirms anything.
    error_code(lambda: emit_project(draft, project_template(draft), manifest), "PROJECT_REVIEW")


@pytest.mark.parametrize("mutation", ["source", "profile", "context", "manifest", "draft"])
def test_any_material_mutation_invalidates_current_review(manifest: Path, mutation: str) -> None:
    draft = create_project(manifest)
    owner = tutorial_decisions(draft)
    if mutation == "draft":
        draft = draft.model_copy(update={"accounting": {**draft.accounting, "candidates": 0}})
    elif mutation == "manifest":
        change(manifest, lambda d: d.update(project_id="changed"))
    else:
        path = (
            manifest.parent
            / {
                "source": "metadata.csv",
                "profile": "metadata-profile.json",
                "context": "context.json",
            }[mutation]
        )
        path.write_bytes(
            path.read_bytes().replace(b"Engineering", b"Different")
            if mutation == "source"
            else path.read_bytes() + b"\n"
        )
    error_code(lambda: emit_project(draft, owner, manifest), "PROJECT_SOURCE_CHANGED")


def test_manifest_order_alias_order_and_relocation_contract(manifest: Path, tmp_path: Path) -> None:
    first = create_project(manifest)
    members = next(p.members for p in first.proposals if p.field == "id")
    change(
        manifest,
        lambda d: d.update(
            aliases=[
                {
                    "members": list(members),
                    "rationale": "Owner configuration proposes these aliases.",
                }
            ]
        ),
    )
    first = create_project(manifest)
    owner = tutorial_decisions(first)
    initial = emit_project(first, owner, manifest)
    change(manifest, lambda d: (d["sources"].reverse(), d["aliases"][0]["members"].reverse()))
    assert serialize(create_project(manifest)) == serialize(first)
    assert emit_project(first, owner, manifest) == initial
    destination = tmp_path / "relocated_é"
    shutil.copytree(manifest.parent, destination)
    assert serialize(create_project(destination / manifest.name)) == serialize(first)
    assert emit_project(first, owner, destination / manifest.name) == initial
    assert str(manifest.parent).encode() not in serialize(first)


@pytest.mark.parametrize("graph", ["drawio", "graphml"])
def test_actual_native_trace_denied_despite_identity_interfaces_and_arrows(
    tmp_path: Path, graph: str
) -> None:
    path = synthetic_project(tmp_path, graph=graph)
    change(
        tmp_path / "context.json",
        lambda c: c.update(
            services=[
                {
                    "id": "svc_plc",
                    "asset_id": "plc",
                    "interface_id": "if_plc",
                    "protocol": "tcp",
                    "destination_ports": [{"start": 502, "end": 502}],
                }
            ]
        ),
    )
    draft = create_project(path)
    artifacts = emit_project(draft, tutorial_decisions(draft), path)
    validated = validate_bytes(artifacts["architecture.yaml"])
    trace = trace_architecture(validated, "eng", "svc_plc")
    assert trace.intervals and all(not i.reachable for i in trace.intervals)
    assert not validated.model.transport_edges and not validated.model.forwarding_edges
    assert not validated.model.rules
    assert not build_graph(validated.model, RESOURCE_LIMITS).edges


@pytest.mark.parametrize(
    "bad_path",
    [
        "../escape.csv",
        "/absolute.csv",
        "C:/source.csv",
        "C:source.csv",
        "\\\\host\\file",
        "https://example.invalid/a.csv",
        "file:///source.csv",
        "a/../b",
        "./a.csv",
        "a//b.csv",
        "a\\b.csv",
        "*.csv",
        "a?.csv",
        "a.csv:stream",
        "a/CON.txt",
        "a/nul",
        "a/lpt1.csv",
        "a./b",
        "a /b",
        "a.csv\x00",
        "a.csv\n",
        "a.csv\x85",
    ],
)
def test_portable_path_rejections(tmp_path: Path, bad_path: str) -> None:
    error_code(lambda: project_path(tmp_path, bad_path), "PROJECT_PATH")


@pytest.mark.parametrize(
    "case",
    [
        "duplicate",
        "unknown_key",
        "version",
        "bool_version",
        "adapter",
        "missing_source",
        "missing_profile",
        "cycle",
        "path_collision",
        "same_file",
        "bad_preference",
        "unknown_preference",
        "too_many",
        "no_sources",
        "unknown_source_key",
        "source_version",
    ],
)
def test_manifest_fail_closed(manifest: Path, case: str) -> None:
    mutations: dict[str, Any] = {
        "duplicate": lambda d: d["sources"].append(d["sources"][0]),
        "unknown_key": lambda d: d.update(include="other.json"),
        "version": lambda d: d.update(project_version=2),
        "bool_version": lambda d: d.update(project_version=True),
        "adapter": lambda d: d["sources"][0].update(adapter="json"),
        "missing_source": lambda d: d["sources"][0].update(path="missing.csv"),
        "missing_profile": lambda d: d["sources"][0].update(profile="missing.json"),
        "cycle": lambda d: d["sources"][0].update(path="project.json"),
        "path_collision": lambda d: d["sources"][0].update(profile="metadata.csv"),
        "same_file": lambda d: d["sources"][1].update(path="metadata.csv"),
        "bad_preference": lambda d: d.update(preferred_sources={"rules": "inventory"}),
        "unknown_preference": lambda d: d.update(preferred_sources={"asset.id": "other"}),
        "too_many": lambda d: d.update(sources=d["sources"] * 5),
        "no_sources": lambda d: d.update(sources=[]),
        "unknown_source_key": lambda d: d["sources"][0].update(credentials="secret"),
        "source_version": lambda d: d["sources"][0].update(subset_version=99),
    }
    change(manifest, mutations[case])
    with pytest.raises(ModelError):
        create_project(manifest)


@pytest.mark.parametrize(
    "attack", ["duplicate_json", "yaml_alias", "yaml_include", "deep", "oversize"]
)
def test_untrusted_manifest_parser(tmp_path: Path, attack: str) -> None:
    path = tmp_path / "project.json"
    data = {
        "duplicate_json": b'{"project_version":1,"project_version":1}',
        "yaml_alias": b"a: &x [1]\nb: *x\n",
        "yaml_include": b"a: !include other.yaml\n",
        "deep": b"[" * 50 + b"0" + b"]" * 50,
        "oversize": b" " * 65537,
    }[attack]
    path.write_bytes(data)
    with pytest.raises(ModelError):
        load_manifest(path)


@pytest.mark.parametrize("control", ["draft", "decision"])
def test_control_versions_are_separate_and_strict(manifest: Path, control: str) -> None:
    draft = create_project(manifest)
    record = draft if control == "draft" else project_template(draft)
    path = manifest.parent / "control.json"
    payload = record.model_dump(mode="json")
    payload["project_draft_version" if control == "draft" else "project_decisions_version"] = True
    write_json(path, payload)
    with pytest.raises(ModelError):
        load_project_record(path, ProjectDraft if control == "draft" else ProjectDecisions)


@pytest.mark.parametrize(
    "case",
    [
        "stale",
        "unnamed",
        "no_model",
        "no_rationale",
        "unresolved",
        "no_entity_rationale",
        "missing_member",
        "duplicate_member",
        "unknown_member",
        "mixed_family",
        "duplicate_id",
        "missing_conflict",
        "unresolved_conflict",
        "empty_conflict_rationale",
        "duplicate_conflict",
        "missing_ack",
        "wrong_ack_hash",
        "wrong_ack_set",
        "duplicate_ack",
        "wrong_field",
        "foreign_field_source",
        "contradictory_field",
        "rejected_correction",
        "invalid_native_id",
        "invalid_native_field",
        "wrong_reference_family",
        "rejected_reference",
        "unsupported_policy_field",
    ],
)
def test_adversarial_owner_decisions(manifest: Path, case: str) -> None:
    draft = create_project(manifest)
    payload = tutorial_decisions(draft).model_dump(mode="json")
    assets = [d for d in payload["entities"] if d["canonical_id"] in {"eng", "plc"}]
    entry = assets[0]
    changes: dict[str, Any] = {
        "stale": lambda: payload.update(draft_sha256="0" * 64),
        "unnamed": lambda: payload.update(reviewer=" "),
        "no_model": lambda: payload.update(model_confirmed=False),
        "no_rationale": lambda: payload.update(model_rationale=" "),
        "unresolved": lambda: entry.update(decision="UNRESOLVED"),
        "no_entity_rationale": lambda: entry.update(rationale=""),
        "missing_member": lambda: payload["entities"].remove(entry),
        "duplicate_member": lambda: payload["entities"].append(entry),
        "unknown_member": lambda: entry["members"].append("unknown::candidate"),
        "mixed_family": lambda: entry["members"].extend(
            next(d for d in payload["entities"] if d["canonical_id"] == "control")["members"]
        ),
        "duplicate_id": lambda: assets[1].update(canonical_id=assets[0]["canonical_id"]),
        "missing_conflict": lambda: payload.update(conflicts=[]),
        "unresolved_conflict": lambda: payload["conflicts"][0].update(resolved=False),
        "empty_conflict_rationale": lambda: payload["conflicts"][0].update(rationale=" "),
        "duplicate_conflict": lambda: payload["conflicts"].append(payload["conflicts"][0]),
        "missing_ack": lambda: payload.update(acknowledgments=[]),
        "wrong_ack_hash": lambda: payload["acknowledgments"][0].update(set_sha256="0" * 64),
        "wrong_ack_set": lambda: payload["acknowledgments"][0]["members"].pop(),
        "duplicate_ack": lambda: payload["acknowledgments"].append(payload["acknowledgments"][0]),
        "wrong_field": lambda: entry.update(corrections={"nonexistent": "x"}),
        "foreign_field_source": lambda: entry.update(field_sources={"role": "unknown::x"}),
        "contradictory_field": lambda: entry.update(field_sources={}),
        "rejected_correction": lambda: entry.update(
            decision="OWNER_REJECTED", corrections={"name": "x"}
        ),
        "invalid_native_id": lambda: entry.update(canonical_id="Not a native ID"),
        "invalid_native_field": lambda: entry.update(corrections={"kind": "firewall_icon"}),
        "wrong_reference_family": lambda: entry.update(
            references={"zone_id": assets[1]["members"][0]}, field_sources={}
        ),
        "rejected_reference": lambda: (
            next(d for d in payload["entities"] if d["canonical_id"] == "control").update(
                decision="OWNER_REJECTED"
            ),
            entry.update(
                references={
                    "zone_id": next(
                        d for d in payload["entities"] if d["canonical_id"] == "control"
                    )["members"][0]
                },
                field_sources={},
            ),
        ),
        "unsupported_policy_field": lambda: entry.update(corrections={"transport_edges": "allow"}),
    }
    changes[case]()
    with pytest.raises(ModelError):
        emit_project(draft, ProjectDecisions.model_validate(payload), manifest)


def test_safe_connector_ack_is_bounded_non_authoritative_and_disclosed(manifest: Path) -> None:
    draft = create_project(manifest)
    original = project_template(draft)
    updated = acknowledge_connectors(draft, original, "topology", "Owner", "Inventory-only review")
    assert updated.entities == original.entities
    assert not updated.model_confirmed
    assert len(updated.acknowledgments[0].members) == 5
    assert updated.acknowledgments[0].members == connector_sets(draft)["topology"]
    assert updated.draft_sha256 == project_digest(draft)
    for source, reviewer, rationale in [
        ("inventory", "Owner", "x"),
        ("missing", "Owner", "x"),
        ("topology", "", "x"),
        ("topology", "Owner", " "),
    ]:
        error_code(
            lambda s=source, r=reviewer, why=rationale: acknowledge_connectors(
                draft, original, s, r, why
            ),
            "PROJECT_ACK",
        )
    error_code(
        lambda: acknowledge_connectors(draft, updated, "topology", "Another", "x"),
        "PROJECT_REVIEWER",
    )


def test_hundreds_of_connectors_need_one_safe_ack(tmp_path: Path) -> None:
    path = synthetic_project(tmp_path, count=300, contradictory=False)
    draft = create_project(path)
    owner = tutorial_decisions(draft)
    assert len(owner.acknowledgments) == 1
    assert len(owner.acknowledgments[0].members) == 299
    validated = validate_bytes(emit_project(draft, owner, path)["architecture.yaml"])
    assert len(validated.model.assets) == 300
    assert not build_graph(validated.model, RESOURCE_LIMITS).edges


def test_human_report_escapes_markup_and_focuses_one_group(manifest: Path) -> None:
    change(
        manifest.parent / "inventory-profile.json",
        lambda d: d["tables"][0]["constants"].update(role="<script>*payload*</script>"),
    )
    # Profile cannot map and set role at the same time; change its native name constant instead.
    change(
        manifest.parent / "inventory-profile.json",
        lambda d: (d["tables"][0]["fields"].pop("role"), None),
    )
    draft = create_project(manifest)
    report = review_markdown(draft)
    assert b"<script>" not in report
    assert b"Blocking conflicts" in report and b"Source diagnostics" in report
    group = draft.conflicts[0]
    assert group.group_id in review_markdown(draft, group.group_id).decode().replace("\\", "")
    error_code(lambda: review_markdown(draft, "unknown"), "PROJECT_GROUP")


@pytest.mark.parametrize(
    "field,limit",
    [
        ("sources", 1),
        ("source_bytes", 1),
        ("candidates", 1),
        ("evidence_items", 1),
        ("connectors", 1),
        ("proposals", 1),
        ("conflicts", 0),
        ("draft_bytes", 1),
        ("control_events", 1),
        ("depth", 2),
    ],
)
def test_aggregate_limits_fail_closed(
    manifest: Path, monkeypatch: pytest.MonkeyPatch, field: str, limit: int
) -> None:
    monkeypatch.setattr(
        project, "PROJECT_LIMITS", replace(project.PROJECT_LIMITS, **{field: limit})
    )
    with pytest.raises(ModelError):
        create_project(manifest)


@pytest.mark.parametrize("field", ["sidecar_bytes", "decisions"])
def test_emission_budgets(manifest: Path, monkeypatch: pytest.MonkeyPatch, field: str) -> None:
    draft = create_project(manifest)
    owner = tutorial_decisions(draft)
    monkeypatch.setattr(
        project_review, "PROJECT_LIMITS", replace(project.PROJECT_LIMITS, **{field: 1})
    )
    with pytest.raises(ModelError):
        emit_project(draft, owner, manifest)


def test_output_overlap_and_no_overwrite(manifest: Path) -> None:
    for output in (manifest, manifest.parent, manifest.parent / "metadata.csv"):
        error_code(lambda p=output: protected_output(manifest, (p,)), "PROJECT_OUTPUT")
    draft = create_project(manifest)
    artifacts = emit_project(draft, tutorial_decisions(draft), manifest)
    output = manifest.parent / "accepted"
    write_new_bundle(output, artifacts)
    before = {p.name: p.read_bytes() for p in output.iterdir()}
    error_code(lambda: write_new_bundle(output, artifacts), "IMPORT_OUTPUT")
    assert {p.name: p.read_bytes() for p in output.iterdir()} == before


def test_cli_end_to_end_with_review_group_and_batch_ack(manifest: Path) -> None:
    runner = CliRunner()
    root = manifest.parent
    for operation in ("inspect", "preview"):
        result = runner.invoke(app, ["import", "project", operation, str(manifest)])
        assert result.exit_code == 0, result.output
    draft_path, decisions_path, report_path = [
        root / n for n in ("draft.json", "decisions.json", "review.md")
    ]

    def invoke(args: list[str], expected: int = 0) -> None:
        result = runner.invoke(app, ["import", "project", *args])
        assert result.exit_code == expected, result.output

    invoke(["map", str(manifest), "--output", str(draft_path)])
    invoke(
        [
            "review",
            str(draft_path),
            "--decisions",
            str(decisions_path),
            "--report",
            str(report_path),
        ]
    )
    draft = load_project_record(draft_path, ProjectDraft)
    assert not load_project_record(decisions_path, ProjectDecisions).model_confirmed
    invoke(["review", str(draft_path), "--group", draft.conflicts[0].group_id])
    invoke(
        [
            "acknowledge",
            str(draft_path),
            "--decisions",
            str(decisions_path),
            "--source",
            "topology",
            "--reviewer",
            "Owner",
            "--rationale",
            "Documentary only",
            "--output",
            str(root / "ack.json"),
        ]
    )
    emit_args = [
        "emit",
        str(draft_path),
        "--project",
        str(manifest),
        "--decisions",
        str(decisions_path),
        "--output",
        str(root / "accepted"),
    ]
    invoke(emit_args, 2)
    assert not (root / "accepted").exists()
    decisions_path.write_bytes(serialize(tutorial_decisions(draft)))
    invoke(emit_args)
    invoke(emit_args, 2)
    assert runner.invoke(app, ["validate", str(root / "accepted/architecture.yaml")]).exit_code == 0


@pytest.mark.parametrize("attack", ["xml", "json", "profile", "xlsx"])
def test_one_malformed_source_prevents_any_publication(manifest: Path, attack: str) -> None:
    bad = {
        "xml": ("topology.drawio", b'<!DOCTYPE x [<!ENTITY x "xx">]><mxfile>&x;</mxfile>'),
        "json": ("interfaces.json", b'{"interfaces":[],"interfaces":[]}'),
        "profile": ("topology-profile.json", b'{"profile_version":99}'),
        "xlsx": ("inventory.xlsx", b"PK invalid"),
    }[attack]
    (manifest.parent / bad[0]).write_bytes(bad[1])
    output = manifest.parent / "draft.json"
    result = CliRunner().invoke(
        app, ["import", "project", "map", str(manifest), "--output", str(output)]
    )
    assert result.exit_code == 2 and not output.exists()
    assert not list(manifest.parent.glob(".otarchguard-*"))


def test_envelope_rejects_deep_control() -> None:
    value: dict[str, object] = {}
    for _ in range(45):
        value = {"nested": value}
    with pytest.raises(ModelError):
        check_project_envelope(value, 100000)


def test_tsv_netbox_and_dangling_graph_evidence(tmp_path: Path) -> None:
    path = synthetic_project(tmp_path, formats=("csv", "graph"), contradictory=False)
    source = tmp_path / "metadata.csv"
    source.rename(tmp_path / "metadata.tsv")
    (tmp_path / "metadata.tsv").write_text(
        source.with_suffix(".tsv").read_text().replace(",", "\t"), encoding="utf-8"
    )
    change(path, lambda d: d["sources"][0].update(path="metadata.tsv", adapter="tsv"))
    graph = tmp_path / "topology.drawio"
    graph.write_text(graph.read_text().replace('target="fw"', 'target="missing"'), encoding="utf-8")
    draft = create_project(path)
    assert any(d.code == "GRAPH_DANGLING" for s in draft.sources for d in s.evidence.diagnostics)
    assert not validate_bytes(
        emit_project(draft, tutorial_decisions(draft), path)["architecture.yaml"]
    ).model.transport_edges
    # Reuse the accepted offline NetBox adapter; no network connection is made.
    fixture = Path(__file__).resolve().parents[1] / "examples/import-studio"
    for name in ("netbox-inventory.json", "netbox-profile.json", "netbox-context.yaml"):
        shutil.copyfile(fixture / name, tmp_path / name)
    write_json(
        path,
        {
            "project_version": 1,
            "project_id": "netbox-project",
            "sources": [
                {
                    "id": "netbox",
                    "path": "netbox-inventory.json",
                    "adapter": "netbox-offline-v1",
                    "profile": "netbox-profile.json",
                }
            ],
            "model_context": "netbox-context.yaml",
        },
    )
    netbox = create_project(path)
    assert netbox.sources[0].evidence.profile.adapter == "netbox-offline-v1"  # type: ignore[union-attr]


def test_duplicate_names_and_addresses_propose_without_merging(manifest: Path) -> None:
    change(
        manifest.parent / "interfaces.json",
        lambda d: d["interfaces"][1].update(ip=d["interfaces"][0]["ip"]),
    )
    change(
        manifest.parent / "inventory-profile.json",
        lambda d: (
            d["tables"][0]["fields"].pop("name"),
            d["tables"][0]["constants"].update(name="Shared label"),
        ),
    )
    draft = create_project(manifest)
    assert any(g.code == "REUSED_ADDRESS" for g in draft.conflicts)
    assert any(g.field == "name" and len(g.members) == 6 for g in draft.proposals)
    assert project_summary(draft)["owner_confirmed_declarations"] == 0
    template = project_template(draft)
    assert all(len(d.members) == 1 and d.decision == "UNRESOLVED" for d in template.entities)


@pytest.mark.parametrize("attack", ["unknown", "repeated", "mixed", "duplicate"])
def test_alias_integrity(manifest: Path, attack: str) -> None:
    draft = create_project(manifest)
    asset = next(p for p in draft.proposals if p.field == "id")
    members = list(asset.members)
    if attack == "unknown":
        members[0] = "inventory::unknown"
    elif attack == "repeated":
        members[0] = members[1]
    elif attack == "mixed":
        members[0] = next(k for k, (_, c) in catalog(draft.sources).items() if c.entity == "zone")
    aliases = [{"members": members, "rationale": "Explicit fixture alias configuration"}]
    if attack == "duplicate":
        aliases *= 2
    change(manifest, lambda d: d.update(aliases=aliases))
    error_code(lambda: create_project(manifest), "PROJECT_ALIAS")


def test_owner_can_keep_matching_names_separate_and_correct_identity(manifest: Path) -> None:
    draft = create_project(manifest)
    payload = tutorial_decisions(draft).model_dump(mode="json")
    asset = next(d for d in payload["entities"] if d["canonical_id"] == "plc")
    graphical = next(k for k in asset["members"] if k.startswith("topology::"))
    asset["members"].remove(graphical)
    payload["entities"].append(
        {
            "members": [graphical],
            "decision": "OWNER_CONFIRMED",
            "canonical_id": "another_plc",
            "corrections": {
                "zone_id": "control",
                "role": "Spare controller",
                "kind": "endpoint",
                "scope": "internal",
                "domain_classification": "iacs",
                "safety_classification": "unassessed",
                "criticality": "unspecified",
            },
            "rationale": "Fictional owner establishes a distinct device despite its matching name.",
        }
    )
    owner = ProjectDecisions.model_validate(payload)
    model = validate_bytes(emit_project(draft, owner, manifest)["architecture.yaml"]).model
    assert len(model.assets) == 7
    assert {a.id for a in model.assets} >= {"plc", "another_plc"}


def test_explicit_reference_rename_and_rejected_target(tmp_path: Path) -> None:
    path = synthetic_project(tmp_path, formats=("xlsx", "graph"))
    change(
        tmp_path / "inventory-profile.json",
        lambda d: d["tables"][0]["fields"]["zone_id"].update(reference={"table": "zones"}),
    )
    draft = create_project(path)
    payload = tutorial_decisions(draft).model_dump(mode="json")
    zone = next(d for d in payload["entities"] if d["canonical_id"] == "control")
    zone["canonical_id"] = "confirmed_control"
    error_code(
        lambda: emit_project(draft, ProjectDecisions.model_validate(payload), path),
        "PROJECT_REFERENCE",
    )
    for decision in payload["entities"]:
        if decision["canonical_id"] not in {"alternate", "confirmed_control"}:
            decision["references"] = {"zone_id": zone["members"][0]}
    model = validate_bytes(
        emit_project(draft, ProjectDecisions.model_validate(payload), path)["architecture.yaml"]
    ).model
    assert all(a.zone_id == "confirmed_control" for a in model.assets)
    zone["decision"] = "OWNER_REJECTED"
    error_code(
        lambda: emit_project(draft, ProjectDecisions.model_validate(payload), path),
        "PROJECT_REFERENCE",
    )


def test_exact_resolution_command_requires_explicit_members_and_resets_confirmation(
    manifest: Path,
) -> None:
    draft = create_project(manifest)
    owner = tutorial_decisions(draft)
    decision = next(d for d in owner.entities if d.canonical_id == "plc")
    changed = resolve_entity(draft, owner, decision, owner.reviewer)
    assert not changed.model_confirmed and len(changed.entities) == len(owner.entities)
    error_code(
        lambda: resolve_entity(
            draft,
            owner,
            decision.model_copy(update={"members": decision.members[:1]}),
            owner.reviewer,
        ),
        "PROJECT_IDENTITY",
    )
    root = manifest.parent
    (root / "draft.json").write_bytes(serialize(draft))
    (root / "decisions.json").write_bytes(serialize(project_template(draft)))
    result = CliRunner().invoke(
        app,
        [
            "import",
            "project",
            "resolve",
            str(root / "draft.json"),
            "--decisions",
            str(root / "decisions.json"),
            *[part for member in decision.members for part in ("--member", member)],
            "--canonical-id",
            "plc",
            "--reviewer",
            "Owner",
            "--rationale",
            "Explicitly reviewed fixture identity",
            "--output",
            str(root / "resolved.json"),
        ],
    )
    assert result.exit_code == 0, result.output
    resolved = load_project_record(root / "resolved.json", ProjectDecisions)
    assert not resolved.model_confirmed
    assert any(
        d.members == decision.members and d.decision == "OWNER_CONFIRMED" for d in resolved.entities
    )


def test_ancestor_links_and_hardlink_aliases_fail(
    manifest: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = Path.is_symlink
    with monkeypatch.context() as patch:
        patch.setattr(Path, "is_symlink", lambda p: p == manifest.parent or original(p))
        error_code(lambda: create_project(manifest), "PROJECT_PATH")
    import os

    original_file = manifest.parent / "metadata.csv"
    alias_file = manifest.parent / "alias.csv"
    try:
        os.link(original_file, alias_file)
    except PermissionError:
        # Some managed Windows sandboxes deny creating hard links. Exercise the
        # same file-ID collision independently without disabling the security check.
        shutil.copyfile(original_file, alias_file)
        original_stat = Path.stat

        def aliased_stat(p: Path, *, follow_symlinks: bool = True) -> os.stat_result:
            return original_stat(
                original_file if p == alias_file else p, follow_symlinks=follow_symlinks
            )

        monkeypatch.setattr(Path, "stat", aliased_stat)
    change(
        manifest,
        lambda d: d["sources"].append(
            {
                "id": "alias",
                "path": "alias.csv",
                "adapter": "csv",
                "profile": "metadata-profile.json",
            }
        ),
    )
    error_code(lambda: create_project(manifest), "PROJECT_PATH_COLLISION")


def test_duplicate_label_groups_are_bounded_sets_not_all_pairs(tmp_path: Path) -> None:
    path = synthetic_project(tmp_path, count=150, contradictory=False)
    change(
        tmp_path / "inventory-profile.json",
        lambda d: (
            d["tables"][0]["fields"].pop("name"),
            d["tables"][0]["constants"].update(name="Repeated"),
        ),
    )
    draft = create_project(path)
    group = next(g for g in draft.proposals if g.field == "name" and g.value == "Repeated")
    assert len(group.members) == 150
    assert len(draft.proposals) < 500


@pytest.mark.parametrize("field,value", [("id", "ENG"), ("id", "eNg")])
def test_case_collision_is_reported_never_merged(manifest: Path, field: str, value: str) -> None:
    text = (manifest.parent / "metadata.csv").read_text()
    (manifest.parent / "metadata.csv").write_text(
        text.replace("eng,Engineering", value + ",Engineering"), encoding="utf-8"
    )
    draft = create_project(manifest)
    assert any(g.code == "NORMALIZATION_COLLISION" for g in draft.conflicts)
    assert all(d.decision == "UNRESOLVED" for d in project_template(draft).entities)


def test_native_owner_context_retains_its_exact_analytical_identity(
    manifest: Path, minimal: dict[str, Any]
) -> None:
    write_json(manifest.parent / "context.json", minimal)
    draft = create_project(manifest)
    payload = tutorial_decisions(draft).model_dump(mode="json")
    for decision in payload["entities"]:
        decision.update(decision="EVIDENCE_ONLY", field_sources={}, corrections={}, references={})
    emitted = validate_bytes(
        emit_project(draft, ProjectDecisions.model_validate(payload), manifest)["architecture.yaml"]
    )
    original = validate_bytes(_declaration_yaml(minimal))
    assert emitted.sha256 == original.sha256
    assert build_graph(emitted.model, RESOURCE_LIMITS) == build_graph(
        original.model, RESOURCE_LIMITS
    )


def test_undirected_graph_edges_remain_evidence_only(manifest: Path) -> None:
    root = manifest.parent
    path = synthetic_project(root / "undirected", graph="graphml")
    graph_path = path.parent / "topology.graphml"
    graph_path.write_text(
        graph_path.read_text().replace('edgedefault="directed"', 'edgedefault="undirected"'),
        encoding="utf-8",
    )
    draft = create_project(path)
    graph = next(s.evidence.graph for s in draft.sources if s.evidence.graph)
    assert all(e.direction == "undirected" for e in graph.edges)
    model = validate_bytes(
        emit_project(draft, tutorial_decisions(draft), path)["architecture.yaml"]
    ).model
    assert not build_graph(model, RESOURCE_LIMITS).edges and not model.rules
