"""Small release-critical relations using the existing raw-declaration oracle."""

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
import yaml
from test_reachability_oracle import oracle, replay_raw
from typer.testing import CliRunner

from otarchguard.api import validate_bytes
from otarchguard.cli import app
from otarchguard.diagnostics import ModelError
from otarchguard.explorer import generate_explorer
from otarchguard.reachability import evaluate_query
from otarchguard.reporting import LIMITATIONS


def test_alternate_multihop_route_and_critical_forwarding(boundary: dict[str, Any]) -> None:
    # Existing IT -> firewall -> DMZ listener path. Add a separately denied
    # direct route in the same declared conduit; it must not remove the gateway.
    boundary["transport_edges"].append(
        {
            "id": "direct",
            "source_interface_id": "it_net",
            "destination_interface_id": "jump_net",
            "conduit_id": "c_it_dmz",
        }
    )
    boundary["suc"]["access_points"].append(
        {
            "id": "direct_access",
            "kind": "modeled_network",
            "description": "Fictional independent direct crossing.",
            "external_interface_id": "it_net",
            "internal_interface_id": "jump_net",
            "edge_ids": ["direct"],
        }
    )
    rule = deepcopy(boundary["rules"][0])
    rule.update(id="deny_direct", edge_ids=["direct"], effect="deny")
    boundary["rules"].append(rule)

    def check(data: dict[str, Any], expected: bool) -> None:
        assert oracle(data, "it", "svc_jump", 3389) is expected
        result = evaluate_query(validate_bytes(yaml.safe_dump(data).encode()), "it", "svc_jump")
        assert len(result.intervals) == 1 and result.intervals[0].reachable is expected
        witness = result.intervals[0].witness
        if expected:
            assert witness is not None
            replay_raw(data, witness)
        else:
            assert witness is None and result.intervals[0].diagnostics is not None

    check(boundary, True)
    blocked = deepcopy(boundary)
    deny = deepcopy(blocked["rules"][0])
    deny.update(id="deny_critical", edge_ids=["f_it_dmz"], effect="deny")
    blocked["rules"].append(deny)
    check(blocked, False)
    # A general allow cannot defeat the applicable specific deny.
    general = deepcopy(deny)
    general.update(id="general_allow", effect="allow", source={"all_assets": True})
    blocked["rules"].append(general)
    check(blocked, False)
    # Restore the sole transition, then permit an independent path and break
    # the original again. The independent witness must survive.
    restored = deepcopy(blocked)
    restored["rules"] = [r for r in restored["rules"] if r["id"] != "deny_critical"]
    check(restored, True)
    blocked["rules"] = [r for r in blocked["rules"] if r["id"] != "deny_direct"]
    alternative = deepcopy(blocked["rules"][0])
    alternative.update(id="allow_direct", edge_ids=["direct"])
    blocked["rules"].append(alternative)
    check(blocked, True)
    # Remove the explicit forwarding declaration, retaining a valid model.
    missing = deepcopy(boundary)
    missing["forwarding_edges"] = [e for e in missing["forwarding_edges"] if e["id"] != "f_it_dmz"]
    for r in missing["rules"]:
        r["edge_ids"] = [e for e in r["edge_ids"] if e != "f_it_dmz"]
    missing["suc"]["access_points"] = [
        a for a in missing["suc"]["access_points"] if a["id"] != "ap_it_dmz"
    ]
    check(missing, False)


@pytest.mark.parametrize("invalid", [False, True])
def test_rejection_versus_model_negative_through_public_outputs(
    minimal: dict[str, Any], tmp_path: Path, invalid: bool
) -> None:
    # A validated finite model can omit physical edges. Its conclusion must
    # retain the completeness declaration and the existing model limitations.
    minimal["rules"] = []
    minimal["intents"][0]["kind"] = "prohibited"
    if invalid:
        minimal["transport_edges"][0]["destination_interface_id"] = "missing"
    model = tmp_path / "model.yaml"
    model.write_text(yaml.safe_dump(minimal), encoding="utf-8")
    runner = CliRunner()
    for format in ("json", "html"):
        report = tmp_path / f"report.{format}"
        result = runner.invoke(
            app, ["check", str(model), "--report", str(report), "--report-format", format]
        )
        if invalid:
            assert result.exit_code == 2 and not result.stdout and not report.exists()
            assert json.loads(result.stderr)["category"] == "invalid_input"
        else:
            assert result.exit_code == 0, result.output
            text = report.read_text(encoding="utf-8")
            assert all(limitation in text for limitation in LIMITATIONS)
            assert minimal["suc"]["completeness_assertion"] in text
            if format == "json":
                record = json.loads(text)
                assert record["status"] == "passed"
                assert record["scope"].startswith("Declared initiation model")
                interval = record["result"]["intents"][0]["queries"][0]["intervals"][0]
                assert interval["reachable"] is False and interval["diagnostics"]
    site = tmp_path / "site"
    if invalid:
        with pytest.raises(ModelError):
            generate_explorer(model, site)
        assert not site.exists()
    else:
        assert generate_explorer(model, site)["status"] == "complete"
        text = " ".join(p.read_text(encoding="utf-8") for p in site.glob("*.html"))
        assert minimal["suc"]["completeness_assertion"] in text
        assert "Declared" in text and "unassessed" in text
