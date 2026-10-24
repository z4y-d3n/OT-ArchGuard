"""Independent oracles for assessment, correspondence and exact analytical deltas."""

import copy
import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from typer.testing import CliRunner

from otarchguard.api import validate_bytes
from otarchguard.architecture_comparison import compare_architecture_versions
from otarchguard.cli import app
from otarchguard.diagnostics import ModelError
from otarchguard.explorer_data import load_model
from otarchguard.explorer_html import audit_site
from otarchguard.ingestion.project import create_project
from otarchguard.ingestion.project_review import emit_project
from otarchguard.quality import ReviewQuery, assess_quality, canonical
from otarchguard.review_explorer import generate_review
from otarchguard.trace import trace_architecture
from tools.synthetic_projects import synthetic_project, tutorial_decisions


def write(path: Path, data: Any) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def native(path: Path, data: dict[str, Any]) -> Path:
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def profile(path: Path, model: Path, requirements: list[dict[str, Any]], **kw: Any) -> Path:
    return write(
        path,
        {
            "profile_version": 1,
            "model_sha256": load_model(model).sha256,
            "context": "Fictional owner review",
            "requirements": requirements,
            **kw,
        },
    )


def requirement(expectation: str, **kw: Any) -> dict[str, Any]:
    return {
        "id": "selected",
        "expectation": expectation,
        "rationale": "Explicit fictional owner expectation",
        **kw,
    }


@pytest.fixture
def model(tmp_path: Path, minimal: dict[str, Any]) -> Path:
    return native(tmp_path / "model.yaml", minimal)


@pytest.fixture
def evidence(tmp_path: Path) -> tuple[Path, Path]:
    manifest = synthetic_project(tmp_path / "project", count=4, contradictory=True)
    draft = create_project(manifest)
    artifacts = emit_project(draft, tutorial_decisions(draft), manifest)
    for name, data in artifacts.items():
        (tmp_path / name).write_bytes(data)
    return tmp_path / "architecture.yaml", tmp_path / "architecture.provenance.json"


def test_model_only_has_no_security_score_or_false_denial(model: Path) -> None:
    report = assess_quality(model)
    assert report["coverage"] == []
    assert report["analyses"] == []
    assert {f["state"] for f in report["findings"]} == {"SATISFIED", "NOT_ASSESSED"}
    assert canonical(report) == canonical(assess_quality(model))


@pytest.mark.parametrize(
    "expectation,field,satisfied",
    [
        ("DECLARED_VALUE", "zone_id", True),
        ("DECLARED_VALUE", "criticality", False),
        ("FIELD_PROVENANCE", "zone_id", False),
        ("ENTITY_PROVENANCE", None, False),
        ("OWNER_INFORMATION", "description", False),
        ("SOURCE_AVAILABLE", None, False),
    ],
)
def test_explicit_denominator_never_drops_missing_evidence(
    model: Path,
    tmp_path: Path,
    expectation: str,
    field: str | None,
    satisfied: bool,
) -> None:
    req = requirement(expectation)
    if field:
        req["field"] = field
    if expectation == "DECLARED_VALUE" and not satisfied:
        req["expected_value"] = "low"
    if expectation == "SOURCE_AVAILABLE":
        req["entity_ids"] = ["missing-document"]
    p = profile(tmp_path / "profile.json", model, [req])
    report = assess_quality(model, profile=p)
    coverage = report["coverage"][0]
    assert coverage["required"] > 0
    assert coverage["satisfied"] == (coverage["required"] if satisfied else 0)
    assert coverage["excluded"] == []


def test_external_owner_information_does_not_change_native_schema(
    model: Path, tmp_path: Path
) -> None:
    identity = load_model(model).model.assets[0].id
    before = model.read_bytes()
    p = profile(
        tmp_path / "profile.json",
        model,
        [requirement("OWNER_INFORMATION", field="description", entity_ids=[identity])],
        information=[
            {
                "entity_kind": "assets",
                "entity_id": identity,
                "field": "description",
                "value": "Reviewed fictional asset",
                "reviewer": "Owner",
                "rationale": "Owner supplied description",
            }
        ],
    )
    report = assess_quality(model, profile=p)
    assert report["coverage"][0]["satisfied"] == 1
    assert model.read_bytes() == before


@pytest.mark.parametrize(
    "mutation",
    [
        "stale",
        "version",
        "bool_version",
        "unknown",
        "unknown_field",
        "duplicate_requirements",
        "unknown_entity",
        "mixed_wildcard",
        "blank_rationale",
        "wrong_expected_type",
        "deep",
        "duplicate_key",
        "huge_text",
        "control_text",
        "bad_utf8",
        "too_many_requirements",
    ],
)
def test_profiles_fail_closed(model: Path, tmp_path: Path, mutation: str) -> None:
    p = profile(tmp_path / "p.json", model, [requirement("DECLARED_VALUE", field="zone_id")])
    data = json.loads(p.read_text())
    if mutation == "stale":
        data["model_sha256"] = "0" * 64
    elif mutation == "version":
        data["profile_version"] = 2
    elif mutation == "bool_version":
        data["profile_version"] = True
    elif mutation == "unknown":
        data["extra"] = "bad"
    elif mutation == "unknown_field":
        data["requirements"][0]["field"] = "not_native"
    elif mutation == "duplicate_requirements":
        data["requirements"] *= 2
    elif mutation == "unknown_entity":
        data["requirements"][0]["entity_ids"] = ["absent"]
    elif mutation == "mixed_wildcard":
        data["requirements"][0]["entity_ids"] = ["*", "absent"]
    elif mutation == "blank_rationale":
        data["requirements"][0]["rationale"] = " "
    elif mutation == "wrong_expected_type":
        data["requirements"][0]["expected_value"] = 3
    elif mutation == "huge_text":
        data["context"] = "x" * 5000
    elif mutation == "control_text":
        data["context"] = "bad\x00"
    elif mutation == "too_many_requirements":
        data["requirements"] *= 1001
    write(p, data)
    if mutation == "deep":
        p.write_text("[" * 17 + "0" + "]" * 17)
    elif mutation == "duplicate_key":
        p.write_text('{"profile_version":1,"profile_version":1}')
    elif mutation == "bad_utf8":
        p.write_bytes(b"\xff")
    with pytest.raises(ModelError):
        assess_quality(model, profile=p)


def test_profiles_are_identity_bound_and_semantic_changes_invalidate(
    model: Path, tmp_path: Path
) -> None:
    p = profile(tmp_path / "p.json", model, [requirement("DECLARED_VALUE", field="zone_id")])
    a = assess_quality(model, profile=p)
    data = json.loads(p.read_text())
    data["requirements"][0]["expected_value"] = "absent-zone"
    write(p, data)
    b = assess_quality(model, profile=p)
    assert a["assessment_sha256"] != b["assessment_sha256"]
    assert a["findings"][0]["model_sha256"] == b["findings"][0]["model_sha256"]
    assert b["coverage"][0]["satisfied"] == 0


def test_verified_evidence_conflicts_remain_resolved(
    evidence: tuple[Path, Path], tmp_path: Path
) -> None:
    model, sidecar = evidence
    p = profile(tmp_path / "p.json", model, [requirement("ENTITY_PROVENANCE")])
    report = assess_quality(model, provenance=sidecar, profile=p)
    conflicts = [f for f in report["findings"] if f["rule_id"] == "retained-conflict"]
    assert conflicts and all(f["state"] == "SATISFIED" for f in conflicts)
    assert all(f["source_references"] for f in conflicts)
    assert report["coverage"][0]["satisfied"] > 0
    assert report["provenance_sha256"]


@pytest.mark.parametrize("mutation", ["hash", "decision", "catalog", "identity_index", "version"])
def test_sidecars_are_reverified(evidence: tuple[Path, Path], mutation: str) -> None:
    model, sidecar = evidence
    value = json.loads(sidecar.read_text())
    if mutation == "hash":
        value["model_sha256"] = "0" * 64
    elif mutation == "decision":
        value["decisions"]["model_confirmed"] = False
    elif mutation == "catalog":
        value["catalog"]["sources"][0]["evidence"]["source"]["sha256"] = "0" * 64
    elif mutation == "identity_index":
        value["identity_index"] = []
    elif mutation == "version":
        value["project_provenance_version"] = 99
    write(sidecar, value)
    with pytest.raises(ModelError):
        assess_quality(model, provenance=sidecar)
    with pytest.raises(ModelError):
        compare_architecture_versions(model, model, baseline_provenance=sidecar)


@pytest.mark.parametrize(
    "collection,field,value",
    [
        ("assets", "name", "New name"),
        ("assets", "criticality", "high"),
        ("assets", "role", "New role"),
        ("zones", "purpose", "New purpose"),
        ("interfaces", "ipv4", "192.0.2.100/24"),
        ("rules", "effect", "deny"),
    ],
)
def test_native_differences_invert_exactly(
    model: Path, minimal: dict[str, Any], tmp_path: Path, collection: str, field: str, value: str
) -> None:
    changed = copy.deepcopy(minimal)
    changed[collection][0][field] = value
    other = native(tmp_path / "other.yaml", changed)
    forward = compare_architecture_versions(model, other)
    reverse = compare_architecture_versions(other, model)
    a = next(c for c in forward["changes"] if c["entity_kind"] == collection)
    b = next(c for c in reverse["changes"] if c["entity_kind"] == collection)
    assert a["baseline"] == b["proposed"] and a["proposed"] == b["baseline"]
    assert a["fields"][0]["field"] == field
    assert forward["analytical_status"] == "NOT_EVALUATED"
    assert forward["analytical_results"] == []


def test_removed_transport_is_structural_until_query_evaluated(
    model: Path, minimal: dict[str, Any], tmp_path: Path
) -> None:
    changed = copy.deepcopy(minimal)
    changed["transport_edges"] = []
    changed["rules"] = []
    changed["intents"] = []
    other = native(tmp_path / "other.yaml", changed)
    report = compare_architecture_versions(model, other)
    assert any(
        c["action"] == "REMOVED" and c["entity_kind"] == "transport_edges"
        for c in report["changes"]
    )
    assert report["analytical_status"] == "NOT_EVALUATED"


@pytest.mark.parametrize("protocol", ["tcp", "udp"])
@pytest.mark.parametrize("port", [1, 53, 443, 502, 65535])
def test_exact_delta_matches_independent_native_oracle(
    minimal: dict[str, Any], tmp_path: Path, protocol: str, port: int
) -> None:
    before = copy.deepcopy(minimal)
    before["intents"] = []
    before["scenarios"] = []
    for service in before["services"]:
        service["protocol"] = protocol
        service["destination_ports"] = [{"start": port, "end": port}]
    for rule in before["rules"]:
        rule["protocol"] = protocol
        rule["destination_ports"] = [{"start": port, "end": port}]
    after = copy.deepcopy(before)
    after["rules"] = []
    a, b = native(tmp_path / "a.yaml", before), native(tmp_path / "b.yaml", after)
    source = before["assets"][0]["id"]
    service = before["services"][0]["id"]
    q = ReviewQuery(source_asset_id=source, service_id=service)
    report = compare_architecture_versions(a, b, queries=(q,))
    delta = report["analytical_results"][0]
    oracle_a = trace_architecture(validate_bytes(a.read_bytes()), source, service)
    oracle_b = trace_architecture(validate_bytes(b.read_bytes()), source, service)
    assert delta["baseline"]["model_sha256"] == oracle_a.model_sha256
    assert delta["proposed"]["model_sha256"] == oracle_b.model_sha256
    assert delta["intervals"] == [
        {
            "start": port,
            "end": port,
            "protocol": protocol,
            "classification": "NO_LONGER_ALLOWED_FOR_EVALUATED_QUERY",
            "baseline_reachable": True,
            "proposed_reachable": False,
            "reason": "Derived from both exact native trace intervals; witnesses and frontier "
            "diagnostics retained.",
        }
    ]
    inverted = compare_architecture_versions(b, a, queries=(q,))
    assert (
        inverted["analytical_results"][0]["intervals"][0]["classification"]
        == "NEWLY_ALLOWED_FOR_EVALUATED_QUERY"
    )


def test_changed_service_binding_is_not_comparable(
    model: Path, minimal: dict[str, Any], tmp_path: Path
) -> None:
    source = minimal["assets"][0]["id"]
    service = minimal["services"][0]["id"]
    changed = copy.deepcopy(minimal)
    changed["services"][0]["destination_ports"] = [{"start": 503, "end": 503}]
    changed["intents"] = []
    other = native(tmp_path / "other.yaml", changed)
    result = compare_architecture_versions(
        model, other, queries=(ReviewQuery(source_asset_id=source, service_id=service),)
    )
    assert result["analytical_results"][0]["classification"] == "NOT_COMPARABLE"
    assert result["analytical_results"][0]["intervals"] == []


def test_explicit_rename_is_separate_from_unmatched_add_remove(
    model: Path, minimal: dict[str, Any], tmp_path: Path
) -> None:
    before_id = minimal["assets"][0]["id"]
    changed = json.loads(json.dumps(minimal).replace('"' + before_id + '"', '"renamed"'))
    other = native(tmp_path / "other.yaml", changed)
    report = compare_architecture_versions(model, other)
    assert {c["action"] for c in report["changes"] if c["entity_kind"] == "assets"} == {
        "ADDED",
        "REMOVED",
    }
    mapping = write(
        tmp_path / "mapping.json",
        {
            "mapping_version": 1,
            "baseline_model_sha256": load_model(model).sha256,
            "proposed_model_sha256": load_model(other).sha256,
            "correspondences": [
                {
                    "entity_kind": "assets",
                    "baseline_id": before_id,
                    "proposed_id": "renamed",
                    "rationale": "Owner establishes continuity",
                }
            ],
        },
    )
    mapped = compare_architecture_versions(model, other, mapping=mapping)
    changes = [c for c in mapped["changes"] if c["entity_kind"] == "assets"]
    assert len(changes) == 1 and changes[0]["action"] == "MODIFIED"
    assert changes[0]["correspondence"]["policy"] == "explicit_owner_mapping"


def test_explicit_identifier_reuse_produces_add_remove(model: Path, tmp_path: Path) -> None:
    identity = load_model(model).model.assets[0].id
    mapping = write(
        tmp_path / "m.json",
        {
            "mapping_version": 1,
            "baseline_model_sha256": load_model(model).sha256,
            "proposed_model_sha256": load_model(model).sha256,
            "reused_identifiers": [
                {
                    "entity_kind": "assets",
                    "id": identity,
                    "rationale": "Owner declares distinct replacement",
                }
            ],
        },
    )
    report = compare_architecture_versions(model, model, mapping=mapping)
    assert {c["action"] for c in report["changes"]} == {"ADDED", "REMOVED"}


def test_quality_scope_change_cannot_resolve_findings(model: Path, tmp_path: Path) -> None:
    a = profile(tmp_path / "a.json", model, [requirement("ENTITY_PROVENANCE")])
    b = profile(tmp_path / "b.json", model, [])
    report = compare_architecture_versions(model, model, baseline_profile=a, proposed_profile=b)
    assert {c["classification"] for c in report["quality_changes"]} == {"NOT_COMPARABLE"}


def test_documentary_only_connector_change_does_not_invent_native_change(
    evidence: tuple[Path, Path], tmp_path: Path
) -> None:
    model, old_sidecar = evidence
    manifest = tmp_path / "project/project.json"
    # Locate the generated manifest without depending on a private basename.
    manifest = next(
        p for p in (tmp_path / "project").glob("*.json") if '"project_version"' in p.read_text()
    )
    graph = tmp_path / "project/topology.drawio"
    graph.write_text(
        graph.read_text().replace(
            "</root>", '<mxCell id="new_arrow" edge="1" parent="1" source="n0" target="n1"/></root>'
        )
    )
    draft = create_project(manifest)
    artifacts = emit_project(draft, tutorial_decisions(draft), manifest)
    other_model, other_sidecar = tmp_path / "new.yaml", tmp_path / "new.json"
    other_model.write_bytes(artifacts["architecture.yaml"])
    other_sidecar.write_bytes(artifacts["architecture.provenance.json"])
    assert load_model(model).sha256 == load_model(other_model).sha256
    report = compare_architecture_versions(
        model, other_model, baseline_provenance=old_sidecar, proposed_provenance=other_sidecar
    )
    assert any(
        c["entity_kind"] == "documentary_connectors" and c["action"] == "ADDED"
        for c in report["changes"]
    )
    assert not any(c["layer"] == "NATIVE" for c in report["changes"])
    assert report["analytical_status"] == "NOT_EVALUATED"


@pytest.mark.parametrize("comparison", [False, True])
def test_compact_site_is_offline_inert_and_byte_identical(
    model: Path, tmp_path: Path, comparison: bool
) -> None:
    attack = '<svg onload="alert(1)"><script>alert(2)</script>javascript:evil'
    p = profile(
        tmp_path / "p.json",
        model,
        [requirement("OWNER_INFORMATION", field="description", rationale=attack)],
    )
    kw: dict[str, Any] = {"profile": p}
    if comparison:
        kw.update(proposed=model, proposed_profile=p)
    before = model.read_bytes()
    a = generate_review(model, tmp_path / "site", **kw)
    generate_review(model, tmp_path / "repeat", **kw)
    assert a["site"]["broken_links"] == 0
    assert audit_site(tmp_path / "site")["broken_links"] == 0
    assert {p.name: p.read_bytes() for p in (tmp_path / "site").iterdir()} == {
        p.name: p.read_bytes() for p in (tmp_path / "repeat").iterdir()
    }
    html = "".join(p.read_text() for p in (tmp_path / "site").glob("*.html"))
    assert "<script>" not in html and "<svg onload" not in html
    assert "Skip to main content" in html and 'scope="col"' in html
    assert model.read_bytes() == before
    with pytest.raises(ModelError):
        generate_review(model, tmp_path / "site", **kw)


@pytest.mark.parametrize("command", ["quality", "compare-architecture"])
def test_additive_cli_has_reliable_errors(model: Path, tmp_path: Path, command: str) -> None:
    args = [command, str(model)]
    if command == "compare-architecture":
        args.append(str(model))
    args += ["--output", str(tmp_path / "site")]
    result = CliRunner().invoke(app, args)
    assert result.exit_code == 0, result.output
    assert (tmp_path / "site/review.json").is_file()
    assert CliRunner().invoke(app, args).exit_code == 2
    bad = [*args[:-1], str(tmp_path / "bad"), "--trace", "invalid"]
    assert CliRunner().invoke(app, bad).exit_code == 2
    assert not (tmp_path / "bad").exists()


def test_quality_cli_does_not_require_a_site(model: Path) -> None:
    result = CliRunner().invoke(app, ["quality", str(model)])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["quality_version"] == 1


@pytest.mark.parametrize("command", ["quality", "compare-architecture"])
def test_option_diagnostics_name_the_actual_command(model: Path, command: str) -> None:
    result = CliRunner().invoke(app, [command, str(model), "--unknown-option"])
    assert result.exit_code == 2
    assert "Invalid " + command + " options" in result.stderr


def test_empty_collection_still_rejects_unknown_native_field(
    minimal: dict[str, Any],
    tmp_path: Path,
) -> None:
    for collection in (
        "interfaces",
        "services",
        "rules",
        "transport_edges",
        "intents",
        "scenarios",
    ):
        minimal[collection] = []
    model = native(tmp_path / "empty.yaml", minimal)
    p = profile(
        tmp_path / "p.json",
        model,
        [requirement("DECLARED_VALUE", entity_kind="interfaces", field="invented")],
    )
    with pytest.raises(ModelError):
        assess_quality(model, profile=p)
    profile(p, model, [requirement("DECLARED_VALUE", entity_kind="interfaces", field="ipv4")])
    report = assess_quality(model, profile=p)
    assert report["coverage"][0]["required"] == 0
    assert report["coverage"][0]["state"] == "NOT_APPLICABLE"


@pytest.mark.parametrize(
    "mutation",
    [
        "stale",
        "version",
        "boolean",
        "missing",
        "duplicate_source",
        "duplicate_target",
        "ambiguous_swap",
        "blank",
        "reused_missing",
        "reused_duplicate",
        "reused_and_mapped",
    ],
)
def test_invalid_identity_mappings_fail_closed(model: Path, tmp_path: Path, mutation: str) -> None:
    ids = [a.id for a in load_model(model).model.assets]
    sha = load_model(model).sha256
    pair = {
        "entity_kind": "assets",
        "baseline_id": ids[0],
        "proposed_id": ids[0],
        "rationale": "Owner",
    }
    reuse = {"entity_kind": "assets", "id": ids[0], "rationale": "Distinct replacement"}
    data: dict[str, Any] = {
        "mapping_version": 1,
        "baseline_model_sha256": sha,
        "proposed_model_sha256": sha,
        "correspondences": [pair],
    }
    if mutation == "stale":
        data["baseline_model_sha256"] = "0" * 64
    elif mutation == "version":
        data["mapping_version"] = 2
    elif mutation == "boolean":
        data["mapping_version"] = True
    elif mutation == "missing":
        pair["baseline_id"] = "missing"
    elif mutation == "duplicate_source":
        data["correspondences"].append(dict(pair))
    elif mutation == "duplicate_target":
        data["correspondences"].append({**pair, "baseline_id": ids[1]})
    elif mutation == "ambiguous_swap":
        pair["proposed_id"] = ids[1]
    elif mutation == "blank":
        pair["rationale"] = " "
    elif mutation == "reused_missing":
        data.update(correspondences=[], reused_identifiers=[{**reuse, "id": "missing"}])
    elif mutation == "reused_duplicate":
        data.update(correspondences=[], reused_identifiers=[reuse, reuse])
    elif mutation == "reused_and_mapped":
        data["reused_identifiers"] = [reuse]
    mapping = write(tmp_path / "map.json", data)
    with pytest.raises(ModelError):
        compare_architecture_versions(model, model, mapping=mapping)


def test_reused_destination_cannot_claim_comparable_connectivity(
    model: Path, tmp_path: Path
) -> None:
    snapshot = load_model(model)
    mapping = write(
        tmp_path / "mapping.json",
        {
            "mapping_version": 1,
            "baseline_model_sha256": snapshot.sha256,
            "proposed_model_sha256": snapshot.sha256,
            "reused_identifiers": [
                {"entity_kind": "assets", "id": "plc", "rationale": "Replacement"}
            ],
        },
    )
    report = compare_architecture_versions(
        model,
        model,
        mapping=mapping,
        queries=(ReviewQuery(source_asset_id="eng", service_id="svc_plc"),),
    )
    assert report["analytical_results"][0]["classification"] == "NOT_COMPARABLE"


def test_interval_partition_changes_preserve_exact_port_semantics(
    minimal: dict[str, Any], tmp_path: Path
) -> None:
    before = copy.deepcopy(minimal)
    before["intents"] = []
    before["services"][0]["destination_ports"] = [{"start": 500, "end": 510}]
    before["rules"][0]["destination_ports"] = [{"start": 500, "end": 505}]
    after = copy.deepcopy(before)
    after["rules"][0]["destination_ports"] = [{"start": 504, "end": 510}]
    a, b = native(tmp_path / "a.yaml", before), native(tmp_path / "b.yaml", after)
    result = compare_architecture_versions(
        a, b, queries=(ReviewQuery(source_asset_id="eng", service_id="svc_plc"),)
    )
    intervals = result["analytical_results"][0]["intervals"]
    for port in range(500, 511):
        interval = next(i for i in intervals if i["start"] <= port <= i["end"])
        assert interval["baseline_reachable"] == (port <= 505)
        assert interval["proposed_reachable"] == (port >= 504)


@pytest.mark.parametrize("stage", ["audit", "rename"])
def test_failed_publication_leaves_no_partial_output(
    model: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stage: str
) -> None:
    def denied(*args: object, **kw: object) -> None:
        raise PermissionError("Injected publication failure")

    monkeypatch.setattr(
        "otarchguard.explorer_html.audit_site"
        if stage == "audit"
        else "otarchguard.review_explorer.os.rename",
        denied,
    )
    with pytest.raises(ModelError):
        generate_review(model, tmp_path / "site")
    assert not (tmp_path / "site").exists()
    assert not list(tmp_path.glob(".otarchguard-review-*"))


def test_selected_profile_constants_do_not_establish_documentary_support(
    evidence: tuple[Path, Path], tmp_path: Path
) -> None:
    model, sidecar = evidence
    p = profile(tmp_path / "profile.json", model, [requirement("FIELD_PROVENANCE", field="scope")])
    result = assess_quality(model, provenance=sidecar, profile=p)
    assert result["coverage"][0]["satisfied"] == 0


@pytest.mark.parametrize("kind", ["queries", "requirements"])
def test_resource_limits_fail_before_unbounded_output(
    model: Path, tmp_path: Path, kind: str
) -> None:
    if kind == "queries":
        with pytest.raises(ModelError):
            compare_architecture_versions(
                model,
                model,
                queries=(ReviewQuery(source_asset_id="eng", service_id="svc_plc"),) * 17,
            )
    else:
        p = profile(
            tmp_path / "p.json", model, [requirement("DECLARED_VALUE", field="zone_id")] * 1001
        )
        with pytest.raises(ModelError):
            assess_quality(model, profile=p)


def test_swapped_model_sidecar_fails_in_both_directions(
    evidence: tuple[Path, Path], tmp_path: Path
) -> None:
    model, sidecar = evidence
    other = yaml.safe_load(model.read_text())
    other["revision"] = "Another revision"
    changed = native(tmp_path / "changed.yaml", other)
    with pytest.raises(ModelError):
        compare_architecture_versions(model, changed, proposed_provenance=sidecar)
    with pytest.raises(ModelError):
        compare_architecture_versions(changed, model, baseline_provenance=sidecar)


def test_normalized_model_and_json_key_order_preserve_review_bytes(
    model: Path, tmp_path: Path
) -> None:
    reordered = native(
        tmp_path / "reordered.yaml", dict(reversed(list(yaml.safe_load(model.read_text()).items())))
    )
    p = profile(tmp_path / "a.json", model, [requirement("DECLARED_VALUE", field="zone_id")])
    q = write(tmp_path / "b.json", dict(reversed(list(json.loads(p.read_text()).items()))))
    assert canonical(assess_quality(model, profile=p)) == canonical(
        assess_quality(reordered, profile=q)
    )
