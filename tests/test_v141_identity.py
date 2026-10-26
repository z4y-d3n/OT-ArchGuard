"""Independent separation checks; immutable legacy fixtures remain unchanged."""

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from otarchguard import DISTRIBUTION_VERSION, NATIVE_ENGINE_VERSION, __version__
from otarchguard.api import validate_file
from otarchguard.evidence.workspace import build_snapshot
from otarchguard.reporting import build_report
from otarchguard.trace import trace_file
from tools.evidence_identity import AnalysisInputs, proposed_analysis_id

ROOT = Path(__file__).resolve().parents[1]


def inputs() -> AnalysisInputs:
    return AnalysisInputs("a" * 64, "b" * 64, None, None, None, None, None, "c" * 64)


def test_distribution_advances_without_changing_native_engine_evidence() -> None:
    assert DISTRIBUTION_VERSION == "1.4.0.dev1"
    assert __version__ == "1.3.0"
    assert NATIVE_ENGINE_VERSION == "1.3.0"
    path = ROOT / "tests/fixtures/minimal-valid.yaml"
    assert build_report("validation", (validate_file(path),))["engine_version"] == "1.3.0"
    assert trace_file(path, "eng", "svc_plc").engine_version == "1.3.0"


@pytest.mark.parametrize("name", list(AnalysisInputs.__dataclass_fields__))
def test_every_analytical_input_changes_revision_not_physical_collection(name: str) -> None:
    original = inputs()
    changed = replace(original, **{name: "d" * 64})
    assert proposed_analysis_id(original) != proposed_analysis_id(changed)
    if name != "capture_sha256":
        assert original.capture_sha256 == changed.capture_sha256


def test_identity_proposal_has_independent_canonical_oracle_and_no_review_assertion() -> None:
    canonical = (
        '{"domain":"otarchguard.analysis","inputs":{'
        '"capture_sha256":"' + "a" * 64 + '","comparison_sha256":null,'
        '"enrichment_sha256":null,"mapping_sha256":null,"model_sha256":null,'
        '"observations_sha256":"' + "b" * 64 + '","policy_sha256":null,'
        '"producer_semantics_sha256":"' + "c" * 64 + '"},"proposal_version":1}'
    )
    assert (
        proposed_analysis_id(inputs())
        == "analysis-proposal-" + hashlib.sha256(canonical.encode()).hexdigest()
    )
    assert "approv" not in canonical and "baseline" not in canonical


@pytest.mark.parametrize("bad", ["a" * 63, "A" * 64, "../capture", "é" * 64, None, 1, True])
def test_proposal_rejects_ambiguous_identity(bad: Any) -> None:
    with pytest.raises(ValueError):
        proposed_analysis_id(replace(inputs(), capture_sha256=bad))


def test_snapshot_v1_keeps_its_contract_and_label_identity() -> None:
    path = ROOT / "tests/fixtures/capture-contract-v2/supported/observations.json"
    observation: dict[str, Any] = json.loads(path.read_bytes())
    first = build_snapshot(observation, "first review context")
    second = build_snapshot(observation, "different context")
    assert first["snapshot_version"] == second["snapshot_version"] == 1
    assert first["capture_sha256"] == second["capture_sha256"]
    assert first["snapshot_id"] != second["snapshot_id"]
    assert "analysis_id" not in first and "approved" not in first
