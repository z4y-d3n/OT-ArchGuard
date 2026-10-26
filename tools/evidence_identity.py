"""V14-02 identity proposal probe, deliberately outside runtime snapshot storage.

No ingestion, approval, baseline, persistence or migration is performed here.
Only already validated artifact digests belong in the proposed identity envelope.
"""

import hashlib
import json
from dataclasses import asdict, dataclass


def _sha(value: str) -> bool:
    return len(value) == 64 and all(c in "0123456789abcdef" for c in value)


@dataclass(frozen=True)
class AnalysisInputs:
    capture_sha256: str
    observations_sha256: str
    enrichment_sha256: str | None
    model_sha256: str | None
    mapping_sha256: str | None
    comparison_sha256: str | None
    policy_sha256: str | None
    producer_semantics_sha256: str


def proposed_analysis_id(inputs: AnalysisInputs) -> str:
    """Domain-separated experimental identity, never a snapshot-v1 identifier."""
    fields = asdict(inputs)
    if any(value is not None and not _sha(value) for value in fields.values()):
        raise ValueError("Expected exact lowercase SHA-256 input identities")
    envelope = {"proposal_version": 1, "domain": "otarchguard.analysis", "inputs": fields}
    canonical = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode("ascii")
    return "analysis-proposal-" + hashlib.sha256(canonical).hexdigest()
