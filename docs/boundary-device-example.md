# Synthetic boundary-device worked example

This logical example uses invented inventory and declared initiation paths.
Expected outcomes are exercised by existing tests and installed walkthroughs.
It is not a deployment recommendation or session simulator.

## SUC and owner assertions

| SUC field | Declared value |
| --- | --- |
| ID / name | `demo_cell` / Synthetic packaging control cell |
| Purpose / intended use | Demonstrate controlled remote maintenance initiation and PLC supervision using declared network paths. |
| Controlled process | Imaginary packaging conveyor with one PLC and supervisory SCADA; no actual process or hardware. |
| Boundary description | Internal inventory: `fw`, `jump`, `scada`, `plc`. External context: enterprise workstation `it`. The perimeter crossing is the firewall's IT-to-DMZ forwarding transition, not inclusion of IT in the YAML inventory. |
| Completeness assertion | The example owner asserts this finite teaching inventory and listener set; physical access, return traffic, authentication, external services and deployed configurations are not verified. No real plant completeness is claimed. |
| Access point `ap_it_dmz` | Kind `modeled_network`; external-placement interface `fw_it`; internal-placement interface `fw_dmz`; crossing edge set `{f_it_dmz}`. No reverse crossing is declared. Both interfaces belong to internal asset `fw`. |
| Access point `ap_cabinet` | Kind `unmodeled`; synthetic cabinet/service access, description only; no edge/interface references or reachability effect. |
| Dependency `dep_support` | External asset set `{it}`; required-intent set `{req_it_jump}`; description: enterprise support origin required for this declared remote-maintenance use case. It grants no permissions. |

No SL-T, SL-C or SL-A values are supplied; all remain unassessed. Assessment and
approval evidence is external. Inventory scope is not an exposure-source set.

## Zones and classifications

| Zone ID | Name / purpose | SUC scope | Owner grouping rationale | Safety designation |
| --- | --- | --- | --- | --- |
| `enterprise` | Enterprise IT / support origin | external | Business workstation under enterprise administration; outside the assessed cell. | `non_safety` |
| `dmz` | Industrial DMZ / managed access and boundary administration | internal | Jump service and firewall administrative ownership grouped for this simplified teaching model. This ownership does not place all firewall interfaces in the DMZ. | `non_safety` |
| `control` | OT control / supervisory and controller functions | internal | SCADA and PLC share the declared cell supervision needs; narrow required flows are independently authored. | `non_safety` |

| Asset ID | Role | Kind | Owner zone | Scope | Domain classification | Safety classification | Criticality |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `it` | Enterprise support workstation | `endpoint` | `enterprise` | external | `business` | `non_safety` | medium |
| `fw` | Three-interface firewall/gateway | `boundary_device` | `dmz` | internal | `iacs` | `non_safety` | high |
| `jump` | Jump server | `endpoint` | `dmz` | internal | `iacs` | `non_safety` | high |
| `scada` | SCADA server | `endpoint` | `control` | internal | `iacs` | `non_safety` | high |
| `plc` | Controller | `endpoint` | `control` | internal | `iacs` | `non_safety` | critical |

Classification is explicitly supplied by the example owner. A critical PLC is
not automatically safety-related. None of these classifications supplies a rule.

## Interfaces and services

All addresses are synthetic documentation addresses in one modeled address
space. CIDRs are labels/validation inputs; they never generate connectivity.

| Interface ID | Asset | Placement zone | IPv4 interface CIDR |
| --- | --- | --- | --- |
| `it_net` | `it` | `enterprise` | `192.0.2.10/24` |
| `fw_it` | `fw` | `enterprise` | `192.0.2.1/24` |
| `fw_dmz` | `fw` | `dmz` | `198.51.100.1/24` |
| `fw_ot` | `fw` | `control` | `203.0.113.1/24` |
| `jump_net` | `jump` | `dmz` | `198.51.100.10/24` |
| `scada_net` | `scada` | `control` | `203.0.113.10/24` |
| `plc_net` | `plc` | `control` | `203.0.113.20/24` |

| Service ID | Destination asset/interface | Protocol / destination ports | Meaning of declaration |
| --- | --- | --- | --- |
| `svc_jump` | `jump` / `jump_net` | TCP / `{3389}` | Synthetic remote desktop listener; no authentication/session claim. |
| `svc_scada` | `scada` / `scada_net` | TCP / `{3389}` | Separate SCADA maintenance initiation target. |
| `svc_plc` | `plc` / `plc_net` | TCP / `{502}` | Synthetic PLC service; no industrial-protocol or process-safety inference. |
| `svc_fw` | `fw` / `fw_dmz` | TCP / `{443}` | Management listener on the DMZ interface only; not on `fw_it` or `fw_ot`. |

## Pairwise conceptual conduits

| Conduit ID | Exactly two zone IDs | Purpose / common security needs | Member edge IDs |
| --- | --- | --- | --- |
| `c_it_dmz` | `{enterprise, dmz}` | Restrict enterprise maintenance initiation to the declared jump listener; no implied management access or onward initiation. | `{f_it_dmz}` |
| `c_dmz_ot` | `{dmz, control}` | Restrict DMZ-origin maintenance initiation to the SCADA listener; no implicit direct jump-to-PLC access. | `{f_dmz_ot}` |

These are two conceptual channel groups, not one three-zone conduit. The single
physical firewall is represented once, owned by `dmz`, with three explicit
attachments. Its internal forwarding edges implement the modeled crossings.
There is no `c_it_ot` conduit or IT-to-OT forwarding edge in the baseline.

## Complete baseline edge inventory

The following are **all** baseline edges. Nothing is implied by lines in a
diagram, common subnets, the presence of a device or conduit, or the ability to
reach a listener. Transport and forwarding alternate for transit paths.

| Edge ID | Kind | Directed interface transfer | Conduit |
| --- | --- | --- | --- |
| `t_it_fw` | transport | `it_net` egress -> `fw_it` ingress | none; both placements enterprise |
| `f_it_dmz` | forwarding | `fw_it` ingress -> `fw_dmz` egress | `c_it_dmz` |
| `t_fw_jump` | transport | `fw_dmz` egress -> `jump_net` ingress | none; both DMZ |
| `t_jump_fw` | transport | `jump_net` egress -> `fw_dmz` ingress | none; both DMZ |
| `f_dmz_ot` | forwarding | `fw_dmz` ingress -> `fw_ot` egress | `c_dmz_ot` |
| `t_fw_scada` | transport | `fw_ot` egress -> `scada_net` ingress | none; both control |
| `t_fw_plc` | transport | `fw_ot` egress -> `plc_net` ingress | none; both control; intentionally no baseline allow |
| `t_scada_plc` | transport | `scada_net` egress -> `plc_net` ingress | none; both control |

Forwarding is individually directed; there is no reverse transfer or implicit
all-interface switch inside `fw`. In particular, after `f_it_dmz` a packet is at
`fw_dmz` **egress**, not the ingress needed for `f_dmz_ot`. No automatic transition
connects these states. `jump` has no internal forwarding edges. A reached jump
application cannot become a new source in an IT-origin query.

## Complete baseline enforcement rules

Each row is one rule, with singleton original source/destination asset selectors
and the exact nonempty edge-ID set shown. All values are explicit; no omitted
wildcards. Permission depends on the original endpoints throughout the path,
not on the intermediate firewall. Deny overrides allow, independent of row order;
absence of a matching allow denies every edge.

| Rule ID | Effect | Source | Destination | Protocol | Ports | Edge IDs |
| --- | --- | --- | --- | --- | --- | --- |
| `allow_it_jump` | allow | `it` | `jump` | TCP | `{3389}` | `{t_it_fw, f_it_dmz, t_fw_jump}` |
| `allow_jump_scada` | allow | `jump` | `scada` | TCP | `{3389}` | `{t_jump_fw, f_dmz_ot, t_fw_scada}` |
| `allow_scada_plc` | allow | `scada` | `plc` | TCP | `{502}` | `{t_scada_plc}` |
| `allow_jump_fw` | allow | `jump` | `fw` | TCP | `{443}` | `{t_jump_fw}` |
| `deny_it_plc` | deny | `it` | `plc` | TCP | `{502}` | `{t_it_fw, f_it_dmz, f_dmz_ot, t_fw_plc}` |

The deny row makes owner intent visible in permissions but is not needed to
prevent the baseline path: missing permits/forwarding already do so. Independent
prohibited intents below are still necessary to test desired policy. Declaring
a required or prohibited intent never creates or removes an edge/permission.

## Intents and expected baseline reachability

| Intent ID | Kind | Source set | Destination-service set | Expected result |
| --- | --- | --- | --- | --- |
| `req_it_jump` | required | `{it}` | `{svc_jump}` | pass |
| `req_jump_scada` | required | `{jump}` | `{svc_scada}` | pass |
| `req_scada_plc` | required | `{scada}` | `{svc_plc}` | pass |
| `req_jump_fw` | required | `{jump}` | `{svc_fw}` | pass |
| `prohibit_it_ot` | prohibited | `{it}` | `{svc_scada, svc_plc}` | pass; neither reachable |
| `prohibit_it_fw` | prohibited | `{it}` | `{svc_fw}` | pass |
| `prohibit_jump_plc` | prohibited | `{jump}` | `{svc_plc}` | pass |
| `prohibit_scada_dmz` | prohibited | `{scada}` | `{svc_jump, svc_fw}` | pass |

Exposure scenario `support_scope` uses origins `{it, jump, scada}` and services
`{svc_jump, svc_scada, svc_plc, svc_fw}`. Self asset/service pairs are excluded as
specified in the domain model. Its ten remaining queries have these outcomes:

| Original source | Destination service | Reachable? | Witness or reason |
| --- | --- | --- | --- |
| `it` | `svc_jump` | yes | `t_it_fw -> f_it_dmz -> t_fw_jump`, all allowed by `allow_it_jump`. |
| `it` | `svc_scada` | no | No IT-to-OT forwarding path; jump sessions cannot compose. |
| `it` | `svc_plc` | no | No suitable forwarding/permits; explicit denial also matches listed edges. |
| `it` | `svc_fw` | no | Reaching `fw_it` cannot satisfy the listener bound to `fw_dmz`; no matching management permits. |
| `jump` | `svc_scada` | yes | `t_jump_fw -> f_dmz_ot -> t_fw_scada`, all allowed by `allow_jump_scada`. |
| `jump` | `svc_plc` | no | Structural path via `t_jump_fw -> f_dmz_ot -> t_fw_plc` lacks permits for original destination `plc`. |
| `jump` | `svc_fw` | yes | `t_jump_fw`, allowed by `allow_jump_fw`; ending at firewall ingress requires no forwarding. |
| `scada` | `svc_jump` | no | No reverse transport/forwarding chain or permissions. |
| `scada` | `svc_plc` | yes | `t_scada_plc`, allowed by `allow_scada_plc`. |
| `scada` | `svc_fw` | no | No reverse management path or permissions. |

Expected exposure: four reachable source/destination/service/port tuples and
four unique destination assets over this scope. All eight intents pass; the
`check` command should exit 0. These are model expectations, not measured
results or security-level/certification evidence. Reversing an initiation or
changing TCP to UDP never inherits permission.

## Independent negative and mutation cases

Each case starts from the baseline and changes only the stated declarations;
keep all references consistent unless invalid-reference behavior is the subject.
Expected exits refer to the CLI contract. The regression suite exercises these boundary cases.

| Case | Mutation/query | Expected behavior and acceptance link |
| --- | --- | --- |
| B01 | Baseline as specified. | Four reachable tuples, all intents pass; `check` exit 0. T21/T23. |
| B02 | Remove `f_dmz_ot` and its references from `allow_jump_scada`/`deny_it_plc`; retain interfaces, conduits and transport. | `jump -> svc_scada` becomes unreachable and `req_jump_scada` fails, exit 1. Multihoming/common ownership cannot replace forwarding. SUC access-point record is unchanged because the removed edge was internal/internal. T06/T23. |
| B03 | Keep `f_dmz_ot` but remove it from `allow_jump_scada`. | Same failed required query, exit 1, now structural path exists but permission is missing. T08/T23. |
| B04 | Add rule `deny_jump_scada`, deny original `jump -> scada` TCP/3389 on `{f_dmz_ot}`, keeping all allows. | Required query fails regardless of rule order, exit 1. Default denial is distinct from explicit matching denial. T08/T23. |
| B05 | Replace `allow_jump_scada` with identical edges/protocol/port but source selector `{fw}`. | `jump -> svc_scada` becomes unreachable: source stays `jump` through the firewall. A newly queried firewall-origin result would be a different query. Exit 1. T06/T23. |
| B06 | Leave baseline; query IT-to-PLC and IT-to-SCADA despite IT-to-jump and jump-to-SCADA being allowed. | Both unreachable. Neither jump application access nor two successive firewall forwarding edges creates an end-to-end path. T09/T11/T23. |
| B07 | Add `allow_it_fw`, allow `it -> fw` TCP/443 on `{t_it_fw}` only. | `it -> svc_fw` remains unreachable because listener ingress is `fw_dmz`, not `fw_it`. Baseline required/prohibited intents still pass, exit 0. No implicit cross-interface management acceptance. T11/T23. |
| B08 | Remove `svc_jump` from `prohibit_scada_dmz` (keep its `svc_fw` prohibition), then add a test intent requiring `scada -> svc_jump`; add no reverse edges/rules. | New requirement fails, exit 1. Avoid a contradictory required/prohibited intent, which would instead be invalid input. This test intent is a definition change, not an unchanged-required-flow regression in comparison. TCP reply handling remains unsupported. T05/T17/T23. |
| B09 | Change `f_dmz_ot` conduit to `c_it_dmz`, or omit it; alternatively add a conduit to same-zone `t_jump_fw`. | Invalid supported placement/pair declarations, exit 2 before analysis, not unreachable and not an IEC violation. T03/T23. |
| B10 | Replace `c_dmz_ot` with a purported single conduit for `{enterprise, dmz, control}`; or request protected transit through `dmz` within one enterprise/control conduit. | Unsupported-model diagnostic, exit 2. Do not silently split, flatten or call a standards violation. T23. |
| B11 | Give `fw` a second owner zone or conduit ownership; alternatively set it to `endpoint` while keeping cross-zone interface placement/forwarding. | Multiple/conduit ownership is unsupported, exit 2. Endpoint placement/forwarding inconsistency is invalid supported input, exit 2. A role string such as firewall grants nothing. T11/T23. |
| B12 | Keep baseline and expand ownership selector for `{enterprise}`, then `{dmz}`. | Enterprise selects `{it}`, DMZ selects `{fw, jump}`. `fw_it` attachment never makes firewall a second enterprise-owned asset. This selector check creates no connectivity. T11/T23. |

B02-B05 reduce exposure from four to three tuples in `support_scope`, while
breaking `req_jump_scada`. Reports must show that regression and failed intent;
the comparison must not describe the change as successful because its
reachability count decreased (exit 1). The same SCADA service and endpoints are
unchanged, so this is a genuine declared required-flow regression. PLC access
from SCADA is unaffected.

For B02 the two pairwise conduits may remain with empty/nonempty membership;
conduit presence alone grants nothing. For a test deleting the actual SUC crossing
`f_it_dmz`, also remove it from all referencing rules and replace the access-point
declaration with an appropriately described unmodeled record if the crossing is
no longer modeled. A dangling access-point edge reference is a validation error,
not evidence of isolation. T22 covers this distinction.

## Unsupported semantics and limits

- One conduit connecting more than two zones, or protected conduit transit through
  a third zone without explicit supported transfers, is unsupported. Two pairwise
  declarations do not prove security of such transit.
- Conduit-owned assets, multiple owner zones and same-interface hairpin forwarding
  are unsupported. One owner zone with explicit boundary-device attachments is
  the accepted bounded representation, not complete normative asset partitioning.
- NAT, proxies, application-session relay/pivoting, stateful return traffic,
  first-match firewall rules, source-interface restrictions for local-origin
  traffic, VLAN/L2, IPv6 and dynamic routing remain unsupported.
- No firewall inspection, real monitoring, physical separation, authentication,
  exploitability, process safety, SL assessment or risk approval is verified.
