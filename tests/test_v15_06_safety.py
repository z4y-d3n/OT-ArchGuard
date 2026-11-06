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
from otarchguard.explorer import ExploreOptions, generate_explorer, path
from otarchguard.reachability import evaluate_query
from otarchguard.reporting import LIMITATIONS


def test_alternate_multihop_route_and_critical_forwarding(boundary: dict[str, Any]) -> None:
    # Reuse the three-zone fixture, adding a second explicit gateway so the
    # route IT -> DMZ -> OT contains transport between its forwarding steps.
    # Consecutive forwarding steps alone are not supported model transitions.
    boundary["assets"].append({**boundary["assets"][1], "id": "gateway"})
    boundary["interfaces"].extend(
        [
            {
                "id": "gw_dmz",
                "asset_id": "gateway",
                "placement_zone_id": "dmz",
                "ipv4": "198.51.100.2/24",
            },
            {
                "id": "gw_ot",
                "asset_id": "gateway",
                "placement_zone_id": "control",
                "ipv4": "203.0.113.2/24",
            },
        ]
    )
    boundary["transport_edges"].extend(
        [
            {
                "id": "t_fw_gw",
                "source_interface_id": "fw_dmz",
                "destination_interface_id": "gw_dmz",
            },
            {
                "id": "t_gw_scada",
                "source_interface_id": "gw_ot",
                "destination_interface_id": "scada_net",
            },
        ]
    )
    boundary["forwarding_edges"].append(
        {
            "id": "f_gw_ot",
            "ingress_interface_id": "gw_dmz",
            "egress_interface_id": "gw_ot",
            "conduit_id": "c_dmz_ot",
        }
    )
    boundary["conduits"].append(
        {**boundary["conduits"][0], "id": "c_it_ot", "zone_ids": ["enterprise", "control"]}
    )
    boundary["transport_edges"].append(
        {
            "id": "direct",
            "source_interface_id": "it_net",
            "destination_interface_id": "scada_net",
            "conduit_id": "c_it_ot",
        }
    )
    boundary["suc"]["access_points"].append(
        {
            "id": "direct_access",
            "kind": "modeled_network",
            "description": "Fictional independent direct crossing.",
            "external_interface_id": "it_net",
            "internal_interface_id": "scada_net",
            "edge_ids": ["direct"],
        }
    )
    rule = deepcopy(boundary["rules"][0])
    rule.update(
        id="allow_it_scada",
        destination={"asset_ids": ["scada"]},
        edge_ids=["t_it_fw", "f_it_dmz", "t_fw_gw", "f_gw_ot", "t_gw_scada"],
    )
    boundary["rules"].append(deepcopy(rule))
    rule.update(id="deny_direct", edge_ids=["direct"], effect="deny")
    boundary["rules"].append(rule)

    def check(data: dict[str, Any], expected: bool) -> None:
        assert oracle(data, "it", "svc_scada", 3389) is expected
        result = evaluate_query(validate_bytes(yaml.safe_dump(data).encode()), "it", "svc_scada")
        assert len(result.intervals) == 1 and result.intervals[0].reachable is expected
        witness = result.intervals[0].witness
        if expected:
            assert witness is not None
            replay_raw(data, witness)
        else:
            assert witness is None and result.intervals[0].diagnostics is not None

    check(boundary, True)
    blocked = deepcopy(boundary)
    deny = deepcopy(rule)
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
    alternative = deepcopy(rule)
    alternative.update(id="allow_direct", edge_ids=["direct"], effect="allow")
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
    options = ExploreOptions(traces=(("eng", "svc_plc"),), check=True)
    if invalid:
        with pytest.raises(ModelError):
            generate_explorer(model, site, options=options)
        assert not site.exists()
    else:
        assert generate_explorer(model, site, options=options)["status"] == "complete"
        text = " ".join(p.read_text(encoding="utf-8") for p in site.glob("*.html"))
        assert minimal["suc"]["completeness_assertion"] in text
        assert "Declared" in text and "unassessed" in text
        trace_page = site / path("analysis", ["trace", "eng", "svc_plc"])
        assert "No authorized path for evaluated ports" in trace_page.read_text(encoding="utf-8")
