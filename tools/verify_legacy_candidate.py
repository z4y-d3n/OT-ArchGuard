"""Reproduce the immutable v1.2 native contract against a regular installed candidate."""

import argparse
import hashlib
import html
import io
import json
import os
import re
import subprocess
import sys
import sysconfig
import tarfile
from pathlib import Path
from typing import Any

from tools.compare_versioned_contract import compare_captures, compare_json

ROOT = Path(__file__).resolve().parents[1]
BASELINE = "f52c792b683cb499dc7de765b65b5cc897a96854"
PRESENTATION = "117318393ead604a023a24bad7d53eb429faa13f"
_PRESENTATION_MODULES = frozenset(
    {
        "diagrams.py",
        "explorer.py",
        "explorer_html.py",
        "explorer_exposure.py",
        "reporting.py",
        "review_explorer.py",
        "trace_reporting.py",
    }
)
_PRESENTATION_HTML = frozenset(
    {"validate.html", "check.html", "exposure.html", "compare.html", "trace.html"}
    | {
        f"trace-{case}-policy-{policy}.html"
        for case in ("mixed", "missing_permit", "explicit_deny", "absent")
        for policy in (0, 1)
    }
)


def _archive_files(raw: bytes) -> dict[str, bytes]:
    files = {}
    with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
        for member in archive.getmembers():
            if member.isfile():
                stream = archive.extractfile(member)
                assert stream is not None
                files[member.name] = stream.read()
    return files


def _module_hashes(files: dict[str, bytes]) -> dict[str, str]:
    return {
        name.removeprefix("src/otarchguard/"): hashlib.sha256(data).hexdigest()
        for name, data in files.items()
        if name.startswith("src/otarchguard/") and name.endswith(".py")
    }


def _check_presentation_installation(installed: dict[str, Any], expected: dict[str, str]) -> None:
    if installed["version"] != "1.3.0" or installed["hashes"] != expected:
        raise ValueError("Installed presentation package differs from the exact approved commit")


def _candidate_module_hashes(approved: dict[str, bytes]) -> dict[str, str]:
    """Derive candidate bytes from the immutable approval, never current HEAD.

    Exactly one distribution literal changes. Native identity, renderer bytes,
    module inventory and every other byte remain independently pinned.
    """
    name = "src/otarchguard/__init__.py"
    original = b'DISTRIBUTION_VERSION = "1.4.0.dev1"\n'
    replacement = b'DISTRIBUTION_VERSION = "1.4.0"\n'
    if approved[name].count(original) != 1:
        raise ValueError("Approved distribution source has an unexpected version literal")
    candidate = {**approved, name: approved[name].replace(original, replacement, 1)}
    return _module_hashes(candidate)


def _check_candidate_installation(installed: dict[str, Any], expected: dict[str, str]) -> None:
    """Require the stable distribution's exact regular installed source identity."""
    module = Path(installed["module"]).resolve()
    if (
        installed["version"] != "1.3.0"
        or installed["distribution_version"] != "1.4.0"
        or installed["hashes"] != expected
        or module != Path(installed["distribution_module"]).resolve()
        or module.is_relative_to(ROOT / "src")
        or installed["editable"]
    ):
        raise ValueError("Installed candidate differs from the exact reviewed transition")


def _check_candidate_source(expected: dict[str, str]) -> None:
    source = ROOT / "src/otarchguard"
    files = list(source.rglob("*.py"))
    if any(p.is_symlink() or not p.is_file() for p in files):
        raise ValueError("Candidate source must contain regular reviewed modules")
    hashes = {
        p.relative_to(source).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files
    }
    if hashes != expected:
        raise ValueError("Candidate source differs from the exact reviewed distribution transition")


def _analytical_view(source: Path, target: Path) -> None:
    """Copy analytical bytes unchanged; retain original full captures separately.

    The seven presentation module hashes and thirteen HTML files are checked
    against the independently installed approved pin before this projection.
    Only capture-provenance metadata is narrowed to describe these copied files.
    """
    files = {p.name: p.read_bytes() for p in source.iterdir() if p.is_file()}
    record = json.loads(files.pop("manifest.json"))
    actual = {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}
    if record["artifacts"] != actual:
        raise ValueError("Capture manifest hashes do not match actual bytes")
    target.mkdir()
    retained = {name: data for name, data in files.items() if name not in _PRESENTATION_HTML}
    for name, data in retained.items():
        (target / name).write_bytes(data)
    record["production_sha256"] = {
        name: digest
        for name, digest in record["production_sha256"].items()
        if name not in _PRESENTATION_MODULES
    }
    record["artifacts"] = {
        name: hashlib.sha256(data).hexdigest() for name, data in retained.items()
    }
    (target / "manifest.json").write_text(
        json.dumps(record, sort_keys=True) + "\n", encoding="utf-8"
    )


def _compare_reviewed_captures(
    output: Path,
    baseline_hashes: dict[str, str],
    approved_hashes: dict[str, str],
    candidate_hashes: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Require approved HTML bytes AND the immutable v1.2 analytical contract."""
    baseline, candidate, approved = (
        output / name for name in ("baseline", "candidate", "approved")
    )
    for folder, hashes in (
        (baseline, baseline_hashes),
        (approved, approved_hashes),
        (candidate, approved_hashes if candidate_hashes is None else candidate_hashes),
    ):
        if {p.name for p in folder.glob("*.html")} != _PRESENTATION_HTML:
            raise ValueError("Unreviewed HTML capture inventory")
        manifest = json.loads((folder / "manifest.json").read_bytes())
        if manifest["production_sha256"] != {
            name: value for name, value in hashes.items() if "/" not in name
        }:
            raise ValueError("Capture source identity differs from its exact Git pin")
    # This is an exact-output comparison, not a generic exception for HTML.
    presentation = compare_captures(approved, candidate, old="1.3.0", new="1.3.0")
    pattern = (
        r'(<section id="(?:json-evidence|json)">.*?<pre>)(.*?)(</pre></details></section></main>)'
    )
    html_hashes = {}
    for name in sorted(_PRESENTATION_HTML):
        left, right = (folder / name for folder in (baseline, candidate))
        a, b = (
            list(re.finditer(pattern, path.read_text(encoding="utf-8"), re.S))
            for path in (left, right)
        )
        if len(a) != 1 or len(b) != 1:
            raise ValueError("Expected exactly one complete HTML JSON appendix")
        compare_json(
            html.unescape(a[0][2]).encode(), html.unescape(b[0][2]).encode(), "1.2.0", "1.3.0"
        )
        html_hashes[name] = hashlib.sha256(right.read_bytes()).hexdigest()
    for source, target in ((baseline, "analytical-baseline"), (candidate, "analytical-candidate")):
        _analytical_view(source, output / target)
    analytical = compare_captures(
        output / "analytical-baseline",
        output / "analytical-candidate",
        old="1.2.0",
        new="1.3.0",
        allowed_module_changes=frozenset({"cli.py", "reachability.py"}),
    )
    analytical["artifacts"].update(
        {name: "APPROVED_PRESENTATION_EXACT_BYTES" for name in html_hashes}
    )
    analytical.update(
        count=presentation["count"],
        baseline=str(baseline),
        candidate=str(candidate),
        presentation_reference_commit=PRESENTATION,
        approved_presentation_comparison=presentation,
        approved_html_sha256=html_hashes,
        analytical_artifact_count=analytical["count"] - 1,
        html_json_appendices_compared=len(html_hashes),
        historical_html_bytes_identical=False,
    )
    return analytical


def _reviewed_explorer_header_change(before: bytes, after: bytes) -> bool:
    """Allow one exact row-header assertion edit; every other byte must match."""
    original = b'        assert all(a.get("scope") == "col" for t, a in parser.tags if t == "th")\n'
    reviewed = (
        b'        assert all(a.get("scope") in {"col", "row"} '
        b'for t, a in parser.tags if t == "th")\n'
    )
    return before.count(original) == 1 and before.replace(original, reviewed, 1) == after


def _reviewed_additional_presentation_change(name: str, before: bytes, after: bytes) -> bool:
    """Allow only the two additional, explicitly reviewed presentation-test diffs."""
    changes: tuple[tuple[bytes, bytes], ...]
    if name == "tests/test_presentation.py":
        changes = (
            (
                b'                assert ("scope", "col") in attrs\n',
                b'                assert ("scope", "col") in attrs or ("scope", "row") in attrs\n',
            ),
        )
    elif name == "tests/test_product_presentation.py":
        changes = (
            (
                b"    assert page.max_dl_depth == 3 and page.dl_depth == 0\n",
                b"    assert page.max_dl_depth == 1 and page.dl_depth == 0\n",
            ),
            (
                b'    assert page.tags.count("dt") == page.tags.count("dd") == 8\n'
                b'    assert ".properties>dd{margin:0;min-width:0}" in CSS\n',
                b'    assert page.tags.count("dt") == page.tags.count("dd") == 5\n'
                b'    assert ".compact-fields>div>dt,.compact-fields>div>dd{display:inline" '
                b"in CSS\n"
                b'    assert ".compact-fields{display:flex" in CSS\n'
                b'    assert "grid-template-columns:fit-content(35%)" not in CSS\n',
            ),
        )
    else:
        return False
    expected = before
    for original, reviewed in changes:
        if expected.count(original) != 1:
            return False
        expected = expected.replace(original, reviewed, 1)
    return expected == after


def verify(output: Path, baseline_python: Path | None = None) -> dict[str, Any]:
    """Use fresh output; baseline installation may share approved dependency packages."""
    output.mkdir(parents=True, exist_ok=False)
    archive_bytes = subprocess.check_output(["git", "archive", BASELINE], cwd=ROOT)
    baseline = _archive_files(archive_bytes)
    expected = _module_hashes(baseline)
    historical_tests = [name for name in baseline if name.startswith("tests/")]
    for name in historical_tests:
        before, after = baseline[name], (ROOT / name).read_bytes()
        if name == "tests/test_release_candidate.py":
            before = before.replace(
                b'RELEASE_VERSION = "1.2.0"',
                b'RELEASE_VERSION = "1.4.0"\nENGINE_VERSION = "1.3.0"',
            )
            for field in (
                b"__version__",
                b'legacy["engine_version"]',
                b"trace.engine_version",
                b'payload["engine_version"]',
            ):
                before = before.replace(
                    field + b" == RELEASE_VERSION", field + b" == ENGINE_VERSION"
                )
        if name == "tests/test_cli.py":
            before = before.replace(
                b"from otarchguard import __version__",
                b"from otarchguard import DISTRIBUTION_VERSION as __version__",
            )
        if name == "tests/test_explorer.py" and _reviewed_explorer_header_change(before, after):
            before = after
        if _reviewed_additional_presentation_change(name, before, after):
            before = after
        if before != after:
            raise ValueError(f"Unreviewed historical test change: {name}")
    for name in ("docs/yaml-schema-v1.md", "src/otarchguard/contract.py"):
        if baseline[name] != (ROOT / name).read_bytes():
            raise ValueError(f"Historical native contract changed: {name}")
    project = baseline["pyproject.toml"].replace(b'version = "1.2.0"', b'version = "1.4.0"')
    if project != (ROOT / "pyproject.toml").read_bytes():
        raise ValueError("Project changes exceed the approved package version transition")
    environment = {
        **os.environ,
        "OTARCHGUARD_OFFLINE_CHECK": "1",
        "PYTHONPATH": str(ROOT / "tools/offline"),
        "PIP_NO_INDEX": "1",
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
    }
    commands = []

    def run(python: Path, *args: str, timeout: int = 300) -> bytes:
        command = [str(python), *args]
        result = subprocess.run(
            command, cwd=ROOT, env=environment, capture_output=True, timeout=timeout
        )
        commands.append({"command": command, "exit": result.returncode})
        number = len(commands)
        (output / f"command-{number}.stdout").write_bytes(result.stdout)
        (output / f"command-{number}.stderr").write_bytes(result.stderr)
        if result.returncode:
            raise RuntimeError(f"Historical verification command {number} failed")
        return result.stdout

    def install_reference(raw: bytes, name: str) -> Path:
        source = output / (name + "-source")
        source.mkdir()
        # Both sources are immutable local Git pins, never external archives.
        with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
            archive.extractall(source, filter="data")
        env = output / (name + "-env")
        run(Path(sys.executable), "-m", "venv", "--system-site-packages", str(env))
        python = env / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        site = Path(
            json.loads(
                run(
                    python,
                    "-c",
                    "import json,sysconfig; print(json.dumps(sysconfig.get_path('purelib')))",
                )
            )
        )
        if not site.resolve().is_relative_to(env.resolve()):
            raise ValueError("Reference dependencies must stay inside the reference environment")
        # Share already installed dependency packages even when this verifier is
        # itself running in a virtual environment. The reference's own package
        # takes precedence; the source/hash and installation-path checks bind it.
        (site / "approved-dependencies.pth").write_text(
            sysconfig.get_path("purelib") + "\n", encoding="utf-8"
        )
        run(
            python,
            "-m",
            "pip",
            "install",
            "--no-index",
            "--no-deps",
            "--no-cache-dir",
            "--no-build-isolation",
            "--ignore-installed",
            str(source),
        )
        return python

    if baseline_python is None:
        baseline_python = install_reference(archive_bytes, "baseline")
    probe = (
        "import hashlib,json,pathlib,otarchguard,importlib.metadata as m; "
        "r=pathlib.Path(otarchguard.__file__).parent; "
        "d=m.distribution('otarchguard'); "
        "print(json.dumps({'version':otarchguard.__version__,"
        "'distribution_version':d.version,"
        "'distribution_module':str(d.locate_file('otarchguard')),"
        "'editable':json.loads(d.read_text('direct_url.json') or '{}')"
        ".get('dir_info',{}).get('editable',False),"
        "'module':str(r),'hashes':{p.relative_to(r).as_posix():"
        "hashlib.sha256(p.read_bytes()).hexdigest() for p in r.rglob('*.py')}},sort_keys=True))"
    )
    installed = json.loads(run(baseline_python, "-c", probe))
    if installed["version"] != "1.2.0" or installed["hashes"] != expected:
        raise ValueError("Installed baseline differs from the pinned immutable Git tree")
    presentation_archive = subprocess.check_output(["git", "archive", PRESENTATION], cwd=ROOT)
    approved_files = _archive_files(presentation_archive)
    approved_hashes = _module_hashes(approved_files)
    candidate_hashes = _candidate_module_hashes(approved_files)
    _check_candidate_source(candidate_hashes)
    if (ROOT / "tools/capture_contract.py").read_bytes() != approved_files[
        "tools/capture_contract.py"
    ]:
        raise ValueError("Capture utility differs from the approved presentation commit")
    approved_python = install_reference(presentation_archive, "approved")
    for python in (approved_python, Path(sys.executable)):
        observed = json.loads(run(python, "-c", probe))
        if python == approved_python:
            _check_presentation_installation(observed, approved_hashes)
        else:
            _check_candidate_installation(observed, candidate_hashes)
        if python == approved_python and not Path(observed["module"]).is_relative_to(
            approved_python.parent.parent
        ):
            raise ValueError(
                "Approved presentation package must be installed in its own environment"
            )
    for python, name in (
        (baseline_python, "baseline"),
        (approved_python, "approved"),
        (Path(sys.executable), "candidate"),
    ):
        run(python, "-m", "tools.capture_contract", str(output / name), timeout=600)
    comparison = _compare_reviewed_captures(output, expected, approved_hashes, candidate_hashes)
    comparison.update(
        baseline_commit=BASELINE,
        baseline_installed_module=installed["module"],
        baseline_module_sha256=expected,
        approved_package_sha256=approved_hashes,
        candidate_package_sha256=candidate_hashes,
        distribution_transition="1.4.0.dev1 -> 1.4.0; __init__.py literal only",
        historical_test_files=len(historical_tests),
        historical_test_exception=(
            "Exact distribution assertion, four fixed 1.3.0 engine/API assertions, "
            "CLI version-test import, and exact reviewed presentation assertions in "
            "test_explorer.py, test_presentation.py and test_product_presentation.py only"
        ),
        commands=commands,
    )
    (output / "comparison.json").write_text(
        json.dumps(comparison, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    return comparison


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--baseline-python", type=Path)
    args = parser.parse_args()
    result = verify(args.output.resolve(), args.baseline_python)
    print(
        f"Native analytical compatibility PASS: {result['analytical_artifact_count']} artifacts; "
        f"approved presentation PASS: {result['html_json_appendices_compared']} HTML files"
    )


if __name__ == "__main__":
    main()
