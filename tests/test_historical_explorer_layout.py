"""Independent structural/geometry contracts; these are not browser acceptance.

The old recursively shrinking grids and unconstrained finding tables must fail
these oracles. Width calculations deliberately model only the emitted layout
contract, not font shaping, painting, keyboard input or a browser's CSS engine.
"""

import copy
import hashlib
import math
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any

import pytest
from test_historical_explorer_render import _fixture, _source, _structural_oracle

from otarchguard.drift.explorer_render import PROTOCOLS, render


@dataclass
class Element:
    tag: str
    attrs: dict[str, str | None] = field(default_factory=dict)
    children: list["Element | str"] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "".join(n if isinstance(n, str) else n.text for n in self.children)

    def nodes(self, tag: str, classname: str = "") -> list["Element"]:
        result = []
        for node in self.children:
            if isinstance(node, Element):
                if node.tag == tag and (
                    not classname or classname in str(node.attrs.get("class", "")).split()
                ):
                    result.append(node)
                result.extend(node.nodes(tag, classname))
        return result


class DOM(HTMLParser):
    def __init__(self, raw: bytes) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Element("root")
        self.stack = [self.root]
        self.feed(raw.decode("utf-8"))
        self.close()
        assert len(self.stack) == 1

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = Element(tag, dict(attrs))
        self.stack[-1].children.append(node)
        if tag not in {"meta", "link", "hr", "br"}:
            self.stack.append(node)

    def handle_endtag(self, tag: str) -> None:
        assert self.stack[-1].tag == tag
        self.stack.pop()

    def handle_data(self, data: str) -> None:
        self.stack[-1].children.append(data)


def rules(css: str, viewport: float, *, print_mode: bool = False) -> dict[str, dict[str, str]]:
    """Read our finite stylesheet's blocks and media cascade independently."""
    result: dict[str, dict[str, str]] = {}

    def visit(text: str) -> None:
        while "{" in text:
            head, tail = text.split("{", 1)
            depth, end = 1, 0
            while depth:
                if tail[end] == "{":
                    depth += 1
                elif tail[end] == "}":
                    depth -= 1
                end += 1
            body, text = tail[: end - 1], tail[end:]
            head = head.strip()
            if head.startswith("@media"):
                maximum = re.fullmatch(r"@media\(max-width:(\d+)px\)", head)
                if maximum and not print_mode and viewport <= int(maximum[1]):
                    visit(body)
                elif head == "@media print" and print_mode:
                    visit(body)
            else:
                declarations = dict(
                    (key.strip(), value.strip())
                    for item in body.split(";")
                    if ":" in item
                    for key, value in [item.split(":", 1)]
                )
                for selector in head.split(","):
                    result.setdefault(selector.strip(), {}).update(declarations)

    visit(css)
    return result


def rem(value: str) -> float:
    assert re.fullmatch(r"[\d.]+rem", value)
    return float(value[:-3]) * 16


def panel_contract(css: str, viewport: int, zoom: int = 1) -> tuple[int, float]:
    width = viewport / zoom
    cascade = rules(css, width)
    grid = cascade[".compare"]
    fit = re.fullmatch(
        r"repeat\(auto-fit,minmax\(min\(100%,([\d.]+rem)\),1fr\)\)", grid["grid-template-columns"]
    )
    assert fit is not None, "Comparison must reserve readable width before adding a second panel"
    # The shared selector is expanded into individual selectors by the parser.
    container = min(width, rem(cascade["main"]["max-width"]))
    padding = cascade["main"]["padding"].split()
    inset = rem(padding[0]) if len(padding) == 1 else container * float(padding[1][:-1]) / 100
    record_inset = rem(cascade[".record"]["padding"])
    available = container - 2 * inset - 2 * record_inset - 2
    gap = rem(grid["gap"])
    columns = min(2, max(1, math.floor((available + gap) / (rem(fit[1]) + gap))))
    inner = (available - (columns - 1) * gap) / columns
    inner -= 2 * rem(cascade[".compare>section"]["padding"]) + 2
    assert inner > 0
    return columns, inner


def retained_contract(node: Element, css: str, width: float) -> None:
    cascade = rules(css, width)
    groups = node.nodes("dl")
    assert groups
    for group in groups:
        assert group.attrs.get("class") == "retained-fields", (
            "Nested evidence uses a shrinking grid"
        )
        assert cascade[".retained-fields"]["display"] == "block"
        assert "grid-template-columns" not in cascade[".retained-fields"]
        children = [n for n in group.children if isinstance(n, Element)]
        assert len(children) % 2 == 0
        assert [n.tag for n in children] == ["dt", "dd"] * (len(children) // 2)
    assert cascade[".retained-fields>dd"]["margin"] == "0"
    assert not any("padding" in key for key in cascade[".retained-fields"])
    for sequence in node.nodes("ul", "retained-list"):
        assert sequence.attrs.get("role") == "list"
        assert cascade[".retained-list"]["padding"] == "0"
    assert cascade["code"]["overflow-wrap"] == "anywhere"
    assert cascade["dt"]["overflow-wrap"] == "break-word"


def table_contract(node: Element, css: str, viewport: int) -> None:
    cascade = rules(css, viewport)
    wrappers = node.nodes("div", "finding-table")
    assert wrappers, "Finding columns have no shared sizing contract"
    for wrapper in wrappers:
        (region,) = wrapper.nodes("div", "scroll")
        assert region.attrs.get("role") == "region" and region.attrs.get("tabindex") == "0"
        assert region.attrs.get("aria-label")
        (table,) = region.nodes("table")
        headers = table.nodes("th")
        assert [h.text for h in headers] == [
            "Finding and evidence",
            "Canonical category",
            "Comparability",
            "Meaning",
        ]
        assert all(h.attrs.get("scope") == "col" for h in headers)
        assert cascade[".finding-table table"]["table-layout"] == "fixed"
        reserved = [rem(cascade[f".finding-table th:nth-child({i})"]["width"]) for i in range(1, 4)]
        minimum = rem(cascade[".finding-table table"]["min-width"])
        assert reserved[0] >= 12 * 16 and reserved[2] >= 11 * 16
        assert minimum - sum(reserved) >= 14 * 16, "Meaning has no useful remaining width"
        assert cascade[".finding-table"]["max-width"] == "100%"
        assert cascade[".scroll"]["overflow"] == "auto"
        assert cascade[".scroll"]["max-width"] == "100%"
        for row in table.nodes("tbody")[0].nodes("tr"):
            cells = row.nodes("td")
            assert len(cells) == 4
            status = cells[2]
            assert status.text in {
                "COMPARABLE",
                "PARTIALLY_COMPARABLE",
                "INDETERMINATE",
                "INCOMPARABLE",
            }
            parts = status.nodes("span", "status-part")
            assert parts and "".join(p.text for p in parts) == status.text
            assert all(re.fullmatch(r"[A-Z]+_?", p.text) for p in parts)
            assert cascade[".status-part"]["display"] == "inline-block"


def deep_fixture(depth: int) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    report, verified = _fixture()
    leaf: dict[str, Any] = {
        "source_interface_states": [
            {
                "interface_id": "if-" + "a" * 64,
                "state": "SUPPORTED",
                "interval": {"start": 502, "end": 502},
            }
        ],
        "target_interface_states": [{"interface_id": "if-" + "b" * 64, "state": "INDETERMINATE"}],
        "diagnostics": [{"message": "A long retained diagnostic with readable words. " * 30}],
        "long_" + "label_" * 30: "f" * 64,
    }
    nested = leaf
    for _ in range(depth):
        nested = {"native_witness": nested}
    finding = report["comparisons"][0]["findings"][4]
    finding["reference"] = {"source": _source("a"), "assessment": nested}
    finding["candidate"] = {"source": _source("b"), "assessment": {"diagnostics": ["Short side"]}}
    return report, verified, leaf


@pytest.mark.parametrize("viewport,columns", [(1440, 2), (1024, 1), (768, 1), (390, 1), (375, 1)])
@pytest.mark.parametrize("depth", [1, 6, 16])
def test_native_nested_evidence_keeps_usable_width_and_all_values(
    viewport: int, columns: int, depth: int
) -> None:
    report, verified, leaf = deep_fixture(depth)
    original = copy.deepcopy(report)
    files = render(report, verified)
    css = files["style.css"].decode()
    page = DOM(files["native.html"]).root
    (record,) = page.nodes("section", "record")
    (comparison,) = record.nodes("div", "compare")
    panels = [n for n in comparison.children if isinstance(n, Element)]
    actual_columns, available = panel_contract(css, viewport)
    assert actual_columns == columns
    assert available >= 280, "Readable content width, independent of nested depth"
    assert len(panels) == 2
    for panel, char in zip(panels, ("a", "b"), strict=True):
        retained_contract(panel, css, available)
        aid = _source(char)["analysis_id"]
        assert aid in panel.text
        expected = "source-" + hashlib.sha256(aid.encode()).hexdigest() + ".html"
        assert any(a.attrs.get("href") == expected for a in panel.nodes("a"))
    assert leaf["diagnostics"][0]["message"] in panels[0].text
    assert "if-" + "a" * 64 in panels[0].text and "if-" + "b" * 64 in panels[0].text
    assert "Short side" in panels[1].text
    assert len(_structural_oracle(files)) == len([n for n in files if n.endswith(".html")])
    assert report == original


@pytest.mark.parametrize("viewport", [1440, 1024, 768, 390, 375])
def test_all_seven_protocol_tables_reserve_columns_and_retain_status(viewport: int) -> None:
    report, verified = _fixture()
    for i, finding in enumerate(report["comparisons"][0]["findings"][8:]):
        finding["subtype"] = "REFERENCE_ONLY_METADATA" if i % 2 else "CANDIDATE_ONLY_METADATA"
        finding["explanation"] = "Long explanatory text must not consume the finding column. " * 20
    files = render(report, verified)
    css = files["style.css"].decode()
    for family in PROTOCOLS:
        page = DOM(files["protocol-" + family.replace("_", "-") + ".html"]).root
        table_contract(page, css, viewport)
        (tbody,) = page.nodes("tbody")
        (row,) = tbody.nodes("tr")
        assert row.nodes("td")[2].text == "PARTIALLY_COMPARABLE"
        label = row.nodes("td")[0].text
        neutral = {"Reference only metadata", "Candidate only metadata"}
        if family == "modbus_tcp":
            assert label.split(" · #")[0] in neutral
            assert re.search(r" · #[0-9a-f]{12}$", label)
        else:
            assert label in neutral
    pages = _structural_oracle(files)
    ids = [value for p in pages.values() for value in p.ids if value.startswith("f-")]
    assert len(ids) == len(set(ids)) == 15


@pytest.mark.parametrize("viewport", [1440, 1024, 768])
def test_zoom_oriented_geometry_stacks_and_print_releases_minimums(viewport: int) -> None:
    report, verified, _ = deep_fixture(6)
    css = render(report, verified)["style.css"].decode()
    columns, width = panel_contract(css, viewport, zoom=2)
    assert columns == 1 and width >= 280
    printed = rules(css, viewport, print_mode=True)
    assert printed[".compare"]["display"] == "block"
    assert printed[".finding-table table"]["min-width"] == "0"
    assert (
        sum(float(printed[f".finding-table th:nth-child({i})"]["width"][:-1]) for i in range(1, 4))
        <= 70
    )


def test_original_failure_patterns_are_rejected_by_layout_oracles() -> None:
    report, verified, _ = deep_fixture(6)
    files = render(report, verified)
    css = files["style.css"].decode()
    broken = files["native.html"].replace(b'class="retained-fields"', b'class="properties"')
    with pytest.raises(AssertionError, match="shrinking grid"):
        retained_contract(DOM(broken).root, css, 300)
    broken = files["protocol-modbus-tcp.html"].replace(
        b'class="finding-table"', b'class="auto-table"'
    )
    with pytest.raises(AssertionError, match="no shared sizing"):
        table_contract(DOM(broken).root, css, 768)
