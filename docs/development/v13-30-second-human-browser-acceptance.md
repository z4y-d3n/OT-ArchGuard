# V13-30 — Second human browser acceptance

Date: 2026-10-26. Status: **PENDING — no second human result recorded**.
The original owner results are preserved below. The UX scope is not frozen.
Automated structure, link, screenshot and source checks do not grant human PASS.

## Report and identity

After final installed verification, open
`output/v13-ux/wheel-tutorial/comparison/index.html` directly in an ordinary
permitted browser. The exact candidate commit, selected regular installed wheel,
archive SHA-256 and report hashes are authoritative only as recorded in
`output/v13-ux/{release-manifest.json,package-identities.json,owner-review.md}`.
If those receipts or the report are missing or disagree, complete verification
before asking the owner to accept it. The original report remains under
`output/v13-final/wheel-tutorial/`; do not confuse the two review targets.

Record the browser/version, date, reviewed identity, each PASS/FAIL and concrete
comments. No original review date or browser version is invented. Optional
screenshots should identify the page and viewport; a crop is not evidence that
off-screen application content is missing.

## Six real-review criteria

| Criterion | Original owner result | Required second review | Second result |
| --- | --- | --- | --- |
| Immediate comprehension | PASS | Understand packet/address/aggregate counts, main findings and analytical coverage without interpreting JSON | PENDING |
| Communication diagram | PASS | Confirm direction, transport/ports, readable assessments and separate ARP sender/target/Ethernet-delivery semantics | PENDING |
| Navigation and traceability | FAIL | Follow an address to all its communications, related finding, group, association and exact evidence, then return through context links | PENDING |
| Interpretation of analytical results | FAIL | Distinguish declared reachability/discrepancy, unmapped, uncertain, unsupported and missing-observation scope without inferring deployed authorization or blocking | PENDING |
| Legibility | PASS | Inspect timestamps, tables, IPv6, long IDs/review text at approximately 200% zoom and a narrow viewport without losing essential information | PENDING |
| Offline operation and keyboard navigation | PASS | Open all views locally without Internet; use Tab, Shift+Tab and Enter with visible focus and usable native disclosures | PENDING |

Only the owner may supply these second human outcomes. The original navigation
and interpretation FAILs remain unresolved acceptance requirements until then.
Any newly failing previously passing criterion also requires correction and
another affected check.

## Expected walkthrough

1. On Overview, compare summary counts and category meanings with their linked
   records. Counts are packet records/aggregates, not established sessions.
2. From Observed addresses, choose the engineering address `192.0.2.10` or HMI
   `192.0.2.11`, inspect its owner-review status, and follow a communication toward
   `192.0.2.20` TCP/502. The fictional engineering path is model-compatible; the
   HMI example is a declared-model discrepancy. Neither establishes deployed
   authorization, an application outcome or a real firewall decision.
3. Follow **All N related communications**. Use Next/Previous page when necessary,
   then open exact aggregate, finding, evidence and group links. Inspect the
   association and return to its address. A short preview must not conceal
   remaining relationships.
4. Inspect the undeclared TCP/102 example, unknown endpoints, response-only TCP,
   UDP, IPv6 and unsupported content. Confirm that explanations leave unsupported
   or insufficient evidence unassessed and that native results appear only when
   the canonical comparison supplied them.
5. Inspect ARP request/reply panels. Target protocol references and broadcast/
   unicast Ethernet delivery must be clear; no target existence, response or
   physical ownership is inferred.
6. Open Protocols, Coverage, Bidirectional groups, Owner associations, Evidence
   index and Services not observed. Transport/hint rows, coverage counts, empty
   states, review fields and limitations should be understandable without JSON.
   The extended demonstration suppresses absence assessment because interpretation
   is incomplete; it must not invent a missing-service conclusion. A group is
   related observed tuples, not a proven application session.
7. On evidence details, inspect packet indices/offsets, original timestamps,
   reviewed decisions, visible uncertainty, native witness/diagnostic when
   present, canonical identifiers and JSON links. Expand advanced details using
   the keyboard; necessary limitations must already be visible.
8. Repeat principal navigation at approximately 200% zoom and a narrow window.
   Inspect long addresses/IDs and text wrapping, horizontal table access, focus
   visibility, disclosures and the persistent sensitive-metadata warning. If a
   separately supplied dense report omits its diagram, confirm that complete
   tables and all paginated relationships remain accessible.

No server, proxy or network service is required. If automation rejects `file://`,
do not bypass that policy through a local server, alternate proxy or unauthorized
surface. The owner can review the local file in a permitted browser and report
the real outcomes. Screen-reader/print inspection is useful when practical but
does not imply formal accessibility certification.

Only after the second review passes may the owner consider a planned UX freeze,
subject to exact-source hosted validation and publication approval. Security and
correctness maintenance remain possible after any freeze.
