"""Contract-2 compact pages preserve every semantic record, fragment and decision."""

import hashlib
import json
from pathlib import Path

import pytest

from otarchguard.explorer import generate_explorer, path
from otarchguard.explorer_html import PageAudit, SiteWriter, audit_site
from tools.synthetic_explorer import explorer_workload


def scaffold(writer: SiteWriter) -> None:
    for name in ("index", "zones", "assets", "interfaces", "declarations", "evidence", "analysis"):
        writer.page(name + ".html", name, "<p>Declared only</p>")
    writer.write("assets.css", b"html{color:black}")


@pytest.mark.parametrize(
    "family", ["candidate", "decision", "group", "node", "connector", "observation"]
)
def test_grouped_records_and_nested_anchors(tmp_path: Path, family: str) -> None:
    writer = SiteWriter(tmp_path, "a" * 64)
    scaffold(writer)
    names = [path(family, i) for i in range(120)]
    for i, name in enumerate(names):
        writer.page(
            name,
            f"Record {i}",
            '<section id="observation"><h2>Original</h2><p>Evidence</p></section><a href="'
            + names[(i + 1) % len(names)]
            + '#observation">Next</a>',
        )
    result = writer.finish({})
    assert result["explorer_version"] == 2
    assert int(result["html_pages"]) < 60  # type: ignore[call-overload]
    assert audit_site(tmp_path)["broken_links"] == 0
    index = writer.locations
    assert all("#" in index[name] for name in names)
    assert all(not (tmp_path / name).exists() for name in names)
    for name in names:
        file, _, anchor = index[name].partition("#")
        parser = PageAudit()
        parser.feed((tmp_path / file).read_text())
        assert anchor in parser.ids and anchor + "-observation" in parser.ids


def test_hash_bucket_split_and_unrelated_bucket_stability(tmp_path: Path) -> None:
    names = [path("candidate", i) for i in range(100)]

    def site(root: Path, entries: list[str]) -> dict[str, str]:
        root.mkdir()
        writer = SiteWriter(root, "b" * 64)
        scaffold(writer)
        for name in reversed(entries):
            writer.page(name, name, "<p>Exact retained evidence.</p>")
        writer.finish({})
        return writer.locations

    before = site(tmp_path / "before", names)
    extra = next(path("candidate", i) for i in range(100, 10000) if path("candidate", i)[10] == "0")
    after = site(tmp_path / "after", [*names, extra])
    for name in names:
        if name[10] != "0":
            assert before[name] == after[name]
    assert before.keys() <= after.keys()


def test_medium_compaction_complete_links_and_determinism(tmp_path: Path) -> None:
    model, sidecar = explorer_workload(tmp_path / "input", 150, 200, 250, 5)
    results = [
        generate_explorer(model, tmp_path / name, provenance=sidecar)
        for name in ("first", "repeat")
    ]
    counts = results[0]["site"]
    assert isinstance(counts, dict)
    assert counts["html_pages"] <= 1358
    assert counts["total_bytes"] <= 10_975_616 * 1.1
    for name in ("first", "repeat"):
        assert audit_site(tmp_path / name)["broken_links"] == 0

    def hashes(root: Path) -> dict[str, str]:
        return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in root.iterdir()}

    assert hashes(tmp_path / "first") == hashes(tmp_path / "repeat")
    manifest = json.loads((tmp_path / "first/manifest.json").read_text())
    # Each old detail identity survives in the location index, not a redirect file.
    assert len(manifest["locations"]) == 2264
    assert manifest["largest_html_bytes"] <= 1024 * 1024
