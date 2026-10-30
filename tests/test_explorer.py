"""Independent structural, trust, security, integrity and installed Explorer checks."""

import hashlib
import json
import os
import re
import subprocess
from dataclasses import replace
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

import pytest
import yaml

from otarchguard.diagnostics import ModelError
from otarchguard.explorer import ExploreOptions, generate_explorer, path
from otarchguard.explorer_data import EXPLORER_LIMITS, load_model, load_provenance, page_id
from otarchguard.explorer_html import CSS, PageAudit, SiteWriter, audit_site, escape, link
from otarchguard.ingestion.project import create_project
from otarchguard.ingestion.project_records import EntityDecision
from otarchguard.ingestion.project_review import emit_project
from otarchguard.ingestion.reconciliation import catalog
from otarchguard.ingestion.workflow import _declaration_yaml
from otarchguard.reporting import architecture_svg, build_report, html_report, json_report
from otarchguard.trace import trace_architecture
from otarchguard.trace_reporting import trace_json
from tools.synthetic_projects import synthetic_project, tutorial_decisions


class Document(HTMLParser):
    def __init__(self, text: str) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: list[tuple[str, dict[str, str | None]]] = []
        self.text: list[str] = []
        self.feed(text)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append((tag, dict(attrs)))

    def handle_data(self, text: str) -> None:
        self.text.append(text)


def content(path: Path) -> str:
    return " ".join(Document(path.read_text(encoding="utf-8")).text)


def files(root: Path) -> dict[str, bytes]:
    return {p.name: p.read_bytes() for p in root.iterdir()}


def location(root: Path, semantic: str) -> str:
    index = json.loads((root / "manifest.json").read_text(encoding="utf-8"))["locations"]
    return str(index.get(semantic, semantic))


def page_at(root: Path, semantic: str) -> Path:
    return root / location(root, semantic).partition("#")[0]


@pytest.fixture(scope="module")
def accepted(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    root = tmp_path_factory.mktemp("explorer-project")
    manifest = synthetic_project(root)
    draft = create_project(manifest)
    artifacts = emit_project(draft, tutorial_decisions(draft), manifest)
    for name, data in artifacts.items():
        (root / name).write_bytes(data)
    return root / "architecture.yaml", root / "architecture.provenance.json"


@pytest.fixture(scope="module")
def evidence_site(
    accepted: tuple[Path, Path],
    tmp_path_factory: pytest.TempPathFactory,
) -> Path:
    root = tmp_path_factory.mktemp("explorer-generated") / "site"
    generate_explorer(accepted[0], root, provenance=accepted[1])
    return root


def test_real_multisource_chain_and_owner_conflict(
    evidence_site: Path,
    accepted: tuple[Path, Path],
) -> None:
    sidecar = load_provenance(accepted[1], load_model(accepted[0]))
    candidates = catalog(sidecar.catalog.sources)
    row = next(
        r
        for r in sidecar.identity_index
        if r["source_id"] == "metadata"
        and any(
            f.field == "zone_id" and f.normalized_value == "alternate"
            for f in candidates[str(r["candidate_entity_id"])][1].fields
        )
    )
    key = str(row["candidate_entity_id"])
    native_id = str(row["model_id"])
    asset = evidence_site / path("native", ["assets", native_id])
    assert "control" in content(asset)
    # The rejected alternate belongs to documentary field evidence, never native zone_id.
    native = load_model(accepted[0]).model
    assert next(a for a in native.assets if a.id == native_id).zone_id == "control"
    candidate = page_at(evidence_site, path("candidate", key))
    assert "alternate" in content(candidate)
    page = Document(candidate.read_text(encoding="utf-8"))
    links = [a["href"] for t, a in page.tags if t == "a"]
    decision = next(d for d in sidecar.decisions.entities if key in d.members)
    decision_path = path("decision", sorted(decision.members))
    assert location(evidence_site, decision_path) in links
    assert path("source", "metadata") in links
    assert path("native", ["assets", native_id]) in links
    assert any(p and p.startswith("group-") for p in links)
    # XLSX + CSV + drawing are distinct origins for the same accepted native asset.
    origins = [
        r
        for r in sidecar.identity_index
        if r["model_id"] == native_id
        and candidates[str(r["candidate_entity_id"])][1].entity == "asset"
    ]
    assert {r["source_id"] for r in origins} == {"inventory", "metadata", "topology"}
    for origin in origins:
        assert location(
            evidence_site, path("candidate", origin["candidate_entity_id"])
        ) in asset.read_text(encoding="utf-8")
    assert "inventory zone controls" in content(page_at(evidence_site, decision_path))


def test_documentary_connectors_never_create_native_edges(
    evidence_site: Path,
    accepted: tuple[Path, Path],
) -> None:
    model = load_model(accepted[0])
    assert not model.model.transport_edges and not model.model.forwarding_edges
    pages = list(evidence_site.glob("connector-*.html"))
    index = json.loads((evidence_site / "manifest.json").read_text())["locations"]
    assert sum(key.startswith("connector-") for key in index) == 5
    for page in pages:
        parsed = Document(page.read_text(encoding="utf-8"))
        assert any(t == "path" and "documentary" in (a.get("class") or "") for t, a in parsed.tags)
        assert not any(t == "path" and "declared" in (a.get("class") or "") for t, a in parsed.tags)
        assert "Documented only" in content(page)
        assert "unknown from this evidence" in content(page)
    assert not list(evidence_site.glob("analysis-*.html"))
    assert "No analytical result is available" in content(evidence_site / "index.html")


def test_model_only_engine_results_and_unmodified_reports(tmp_path: Path) -> None:
    source = Path("tests/fixtures/boundary-device.yaml")
    validated = load_model(source)
    before_model = source.read_bytes()
    before = (
        architecture_svg(validated),
        json_report(build_report("validation", (validated,))),
        html_report(build_report("validation", (validated,)), (validated,)),
    )
    trace = trace_architecture(validated, "it", "svc_jump")
    before_trace = trace_json(trace)
    output = tmp_path / "site"
    generate_explorer(
        source, output, options=ExploreOptions((("it", "svc_jump"),), True, ("support_scope",))
    )
    after = (
        architecture_svg(validated),
        json_report(build_report("validation", (validated,))),
        html_report(build_report("validation", (validated,)), (validated,)),
    )
    assert before == after and before_model == source.read_bytes()
    assert before_trace == trace_json(trace_architecture(validated, "it", "svc_jump"))
    assert "source provenance unavailable" in content(output / "index.html")
    trace_page = output / path("analysis", ["trace", "it", "svc_jump"])
    text = content(trace_page)
    assert validated.sha256 in text and "tcp" in text and "3389" in text
    assert "Allowed under the declared model" in text
    assert path("analysis", ["trace", "it", "svc_jump"]) in (
        output / path("native", ["assets", "it"])
    ).read_text(encoding="utf-8")
    assert "support_scope" in content(output / "analysis.html")


def test_negative_query_differs_from_missing_query(tmp_path: Path, minimal: dict[str, Any]) -> None:
    source = tmp_path / "model.yaml"
    source.write_bytes(_declaration_yaml(minimal))
    validated = load_model(source)
    service = validated.model.services[0]
    origin = next(a.id for a in validated.model.assets if a.id != service.asset_id)
    minimal["rules"] = []
    source.write_bytes(_declaration_yaml(minimal))
    negative = trace_architecture(load_model(source), origin, service.id)
    assert not any(i.reachable for i in negative.intervals)
    generate_explorer(
        source, tmp_path / "assessed", options=ExploreOptions(((origin, service.id),))
    )
    generate_explorer(source, tmp_path / "absent")
    assert "No authorized path for evaluated ports" in content(
        tmp_path / "assessed" / path("analysis", ["trace", origin, service.id])
    )
    assert "Not evaluated" in content(tmp_path / "absent/index.html")
    assert not list((tmp_path / "absent").glob("analysis-*.html"))


def test_no_intents_claim_no_security_conclusion(
    tmp_path: Path, accepted: tuple[Path, Path]
) -> None:
    generate_explorer(accepted[0], tmp_path / "site", options=ExploreOptions(check=True))
    text = content(tmp_path / "site" / path("analysis", "check"))
    assert "No intents were declared" in text and "no source/service queries evaluated" in text


@pytest.mark.parametrize(
    "field",
    [
        "model_sha256",
        "draft_sha256",
        "scope",
        "project_provenance_version",
        "identity_index",
        "declarations",
        "decisions",
        "catalog",
    ],
)
def test_sidecar_tampering_fails_closed(
    tmp_path: Path,
    accepted: tuple[Path, Path],
    field: str,
) -> None:
    value = json.loads(accepted[1].read_text(encoding="utf-8"))
    if field in {"identity_index", "declarations"}:
        value[field] = []
    elif field in {"decisions", "catalog"}:
        value[field] = {}
    elif field == "project_provenance_version":
        value[field] = True
    else:
        value[field] = "tampered"
    sidecar = tmp_path / "sidecar.json"
    sidecar.write_text(json.dumps(value))
    with pytest.raises(ModelError):
        generate_explorer(accepted[0], tmp_path / "site", provenance=sidecar)
    assert not (tmp_path / "site").exists()
    assert not list(tmp_path.glob(".otarchguard-explorer-*"))


@pytest.mark.parametrize(
    "payload",
    [
        b"{}",
        b'{"project_provenance_version":1,"project_provenance_version":1}',
        b"[]",
        b"null",
        b"<html>old report</html>",
        b'{"project_provenance_version":1e0}',
        b'{"project_provenance_version":2}',
        b'{"project_provenance_version":1,"x":NaN}',
    ],
)
def test_malformed_or_unsupported_provenance(
    tmp_path: Path,
    accepted: tuple[Path, Path],
    payload: bytes,
) -> None:
    sidecar = tmp_path / "sidecar.json"
    sidecar.write_bytes(payload)
    with pytest.raises(ModelError):
        generate_explorer(accepted[0], tmp_path / "site", provenance=sidecar)
    assert not (tmp_path / "site").exists()


HOSTILE = [
    "<script>alert(1)</script>",
    "<img src=x onerror=alert(1)>",
    "<svg onload=alert(1)>",
    "javascript:alert(1)",
    "</script><script>alert(1)</script>",
    '" onclick="alert(1)',
    "../../private",
    "C:" + "\\" + "Users" + "\\Example\\secret",
    "&amp;&lt;script&gt;",
    'a & b \' quoted "text"',
    "data:text/html,<script>x</script>",
    "https://example.invalid/external.css",
    "Аsset",
    "é",
    "e\u0301",
    "a\u202eb",
    'xmlns:xlink="bad" xlink:href="javascript:alert(1)"',
]


@pytest.mark.parametrize("label", HOSTILE)
def test_hostile_native_text_is_inert(tmp_path: Path, minimal: dict[str, Any], label: str) -> None:
    minimal["assets"][0]["name"] = label
    minimal["zones"][0]["name"] = label
    source = tmp_path / "model.yaml"
    source.write_bytes(_declaration_yaml(minimal))
    output = tmp_path / "site"
    generate_explorer(source, output)
    for file in output.glob("*.html"):
        parser = PageAudit()
        parser.feed(file.read_text(encoding="utf-8"))
        assert not any(h.startswith(("http", "javascript", "data:", "file:")) for h in parser.links)
    assert 'onclick="alert(1)' not in (output / "index.html").read_text(encoding="utf-8")
    assert not any("private" in p.name or "secret" in p.name for p in output.iterdir())
    assert "C:" + "\\" + "Users" not in (output / "index.html").read_text(encoding="utf-8")


@pytest.mark.parametrize("label", ["a\x00b", "a\x01b", "a\x7fb", "a\x85b", "a\ud800b", "x" * 4097])
def test_unsupported_text_rejects_without_output(
    tmp_path: Path, minimal: dict[str, Any], label: str
) -> None:
    minimal["assets"][0]["name"] = label
    source = tmp_path / "model.yaml"
    source.write_bytes(yaml.safe_dump(minimal, allow_unicode=False).encode())
    with pytest.raises(ModelError):
        generate_explorer(source, tmp_path / "site")
    assert not (tmp_path / "site").exists()
    assert not list(tmp_path.glob(".otarchguard-explorer-*"))


@pytest.mark.parametrize(
    "kind,identities",
    [
        ("native", ["CON", "con", "aux", "../x", "a/b", "a\\b", "X", "x"]),
        ("source", ["é", "e\u0301", "ß", "SS", "А", "A"]),
        ("candidate", ["one::a", "two::a", "ONE::a", "one::A"]),
    ],
)
def test_stable_ids_are_unique_portable_and_independently_hashed(
    kind: str, identities: list[str]
) -> None:
    names = [page_id(kind, i) for i in identities]
    assert len(set(n.casefold() for n in names)) == len(names)
    for identity, name in zip(identities, names, strict=True):
        expected = hashlib.sha256(
            json.dumps(
                [kind, identity], sort_keys=True, ensure_ascii=True, separators=(",", ":")
            ).encode()
        ).hexdigest()
        assert name == kind + "-" + expected
        assert re.fullmatch("[a-z]+-[0-9a-f]{64}", name)


def test_relocation_key_order_and_repeat_bytes(
    tmp_path: Path,
    accepted: tuple[Path, Path],
    evidence_site: Path,
) -> None:
    sidecar = json.loads(accepted[1].read_text(encoding="utf-8"))
    # Key order/whitespace is irrelevant; evidence-array identities are not redefined.
    changed = tmp_path / "sidecar.json"
    changed.write_text(json.dumps(dict(reversed(list(sidecar.items())))))
    generate_explorer(accepted[0], tmp_path / "relocated", provenance=changed)
    assert files(tmp_path / "relocated") == files(evidence_site)


def test_complete_link_integrity_manifest_and_semantic_structure(evidence_site: Path) -> None:
    manifest = json.loads((evidence_site / "manifest.json").read_text(encoding="utf-8"))
    assert audit_site(evidence_site)["html_pages"] == manifest["html_pages"]
    assert set(manifest["files"]) == set(files(evidence_site)) - {"manifest.json"}
    for name, sha in manifest["files"].items():
        assert hashlib.sha256((evidence_site / name).read_bytes()).hexdigest() == sha
    for file in evidence_site.glob("*.html"):
        text = file.read_text(encoding="utf-8")
        parser = Document(text)
        tags = [t for t, _ in parser.tags]
        assert tags.count("main") == tags.count("h1")
        head = text.split("</head>")[0]
        assert head.count("<title>") == 1
        assert tags.count("main") == 1
        assert any(t == "html" and a.get("lang") == "en" for t, a in parser.tags)
        assert any(t == "a" and a.get("href") == "#main" for t, a in parser.tags)
        assert any(t == "nav" and a.get("aria-label") for t, a in parser.tags)
        assert not {"script", "button", "input", "img", "iframe"} & set(tags)
        assert tags.count("table") == tags.count("caption")
        assert all(a.get("scope") in {"col", "row"} for t, a in parser.tags if t == "th")
        assert all(a.get("tabindex") == "0" for t, a in parser.tags if a.get("class") == "scroll")
        assert all(a.get("role") == "img" for t, a in parser.tags if t == "svg")
        for svg in re.findall(r"<svg\b.*?</svg>", text, re.DOTALL):
            root = ET.fromstring(svg)
            assert root.find("{http://www.w3.org/2000/svg}title") is not None
            assert root.find("{http://www.w3.org/2000/svg}desc") is not None
        assert "Not evaluated differs from a negative result" in content(file)
    assert ":focus-visible" in CSS and "max-width:640px" in CSS


@pytest.mark.parametrize(
    "text",
    [
        '<script src="https://example.invalid"></script>',
        '<img src="remote">',
        '<svg onload="alert(1)"></svg>',
        '<a href="javascript:alert(1)">x</a>',
        '<a href="../secret.html">x</a>',
        '<g fill="url(https://example.invalid)"></g>',
        '<p id="same"></p><p id="same"></p>',
        "<svg><foreignObject>x</foreignObject></svg>",
        '<style>@import "https://example.invalid";</style>',
        '<svg:script xmlns:svg="http://www.w3.org/2000/svg">alert(1)</svg:script>',
        '<meta http-equiv="refresh" content="0;url=https://example.invalid">',
        '<link rel="prefetch" href="elsewhere.html">',
    ],
)
def test_independent_output_audit_rejects_active_resources(text: str) -> None:
    with pytest.raises(ValueError):
        PageAudit().feed(text)


@pytest.mark.parametrize(
    "destination",
    [
        "javascript:x",
        "https://example.invalid",
        "../../x",
        "file:///private",
        "data:x",
        'a.html#bad"x',
    ],
)
def test_untrusted_urls_never_become_links(destination: str) -> None:
    with pytest.raises(ValueError):
        link(destination, "label")


def test_existing_output_untouched_and_staging_failure_cleaned(
    tmp_path: Path,
    accepted: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "site"
    target.mkdir()
    (target / "owner.txt").write_text("Owner bytes")
    with pytest.raises(ModelError):
        generate_explorer(accepted[0], target)
    assert files(target) == {"owner.txt": b"Owner bytes"}

    def broken(self: SiteWriter, name: str, data: bytes) -> None:
        raise OSError("Synthetic disk failure")

    monkeypatch.setattr(SiteWriter, "write", broken)
    with pytest.raises(ModelError):
        generate_explorer(accepted[0], tmp_path / "failed")
    assert not (tmp_path / "failed").exists()
    assert not list(tmp_path.glob(".otarchguard-explorer-*"))


@pytest.mark.parametrize("budget", ["pages", "page_bytes", "total_bytes", "analyses"])
def test_output_budgets_never_publish_partial_sites(
    budget: str,
    tmp_path: Path,
    accepted: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    limits = replace(EXPLORER_LIMITS, **{budget: 0})
    for module in ("otarchguard.explorer", "otarchguard.explorer_html"):
        monkeypatch.setattr(module + ".EXPLORER_LIMITS", limits)
    with pytest.raises(ModelError):
        generate_explorer(accepted[0], tmp_path / "site", options=ExploreOptions(check=True))
    assert not (tmp_path / "site").exists()


def test_symlink_input_output_and_ancestors_are_rejected(tmp_path: Path) -> None:
    source = Path("tests/fixtures/minimal-valid.yaml").resolve()
    target = tmp_path / "linked.yaml"
    try:
        target.symlink_to(source)
    except OSError:
        # Managed Windows can deny creating links. Independently exercise the guard.
        from unittest.mock import patch

        with patch.object(Path, "is_symlink", return_value=True), pytest.raises(ModelError):
            generate_explorer(source, tmp_path / "site")
    else:
        with pytest.raises(ModelError):
            generate_explorer(target, tmp_path / "site")
    assert not (tmp_path / "site").exists()


@pytest.mark.parametrize("query", ["no-colon", "a:", ":b", "a:b:c", "missing:svc_plc"])
def test_real_console_structured_failure_no_output(
    tmp_path: Path,
    installed_console: Path,
    query: str,
) -> None:
    result = subprocess.run(
        [
            str(installed_console),
            "explore",
            str(Path("tests/fixtures/minimal-valid.yaml").resolve()),
            "--output",
            str(tmp_path / "site"),
            "--trace",
            query,
        ],
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 2 and not result.stdout
    diagnostic = json.loads(result.stderr)
    assert diagnostic["category"] in {"invalid_input", "unsupported_model"}
    assert not (tmp_path / "site").exists()


def test_real_console_works_outside_checkout(
    tmp_path: Path,
    installed_console: Path,
    accepted: tuple[Path, Path],
) -> None:
    result = subprocess.run(
        [
            str(installed_console),
            "explore",
            str(accepted[0]),
            "--provenance",
            str(accepted[1]),
            "--output",
            "site",
        ],
        cwd=tmp_path,
        capture_output=True,
        timeout=40,
    )
    assert result.returncode == 0, result.stderr
    metadata = json.loads(result.stdout)
    assert metadata["status"] == "complete"
    assert metadata["site"]["html_pages"] > 50
    assert "files" not in metadata["site"]
    assert metadata["model_sha256"] == load_model(accepted[0]).sha256


def test_nonregular_file_refused_without_open(tmp_path: Path) -> None:
    if os.name != "nt":
        target = tmp_path / "pipe"
        fifo_function = "mkfifo"
        getattr(os, fifo_function)(target)
    else:
        target = tmp_path
    with pytest.raises(ModelError):
        generate_explorer(target, tmp_path / "site")


def test_missing_and_duplicate_local_anchor_detection(tmp_path: Path) -> None:
    (tmp_path / "a.html").write_text('<a href="b.html#missing">Broken</a>')
    (tmp_path / "b.html").write_text('<p id="other">Other</p>')
    with pytest.raises(ValueError, match="anchor"):
        audit_site(tmp_path)
    (tmp_path / "b.html").unlink()
    with pytest.raises(ValueError, match="file"):
        audit_site(tmp_path)


def test_default_palette_contrast() -> None:
    def luminance(color: str) -> float:
        channels = [int(color[i : i + 2], 16) / 255 for i in (0, 2, 4)]
        linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in channels]
        return sum(a * b for a, b in zip(linear, (0.2126, 0.7152, 0.0722), strict=True))

    for foreground in ("172d3e", "124f7c", "40596b", "763d00"):
        for background in ("ffffff", "f2f5f7", "e5edf2", "fff7e5"):
            assert (luminance(background) + 0.05) / (luminance(foreground) + 0.05) >= 4.5


def test_safety_boundary_preserves_quotes_entities_and_visible_bidi() -> None:
    assert escape("&lt;x&gt;") == "&amp;lt;x&amp;gt;"
    assert escape('"x"') == "&quot;x&quot;"
    assert "[U+202E]" in escape("a\u202eb")
    assert "local path withheld" in escape("file:///fictional/secret")


@pytest.mark.parametrize("hostile", HOSTILE[:9])
def test_hostile_evidence_labels_and_owner_rationales_are_inert(
    tmp_path: Path,
    hostile: str,
) -> None:
    manifest = synthetic_project(tmp_path / "project")
    topology = manifest.parent / "topology.drawio"
    xml = ET.fromstring(topology.read_text(encoding="utf-8"))
    for cell in xml.findall(".//mxCell"):
        if cell.get("vertex") == "1" or cell.get("edge") == "1":
            cell.set("value", hostile)
    topology.write_text(ET.tostring(xml, encoding="unicode"), encoding="utf-8")
    draft = create_project(manifest)
    owner = tutorial_decisions(draft)
    owner = owner.model_copy(
        update={
            "entities": tuple(d.model_copy(update={"rationale": hostile}) for d in owner.entities)
        }
    )
    artifacts = emit_project(draft, owner, manifest)
    for name, data in artifacts.items():
        (tmp_path / name).write_bytes(data)
    generate_explorer(
        tmp_path / "architecture.yaml",
        tmp_path / "site",
        provenance=tmp_path / "architecture.provenance.json",
    )
    assert audit_site(tmp_path / "site")["html_pages"] > 50
    for file in (tmp_path / "site").glob("*.html"):
        PageAudit().feed(file.read_text(encoding="utf-8"))


def test_rejected_graphical_origin_stays_documentary(tmp_path: Path) -> None:
    manifest = synthetic_project(tmp_path / "project")
    draft = create_project(manifest)
    owner = tutorial_decisions(draft)
    original = next(d for d in owner.entities if d.canonical_id == "eng")
    graph_member = next(m for m in original.members if m.startswith("topology::"))
    selected = original.model_copy(
        update={"members": tuple(m for m in original.members if m != graph_member)}
    )
    rejected = EntityDecision(
        members=(graph_member,),
        decision="OWNER_REJECTED",
        rationale="Fictional owner rejects this graphical alias.",
    )
    owner = owner.model_copy(
        update={
            "entities": tuple(d for d in owner.entities if d is not original) + (selected, rejected)
        }
    )
    artifacts = emit_project(draft, owner, manifest)
    for name, data in artifacts.items():
        (tmp_path / name).write_bytes(data)
    generate_explorer(
        tmp_path / "architecture.yaml",
        tmp_path / "site",
        provenance=tmp_path / "architecture.provenance.json",
    )
    text = content(page_at(tmp_path / "site", path("candidate", graph_member)))
    assert "OWNER_REJECTED" in text and "No native entity accepted" in text
    native = (tmp_path / "site" / path("native", ["assets", "eng"])).read_text(encoding="utf-8")
    assert location(tmp_path / "site", path("candidate", graph_member)) not in native


def test_native_ordering_preserves_byte_output(tmp_path: Path, minimal: dict[str, Any]) -> None:
    a, b = tmp_path / "a.yaml", tmp_path / "b.yaml"
    a.write_bytes(_declaration_yaml(minimal))
    for value in minimal.values():
        if isinstance(value, list):
            value.reverse()
    b.write_bytes(_declaration_yaml(minimal))
    generate_explorer(a, tmp_path / "first")
    generate_explorer(b, tmp_path / "second")
    assert files(tmp_path / "first") == files(tmp_path / "second")
