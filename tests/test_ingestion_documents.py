"""Documentary subsets, exact provenance, review integration and hostile OPC inputs."""

import io
import json
import zipfile
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from otarchguard.api import validate_bytes
from otarchguard.cli import app
from otarchguard.diagnostics import ModelError
from otarchguard.explorer import generate_explorer, path
from otarchguard.explorer_html import PageAudit, audit_site
from otarchguard.ingestion.documents import DOCUMENT_LIMITS, create_document_draft, inspect_document
from otarchguard.ingestion.project import create_project
from otarchguard.ingestion.project_review import (
    acknowledge_connectors,
    emit_project,
    project_template,
)
from otarchguard.ingestion.records import DocumentProfile, ImportDraft
from otarchguard.ingestion.workflow import create_draft, serialize
from tools.synthetic_documents import R, docx_parts, package, pptx_parts, write_documents
from tools.synthetic_projects import synthetic_project, tutorial_decisions, write_json


def profile(
    adapter: str, *, collection: str | None = None, select: tuple[str, ...] = ("*",)
) -> DocumentProfile:
    return DocumentProfile.model_validate(
        {
            "profile_version": 4,
            "adapter": adapter,
            "select": select,
            "tables": []
            if collection is None
            else [
                {
                    "name": "assets",
                    "collection": collection,
                    "entity": "asset",
                    "fields": {
                        key: {"path": "/" + source}
                        for key, source in (("id", "id"), ("name", "name"), ("zone_id", "zone"))
                    },
                }
            ],
        }
    )


@pytest.fixture
def documents(tmp_path: Path) -> Path:
    root = tmp_path / "documents"
    write_documents(root)
    return root


FORMATS = [
    ("txt", "notes.txt", "key-values"),
    ("md", "notes.md", "table:1"),
    ("docx", "inventory.docx", "word/document.xml/table:1"),
    ("pptx", "architecture.pptx", "slide:257/table:4"),
]


@pytest.mark.parametrize("adapter,filename,collection", FORMATS)
def test_no_inference_exact_mapping_and_roundtrip(
    documents: Path, adapter: str, filename: str, collection: str
) -> None:
    unmapped = create_draft(documents / filename, profile(adapter))
    assert unmapped.import_version == 5 and not unmapped.candidates
    assert unmapped.document and unmapped.document.observations
    assert ImportDraft.model_validate_json(serialize(unmapped)) == unmapped
    mapped = create_draft(documents / filename, profile(adapter, collection=collection))
    assert len(mapped.candidates) == 1
    assert mapped.candidates[0].state == "UNRESOLVED"
    assert {f.field: f.normalized_value for f in mapped.candidates[0].fields} == {
        "id": "eng",
        "name": "Engineering Station",
        "zone_id": "alternate",
    }
    assert all(f.location is not None for f in mapped.candidates[0].fields)
    assert b"OWNER_CONFIRMED" not in serialize(unmapped)


def test_docx_runs_preserve_spaces_tabs_breaks_and_order(documents: Path) -> None:
    draft = create_draft(documents / "inventory.docx", profile("docx"))
    assert draft.document
    assert [o.text for o in draft.document.observations[:3]] == [
        "Inventory",
        " A B\tC\nD",
        "TCP 502 allowed",
    ]
    assert draft.document.observations[0].category == "heading"
    assert draft.document.observations[3].location.record == "row:1/cell:1"
    assert all("page" not in o.location.record for o in draft.document.observations)


def test_pptx_explicit_order_ids_and_inert_arrows(documents: Path) -> None:
    draft = create_draft(documents / "architecture.pptx", profile("pptx"))
    assert draft.document
    first = draft.document.observations[0]
    assert first.location.collection == "slide:257"
    assert "slide2.xml/order:1/shape:2" in first.location.record
    assert any(d.code == "DOCUMENT_SHAPE_EXCLUDED" for d in draft.diagnostics)
    assert not draft.graph and not draft.candidates


def test_markdown_inert_structures_and_cell_provenance(documents: Path) -> None:
    draft = create_draft(documents / "notes.md", profile("md"))
    assert draft.document
    categories = {o.category for o in draft.document.observations}
    assert {"heading", "paragraph", "list", "fenced_text", "table_cell"} <= categories
    assert any(o.text == "<script>alert(1)</script>" for o in draft.document.observations)
    assert draft.document.observations[-1].location.record == "line:9/cell:3"


@pytest.mark.parametrize("adapter,filename,collection", FORMATS)
def test_mixed_project_review_stale_and_explorer(
    documents: Path, adapter: str, filename: str, collection: str, tmp_path: Path
) -> None:
    manifest = synthetic_project(tmp_path / "project")
    root = manifest.parent
    (root / filename).write_bytes((documents / filename).read_bytes())
    write_json(
        root / "document-profile.json",
        profile(adapter, collection=collection).model_dump(mode="json"),
    )
    value = json.loads(manifest.read_text())
    value["sources"].append(
        dict(id="document", path=filename, adapter=adapter, profile="document-profile.json")
    )
    write_json(manifest, value)
    draft = create_project(manifest)
    template = project_template(draft)
    ack = acknowledge_connectors(
        draft, template, "document", "Fictional owner", "Documentary context only"
    )
    assert ack.entities == template.entities and not ack.model_confirmed
    owner = tutorial_decisions(draft)
    assert draft.conflicts
    artifacts = emit_project(draft, owner, manifest)
    for name, data in artifacts.items():
        (tmp_path / name).write_bytes(data)
    native = validate_bytes(artifacts["architecture.yaml"]).model
    assert not native.transport_edges and not native.rules and not native.forwarding_edges
    result = generate_explorer(
        tmp_path / "architecture.yaml",
        tmp_path / "site",
        provenance=tmp_path / "architecture.provenance.json",
    )
    assert result["site"]["broken_links"] == 0  # type: ignore[index]
    sidecar = json.loads(artifacts["architecture.provenance.json"])
    assert any(s["evidence"].get("document") for s in sidecar["catalog"]["sources"])
    site = tmp_path / "site"
    assert audit_site(site)["anchors"] > 0
    locations = json.loads((site / "manifest.json").read_text())["locations"]
    obs = next(s for s in draft.sources if s.id == "document").evidence.document
    assert obs
    for item in obs.observations:
        assert path("observation", ["document", item.observation_id]) in locations
    source = root / filename
    if adapter in {"txt", "md"}:
        source.write_bytes(source.read_bytes() + b"\nNew paragraph\n")
    else:
        source.write_bytes(
            package(
                docx_parts("Changed paragraph")
                if adapter == "docx"
                else pptx_parts("Changed slide")
            )
        )
    with pytest.raises(ModelError) as changed:
        emit_project(draft, owner, manifest)
    assert changed.value.diagnostics[0].code == "PROJECT_SOURCE_CHANGED"
    fresh = create_project(manifest)
    with pytest.raises(ModelError) as stale:
        emit_project(fresh, owner, manifest)
    assert stale.value.diagnostics[0].code == "PROJECT_STALE_REVIEW"


@pytest.mark.parametrize("adapter,filename,collection", FORMATS)
def test_selected_table_evidence_only(
    documents: Path, adapter: str, filename: str, collection: str
) -> None:
    draft = create_draft(documents / filename, profile(adapter, select=(collection,)))
    assert not draft.candidates
    assert draft.document
    assert all(o.location.collection == collection for o in draft.document.observations)


@pytest.mark.parametrize("raw", [b"\xff", b"a\x00b", b"a\x1bb", b"a\xc2\x85b", b"\xff\xfea\x00"])
def test_reject_encoding_and_controls(tmp_path: Path, raw: bytes) -> None:
    source = tmp_path / "bad.txt"
    source.write_bytes(raw)
    with pytest.raises(ModelError):
        create_draft(source, profile("txt"))


@pytest.mark.parametrize("text", ["x" * 4097, "a\n" * 4001])
def test_text_limits_before_mapping(tmp_path: Path, text: str) -> None:
    source = tmp_path / "large.txt"
    source.write_text(text)
    with pytest.raises(ModelError):
        create_draft(source, profile("txt"))


@pytest.mark.parametrize(
    "adapter,parts_fn,main",
    [("docx", docx_parts, "word/document.xml"), ("pptx", pptx_parts, "ppt/slides/slide2.xml")],
)
@pytest.mark.parametrize(
    "attack",
    [
        "dtd",
        "pi",
        "external",
        "missing",
        "macro",
        "traversal",
        "case",
        "duplicate",
        "bomb",
        "bad-types",
        "namespace",
        "cycle",
        "truncated",
    ],
)
def test_opc_xml_attacks(
    tmp_path: Path, adapter: str, parts_fn: Any, main: str, attack: str
) -> None:
    parts = parts_fn()
    if attack == "dtd":
        parts[main] = '<!DOCTYPE x [<!ENTITY e "attack">]>' + parts[main]
    elif attack == "pi":
        parts[main] = "<?work execute?>" + parts[main]
    elif attack == "external":
        parts["_rels/.rels"] = parts["_rels/.rels"].replace(
            'Target="', 'TargetMode="External" Target="https://invalid.example/'
        )
    elif attack == "missing":
        del parts[main]
    elif attack == "macro":
        parts["vbaProject.bin"] = "macro"
    elif attack == "traversal":
        parts["../outside.xml"] = "<x/>"
    elif attack == "case":
        parts[main.upper()] = parts[main]
    elif attack == "bomb":
        parts[main] = "<x>" + "a" * 1_000_000 + "</x>"
    elif attack == "bad-types":
        parts["[Content_Types].xml"] = "<Types/>"
    elif attack == "namespace":
        parts[main] = '<x xmlns="' + "x" * 5000 + '"/>'
    elif attack == "cycle":
        main_target = "word/document.xml" if adapter == "docx" else "ppt/presentation.xml"
        parts["_rels/.rels"] = (
            parts["_rels/.rels"]
            .replace(R + "/officeDocument", R + "/slide")
            .replace(main_target, main_target)
        )
    data = package(parts)
    if attack == "duplicate":
        stream = io.BytesIO(data)
        with (
            pytest.warns(UserWarning, match="Duplicate name"),
            zipfile.ZipFile(stream, "a") as archive,
        ):
            archive.writestr(main, parts[main])
        data = stream.getvalue()
    elif attack == "truncated":
        data = data[: len(data) // 2]
    source = tmp_path / ("hostile." + adapter)
    source.write_bytes(data)
    with pytest.raises(ModelError):
        create_draft(source, profile(adapter))


@pytest.mark.parametrize("construct", ["ins", "del", "fldSimple", "sdt", "object", "drawing"])
def test_docx_unsupported_constructs_fail_closed(tmp_path: Path, construct: str) -> None:
    parts = docx_parts()
    parts["word/document.xml"] = parts["word/document.xml"].replace(
        "<w:r>", f"<w:{construct}/><w:r>", 1
    )
    source = tmp_path / "unsupported.docx"
    source.write_bytes(package(parts))
    with pytest.raises(ModelError):
        create_draft(source, profile("docx"))


@pytest.mark.parametrize(
    "limit",
    [
        "source_bytes",
        "uncompressed_bytes",
        "members",
        "xml_depth",
        "xml_elements",
        "xml_text",
        "observations",
        "paragraphs",
        "tables",
        "cells",
        "text",
    ],
)
def test_cumulative_document_limits(documents: Path, limit: str) -> None:
    with pytest.raises(ModelError):
        create_document_draft(
            documents / "inventory.docx", profile("docx"), replace(DOCUMENT_LIMITS, **{limit: 0})
        )


@pytest.mark.parametrize("adapter,filename,collection", FORMATS)
def test_inspection_and_cli(documents: Path, adapter: str, filename: str, collection: str) -> None:
    result = inspect_document(documents / filename, adapter)
    assert len(result["preview"]) <= 10  # type: ignore[arg-type]
    output = CliRunner().invoke(app, ["import", "inspect", str(documents / filename)])
    assert output.exit_code == 0, output.output
    assert json.loads(output.stdout)["subset_version"] == 1


@pytest.mark.parametrize("extension", ["pdf", "vsdx"])
def test_optional_formats_are_explicitly_deferred(tmp_path: Path, extension: str) -> None:
    result = CliRunner().invoke(
        app, ["import", "inspect", str(tmp_path / ("deferred." + extension))]
    )
    assert result.exit_code == 2 and "IMPORT_DOCUMENT_UNSUPPORTED" in result.output


@pytest.mark.parametrize("adapter,filename,collection", FORMATS)
def test_document_selection_typos_fail_closed(
    documents: Path, adapter: str, filename: str, collection: str
) -> None:
    with pytest.raises(ModelError):
        create_draft(documents / filename, profile(adapter, select=("absent-collection",)))


@pytest.mark.parametrize("mutation", ["merge", "tracked-row", "nested", "field"])
def test_word_table_unsupported_content_is_not_silently_lost(tmp_path: Path, mutation: str) -> None:
    parts = docx_parts()
    main = "word/document.xml"
    if mutation == "merge":
        parts[main] = parts[main].replace(
            "<w:tc>", '<w:tc><w:tcPr><w:gridSpan w:val="2"/></w:tcPr>', 1
        )
    elif mutation == "tracked-row":
        parts[main] = parts[main].replace("<w:tr>", "<w:tr><w:trPr><w:ins/></w:trPr>", 1)
    elif mutation == "nested":
        parts[main] = parts[main].replace("<w:tc>", "<w:tc><w:tbl/>", 1)
    else:
        parts[main] = parts[main].replace("<w:tc>", "<w:tc><w:p><w:fldSimple/></w:p>", 1)
    path = tmp_path / "unsupported.docx"
    path.write_bytes(package(parts))
    with pytest.raises(ModelError):
        create_draft(path, profile("docx"))


def test_evidence_only_text_does_not_parse_duplicate_keys(tmp_path: Path) -> None:
    path = tmp_path / "notes.txt"
    path.write_text("id=old\nid=current\n", encoding="utf-8")
    draft = create_draft(path, profile("txt"))
    assert draft.document and len(draft.document.observations) == 2 and not draft.candidates
    with pytest.raises(ModelError):
        create_draft(path, profile("txt", collection="key-values"))


@pytest.mark.parametrize(
    "mutation", ["slide-id", "duplicate-slide-id", "shape-id", "duplicate-shape-id"]
)
def test_presentation_structural_ids_fail_closed(tmp_path: Path, mutation: str) -> None:
    parts = pptx_parts()
    if mutation in {"slide-id", "duplicate-slide-id"}:
        parts["ppt/presentation.xml"] = parts["ppt/presentation.xml"].replace(
            'id="257"', 'id="invalid"' if mutation == "slide-id" else 'id="0256"'
        )
    else:
        parts["ppt/slides/slide2.xml"] = parts["ppt/slides/slide2.xml"].replace(
            'id="2"', 'id="invalid"' if mutation == "shape-id" else 'id="03"'
        )
    source = tmp_path / "invalid.pptx"
    source.write_bytes(package(parts))
    with pytest.raises(ModelError):
        create_draft(source, profile("pptx"))


@pytest.mark.parametrize(
    "text",
    [
        "<script>alert(1)</script>",
        '<img src="https://example.invalid/x">',
        "javascript:alert(1)",
        "a\u202eb",
        "../outside",
        "file:///fictional/private",
    ],
)
def test_hostile_document_html_is_inert(tmp_path: Path, text: str) -> None:
    manifest = synthetic_project(tmp_path / "project")
    source = manifest.parent / "notes.txt"
    source.write_text(text, encoding="utf-8")
    write_json(manifest.parent / "notes-profile.json", profile("txt").model_dump(mode="json"))
    config = json.loads(manifest.read_text())
    config["sources"].append(
        dict(id="notes", adapter="txt", path="notes.txt", profile="notes-profile.json")
    )
    write_json(manifest, config)
    draft = create_project(manifest)
    for name, data in emit_project(draft, tutorial_decisions(draft), manifest).items():
        (tmp_path / name).write_bytes(data)
    site = tmp_path / "site"
    generate_explorer(
        tmp_path / "architecture.yaml", site, provenance=tmp_path / "architecture.provenance.json"
    )
    for page in site.glob("*.html"):
        PageAudit().feed(page.read_text(encoding="utf-8"))
