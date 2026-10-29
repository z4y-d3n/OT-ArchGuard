"""Independent command integration protects frozen observations and source files."""

import hashlib
import json
import socket
from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from otarchguard.capture.observations import analyze_capture
from otarchguard.cli import app
from tools.capture_workloads import write_pcap
from tools.read_capture_evidence import validate_observations

runner = CliRunner()


def test_enrichment_does_not_reinterpret_observations_or_touch_capture(
    tmp_path: Path, monkeypatch: Any
) -> None:
    def denied(*args: object, **kwargs: object) -> Any:
        raise AssertionError("Offline enrichment attempted network access")

    monkeypatch.setattr(socket, "socket", denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)
    capture = tmp_path / "fictional.pcap"
    write_pcap(capture)
    original = capture.read_bytes()
    before = analyze_capture(capture)
    output = tmp_path / "enrichment.json"
    first = runner.invoke(app, ["capture", "enrich", str(capture), "--output", str(output)])
    second = runner.invoke(app, ["capture", "enrich", str(capture)])
    assert first.exit_code == second.exit_code == 0, first.stderr
    assert not first.stderr and not second.stderr
    assert first.stdout.encode() == output.read_bytes() == second.stdout.encode()
    artifact = json.loads(first.stdout)
    assert artifact["capture_sha256"] == hashlib.sha256(original).hexdigest()
    assert artifact["enrichment_version"] == 1
    assert artifact["observations_sha256"] is None
    assert analyze_capture(capture) == before
    assert capture.read_bytes() == original
    validate_observations(before)
    refused = runner.invoke(app, ["capture", "enrich", str(capture), "--output", str(output)])
    assert refused.exit_code == 2 and not refused.stdout
    assert output.read_bytes() == first.stdout.encode()


def test_snapshot_cli_uses_exact_v13_artifact_and_rejects_corrupt_import(tmp_path: Path) -> None:
    source = Path(__file__).parent / "fixtures/capture-contract-v2/supported/observations.json"
    original = source.read_bytes()
    workspace = tmp_path / "history"
    initialized = runner.invoke(app, ["evidence", "init", str(workspace)])
    assert initialized.exit_code == 0, initialized.stderr
    added = runner.invoke(app, ["evidence", "add", str(workspace), str(source)])
    assert added.exit_code == 0 and not added.stderr, added.stderr
    receipt = json.loads(added.stdout)
    assert receipt["status"] == "ADDED"
    snapshot_id = receipt["snapshot"]["snapshot_id"]
    shown = runner.invoke(app, ["evidence", "show", str(workspace), snapshot_id])
    assert shown.exit_code == 0 and not shown.stderr
    snapshot = json.loads(shown.stdout)
    assert snapshot["observations"] == json.loads(original)
    duplicate = runner.invoke(app, ["evidence", "add", str(workspace), str(source)])
    assert duplicate.exit_code == 0
    assert json.loads(duplicate.stdout)["status"] == "DUPLICATE_CAPTURE"
    corrupt = tmp_path / "corrupt.json"
    value = json.loads(original)
    value["coverage"]["packets"] += 1
    corrupt.write_text(json.dumps(value), encoding="utf-8")
    refused = runner.invoke(app, ["evidence", "add", str(workspace), str(corrupt)])
    assert refused.exit_code == 2 and not refused.stdout
    assert len(list((workspace / "snapshots").glob("*.json"))) == 1
    verified = runner.invoke(app, ["evidence", "verify", str(workspace)])
    assert verified.exit_code == 0 and json.loads(verified.stdout)["snapshots"] == 1
    assert source.read_bytes() == original
