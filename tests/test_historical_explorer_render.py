"""Independent finite UI fixtures, navigation oracles and deliberate layout failures."""

import copy
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import pytest

from otarchguard.diagnostics import ModelError
from otarchguard.drift import explorer_render
from otarchguard.drift.explorer_render import CSS, PROTOCOLS, render


def _source(char: str) -> dict[str, Any]:
    return {
        "analysis_id": "analysis-" + char * 64,
        "snapshot_id": "snapshot-" + char * 64,
        "capture_sha256": char * 64,
        "observations_sha256": "c" * 64,
        "producer_semantics_sha256": "d" * 64,
        "attachments": {"model": "attachment-" + char * 64},
    }


def _finding(subtype: str, category: str = "OBSERVED_COMMUNICATION_DIFFERENCE") -> dict[str, Any]:
    return {
        "category": category,
        "subtype": subtype,
        "key": {
            "source_ip": "2001:db8:1111:2222:3333:4444:5555:6666",
            "destination_ip": "192.0.2.20",
            "transport": "tcp",
            "source_port": 41000,
            "destination_port": 502,
            "vlans": [12],
        },
        "reference": {
            "source": _source("a"),
            "metadata": {"packets": 7, "status_packet_counts": {"decoded": 7}},
            "packet_references": [{"flow_id": "flow-123", "packet": {"index": 4, "offset": 200}}],
            "packet_references_omitted": 6,
        },
        "candidate": {"source": _source("b"), "metadata": {"packets": 9}},
        "comparability": "PARTIALLY_COMPARABLE",
        "explanation": "A finite supported observation difference.",
        "limitations": ["Missing observations do not prove blocking."],
        "unsupported_interpretations": ["No operational absence is established."],
    }


def _fixture() -> tuple[dict[str, Any], dict[str, Any]]:
    findings = [
        _finding("REFERENCE_ONLY_OBSERVATION"),
        _finding("CANDIDATE_ONLY_OBSERVATION"),
        _finding("OBSERVED_IN_BOTH"),
        _finding("DECLARED_OBJECT_CHANGED", "DECLARED_ARCHITECTURE_CHANGE"),
        _finding("REACHABILITY_CHANGED", "NATIVE_ASSESSMENT_DIFFERENCE"),
        _finding("CAPTURE_COVERAGE_CHANGED", "COVERAGE_DIFFERENCE"),
        _finding("PROTOCOL_SEMANTICS_CHANGED", "ANALYTICAL_INTERPRETATION_DIFFERENCE"),
        _finding("UNALIGNED_COLLECTION", "INDETERMINATE_COMPARISON"),
    ]
    findings[0]["candidate"] = None
    findings[1]["reference"] = None
    findings[-1]["comparability"] = "INDETERMINATE"
    for family in PROTOCOLS:
        finding = _finding("CANDIDATE_ONLY_METADATA", "PROTOCOL_METADATA_DIFFERENCE")
        finding["key"].update(protocol=family, status="recognized", recognition_method="structural")
        findings.append(finding)
    scope = {
        "environment": "Fictional training segment",
        "purpose": "Finite evidence review",
        "coverage": "Selected files",
        "uncertainties": ["Sensor authenticity unknown"],
        "vantage_points": ["Declared mirror"],
        "protocols": ["modbus_tcp"],
    }
    assessment = {
        "overall": "INDETERMINATE",
        "communication_metadata": "PARTIALLY_COMPARABLE",
        "protocol_metadata": "PARTIALLY_COMPARABLE",
        "asset_continuity": "INDETERMINATE",
        "temporal_order": "OVERLAPPING_WINDOWS",
        "independent_collections": True,
        "limitations": ["Clock synchronization unknown"],
        "dimensions": [
            {
                "dimension": "packet_interpretation",
                "result": "PARTIALLY_COMPARABLE",
                "source_evidence": {
                    "sources": [_source("a"), _source("b")],
                    "values": [{"packets": 7}, {"packets": 9}],
                },
                "reason": "Uninterpreted packets remain.",
                "consequence": "No absence conclusion is supported.",
            }
        ],
    }
    report = {
        "drift_version": 1,
        "engine_version": "1.4.0-drift.1",
        "comparability_policy_version": 1,
        "implementation_sha256": {"drift/engine.py": "f" * 64},
        "drift_id": "drift-" + "f" * 64,
        "inputs": {
            "baseline": {"baseline_id": "baseline-" + "e" * 64, "scope": scope},
            "approval": {
                "review_id": "review-" + "e" * 64,
                "reviewer": "Fictional reviewer",
                "rationale": "Declared finite reference",
            },
            "review_frontier": ["review-" + "e" * 64],
            "reference_sources": [_source("a")],
            "candidate_sources": [_source("b")],
            "selected_models": None,
            "workspace_manifest_sha256": "0" * 64,
        },
        "options": {
            "mode": "qualified",
            "context": {
                "pairs": [
                    {
                        "reference_analysis_id": _source("a")["analysis_id"],
                        "candidate_analysis_id": _source("b")["analysis_id"],
                        "alignment": "asserted",
                        "rationale": "Fictional same segment",
                        "candidate_scope": scope,
                        "native_queries": [],
                    }
                ]
            },
        },
        "comparisons": [
            {
                "reference_analysis_id": _source("a")["analysis_id"],
                "candidate_analysis_id": _source("b")["analysis_id"],
                "comparability": assessment,
                "findings": findings,
            }
        ],
        "unaligned_findings": [],
        "architecture_findings": [],
        "summary": {
            "categories": {
                "OBSERVED_COMMUNICATION_DIFFERENCE": 3,
                "DECLARED_ARCHITECTURE_CHANGE": 1,
                "NATIVE_ASSESSMENT_DIFFERENCE": 1,
                "COVERAGE_DIFFERENCE": 1,
                "ANALYTICAL_INTERPRETATION_DIFFERENCE": 1,
                "INDETERMINATE_COMPARISON": 1,
                "PROTOCOL_METADATA_DIFFERENCE": 7,
            },
            "difference_records": 13,
            "unchanged_support_records": 1,
            "abstentions": 1,
            "findings": 15,
            "distinct_physical_collections": 2,
            "interpretation": "Qualified finite evidence differences.",
        },
        "limitations": ["No incidents or operational safety conclusions are determined."],
        "reproduction": "Revalidate source dependencies and replay the historical frontier.",
    }
    verification = {
        "status": "REPRODUCIBLE_HISTORICAL_REPORT",
        "recorded_baseline_status": "APPROVED",
        "current_baseline_status": "REVOKED",
        "canonical_reproduction": True,
        "currently_approved_reference": False,
    }
    return report, verification


class _Page(HTMLParser):
    def __init__(self, raw: bytes) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: set[str] = set()
        self.hrefs: list[str] = []
        self.tags: list[str] = []
        self.headers = 0
        self.main = 0
        self.h1 = 0
        self.skip = False
        self.text = ""
        self.feed(raw.decode("utf-8"))
        self.close()

    def handle_data(self, data: str) -> None:
        self.text += data

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        self.tags.append(tag)
        assert tag not in {"script", "iframe", "img", "foreignobject", "form"}
        assert not any(k.startswith("on") or k in {"style", "src"} for k in values)
        if "id" in values:
            identity = str(values["id"])
            assert identity not in self.ids
            self.ids.add(identity)
        if tag == "a":
            href = str(values["href"])
            assert re.fullmatch(r"[a-z0-9-]+\.(?:html|css)(?:#[a-z0-9-]+)?|#[a-z0-9-]+", href)
            self.hrefs.append(href)
            self.skip |= href == "#main" and values.get("class") == "skip"
        if tag == "main":
            self.main += 1
        if tag == "h1":
            self.h1 += 1
        if tag == "th":
            assert values.get("scope") in {"col", "row"}
            self.headers += 1
        if tag == "div" and values.get("class") == "scroll":
            assert values.get("role") == "region"
            assert values.get("tabindex") == "0"
            assert values.get("aria-label")


def _structural_oracle(files: dict[str, bytes]) -> dict[str, _Page]:
    pages = {name: _Page(raw) for name, raw in files.items() if name.endswith(".html")}
    for name, page in pages.items():
        assert page.main == page.h1 == 1, name
        assert page.skip, name
        assert {"html", "head", "body", "title", "nav", "footer"} <= set(page.tags)
        for href in page.hrefs:
            target, _, fragment = href.partition("#")
            target = target or name
            assert target in files, (name, href)
            if fragment:
                assert fragment in pages[target].ids, (name, href)
    return pages


def test_complete_navigation_and_semantic_counts() -> None:
    report, verification = _fixture()
    files = render(report, verification, page_size=5)
    pages = _structural_oracle(files)
    overview = files["index.html"].decode()
    assert '<span class="metric">13</span>' in overview
    assert '<span class="metric">1</span>' in overview
    assert "REVOKED" in overview and "APPROVED" in overview
    assert "INDETERMINATE" in pages["index.html"].text
    assert "PARTIALLY_COMPARABLE" in pages["index.html"].text
    all_ids = [
        identity for page in pages.values() for identity in page.ids if identity.startswith("f-")
    ]
    assert len(all_ids) == len(set(all_ids)) == 15
    assert b"flow-123" in files["communications.html"]
    assert b"Packet references omitted" in files["communications.html"]
    assert b"Back to domain" in files["communications.html"]
    assert b"Pair 1 context" in files["communications.html"]
    assert b"Related retained records" in files["communications.html"]
    assert b"does not establish physical device continuity" in files["communications.html"]
    assert b"No operational absence" in files["communications.html"]
    assert b"REACHABILITY_CHANGED" not in files["abstentions.html"]
    for family, label in PROTOCOLS.items():
        name = "protocol-" + family.replace("_", "-") + ".html"
        assert name in files
        assert label.encode() in files[name]
    assert b"2001:db8:1111:2222:3333:4444:5555:6666" in files["communications.html"]
    assert _source("a")["analysis_id"].encode() in files["communications.html"]


def test_deterministic_rendering_and_page_size_preserves_all_records() -> None:
    report, verification = _fixture()
    first = render(report, verification, page_size=5)
    assert first == render(copy.deepcopy(report), copy.deepcopy(verification), page_size=5)
    second = render(report, verification, page_size=200)
    first_ids = {
        identity
        for p in _structural_oracle(first).values()
        for identity in p.ids
        if identity.startswith("f-")
    }
    second_ids = {
        identity
        for p in _structural_oracle(second).values()
        for identity in p.ids
        if identity.startswith("f-")
    }
    assert first_ids == second_ids and len(first_ids) == 15
    assert b"Records 1\xe2\x80\x935 of 7" in first["protocols.html"]
    assert b"Page 2 of 2" in first["protocols-2.html"]


def test_dense_diagram_omission_preserves_every_finding() -> None:
    report, verification = _fixture()
    report["comparisons"][0]["findings"] = [
        _finding("CANDIDATE_ONLY_OBSERVATION") for _ in range(73)
    ]
    report["summary"].update(
        difference_records=73,
        unchanged_support_records=0,
        abstentions=0,
        findings=73,
        categories={"OBSERVED_COMMUNICATION_DIFFERENCE": 73},
    )
    files = render(report, verification, page_size=5)
    pages = _structural_oracle(files)
    assert b"diagram omitted" in files["communications.html"]
    assert b"Complete paginated records remain below" in files["communications.html"]
    assert b"<svg" not in files["communications.html"]
    assert "communications-15.html" in files
    assert sum(identity.startswith("f-") for p in pages.values() for identity in p.ids) == 73
    assert b"Records 71\xe2\x80\x9373 of 73" in files["communications-15.html"]
    assert b"Preview of 8 of 72 related records" in files["communications.html"]
    assert b"The related-record preview is incomplete" in files["communications.html"]


def test_actual_small_diagram_has_accessible_lanes_and_record_links() -> None:
    report, verification = _fixture()
    files = render(report, verification)
    page = files["communications.html"].decode()
    assert 'aria-labelledby="communication-title communication-desc"' in page
    assert "Reference only" in page and "Candidate only" in page and "Common relationship" in page
    assert page.count('marker-end="url(#direction-arrow)"') == 3
    assert "<figcaption>" in page and "</figure>" in page
    assert "M 305 50 L 595 50" in page and "M 305 136 L 595 136" in page
    _structural_oracle(files)


def test_narrow_diagram_retains_readable_scale_inside_labeled_scroll_region() -> None:
    report, verification = _fixture()
    files = render(report, verification)
    page, css = files["communications.html"].decode(), files["style.css"].decode()
    assert (
        '<div class="scroll diagram-scroll" tabindex="0" role="region" '
        'aria-label="Observed communication diagram; scroll horizontally for complete '
        'relationships">'
        '<svg viewBox="0 0 900 '
    ) in page
    assert "</svg></div><figcaption>On narrow screens, focus the diagram region" in page
    rule = re.search(r"\.diagram-scroll svg\{([^}]+)\}", css)
    assert rule is not None
    minimum = re.search(r"min-width:(\d+)px", rule[1])
    assert minimum is not None
    # The 900-unit drawing uses 14-unit labels. At a 375px viewport it must
    # retain at least 14px labels, while the outer .scroll region owns overflow.
    drawing_width = max(375 - 32, int(minimum[1]))
    assert drawing_width / 900 * 14 >= 14
    assert "max-width:none" in rule[1]
    assert ".scroll{overflow:auto;max-width:100%" in css
    assert ".diagram-scroll svg{min-width:0;width:100%;max-width:100%}" in css
    _structural_oracle(files)


def test_untrusted_text_stays_text_and_paths_bidi_are_visible() -> None:
    report, verification = _fixture()
    report["inputs"]["approval"]["rationale"] = (
        '<script>alert(1)</script><svg onload="x"><foreignObject>bad</foreignObject></svg> '
        "javascript:evil data:bad file:///private/evidence C:\\Users\\owner\\capture.pcap "
        "\u202ehidden"
    )
    files = render(report, verification)
    evidence = files["evidence.html"].decode()
    assert "&lt;script&gt;" in evidence and "&lt;foreignObject&gt;" in evidence
    assert "<script>" not in evidence and "<foreignObject>" not in evidence
    assert "[local path withheld]" in evidence and "C:\\Users" not in evidence
    assert "[U+202E]hidden" in evidence and "\u202e" not in evidence
    _structural_oracle(files)


@pytest.mark.parametrize("value", ["bad\x00text", "bad\x7ftext", "bad\ud800text", "x" * 4097])
def test_invalid_display_text_fails_closed(value: str) -> None:
    report, verification = _fixture()
    report["inputs"]["approval"]["rationale"] = value
    with pytest.raises(ModelError):
        render(report, verification)


@pytest.mark.parametrize("size", [True, 0, 4, 201, "50"])
def test_display_options_are_bounded(size: Any) -> None:
    report, verification = _fixture()
    with pytest.raises(ModelError):
        render(report, verification, page_size=size)


def test_static_accessibility_regression_oracle_detects_actual_defect() -> None:
    report, verification = _fixture()
    files = render(report, verification)
    _structural_oracle(files)
    files["index.html"] = files["index.html"].replace(
        b'<a class="skip" href="#main">Skip to main content</a>', b""
    )
    with pytest.raises(AssertionError):
        _structural_oracle(files)


def test_css_responsive_focus_contrast_and_print_contract() -> None:
    assert "outline:3px solid #8c4300" in CSS
    assert "@media(max-width:700px)" in CSS and "@media(max-width:480px)" in CSS
    assert "grid-template-columns:minmax(0,1fr)" in CSS
    assert "overflow-wrap:anywhere" in CSS and "@media print" in CSS
    assert "url(" not in CSS and "@import" not in CSS

    # WCAG relative luminance, using literal documented foreground/background colors.
    def luminance(rgb: tuple[int, int, int]) -> float:
        channels = [v / 255 for v in rgb]
        linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in channels]
        return sum(v * weight for v, weight in zip(linear, (0.2126, 0.7152, 0.0722), strict=True))

    foreground = luminance((0x18, 0x2C, 0x3B))
    background = luminance((0xF2, 0xF5, 0xF7))
    assert (background + 0.05) / (foreground + 0.05) > 7


def test_empty_domain_has_honest_explanation_without_empty_diagram() -> None:
    report, verification = _fixture()
    report["comparisons"][0]["findings"] = []
    report["summary"].update(
        difference_records=0, unchanged_support_records=0, abstentions=0, findings=0, categories={}
    )
    files = render(report, verification)
    _structural_oracle(files)
    assert b"<svg" not in files["communications.html"]
    assert b"does not establish operational safety" in files["communications.html"]
    assert b"None in this view" in files["communications.html"]


@pytest.mark.parametrize(
    "field",
    ["findings", "difference_records", "unchanged_support_records", "abstentions", "categories"],
)
def test_summary_mismatch_fails_instead_of_publishing_miscounted_ui(field: str) -> None:
    report, verification = _fixture()
    report["summary"][field] = {} if field == "categories" else 200
    with pytest.raises(ModelError, match="Architecture processing failed"):
        render(report, verification)


@pytest.mark.parametrize("limit", ["MAX_PAGES", "MAX_PAGE_BYTES", "MAX_RENDERED_BYTES"])
def test_incremental_rendering_budget_fails_closed(
    limit: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    report, verification = _fixture()
    monkeypatch.setattr(explorer_render, limit, 1)
    with pytest.raises(ModelError):
        render(report, verification)


class _FindingLinks(HTMLParser):
    """Read first-column link text independently of the production label helper."""

    def __init__(self, page: bytes) -> None:
        super().__init__(convert_charrefs=True)
        self.labels: list[tuple[str, str]] = []
        self.cell = 0
        self.href: str | None = None
        self.value = ""
        self.feed(page.decode())

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self.cell = 0
        elif tag == "td":
            self.cell += 1
        elif tag == "a" and self.cell == 1:
            self.href = dict(attrs).get("href")
            self.value = ""

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self.href is not None:
            self.labels.append((self.href, self.value))
            self.href = None
        elif tag == "table":
            self.cell = 0

    def handle_data(self, data: str) -> None:
        if self.href is not None:
            self.value += data


def _modbus_key() -> dict[str, Any]:
    return {
        "protocol": "modbus_tcp",
        "status": "STRUCTURALLY_VALID",
        "recognition_method": "HEADER_STRUCTURE",
        "message_category": "read_type",
        "header_metadata": {"function_code": 3, "unit_id": 1},
        "endpoint_scope": "OBSERVED_IP_HEADER",
        "source_ip": "192.0.2.10",
        "destination_ip": "192.0.2.20",
    }


def test_four_canonical_modbus_findings_have_distinct_supported_labels(tmp_path: Path) -> None:
    from otarchguard.drift.engine import compare
    from otarchguard.drift.reports import verify_report
    from tools.drift_walkthrough import canonical, comparison_context, prepare

    selected = prepare(tmp_path / "fictional", variations=False)
    workspace = Path(selected["workspace"])
    reference = selected["periods"]["reference"]["analysis_id"]
    candidate = selected["periods"]["candidate"]["analysis_id"]
    report = compare(
        workspace,
        selected["baseline_id"],
        [candidate],
        comparison_context(reference, candidate, selected["scope"]),
    )
    original = canonical(report)
    path = tmp_path / "drift.json"
    path.write_bytes(original)
    verified = verify_report(workspace, path)
    files = render(report, verified)
    links = _FindingLinks(files["protocol-modbus-tcp.html"]).labels
    assert [label for _, label in links] == [
        "Reference only · FC03 Read-type · 192.0.2.10 → 192.0.2.20",
        "Reference only · FC03 Read-type · 192.0.2.11 → 192.0.2.20",
        "Candidate only · FC03 Read-type · 192.0.2.99 → 192.0.2.20",
        "Candidate only · FC06 Write-type · 192.0.2.11 → 192.0.2.20",
    ]
    assert len({label for _, label in links}) == len({href for href, _ in links}) == 4
    pages = _structural_oracle(files)
    identities = [
        identity for page in pages.values() for identity in page.ids if identity.startswith("f-")
    ]
    assert len(identities) == len(set(identities)) == 14
    assert canonical(report) == path.read_bytes() == original
    assert all(href.partition("#")[2] in pages["protocols.html"].ids for href, _ in links)
    assert (
        b"Write-type function metadata does not prove successful command execution."
        in (files["protocols.html"])
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"header_metadata": None},
        {"header_metadata": {"function_code": True}},
        {"header_metadata": {"function_code": -1}},
        {"header_metadata": {"function_code": 256}},
        {"message_category": "executed_write"},
        {"message_category": []},
        {"status": "PORT_HINT"},
        {"status": "UNSUPPORTED_VARIANT"},
        {"status": "TRUNCATED"},
        {"status": "MALFORMED"},
        {"recognition_method": "PORT_ASSOCIATION"},
    ],
)
def test_missing_or_unsupported_modbus_metadata_stays_neutral(changes: dict[str, Any]) -> None:
    report, verified = _fixture()
    finding = report["comparisons"][0]["findings"][8]
    finding.update(subtype="REFERENCE_ONLY_METADATA", key=_modbus_key() | changes)
    files = render(report, verified)
    (link,) = _FindingLinks(files["protocol-modbus-tcp.html"]).labels
    assert re.fullmatch(r"Reference only metadata · #[0-9a-f]{12}", link[1])
    assert link[1].endswith("#" + link[0].split("#f-")[1][:12])
    assert files == render(copy.deepcopy(report), copy.deepcopy(verified))


@pytest.mark.parametrize(
    "endpoint", [None, "javascript:evil", "<script>x</script>", "fe80::1%eth0"]
)
def test_missing_ip_context_uses_short_id_without_invented_direction(endpoint: object) -> None:
    report, verified = _fixture()
    finding = report["comparisons"][0]["findings"][8]
    finding["key"] = _modbus_key() | {"destination_ip": endpoint}
    files = render(report, verified)
    ((_, label),) = _FindingLinks(files["protocol-modbus-tcp.html"]).labels
    assert re.fullmatch(r"Candidate only · FC03 Read-type · #[0-9a-f]{12}", label)
    assert "→" not in label
    _structural_oracle(files)


def test_identical_descriptions_use_existing_ids_and_other_families_stay_unchanged() -> None:
    report, verified = _fixture()
    findings = report["comparisons"][0]["findings"]
    for i, finding in enumerate(findings[8:10]):
        finding["key"] = _modbus_key()
        finding["key"]["header_metadata"]["unit_id"] = i + 1
    files = render(report, verified)
    labels = _FindingLinks(files["protocol-modbus-tcp.html"]).labels
    assert len({label for _, label in labels}) == 2
    for href, label in labels:
        assert re.fullmatch(
            r"Candidate only · FC03 Read-type · 192.0.2.10 → 192.0.2.20 · #[0-9a-f]{12}", label
        )
        assert label.endswith("#" + href.split("#f-")[1][:12])
    baseline_report, baseline_verified = _fixture()
    baseline = render(baseline_report, baseline_verified)
    for family in ("ethernet_ip", "s7comm", "iec104", "opcua_binary", "dnp3"):
        name = "protocol-" + family.replace("_", "-") + ".html"
        assert files[name] == baseline[name]
    # An FC-shaped field in another family must not acquire a Modbus label.
    findings[9]["key"]["protocol"] = "profinet_dcp"
    other = render(report, verified)
    assert (
        _FindingLinks(other["protocol-profinet-dcp.html"]).labels[0][1]
        == "Candidate only metadata · PROFINET DCP"
    )
