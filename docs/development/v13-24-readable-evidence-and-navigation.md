# V13-24 — Readable evidence and contextual navigation

Date: 2026-10-26. Status: **local implementation and preliminary structural
verification; final installed-candidate and human acceptance pending**. This
record covers the readable-presentation and navigation requirements from the
remediation prompt. The original six owner results remain unchanged in
[V13-23](v13-23-ux-findings-and-baseline.md), including navigation and interpretation
FAIL. The second review is PENDING.

## What changed and why

`src/otarchguard/capture/explorer.py` now builds readable records and reciprocal
context links. `capture/display.py` handles escaped structured fields, contextual
empty states, exact identities and UTC display. `capture/views.py` supplies
overview, metadata, protocol, coverage and interpretation views. These are static
presentation adapters; they do not reparse packets, infer sessions, choose owner
identities or call the native evaluator to create new conclusions.

| View | Primary analyst information | Exact evidence retained |
| --- | --- | --- |
| Overview | Packet/address/aggregate/group counts, interpreted/unsupported coverage, finding categories and scope | Capture/interface metadata, exact identity and canonical observations link |
| Protocols | Transport-count rows and protocol/transport/port/count/category hint columns | Original aggregate hints in canonical observations; overlapping contributions remain counted |
| Coverage and limits | Processing counts, readable limitations, container completeness and scoped/suppressed absence status | Original limits, coverage values and classifications in canonical artifacts |
| Observed addresses | Roles, appearances, MAC evidence, readable review status, preview and complete communication-reference link | Full linked association records and original observation fields |
| Owner associations | Address, decision, candidates, selection, reviewer and rationale | Evidence bindings and complete canonical review record in technical disclosure |
| Conversations | Readable communication identity, exact UTC display, finding, group and endpoint context | Canonical flow ID, rational time and aggregate in evidence details/JSON |
| Bidirectional groups | Member endpoint context, transport, aggregate and packet counts, times and linked members | Original member IDs and initiation metadata; no session-success inference |
| Findings / comparison | Communication label, model assessment, plain interpretation and recorded reason | Exact classification code, native result and canonical comparison |
| Evidence index/details | Communication summary, observed metadata, packet references, associations, model result, return links and visible uncertainty | Full aggregate, identifiers and evaluator record remain available as advanced data |
| Services not observed | Declared service and finite comparison scope, or an explicit suppressed/not-requested state | Original absence assessment and records; no claim of blocking or unavailability |

The protocol page explicitly states: “Port hints are associations based on
observed port numbers. They do not confirm that the corresponding industrial
application protocol was decoded or used successfully.” Transport is taken from
the observed aggregate; hints are not invented application recognition. Counts
may overlap, and their sum can exceed packet records.

The coverage page distinguishes processed container framing, interpreted packets,
analytical eligibility and actual sensor visibility. An empty capture limitation
list becomes a contextual sentence, never a claim that the network was fully
visible. Unsupported/uncertain conditions and scope explanations remain outside
collapsed technical panels.

## Navigation and complete address paths

Main navigation exposes Overview, Observed addresses, Conversations, Protocols,
Findings / comparison, and Coverage and limits. Secondary navigation exposes
Bidirectional groups, Owner associations, Evidence index, Address communication
links, and Services not observed. Current-page markup and visible styling identify
the active view. Paginated pages stay in their logical view family.

Each record receives a generated anchor tied to the original identity. URL syntax
is renderer controlled; imported identifiers cannot become executable links.
Primary link text describes the communication, for example endpoints and TCP/502,
while full canonical identities remain in fragments and technical details.
Missing endpoints are explicit. ARP labels retain sender/target terminology.

The observed-address row previews up to eight related aggregates for bounded
layout, then links **All N related communications** to the first matching record
in the complete `address-links*.html` index. This index is ordered by cataloged
address and canonical aggregate order. Every address/aggregate relationship is
listed exactly once for that address, with address context, communication,
exact evidence and finding links. A flow mentioning the same cataloged address
at both ends contributes one address-reference row.

For a high-cardinality address, the complete route is:

1. Open the observed address in `hosts*.html`.
2. Select **All N related communications**; the fragment opens its first address
   reference in `address-links*.html`.
3. Follow **Next page** while that address's records continue. Every relationship
   remains accessible, including those beyond the eight-row preview or a page boundary.
4. Open the readable communication to its anchored directed aggregate, or use
   the same reference row's exact evidence/finding link.
5. From the aggregate, follow evidence, finding, related group or either cataloged
   endpoint. From details, return to that communication, its evidence index entry,
   group or finding. Associations return to the correct address and its complete
   communication references.

Pagination includes page/record counts and previous/next links. Conversation,
group, finding, association, evidence and address targets are precomputed for
their actual page, so links do not assume the first page. The evidence index
uses `evidence.html` / `evidenceindex-N.html`; detail pages keep `evidence-N.html`,
avoiding filename collisions. Complete canonical JSON remains directly linked.

Uncataloged addresses are labeled as such, without invented host or association
links. An ARP target can link to a cataloged address only when the existing
canonical catalog independently contains that address; the label still identifies
it as an ARP target reference. A target-only ARP mention creates no catalog or
mapping proposal through this renderer.

## Evidence detail and analytical meaning

Details show communication summary, observed metadata, packet record/block
offsets, interface references, captured/original lengths, exact times, bounded
sampling omissions, linked owner decisions and architecture assessment. Native
query context and selected witness/diagnostic remain available when the producer
actually supplied them. No unavailable native result is invented.

The interpretation statements qualify each actual classification: model-compatible
reachability is the specific declared initiation/port result; a discrepancy is
model disagreement, not a proven intrusion or deployed firewall denial. Unmapped,
ambiguous, uncertain and unsupported observations remain unassessed. Declared
service absence is finite capture evidence, never proof of blocking outside it.
There is no new severity scale.

The accepted diagram is preserved: its `_diagram` function source is unchanged
from `5c4c18d`, including separate IP lanes, exact port/direction labels, evidence
links, ARP panels and Ethernet broadcast/unicast wording. More than 16 addresses
or 24 aggregates produces the existing explicit diagram omission, with complete
paginated records still accessible. Neither the overview nor the tables imply
physical topology, IP ownership or a completed session.

## Verification scope and pending review

Preliminary display/view executions and exact timestamp cases are recorded in
[V13-25](v13-25-timestamp-and-summary-validation.md); their counts overlap and
are not final installed-suite counts. The independent
`tests/test_capture_ux_integrity.py` suite checks generated HTML with its own
parser, exact frozen JSON, unchanged core module hashes, link/fragment uniqueness,
meaningful text, contextual joins, dense pagination, ARP target exclusion,
determinism, network denial, escaping and failed-output preservation.

Initial integration checks exposed assumptions that every address row should
contain every direct aggregate link. The intended bounded design instead requires
the complete paginated relationship path above; verification must traverse and
check that path without dropping the requirement that every relationship is
accessible. Current-page checks must likewise inspect the actual logical
navigation target. Final focused and installed results belong to the final
regression record, not an inferred PASS from this design description.

Rendering retains escaping, local CSS, restrictive CSP, sensitive-data warnings,
no-clobber staging, per-page/site/output budgets and JavaScript-free links and
native disclosures. No new analytical contract or producer dependency is added.
Actual keyboard/focus, 200% zoom, narrow layout, long strings and human comprehension
still require the second owner browser review. Static structure is supporting
evidence and does not establish WCAG certification or resolve the original two FAILs.
