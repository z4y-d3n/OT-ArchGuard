"""Reject misleading fixed-input benchmark receipts before reporting acceptance."""

import json
from pathlib import Path
from typing import Any

import pytest

from benchmarks import protocol_regression as regression
from tools.history_performance_worker import file_manifest


def _inputs(root: Path) -> None:
    root.mkdir()
    path = root / "small.pcap"
    path.write_bytes(b"fictional benchmark sentinel")
    (root / "inputs.json").write_text(json.dumps(file_manifest(root)), encoding="utf-8")


@pytest.mark.parametrize("change", ["mutated", "extra", "missing"])
def test_fixed_input_inventory_changes_never_produce_a_measurement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    root = tmp_path / "inputs"
    _inputs(root)
    if change == "mutated":
        (root / "small.pcap").write_bytes(b"replaced")
    elif change == "extra":
        (root / "extra.pcap").write_bytes(b"injected")
    else:
        (root / "small.pcap").unlink()

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("Changed inputs must be rejected before executing product code")

    monkeypatch.setattr(regression, "_run", forbidden)
    output = tmp_path / "receipt.json"
    with pytest.raises(ValueError, match="inventory changed"):
        regression.measure(root, output)
    assert not output.exists()


@pytest.mark.parametrize("phase", ["latency", "allocation"])
def test_output_identity_change_in_either_measurement_phase_rejects_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, phase: str
) -> None:
    root = tmp_path / "inputs"
    _inputs(root)
    monkeypatch.setattr(regression, "package_identity", lambda: {"fictional_test_only": True})
    calls = 0

    def measured(path: Path) -> tuple[dict[str, Any], None]:
        nonlocal calls
        calls += 1
        changed = calls == (2 if phase == "latency" else 5)
        return {"status": "complete", "output_sha256": "changed" if changed else "stable"}, None

    monkeypatch.setattr(regression, "_run", measured)
    output = tmp_path / "receipt.json"
    with pytest.raises(AssertionError, match="changed canonical output"):
        regression.measure(root, output)
    assert not output.exists()
