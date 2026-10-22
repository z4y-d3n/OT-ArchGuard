# Synthetic reference architecture walkthroughs

These are finite, invented teaching models using documentation IPv4 addresses.
They are not recommended production designs or standards/compliance evidence.
Service labels/ports identify synthetic listeners; no actual protocol behavior,
authentication, return traffic, compromise or process impact is verified.
Owner criticality and completeness assertions are descriptive only.

Run from the repository root after the regular installed package:

```powershell
.\.venv\Scripts\python.exe examples/run_examples.py
```

The runner invokes the **installed CLI** 27 times. For every YAML below it runs
`validate`, `check`, and `exposure --scenario SCENARIO`; for every baseline/proposal
pair it runs `compare --scenario SCENARIO` twice, writing HTML and JSON. It checks
native exits and empty stderr, stops on any mismatch, and writes reports to
`output/examples/` (ignored by Git). No network or browser is involved.

To run a single example explicitly, substitute FAMILY, FILE and SCENARIO from
the table below; these commands apply to **each** listed file:

```powershell
.\.venv\Scripts\otarchguard.exe validate examples/FAMILY/FILE.yaml
.\.venv\Scripts\otarchguard.exe check examples/FAMILY/FILE.yaml
.\.venv\Scripts\otarchguard.exe exposure examples/FAMILY/FILE.yaml --scenario SCENARIO
.\.venv\Scripts\otarchguard.exe compare examples/FAMILY/baseline.yaml examples/FAMILY/proposed.yaml --scenario SCENARIO --report output/FAMILY-comparison.html
```

Create `output/` first if not using the runner. For all seven YAML files,
validation succeeds with exit 0. Check/exposure/comparison results are:

| Family / file | Scenario | Reachable interval observations / destination assets | Check/exposure exit | Main finding |
| --- | --- | --- | --- | --- |
| segmented-plant/baseline | plant_scope | 5 / 4 | 0 | All nine independent intents pass. |
| segmented-plant/proposed | plant_scope | 6 / 4 | 1 | Enterprise→PLC TCP/502 violates prohibit_it_ot. |
| flat-plant/baseline | plant_scope | 3 / 2 | 0 | eng→PLC, HMI→PLC and eng→HMI permitted. |
| flat-plant/proposed | plant_scope | 1 / 1 | 1 | Only eng→PLC remains; req_hmi_plc fails. |
| remote-support/baseline | support_scope | 4 / 4 | 0 | All eight approved boundary-device intents pass. |
| remote-support/proposed | support_scope | 5 / 4 | 1 | Added explicit direct IT→PLC path violates prohibit_it_ot. |
| remote-support/application-only | support_scope | 3 / 3 | 1 | req_jump_scada fails; application permissions do not relay IT→PLC. |

All three baseline→proposed comparisons exit **1**, with complete reports.
Segmented and remote proposals each add the single IT→PLC TCP/502 observation,
with no newly reachable asset: PLC was already reachable from another origin.
The flat proposal removes HMI→PLC TCP/502 and eng→HMI TCP/443; HMI is no longer
reachable in the finite scope, and the broken HMI requirement remains prominent.
Those decreases are not an operational success or a risk-reduction claim.

## Segmented manufacturing plant

The four zones are enterprise (external), industrial DMZ, supervisory and cell
control. The historian is owned/placed in the DMZ, SCADA in supervisory, and the
engineer/critical PLC in control. Firewall ownership remains DMZ while its
interfaces are placed in four zones. Pairwise conduits and explicit transitions
separate selected historian/engineering communications. Baseline includes a
declared direct IT/control candidate transition without permission. The proposal
removes the IT→PLC deny and grants TCP/1–65535 on that specific path, exposing the
declared TCP/502 listener. No conduit or role itself grants forwarding.

## Flat/permissive plant

Three endpoints share a control zone but connect through only three explicit
directed edges. Broad endpoint selectors and TCP/1–65535 permits produce three
observations, not arbitrary full-mesh connectivity. Narrowing to eng→PLC TCP/502
also removes required HMI→PLC traffic. The report's operational section shows
`req_hmi_plc` as FAILED before discussing lower exposure.

## Remote-support design

Baseline is canonically identical to the approved `boundary-device.yaml`: every
asset/interface ID, administrative owner, placement, service binding, forwarding
transition and original rule/intent is preserved. IT reaches only the jump
management listener; independently initiated jump→SCADA, jump→firewall-management
and SCADA→PLC permissions remain separate.

The proposal adds an explicit `f_it_ot` fw_it→fw_ot forwarding transition,
pairwise `c_it_ot`, matching SUC access point and endpoint-preserving IT→PLC
permission, and removes the IT→PLC deny. This is a deliberately declared bypass;
the two original consecutive forwarding edges still cannot compose without a
transport transition. The negative `application-only` variant removes only
`f_dmz_ot` and its rule references. IT→jump remains permitted, SCADA→PLC remains
permitted, but IT cannot relay through application services to reach PLC.
The unmodeled cabinet access point and external support dependency remain visible.

## Reproduction and review

`generate_examples.py` reproduces the seven checked-in YAML files from the public
schema fixtures, using existing PyYAML only. Run it deliberately when editing
examples; it overwrites these generated teaching YAML files:

```powershell
.\.venv\Scripts\python.exe examples/generate_examples.py
```

Expected results are executed by `tests/test_reporting.py`, with witness replay,
not assumed from file names. Repeated reports and canonical input permutations
are tested byte-for-byte. See [report format and limitations](../docs/reporting.md).
Open generated HTML directly from disk; the application requires no server,
scripts, external styles/fonts or images. Automated parser/XML and network-blocked
runtime tests complement, but do not replace, human offline visual review.
