"""Reject ambiguous core metadata even when archive source and RECORD remain valid."""

import base64
import csv
import hashlib
import io
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest

from tools import audit_release as release

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def archives(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path, Path]:
    """Build in an isolated source copy; never mutate checkout build metadata."""
    work = tmp_path_factory.mktemp("metadata-archive-audit")
    source = work / "source"
    for name in release.PUBLIC_FILES:
        target = source / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    destination = work / "artifacts"
    subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; from setuptools import build_meta; destination=sys.argv[1]; "
            "build_meta.build_wheel(destination); build_meta.build_sdist(destination)",
            str(destination),
        ],
        cwd=source,
        check=True,
        capture_output=True,
        timeout=120,
    )
    wheel = destination / f"otarchguard-{release.VERSION}-py3-none-any.whl"
    sdist = destination / f"otarchguard-{release.VERSION}.tar.gz"
    assert release.audit(wheel, sdist, source)["status"] == "passed"
    return source, wheel, sdist


def _metadata(data: bytes, field: str, mutation: str) -> bytes:
    newline = b"\r\n" if b"\r\n\r\n" in data else b"\n"
    header, separator, description = data.partition(newline * 2)
    lines = header.split(newline)
    prefix = (field + ": ").encode()
    matches = [i for i, line in enumerate(lines) if line.startswith(prefix)]
    assert len(matches) == 1 and separator
    index = matches[0]
    if mutation == "omit":
        del lines[index]
    elif mutation == "identical":
        lines.insert(index + 1, lines[index])
    elif mutation.startswith("replace:"):
        lines[index] = prefix + mutation.removeprefix("replace:").encode()
    else:
        lines.insert(index + 1, prefix + b"unreviewed-conflicting-value")
    return newline.join(lines) + separator + description


def _rewrite_wheel(
    original: Path,
    destination: Path,
    field: str,
    mutation: str,
    *,
    member: str = "METADATA",
    replacement: bytes | None = None,
) -> None:
    with zipfile.ZipFile(original) as archive:
        members = {entry.filename: (entry, archive.read(entry)) for entry in archive.infolist()}
    name = f"{release.DIST_INFO}/{member}"
    entry, data = members[name]
    members[name] = entry, _metadata(data, field, mutation) if replacement is None else replacement
    record = f"{release.DIST_INFO}/RECORD"
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    for name, (_, data) in members.items():
        digest = "sha256=" + base64.urlsafe_b64encode(
            hashlib.sha256(data).digest()
        ).decode().rstrip("=")
        writer.writerow((name, "", "") if name == record else (name, digest, str(len(data))))
    members[record] = members[record][0], stream.getvalue().encode()
    with zipfile.ZipFile(destination, "w") as archive:
        for entry, data in members.values():
            archive.writestr(entry, data)


def _rewrite_sdist(
    original: Path,
    destination: Path,
    target: str,
    field: str,
    mutation: str,
    *,
    replacement: bytes | None = None,
) -> None:
    suffix = "PKG-INFO" if target == "sdist-root" else "src/otarchguard.egg-info/PKG-INFO"
    if target == "entrypoints":
        suffix = "src/otarchguard.egg-info/entry_points.txt"
    path = f"otarchguard-{release.VERSION}/{suffix}"
    with tarfile.open(original, "r:gz") as source, tarfile.open(destination, "w:gz") as output:
        for member in source.getmembers():
            if member.isfile():
                stream = source.extractfile(member)
                assert stream is not None
                data = stream.read()
                if member.name == path:
                    data = _metadata(data, field, mutation) if replacement is None else replacement
                    member.size = len(data)
                output.addfile(member, io.BytesIO(data))
            else:
                output.addfile(member)


def test_unchanged_built_metadata_is_accepted(archives: tuple[Path, Path, Path]) -> None:
    source, wheel, sdist = archives
    assert release.audit(wheel, sdist, source)["status"] == "passed"


@pytest.mark.parametrize("mutation", ["conflicting", "identical", "omit"])
@pytest.mark.parametrize(
    "target,field",
    [
        ("wheel", field)
        for field in (
            "Metadata-Version",
            "Name",
            "Version",
            "License-Expression",
            "Requires-Python",
        )
    ]
    + [("sdist-root", "Version"), ("sdist-egg", "Version")],
)
def test_singleton_metadata_cannot_be_duplicated_or_omitted(
    archives: tuple[Path, Path, Path], tmp_path: Path, target: str, field: str, mutation: str
) -> None:
    source, wheel, sdist = archives
    if target == "wheel":
        changed = tmp_path / wheel.name
        _rewrite_wheel(wheel, changed, field, mutation)
        wheel = changed
    else:
        changed = tmp_path / sdist.name
        _rewrite_sdist(sdist, changed, target, field, mutation)
        sdist = changed
    with pytest.raises(ValueError, match="metadata"):
        release.audit(wheel, sdist, source)


@pytest.mark.parametrize("mutation", ["conflicting", "identical", "omit"])
@pytest.mark.parametrize("field", ["Wheel-Version", "Root-Is-Purelib", "Tag"])
def test_wheel_profile_cannot_be_changed_duplicated_or_omitted(
    archives: tuple[Path, Path, Path], tmp_path: Path, field: str, mutation: str
) -> None:
    source, wheel, sdist = archives
    changed = tmp_path / wheel.name
    _rewrite_wheel(wheel, changed, field, mutation, member="WHEEL")
    with pytest.raises(ValueError, match="wheel metadata"):
        release.audit(changed, sdist, source)


@pytest.mark.parametrize(
    "replacement",
    [
        b"[console_scripts]\notarchguard = otarchguard.cli:app\nextra = otarchguard.cli:app\n",
        b"[console_scripts]\notarchguard = otarchguard.cli:app\notarchguard = malicious:app\n",
        b"[console_scripts]\notarchguard = otarchguard.cli:app\n[other]\nextra = malicious:app\n",
        b"[console_scripts]\notarchguard = malicious:app\n",
        b"[console_scripts]\nOTARCHGUARD = otarchguard.cli:app\n",
        b"[DEFAULT]\notarchguard = otarchguard.cli:app\n[console_scripts]\n",
        b"otarchguard = otarchguard.cli:app\n",
        b"[console_scripts]\n# otarchguard = otarchguard.cli:app\nextra = malicious:app\n",
    ],
)
def test_entry_points_equal_project_scripts_even_if_both_archives_agree(
    archives: tuple[Path, Path, Path], tmp_path: Path, replacement: bytes
) -> None:
    source, wheel, sdist = archives
    changed_wheel, changed_sdist = tmp_path / wheel.name, tmp_path / sdist.name
    _rewrite_wheel(wheel, changed_wheel, "", "", member="entry_points.txt", replacement=replacement)
    _rewrite_sdist(sdist, changed_sdist, "entrypoints", "", "", replacement=replacement)
    with pytest.raises(ValueError, match="entry point metadata"):
        release.audit(changed_wheel, changed_sdist, source)


@pytest.mark.parametrize("version", ["garbage", "9.9"])
def test_metadata_format_requires_reviewed_value_even_if_all_three_records_agree(
    archives: tuple[Path, Path, Path], tmp_path: Path, version: str
) -> None:
    source, wheel, sdist = archives
    changed_wheel = tmp_path / wheel.name
    intermediate, changed_sdist = tmp_path / "root-pkginfo.tar.gz", tmp_path / sdist.name
    mutation = "replace:" + version
    _rewrite_wheel(wheel, changed_wheel, "Metadata-Version", mutation)
    _rewrite_sdist(sdist, intermediate, "sdist-root", "Metadata-Version", mutation)
    _rewrite_sdist(intermediate, changed_sdist, "sdist-egg", "Metadata-Version", mutation)
    with pytest.raises(ValueError, match="metadata"):
        release.audit(changed_wheel, changed_sdist, source)
