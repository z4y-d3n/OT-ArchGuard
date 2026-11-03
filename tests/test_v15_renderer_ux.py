"""Literal semantic oracle, isolated CSS and independent predecessor rendering."""

import copy
import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest
from test_historical_explorer_bundle import inputs as inputs
from test_historical_explorer_layout import DOM, Element, rules
from test_historical_explorer_render import _fixture, _structural_oracle

from otarchguard.diagnostics import ModelError
from otarchguard.drift import explorer_bundle as bundle
from otarchguard.drift.contract import LIMITATIONS
from otarchguard.drift.explorer_render import render
from tools.verify_v15_transition import reference

EXPECTED = [
    "Differences describe selected finite evidence and declared models, not deployment changes.",
    "Unobserved traffic is not proven absent, blocked or evidence of an offline device.",
    "Raw addresses and matching labels do not establish physical device or sensor identity.",
    "Packet counts are raw counts, not rates or normalized activity trends.",
    "Capture authenticity, clock synchronization and reviewer authority are unattested.",
    "Protocol headers do not prove command execution, application success or authorization.",
    "No incident, attribution, industrial safety or risk severity is determined.",
]


def test_exact_seven_semantic_items_and_unchanged_input() -> None:
    assert list(LIMITATIONS) == EXPECTED
    report, verification = _fixture()
    report["limitations"] = EXPECTED.copy()
    before = copy.deepcopy(report)
    files = render(report, verification)
    _structural_oracle(files)
    (listing,) = DOM(files["index.html"]).root.nodes("ul", "major-limitations")
    items = [n for n in listing.children if isinstance(n, Element)]
    assert [n.tag for n in items] == ["li"] * 7
    assert [n.text for n in items] == report["limitations"] == EXPECTED
    assert listing.attrs["class"] == "major-limitations"
    assert all(b'major-limitations"' not in data for n, data in files.items() if n != "index.html")
    assert report == before and render(report, verification) == files


@pytest.mark.parametrize(
    "viewport,print_mode", [(1440, False), (375, False), (187.5, False), (800, True)]
)
def test_local_vertical_native_bullet_css(viewport: float, print_mode: bool) -> None:
    files = render(*_fixture())
    css = rules(files["style.css"].decode(), viewport, print_mode=print_mode)
    listing, item = css[".major-limitations"], css[".major-limitations>li"]
    assert listing["display"] == "block" and listing["list-style"] == "disc outside"
    assert listing["padding-left"] == "1.4rem" and listing["max-width"] == "100%"
    assert item["display"] == "list-item" and item["margin"] == ".5rem 0"
    assert item["overflow-wrap"] == "anywhere" and item["white-space"] == "normal"
    assert css[".compact-evidence .evidence-values"]["display"] == "flex"


def test_hostile_and_long_text_is_escaped_without_changing_navigation() -> None:
    report, verification = _fixture()
    report["limitations"] = ['<script>alert("x")</script> & ' + "x" * 4000]
    files = render(report, verification)
    _structural_oracle(files)
    (listing,) = DOM(files["index.html"]).root.nodes("ul", "major-limitations")
    assert listing.nodes("li")[0].text == report["limitations"][0]
    assert b"<script>" not in files["index.html"]


@pytest.mark.parametrize("value", ["not a list", [1], {"a": "text"}])
def test_invalid_limitation_structure_fails_closed(value: object) -> None:
    report, verification = _fixture()
    report["limitations"] = value
    with pytest.raises(ModelError):
        render(report, verification)


@pytest.mark.parametrize(
    "version,accepted",
    [
        ("1.4.0-historical-explorer.1", True),
        ("1.4.0-historical-explorer.2", True),
        ("1.5.0.dev1-historical-explorer.1", True),
        ("1.5.0.dev1-historical-explorer.2", False),
        ("forged", False),
    ],
)
def test_explicit_portable_renderer_version_matrix(
    inputs: tuple[dict[str, bytes], dict[str, Any]],
    tmp_path: Path,
    version: str,
    accepted: bool,
) -> None:
    files, identity = copy.deepcopy(inputs)
    identity["renderer_version"] = version
    output = tmp_path / "bundle"
    if accepted:
        result = bundle.publish(files, identity, output, before_publish=lambda: None)
        assert bundle.verify_bundle(output)["bundle_id"] == result["bundle_id"]
    else:
        with pytest.raises(ModelError):
            bundle.publish(files, identity, output, before_publish=lambda: None)


def test_unrelated_pages_and_overview_bytes_match_immutable_predecessor(tmp_path: Path) -> None:
    name = "v15_independent_old_renderer"
    path = tmp_path / "old_renderer.py"
    path.write_bytes(reference()["src/otarchguard/drift/explorer_render.py"])
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    old = importlib.util.module_from_spec(spec)
    sys.modules[name] = old
    try:
        spec.loader.exec_module(old)
        report, verification = _fixture()
        report["limitations"] = EXPECTED.copy()
        before, after = old.render(report, verification), render(report, verification)
    finally:
        sys.modules.pop(name, None)
    assert before.keys() == after.keys()
    for page in before:
        if not page.endswith(".html"):
            continue
        left = before[page].replace(
            b"1.4.0-historical-explorer.2", b"1.5.0.dev1-historical-explorer.1"
        )
        right = after[page]
        if page == "index.html":
            start = b"<h2>Major limitations</h2>"
            prefix, section = left.split(start)
            _, suffix = section.split(b"</ul></div>", 1)
            new_prefix, new_section = right.split(start)
            _, new_suffix = new_section.split(b"</ul>", 1)
            assert (prefix, suffix) == (new_prefix, new_suffix)
        else:
            assert left == right
