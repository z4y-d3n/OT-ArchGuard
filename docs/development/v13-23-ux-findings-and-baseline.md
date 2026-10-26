# V13-23 — Human UX findings and preserved baseline

Date: 2026-10-26. Status: **baseline reproduced; original human acceptance
failures remain open pending second review**. This record begins the focused
presentation remediation requested after the earlier engineering acceptance.
It does not reopen the validated parser or replace human feedback with link tests.

## Authoritative original owner review

| Criterion | Original owner result | Second review of corrected report |
| --- | --- | --- |
| Immediate comprehension | PASS | PENDING |
| Communication diagram | PASS | PENDING |
| Navigation and traceability | FAIL | PENDING |
| Interpretation of analytical results | FAIL | PENDING |
| Legibility | PASS | PENDING |
| Offline operation and keyboard navigation | PASS | PENDING |

The two FAIL results are product-acceptance findings. A page may load, all links
may resolve, and the analyst may still lack the context needed to navigate or
interpret it. Automated correctness, screenshots and DOM inspection support the
next review; only the owner's actual second review can accept those criteria.
Previously passing criteria must also be rechecked on the corrected report.

## Exact baseline and reproduction

The branch began at `e763f0cb6591dee6b80b6aa846286d2b901a95ae`, a clean
documentation-only child of hosted candidate
`5c4c18da4711c36f4f5750c03009d429551d0cf0`. Six-platform run
[40246239841](https://github.com/z4y-d3n/OT-ArchGuard/actions/runs/40246239841)
passed for `5c4c18d`; it does not validate subsequent renderer changes.
[V13-27](v13-27-source-and-release-provenance.md) records independently verified
source trees, packages, archived test receipts and the documentation relationship.

The report named by the owner exists at
`output/v13-final/wheel-tutorial/comparison/index.html`. Its fictional PCAPNG
capture has 12 records, seven cataloged addresses, 12 directed aggregates,
11 bidirectional groups and 12 flow findings. Declared-service absence is
suppressed because the fixture includes uninterpreted content. These are actual
canonical counts, not example totals copied from the prompt.

The original report was reproduced offline from its three canonical artifacts
using a preserved regular installed renderer whose bytes match `5c4c18d`.
All 14 output files were byte-identical. The original capture SHA-256 is
`0c4c4c320bda1bde2991bf3ed21980f1e61736c7ee2e07a7ca75ec390e12362d`;
the overview SHA-256 is
`7b9ff82ea251b7eeb35f1f554ad2bbbe05fd8e1b9ccd58fd24a801f3286480fa`.
Raw receipts remain in `output/v13-ux/provenance/`, including `review.json`
and `original-render-reproduction.json`. The original report was not overwritten.

The accessible attachments inventory contained the pasted instruction but no
`demo_pcap.zip` or screenshot images. Those attachments were not inspected.
The existing named report and its exact reproduced bytes are the primary local
fixture. No finding is inferred from an unavailable screenshot or a cropped image.

## Reproduced issues and remediation boundary

| ID | Baseline problem and cause | Corrected presentation and verification target |
| --- | --- | --- |
| UX-01 | Generic `_json` / `_properties` rendering exposed dictionaries, arrays and escaped JSON hint keys as primary information | Structured protocol tables, coverage properties, readable decisions and semantic evidence sections; retain complete canonical JSON and advanced records |
| UX-02 | Findings used full opaque flow identifiers as primary clickable labels | Communication labels show endpoints, observed transport and destination port when available; exact IDs remain in stable fragments and technical evidence |
| UX-03 | Conversation first/last times displayed rational epoch seconds directly | Exact arithmetic produces readable UTC; canonical rational values and digests remain unchanged, with explicit missing/out-of-range handling |
| UX-04 | Technically valid individual links did not connect address, aggregate, group, finding, review and evidence context clearly | Deterministic contextual links and reciprocal return paths, including complete paginated address-to-communication references |
| UX-05 | Classification codes and terse reasons required excessive analytical inference | Human labels, local interpretation statements and visible uncertainty explain the declared-model scope without asserting deployed behavior |
| UX-06 | Overview prioritized raw metadata over useful counts and analytical coverage | Summary reads canonical counts and category totals; flow findings and declared-service observations use separate units |
| UX-07 | Empty arrays, dominant digests and full review objects added noise | Contextual empty states, readable review fields and collapsed exact identities; uncertainty stays visible rather than hidden in advanced panels |
| UX-08 | Page naming and limited discoverability obscured evidence relationships | Main navigation retains familiar views, `Findings / comparison` bridges terminology, and secondary navigation exposes groups, associations, evidence and address links |

The local implementation is limited to `capture/explorer.py` plus display/view
adapters and UX tests. It adds no runtime dependency, JavaScript, server or active
network operation. The parser, observation model, association logic, native
evaluator, canonical contract versions, identities and source decisions are
preservation requirements, not renderer implementation choices.

## Preserved accepted strengths

The communication diagram retains separate directed IP lanes, transport/ports,
evidence links, readable assessment labels and exact codes. ARP uses sender/target
field panels with actual Ethernet delivery; it does not draw a unicast arrow to
a merely referenced target. A direct source-text comparison confirms `_diagram`
is unchanged from `5c4c18d`; `diagram-preservation.json` records this preliminary
check. Complete tables remain the navigation fallback when the diagram is dense.

Observed traffic never proves authorization, a successful application exchange,
established session or actual firewall behavior. Missing traffic never proves
blocking. Accepted associations remain owner assertions for finite evidence;
ARP targets do not become observed devices through presentation changes.

## Verification and next acceptance

Preliminary display/view checks are recorded in
[V13-25](v13-25-timestamp-and-summary-validation.md). Independent UX tests inspect
actual generated markup and relationships, not the renderer's own helper output.
Integration review also exercises dense/paginated paths before finalization;
an initial link expectation is not accepted merely because an endpoint exists.

[V13-24](v13-24-readable-evidence-and-navigation.md) records the actual revised
presentation and traversal design. Final exact-source installed wheel/sdist,
contract invariance, safety, resource and hosted receipts belong to the new
regression records. A fresh report from that verified candidate must receive a
separate real owner review. No final installed, hosted or human PASS is claimed
by this baseline document.
