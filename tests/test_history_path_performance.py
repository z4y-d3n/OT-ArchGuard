"""Independent equivalence and race tests for fresh single-record read path checks."""

import errno
import os
import stat
import sys
from dataclasses import asdict
from pathlib import Path, PosixPath, WindowsPath
from types import SimpleNamespace
from typing import Any

import pytest

from otarchguard.diagnostics import ModelError
from otarchguard.evidence import history, paths, workspace


class UntrustedWindowsPath(WindowsPath):
    def is_junction(self) -> bool:
        return True


class UntrustedPosixPath(PosixPath):
    def is_junction(self) -> bool:
        return True


def outcome(operation: Any, path: Path) -> dict[str, Any]:
    try:
        operation(path)
        return {"status": "accepted-path-only"}
    except ModelError as error:
        return {"diagnostics": [asdict(d) for d in error.diagnostics]}
    except Exception as error:
        return {
            "exception": type(error).__name__,
            "errno": getattr(error, "errno", None),
            "winerror": getattr(error, "winerror", None),
        }


def real_symlink(
    tmp_path: Path, name: str, directory: bool = False, dangling: bool = False
) -> Path | None:
    target = tmp_path / ("target-" + name)
    if not dangling:
        if directory:
            target.mkdir()
            (target / "data.json").write_bytes(b"{}")
        else:
            target.write_bytes(b"{}")
    link = tmp_path / name
    try:
        link.symlink_to(target, target_is_directory=directory)
    except OSError:
        return None
    return link


def existing_windows_junction() -> Path | None:
    if os.name != "nt":
        return None
    drive = Path(os.environ.get("SystemDrive", "C:") + "/")
    for candidate in (drive / "Documents and Settings", drive / "Users/All Users"):
        try:
            if candidate.is_junction():
                return candidate
        except OSError:
            continue
    return None


@pytest.mark.parametrize(
    "name",
    [
        "plain.json",
        "missing/child.json",
        "漢",
        "ñ",
        "emoji-\U0001f600",
        "CON",
        "NUL.txt",
        "con.A",
        "LPT9.json",
        "COM0",
        "trailing.",
        "trailing ",
        "alternate:stream",
        "wild*card",
        "bad?name",
        "bad|name",
        "bad<name",
        "bad>name",
        'bad"name',
        "control\nname",
        "control\x7fname",
        "control\x9fname",
        "one/../other",
    ],
)
def test_read_path_rules_keep_frozen_outcomes_for_portable_and_hostile_names(
    tmp_path: Path, name: str
) -> None:
    (tmp_path / "plain.json").write_bytes(b"{}")
    path = tmp_path / name
    assert outcome(paths._check_read_path, path) == outcome(workspace._local, path)


@pytest.mark.parametrize("path", ["//unreachable-server/share/file", "\\\\?\\C:\\Windows"])
def test_remote_and_device_forms_reject_without_weakening_lexical_policy(path: str) -> None:
    selected = Path(path)
    actual = outcome(paths._check_read_path, selected)
    assert actual == outcome(workspace._local, selected)
    assert actual["diagnostics"][0]["code"] == "EVIDENCE_PATH"


@pytest.mark.parametrize("kind", ["file", "directory", "dangling"])
def test_real_links_when_available_keep_exact_frozen_rejection(tmp_path: Path, kind: str) -> None:
    link = real_symlink(tmp_path, "link", kind == "directory", kind == "dangling")
    if link is None:
        # No skip conceals an untested affirmative result. Unsupported creation
        # still exercises the conservative custom-observer fallback below.
        link = UntrustedWindowsPath(tmp_path) if os.name == "nt" else UntrustedPosixPath(tmp_path)
    selected = link / "data.json" if kind == "directory" else link
    actual = outcome(paths._check_read_path, selected)
    assert actual == outcome(workspace._local, selected)
    assert actual["diagnostics"][0]["code"] == "EVIDENCE_PATH"


def test_real_windows_junction_or_explicit_unavailable_capability(tmp_path: Path) -> None:
    junction = existing_windows_junction()
    if junction is None:
        # The portable symlink boundary remains mandatory when this Windows-only
        # filesystem capability is absent. Current Windows acceptance separately
        # records actual junction metadata and Python-version probe receipts.
        selected = tmp_path / "alternate:stream"
    else:
        selected = junction
        info = junction.lstat()
        assert getattr(info, "st_file_attributes", 0) & 0x400
        assert getattr(info, "st_reparse_tag", 0) == 0xA0000003
    actual = outcome(paths._check_read_path, selected)
    assert actual == outcome(workspace._local, selected)
    assert actual["diagnostics"][0]["code"] == "EVIDENCE_PATH"


@pytest.mark.parametrize("fault", ["missing", "denied", "not-directory", "io", "value"])
def test_changed_lstat_observers_keep_version_specific_frozen_error_policy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    selected = tmp_path / "ordinary.json"
    selected.write_bytes(b"{}")
    original = type(selected).lstat
    error = {
        "missing": FileNotFoundError(errno.ENOENT, "synthetic missing"),
        "denied": PermissionError(errno.EACCES, "synthetic denied"),
        "not-directory": OSError(errno.ENOTDIR, "synthetic not-directory"),
        "io": OSError(errno.EIO, "synthetic I/O error"),
        "value": ValueError("synthetic value error"),
    }[fault]

    def failing(path: Path) -> os.stat_result:
        if path == selected:
            raise error
        return original(path)

    monkeypatch.setattr(type(selected), "lstat", failing)
    assert outcome(paths._check_read_path, selected) == outcome(workspace._local, selected)


def test_concrete_lstat_override_cannot_hide_a_real_link_from_frozen_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    selected = (
        existing_windows_junction() if os.name == "nt" and sys.version_info < (3, 13) else None
    )
    if selected is None:
        selected = real_symlink(tmp_path, "observer-link")
    if selected is None:
        selected = tmp_path / "ordinary.json"
        selected.write_bytes(b"{}")
    original = type(selected).lstat

    def following(path: Path) -> os.stat_result:
        return os.stat(path, follow_symlinks=True)

    monkeypatch.setattr(type(selected), "lstat", following)
    calls: list[Path] = []
    frozen = workspace._local

    def fallback(path: Path) -> None:
        calls.append(path)
        frozen(path)

    monkeypatch.setattr(paths, "_local", fallback)
    actual = outcome(paths._check_read_path, selected)
    assert calls == [selected]
    assert actual == outcome(workspace._local, selected)
    # Keep this reference alive to document that the replacement is a distinct
    # concrete-class observer, rather than the inherited Path.lstat function.
    assert original is not following


def test_observer_equality_cannot_impersonate_native_function_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    selected = (
        existing_windows_junction() if os.name == "nt" and sys.version_info < (3, 13) else None
    )
    if selected is None:
        selected = real_symlink(tmp_path, "equal-observer-link")
    if selected is None:
        selected = tmp_path / "ordinary.json"
        selected.write_bytes(b"{}")

    class EqualObserver:
        def __eq__(self, other: object) -> bool:
            return True

        def __get__(self, instance: Path | None, owner: type[Path]) -> Any:
            if instance is None:
                return self
            return lambda: os.stat(instance, follow_symlinks=True)

    monkeypatch.setattr(type(selected), "lstat", EqualObserver())
    calls: list[Path] = []

    def fallback(path: Path) -> None:
        calls.append(path)
        workspace._local(path)

    monkeypatch.setattr(paths, "_local", fallback)
    actual = outcome(paths._check_read_path, selected)
    assert calls == [selected]
    assert actual == outcome(workspace._local, selected)


@pytest.mark.parametrize(
    "kind", ["mode", "symlink-tag", "mount-tag", "other-reparse", "undefined-tag"]
)
def test_one_metadata_record_covers_every_unsafe_flag_and_ignores_undefined_tag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    selected = tmp_path / "metadata.json"
    selected.write_bytes(b"{}")
    original = type(selected).lstat
    counts: list[Path] = []
    mode = stat.S_IFLNK if kind == "mode" else stat.S_IFREG
    tag = 0xA000000C if kind == "symlink-tag" else 0xA0000003
    attributes = 0 if kind in {"mode", "undefined-tag"} else 0x400

    def supplied(path: Path) -> Any:
        if path == selected:
            counts.append(path)
            return SimpleNamespace(st_mode=mode, st_file_attributes=attributes, st_reparse_tag=tag)
        return original(path)

    monkeypatch.setattr(type(selected), "lstat", supplied)
    # Simulate an interpreter/OS observation provider at module initialization.
    # This is test instrumentation, never a caller-controlled production flag.
    monkeypatch.setattr(paths, "_NATIVE_OBSERVERS", paths._observers())
    actual = outcome(paths._check_read_path, selected)
    if kind == "undefined-tag":
        assert actual == {"status": "accepted-path-only"}
    else:
        assert actual["diagnostics"][0]["code"] == "EVIDENCE_PATH"
    assert counts == [selected]


def metadata_query_count(operation: Any, selected: Path) -> int:
    count = 0

    def profile(frame: Any, event: str, argument: Any) -> None:
        nonlocal count
        if event == "c_call" and getattr(argument, "__name__", "") in {
            "stat",
            "lstat",
            "_path_islink",
            "_path_isjunction",
        }:
            count += 1

    sys.setprofile(profile)
    try:
        operation(selected)
    finally:
        sys.setprofile(None)
    return count


def test_normal_path_uses_one_fresh_metadata_query_for_each_ancestor(tmp_path: Path) -> None:
    selected = tmp_path / "query.json"
    selected.write_bytes(b"{}")
    ancestors = 1 + len(selected.absolute().parents)
    assert metadata_query_count(paths._check_read_path, selected) == ancestors
    original_queries = metadata_query_count(workspace._local, selected)
    assert original_queries >= 2 * ancestors
    if os.name == "nt":
        assert original_queries == 3 * ancestors


@pytest.mark.parametrize("label", ["old", "new"])
def test_observed_unsafe_link_cannot_be_retried_into_acceptance_after_path_changes(
    tmp_path: Path, label: str
) -> None:
    selected = real_symlink(tmp_path, "transition-" + label)
    if selected is None:
        # The mandatory field-level unsafe-record cases above cover platforms
        # where creating a real symbolic link is unavailable.
        assert outcome(paths._check_read_path, tmp_path / "NUL")["diagnostics"]
        return
    operation = workspace._local if label == "old" else paths._check_read_path
    stage = "is_symlink" if label == "old" else "lstat"
    changed: list[bool] = []

    def transition(frame: Any, event: str, argument: Any) -> None:
        if (
            event == "return"
            and frame.f_code.co_name == stage
            and frame.f_locals.get("self") == selected
            and not changed
        ):
            observed = argument is True if stage == "is_symlink" else stat.S_ISLNK(argument.st_mode)
            if observed:
                changed.append(True)
                # Only this test's own temporary link is replaced, never evidence.
                assert tmp_path in selected.parents
                selected.unlink()
                selected.write_bytes(b'{"now_regular":true}')

    sys.setprofile(transition)
    try:
        actual = outcome(operation, selected)
    finally:
        sys.setprofile(None)
    assert changed == [True]
    assert actual["diagnostics"][0]["code"] == "EVIDENCE_PATH"


def test_history_read_checks_before_and_after_and_keeps_frozen_other_path_policy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert vars(history)["_local"] is workspace._local
    assert vars(history)["_publish"] is workspace._publish
    selected = tmp_path / "metadata.json"
    selected.write_bytes(b"{}")
    checks: list[Path] = []
    actual_check = paths._check_read_path

    def observed(path: Path) -> None:
        checks.append(path)
        actual_check(path)

    monkeypatch.setattr(history, "_check_read_path", observed)
    assert history._read_bytes(selected, history.HISTORY_LIMITS) == b"{}"
    assert checks == [selected, selected]
