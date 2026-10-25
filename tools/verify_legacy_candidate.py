"""Reproduce the immutable v1.2 native contract against a regular installed candidate."""

import argparse
import hashlib
import io
import json
import os
import subprocess
import sys
import tarfile
from pathlib import Path
from typing import Any

from tools.compare_versioned_contract import compare_captures

ROOT = Path(__file__).resolve().parents[1]
BASELINE = "f52c792b683cb499dc7de765b65b5cc897a96854"


def verify(output: Path, baseline_python: Path | None = None) -> dict[str, Any]:
    """Use fresh output; baseline installation may share approved dependency packages."""
    output.mkdir(parents=True, exist_ok=False)
    archive_bytes = subprocess.check_output(["git", "archive", BASELINE], cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(archive_bytes)) as archive:
        baseline = {}
        for member in archive.getmembers():
            if member.isfile():
                stream = archive.extractfile(member)
                assert stream is not None
                baseline[member.name] = stream.read()
    expected = {
        name.removeprefix("src/otarchguard/"): hashlib.sha256(data).hexdigest()
        for name, data in baseline.items()
        if name.startswith("src/otarchguard/") and name.endswith(".py")
    }
    historical_tests = [name for name in baseline if name.startswith("tests/")]
    for name in historical_tests:
        before, after = baseline[name], (ROOT / name).read_bytes()
        if name == "tests/test_release_candidate.py":
            before = before.replace(b'RELEASE_VERSION = "1.2.0"', b'RELEASE_VERSION = "1.3.0"')
        if before != after:
            raise ValueError(f"Unreviewed historical test change: {name}")
    for name in ("docs/yaml-schema-v1.md", "src/otarchguard/contract.py"):
        if baseline[name] != (ROOT / name).read_bytes():
            raise ValueError(f"Historical native contract changed: {name}")
    project = baseline["pyproject.toml"].replace(b'version = "1.2.0"', b'version = "1.3.0"')
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

    if baseline_python is None:
        source = output / "baseline-source"
        source.mkdir()
        # Source is the pinned local Git tree, not an externally supplied archive.
        with tarfile.open(fileobj=io.BytesIO(archive_bytes)) as archive:
            archive.extractall(source, filter="data")
        run(Path(sys.executable), "-m", "venv", "--system-site-packages", str(output / "env"))
        baseline_python = (
            output / "env" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        )
        run(
            baseline_python,
            "-m",
            "pip",
            "install",
            "--no-index",
            "--no-deps",
            "--no-cache-dir",
            "--no-build-isolation",
            str(source),
        )
    probe = (
        "import hashlib,json,pathlib,otarchguard; "
        "r=pathlib.Path(otarchguard.__file__).parent; "
        "print(json.dumps({'version':otarchguard.__version__,"
        "'module':str(r),'hashes':{p.relative_to(r).as_posix():"
        "hashlib.sha256(p.read_bytes()).hexdigest() for p in r.rglob('*.py')}},sort_keys=True))"
    )
    installed = json.loads(run(baseline_python, "-c", probe))
    if installed["version"] != "1.2.0" or installed["hashes"] != expected:
        raise ValueError("Installed baseline differs from the pinned immutable Git tree")
    for python, name in ((baseline_python, "baseline"), (Path(sys.executable), "candidate")):
        run(python, "-m", "tools.capture_contract", str(output / name), timeout=600)
    comparison = compare_captures(
        output / "baseline",
        output / "candidate",
        old="1.2.0",
        new="1.3.0",
        allowed_module_changes=frozenset({"cli.py", "reachability.py"}),
    )
    comparison.update(
        baseline_commit=BASELINE,
        baseline_installed_module=installed["module"],
        baseline_module_sha256=expected,
        historical_test_files=len(historical_tests),
        historical_test_exception="Exact current RELEASE_VERSION assertion only",
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
    print(f"Native compatibility PASS: {result['count']} captured files")


if __name__ == "__main__":
    main()
