"""Graphical extraction, review, numeric fidelity and analytical non-inference."""

import json
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
import yaml
from typer.testing import CliRunner

from otarchguard.api import validate_bytes
from otarchguard.cli import app
from otarchguard.contract import RESOURCE_LIMITS
from otarchguard.diagnostics import ModelError
from otarchguard.graph import build_graph
from otarchguard.ingestion.graphical import inspect_graph, read_graph
from otarchguard.ingestion.numbers import NumericToken
from otarchguard.ingestion.records import GraphProfile, ImportDraft, OwnerDecisions
from otarchguard.ingestion.workflow import (
    create_draft,
    emit_artifacts,
    load_profile,
    load_record,
    review_summary,
    review_template,
    serialize,
)
from otarchguard.trace import trace_architecture
from tools.synthetic_graphs import drawio_xml, graph_profile, graphml_xml


def source(tmp_path: Path, adapter: str, text: str | None = None) -> Path:
    path = tmp_path / ("topology." + adapter)
    path.write_text(
        text or (drawio_xml() if adapter == "drawio" else graphml_xml()), encoding="utf-8"
    )
    return path


def owner(draft: ImportDraft) -> OwnerDecisions:
    data = review_template(draft).model_dump(mode="json")
    context = yaml.safe_load(
        (
            Path(__file__).resolve().parents[1] / "examples/import-studio/model-context.yaml"
        ).read_text()
    )
    data.update(
        reviewer="Synthetic owner",
        model_confirmed=True,
        model_rationale="Reviewed inventory and evidence only",
        model=context,
    )
    for resolution, candidate in zip(data["resolutions"], draft.candidates, strict=True):
        resolution.update(
            decision="OWNER_REJECTED" if candidate.entity == "connection" else "OWNER_CONFIRMED",
            rationale="Reviewed synthetic evidence",
        )
    return OwnerDecisions.model_validate(data)


@pytest.mark.parametrize("adapter", ["graphml", "drawio"])
def test_full_workflow_and_native_invariant(tmp_path: Path, adapter: str) -> None:
    path = source(tmp_path, adapter)
    draft = create_draft(path, graph_profile(adapter, edges=True))
    assert draft.import_version == 4 and len(draft.candidates) == 11
    assert draft.graph is not None and len(draft.graph.edges) == 5
    assert all(e.relationship == "diagram_evidence_only" for e in draft.graph.edges)
    assert all(c.state == "UNRESOLVED" for c in draft.candidates)
    assert not review_template(draft).model_confirmed
    with pytest.raises(ModelError):
        emit_artifacts(draft, review_template(draft), path)
    artifacts = emit_artifacts(draft, owner(draft), path)
    assert artifacts == emit_artifacts(draft, owner(draft), path)
    validated = validate_bytes(artifacts["architecture.yaml"])
    assert len(validated.model.assets) == 6 and len(validated.model.zones) == 1
    for field in ("transport_edges", "forwarding_edges", "rules", "services", "interfaces"):
        assert not getattr(validated.model, field)
    graph = build_graph(validated.model, RESOURCE_LIMITS)
    assert not graph.edges and all(not v for v in graph.origins.values())
    sidecar = json.loads(artifacts["architecture.provenance.json"])
    assert sidecar["graph"]["edges"][0]["relationship"] == "diagram_evidence_only"
    assert sidecar["model_sha256"] == validated.sha256
    if adapter == "drawio":
        assert sum(n.kind == "group" for n in draft.graph.nodes) == 2
        assert {n.parent for n in draft.graph.nodes if n.kind == "node"} == {"area_a", "area_b"}
    bad = owner(draft).model_dump(mode="json")
    for r in bad["resolutions"]:
        r["decision"] = "OWNER_CONFIRMED"
    with pytest.raises(ModelError) as error:
        emit_artifacts(draft, OwnerDecisions.model_validate(bad), path)
    assert error.value.diagnostics[0].code == "IMPORT_RELATIONSHIP"


@pytest.mark.parametrize("compressed", [False, True])
def test_multipage_scope_and_compression_equivalence(tmp_path: Path, compressed: bool) -> None:
    path = source(tmp_path, "drawio", drawio_xml(compressed=compressed, pages=2))
    draft = create_draft(path, graph_profile("drawio", pages=2))
    assert len(draft.candidates) == len({c.candidate_id for c in draft.candidates}) == 12
    assert not any(c.code == "DUPLICATE_IDENTITY" for c in draft.conflicts)
    assert {c.location.collection for c in draft.candidates if hasattr(c, "location")} == {
        "page1",
        "page2",
    }
    normal = source(tmp_path, "drawio", drawio_xml(pages=2))
    other = create_draft(normal, graph_profile("drawio", pages=2))
    assert [c.candidate_id for c in draft.candidates] == [c.candidate_id for c in other.candidates]
    assert draft.graph is not None and other.graph is not None
    assert draft.graph.nodes == other.graph.nodes and draft.graph.edges == other.graph.edges
    if compressed:
        assert draft.source.sha256 != other.source.sha256


@pytest.mark.parametrize("change", ["order", "attributes", "geometry", "page_order"])
def test_drawio_metamorphic_identity(tmp_path: Path, change: str) -> None:
    path = source(tmp_path, "drawio", drawio_xml(pages=2))
    profile = graph_profile("drawio", pages=2)
    before = create_draft(path, profile)
    root = ET.fromstring(path.read_text())
    if change == "page_order":
        root[:] = list(reversed(root))
    for page in root:
        cells = page[0][0]
        if change == "order":
            cells[:] = list(reversed(cells))
        for element in page.iter():
            if change == "attributes":
                element.attrib = dict(reversed(list(element.attrib.items())))
            if change == "geometry" and element.tag == "mxGeometry":
                element.set("x", "9999")
    path.write_text(ET.tostring(root, encoding="unicode"))
    after = create_draft(path, profile)
    assert [c.candidate_id for c in before.candidates] == [c.candidate_id for c in after.candidates]
    assert before.source.sha256 != after.source.sha256
    with pytest.raises(ModelError) as error:
        emit_artifacts(before, owner(before), path)
    assert error.value.diagnostics[0].code == "IMPORT_SOURCE_CHANGED"


def test_graphml_direction_and_order(tmp_path: Path) -> None:
    path = source(tmp_path, "graphml", graphml_xml(directed=False))
    doc = read_graph(path, "graphml")
    assert [(e.element_id, e.direction, e.direction_origin) for e in doc.edges] == [
        ("e0", "directed", "edge_override"),
        *[(f"e{i}", "undirected", "graph_default") for i in range(1, 5)],
    ]
    before = create_draft(path, graph_profile("graphml"))
    root = ET.fromstring(path.read_text())
    graph = root[-1]
    graph[:] = list(reversed(graph))
    path.write_text(ET.tostring(root, encoding="unicode"))
    after = create_draft(path, graph_profile("graphml"))
    assert before.candidates == after.candidates
    assert before.graph is not None and after.graph is not None
    assert before.graph.edges == after.graph.edges


@pytest.mark.parametrize(
    "token",
    [
        "-0",
        "0.1",
        "0.10000000000000001",
        "1.00",
        "1e-400",
        "1e309",
        "1e-9999",
        "9007199254740993.0",
    ],
)
def test_exact_graphml_numeric_defaults(tmp_path: Path, token: str) -> None:
    path = source(tmp_path, "graphml", graphml_xml().replace("0.10000000000000001", token))
    profile_data = graph_profile("graphml").model_dump(mode="json")
    profile_data["tables"][0]["fields"]["role"] = {
        "path": "/attributes/load",
        "value_type": "number",
    }
    draft = create_draft(path, GraphProfile.model_validate(profile_data))
    for c in draft.candidates:
        value = next(f for f in c.fields if f.field == "role")
        assert isinstance(value.raw_value, NumericToken) and value.raw_value.numeric_token == token
        assert value.normalized_value == token
    emitted = validate_bytes(emit_artifacts(draft, owner(draft), path)["architecture.yaml"])
    assert {a.role for a in emitted.model.assets} == {token}
    file = tmp_path / "draft.json"
    file.write_bytes(serialize(draft))
    assert serialize(load_record(file, ImportDraft)) == serialize(draft)


@pytest.mark.parametrize("adapter", ["drawio", "graphml"])
def test_cli_roundtrip_no_clobber_and_stale(tmp_path: Path, adapter: str) -> None:
    path = source(tmp_path, adapter)
    profile_file = tmp_path / "profile.json"
    profile_file.write_bytes(serialize(graph_profile(adapter)))
    assert load_profile(profile_file) == graph_profile(adapter)
    runner = CliRunner()
    draft_file, decisions = tmp_path / "draft.json", tmp_path / "decisions.json"
    commands = [
        ["inspect", str(path)],
        ["preview", str(path), "--profile", str(profile_file)],
        ["map", str(path), "--profile", str(profile_file), "--output", str(draft_file)],
        ["review", str(draft_file), "--decisions", str(decisions)],
    ]
    for command in commands:
        result = runner.invoke(app, ["import", *command])
        assert result.exit_code == 0, result.output
    draft = load_record(draft_file, ImportDraft)
    assert review_summary(draft)["graph"]
    decisions.write_bytes(serialize(owner(draft)))
    args = [
        "import",
        "emit",
        str(draft_file),
        "--source",
        str(path),
        "--decisions",
        str(decisions),
        "--output",
        str(tmp_path / "accepted"),
    ]
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    assert runner.invoke(app, args).exit_code == 2
    path.write_text(path.read_text() + "\n")
    args[-1] = str(tmp_path / "stale")
    assert runner.invoke(app, args).exit_code == 2
    assert not (tmp_path / "stale").exists()


def test_dangling_text_and_links_are_inert(tmp_path: Path) -> None:
    text = (
        drawio_xml()
        .replace('target="fw"', 'target="missing"')
        .replace(
            'label="PLC"', 'label="&lt;script&gt;bad()&lt;/script&gt;" link="javascript:secret()"'
        )
    )
    path = source(tmp_path, "drawio", text)
    doc = read_graph(path, "drawio")
    assert doc.edges[0].destination == "missing" and doc.edges[0].unresolved == ("destination",)
    assert {d.code for d in doc.diagnostics} >= {"GRAPH_DANGLING", "GRAPH_EXTERNAL", "GRAPH_MARKUP"}
    draft = create_draft(path, graph_profile("drawio"))
    assert b"javascript:secret" not in serialize(draft)
    assert b"<script>bad()" in serialize(draft)
    assert len(inspect_graph(path, "drawio")["pages"]) == 1  # type: ignore[arg-type]


def test_group_requires_explicit_mapping_and_review(tmp_path: Path) -> None:
    path = source(tmp_path, "drawio")
    data = graph_profile("drawio").model_dump(mode="json")
    data["tables"] = [
        {
            "name": "zones",
            "collection": "groups",
            "entity": "zone",
            "fields": {"id": {"path": "/id"}, "name": {"path": "/label"}},
        }
    ]
    draft = create_draft(path, GraphProfile.model_validate(data))
    assert len(draft.candidates) == 2 and all(c.entity == "zone" for c in draft.candidates)
    assert all(c.ambiguities and c.state == "UNRESOLVED" for c in draft.candidates)
    with pytest.raises(ModelError):
        emit_artifacts(draft, review_template(draft), path)


@pytest.mark.parametrize("adapter", ["drawio", "graphml"])
def test_native_trace_has_no_path_despite_connectors(tmp_path: Path, adapter: str) -> None:
    path = source(tmp_path, adapter)
    data = graph_profile(adapter).model_dump(mode="json")
    data["tables"][0]["fields"]["id"] = {"path": "/id"}
    draft = create_draft(path, GraphProfile.model_validate(data))
    review = owner(draft).model_dump(mode="json")
    review["model"]["interfaces"] = [
        {"id": "if_eng", "asset_id": "eng", "placement_zone_id": "control", "ipv4": "10.0.0.1/24"},
        {"id": "if_plc", "asset_id": "plc", "placement_zone_id": "control", "ipv4": "10.0.0.2/24"},
    ]
    review["model"]["services"] = [
        {
            "id": "svc_plc",
            "asset_id": "plc",
            "interface_id": "if_plc",
            "protocol": "tcp",
            "destination_ports": [{"start": 502, "end": 502}],
        }
    ]
    validated = validate_bytes(
        emit_artifacts(draft, OwnerDecisions.model_validate(review), path)["architecture.yaml"]
    )
    trace = trace_architecture(validated, "eng", "svc_plc")
    assert trace.intervals and all(not i.reachable for i in trace.intervals)
    assert not build_graph(validated.model, RESOURCE_LIMITS).edges


@pytest.mark.parametrize(
    "variant", ["xml", "standalone", "anonymous", "same_labels", "schema_location"]
)
def test_supported_variants(tmp_path: Path, variant: str) -> None:
    adapter = "drawio" if variant == "standalone" else "graphml"
    xml = drawio_xml() if adapter == "drawio" else graphml_xml()
    profile = graph_profile(adapter)
    if variant == "standalone":
        xml = ET.tostring(ET.fromstring(xml)[0][0], encoding="unicode")
        profile = profile.model_copy(update={"scopes": ("standalone",)})
    if variant == "anonymous":
        for i in range(5):
            xml = xml.replace(f'edge id="e{i}"', "edge")
    if variant == "same_labels":
        xml = xml.replace("Engineering workstation", "PLC")
    if variant == "schema_location":
        xml = xml.replace(
            "<graphml ",
            '<graphml xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            'xsi:schemaLocation="https://invalid.example/never-fetch" ',
        )
    path = source(tmp_path, adapter, xml)
    if variant == "xml":
        path = path.rename(path.with_suffix(".xml"))
    draft = create_draft(path, profile)
    assert len(draft.candidates) == len({c.candidate_id for c in draft.candidates}) == 6
    assert draft.graph is not None and len(draft.graph.edges) == 5
    assert "https://invalid.example" not in serialize(draft).decode()


def test_stale_decision_and_explicit_xml_selection(tmp_path: Path) -> None:
    path = source(tmp_path, "graphml")
    draft = create_draft(path, graph_profile("graphml"))
    decision = owner(draft).model_copy(update={"draft_sha256": "0" * 64})
    with pytest.raises(ModelError) as error:
        emit_artifacts(draft, decision, path)
    assert error.value.diagnostics[0].code == "IMPORT_STALE_REVIEW"
    path = path.rename(path.with_suffix(".xml"))
    runner = CliRunner()
    assert runner.invoke(app, ["import", "inspect", str(path)]).exit_code == 2
    result = runner.invoke(app, ["import", "inspect", str(path), "--adapter", "graphml"])
    assert result.exit_code == 0, result.output
