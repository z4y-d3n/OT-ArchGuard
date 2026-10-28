"""Product-wide presentation contracts over actual adapters, without browser claims."""

import copy
from collections.abc import Callable
from typing import Any

import pytest
from test_historical_explorer_layout import DOM, Element

from otarchguard.capture.display import render_value
from otarchguard.capture.explorer import _record_table
from otarchguard.diagnostics import ModelError
from otarchguard.drift.explorer_render import _value as historical_value
from otarchguard.explorer import Explorer
from otarchguard.explorer_html import SEMANTIC_CSS, escape, structured_value, table
from otarchguard.reporting import _field_values, _table
from otarchguard.review_explorer import _value as review_value


def architecture_value(value: object) -> str:
    renderer = object.__new__(Explorer)
    renderer.native_paths = {}
    return renderer.value(value)


ADAPTERS: tuple[Callable[[object], str], ...] = (
    architecture_value,
    render_value,
    historical_value,
    review_value,
    _field_values,
)


def structure(root: Element) -> None:
    for node in root.nodes("table"):
        assert not node.nodes("table"), "A nested table competes for cell width"
        assert node.nodes("caption")[0].text
        assert node.nodes("thead") and node.nodes("tbody")
        assert all(h.attrs.get("scope") == "col" for h in node.nodes("thead")[0].nodes("th"))
        assert all(h.attrs.get("scope") == "row" for h in node.nodes("tbody")[0].nodes("th"))
    assert all(not node.nodes("dl") for node in root.nodes("dl"))
    assert all(not node.nodes("ul") for node in root.nodes("ul"))
    assert not root.nodes("script") and not root.nodes("img")


@pytest.mark.parametrize("adapter", ADAPTERS)
@pytest.mark.parametrize("depth", [1, 3, 8, 24])
def test_deep_records_keep_context_and_every_leaf_without_visual_nesting(
    adapter: Callable[[object], str],
    depth: int,
) -> None:
    value: Any = {"identity": "f" * 64, "hostile": '</td><script>"&unsafe</script>'}
    for i in range(depth):
        value = {"level_" + str(i): [{"ordinal": i, "retained": value}]}
    original = copy.deepcopy(value)
    raw = adapter(value)
    root = DOM(raw.encode()).root
    structure(root)
    assert value == original and raw == adapter(value)
    assert "f" * 64 in root.text and '</td><script>"&unsafe</script>' in root.text
    assert len(root.nodes("table")) == depth
    assert "Record 1" in root.nodes("h4")[-1].text
    assert len(raw) < 400_000


@pytest.mark.parametrize("adapter", ADAPTERS)
def test_uniform_records_keep_duplicates_order_and_readable_column_groups(
    adapter: Callable[[object], str],
) -> None:
    values = [{f"counter_{key}": row * 100 + key for key in range(17)} for row in range(100)]
    values[1] = dict(values[0])  # Equal records are still distinct retained records.
    before = copy.deepcopy(values)
    root = DOM(adapter(values).encode()).root
    structure(root)
    assert len(root.nodes("table")) == 3
    for node in root.nodes("table"):
        assert len(node.nodes("thead")[0].nodes("th")) <= 7
        assert len(node.nodes("tbody")[0].nodes("tr")) == 100
        assert [h.text for h in node.nodes("tbody")[0].nodes("th")] == [
            str(i) for i in range(1, 101)
        ]
    assert values == before


@pytest.mark.parametrize("adapter", ADAPTERS)
def test_heterogeneous_nested_lists_empty_missing_false_and_quotes_are_distinct(
    adapter: Callable[[object], str],
) -> None:
    data = {
        "identities": ["same", "same"],
        "mixed": [{"only_a": "alpha"}, {"only_b": "beta"}],
        "nested": [["first", "second"], ["third"]],
        "empty_map": {},
        "empty_list": [],
        "missing": None,
        "zero": 0,
        "false": False,
        "text": 'long [label] "&" ' + "界" * 3500,
    }
    root = DOM(adapter(data).encode()).root
    structure(root)
    assert root.text.count("same") == 2
    assert all(
        text in root.text
        for text in ("alpha", "beta", "first", "second", "third", "{}", "界" * 3500)
    )
    assert root.text.index("first") < root.text.index("second") < root.text.index("third")
    assert len(root.nodes("dt")) == len(root.nodes("dd"))


@pytest.mark.parametrize("adapter", ADAPTERS)
def test_witness_step_numbers_and_endpoint_context_follow_input_order(
    adapter: Callable[[object], str],
) -> None:
    data = {
        "steps": [
            {"edge_id": "z_first", "source": {"asset_id": "A", "state": {"interface_id": "if_A"}}},
            {"edge_id": "a_second", "source": {"asset_id": "B", "state": {"interface_id": "if_B"}}},
        ]
    }
    root = DOM(adapter(data).encode()).root
    structure(root)
    (steps,) = root.nodes("table")
    assert "Ordered witness steps" in steps.nodes("caption")[0].text
    assert [cell.text for cell in steps.nodes("td")] == ["z_first", "a_second"]
    headings = [node.text for node in root.nodes("h4")]
    assert any("Step 1" in h and "State" in h for h in headings)
    assert any("Step 2" in h and "State" in h for h in headings)


def test_existing_html_table_consumers_lift_complex_values_out_of_cells() -> None:
    nested = structured_value([{"edge": "one"}, {"edge": "two"}], lambda v, _: escape(v))
    raw = table("Outer comparison", ("Identity", "Evidence"), [("model A", nested)])
    root = DOM(raw.encode()).root
    structure(root)
    assert all(not node.nodes("table") for node in root.nodes("td"))
    assert "model A" in root.text and "one" in root.text and "two" in root.text


def test_pcap_record_table_preserves_original_row_anchors_and_all_evidence() -> None:
    records: list[tuple[str, tuple[str, ...]]] = [
        (
            "association-one",
            ("192.0.2.1", render_value({"reviewer": "Owner", "state": "accepted"})),
        ),
        ("association-two", ("192.0.2.2", render_value({"reviewer": "Other", "state": "pending"}))),
    ]
    root = DOM(_record_table("Reviewed associations", ("Address", "Review"), records).encode()).root
    structure(root)
    assert [r.attrs.get("id") for r in root.nodes("tr") if "id" in r.attrs] == [
        "association-one",
        "association-two",
    ]
    assert all(not node.nodes("dl") for node in root.nodes("td"))
    assert "Owner" in root.text and "Other" in root.text


def test_native_global_diagnostic_is_separate_from_each_blocked_edge() -> None:
    data = [
        {
            "reason": "NO_PERMITTED_PATH",
            "structural_path_exists": True,
            "blocked_edge_count": 9,
            "truncated": True,
            "limitation": "Bounded frontier only",
            "blocked_edges": [
                {"edge_id": "e1", "reason": "MISSING_PERMIT"},
                {"edge_id": "e2", "reason": "EXPLICIT_DENY"},
            ],
        }
    ]
    root = DOM(_table("Bounded diagnostic", data).encode()).root
    structure(root)
    assert len(root.nodes("table")) == 2
    assert "NO_PERMITTED_PATH" in root.nodes("table")[0].text
    assert "MISSING_PERMIT" in root.nodes("table")[1].text
    assert "EXPLICIT_DENY" in root.nodes("table")[1].text
    assert "9" in root.text and "Bounded frontier only" in root.text


def test_shared_styles_make_real_tables_focusable_scrollable_and_printable() -> None:
    raw = _table("Wide retained records", [{"hash": "b" * 64, "message": "long " * 300}])
    root = DOM(raw.encode()).root
    region = root.nodes("div", "scroll")[0]
    assert region.attrs.get("tabindex") == "0" and region.attrs.get("role") == "region"
    assert region.attrs.get("aria-label")
    assert "overflow:auto;max-width:100%" in SEMANTIC_CSS
    assert "min-width:8ch" in SEMANTIC_CSS and "table-header-group" in SEMANTIC_CSS


@pytest.mark.parametrize("adapter", ADAPTERS)
@pytest.mark.parametrize("key", ["x" * 4096, "sha256_" * 585])
def test_valid_source_key_limit_is_not_reapplied_to_derived_labels(
    adapter: Callable[[object], str],
    key: str,
) -> None:
    root = DOM(adapter([{key: {"field": "retained"}}]).encode()).root
    assert "retained" in root.text
    structure(root)


@pytest.mark.parametrize("adapter", ADAPTERS)
def test_labels_validate_original_keys_before_humanizing_or_minimizing(
    adapter: Callable[[object], str],
) -> None:
    with pytest.raises(ModelError):
        adapter({"_" * 5000: "over limit"})
    root = DOM(adapter({"C:/Users/private_secret.txt": "retained"}).encode()).root
    assert "private" not in root.text and "secret" not in root.text
    assert "[local path withheld]" in root.text and "retained" in root.text
