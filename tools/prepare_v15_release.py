"""Assemble exactly four stable v1.5 assets from clean, authorized committed source."""

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from tools.audit_release import audit
from tools.prepare_release import _manifest, _names, _source, verify_checksums
from tools.verify_v15_06_transition import VERSION, check_source, reference

ROOT = Path(__file__).resolve().parents[1]


def _authorized_source(root: Path) -> dict[str, Any]:
    source = _source(root)
    # Distribution, engine, complete runtime inventory and historical policies
    # must match the independent V15-06 authorization, not a build receipt.
    check_source(root, reference())
    return source


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
    (verify_assets if args.verify else prepare)(args.output.resolve())
    print("Four local v1.5.0 assets verified; publication requires owner authorization")


if __name__ == "__main__":
    main()
