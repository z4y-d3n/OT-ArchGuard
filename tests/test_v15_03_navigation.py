"""Exact document orientation and authentic evidence journeys, using independent DOMs."""

import copy
import importlib.util
import re
import subprocess
from pathlib import Path
from typing import Any

import pytest
from test_capture_ux_integrity import Document, documents, frozen, render

from otarchguard.explorer_html import audit_site

ROOT = Path(__file__).resolve().parents[1]
BASE = "a3cf2f2e226b7a0fe985816cbaafb6ec6527b2f5"


def check_orientation(pages: dict[str, Document], flows: list[dict[str, Any]], size: int) -> None:
    for name, page in pages.items():
        ids = [n.attrs["id"] for n in page.elements if "id" in n.attrs]
        assert len(ids) == len(set(ids))
        for node in page.links():
            href = str(node.attrs["href"])
            filename, _, fragment = href.partition("#")
            if filename.endswith(".json"):
                continue
            target = pages[filename or name]
            if fragment:
                assert any(n.attrs.get("id") == fragment for n in target.elements)
            if node.attrs.get("aria-current") == "page":
                assert filename == name, "current page points to a different document"
        main = [n for n in page.elements if n.tag == "main"]
        assert len(main) == 1 and main[0].attrs == {"id": "main", "tabindex": "-1"}
        family_nav = [
            n
            for n in page.elements
            if n.tag == "nav"
            and n.attrs.get("aria-label") in {"Main evidence views", "Related evidence views"}
        ]
        active = [
            n
            for nav in family_nav
            for n in nav.descendants()
            if n.tag == "a" and n.attrs.get("aria-current") in {"page", "true"}
        ]
        assert len(active) == 1
        family = re.sub(r"-\d+\.html$", ".html", name)
        if name.startswith(("evidence-", "evidenceindex-")):
            family = "evidence.html"
        assert active[0].attrs["href"] == family
        assert active[0].attrs["aria-current"] == ("page" if name == family else "true")
    listings: dict[str, list[tuple[int, str]]] = {}
    for name, page in pages.items():
        if not any(
            n.tag == "nav" and n.attrs.get("aria-label") == "Table pages" for n in page.elements
        ):
            continue
        stem = name.removesuffix(".html")
        match = re.fullmatch(r"(.+)-(\d+)", stem)
        number = int(match[2]) if match else 1
        stem = match[1] if match else stem
        if stem == "evidenceindex":
            stem = "evidence"
        listings.setdefault(stem, []).append((number, name))
    for stem, numbered in listings.items():
        ordered = sorted(numbered)
        assert [n for n, _ in ordered] == list(range(1, len(ordered) + 1))
        total = sum(
            1
            for _, name in ordered
            for node in pages[name].elements
            if node.tag == "tr" and "id" in node.attrs
        )
        assert len(ordered) == max(1, (total + size - 1) // size)
        for index, (_, name) in enumerate(ordered):
            expected_name = (
                stem + ".html"
                if index == 0
                else ("evidenceindex" if stem == "evidence" else stem) + f"-{index + 1}.html"
            )
            assert name == expected_name
            pager = [
                n
                for n in pages[name].elements
                if n.tag == "nav" and n.attrs.get("aria-label") == "Table pages"
            ]
            assert len(pager) == 1
            current = [n for n in pager[0].descendants() if n.attrs.get("aria-current") == "page"]
            assert len(current) == 1 and current[0].tag == "p"
            start, end = min(index * size + 1, total), min((index + 1) * size, total)
            assert current[0].text() == (
                f"Page {index + 1} of {len(ordered)} · Records {start}–{end} of {total}"
            )
            links = {n.text(): n.attrs["href"] for n in pager[0].descendants() if n.tag == "a"}
            expected = {}
            if index:
                expected["Previous page"] = ordered[index - 1][1]
            if index + 1 < len(ordered):
                expected["Next page"] = ordered[index + 1][1]
            assert links == expected, "listing pagination destination"
    count = (len(flows) + size - 1) // size
    for i in range(count):
        name = f"evidence-{i + 1}.html"
        page = pages[name]
        pager = [
            n
            for n in page.elements
            if n.tag == "nav" and n.attrs.get("aria-label") == "Evidence detail pages"
        ]
        assert len(pager) == 1
        current = [n for n in pager[0].descendants() if n.attrs.get("aria-current") == "page"]
        assert len(current) == 1 and current[0].tag == "p"
        text = pager[0].text()
        assert f"Page {i + 1} of {count}" in text
        assert f"Records {i * size + 1}–{min((i + 1) * size, len(flows))} of {len(flows)}" in text
        links = {n.text(): n.attrs["href"] for n in pager[0].descendants() if n.tag == "a"}
        expected = {}
        if i:
            expected["Previous page"] = f"evidence-{i}.html"
        if i + 1 < count:
            expected["Next page"] = f"evidence-{i + 2}.html"
        assert links == expected, "pagination destination"
        actual = [n.attrs["id"] for n in page.elements if n.attrs.get("class") == "evidence-record"]
        assert actual == ["flow-" + f["id"] for f in flows[i * size : (i + 1) * size]]


@pytest.mark.parametrize("case", ["supported", "limited"])
@pytest.mark.parametrize("size", [1, 2, 100])
def test_complete_document_and_detail_batch_journey(tmp_path: Path, case: str, size: int) -> None:
    value = frozen(case)
    original = copy.deepcopy(value)
    output = tmp_path / "site"
    render(output, value, size)
    check_orientation(documents(output), value["observations"]["flows"], size)
    assert value == original
    assert audit_site(output)["html_pages"] == len(documents(output))


@pytest.mark.parametrize(
    "mutation",
    [
        "wrong-current",
        "missing-anchor",
        "duplicate-id",
        "wrong-next",
        "omitted-record",
        "wrong-record",
        "wrong-listing-next",
        "missing-current",
    ],
)
def test_independent_journey_guard_rejects_corruption(tmp_path: Path, mutation: str) -> None:
    value = frozen("supported")
    output = tmp_path / "site"
    render(output, value, 2)
    page = output / "evidence-1.html"
    text = page.read_text(encoding="utf-8")
    first = value["observations"]["flows"][0]["id"]
    second = value["observations"]["flows"][1]["id"]
    if mutation == "wrong-current":
        text = text.replace(
            'href="evidence.html" aria-current="true"', 'href="evidence.html" aria-current="page"'
        )
    elif mutation == "missing-anchor":
        text = text.replace('id="flow-' + first + '"', 'id="missing"')
    elif mutation == "duplicate-id":
        text = text.replace('id="flow-' + second + '"', 'id="flow-' + first + '"')
    elif mutation == "wrong-next":
        text = text.replace('href="evidence-2.html">Next page', 'href="evidence-3.html">Next page')
    elif mutation == "omitted-record":
        text = text.replace('class="evidence-record"', 'class="hidden-record"', 1)
    elif mutation == "wrong-record":
        text = text.replace('id="flow-' + first + '"', 'id="flow-' + "0" * 64 + '"')
    elif mutation == "wrong-listing-next":
        page = output / "conversations.html"
        text = page.read_text(encoding="utf-8").replace(
            'href="conversations-2.html">Next page', 'href="conversations-3.html">Next page'
        )
    else:
        text = text.replace('<p aria-current="page">', "<p>")
    assert text != page.read_text(encoding="utf-8")
    page.write_text(text, encoding="utf-8")
    with pytest.raises((AssertionError, KeyError)):
        check_orientation(documents(output), value["observations"]["flows"], 2)


def test_empty_capture_listing_orientation(tmp_path: Path) -> None:
    from otarchguard.capture.explorer import generate_site
    from otarchguard.capture.observations import analyze_capture
    from tools.capture_workloads import write_pcap

    source = tmp_path / "empty.pcap"
    write_pcap(source, count=0)
    observed = analyze_capture(source)
    output = tmp_path / "site"
    generate_site(observed, output)
    check_orientation(documents(output), [], 100)


def test_predecessor_canonical_and_identified_evidence_content_are_exact(tmp_path: Path) -> None:
    source = subprocess.check_output(
        ["git", "show", BASE + ":src/otarchguard/capture/explorer.py"], cwd=ROOT
    )
    path = tmp_path / "predecessor.py"
    path.write_bytes(source)
    spec = importlib.util.spec_from_file_location("v15_03_original_capture", path)
    assert spec and spec.loader
    old = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old)
    from dataclasses import replace

    from otarchguard.capture.contract import CAPTURE_LIMITS

    value = frozen("limited")
    old.generate_site(
        value["observations"],
        tmp_path / "before",
        value["comparison"],
        mapping=value["mapping"],
        limits=replace(CAPTURE_LIMITS, rows_per_page=2),
    )
    render(tmp_path / "after", value, 2)
    before, after = documents(tmp_path / "before"), documents(tmp_path / "after")
    assert before.keys() == after.keys()
    for name in ("observations.json", "comparison.json", "mapping.json"):
        assert (tmp_path / "before" / name).read_bytes() == (tmp_path / "after" / name).read_bytes()
    for name in before:
        old_records = {
            n.attrs["id"]: n.text()
            for n in before[name].elements
            if "id" in n.attrs and n.attrs["id"] != "main"
        }
        new_records = {
            n.attrs["id"]: n.text()
            for n in after[name].elements
            if "id" in n.attrs and n.attrs["id"] != "main"
        }
        assert old_records == new_records, name
