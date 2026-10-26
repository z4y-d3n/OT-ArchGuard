"""Readable summaries use actual evidence counts without modifying canonical records."""

import copy
import json
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import pytest

from otarchguard.capture.explorer import generate_site
from otarchguard.capture.reconciliation import CLASSIFICATIONS
from otarchguard.capture.views import (
    CLASSIFICATION_LABELS,
    INTERPRETATIONS,
    PORT_HINT_NOTICE,
    capture_metadata,
    coverage_view,
    interpretation,
    overview_summary,
    protocols_view,
)

FIXTURES = Path(__file__).parent / "fixtures" / "capture-contract-v2"


def evidence(case: str = "limited") -> tuple[dict[str, Any], dict[str, Any]]:
    directory = FIXTURES / case
    return (
        json.loads((directory / "observations.json").read_bytes()),
        json.loads((directory / "comparison.json").read_bytes()),
    )


class _Rows(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self.current: list[str] | None = None
        self.cell: str | None = None
        self.tags: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append(tag)
        if tag == "tr":
            self.current = []
        elif tag in {"th", "td"}:
            self.cell = ""

    def handle_data(self, data: str) -> None:
        if self.cell is not None:
            self.cell += data

    def handle_endtag(self, tag: str) -> None:
        if tag in {"th", "td"} and self.current is not None and self.cell is not None:
            self.current.append(self.cell)
            self.cell = None
        elif tag == "tr" and self.current is not None:
            self.rows.append(self.current)
            self.current = None


@pytest.mark.parametrize("case", ["supported", "limited"])
def test_overview_counts_match_canonical_records_and_keep_declarations_distinct(case: str) -> None:
    observations, comparison = evidence(case)
    html = overview_summary(observations, comparison)
    for label, value in (
        ("Total packet records", observations["coverage"]["packets"]),
        ("Observed addresses", len(observations["hosts"])),
        ("Directed aggregates", len(observations["flows"])),
        ("Bidirectional groups", len(observations["conversations"])),
        ("Model-comparison flow findings", len(comparison["findings"])),
        ("Declared services not observed", len(comparison["declared_services_not_observed"])),
    ):
        assert f"<dt>{label}</dt><dd>{value}</dd>" in html
    rows = _Rows()
    rows.feed(html)
    assert sum(int(row[1]) for row in rows.rows[1:] if row[2] == "Directed aggregates") == len(
        comparison["findings"]
    )
    assert sum(int(row[1]) for row in rows.rows[1:] if row[2] == "Declared services") == len(
        comparison["declared_services_not_observed"]
    )
    assert "established sessions" in html and "complete sensor visibility" in html


def test_unrequested_comparison_is_not_displayed_as_zero_findings() -> None:
    observations, _ = evidence()
    html = overview_summary(observations, None)
    assert "<dd>Not requested</dd>" in html
    assert "no finding count is inferred" in html
    assert "Comparison categories" not in html
    assert "Model comparison was not requested." in coverage_view(observations, None)


def test_protocol_rows_preserve_transport_specific_counts_and_hint_overlap() -> None:
    def hint(protocol: str, port: int) -> dict[str, object]:
        return {"protocol": protocol, "port": port, "level": "PORT_HINT"}

    flows = [
        {
            "transport": "tcp",
            "packets": 3,
            "protocol_hints": [hint("Modbus/TCP", 502), hint("S7comm", 102)],
        },
        {"transport": "tcp", "packets": 2, "protocol_hints": [hint("Modbus/TCP", 502)]},
        {"transport": "udp", "packets": 4, "protocol_hints": [hint("Modbus/TCP", 502)]},
        {"transport": "unknown", "packets": 1, "protocol_hints": []},
    ]
    html = protocols_view(flows)
    rows = _Rows()
    rows.feed(html)
    assert ["TCP", "5"] in rows.rows and ["UDP", "4"] in rows.rows
    assert ["Unknown", "1"] in rows.rows
    assert ["Modbus/TCP", "TCP", "502", "5", "PORT_HINT"] in rows.rows
    assert ["Modbus/TCP", "UDP", "502", "4", "PORT_HINT"] in rows.rows
    assert ["S7comm", "TCP", "102", "3", "PORT_HINT"] in rows.rows
    assert PORT_HINT_NOTICE in html and "sum may exceed the total packet count" in html
    assert "from an IP header" in html
    assert "{&quot;" not in html and "<pre>" not in html
    assert "No port associations were recorded." in protocols_view([])


def test_coverage_has_readable_empty_state_counts_and_visible_scope_limits() -> None:
    observations, comparison = evidence("supported")
    html = coverage_view(observations, comparison)
    for name in ("Decoded", "Unsupported", "Malformed", "Truncated", "Fragmented"):
        assert f"<dt>{name}</dt><dd>{observations['coverage'][name.lower()]}</dd>" in html
    assert "No additional capture-container limitations were recorded." in html
    assert "full sensor coverage or complete capture visibility" in html
    assert "Scoped to this finite capture" in html
    assert comparison["absence_scope"] in html
    assert "<details" not in html and "<pre>" not in html and "[]" not in html
    limited_observations, limited_comparison = evidence()
    limited = coverage_view(limited_observations, limited_comparison)
    assert "<dd>Suppressed</dd>" in limited
    assert "successful communication or physical sensor visibility" in limited


def test_capture_interfaces_and_full_hash_remain_available_without_raw_json() -> None:
    observations, _ = evidence()
    capture = observations["capture"]
    html = capture_metadata(capture)
    assert "Capture interfaces" in html
    assert f"<dt>File bytes</dt><dd>{capture['size_bytes']}</dd>" in html
    assert "<details" in html and capture["sha256"] in html
    assert capture["sha256"][:12] + "…" in html
    assert "interface-level snapshot limit; product budgets still apply" in html
    assert "<pre>" not in html and "{&quot;" not in html


def test_interpretations_cover_actual_codes_and_preserve_uncertainty() -> None:
    assert set(CLASSIFICATION_LABELS) == set(INTERPRETATIONS) == set(CLASSIFICATIONS)
    assert "does not prove deployed authorization" in interpretation("OBSERVED_MODEL_REACHABLE")
    assert "does not prove that a physical firewall denied" in interpretation(
        "OBSERVED_MODEL_UNREACHABLE"
    )
    assert "multiple declared interfaces or services" in interpretation("EVIDENCE_AMBIGUOUS")
    assert "unassessed" in interpretation("FUTURE_UNKNOWN_CODE")


def test_views_are_deterministic_escaped_and_do_not_modify_evidence() -> None:
    observations, comparison = evidence()
    observations["capture"]["format"] = "<script>bad()</script>"
    observations["limitations"] = [
        "<img src=x onerror=bad()> \u202eunsafe C:/Users/private/secret.txt"
    ]
    observations["flows"][0]["protocol_hints"] = [
        {"protocol": "<svg onload=bad()>", "port": 502, "level": "PORT_HINT"}
    ]
    comparison["findings"][0]["classification"] = "<script>future</script>"
    before = copy.deepcopy((observations, comparison))
    outputs = (
        overview_summary(observations, comparison),
        capture_metadata(observations["capture"]),
        protocols_view(observations["flows"]),
        coverage_view(observations, comparison),
    )
    assert (observations, comparison) == before
    assert outputs == (
        overview_summary(observations, comparison),
        capture_metadata(observations["capture"]),
        protocols_view(observations["flows"]),
        coverage_view(observations, comparison),
    )
    parser = _Rows()
    parser.feed("".join(outputs))
    assert not {"script", "img", "svg", "pre", "span", "time"} & set(parser.tags)
    assert "[U+202E]" in outputs[3] and "[local path withheld]" in outputs[3]
    assert "C:/Users/private" not in outputs[3]


def test_mapping_only_report_exposes_original_bindings_without_changing_json(
    tmp_path: Path,
) -> None:
    directory = FIXTURES / "supported"
    observation_bytes = (directory / "observations.json").read_bytes()
    mapping_bytes = (directory / "mapping.json").read_bytes()
    observations = json.loads(observation_bytes)
    mapping = json.loads(mapping_bytes)
    before = copy.deepcopy((observations, mapping))
    output = tmp_path / "mapping-only"
    report = generate_site(observations, output, mapping=mapping)
    assert report["status"] == "complete"
    html = (output / "associations.html").read_text(encoding="utf-8")
    assert "Evidence binding and original review record" in html
    for key in ("capture_sha256", "model_sha256", "observations_sha256"):
        assert mapping[key] in html
    assert (observations, mapping) == before
    assert (output / "observations.json").read_bytes() == observation_bytes
    assert (output / "mapping.json").read_bytes() == mapping_bytes
    assert not (output / "comparison.json").exists()
    assert "Model comparison was not requested" in (output / "findings.html").read_text(
        encoding="utf-8"
    )
