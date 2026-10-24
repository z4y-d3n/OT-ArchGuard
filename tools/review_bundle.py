"""Build and independently reopen a deterministic allowlisted ingestion review ZIP.

This is a source-review selection, not an installable project or an audit-evidence
export. The complete wheel/sdist have their separate public-source archive audit.
"""

import argparse
import hashlib
import io
import json
import re
import stat
import zipfile
from pathlib import Path, PurePosixPath

from otarchguard.diagnostics import ModelError
from otarchguard.ingestion.workflow import write_new_file
from tools.audit_release import PUBLIC_FILES

ROOT = Path(__file__).resolve().parents[1]
REVIEW_FILES = frozenset(
    {
        "LICENSE",
        "src/otarchguard/quality.py",
        "src/otarchguard/architecture_comparison.py",
        "src/otarchguard/review_explorer.py",
        "src/otarchguard/review_cli.py",
        "src/otarchguard/comparison.py",
        "tests/test_quality_comparison.py",
        "tools/quality_walkthrough.py",
        "benchmarks/quality_comparison.py",
        "docs/development/gate-v12-07.md",
        "docs/development/v12-07-quality-and-comparison.md",
        "examples/quality-comparison/README.md",
        "tools/review_bundle.py",
        "tools/synthetic_inventories.py",
        "tests/conftest.py",
        "tools/synthetic_graphs.py",
        "tools/synthetic_projects.py",
        "tools/project_walkthrough.py",
        "benchmarks/projects.py",
        "benchmarks/explorer.py",
        "tools/synthetic_explorer.py",
        "tools/explorer_walkthrough.py",
        "tools/document_walkthrough.py",
        "tools/synthetic_documents.py",
        "tools/development_disk.py",
        "benchmarks/documents.py",
        "tests/test_ingestion_documents.py",
        "tests/test_explorer_compact.py",
        "docs/development/gate-v12-06.md",
        "docs/development/v12-06-document-evidence-and-explorer.md",
        "examples/import-studio/documents/README.md",
        "examples/import-studio/documents/notes.md",
        "examples/import-studio/documents/docx-profile.json",
        "src/otarchguard/cli.py",
        "src/otarchguard/explorer.py",
        "src/otarchguard/explorer_data.py",
        "src/otarchguard/explorer_html.py",
        "tests/test_explorer.py",
        "tests/fixtures/boundary-device.yaml",
        "README.md",
        "docs/development/gate-v12-05.md",
        "docs/development/v12-05-architecture-explorer.md",
        "docs/reporting.md",
        "docs/import-studio.md",
        "examples/explorer/README.md",
    }
    | {
        f"src/otarchguard/ingestion/{name}.py"
        for name in (
            "__init__",
            "cli",
            "records",
            "tabular",
            "workflow",
            "json_inventory",
            "structured",
            "netbox",
            "xlsx",
            "documents",
            "ooxml",
            "numbers",
            "xml_safe",
            "graphical",
            "graphml",
            "drawio",
            "project",
            "project_records",
            "reconciliation",
            "project_review",
            "project_cli",
        )
    }
    | {
        f"tests/{name}.py"
        for name in (
            "test_ingestion",
            "test_ingestion_cli",
            "test_ingestion_structured",
            "test_ingestion_xlsx_security",
            "test_ingestion_numbers",
            "test_review_bundle",
            "test_ingestion_graphical",
            "test_ingestion_graphical_security",
            "test_ingestion_projects",
        )
    }
)
_PERSONAL = re.compile(
    rb"(?i)(?:[a-z]:[/\\]+(?:users|documents and settings)[/\\]+|/(?:home|Users)/)"
)
_FORBIDDEN = {"__pycache__", ".git", ".aws", ".codex", "output", "build", "dist", "private"}


def _safe_member(name: str) -> None:
    path = PurePosixPath(name)
    if (
        path.is_absolute()
        or path.as_posix() != name
        or ".." in path.parts
        or "\\" in name
        or ":" in name
        or any(
            p.casefold() in _FORBIDDEN or p.casefold().startswith((".venv", ".env"))
            for p in path.parts
        )
        or path.suffix.casefold() in {".pyc", ".pyo"}
    ):
        raise ValueError("Unsafe or private review member")


def _safe_content(data: bytes, root: Path) -> None:
    # Intentional synthetic attack paths in tests are not private build locations.
    # Detect actual source roots/home-directory paths, including bytecode co_filename.
    roots = {str(root.resolve()).encode(), root.resolve().as_posix().encode()}
    roots |= {value.replace(b"\\", b"\\\\") for value in roots}
    if _PERSONAL.search(data) or any(value.lower() in data.lower() for value in roots):
        raise ValueError("Private local path in selected review source")


def _source_files(root: Path, selection: frozenset[str]) -> dict[str, bytes]:
    if not selection or not selection <= PUBLIC_FILES:
        raise ValueError("Review selection is outside the approved public allowlist")
    if len({p.casefold() for p in selection}) != len(selection):
        raise ValueError("Case-conflicting review source names")
    files: dict[str, bytes] = {}
    for name in sorted(selection):
        _safe_member(name)
        if (
            Path(name).suffix not in {".py", ".md", ".yaml", ".json", ".csv", ".drawio"}
            and name != "LICENSE"
        ):
            raise ValueError(
                "Only selected public source, documents and fixtures belong in this bundle"
            )
        source = root / name
        if source.is_symlink() or not stat.S_ISREG(source.stat().st_mode):
            raise ValueError("Review inputs must be regular source files")
        data = source.read_bytes()
        data.decode("utf-8")
        _safe_content(data, root)
        files[name] = data
    return files


def audit_review(
    archive_path: Path,
    root: Path = ROOT,
    selection: frozenset[str] = REVIEW_FILES,
) -> dict[str, object]:
    expected = _source_files(root, selection)
    with zipfile.ZipFile(archive_path) as archive:
        infos = archive.infolist()
        names = [p.filename for p in infos]
        if len(names) != len(set(names)) or set(names) != set(expected) | {"review-manifest.json"}:
            raise ValueError("Review archive inventory differs from its approved selection")
        for member in infos:
            _safe_member(member.filename)
            if member.is_dir() or stat.S_IFMT(member.external_attr >> 16) != stat.S_IFREG:
                raise ValueError("Nonregular review archive member")
        files = {name: archive.read(name) for name in names}  # Reopen/CRC check actual output.
    for name, data in expected.items():
        if files[name] != data:
            raise ValueError("Review archive source bytes differ")
        _safe_content(files[name], root)
    hashes = {name: hashlib.sha256(data).hexdigest() for name, data in sorted(expected.items())}
    manifest = json.loads(files["review-manifest.json"])
    if manifest != {
        "review_version": 1,
        "scope": "selected public source, tests, documentation and fixtures",
        "files": hashes,
    }:
        raise ValueError("Review manifest differs from verified source")
    return {
        "status": "passed",
        "archive": archive_path.name,
        "sha256": hashlib.sha256(archive_path.read_bytes()).hexdigest(),
        "files": hashes,
        "member_count": len(files),
        "bytecode_members": 0,
        "personal_paths": 0,
        "development_evidence_members": 0,
    }


def create_review(
    output: Path,
    root: Path = ROOT,
    selection: frozenset[str] = REVIEW_FILES,
) -> dict[str, object]:
    files = _source_files(root, selection)
    hashes = {name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())}
    files["review-manifest.json"] = (
        json.dumps(
            {
                "review_version": 1,
                "scope": "selected public source, tests, documentation and fixtures",
                "files": hashes,
            },
            sort_keys=True,
            indent=2,
        )
        + "\n"
    ).encode()
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
    write_new_file(output, stream.getvalue())
    return audit_review(output, root, selection)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = create_review(args.output)
        write_new_file(
            args.inventory, (json.dumps(result, sort_keys=True, indent=2) + "\n").encode()
        )
    except (ValueError, OSError, zipfile.BadZipFile, ModelError):
        parser.exit(2, "Review bundle validation failed; no archive has been accepted.\n")
    print(f"Verified sanitized review archive: {args.output.name}")


if __name__ == "__main__":
    main()
