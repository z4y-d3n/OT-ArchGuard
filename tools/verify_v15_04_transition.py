"""V15-04 policy 1: reviewed bounded text-validation delta over the exact merged V15-03.

This reviewed policy is an authorization boundary, not a signature. Never derive
authorization from candidate receipts. V15-03 remains a separate historical gate.
"""

import sys

if __name__ == "__main__" and not sys.flags.isolated:
    raise SystemExit("Use python -I tools/verify_v15_04_transition.py")

import argparse
import hashlib
import importlib.metadata as metadata
import io
import json
import os
import shutil
import subprocess
import sysconfig
import tarfile
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PREDECESSOR = "18cb7e84ef16871daf857af48e3cd003ec8200ba"
TREE = "0b512bce31da2b0d9b10160b1a8cdc13ec23fab4"
VERSION = "1.5.0.dev3"
# No bound Historical renderer source changes in this gate.
RENDERER = "1.5.0.dev1-historical-explorer.1"
CHANGED = {
    "__init__.py": "7ccf2c03974ffdadc0fc1f6d1a2af50c88cb53b937002bf616399adc9ecdffdc",
    "explorer_data.py": "d501ecb1a00488a081c39b6fa3e4560d9e9565b7f8a3c8562797ca2e9abeb715",
}


def git_output(*args: str) -> bytes:
    executable = shutil.which("git")
    if executable is None or Path(executable).resolve().is_relative_to(ROOT):
        raise ValueError("Trusted Git outside candidate checkout required")
    return subprocess.check_output([str(Path(executable).resolve()), *args], cwd=ROOT)


def reference() -> dict[str, bytes]:
    if git_output("rev-parse", PREDECESSOR + "^{tree}").decode().strip() != TREE:
        raise ValueError("Unexpected immutable V15-03 tree")
    files = {}
    with tarfile.open(fileobj=io.BytesIO(git_output("archive", PREDECESSOR))) as archive:
        for member in archive.getmembers():
            if member.isfile():
                stream = archive.extractfile(member)
                if stream is None:
                    raise ValueError("Unreadable immutable source")
                files[member.name] = stream.read()
    return files


def trusted_helpers(before: dict[str, bytes]) -> dict[str, Any]:
    # Compile authenticated Git bytes directly, never a mutable helper or .pyc.
    namespace: dict[str, Any] = {
        "__name__": "v15_04_immutable_helpers",
        "__file__": str(ROOT / "tools/verify_v15_transition.py"),
    }
    exec(compile(before["tools/verify_v15_transition.py"], "immutable-v15-02", "exec"), namespace)
    namespace["VERSION"] = VERSION
    return namespace


def expected_modules(before: dict[str, bytes]) -> dict[str, str]:
    original = {
        name.removeprefix("src/otarchguard/"): hashlib.sha256(data).hexdigest()
        for name, data in before.items()
        if name.startswith("src/otarchguard/") and name.endswith(".py")
    }
    if len(original) != 97 or not CHANGED.keys() <= original.keys():
        raise ValueError("Unexpected predecessor inventory")
    return {**original, **CHANGED}


def check_source(root: Path, before: dict[str, bytes]) -> dict[str, Any]:
    helpers = trusted_helpers(before)
    expected = expected_modules(before)
    if helpers["module_hashes"](root / "src/otarchguard") != expected:
        raise ValueError("Source differs from exact reviewed V15-04 modules")
    protected = {
        name: data
        for name, data in before.items()
        if name.startswith(("tests/", "tools/"))
        and name != "tools/public-files.txt"
        or name in {"docs/yaml-schema-v1.md", "pyproject.toml"}
    }
    for name in (
        "tests/test_v141_identity.py",
        "tests/test_release_candidate.py",
        "pyproject.toml",
    ):
        token = b'"1.5.0.dev2"'
        if protected[name].count(token) != 1:
            raise ValueError("Unexpected predecessor version literal")
        protected[name] = protected[name].replace(token, b'"1.5.0.dev3"', 1)
    for name, data in protected.items():
        path = root / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Protected source missing: {name}")
        if path.read_bytes() != data:
            raise ValueError(f"Protected predecessor evidence changed: {name}")
    return {
        "policy": "V15-04.1",
        "predecessor": PREDECESSOR,
        "tree": TREE,
        "changed": {
            n: {
                "before": hashlib.sha256(before["src/otarchguard/" + n]).hexdigest(),
                "after": expected[n],
            }
            for n in sorted(CHANGED)
        },
        "unchanged": {n: h for n, h in expected.items() if n not in CHANGED},
        "protected_predecessor_files": len(protected),
        "additions": [],
        "removals": [],
    }


def check_installation(before: dict[str, bytes]) -> dict[str, Any]:
    # Immutable V15-03 archived helper hashes every physical installed source BEFORE import.
    return trusted_helpers(before)["check_installation"](expected_modules(before))  # type: ignore[no-any-return]


def verify(output: Path) -> dict[str, Any]:
    before = reference()
    source = check_source(ROOT, before)
    installed = check_installation(before)
    output.mkdir(parents=True, exist_ok=False)
    commands: list[dict[str, Any]] = []
    environment = {
        **os.environ,
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
        "PIP_NO_INDEX": "1",
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "OTARCHGUARD_OFFLINE_CHECK": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPYCACHEPREFIX": str(output / "cache"),
        "GIT_DIR": git_output("rev-parse", "--absolute-git-dir").decode().strip(),
    }

    def run(command: list[str], cwd: Path) -> bytes:
        result = subprocess.run(
            command,
            cwd=cwd,
            env={**environment, "PYTHONPATH": str(cwd / "tools/offline")},
            capture_output=True,
            timeout=1800,
        )
        index = len(commands) + 1
        commands.append({"command": command, "cwd": str(cwd), "exit": result.returncode})
        (output / f"command-{index}.stdout").write_bytes(result.stdout)
        (output / f"command-{index}.stderr").write_bytes(result.stderr)
        (output / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        if result.returncode:
            raise RuntimeError(f"V15-04 command {index} failed; inspect retained logs")
        return result.stdout

    predecessor = output / "predecessor"
    predecessor.mkdir()
    with tarfile.open(fileobj=io.BytesIO(git_output("archive", PREDECESSOR))) as archive:
        archive.extractall(predecessor, filter="data")
    env_path = output / "dev2-env"
    run([sys.executable, "-m", "venv", "--system-site-packages", str(env_path)], ROOT)
    python = env_path / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    site = Path(
        json.loads(
            run(
                [
                    str(python),
                    "-c",
                    "import json,sysconfig;print(json.dumps(sysconfig.get_path('purelib')))",
                ],
                predecessor,
            )
        )
    )
    if not site.resolve().is_relative_to(env_path.resolve()):
        raise ValueError("Reference environment escaped output")
    dependency_site = Path(sysconfig.get_path("purelib")).resolve()
    for dependency in metadata.distributions():
        if dependency.metadata["Name"].lower() == "otarchguard":
            continue
        for member in dependency.files or ():
            original = Path(str(dependency.locate_file(member))).resolve()
            if (
                not original.is_relative_to(dependency_site)
                or not original.is_file()
                or original.suffix == ".pyc"
            ):
                continue
            target = site / original.relative_to(dependency_site)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(original, target)
    run(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--no-index",
            "--no-deps",
            "--no-cache-dir",
            "--no-build-isolation",
            "--ignore-installed",
            str(predecessor),
        ],
        predecessor,
    )
    historical = output / "v15-03"
    run(
        [
            str(python),
            "-I",
            str(predecessor / "tools/verify_v15_03_transition.py"),
            "--output",
            str(historical),
        ],
        predecessor,
    )
    run(
        [
            str(python),
            "-m",
            "pytest",
            "tests/test_v15_03_transition.py",
            "-q",
            "--tb=short",
            "--basetemp=" + str(output / "historical-tests-tmp"),
            "--junitxml=" + str(output / "historical-tests.xml"),
        ],
        predecessor,
    )
    candidate = output / "candidate-native"
    run(
        [
            sys.executable,
            "-I",
            "-B",
            "-X",
            f"pycache_prefix={output / 'native-cache'}",
            str(ROOT / "tools/capture_contract.py"),
            str(candidate),
        ],
        ROOT,
    )
    oracle: dict[str, Any] = {"__name__": "immutable_native_oracle"}
    exec(
        compile(before["tools/compare_versioned_contract.py"], "immutable-comparator", "exec"),
        oracle,
    )
    native = oracle["compare_captures"](
        historical / "candidate-native",
        candidate,
        old="1.3.0",
        new="1.3.0",
        allowed_module_changes=frozenset(),
    )
    if any(v != "EXACT_BYTES" for n, v in native["artifacts"].items() if n != "manifest.json"):
        raise ValueError("Canonical native result changed")
    cross = output / "old-producer"
    script = (
        "import json;from pathlib import Path;"
        "from tools.drift_walkthrough import prepare,comparison_context,canonical;"
        "from otarchguard.drift.engine import compare;"
        "from otarchguard.drift.explorer import generate_explorer;"
        f"r=Path({str(cross)!r});r.mkdir();s=prepare(r/'sources',variations=False);"
        "w=Path(s['workspace']);a=s['periods']['reference']['analysis_id'];"
        "b=s['periods']['candidate']['analysis_id'];"
        "d=compare(w,s['baseline_id'],[b],comparison_context(a,b,s['scope']));"
        "p=r/'report.json';p.write_bytes(canonical(d)+b'\\n');"
        "generate_explorer(w,p,r/'site');print(json.dumps(s))"
    )
    selection = json.loads(run([str(python), "-c", script], predecessor))
    from otarchguard.diagnostics import ModelError
    from otarchguard.drift.explorer import verify_explorer
    from otarchguard.evidence import lifecycle

    workspace = Path(selection["workspace"])

    def inventory() -> dict[str, str]:
        return {
            p.relative_to(cross).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in cross.rglob("*")
            if p.is_file()
        }

    original_inventory = inventory()
    portable = verify_explorer(cross / "site")
    try:
        lifecycle.load_state(workspace)
    except ModelError as error:
        code = error.diagnostics[0].code
        if code != "EVIDENCE_REVISION":
            raise
    else:
        raise ValueError("Old producer acquired new replay authority")
    recovery = json.loads(
        run(
            [
                str(python),
                "-c",
                "import json;from pathlib import Path;"
                "from otarchguard.drift.explorer import verify_explorer;"
                f"print(json.dumps(verify_explorer(Path({str(cross / 'site')!r}),"
                f"workspace=Path({str(workspace)!r}))))",
            ],
            predecessor,
        )
    )
    if not recovery["analytical_reproduction"] or inventory() != original_inventory:
        raise ValueError("Old source recovery failed or modified historical evidence")
    result = {
        "status": "PASS",
        "source": source,
        "installed": installed,
        "native": native,
        "historical_v15_03": json.loads((historical / "transition.json").read_bytes()),
        "cross_producer": {
            "portable": portable,
            "new_replay_rejection": code,
            "old_source_recovery": recovery,
            "historical_files_unchanged": True,
            "approval_transferred": False,
            "inventory": original_inventory,
        },
        "commands": commands,
    }
    (output / "transition.json").write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-only", action="store_true")
    args = parser.parse_args()
    parent = args.output.resolve().parent
    parent.mkdir(parents=True, exist_ok=True)
    prefix, write = sys.pycache_prefix, sys.dont_write_bytecode
    with tempfile.TemporaryDirectory(prefix="v15-04-verified-", dir=parent) as cache:
        sys.pycache_prefix, sys.dont_write_bytecode = cache, True
        try:
            if args.source_only:
                before = reference()
                result = {
                    "source": check_source(ROOT, before),
                    "installed": check_installation(before),
                    "scope": "source_and_installation_only",
                }
                args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
            else:
                verify(args.output.resolve())
        finally:
            sys.pycache_prefix, sys.dont_write_bytecode = prefix, write
    print("V15-04 source/installation PASS" if args.source_only else "V15-04 transition PASS")


if __name__ == "__main__":
    main()
