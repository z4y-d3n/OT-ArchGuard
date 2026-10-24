"""Require exact public-file bytes from the Git commit before building a candidate."""

import argparse
import hashlib
import io
import json
import subprocess
from pathlib import Path


def verify(root: Path, names: frozenset[str]) -> dict[str, object]:
    ordered = sorted(names)
    if any("\n" in n or "\r" in n for n in ordered):
        raise ValueError("Unsafe public source name")
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode().split("\0")
    if set(filter(None, tracked)) != names:
        raise ValueError("Tracked source differs from the public allowlist")
    result = subprocess.run(
        ["git", "cat-file", "--batch"],
        input="".join("HEAD:" + n + "\n" for n in ordered).encode(),
        cwd=root,
        capture_output=True,
        check=True,
    )
    stream = io.BytesIO(result.stdout)
    canonical = {}
    actual = {}
    for name in ordered:
        header = stream.readline().split()
        if len(header) != 3 or header[1] != b"blob":
            raise ValueError("Public file is missing from the committed source")
        size = int(header[2])
        data = stream.read(size)
        if len(data) != size or stream.read(1) != b"\n":
            raise ValueError("Invalid committed source response")
        canonical[name] = hashlib.sha256(data).hexdigest()
        source = root / name
        if source.is_symlink() or not source.is_file():
            raise ValueError("Public source is not a regular file")
        actual[name] = hashlib.sha256(source.read_bytes()).hexdigest()
    if actual != canonical:
        raise ValueError("Public checkout bytes differ from the committed Git blobs")
    identity = hashlib.sha256(
        json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {
        "status": "passed",
        "tested_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True
        ).strip(),
        "public_source_sha256": identity,
        "files": canonical,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    names = frozenset((root / "tools/public-files.txt").read_text().splitlines())
    result = verify(root, names)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print("Verified exact committed public source bytes")


if __name__ == "__main__":
    main()
