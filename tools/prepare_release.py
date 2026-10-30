"""Assemble or reverify four local source-bound release assets; never publish or tag."""

import argparse
import ast
import hashlib
import json
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path
from typing import Any

from tools.audit_release import audit
from tools.verify_source_checkout import verify

ROOT = Path(__file__).resolve().parents[1]


def _source(root: Path) -> dict[str, Any]:
    if subprocess.check_output(["git", "status", "--porcelain=v1"], cwd=root):
        raise ValueError("Release assembly requires a clean committed source checkout")
    names = frozenset((root / "tools/public-files.txt").read_text(encoding="utf-8").splitlines())
    source = verify(root, names)
    source["tree"] = subprocess.check_output(
        ["git", "rev-parse", "HEAD^{tree}"], cwd=root, text=True
    ).strip()
    return source


def _versions(root: Path) -> tuple[str, str]:
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    if project["version"] != "1.4.0":
        raise ValueError("This rehearsal requires reviewed distribution version 1.4.0")
    # Read literals without executing source or importing a different installed
    # package. The independent legacy gate checks the complete approved bytes.
    tree = ast.parse((root / "src/otarchguard/__init__.py").read_bytes())
    for name, expected in (("DISTRIBUTION_VERSION", "1.4.0"), ("NATIVE_ENGINE_VERSION", "1.3.0")):
        values = [
            node.value.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == name for target in node.targets)
            and isinstance(node.value, ast.Constant)
        ]
        if values != [expected]:
            raise ValueError("Source version literals differ from the reviewed release identities")
    return "1.4.0", "1.3.0"


def _names(version: str) -> tuple[str, str, str, str]:
    return (
        f"otarchguard-{version}-py3-none-any.whl",
        f"otarchguard-{version}.tar.gz",
        "release-manifest.json",
        "SHA256SUMS.txt",
    )


def verify_checksums(folder: Path, names: tuple[str, str, str, str]) -> None:
    """Require a complete, canonical checksum list and exactly four regular assets."""
    members = list(folder.iterdir())
    if {p.name for p in members} != set(names) or any(
        p.is_symlink() or not p.is_file() for p in members
    ):
        raise ValueError("Release assets must be exactly four reviewed regular files")
    expected = "".join(
        f"{hashlib.sha256((folder / name).read_bytes()).hexdigest()}  {name}\n"
        for name in names[:-1]
    ).encode("ascii")
    if (folder / names[-1]).read_bytes() != expected:
        raise ValueError(
            "Release checksums are incomplete, noncanonical or do not match asset bytes"
        )


def verify_assets(folder: Path, root: Path = ROOT) -> dict[str, Any]:
    source = _source(root)
    version, engine = _versions(root)
    names = _names(version)
    verify_checksums(folder, names)
    manifest: dict[str, Any] = json.loads((folder / names[2]).read_bytes())
    if manifest["source"] != source or manifest["distribution_version"] != version:
        raise ValueError("Release manifest does not identify the exact committed source")
    if manifest["native_engine_version"] != engine:
        raise ValueError("Release manifest has an unreviewed native engine identity")
    observed = audit(folder / names[0], folder / names[1], root)
    if manifest["archive_audit"] != observed:
        raise ValueError(
            "Release manifest archive audit differs from independently reopened assets"
        )
    expected_manifest = (
        json.dumps(_manifest(source, observed, version, engine), sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")
    if (folder / names[2]).read_bytes() != expected_manifest:
        raise ValueError("Release manifest contains unreviewed fields or acceptance claims")
    return manifest


def _manifest(
    source: dict[str, Any], observed: dict[str, Any], version: str, engine: str
) -> dict[str, Any]:
    return {
        "manifest_version": 1,
        "purpose": "Source-bound local assembly; publication requires owner authorization",
        "distribution_version": version,
        "native_engine_version": engine,
        "source": source,
        "archive_audit": observed,
        "reproducibility": (
            "Exact source and installed payload; archive byte reproducibility not asserted"
        ),
        "acceptance": (
            "Consult source-bound handoff; assembly does not imply CI, owner "
            "or integration acceptance"
        ),
    }


def prepare(output: Path, root: Path = ROOT) -> dict[str, Any]:
    source = _source(root)
    version, engine = _versions(root)
    names = _names(version)
    if output.exists() or output.is_symlink():
        raise ValueError(
            "Use a new release staging directory; existing assets are never overwritten"
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    # Only the completed audited set becomes visible at the requested destination.
    with tempfile.TemporaryDirectory(prefix="release-build-", dir=output.parent) as temporary:
        staging = Path(temporary) / "assets"
        staging.mkdir()
        subprocess.run(
            [
                sys.executable,
                "-c",
                "import sys; from setuptools import build_meta; destination=sys.argv[1]; "
                "build_meta.build_wheel(destination); build_meta.build_sdist(destination)",
                str(staging.resolve()),
            ],
            cwd=root,
            check=True,
            timeout=300,
        )
        observed = audit(staging / names[0], staging / names[1], root)
        if source != _source(root):
            raise ValueError("Release source changed during assembly")
        manifest = _manifest(source, observed, version, engine)
        (staging / names[2]).write_text(
            json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
        (staging / names[3]).write_text(
            "".join(
                f"{hashlib.sha256((staging / name).read_bytes()).hexdigest()}  {name}\n"
                for name in names[:-1]
            ),
            encoding="ascii",
            newline="\n",
        )
        verify_assets(staging, root)
        staging.rename(output)
    return verify_assets(output, root)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--verify", action="store_true", help="Reopen existing assets without rebuilding"
    )
    args = parser.parse_args()
    (verify_assets if args.verify else prepare)(args.output.absolute())
    print("Four source-bound local release assets verified; no publication performed")


if __name__ == "__main__":
    main()
