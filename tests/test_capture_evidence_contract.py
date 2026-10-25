"""Frozen byte-level artifacts and regeneration are independent consumer contracts."""

import hashlib
import json
from pathlib import Path

import pytest

from tools.freeze_capture_contracts import freeze
from tools.read_capture_evidence import load_bundle

FIXTURES = Path(__file__).parent / "fixtures/capture-contract-v2"
OBSERVATION_IDENTITIES = {
    "supported": "d5761264e32e0f5430cb36580f7075665e5eecd87abb5cc9a7cb090fc4fdca71",
    "limited": "f855b94fb59319edb777a4b30bad3683ac019103dc842e9fa8ae1ffdfc7d76d1",
}


@pytest.mark.parametrize("case", ["supported", "limited"])
def test_frozen_evidence_can_be_consumed_without_any_capture(case: str) -> None:
    manifest = json.loads((FIXTURES / "manifest.json").read_bytes())
    directory = FIXTURES / case
    assert sorted(p.suffix for p in directory.iterdir()) == [".json"] * 3
    for name, expected in manifest["cases"][case]["files"].items():
        assert hashlib.sha256((directory / name).read_bytes()).hexdigest() == expected
    bundle = load_bundle(directory)
    observations = bundle["observations"]
    assert observations["observations_sha256"] == OBSERVATION_IDENTITIES[case]
    assert observations["observation_version"] == 2
    assert {f["transport"] for f in observations["flows"]} >= {"tcp", "udp", "arp", "icmpv6"}
    assert bundle["comparison"]["absence_assessment"]["status"] == (
        "scoped" if case == "supported" else "suppressed"
    )
    if case == "supported":
        assert bundle["comparison"]["declared_services_not_observed"]
    else:
        assert observations["coverage"]["unsupported"] == 1
        assert {f["arp"]["operation"] for f in observations["flows"] if f["arp"]} == {
            "request",
            "reply",
        }
        assert not bundle["comparison"]["declared_services_not_observed"]


def test_goldens_regenerate_with_exact_canonical_bytes(tmp_path: Path) -> None:
    output = tmp_path / "golden"
    freeze(output)
    expected = sorted(p.relative_to(FIXTURES) for p in FIXTURES.rglob("*.json"))
    assert sorted(p.relative_to(output) for p in output.rglob("*.json")) == expected
    for relative in expected:
        assert (output / relative).read_bytes() == (FIXTURES / relative).read_bytes()
