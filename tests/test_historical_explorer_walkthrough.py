"""All fictional acceptance scenarios through regular installed public consumers."""

from pathlib import Path

from tools.historical_explorer_walkthrough import scenario


def test_fictional_historical_explorer_walkthrough(tmp_path: Path) -> None:
    receipt = scenario(tmp_path / "tutorial")
    assert receipt["status"] == "passed"
    assert set(receipt["scenarios"]) == {"normal", "incomplete", "decoder", "unchanged", "dense"}
    assert receipt["human_visual_acceptance"] == "PENDING"
    assert receipt["fresh_verification_after_revocation"]["approval_snapshot_changed"] is True
