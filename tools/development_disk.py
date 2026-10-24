"""Report-only local disk inventory. Never delete or follow directory links."""

import argparse
import json
import os
from pathlib import Path


def size(root: Path) -> tuple[int, int]:
    total = files = 0
    pending = [root]
    while pending:
        directory = pending.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                if entry.is_symlink():
                    continue
                if entry.is_dir(follow_symlinks=False):
                    child = Path(entry.path)
                    if not child.is_junction():
                        pending.append(child)
                elif entry.is_file(follow_symlinks=False):
                    total += entry.stat(follow_symlinks=False).st_size
                    files += 1
    return total, files


def report(root: Path) -> dict[str, object]:
    rows = []
    for path in sorted(root.iterdir()):
        if path.is_symlink() or path.is_junction() or not path.is_dir():
            continue
        name = path.name
        category = (
            "protected historical/current evidence; owner review required"
            if name in {"output", "dist", ".git"}
            else "regenerable environment; preserve current verification environments"
            if name.startswith(".venv")
            else "regenerable cache/build; review exact paths before deletion"
            if name
            in {"build", ".cache", ".pytest_tmp", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
            else "owner/source data; protected"
        )
        total, count = size(path)
        rows.append(dict(directory=name, bytes=total, files=count, category=category))
    evidence = []
    development = root / "output/v1.2-development"
    if development.is_dir():
        for gate in sorted(development.iterdir()):
            if gate.is_dir() and not gate.is_symlink() and not gate.is_junction():
                total, count = size(gate)
                evidence.append(
                    dict(
                        directory=gate.relative_to(root).as_posix(),
                        bytes=total,
                        files=count,
                        category="protected gate evidence",
                    )
                )
    return {
        "mode": "report-only",
        "deletions": [],
        "directories": sorted(rows, key=lambda row: float(str(row["bytes"])), reverse=True),
        "gate_evidence": evidence,
        "retention": "Preserve accepted releases, prior gate evidence, owner files and current "
        "verification environments. Any deletion needs separate approval of exact paths.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report(args.root), stream, sort_keys=True, indent=2)


if __name__ == "__main__":
    main()
