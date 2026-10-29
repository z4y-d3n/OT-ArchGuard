"""Audit every release member against the explicit public source manifest."""

import argparse
import base64
import csv
import hashlib
import io
import json
import re
import stat
import tarfile
import tomllib
import zipfile
from collections.abc import Mapping
from configparser import ConfigParser
from configparser import Error as ConfigError
from email.parser import BytesParser
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_FILES = frozenset((ROOT / "tools/public-files.txt").read_text(encoding="utf-8").splitlines())
VERSION = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
DIST_INFO = f"otarchguard-{VERSION}.dist-info"
WHEEL_METADATA = frozenset(
    {
        "METADATA",
        "WHEEL",
        "entry_points.txt",
        "top_level.txt",
        "RECORD",
        "licenses/LICENSE",
        "licenses/THIRD_PARTY_NOTICES.md",
    }
)
GENERATED = frozenset(
    {"PKG-INFO", "setup.cfg"}
    | {
        f"src/otarchguard.egg-info/{name}"
        for name in (
            "PKG-INFO",
            "SOURCES.txt",
            "dependency_links.txt",
            "entry_points.txt",
            "requires.txt",
            "top_level.txt",
        )
    }
)


class _EntryPoints(ConfigParser):
    def optionxform(self, optionstr: str) -> str:
        return optionstr


def check_member(name: str, *, wheel: bool) -> None:
    path = PurePosixPath(name)
    if (
        path.is_absolute()
        or path.as_posix() != name
        or ".." in path.parts
        or "\\" in name
        or ":" in name
    ):
        raise ValueError(f"Unsafe archive member: {name}")
    if wheel:
        allowed = {
            p.removeprefix("src/")
            for p in PUBLIC_FILES
            if p.startswith("src/otarchguard/") and p.endswith(".py")
        }
        allowed.update(f"{DIST_INFO}/{p}" for p in WHEEL_METADATA)
    else:
        allowed = set(PUBLIC_FILES | GENERATED)
    if name not in allowed:
        raise ValueError(f"Unreviewed archive member: {name}")


def verify_source_files(
    files: Mapping[str, bytes], source_root: Path, expected: frozenset[str]
) -> None:
    if not expected <= files.keys():
        raise ValueError("Source distribution is missing reviewed public files")
    for name in sorted(expected):
        source = source_root / name
        if source.is_symlink() or not source.is_file() or files[name] != source.read_bytes():
            raise ValueError(f"Source bytes differ: {name}")


def normalize_requirement(value: str) -> tuple[str, tuple[str, ...]]:
    """Compare package names and complete constraint clauses independent of order."""
    match = re.fullmatch(r"([A-Za-z0-9_.-]+)(.*)", value.replace(" ", ""))
    if match is None:
        raise ValueError("Unsupported dependency representation")
    name = re.sub(r"[-_.]+", "-", match.group(1)).lower()
    clauses = tuple(sorted(filter(None, match.group(2).split(","))))
    return name, clauses


def read_wheel(wheel: Path) -> dict[str, bytes]:
    """Validate every ZIP entry before reading; no ignored directories or links."""
    with zipfile.ZipFile(wheel) as archive:
        infos = archive.infolist()
        names = [entry.filename for entry in infos]
        if len(names) != len({name.casefold() for name in names}):
            raise ValueError("Duplicate or case-conflicting wheel member")
        for entry in infos:
            if entry.orig_filename != entry.filename:
                raise ValueError("Wheel member name was truncated by ZIP decoding")
            check_member(entry.filename, wheel=True)
            kind = stat.S_IFMT(entry.external_attr >> 16)
            if entry.is_dir() or kind not in {0, stat.S_IFREG}:
                raise ValueError("Wheel contains a link, directory or special file")
        return {entry.filename: archive.read(entry) for entry in infos}


def audit(wheel: Path, sdist: Path, source_root: Path | None = None) -> dict[str, object]:
    source_root = source_root or ROOT
    wheel_files = read_wheel(wheel)
    source_files: dict[str, bytes] = {}
    source_names: set[str] = set()
    with tarfile.open(sdist, "r:gz") as archive:
        for member in archive.getmembers():
            if member.name.casefold() in source_names:
                raise ValueError("Duplicate or case-conflicting source member")
            source_names.add(member.name.casefold())
            if (
                PurePosixPath(member.name).as_posix() != member.name
                or ".." in PurePosixPath(member.name).parts
                or "\\" in member.name
                or ":" in member.name
            ):
                raise ValueError("Unsafe source archive member")
            expected_root = f"otarchguard-{VERSION}"
            if member.name.split("/", 1)[0] != expected_root:
                raise ValueError("Unexpected source archive root")
            if member.isdir():
                if member.name != expected_root:
                    relative = member.name.split("/", 1)[1].rstrip("/")
                    if not any(p.startswith(relative + "/") for p in PUBLIC_FILES | GENERATED):
                        raise ValueError("Unreviewed source archive directory")
                continue
            if not member.isfile() or "/" not in member.name:
                raise ValueError("Source distribution contains a link or special file")
            name = member.name.split("/", 1)[1]
            if name in source_files:
                raise ValueError("Duplicate source member")
            stream = archive.extractfile(member)
            if stream is None:
                raise ValueError("Unreadable source member")
            source_files[name] = stream.read()
    for name in wheel_files:
        check_member(name, wheel=True)
    for name in source_files:
        check_member(name, wheel=False)
    verify_source_files(source_files, source_root, PUBLIC_FILES)
    expected_modules = {
        n.removeprefix("src/")
        for n in PUBLIC_FILES
        if n.startswith("src/otarchguard/") and n.endswith(".py")
    }
    if set(wheel_files) != expected_modules | {f"{DIST_INFO}/{p}" for p in WHEEL_METADATA}:
        raise ValueError("Wheel member inventory differs from reviewed contents")
    project = tomllib.loads((source_root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    metadata = BytesParser().parsebytes(wheel_files[f"{DIST_INFO}/METADATA"])
    wheel_metadata = BytesParser().parsebytes(wheel_files[f"{DIST_INFO}/WHEEL"])
    for field, expected_value in (
        ("Wheel-Version", "1.0"),
        ("Root-Is-Purelib", "true"),
        ("Tag", "py3-none-any"),
    ):
        if wheel_metadata.get_all(field) != [expected_value]:
            raise ValueError(f"Unexpected pure-Python wheel metadata: {field}")
    for field, expected_value in (
        ("Metadata-Version", "2.4"),
        ("Name", project["name"]),
        ("Version", project["version"]),
        ("License-Expression", "Apache-2.0"),
        ("Requires-Python", ">=3.12"),
    ):
        if metadata.get_all(field) != [expected_value]:
            raise ValueError(f"Unexpected wheel metadata: {field}")
    for name in ("PKG-INFO", "src/otarchguard.egg-info/PKG-INFO"):
        source_metadata = BytesParser().parsebytes(source_files[name])
        for field in (
            "Metadata-Version",
            "Name",
            "Version",
            "License-Expression",
            "Requires-Python",
            "Requires-Dist",
        ):
            if source_metadata.get_all(field) != metadata.get_all(field):
                raise ValueError(f"Source/wheel metadata differs: {field}")
    runtime = {
        normalize_requirement(d)
        for d in metadata.get_all("Requires-Dist", [])
        if "extra ==" not in d
    }
    if runtime != {normalize_requirement(d) for d in project["dependencies"]}:
        raise ValueError("Runtime dependencies differ from project metadata")
    for name in ("LICENSE", "THIRD_PARTY_NOTICES.md"):
        if wheel_files[f"{DIST_INFO}/licenses/{name}"] != source_files[name]:
            raise ValueError(f"License document differs: {name}")
    entry_points = _EntryPoints(interpolation=None)
    try:
        entry_points.read_string(wheel_files[f"{DIST_INFO}/entry_points.txt"].decode("utf-8"))
    except (ConfigError, UnicodeError) as error:
        raise ValueError("Invalid console entry point metadata") from error
    if (
        entry_points.defaults()
        or entry_points.sections() != ["console_scripts"]
        or dict(entry_points.items("console_scripts", raw=True)) != project["scripts"]
    ):
        raise ValueError("Console entry point metadata differs from the reviewed project scripts")
    for name in expected_modules:
        if wheel_files[name] != source_files["src/" + name]:
            raise ValueError(f"Wheel/source module differs: {name}")
    record_name = f"{DIST_INFO}/RECORD"
    rows = list(csv.reader(io.StringIO(wheel_files[record_name].decode())))
    if len(rows) != len(wheel_files) or {r[0] for r in rows} != set(wheel_files):
        raise ValueError("Wheel RECORD inventory differs")
    for name, digest, size in rows:
        if name == record_name:
            if digest or size:
                raise ValueError("Wheel RECORD self entry is invalid")
        else:
            data = wheel_files[name]
            expected_digest = "sha256=" + base64.urlsafe_b64encode(
                hashlib.sha256(data).digest()
            ).decode().rstrip("=")
            if digest != expected_digest or size != str(len(data)):
                raise ValueError("Wheel RECORD hash/size differs")
    for generated in ("entry_points.txt", "top_level.txt"):
        if (
            source_files[f"src/otarchguard.egg-info/{generated}"]
            != wheel_files[f"{DIST_INFO}/{generated}"]
        ):
            raise ValueError("Generated entry point/package metadata differs")
    sources = set(source_files["src/otarchguard.egg-info/SOURCES.txt"].decode().splitlines())
    if not PUBLIC_FILES <= sources or not sources <= PUBLIC_FILES | GENERATED:
        raise ValueError("Generated SOURCES list differs from reviewed files")
    return {
        "status": "passed",
        "version": VERSION,
        "license": "Apache-2.0",
        "public_file_count": len(PUBLIC_FILES),
        "source_bytes_equal": True,
        "requires_python": metadata["Requires-Python"],
        "requires_dist": sorted(metadata.get_all("Requires-Dist", [])),
        "archives": {
            path.name: {
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "bytes": path.stat().st_size,
                "members": {n: hashlib.sha256(d).hexdigest() for n, d in sorted(files.items())},
            }
            for path, files in ((wheel, wheel_files), (sdist, source_files))
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path)
    parser.add_argument("sdist", type=Path)
    parser.add_argument("--source-root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.wheel, args.sdist, args.source_root)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(f"Archive audit passed: {args.wheel.name}, {args.sdist.name}")


if __name__ == "__main__":
    main()
