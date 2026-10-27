"""Independent emitted-byte, publication and portable-integrity adversaries."""

import copy
import hashlib
import json
import os
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from otarchguard.diagnostics import ModelError
from otarchguard.drift import explorer_bundle as bundle
from otarchguard.drift.engine import compare
from otarchguard.drift.reports import verify_report
from tools.drift_walkthrough import comparison_context, prepare


def _json(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode() + b"\n"
    )


def _page(body: str = "<p>Finite evidence only.</p>") -> bytes:
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; '
        "style-src 'self'; script-src 'none'; base-uri 'none'; form-action 'none'\">"
        '<title>Historical comparison</title><link rel="stylesheet" href="style.css">'
        '</head><body><a href="#main">Skip to content</a><main id="main">'
        "<h1>Historical comparison</h1>" + body + "</main></body></html>"
    ).encode("utf-8")


@pytest.fixture(scope="module")
def inputs(tmp_path_factory: pytest.TempPathFactory) -> tuple[dict[str, bytes], dict[str, Any]]:
    root = tmp_path_factory.mktemp("historical-bundle-inputs")
    selected = prepare(root / "sources", variations=False)
    workspace = Path(selected["workspace"])
    reference = selected["periods"]["reference"]["analysis_id"]
    candidate = selected["periods"]["candidate"]["analysis_id"]
    report = compare(
        workspace,
        selected["baseline_id"],
        [candidate],
        comparison_context(reference, candidate, selected["scope"]),
    )
    raw = _json(report)
    report_path = root / "report.json"
    report_path.write_bytes(raw)
    verification = verify_report(workspace, report_path)
    identity = {
        "historical_explorer_version": 1,
        "renderer_version": "1.4.0-historical-explorer.1",
        "renderer_sha256": "a" * 64,
        "report_sha256": hashlib.sha256(raw).hexdigest(),
        "report_bytes": len(raw),
        "drift_id": report["drift_id"],
        "drift_version": report["drift_version"],
        "engine_version": report["engine_version"],
        "comparability_policy_version": report["comparability_policy_version"],
        "baseline_id": selected["baseline_id"],
        "recorded_approval_id": selected["approval_id"],
        "workspace_inventory_sha256": "b" * 64,
        "generation_verification": verification,
        "options": {"page_size": 50},
    }
    return {
        "index.html": _page(),
        "style.css": b"body {color:#162332;background:#fff}",
        "report.json": raw,
        "verification.json": _json(verification),
    }, identity


def _publish(
    inputs: tuple[dict[str, bytes], dict[str, Any]],
    output: Path,
) -> dict[str, Any]:
    files, identity = inputs
    return bundle.publish(files, identity, output, before_publish=lambda: None)


def test_portable_deterministic_complete_read_only_bundle(
    inputs: tuple[dict[str, bytes], dict[str, Any]],
    tmp_path: Path,
) -> None:
    first, second = tmp_path / "first", tmp_path / "second"
    result = _publish(inputs, first)
    _publish(inputs, second)
    before = {p.name: p.read_bytes() for p in first.iterdir()}
    assert before == {p.name: p.read_bytes() for p in second.iterdir()}
    checked = bundle.verify_bundle(first)
    assert checked["status"] == "PORTABLE_INTEGRITY_VALID"
    assert checked["analytical_reproduction"] is False
    assert checked["html_pages"] == 1
    assert checked["internal_links"] == 2
    assert checked["files"] == 5
    assert checked["bundle_id"] == result["bundle_id"]
    assert before == {p.name: p.read_bytes() for p in first.iterdir()}
    manifest = json.loads(before[bundle.MANIFEST])
    body = {k: v for k, v in manifest.items() if k != "bundle_id"}
    independent = hashlib.sha256(
        b"otarchguard.historical-explorer.v1\x00" + _json(body)
    ).hexdigest()
    assert manifest["bundle_id"] == "historical-explorer-" + independent


@pytest.mark.parametrize("member", ["index.html", "style.css", "report.json", "verification.json"])
def test_any_emitted_member_tampering_fails(
    inputs: tuple[dict[str, bytes], dict[str, Any]],
    tmp_path: Path,
    member: str,
) -> None:
    output = tmp_path / "site"
    _publish(inputs, output)
    with (output / member).open("ab") as stream:
        stream.write(b" ")
    with pytest.raises(ModelError):
        bundle.verify_bundle(output)


@pytest.mark.parametrize(
    "mutation", ["extra", "missing", "manifest", "duplicate-json", "duplicate-file"]
)
def test_exact_inventory_and_manifest_fail_closed(
    inputs: tuple[dict[str, bytes], dict[str, Any]],
    tmp_path: Path,
    mutation: str,
) -> None:
    output = tmp_path / "site"
    _publish(inputs, output)
    path = output / bundle.MANIFEST
    manifest = json.loads(path.read_bytes())
    if mutation == "extra":
        (output / "extra.json").write_bytes(b"{}")
    elif mutation == "missing":
        (output / "style.css").unlink()
    elif mutation == "manifest":
        manifest["identity"]["options"]["page_size"] = 100
        path.write_bytes(_json(manifest))
    elif mutation == "duplicate-json":
        path.write_bytes(path.read_bytes().replace(b'{"audit":', b'{"audit":{},"audit":', 1))
    else:
        manifest["files"].append(manifest["files"][0])
        path.write_bytes(_json(manifest))
    with pytest.raises(ModelError):
        bundle.verify_bundle(output)


@pytest.mark.parametrize(
    "body",
    [
        "<script>alert(1)</script>",
        '<img src="https://example.test/pixel">',
        '<p onclick="alert(1)">x</p>',
        '<p style="background:url(https://example.test)">x</p>',
        '<a href="javascript:alert(1)">bad</a>',
        '<a href="data:text/html,x">bad</a>',
        '<a href="file:///etc/passwd">bad</a>',
        '<a href="../index.html">bad</a>',
        '<a href="https://example.test">bad</a>',
        '<a href="missing.html">missing</a>',
        '<a href="#missing">missing</a>',
        '<p id="main">duplicate</p>',
        '<p id="x" id="y">duplicate attr</p>',
        "<div><p>unbalanced</div>",
        '<meta http-equiv="refresh" content="0;url=https://example.test">',
        '<svg viewBox="0 0 1 1" aria-label="bad"><foreignObject>x</foreignObject></svg>',
        '<svg viewBox="0 0 1 1" aria-label="bad"><a href="https://example.test">x</a></svg>',
        '<svg viewBox="0 0 1 1" aria-label="bad"><path d="M0 0" fill="url(http://x)"></path></svg>',
        '<svg viewBox="0 0 1 1" aria-label="bad"><path d="M0 0" fill="u\\72l(http://x)"></path></svg>',
        "<p>bidirectional\u202econtrol</p>",
        "<p>control\x00character</p>",
    ],
)
def test_actual_generated_markup_security_adversaries(body: str) -> None:
    files = {
        "index.html": _page(body),
        "style.css": b"body{color:#000}",
        "report.json": b"{}",
        "verification.json": b"{}",
    }
    with pytest.raises(ModelError):
        bundle.audit_files(files)


@pytest.mark.parametrize(
    "css",
    [
        b'@import "https://example.test/x";',
        b"a{background:url(data:x)}",
        b"a{width:expression(alert(1))}",
        b"a{background:u\\72l(x)}",
        b"/*hidden*/a{}",
        b'body{background:image-set("https://example.test/pixel" 1x)}',
        b"@font-face{font-family:remote;src:local(system)}",
    ],
)
def test_stylesheet_cannot_acquire_network_or_executable_content(css: bytes) -> None:
    with pytest.raises(ModelError):
        bundle.audit_files(
            {
                "index.html": _page(),
                "style.css": css,
                "report.json": b"{}",
                "verification.json": b"{}",
            }
        )


def test_visual_structural_regression_oracle_rejects_defective_page() -> None:
    good = {
        "index.html": _page(),
        "style.css": b"body{color:#000}",
        "report.json": b"{}",
        "verification.json": b"{}",
    }
    assert bundle.audit_files(good)["html_pages"] == 1
    defective = dict(good)
    defective["index.html"] = defective["index.html"].replace(
        b"<h1>Historical comparison</h1>", b"<p>Historical comparison</p>"
    )
    with pytest.raises(ModelError):
        bundle.audit_files(defective)


def test_actual_renderer_stylesheet_accepts_semantic_child_selectors() -> None:
    from otarchguard.drift.explorer_render import CSS

    assert ">" in CSS
    files = {
        "index.html": _page(),
        "style.css": CSS.encode("utf-8"),
        "report.json": b"{}",
        "verification.json": b"{}",
    }
    assert bundle.audit_files(files)["html_pages"] == 1


def test_invalid_unicode_and_unbounded_resources_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    files = {
        "index.html": _page(),
        "style.css": b"body{color:#000}",
        "report.json": b"{}",
        "verification.json": b"{}",
    }
    invalid = dict(files, **{"index.html": b"\xff"})
    with pytest.raises(ModelError):
        bundle.audit_files(invalid)
    for name, value in (("files", 4), ("page_bytes", 10), ("total_bytes", 10), ("links", 1)):
        with monkeypatch.context() as patch:
            patch.setattr(bundle, "BUNDLE_LIMITS", replace(bundle.BUNDLE_LIMITS, **{name: value}))
            with pytest.raises(ModelError):
                bundle.audit_files(files)


def test_oversized_svg_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    files = {
        "index.html": _page(
            '<svg viewBox="0 0 10 10" aria-label="test"><title>Diagram</title>'
            '<rect x="0" y="0" width="1" height="1"></rect></svg>'
        ),
        "style.css": b"body{color:#000}",
        "report.json": b"{}",
        "verification.json": b"{}",
    }
    assert bundle.audit_files(files)["largest_svg_bytes"] > 0
    monkeypatch.setattr(bundle, "BUNDLE_LIMITS", replace(bundle.BUNDLE_LIMITS, svg_bytes=10))
    with pytest.raises(ModelError):
        bundle.audit_files(files)


def test_existing_destination_never_overwritten(
    inputs: tuple[dict[str, bytes], dict[str, Any]],
    tmp_path: Path,
) -> None:
    output = tmp_path / "site"
    output.mkdir()
    sentinel = output / "sentinel.txt"
    sentinel.write_bytes(b"retain")
    with pytest.raises(ModelError):
        _publish(inputs, output)
    assert sentinel.read_bytes() == b"retain"


def test_interruption_never_publishes_completion_manifest(
    inputs: tuple[dict[str, bytes], dict[str, Any]],
    tmp_path: Path,
) -> None:
    output = tmp_path / "interrupted"

    def interrupted() -> None:
        raise RuntimeError("injected interruption before completion")

    with pytest.raises(RuntimeError, match="injected interruption"):
        bundle.publish(*inputs, output, before_publish=interrupted)
    assert output.is_dir()
    assert not (output / bundle.MANIFEST).exists()
    with pytest.raises(ModelError):
        bundle.verify_bundle(output)
    assert not list(tmp_path.glob(".historical-explorer-*"))


def test_concurrent_destination_reservation_is_preserved(
    inputs: tuple[dict[str, bytes], dict[str, Any]],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "site"
    original = bundle._manifest

    def race(files: dict[str, bytes], identity: dict[str, Any]) -> dict[str, Any]:
        result = original(files, identity)
        output.mkdir()
        return result

    monkeypatch.setattr(bundle, "_manifest", race)
    with pytest.raises(ModelError):
        _publish(inputs, output)
    assert not list(output.iterdir())


def test_symlink_or_junction_ancestors_rejected(
    inputs: tuple[dict[str, bytes], dict[str, Any]],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = Path.is_junction
    unsafe = tmp_path / "junction"
    unsafe.mkdir()
    monkeypatch.setattr(Path, "is_junction", lambda self: self == unsafe or original(self))
    with pytest.raises(ModelError):
        _publish(inputs, unsafe / "site")


@pytest.mark.parametrize(
    "mutate",
    [
        lambda identity: identity.pop("options"),
        lambda identity: identity.update(options={"page_size": True}),
        lambda identity: identity.update(generation_verification=[]),
        lambda identity: identity.update(report_sha256="0" * 64),
        lambda identity: identity.update(baseline_id="wrong"),
    ],
)
def test_forged_identity_is_controlled_failure(
    inputs: tuple[dict[str, bytes], dict[str, Any]],
    tmp_path: Path,
    mutate: Any,
) -> None:
    files, original = inputs
    identity = copy.deepcopy(original)
    mutate(identity)
    with pytest.raises(ModelError):
        bundle.publish(files, identity, tmp_path / "site", before_publish=lambda: None)


def _source_case(tmp_path: Path) -> tuple[Path, Path, dict[str, Any]]:
    selected = prepare(tmp_path / "sources", variations=False)
    workspace = Path(selected["workspace"])
    reference = selected["periods"]["reference"]["analysis_id"]
    candidate = selected["periods"]["candidate"]["analysis_id"]
    report = compare(
        workspace,
        selected["baseline_id"],
        [candidate],
        comparison_context(reference, candidate, selected["scope"]),
    )
    path = tmp_path / "report.json"
    path.write_bytes(_json(report))
    return workspace, path, selected


def test_rehashed_false_html_claim_passes_integrity_but_fails_full_reproduction(
    tmp_path: Path,
) -> None:
    from otarchguard.drift.explorer import generate_explorer, verify_explorer

    workspace, report, _ = _source_case(tmp_path)
    output = tmp_path / "site"
    generate_explorer(workspace, report, output)
    index = output / "index.html"
    original = index.read_bytes()
    assert b"not incidents" in original
    changed = original.replace(b"not incidents", b"all incidents")
    assert len(original) == len(changed)
    index.write_bytes(changed)
    path = output / bundle.MANIFEST
    manifest = json.loads(path.read_bytes())
    for item in manifest["files"]:
        if item["name"] == "index.html":
            item["sha256"] = hashlib.sha256(changed).hexdigest()
    body = {k: v for k, v in manifest.items() if k != "bundle_id"}
    manifest["bundle_id"] = (
        "historical-explorer-"
        + hashlib.sha256(b"otarchguard.historical-explorer.v1\x00" + _json(body)).hexdigest()
    )
    path.write_bytes(_json(manifest))
    assert verify_explorer(output)["analytical_reproduction"] is False
    with pytest.raises(ModelError) as caught:
        verify_explorer(output, workspace=workspace)
    assert caught.value.diagnostics[0].code == "HISTORICAL_RENDER"


def test_superseded_reference_reproduces_historically_without_current_approval(
    tmp_path: Path,
) -> None:
    from otarchguard.drift.explorer import generate_explorer, verify_explorer
    from otarchguard.evidence import lifecycle

    workspace, report, selected = _source_case(tmp_path)
    output = tmp_path / "historical"
    generate_explorer(workspace, report, output)
    before = {p.name: p.read_bytes() for p in output.iterdir()}
    successor = lifecycle.propose_baseline(
        workspace,
        workspace.parent / "scope.json",
        [selected["periods"]["candidate"]["analysis_id"]],
        model=selected["periods"]["candidate"]["model_id"],
    )["baseline"]
    lifecycle.record_review(
        workspace,
        successor["baseline_id"],
        "supersede",
        "Fictional successor owner",
        "Choose an exact successor reference",
        predecessor=selected["approval_id"],
    )
    checked = verify_explorer(output, workspace=workspace)
    assert checked["analytical_reproduction"] is True
    assert checked["source_reproduction"]["current_baseline_status"] == "SUPERSEDED"
    assert checked["source_reproduction"]["currently_approved_reference"] is False
    assert checked["approval_snapshot_changed"] is True
    assert before == {p.name: p.read_bytes() for p in output.iterdir()}
    second = tmp_path / "after-supersession"
    generate_explorer(workspace, report, second)
    overview = (second / "index.html").read_text(encoding="utf-8")
    assert "SUPERSEDED" in overview
    assert (second / "report.json").read_bytes() == report.read_bytes()


def test_forged_historical_receipt_never_grants_current_authority(tmp_path: Path) -> None:
    from otarchguard.drift import explorer, explorer_render

    workspace, report_path, _ = _source_case(tmp_path)
    legitimate = tmp_path / "legitimate"
    explorer.generate_explorer(workspace, report_path, legitimate)
    manifest = json.loads((legitimate / bundle.MANIFEST).read_bytes())
    identity = copy.deepcopy(manifest["identity"])
    receipt = identity["generation_verification"]
    receipt["current_baseline_status"] = "REVOKED"
    receipt["currently_approved_reference"] = False
    receipt["review_graph_changed"] = True
    report = json.loads(report_path.read_bytes())
    files = explorer_render.render(report, receipt, page_size=identity["options"]["page_size"])
    files["report.json"] = report_path.read_bytes()
    files["verification.json"] = (
        json.dumps(receipt, sort_keys=True, ensure_ascii=True, indent=2, allow_nan=False) + "\n"
    ).encode()
    forged = tmp_path / "forged-receipt"
    bundle.publish(files, identity, forged, before_publish=lambda: None)
    checked = explorer.verify_explorer(forged, workspace=workspace)
    assert checked["analytical_reproduction"] is True
    assert checked["generation_authority_authenticated"] is False
    assert checked["approval_snapshot_changed"] is True
    assert checked["source_reproduction"]["current_baseline_status"] == "APPROVED"
    assert checked["source_reproduction"]["currently_approved_reference"] is True
    receipt["authority"] = "Cryptographically authenticated owner approval"
    files["verification.json"] = _json(receipt)
    with pytest.raises(ModelError):
        bundle.publish(
            files, identity, tmp_path / "false-authenticity", before_publish=lambda: None
        )


def test_portable_integrity_survives_missing_workspace_but_source_mode_fails(
    tmp_path: Path,
) -> None:
    from otarchguard.drift.explorer import generate_explorer, verify_explorer

    workspace, report, _ = _source_case(tmp_path)
    output = tmp_path / "site"
    generate_explorer(workspace, report, output)
    assert verify_explorer(output)["analytical_reproduction"] is False
    with pytest.raises(ModelError):
        verify_explorer(output, workspace=tmp_path / "unavailable-original-workspace")


def test_actual_symlink_member_is_rejected(
    inputs: tuple[dict[str, bytes], dict[str, Any]],
    tmp_path: Path,
) -> None:
    output = tmp_path / "site"
    _publish(inputs, output)
    member = output / "style.css"
    original = tmp_path / "original.css"
    original.write_bytes(member.read_bytes())
    member.unlink()
    try:
        member.symlink_to(original)
    except OSError:
        pytest.skip("Operating system does not grant symlink creation")
    with pytest.raises(ModelError):
        bundle.verify_bundle(output)


def test_actual_windows_junction_is_rejected(
    inputs: tuple[dict[str, bytes], dict[str, Any]],
    tmp_path: Path,
) -> None:
    import subprocess

    if os.name != "nt":
        pytest.skip("Windows junction semantics")
    actual = tmp_path / "actual"
    actual.mkdir()
    junction = tmp_path / "junction"
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(junction.absolute()), str(actual.absolute())],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.skip("Operating system does not grant junction creation")
    assert junction.is_junction()
    with pytest.raises(ModelError):
        _publish(inputs, junction / "site")
    assert not list(actual.iterdir())
