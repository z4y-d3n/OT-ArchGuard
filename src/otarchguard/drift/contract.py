"""Shared finite comparison vocabulary and operation-local accounting."""

from dataclasses import dataclass, field
from typing import Any

from otarchguard.diagnostics import check_limit, fail
from otarchguard.evidence.attachments import canonical

DRIFT_VERSION = 1
POLICY_VERSION = 1
ENGINE_VERSION = "1.4.0-drift.1"
STATES = frozenset({"COMPARABLE", "PARTIALLY_COMPARABLE", "INDETERMINATE", "INCOMPARABLE"})
MODES = frozenset({"strict", "qualified", "descriptive"})
LIMITATIONS = [
    "Differences describe selected finite evidence and declared models, not deployment changes.",
    "Unobserved traffic is not proven absent, blocked or evidence of an offline device.",
    "Raw addresses and matching labels do not establish physical device or sensor identity.",
    "Packet counts are raw counts, not rates or normalized activity trends.",
    "Capture authenticity, clock synchronization and reviewer authority are unattested.",
    "Protocol headers do not prove command execution, application success or authorization.",
    "No incident, attribution, industrial safety or risk severity is determined.",
]


@dataclass(frozen=True, slots=True)
class DriftLimits:
    revisions: int = 64
    collections: int = 64
    keys: int = 50_000
    findings: int = 20_000
    protocol_records: int = 50_000
    references: int = 200_000
    report_bytes: int = 32 * 1024 * 1024
    native_queries: int = 128
    work_units: int = 2_000_000


DRIFT_LIMITS = DriftLimits()


@dataclass(slots=True)
class Budget:
    limits: DriftLimits = DRIFT_LIMITS
    used: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if type(self.limits) is not DriftLimits:
            fail("DRIFT_LIMIT", "$", "Use the supported comparison limit contract.")
        for name in DriftLimits.__dataclass_fields__:
            value = getattr(self.limits, name)
            if type(value) is not int or not 0 < value <= getattr(DRIFT_LIMITS, name):
                fail("DRIFT_LIMIT", "$", "Comparison limits may only narrow supported ceilings.")

    def charge(self, name: str, amount: int = 1) -> None:
        if type(amount) is not int or amount < 0 or name not in DriftLimits.__dataclass_fields__:
            fail("DRIFT_LIMIT", "$", "Unsupported comparison budget charge.")
        count = self.used.get(name, 0) + amount
        check_limit("drift_" + name, count, getattr(self.limits, name))
        self.used[name] = count


@dataclass(frozen=True, slots=True)
class Side:
    """Operation-owned validated inputs; never accepted as public validation authority."""

    analysis: dict[str, Any]
    snapshot: dict[str, Any]
    attachments: dict[str, dict[str, Any]]


def source(side: Side) -> dict[str, Any]:
    return {
        "analysis_id": side.analysis["analysis_id"],
        "snapshot_id": side.snapshot["snapshot_id"],
        "capture_sha256": side.analysis["capture_sha256"],
        "observations_sha256": side.analysis["observations_sha256"],
        "producer_semantics_sha256": side.analysis["producer_semantics_sha256"],
        "attachments": {k: v["attachment_id"] for k, v in sorted(side.attachments.items())},
    }


def finding(
    category: str,
    subtype: str,
    key: object,
    reference: object,
    candidate: object,
    comparability: str,
    explanation: str,
    budget: Budget,
    limitations: list[str] | None = None,
) -> dict[str, Any]:
    if comparability not in STATES:
        fail("DRIFT_STATE", "$", "Unsupported comparison state.")
    result = {
        "category": category,
        "subtype": subtype,
        "key": key,
        "reference": reference,
        "candidate": candidate,
        "comparability": comparability,
        "explanation": explanation,
        "limitations": limitations or [],
        "unsupported_interpretations": list(LIMITATIONS),
    }
    budget.charge("findings")
    budget.charge("report_bytes", len(canonical(result)))
    return result
