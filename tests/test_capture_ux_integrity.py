"""Independent UX safety and frozen-evidence checks, without display-helper oracles."""

import copy
import hashlib
import json
import re
import socket
import struct
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

import pytest
import yaml

from otarchguard.api import validate_bytes
from otarchguard.capture import contract, observations, parser, reconciliation
from otarchguard.capture.contract import CAPTURE_LIMITS
from otarchguard.capture.explorer import generate_site
from otarchguard.diagnostics import ModelError
from tools.capture_workloads import demo_frames, plant_model, write_pcap
from tools.read_capture_evidence import load_bundle

FIXTURES = Path(__file__).parent / "fixtures/capture-contract-v2"
CORE_SHA256 = {
    parser: "460ac34c0df3184d55b1f325ef1b2851256c0b89762910145b0d7c67642de096",
    observations: "9a6ce4376a807ba72a1af195b2d4dc59693494c19fb7d2a6cc7870efd158fddd",
    reconciliation: "9533662627858783d175f0b58aa063102c74a30ad091370ddb7baa4c7ea27f6c",
    contract: "dc90ef11cdbf328904226c9d0a910b2cefd87c977b69e3ffa518c70aabadaedc",
}


@dataclass
class Element:
    tag: str
    attrs: dict[str, str | None]
    parent: "Element | None" = None
    children: list["Element"] = field(default_factory=list)
    content: list[str] = field(default_factory=list)

    def text(self) -> str:
        return " ".join(self.content + [child.text() for child in self.children])

    def ancestors(self) -> list["Element"]:
        values = []
        parent = self.parent
        while parent is not None:
            values.append(parent)
            parent = parent.parent
        return values

    def descendants(self) -> list["Element"]:
        return [child for node in self.children for child in [node, *node.descendants()]]


class Document(HTMLParser):
    """Small independent tree for link/visibility inspection, not the product audit."""

    def __init__(self, data: str) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Element("root", {})
        self.stack = [self.root]
        self.elements: list[Element] = []
        self.feed(data)
        self.close()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = Element(tag, dict(attrs), self.stack[-1])
        self.stack[-1].children.append(node)
        self.elements.append(node)
        if tag not in {"meta", "link", "br", "hr", "img", "input"}:
            self.stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if self.stack[-1].tag == tag:
            self.stack.pop()

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return

    def handle_data(self, data: str) -> None:
        self.stack[-1].content.append(data)

    def links(self) -> list[Element]:
        return [node for node in self.elements if node.tag == "a"]


def frozen(case: str = "limited") -> dict[str, Any]:
    return {
        name: json.loads((FIXTURES / case / (name + ".json")).read_bytes())
        for name in ("observations", "mapping", "comparison")
    }


def render(output: Path, value: dict[str, Any], rows_per_page: int = 100) -> dict[str, Any]:
    return generate_site(
        value["observations"],
        output,
        value["comparison"],
        limits=replace(CAPTURE_LIMITS, rows_per_page=rows_per_page),
        mapping=value["mapping"],
    )


def documents(output: Path) -> dict[str, Document]:
    return {p.name: Document(p.read_text(encoding="utf-8")) for p in output.glob("*.html")}


def assert_links_resolve(output: Path, pages: dict[str, Document]) -> None:
    ids = {}
    for name, page in pages.items():
        values = [n.attrs["id"] for n in page.elements if "id" in n.attrs]
        assert len(values) == len(set(values)), f"Duplicate fragment targets in {name}"
        ids[name] = set(values)
    for name, page in pages.items():
        for node in page.links():
            href = node.attrs.get("href")
            assert isinstance(href, str) and node.text().strip(), f"Empty link in {name}"
            parsed = urlsplit(href)
            assert not parsed.scheme and not parsed.netloc and not parsed.query, href
            target = unquote(parsed.path) or name
            assert "/" not in target and "\\" not in target, href
            assert (output / target).is_file(), (name, href)
            if parsed.fragment:
                assert unquote(parsed.fragment) in ids[target], (name, href)


def test_presentation_remediation_preserves_exact_analytical_module_bytes() -> None:
    for module, expected in CORE_SHA256.items():
        assert module.__file__ is not None
        assert hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest() == expected


@pytest.mark.parametrize("case", ["supported", "limited"])
def test_generated_canonical_artifacts_remain_exact_frozen_bytes_without_input_mutation(
    tmp_path: Path,
    case: str,
) -> None:
    value = frozen(case)
    before = copy.deepcopy(value)
    output = tmp_path / "site"
    render(output, value)
    assert value == before
    for name in ("observations", "mapping", "comparison"):
        assert (output / (name + ".json")).read_bytes() == (
            FIXTURES / case / (name + ".json")
        ).read_bytes()
    assert load_bundle(output) == value


def test_report_bytes_are_deterministic_with_network_operations_denied(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def denied(*args: object, **kwargs: object) -> Any:
        raise AssertionError("UX rendering attempted networking")

    monkeypatch.setattr(socket, "socket", denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)
    value = frozen()
    first, second = tmp_path / "first", tmp_path / "second"
    first_result = render(first, value, 2)
    second_result = render(second, value, 2)
    assert first_result == second_result
    assert {p.name: p.read_bytes() for p in first.iterdir()} == {
        p.name: p.read_bytes() for p in second.iterdir()
    }


@pytest.mark.parametrize("rows", [2, 100])
def test_independent_html_audit_resolves_all_links_and_fragments(tmp_path: Path, rows: int) -> None:
    value = frozen()
    output = tmp_path / "site"
    render(output, value, rows)
    assert_links_resolve(output, documents(output))


def test_primary_analysis_is_structured_and_json_is_advanced_evidence(tmp_path: Path) -> None:
    output = tmp_path / "site"
    render(output, frozen())
    for name, page in documents(output).items():
        for node in page.elements:
            if node.tag == "pre" and node.text().lstrip().startswith(("{", "[")):
                assert any(parent.tag == "details" for parent in node.ancestors()), (
                    name,
                    "Raw JSON remains the default human presentation",
                )
    protocols = documents(output)["protocols.html"]
    assert any(node.tag == "table" for node in protocols.elements)
    assert "Modbus/TCP" in protocols.root.text()
    assert "PORT_HINT" in protocols.root.text()
    coverage = documents(output)["coverage.html"]
    assert "[]" not in coverage.root.text()


def test_finding_evidence_links_have_readable_communication_labels(tmp_path: Path) -> None:
    output = tmp_path / "site"
    value = frozen()
    render(output, value, 2)
    evidence_links = [
        link
        for name, page in documents(output).items()
        if name.startswith("findings")
        for link in page.links()
        if "#flow-" in str(link.attrs.get("href", ""))
    ]
    for finding in value["comparison"]["findings"]:
        links = [
            n
            for n in evidence_links
            if str(n.attrs["href"]).endswith("#flow-" + finding["flow_id"])
        ]
        assert links, finding["flow_id"]
        assert all(re.fullmatch(r"flow-[0-9a-f]{64}", n.text().strip()) is None for n in links)


def test_security_boundary_csp_passive_markup_and_local_styles(tmp_path: Path) -> None:
    output = tmp_path / "site"
    render(output, frozen())
    for name, page in documents(output).items():
        policies = [
            n.attrs.get("content", "")
            for n in page.elements
            if n.tag == "meta" and n.attrs.get("http-equiv") == "Content-Security-Policy"
        ]
        assert len(policies) == 1
        for directive in (
            "default-src 'none'",
            "script-src 'none'",
            "connect-src 'none'",
            "object-src 'none'",
            "base-uri 'none'",
        ):
            assert directive in str(policies[0]), (name, directive)
        assert "Sensitive network metadata" in page.root.text()
        assert not {n.tag for n in page.elements} & {
            "script",
            "iframe",
            "object",
            "embed",
            "form",
            "img",
            "audio",
            "video",
        }
        for node in page.elements:
            assert not any(key.lower().startswith("on") for key in node.attrs), (name, node.attrs)
            if node.tag == "link":
                assert node.attrs == {"rel": "stylesheet", "href": "assets.css"}
    css = (output / "assets.css").read_text(encoding="utf-8")
    assert "@import" not in css and "url(" not in css
    assert ":focus-visible" in css and "@media" in css
    assert not any(p.suffix in {".pcap", ".pcapng", ".js"} for p in output.iterdir())


def test_untrusted_review_text_is_escaped_and_paths_controls_are_not_disclosed(
    tmp_path: Path,
) -> None:
    value = frozen()
    attack = '<img src="https://attacker.invalid/pixel" onerror="alert(1)"><script>bad()</script>'
    text = attack + " C:\\Users\\SensitivePerson\\private.txt \u202eX\u2066Y"
    for proposal in value["comparison"]["association_decisions"]:
        proposal["reviewer"] = text
        proposal["rationale"] = text + " L" * 1500
        proposal["selected_asset_id"] = attack
        proposal["selected_interface_id"] = attack
    for flow in value["observations"]["flows"]:
        for hint in flow["protocol_hints"]:
            hint["protocol"] = attack
    # The renderer is a text sink; this deliberately hostile in-memory record
    # exercises escaping independently of the strict owner-review input parser.
    value["observations"]["limitations"].append(text)
    value["observations"]["capture"]["format"] = attack
    output = tmp_path / "site"
    render(output, value)
    markup = "".join(p.read_text(encoding="utf-8") for p in output.glob("*.html"))
    assert attack not in markup and "&lt;img" in markup and "&lt;script&gt;" in markup
    assert "SensitivePerson" not in markup
    assert "\u202e" not in markup and "\u2066" not in markup
    assert "[U+202E]" in markup and "[U+2066]" in markup
    pages = documents(output)
    assert not {n.tag for p in pages.values() for n in p.elements} & {"img", "script"}
    assert_links_resolve(output, pages)


@pytest.mark.parametrize("control", ["\x00", "\x1b", "\ud800"])
def test_unsupported_display_controls_fail_without_partial_publication(
    tmp_path: Path,
    control: str,
) -> None:
    value = frozen()
    value["observations"]["limitations"].append("Untrusted " + control + " text")
    output = tmp_path / "refused"
    with pytest.raises(ModelError):
        render(output, value)
    assert not output.exists() and not list(tmp_path.glob(".otarchguard-capture-*"))


def test_primary_conversation_times_are_readable_utc_and_exact_times_stay_technical(
    tmp_path: Path,
) -> None:
    output = tmp_path / "site"
    render(output, frozen())
    page = documents(output)["conversations.html"]
    visible = " ".join(
        part
        for node in page.elements
        if not any(parent.tag == "details" for parent in node.ancestors()) and node.tag != "details"
        for part in node.content
    )
    # Independent platform calendar reference for this supported positive epoch;
    # the production formatter uses exact rational decomposition instead.
    expected = datetime.fromtimestamp(1_700_000_000, tz=UTC).strftime("%Y-%m-%d %H:%M:%S")
    assert expected in visible and "UTC" in visible
    assert re.search(r"\d{10,}/\d+", visible) is None
    assert "1700000000000007/1000000" in page.root.text()


def test_unsafe_canonical_identifier_cannot_publish_injected_markup(tmp_path: Path) -> None:
    value = frozen()
    value["observations"]["flows"][0]["id"] = 'flow-" onclick="bad()'
    output = tmp_path / "refused"
    with pytest.raises((ModelError, ValueError, KeyError)):
        render(output, value)
    assert not output.exists() and not list(tmp_path.glob(".otarchguard-capture-*"))


def test_output_budget_and_existing_evidence_are_preserved(tmp_path: Path) -> None:
    value = frozen()
    output = tmp_path / "existing"
    output.mkdir()
    marker = output / "owner-evidence.txt"
    marker.write_bytes(b"original evidence")
    with pytest.raises(ModelError):
        render(output, value)
    assert marker.read_bytes() == b"original evidence"
    failed = tmp_path / "bounded"
    with pytest.raises(ModelError):
        generate_site(
            value["observations"],
            failed,
            value["comparison"],
            replace(CAPTURE_LIMITS, output_bytes=100),
        )
    assert not failed.exists() and not list(tmp_path.glob(".otarchguard-capture-*"))


def anchor_index(pages: dict[str, Document]) -> dict[str, tuple[str, Element]]:
    return {
        str(node.attrs["id"]): (name, node)
        for name, page in pages.items()
        for node in page.elements
        if "id" in node.attrs
    }


def destinations(name: str, element: Element) -> set[tuple[str, str]]:
    targets = set()
    for node in element.descendants():
        if node.tag == "a":
            parsed = urlsplit(str(node.attrs["href"]))
            targets.add((parsed.path or name, parsed.fragment))
    return targets


def paginated_family(pages: dict[str, Document], start: str) -> set[str]:
    """Follow only table pagination, so global navigation cannot prove traceability."""
    visited: set[str] = set()
    pending = [start]
    while pending:
        name = pending.pop()
        if name in visited:
            continue
        visited.add(name)
        page = pages[name]
        for node in page.links():
            if node.text().strip() == "Next page" and any(
                p.attrs.get("aria-label") == "Table pages" for p in node.ancestors()
            ):
                target = urlsplit(str(node.attrs["href"])).path
                assert target in pages
                pending.append(target)
    return visited


def related_targets(
    pages: dict[str, Document],
    host_name: str,
    host: Element,
    host_target: tuple[str, str],
    expected_count: int,
) -> set[tuple[str, str]]:
    """Accept bounded previews when the complete contextual reference index is usable."""
    targets = {t for t in destinations(host_name, host) if t[1].startswith("aggregate-")}
    complete_links = [
        node
        for node in host.descendants()
        if node.tag == "a"
        and "related communications" in node.text().lower()
        and node.text().strip().startswith("All ")
    ]
    if complete_links:
        assert len(complete_links) == 1
        entry = complete_links[0]
        assert re.match(rf"All {expected_count} related communications", entry.text().strip())
        url = urlsplit(str(entry.attrs["href"]))
        first = next(n for n in pages[url.path].elements if n.attrs.get("id") == url.fragment)
        assert host_target in destinations(url.path, first), "Reference index starts at wrong host"
        for name in paginated_family(pages, url.path):
            for row in pages[name].elements:
                if row.tag == "tr" and host_target in destinations(name, row):
                    targets.update(
                        t for t in destinations(name, row) if t[1].startswith("aggregate-")
                    )
    return targets


@pytest.mark.parametrize("rows", [2, 100])
def test_contextual_links_join_exact_addresses_aggregates_groups_findings_and_reviews(
    tmp_path: Path,
    rows: int,
) -> None:
    value = frozen()
    output = tmp_path / "site"
    render(output, value, rows)
    pages = documents(output)
    anchors = anchor_index(pages)
    hosts = {h["ip"]: h for h in value["observations"]["hosts"]}
    proposals = {p["observed_ip"]: p for p in value["mapping"]["proposals"]}

    def target(anchor: str) -> tuple[str, str]:
        name, _ = anchors[anchor]
        return name, anchor

    complete_by_address = {}
    for address, host_record in hosts.items():
        host_anchor = "address-" + host_record["id"]
        host_name, host = anchors[host_anchor]
        expected = {
            target("aggregate-" + f["id"])
            for f in value["observations"]["flows"]
            if address in (f["source_ip"], f["destination_ip"])
        }
        complete_by_address[address] = related_targets(
            pages,
            host_name,
            host,
            target(host_anchor),
            len(expected),
        )
        assert complete_by_address[address] == expected

    for flow in value["observations"]["flows"]:
        flow_id = flow["id"]
        name, aggregate = anchors["aggregate-" + flow_id]
        links = destinations(name, aggregate)
        assert target("flow-" + flow_id) in links
        assert target("finding-" + flow_id) in links
        assert target("group-" + flow["conversation_id"]) in links
        evidence_name, evidence = anchors["flow-" + flow_id]
        assert target("aggregate-" + flow_id) in destinations(evidence_name, evidence)
        finding_name, finding = anchors["finding-" + flow_id]
        assert target("flow-" + flow_id) in destinations(finding_name, finding)
        for key in ("source_ip", "destination_ip"):
            address = flow[key]
            if address in hosts:
                host_anchor = "address-" + hosts[address]["id"]
                assert target(host_anchor) in links
                host_name, host = anchors[host_anchor]
                assert target("aggregate-" + flow_id) in complete_by_address[address]
                proposal = proposals[address]
                review_anchor = "association-" + proposal["id"].replace("_", "-")
                review_name, review = anchors[review_anchor]
                assert target(host_anchor) in destinations(review_name, review)
                assert target(review_anchor) in destinations(host_name, host)
    assert "evidence.html" in pages
    evidence_index_targets = {
        target
        for name in paginated_family(pages, "evidence.html")
        for target in destinations(name, pages[name].root)
    }
    for flow in value["observations"]["flows"]:
        assert target("flow-" + flow["id"]) in evidence_index_targets


def test_primary_and_secondary_navigation_exposes_all_evidence_families_and_current_page(
    tmp_path: Path,
) -> None:
    output = tmp_path / "site"
    render(output, frozen(), 2)
    pages = documents(output)
    required = {
        "index",
        "hosts",
        "conversations",
        "protocols",
        "findings",
        "coverage",
        "groups",
        "associations",
        "evidence",
        "address-links",
        "not-observed",
    }
    for name, page in pages.items():
        nav_links = [node for node in page.links() if any(p.tag == "nav" for p in node.ancestors())]
        assert required <= {str(n.attrs["href"]).split(".", 1)[0] for n in nav_links}
        active = [node for node in nav_links if node.attrs.get("aria-current") == "page"]
        assert active, name
        family = re.sub(r"-\d+$", "", name[:-5])
        if name.startswith(("evidence-", "evidenceindex-")):
            family = "evidence"
        assert any(str(n.attrs["href"]).split(".", 1)[0] == family for n in active), name


def test_dense_paginated_report_retains_every_aggregate_and_complete_address_relationship(
    tmp_path: Path,
) -> None:
    capture = tmp_path / "dense.pcap"
    write_pcap(capture, count=130, cardinality=130)
    obs = observations.analyze_capture(capture)
    model = validate_bytes(yaml.safe_dump(plant_model()).encode())
    mapping = reconciliation.mapping_template(obs, model)
    comparison = reconciliation.compare_capture(obs, model, mapping)
    output = tmp_path / "dense"
    render(output, {"observations": obs, "mapping": mapping, "comparison": comparison}, 7)
    pages = documents(output)
    anchors = anchor_index(pages)
    assert "Diagram omitted" in pages["index.html"].root.text()
    for flow in obs["flows"]:
        assert "aggregate-" + flow["id"] in anchors
        assert "finding-" + flow["id"] in anchors
        assert "flow-" + flow["id"] in anchors
    destination_host = next(h for h in obs["hosts"] if h["ip"] == "192.0.2.20")
    host_name, host = anchors["address-" + destination_host["id"]]
    targets = related_targets(
        pages,
        host_name,
        host,
        (host_name, "address-" + destination_host["id"]),
        len(obs["flows"]),
    )
    for flow in obs["flows"]:
        aggregate_name, _ = anchors["aggregate-" + flow["id"]]
        assert (aggregate_name, "aggregate-" + flow["id"]) in targets
    assert_links_resolve(output, pages)
    assert load_bundle(output)["observations"] == obs


def test_arp_target_reference_stays_out_of_address_and_association_indexes(tmp_path: Path) -> None:
    frame = demo_frames()[8]
    capture = tmp_path / "arp-only.pcap"
    capture.write_bytes(
        struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1)
        + struct.pack("<IIII", 1700000000, 0, len(frame), len(frame))
        + frame
    )
    obs = observations.analyze_capture(capture)
    model = validate_bytes(yaml.safe_dump(plant_model()).encode())
    mapping = reconciliation.mapping_template(obs, model)
    comparison = reconciliation.compare_capture(obs, model, mapping)
    assert [h["ip"] for h in obs["hosts"]] == ["192.0.2.10"]
    assert [p["observed_ip"] for p in mapping["proposals"]] == ["192.0.2.10"]
    output = tmp_path / "arp"
    render(output, {"observations": obs, "mapping": mapping, "comparison": comparison})
    pages = documents(output)
    addresses = [
        n for n in pages["hosts.html"].elements if str(n.attrs.get("id", "")).startswith("address-")
    ]
    assert len(addresses) == 1 and "192.0.2.10" in addresses[0].text()
    assert "Target" in pages["conversations.html"].root.text()
    assert "reference" in pages["conversations.html"].root.text().lower()
    assert "response" in pages["index.html"].root.text().lower()
    assert (output / "observations.json").read_bytes() == json.dumps(
        obs, sort_keys=True, ensure_ascii=True, indent=2
    ).encode() + b"\n"


@pytest.mark.parametrize("case", ["supported", "limited"])
def test_executive_summary_metrics_match_canonical_denominators(tmp_path: Path, case: str) -> None:
    value = frozen(case)
    output = tmp_path / "summary"
    render(output, value)
    page = documents(output)["index.html"]
    displayed = {}
    for definition in page.elements:
        if definition.tag == "dt":
            assert definition.parent is not None
            siblings = definition.parent.children
            index = siblings.index(definition)
            assert index + 1 < len(siblings) and siblings[index + 1].tag == "dd"
            label = definition.text().strip().removesuffix(":")
            displayed[label] = siblings[index + 1].text().strip()
    obs, comparison = value["observations"], value["comparison"]
    expected = {
        "Total packet records": obs["coverage"]["packets"],
        "Observed addresses": len(obs["hosts"]),
        "Directed aggregates": len(obs["flows"]),
        "Bidirectional groups": len(obs["conversations"]),
        "Decoded packet records": obs["coverage"]["decoded"],
        "Unsupported packet records": obs["coverage"]["unsupported"],
        "Model-comparison flow findings": len(comparison["findings"]),
        "Declared services not observed": len(comparison["declared_services_not_observed"]),
    }
    assert {label: displayed[label] for label in expected} == {
        label: str(count) for label, count in expected.items()
    }
    # The incompletely interpreted fixture must not turn a suppressed absence
    # assessment into an additional flow finding or a missing-service claim.
    if case == "limited":
        assert comparison["absence_assessment"]["status"] == "suppressed"
        assert displayed["Declared services not observed"] == "0"


def test_distinct_valid_service_ids_do_not_collide_in_absence_fragment_targets(
    tmp_path: Path,
) -> None:
    raw: dict[str, Any] = plant_model()
    for service, identity, port in zip(
        raw["services"], ("svc_a", "svc-a"), (65000, 65001), strict=True
    ):
        service["id"] = identity
        service["destination_ports"] = [{"start": port, "end": port}]
    model = validate_bytes(yaml.safe_dump(raw).encode())
    obs = frozen("supported")["observations"]
    mapping = reconciliation.mapping_template(obs, model)
    for proposal in mapping["proposals"]:
        if len(proposal["candidates"]) == 1:
            selected = proposal["candidates"][0]
            proposal.update(
                decision="ACCEPT",
                selected_asset_id=selected["asset_id"],
                selected_interface_id=selected["interface_id"],
                reviewer="fictional-reviewer",
                rationale="Synthetic service-fragment regression, not physical identity approval.",
            )
    comparison = reconciliation.compare_capture(obs, model, mapping)
    assert {s["service_id"] for s in comparison["declared_services_not_observed"]} == {
        "svc_a",
        "svc-a",
    }
    value = {"observations": obs, "mapping": mapping, "comparison": comparison}
    original = copy.deepcopy(value)
    output = tmp_path / "service-fragments"
    render(output, value)
    assert value == original
    pages = documents(output)
    rows = [n for n in pages["not-observed.html"].elements if n.tag == "tr" and "id" in n.attrs]
    assert len(rows) == len({n.attrs["id"] for n in rows}) == 2
    assert {n.children[0].text().strip() for n in rows} == {"svc_a", "svc-a"}
    assert_links_resolve(output, pages)
    for name, evidence in value.items():
        assert (output / (name + ".json")).read_bytes() == json.dumps(
            evidence,
            sort_keys=True,
            ensure_ascii=True,
            indent=2,
        ).encode() + b"\n"
