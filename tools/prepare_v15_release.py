"""Assemble exactly four stable v1.5 assets from clean, authorized committed source."""

import sys

if __name__ == "__main__" and not sys.flags.isolated:
    raise SystemExit("Use python -I tools/prepare_v15_release.py")

import argparse
import hashlib
import json
import subprocess
import tempfile
from functools import cache
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
_policy: dict[str, Any] = {
    "__name__": "reviewed_v15_06_policy",
    "__file__": str(ROOT / "tools/verify_v15_06_transition.py"),
}
# The reviewed entry point and policy are trusted source, never mutable .pyc.
exec(
    compile((ROOT / "tools/verify_v15_06_transition.py").read_bytes(), "reviewed-policy", "exec"),
    _policy,
)
VERSION = cast(str, _policy["VERSION"])


def reference() -> dict[str, bytes]:
    return cast(dict[str, bytes], _policy["reference"]())


def check_source(root: Path, before: dict[str, bytes]) -> dict[str, Any]:
    return cast(dict[str, Any], _policy["check_source"](root, before))


@cache
def _primitives() -> dict[str, Any]:
    """Execute authenticated predecessor helpers directly, never checkout caches."""
    before = reference()
    check_source(ROOT, before)
    namespace: dict[str, Any] = {
        "__name__": "immutable_v15_assembly",
        "__file__": str(ROOT / "tools/prepare_release.py"),
    }
    for name in ("verify_source_checkout.py", "audit_release.py", "prepare_release.py"):
        raw = before["tools/" + name]
        if name == "prepare_release.py":
            for statement in (
                b"from tools.audit_release import audit\n",
                b"from tools.verify_source_checkout import verify\n",
            ):
                if raw.count(statement) != 1:
                    raise ValueError("Unexpected authenticated release helper imports")
                raw = raw.replace(statement, b"", 1)
        exec(compile(raw, "immutable-" + name, "exec"), namespace)
    return namespace


def audit(wheel: Path, sdist: Path, root: Path) -> dict[str, Any]:
    return cast(dict[str, Any], _primitives()["audit"](wheel, sdist, root))


def _manifest(
    source: dict[str, Any], observed: dict[str, Any], version: str, engine: str
) -> dict[str, Any]:
    return cast(dict[str, Any], _primitives()["_manifest"](source, observed, version, engine))


def _names(version: str) -> tuple[str, str, str, str]:
    return cast(tuple[str, str, str, str], _primitives()["_names"](version))


def verify_checksums(folder: Path, names: tuple[str, str, str, str]) -> None:
    _primitives()["verify_checksums"](folder, names)


def _authorized_source(root: Path) -> dict[str, Any]:
    # Distribution, engine, complete runtime inventory and historical policies
    # must match the independent V15-06 authorization, not a build receipt.
    check_source(root, reference())
    return cast(dict[str, Any], _primitives()["_source"](root))


def verify_assets(folder: Path, root: Path = ROOT) -> dict[str, Any]:
    source = _authorized_source(root)
    names = _names(VERSION)
    verify_checksums(folder, names)
    observed = audit(folder / names[0], folder / names[1], root)
    expected = _manifest(source, observed, VERSION, "1.3.0")
    canonical = (json.dumps(expected, sort_keys=True, indent=2) + "\n").encode()
    if (folder / names[2]).read_bytes() != canonical:
        raise ValueError("Manifest differs from exact source/assets or invents acceptance claims")
    return expected


def prepare(output: Path, root: Path = ROOT) -> dict[str, Any]:
    source = _authorized_source(root)
    names = _names(VERSION)
    if output.exists() or output.is_symlink():
        raise ValueError("Use a fresh destination; release assets are never overwritten")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="v15-release-", dir=output.parent) as temporary:
        staging = Path(temporary) / "assets"
        staging.mkdir()
        subprocess.run(
            [
                sys.executable,
                "-c",
                "import sys;from setuptools import build_meta;destination=sys.argv[1];"
                "build_meta.build_wheel(destination);build_meta.build_sdist(destination)",
                str(staging.resolve()),
            ],
            cwd=root,
            check=True,
            timeout=300,
        )
        observed = audit(staging / names[0], staging / names[1], root)
        if _authorized_source(root) != source:
            raise ValueError("Source changed during assembly")
        manifest = _manifest(source, observed, VERSION, "1.3.0")
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
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    (verify_assets if args.verify else prepare)(args.output.absolute())
    print("Four local v1.5.0 assets verified; publication requires owner authorization")


if __name__ == "__main__":
    main()
