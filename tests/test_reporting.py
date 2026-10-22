"""T18/T21 and reporting T22/T24: offline, escaped, deterministic evidence."""

import json
import socket
import xml.etree.ElementTree as ET
from copy import deepcopy
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import pytest
import yaml
from typer.testing import CliRunner

from otarchguard import cli
from otarchguard.api import validate_bytes, validate_file
from otarchguard.comparison import compare_architectures
from otarchguard.exposure import exposure_architecture
from otarchguard.intents import check_architecture
from otarchguard.reachability import ReachabilityEngine
from otarchguard.reporting import (
    architecture_svg,
    build_report,
    html_report,
    json_report,
)

ROOT = Path(__file__).resolve().parents[1]
runner = CliRunner()


class OfflineHTML(HTMLParser):
    """Inspect parsed markup, not escaped payload substrings."""

    def __init__(self) -> None:
        super().__init__()
        self.svgs = 0
        self.csp = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        assert tag not in {"script", "iframe", "object", "embed", "img", "link", "base", "form"}
        for key, value in attrs:
            assert not key.startswith("on")
            assert key not in {"href", "src", "srcset", "action"}
            if key == "marker-end":
                assert value in {"url(#transport)", "url(#forward)"}
        if tag == "svg":
            self.svgs += 1
        if ("http-equiv", "Content-Security-Policy") in attrs:
            self.csp = True


def snapshot(data: dict[str, Any]) -> Any:
    return validate_bytes(yaml.safe_dump(data).encode())


@pytest.mark.parametrize("kind", ["validation", "check", "exposure", "comparison"])
def test_reports_are_order_invariant_and_complete(boundary: dict[str, Any], kind: str) -> None:
    first = snapshot(boundary)
    reordered = deepcopy(boundary)
    for value in reordered.values():
        if isinstance(value, list):
            value.reverse()
    reordered["suc"]["access_points"].reverse()
    for rule in reordered["rules"]:
        rule["edge_ids"].reverse()
    second = snapshot(reordered)

    def render(model: Any) -> tuple[bytes, bytes, str]:
        if kind == "validation":
            report = build_report("validation", (model,))
        elif kind == "check":
            report = build_report("check", (model,), check_architecture(model))
        elif kind == "exposure":
            report = build_report(
                "exposure", (model,), exposure_architecture(model, "support_scope")
            )
        else:
            report = build_report(
                "comparison", (model, model), compare_architectures(model, model, "support_scope")
            )
        models = (model, model) if kind == "comparison" else (model,)
        return json_report(report), html_report(report, models), architecture_svg(model)

    a, b = render(first), render(second)
    assert a == b == render(first)
    parsed = json.loads(a[0])
    assert parsed["snapshots"][0]["model_sha256"] == first.sha256
    assert parsed["security_level_evidence"]["SL-A"] == "unassessed"
    assert parsed["snapshots"][0]["model"]["suc"] == json.loads(first.canonical_json)["suc"]
    html = a[1].decode()
    assert "Administrative ownership" in html and "placement_zone_id" in html
    assert "ap_cabinet" in html and "dep_support" in html and "unassessed" in html
    assert "scope" in html and "resource_ceilings" in html
    parser = OfflineHTML()
    parser.feed(html)
    assert parser.csp and parser.svgs == (2 if kind == "comparison" else 1)
    svg = ET.fromstring(a[2])
    ns = {"s": "http://www.w3.org/2000/svg"}
    assert len(svg.findall("s:g[@data-edge-id]", ns)) == len(first.model.transport_edges) + len(
        first.model.forwarding_edges
    )
    assert "f_dmz_ot" in a[2] and "fw_it" in a[2]


@pytest.mark.parametrize(
    "attack",
    [
        '</text><script>alert("x")</script><text>',
        '</pre><img src="https://evil.invalid/x" onerror="alert(1)">',
        "A & B < C > D \"quote\" 'apostrophe'",
        '<svg onload="x"><a href="javascript:x">',
        "line\nnext\tvalue",
    ],
)
def test_malicious_text_is_only_text(boundary: dict[str, Any], attack: str) -> None:
    boundary["zones"][0]["name"] = attack
    boundary["assets"][0]["name"] = attack
    boundary["suc"]["completeness_assertion"] = attack
    boundary["suc"]["access_points"][1]["description"] = attack
    model = snapshot(boundary)
    report = build_report("exposure", (model,), exposure_architecture(model, "support_scope"))
    html = html_report(report, (model,)).decode()
    parser = OfflineHTML()
    parser.feed(html)
    svg = ET.fromstring(architecture_svg(model))
    assert svg.findall(".//{http://www.w3.org/2000/svg}script") == []
    assert attack in "".join(svg.itertext())
    assert (
        json.loads(json_report(report))["snapshots"][0]["model"]["suc"]["completeness_assertion"]
        == attack
    )


def test_large_topology_has_explicit_omissions(minimal: dict[str, Any]) -> None:
    for index in range(25):
        minimal["assets"].append({**minimal["assets"][0], "id": f"extra_{index}"})
    model = snapshot(minimal)
    report = build_report("validation", (model,))
    assert report["snapshots"][0]["diagram"]["mode"] == "summary"
    assert "t_eng_plc" in report["snapshots"][0]["diagram"]["omitted_from_diagram"]["edge_ids"]
    svg = ET.fromstring(architecture_svg(model))
    assert not svg.findall("{http://www.w3.org/2000/svg}g[@data-edge-id]")
    assert "SUMMARY" in "".join(svg.itertext())
    assert "extra_24" in html_report(report, (model,)).decode()


def test_xml_control_characters_are_visible_replacements(minimal: dict[str, Any]) -> None:
    minimal["assets"][0]["name"] = "before\x01after"
    model = snapshot(minimal)
    svg = ET.fromstring(architecture_svg(model))
    assert "before\ufffdafter" in "".join(svg.itertext())
    payload = json.loads(json_report(build_report("validation", (model,))))
    assert payload["snapshots"][0]["model"]["assets"][0]["name"] == "before\x01after"


def test_failed_render_or_resource_limit_preserves_existing_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from dataclasses import replace

    from otarchguard.contract import RESOURCE_LIMITS
    from otarchguard.intents import check_file

    path = ROOT / "tests/fixtures/minimal-valid.yaml"
    output = tmp_path / "report.html"
    output.write_bytes(b"previous report")

    def fail_render(*args: Any, **kwargs: Any) -> bytes:
        raise MemoryError("private detail")

    monkeypatch.setattr(cli, "html_report", fail_render)
    failed = runner.invoke(cli.app, ["check", str(path), "--report", str(output)])
    assert failed.exit_code == 2 and not failed.stdout
    assert json.loads(failed.stderr)["code"] == "INTERNAL_ERROR"
    assert "private detail" not in failed.stderr
    assert output.read_bytes() == b"previous report"

    def bounded_check(*args: Any, **kwargs: Any) -> Any:
        return check_file(path, replace(RESOURCE_LIMITS, state_edge_visits=1))

    monkeypatch.setattr(cli, "check_file", bounded_check)
    failed = runner.invoke(cli.app, ["check", str(path), "--report", str(output)])
    assert failed.exit_code == 2 and not failed.stdout
    assert json.loads(failed.stderr)["category"] == "resource_limit"
    assert output.read_bytes() == b"previous report"


def test_mismatched_evidence_rejected(minimal: dict[str, Any]) -> None:
    first = snapshot(minimal)
    minimal["revision"] = "different"
    second = snapshot(minimal)
    with pytest.raises(ValueError, match="hash"):
        build_report("check", (second,), check_architecture(first))
    with pytest.raises(ValueError, match="hash"):
        html_report(build_report("validation", (first,)), (second,))
    with pytest.raises(ValueError, match="kind"):
        build_report("exposure", (first,), check_architecture(first))


def test_unassessed_classifications_and_custom_ceiling_are_explicit(
    minimal: dict[str, Any],
) -> None:
    from dataclasses import replace

    from otarchguard.contract import RESOURCE_LIMITS

    minimal["zones"][0]["safety_designation"] = "unassessed"
    minimal["assets"][0]["domain_classification"] = "business"
    minimal["assets"][0]["safety_classification"] = "unassessed"
    model = snapshot(minimal)
    limits = replace(RESOURCE_LIMITS, state_edge_visits=12345)
    report = build_report("check", (model,), check_architecture(model, limits), limits=limits)
    assert report["resource_ceilings"]["state_edge_visits"] == 12345
    html = html_report(report, (model,)).decode()
    assert "business" in html and "iacs" in html
    assert "unassessed" in html and "External security-level assessment" in html
    assert "SL-T: 0" not in html and "SL-C: 0" not in html and "SL-A: 0" not in html


def test_report_layout_keeps_diagrams_visible_and_tables_readable() -> None:
    first = validate_file(ROOT / "examples/flat-plant/baseline.yaml")
    second = validate_file(ROOT / "examples/flat-plant/proposed.yaml")
    result = compare_architectures(first, second, "plant_scope")
    html = html_report(
        build_report("comparison", (first, second), result), (first, second)
    ).decode()
    assert html.index("req_hmi_plc — FAILED") < html.index("<svg")
    assert html.index("<svg") < html.index("Findings and witness provenance")
    assert "<table>" not in html[: html.index("<svg")]
    assert 'width="1100" height="' in html
    assert "width:max-content" in html and "min-width:10ch" in html
    assert "overflow-x:auto" in html and "word-break:normal" in html
    assert "Machine-readable JSON appendix (not an architecture diagram)</summary><pre>" in html
    assert "<details><summary>proposed · hmi → plc" in html


@pytest.mark.parametrize("fixture", ["minimal-valid.yaml", "boundary-device.yaml"])
def test_spatial_schematic_nests_placements_and_connects_exact_state_ports(fixture: str) -> None:
    model = validate_file(ROOT / "tests/fixtures" / fixture).model
    svg = ET.fromstring(architecture_svg(validate_file(ROOT / "tests/fixtures" / fixture)))
    ns = {"s": "http://www.w3.org/2000/svg"}
    ports: dict[tuple[str, str], tuple[float, float]] = {}
    for zone in model.zones:
        group = svg.find(f's:g[@data-zone-id="{zone.id}"]', ns)
        assert group is not None
        container = group.find("s:rect", ns)
        assert container is not None
        zx, zy = float(container.attrib["x"]), float(container.attrib["y"])
        zw, zh = float(container.attrib["width"]), float(container.attrib["height"])
        for attachment in group.findall("s:g[@data-asset-id]", ns):
            asset_id = attachment.attrib["data-asset-id"]
            asset = next(a for a in model.assets if a.id == asset_id)
            assert attachment.attrib["data-owner-zone-id"] == asset.zone_id
            assert attachment.attrib["data-placement-zone-id"] == zone.id
            rect = attachment.find("s:rect", ns)
            assert rect is not None
            ax, ay = float(rect.attrib["x"]), float(rect.attrib["y"])
            assert zx < ax < ax + float(rect.attrib["width"]) < zx + zw
            assert zy < ay < ay + float(rect.attrib["height"]) < zy + zh
            for port in attachment.findall(".//s:circle[@data-interface-id]", ns):
                interface = next(
                    i for i in model.interfaces if i.id == port.attrib["data-interface-id"]
                )
                assert interface.placement_zone_id == zone.id and interface.asset_id == asset_id
                ports[interface.id, port.attrib["data-phase"]] = (
                    float(port.attrib["cx"]),
                    float(port.attrib["cy"]),
                )
    assert set(ports) == {
        (i.id, phase) for i in model.interfaces for phase in ("ingress", "egress")
    }
    transitions = svg.findall("s:g[@data-edge-id]", ns)
    assert len(svg.findall(".//s:path[@marker-end]", ns)) == len(transitions)
    assert {g.attrib["data-edge-id"] for g in transitions} == {
        e.id for e in model.transport_edges
    } | {e.id for e in model.forwarding_edges}
    for edge in transitions:
        path = edge.find("s:path", ns)
        assert path is not None
        source_phase, target_phase = (
            ("egress", "ingress")
            if edge.attrib["data-kind"] == "transport"
            else ("ingress", "egress")
        )
        source = ports[edge.attrib["data-source-interface-id"], source_phase]
        target = ports[edge.attrib["data-target-interface-id"], target_phase]
        assert path.attrib["d"].startswith(f"M{int(source[0])},{int(source[1])} H")
        assert path.attrib["d"].endswith(f"V{int(target[1])} H{int(target[0])}")
        assert path.attrib["marker-end"] == (
            "url(#transport)" if source_phase == "egress" else "url(#forward)"
        )


@pytest.mark.parametrize("command", ["validate", "check", "exposure", "compare"])
@pytest.mark.parametrize("format", ["json", "html"])
def test_cli_reports_offline_and_same_stdout(
    command: str, format: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbid_network(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("Report attempted network access")

    monkeypatch.setattr(socket, "socket", forbid_network)
    path = ROOT / "tests/fixtures/boundary-device.yaml"
    args = [command, str(path)] + ([str(path)] if command == "compare" else [])
    if command in ("exposure", "compare"):
        args += ["--scenario", "support_scope"]
    existing = runner.invoke(cli.app, args)
    output = tmp_path / f"report with spaces.{format}"
    generated = runner.invoke(cli.app, [*args, "--report", str(output), "--report-format", format])
    assert generated.exit_code == existing.exit_code == 0, generated.output
    assert generated.stdout == existing.stdout and generated.stderr == ""
    first = output.read_bytes()
    assert (
        runner.invoke(
            cli.app, [*args, "--report", str(output), "--report-format", format]
        ).exit_code
        == 0
    )
    assert output.read_bytes() == first
    if format == "json":
        assert json.loads(first)["report_version"] == 1
    else:
        OfflineHTML().feed(first.decode())


@pytest.mark.parametrize(
    "fixture",
    [
        "invalid-missing-reference.yaml",
        "invalid-interface-placement.yaml",
        "unsupported-model.yaml",
    ],
)
def test_invalid_models_never_write_success_report(fixture: str, tmp_path: Path) -> None:
    path = ROOT / "tests/fixtures" / fixture
    assert path.is_file()
    output = tmp_path / "report.html"
    result = runner.invoke(cli.app, ["validate", str(path), "--report", str(output)])
    assert result.exit_code == 2 and not result.stdout
    assert json.loads(result.stderr)["category"] == (
        "unsupported_model" if fixture == "unsupported-model.yaml" else "invalid_input"
    )
    assert not output.exists()


@pytest.mark.parametrize("failure", ["missing_parent", "input_collision", "directory"])
def test_report_io_failure_is_controlled(tmp_path: Path, failure: str) -> None:
    path = tmp_path / "model.yaml"
    path.write_bytes((ROOT / "tests/fixtures/minimal-valid.yaml").read_bytes())
    before = path.read_bytes()
    output = (
        tmp_path / "absent/report.html"
        if failure == "missing_parent"
        else path
        if failure == "input_collision"
        else tmp_path
    )
    result = runner.invoke(cli.app, ["check", str(path), "--report", str(output)])
    assert result.exit_code == 2 and not result.stdout
    assert json.loads(result.stderr)["code"] == "REPORT_IO_ERROR"
    assert path.read_bytes() == before
    assert not list(tmp_path.glob(".otarchguard-*"))


@pytest.mark.parametrize(
    "family,scenario,before_count,after_count,failed",
    [
        ("segmented-plant", "plant_scope", 5, 6, "prohibit_it_ot"),
        ("flat-plant", "plant_scope", 3, 1, "req_hmi_plc"),
        ("remote-support", "support_scope", 4, 5, "prohibit_it_ot"),
    ],
)
def test_example_family_walkthroughs(
    family: str, scenario: str, before_count: int, after_count: int, failed: str, tmp_path: Path
) -> None:
    baseline = ROOT / "examples" / family / "baseline.yaml"
    proposed = ROOT / "examples" / family / "proposed.yaml"
    first, second = validate_file(baseline), validate_file(proposed)
    result = compare_architectures(first, second, scenario)
    assert result.baseline.passed and not result.proposed.passed
    assert len(result.baseline.observations) == before_count
    assert len(result.proposed.observations) == after_count
    assert any(i.id == failed and not i.passed for i in result.proposed.intent_checks.intents)
    for model, exposure in ((first, result.baseline), (second, result.proposed)):
        engine = ReachabilityEngine(model)
        for query in exposure.queries:
            for interval in query.intervals:
                if interval.witness is not None:
                    assert engine.replay(interval.witness)
    output = tmp_path / "comparison.html"
    args = [
        "compare",
        str(baseline),
        str(proposed),
        "--scenario",
        scenario,
        "--report",
        str(output),
    ]
    run = runner.invoke(cli.app, args)
    assert run.exit_code == 1 and not run.stderr
    html = output.read_text("utf-8")
    assert failed in html
    if family == "flat-plant":
        assert result.broken_required_communications and result.no_longer_reachable
        assert html.index("req_hmi_plc") < html.index("Findings and witness provenance")
        assert "FAILED" in html[: html.index("Interpretation and unassessed evidence")]
    parser = OfflineHTML()
    parser.feed(html)
    assert parser.svgs == 2


def test_remote_baseline_and_application_only_do_not_invent_relay() -> None:
    baseline = validate_file(ROOT / "examples/remote-support/baseline.yaml")
    approved = validate_file(ROOT / "tests/fixtures/boundary-device.yaml")
    assert baseline.canonical_json == approved.canonical_json
    negative = validate_file(ROOT / "examples/remote-support/application-only.yaml")
    result = exposure_architecture(negative, "support_scope")
    assert not result.passed
    assert not any(
        f.source_asset_id == "it" and f.destination_asset_id == "plc" for f in result.observations
    )
    assert any(
        f.source_asset_id == "it" and f.destination_asset_id == "jump" for f in result.observations
    )
