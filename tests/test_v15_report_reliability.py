"""Deterministic publication and diagnostic precedence with real filesystem state."""

import json
import os
import tempfile
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

import otarchguard.cli as cli
from otarchguard.diagnostics import ModelError
from otarchguard.reporting import write_report


@pytest.mark.parametrize("existing", [False, True])
def test_success_create_and_replace(tmp_path: Path, existing: bool) -> None:
    path = tmp_path / "report"
    if existing:
        path.write_bytes(b"old")
    write_report(path, b"new", ())
    assert path.read_bytes() == b"new"
    assert not list(tmp_path.glob(".otarchguard-*"))


def inject(
    monkeypatch: pytest.MonkeyPatch,
    events: list[tuple[str, bool]],
    *,
    replace_error: Exception | None,
    cleanup_error: bool,
) -> None:
    replace, unlink = os.replace, Path.unlink

    def replacing(source: Any, target: Any) -> None:
        events.append(("replace", Path(source).is_file()))
        if replace_error:
            raise replace_error
        replace(source, target)

    def removing(path: Path, missing_ok: bool = False) -> None:
        if path.name.startswith(".otarchguard-"):
            events.append(("unlink", path.is_file()))
            if cleanup_error:
                raise PermissionError("private injected path")
        unlink(path, missing_ok=missing_ok)

    monkeypatch.setattr(os, "replace", replacing)
    monkeypatch.setattr(Path, "unlink", removing)


@pytest.mark.parametrize(
    "replace_failed,cleanup_failed", [(True, False), (True, True), (False, True)]
)
def test_primary_and_secondary_failures_are_accurate_and_preserve_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    replace_failed: bool,
    cleanup_failed: bool,
) -> None:
    path = tmp_path / "report"
    path.write_bytes(b"old")
    events: list[tuple[str, bool]] = []
    inject(
        monkeypatch,
        events,
        replace_error=PermissionError() if replace_failed else None,
        cleanup_error=cleanup_failed,
    )
    with pytest.raises(ModelError) as caught:
        write_report(path, b"new", ())
    (diagnostic,) = caught.value.diagnostics
    assert diagnostic.code == "REPORT_IO_ERROR" and diagnostic.category.value == "io_error"
    assert "private" not in diagnostic.message
    assert ("no new report" in diagnostic.message) == replace_failed
    assert ("cleanup" in diagnostic.message) == cleanup_failed
    assert path.read_bytes() == (b"old" if replace_failed else b"new")
    assert events == [("replace", True), ("unlink", replace_failed)]
    assert len(list(tmp_path.glob(".otarchguard-*"))) == int(replace_failed and cleanup_failed)


def test_cli_dual_failure_remains_controlled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "report"
    path.write_bytes(b"old")
    inject(monkeypatch, [], replace_error=PermissionError(), cleanup_error=True)
    source = Path(__file__).parent / "fixtures/minimal-valid.yaml"
    result = CliRunner().invoke(cli.app, ["validate", str(source), "--report", str(path)])
    assert result.exit_code == 2 and not result.stdout
    assert json.loads(result.stderr)["code"] == "REPORT_IO_ERROR"
    assert path.read_bytes() == b"old"


def test_unexpected_primary_exception_is_not_masked(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inject(monkeypatch, [], replace_error=ValueError("primary"), cleanup_error=True)
    with pytest.raises(ValueError, match="primary"):
        write_report(tmp_path / "report", b"new", ())


def test_input_collision_precedes_temporary_creation(tmp_path: Path) -> None:
    path = tmp_path / "input"
    path.write_bytes(b"input")
    with pytest.raises(ModelError) as error:
        write_report(path, b"new", (path,))
    assert error.value.diagnostics[0].code == "REPORT_IO_ERROR"
    assert path.read_bytes() == b"input" and not list(tmp_path.glob(".otarchguard-*"))


def test_temporary_creation_failure_is_controlled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "report"
    path.write_bytes(b"old")

    def denied(*args: Any, **kwargs: Any) -> Any:
        raise PermissionError("private")

    monkeypatch.setattr(tempfile, "NamedTemporaryFile", denied)
    with pytest.raises(ModelError) as error:
        write_report(path, b"new", ())
    assert error.value.diagnostics[0].code == "REPORT_IO_ERROR"
    assert path.read_bytes() == b"old" and not list(tmp_path.glob(".otarchguard-*"))


def test_temporary_write_failure_cleans_real_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = tempfile.NamedTemporaryFile

    def denied(*args: Any, **kwargs: Any) -> Any:
        stream = original(*args, **kwargs)

        def fail_write(data: bytes) -> int:
            raise PermissionError("injected write")

        monkeypatch.setattr(stream, "write", fail_write)
        return stream

    path = tmp_path / "report"
    path.write_bytes(b"old")
    monkeypatch.setattr(tempfile, "NamedTemporaryFile", denied)
    with pytest.raises(ModelError) as error:
        write_report(path, b"new", ())
    assert error.value.diagnostics[0].code == "REPORT_IO_ERROR"
    assert path.read_bytes() == b"old" and not list(tmp_path.glob(".otarchguard-*"))
