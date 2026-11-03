"""V15-02 policy 1: exact reviewed source plus independent predecessor outputs.

This policy is reviewed code, not a signature. Never read authorization hashes
from candidate receipts. Later gates require a new versioned policy.
"""

import argparse
import hashlib
import importlib.metadata as metadata
import io
import json
import os
import subprocess
import sys
import sysconfig
import tarfile
from pathlib import Path
from typing import Any

from tools.compare_versioned_contract import compare_captures
from tools.verify_legacy_candidate import _archive_files, _module_hashes

ROOT = Path(__file__).resolve().parents[1]
PREDECESSOR = "b3adcc9de21dfff6ad58946028a241844ff88294"
REVIEWED = "867516be2c274a12d251c89bc0310a441b91da45"
VERSION = "1.5.0.dev1"
RENDERER = "1.5.0.dev1-historical-explorer.1"
# Explicit reviewed replacements; never generated or loaded during verification.
CHANGED = {
    "__init__.py": "91cd2607f08d671a1468ee9919cd64617cd0fe86a3dcd5828c9d3c047ffa8626",
    "drift/explorer_render.py": "992d28705eaf4ccb0035016ac743b3a95955d0760851d54dd748503f456868d0",
    "drift/explorer_bundle.py": "107c20d7d1eb3bf22c8b4f6184dda9de5fed4fdfec14161c5a77e89948b75ad4",
    "reporting.py": "1354cd77579e36911b59ab0618ee173fa687fff96ef410219d60d8d78136c85d",
}
RENDERER_SHA256 = "442d13378cd61586664e19f51ea6834537b0155c07e48ff5a6173628c5d6ca6b"


def reference() -> dict[str, bytes]:
    trees = [
        subprocess.check_output(["git", "rev-parse", ref + "^{tree}"], cwd=ROOT).strip()
        for ref in (PREDECESSOR, REVIEWED)
    ]
    if trees != [b"b2a2ec908d02cc36339a7a3d2d3cd736671db3e0"] * 2:
        raise ValueError("Unexpected immutable predecessor tree")
    return _archive_files(subprocess.check_output(["git", "archive", PREDECESSOR], cwd=ROOT))


def expected_modules(before: dict[str, bytes]) -> dict[str, str]:
    original = _module_hashes(before)
    if len(original) != 97 or not CHANGED.keys() <= original.keys():
        raise ValueError("Unexpected predecessor module inventory")
    return {**original, **CHANGED}


def module_hashes(source: Path) -> dict[str, str]:
    if source.is_symlink() or not source.is_dir():
        raise ValueError("Runtime source must be a regular directory")
    result = {}
    for path in source.rglob("*"):
        if "__pycache__" in path.relative_to(source).parts:
            continue
        if path.is_symlink():
            raise ValueError("Runtime source must be regular")
        if path.is_file():
            if path.suffix != ".py":
                raise ValueError("Unknown runtime source member")
            result[path.relative_to(source).as_posix()] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
    return result


def check_source(root: Path, before: dict[str, bytes]) -> dict[str, Any]:
    expected = expected_modules(before)
    if module_hashes(root / "src/otarchguard") != expected:
        raise ValueError("Source differs from exact reviewed V15-02 modules")
    protected = {
        name: data
        for name, data in before.items()
        if name.startswith(("tests/", "tools/"))
        and name != "tools/public-files.txt"
        or name == "docs/yaml-schema-v1.md"
    }
    for name in ("tests/test_v141_identity.py", "tests/test_release_candidate.py"):
        old = (
            b'assert DISTRIBUTION_VERSION == "1.4.0"'
            if name.endswith("test_v141_identity.py")
            else b'RELEASE_VERSION = "1.4.0"'
        )
        if protected[name].count(old) != 1:
            raise ValueError("Unexpected predecessor distribution assertion")
        protected[name] = protected[name].replace(old, old.replace(b"1.4.0", VERSION.encode()), 1)
    for name, data in protected.items():
        path = root / name
        if path.is_symlink() or not path.is_file() or path.read_bytes() != data:
            raise ValueError(f"Protected predecessor evidence changed: {name}")
    project = before["pyproject.toml"]
    token = b'version = "1.4.0"'
    if project.count(token) != 1 or (root / "pyproject.toml").read_bytes() != project.replace(
        token, token.replace(b"1.4.0", VERSION.encode()), 1
    ):
        raise ValueError("Unapproved project metadata transition")
    original = _module_hashes(before)
    return {
        "policy": "V15-02.1",
        "predecessor": PREDECESSOR,
        "reviewed_predecessor": REVIEWED,
        "changed": {n: {"before": original[n], "after": expected[n]} for n in sorted(CHANGED)},
        "unchanged": {n: h for n, h in expected.items() if n not in CHANGED},
        "additions": [],
        "removals": [],
        "protected_predecessor_files": len(protected),
    }


def check_installation(expected: dict[str, str]) -> dict[str, Any]:
    import otarchguard
    from otarchguard.drift import explorer

    distribution = metadata.distribution("otarchguard")
    module = Path(otarchguard.__file__).resolve().parent
    direct = json.loads(distribution.read_text("direct_url.json") or "{}")
    if (
        distribution.version != VERSION
        or otarchguard.DISTRIBUTION_VERSION != VERSION
        or otarchguard.NATIVE_ENGINE_VERSION != "1.3.0"
        or otarchguard.__version__ != "1.3.0"
        or module != Path(str(distribution.locate_file("otarchguard"))).resolve()
        or module.is_relative_to(ROOT / "src")
        or direct.get("dir_info", {}).get("editable", False)
        or module_hashes(module) != expected
        or explorer.RENDERER_VERSION != RENDERER
        or explorer._renderer_identity() != RENDERER_SHA256
    ):
        raise ValueError("Installed candidate differs from exact reviewed V15-02 identity")
    return {
        "module": str(module),
        "distribution": distribution.version,
        "native_engine": otarchguard.NATIVE_ENGINE_VERSION,
        "renderer": explorer.RENDERER_VERSION,
        "renderer_sha256": explorer._renderer_identity(),
        "module_sha256": expected,
    }


def verify(output: Path) -> dict[str, Any]:
    before = reference()
    source = check_source(ROOT, before)
    installed = check_installation(expected_modules(before))
    output.mkdir(parents=True, exist_ok=False)
    commands: list[dict[str, Any]] = []
    environment = {
        **os.environ,
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
        "PIP_NO_INDEX": "1",
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "OTARCHGUARD_OFFLINE_CHECK": "1",
    }

    def run(command: list[str], cwd: Path, *, historical_git: bool = False) -> bytes:
        env = {**environment, "PYTHONPATH": str(cwd / "tools/offline")}
        if historical_git:
            env["GIT_DIR"] = subprocess.check_output(
                ["git", "rev-parse", "--absolute-git-dir"], cwd=ROOT, text=True
            ).strip()
        result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, timeout=1200)
        number = len(commands) + 1
        commands.append({"command": command, "cwd": str(cwd), "exit": result.returncode})
        (output / f"command-{number}.stdout").write_bytes(result.stdout)
        (output / f"command-{number}.stderr").write_bytes(result.stderr)
        (output / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        if result.returncode:
            raise RuntimeError(f"Transition command {number} failed; inspect retained receipts")
        return result.stdout

    predecessor = output / "predecessor-source"
    predecessor.mkdir()
    raw = subprocess.check_output(["git", "archive", PREDECESSOR], cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
        archive.extractall(predecessor, filter="data")
    env_path = output / "predecessor-env"
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
        raise ValueError("Reference environment escaped its reserved directory")
    (site / "approved-dependencies.pth").write_text(sysconfig.get_path("purelib") + "\n")
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
    historical = output / "historical-v14"
    run(
        [
            str(python),
            "-m",
            "tools.verify_legacy_candidate",
            "--output",
            str(historical),
        ],
        predecessor,
        historical_git=True,
    )
    candidate = output / "candidate-native"
    run([sys.executable, "-m", "tools.capture_contract", str(candidate)], ROOT)
    native = compare_captures(
        historical / "candidate",
        candidate,
        old="1.3.0",
        new="1.3.0",
        allowed_module_changes=frozenset({"reporting.py"}),
    )
    if any(v != "EXACT_BYTES" for n, v in native["artifacts"].items() if n != "manifest.json"):
        raise ValueError("V15 native outputs must retain exact predecessor bytes")
    for folder, expected in (
        (historical / "candidate", _module_hashes(before)),
        (candidate, expected_modules(before)),
    ):
        observed = json.loads((folder / "manifest.json").read_bytes())["production_sha256"]
        if observed != {n: h for n, h in expected.items() if "/" not in n}:
            raise ValueError("Native capture source identity is not the reviewed installation")
    # Produce a real predecessor workspace and bundle with its own regular
    # installation, then challenge it with the new installed consumer.
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
    from otarchguard.evidence import lifecycle, revisions

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
        raise ValueError("Old producer acquired new source replay authority")
    old_recovery = json.loads(
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
    if not old_recovery["analytical_reproduction"] or original_inventory != inventory():
        raise ValueError("Historical recovery failed or changed original evidence")
    old_revision = selection["periods"]["reference"]["analysis_id"]
    if (
        revisions.implementation_identities()["__init__.py"]
        == _module_hashes(before)["__init__.py"]
    ):
        raise ValueError("New producer failed to bind development source")
    cross_result = {
        "portable": portable,
        "new_source_replay_rejection": code,
        "old_source_recovery": old_recovery,
        "old_analysis_id": old_revision,
        "historical_files_unchanged": True,
        "historical_inventory_sha256": original_inventory,
        "approval_transferred": False,
    }
    result = {
        "status": "PASS",
        "source": source,
        "installed": installed,
        "native": native,
        "historical": json.loads((historical / "comparison.json").read_bytes()),
        "cross_producer": cross_result,
        "commands": commands,
    }
    (output / "transition.json").write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-only", action="store_true")
    args = parser.parse_args()
    if args.source_only:
        result = check_source(ROOT, reference())
        result["installed"] = check_installation(expected_modules(reference()))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    else:
        verify(args.output.resolve())
    print("V15-02 exact reviewed transition PASS")


if __name__ == "__main__":
    main()
