"""Independent separation checks; immutable legacy fixtures remain unchanged."""

import hashlib
import html
import io
import json
import subprocess
import tarfile
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from otarchguard import DISTRIBUTION_VERSION, NATIVE_ENGINE_VERSION, __version__
from otarchguard.api import validate_file
from otarchguard.evidence.workspace import build_snapshot
from otarchguard.reporting import build_report
from otarchguard.trace import trace_file
from tools import verify_legacy_candidate as legacy
from tools.evidence_identity import AnalysisInputs, proposed_analysis_id

ROOT = Path(__file__).resolve().parents[1]


def inputs() -> AnalysisInputs:
    return AnalysisInputs("a" * 64, "b" * 64, None, None, None, None, None, "c" * 64)


def test_distribution_advances_without_changing_native_engine_evidence() -> None:
    assert DISTRIBUTION_VERSION == "1.4.0"
    assert __version__ == "1.3.0"
    assert NATIVE_ENGINE_VERSION == "1.3.0"
    path = ROOT / "tests/fixtures/minimal-valid.yaml"
    assert build_report("validation", (validate_file(path),))["engine_version"] == "1.3.0"
    assert trace_file(path, "eng", "svc_plc").engine_version == "1.3.0"


@pytest.mark.parametrize("name", list(AnalysisInputs.__dataclass_fields__))
def test_every_analytical_input_changes_revision_not_physical_collection(name: str) -> None:
    original = inputs()
    changed = replace(original, **{name: "d" * 64})
    assert proposed_analysis_id(original) != proposed_analysis_id(changed)
    if name != "capture_sha256":
        assert original.capture_sha256 == changed.capture_sha256


def test_identity_proposal_has_independent_canonical_oracle_and_no_review_assertion() -> None:
    canonical = (
        '{"domain":"otarchguard.analysis","inputs":{'
        '"capture_sha256":"' + "a" * 64 + '","comparison_sha256":null,'
        '"enrichment_sha256":null,"mapping_sha256":null,"model_sha256":null,'
        '"observations_sha256":"' + "b" * 64 + '","policy_sha256":null,'
        '"producer_semantics_sha256":"' + "c" * 64 + '"},"proposal_version":1}'
    )
    assert (
        proposed_analysis_id(inputs())
        == "analysis-proposal-" + hashlib.sha256(canonical.encode()).hexdigest()
    )
    assert "approv" not in canonical and "baseline" not in canonical


@pytest.mark.parametrize("bad", ["a" * 63, "A" * 64, "../capture", "é" * 64, None, 1, True])
def test_proposal_rejects_ambiguous_identity(bad: Any) -> None:
    with pytest.raises(ValueError):
        proposed_analysis_id(replace(inputs(), capture_sha256=bad))


def test_snapshot_v1_keeps_its_contract_and_label_identity() -> None:
    path = ROOT / "tests/fixtures/capture-contract-v2/supported/observations.json"
    observation: dict[str, Any] = json.loads(path.read_bytes())
    first = build_snapshot(observation, "first review context")
    second = build_snapshot(observation, "different context")
    assert first["snapshot_version"] == second["snapshot_version"] == 1
    assert first["capture_sha256"] == second["capture_sha256"]
    assert first["snapshot_id"] != second["snapshot_id"]
    assert "analysis_id" not in first and "approved" not in first


@pytest.fixture(scope="module")
def pinned_legacy_files() -> tuple[bytes, dict[str, bytes]]:
    assert legacy.BASELINE == "f52c792b683cb499dc7de765b65b5cc897a96854"
    raw = subprocess.check_output(["git", "archive", legacy.BASELINE], cwd=ROOT)
    files = {}
    with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
        for member in archive.getmembers():
            if member.isfile():
                stream = archive.extractfile(member)
                assert stream is not None
                files[member.name] = stream.read()
    return raw, files


def test_legacy_header_exception_accepts_exact_reviewed_file(
    pinned_legacy_files: tuple[bytes, dict[str, bytes]],
) -> None:
    before = pinned_legacy_files[1]["tests/test_explorer.py"]
    after = (ROOT / "tests/test_explorer.py").read_bytes()
    assert legacy._reviewed_explorer_header_change(before, after)
    assert not legacy._reviewed_explorer_header_change(before, before)


@pytest.mark.parametrize(
    "mutation", ["additional_assertion", "extra_line", "extra_scope", "scope_order", "crlf"]
)
def test_legacy_header_exception_rejects_every_additional_byte_change(
    pinned_legacy_files: tuple[bytes, dict[str, bytes]],
    mutation: str,
) -> None:
    before = pinned_legacy_files[1]["tests/test_explorer.py"]
    after = (ROOT / "tests/test_explorer.py").read_bytes()
    if mutation == "additional_assertion":
        changed = after.replace(
            b'assert tags.count("main") == 1', b'assert tags.count("main") >= 0'
        )
    elif mutation == "extra_line":
        changed = after + b"\n# Unreviewed historical edit\n"
    elif mutation == "extra_scope":
        changed = after.replace(b'{"col", "row"}', b'{"col", "row", "invalid"}')
    elif mutation == "scope_order":
        changed = after.replace(b'{"col", "row"}', b'{"row", "col"}')
    else:
        changed = after.replace(b"\n", b"\r\n")
    assert changed != after
    assert not legacy._reviewed_explorer_header_change(before, changed)


@pytest.mark.parametrize("count", [0, 2])
def test_legacy_header_exception_requires_one_exact_original_assertion(
    pinned_legacy_files: tuple[bytes, dict[str, bytes]],
    count: int,
) -> None:
    original = b'        assert all(a.get("scope") == "col" for t, a in parser.tags if t == "th")\n'
    reviewed = (
        b'        assert all(a.get("scope") in {"col", "row"} '
        b'for t, a in parser.tags if t == "th")\n'
    )
    before = pinned_legacy_files[1]["tests/test_explorer.py"].replace(original, original * count)
    assert not legacy._reviewed_explorer_header_change(
        before, before.replace(original, reviewed, 1)
    )


@pytest.mark.parametrize(
    "mutation",
    [
        None,
        "tests/test_explorer.py",
        "tests/test_cli.py",
        "tests/test_product_presentation.py",
        "baseline",
    ],
)
def test_legacy_header_exception_preserves_full_verifier_guards(
    pinned_legacy_files: tuple[bytes, dict[str, bytes]],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str | None,
) -> None:
    raw, files = pinned_legacy_files
    root = tmp_path / "candidate"
    names = {name for name in files if name.startswith("tests/")}
    names.update({"docs/yaml-schema-v1.md", "src/otarchguard/contract.py", "pyproject.toml"})
    for name in names:
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        # Isolate the explicitly reviewed transitions; all other historical bytes
        # come directly from the pin. The real checkout is verified separately.
        reviewed = {
            "tests/test_release_candidate.py",
            "tests/test_cli.py",
            "tests/test_explorer.py",
            "tests/test_presentation.py",
            "tests/test_product_presentation.py",
        }
        target.write_bytes(
            (ROOT / name).read_bytes()
            if name in reviewed or not name.startswith("tests/")
            else files[name]
        )
    if mutation and mutation.startswith("tests/"):
        target = root / mutation
        target.write_bytes(target.read_bytes() + b"\n# Unauthorized additional edit\n")

    def archive(command: list[str], *, cwd: Path) -> bytes:
        assert command == ["git", "archive", legacy.BASELINE] and cwd == root
        return raw

    class PreflightPassed(Exception):
        pass

    def probe(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        assert command[1] == "-c" and kwargs["env"]["OTARCHGUARD_OFFLINE_CHECK"] == "1"
        if mutation != "baseline":
            raise PreflightPassed
        return subprocess.CompletedProcess(command, 0, b'{"version":"1.2.0","hashes":{}}', b"")

    monkeypatch.setattr(legacy, "ROOT", root)
    monkeypatch.setattr(subprocess, "check_output", archive)
    monkeypatch.setattr(subprocess, "run", probe)
    if mutation == "baseline":
        with pytest.raises(ValueError, match="Installed baseline differs from the pinned"):
            legacy.verify(tmp_path / "verification", Path("baseline-python"))
    elif mutation:
        with pytest.raises(ValueError, match="Unreviewed historical test change: " + mutation):
            legacy.verify(tmp_path / "verification", Path("baseline-python"))
    else:
        with pytest.raises(PreflightPassed):
            legacy.verify(tmp_path / "verification", Path("baseline-python"))


@pytest.mark.parametrize(
    "name", ["tests/test_presentation.py", "tests/test_product_presentation.py"]
)
def test_legacy_additional_presentation_exceptions_are_exact(
    pinned_legacy_files: tuple[bytes, dict[str, bytes]],
    name: str,
) -> None:
    before = pinned_legacy_files[1][name]
    after = (ROOT / name).read_bytes()
    assert legacy._reviewed_additional_presentation_change(name, before, after)
    for changed in (
        after + b"\n# Unauthorized edit\n",
        after.replace(b'if tag == "th":', b'if tag == "td":')
        if name.endswith("test_presentation.py")
        else after.replace(b"page.max_dl_depth == 1", b"page.max_dl_depth <= 9"),
        after.replace(b"\n", b"\r\n"),
    ):
        assert changed != after
        assert not legacy._reviewed_additional_presentation_change(name, before, changed)
    assert not legacy._reviewed_additional_presentation_change("tests/test_cli.py", before, after)
    if name == "tests/test_product_presentation.py":
        for clause in (
            b"Exit 0 means a supported query completed",
            b"including unreachable or mixed results.",
            b"does not assert reachability",
        ):
            assert after.count(clause) == 1
            assert not legacy._reviewed_additional_presentation_change(
                name, before, after.replace(clause, b"weakened contract", 1)
            )


@pytest.fixture(scope="module")
def approved_presentation_hashes() -> dict[str, str]:
    assert legacy.PRESENTATION == "117318393ead604a023a24bad7d53eb429faa13f"
    raw = subprocess.check_output(["git", "archive", legacy.PRESENTATION], cwd=ROOT)
    result = {}
    with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
        for member in archive.getmembers():
            if (
                member.isfile()
                and member.name.startswith("src/otarchguard/")
                and member.name.endswith(".py")
            ):
                stream = archive.extractfile(member)
                assert stream is not None
                result[member.name.removeprefix("src/otarchguard/")] = hashlib.sha256(
                    stream.read()
                ).hexdigest()
    return result


def test_legacy_presentation_pin_accepts_exact_package(
    approved_presentation_hashes: dict[str, str],
) -> None:
    legacy._check_presentation_installation(
        {"version": "1.3.0", "hashes": approved_presentation_hashes}, approved_presentation_hashes
    )


@pytest.mark.parametrize("mutation", ["renderer", "analysis", "extra", "missing", "version"])
def test_legacy_presentation_pin_rejects_unapproved_package_changes(
    approved_presentation_hashes: dict[str, str],
    mutation: str,
) -> None:
    actual = dict(approved_presentation_hashes)
    version = "1.3.0"
    if mutation in {"renderer", "analysis"}:
        actual["reporting.py" if mutation == "renderer" else "api.py"] = "0" * 64
    elif mutation == "extra":
        actual["unapproved.py"] = "1" * 64
    elif mutation == "missing":
        del actual["explorer_exposure.py"]
    else:
        version = "1.3.1"
    with pytest.raises(ValueError, match="exact approved commit"):
        legacy._check_presentation_installation(
            {"version": version, "hashes": actual}, approved_presentation_hashes
        )


def _rehash_capture(directory: Path) -> None:
    path = directory / "manifest.json"
    value = json.loads(path.read_bytes())
    value["artifacts"] = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in directory.iterdir()
        if p.is_file() and p.name != "manifest.json"
    }
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


@pytest.fixture
def reviewed_captures(tmp_path: Path) -> tuple[Path, dict[str, str], dict[str, str]]:
    # Deliberately different layouts with identical analytical evidence.
    core = {
        name: hashlib.sha256(name.encode()).hexdigest()
        for name in ("api.py", "cli.py", "reachability.py", "__init__.py")
    }
    baseline_hashes = {
        **core,
        **{
            name: "a" * 64
            for name in legacy._PRESENTATION_MODULES
            if name != "explorer_exposure.py"
        },
    }
    approved_hashes = {**core, **{name: "b" * 64 for name in legacy._PRESENTATION_MODULES}}
    for name in ("baseline", "approved", "candidate"):
        directory = tmp_path / name
        directory.mkdir()
        version = "1.2.0" if name == "baseline" else "1.3.0"
        payload = json.dumps(
            {
                "engine_version": version,
                "model_sha256": "c" * 64,
                "result": {"reachable": False, "evidence_id": "retained-evidence"},
            },
            sort_keys=True,
        )
        layout = (
            "<p>Historical fields</p>"
            if name == "baseline"
            else "<table><caption>Approved records</caption></table>"
        )
        for filename in legacy._PRESENTATION_HTML:
            (directory / filename).write_text(
                "<!doctype html>"
                + layout
                + '<section id="json-evidence"><details><pre>'
                + html.escape(payload)
                + "</pre></details></section></main>",
                encoding="utf-8",
            )
        (directory / "check.stdout").write_text(payload + "\n", encoding="utf-8")
        (directory / "diagram.svg").write_bytes(b"<svg>Unchanged declared diagram</svg>")
        record = {
            "python": "3.14",
            "platform": "synthetic",
            "production_sha256": baseline_hashes if name == "baseline" else approved_hashes,
            "inputs": {"model_sha256": "c" * 64},
            "exits": {"check": 0},
            "artifacts": {},
        }
        (directory / "manifest.json").write_text(json.dumps(record), encoding="utf-8")
        _rehash_capture(directory)
    return tmp_path, baseline_hashes, approved_hashes


def test_legacy_reviewed_capture_checks_both_contracts_without_rewriting_evidence(
    reviewed_captures: tuple[Path, dict[str, str], dict[str, str]],
) -> None:
    root, baseline, approved = reviewed_captures
    original = {
        p: p.read_bytes()
        for name in ("baseline", "approved", "candidate")
        for p in (root / name).iterdir()
    }
    result = legacy._compare_reviewed_captures(root, baseline, approved)
    assert result["status"] == "PASS" and result["historical_html_bytes_identical"] is False
    assert result["html_json_appendices_compared"] == 13
    assert len(result["approved_html_sha256"]) == 13
    assert len(result["artifacts"]) == result["count"]
    assert original == {p: p.read_bytes() for p in original}
    assert (root / "analytical-candidate/check.stdout").read_bytes() == (
        root / "candidate/check.stdout"
    ).read_bytes()


@pytest.mark.parametrize(
    "mutation", ["html", "json", "html_json", "identity", "source", "input", "exit", "unknown_html"]
)
def test_legacy_reviewed_capture_rejects_rehashed_unapproved_changes(
    reviewed_captures: tuple[Path, dict[str, str], dict[str, str]],
    mutation: str,
) -> None:
    root, baseline, approved = reviewed_captures
    candidate = root / "candidate"
    if mutation == "html":
        path = candidate / "check.html"
        path.write_bytes(path.read_bytes() + b"<p>Unapproved presentation</p>")
    elif mutation in {"json", "identity"}:
        for name in ("approved", "candidate"):
            path = root / name / "check.stdout"
            value = json.loads(path.read_bytes())
            value["result"]["reachable" if mutation == "json" else "evidence_id"] = (
                True if mutation == "json" else "forged-evidence"
            )
            path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
    elif mutation == "html_json":
        # Both modern copies agree; v1.2 must still reject the altered evidence.
        for name in ("approved", "candidate"):
            path = root / name / "check.html"
            assert path.read_bytes().count(b"false") == 1
            path.write_bytes(path.read_bytes().replace(b"false", b"true"))
    elif mutation == "unknown_html":
        for name in ("baseline", "approved", "candidate"):
            (root / name / "unreviewed.html").write_bytes(b"<!doctype html><p>Extra</p>")
    else:
        for name in ("approved", "candidate") if mutation == "exit" else ("candidate",):
            path = root / name / "manifest.json"
            value = json.loads(path.read_bytes())
            if mutation == "source":
                value["production_sha256"]["reporting.py"] = "0" * 64
            elif mutation == "input":
                value["inputs"]["model_sha256"] = "d" * 64
            else:
                value["exits"]["check"] = False
            path.write_text(json.dumps(value), encoding="utf-8")
    for name in ("baseline", "approved", "candidate"):
        _rehash_capture(root / name)
    with pytest.raises(ValueError):
        legacy._compare_reviewed_captures(root, baseline, approved)
