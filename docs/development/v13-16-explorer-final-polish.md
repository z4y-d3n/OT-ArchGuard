# V13-16 — Explorer terminology and legibility

## A. Executive status

PASS for implemented/static engineering checks; interactive accessibility and
human visual acceptance remain PARTIAL in V13-17. No WCAG certification is claimed.

## B. Changes

Base: dfcb6d9d6c2c1b3b475f1f6a64b193362cabed98. Final source identity is in
V13-20's release manifest. Changed production file: capture/explorer.py.
The existing deterministic lanes, bounded omission and offline publication remain.

- `1 packet records` becomes `1 packet`; other counts use `packets`.
- Every implemented classification has a readable human label; exact unchanged
  codes remain in overview, finding/conversation tables and raw evidence/JSON.
- ARP panels show request/reply, Sender IP, Target IP and actual Ethernet delivery,
  with an explicit nonexistence/ownership/response caution and no target arrow.
- Address navigation no longer calls references verified devices. Host tables
  disclose observation roles, unresolved identity and target-only exclusions.
- Conversation headings distinguish IP endpoints from ARP protocol references;
  missing ports display Unavailable. Rows link to complete evidence details.
- Taller deterministic lanes keep human labels and exact codes on separate lines.
  IPv6 remains in independent endpoint boxes. Diagram bounds remain 16 addresses /
  24 aggregates; all records remain in paginated accessible tables and JSON.

Before: ARP used Observed source/destination with a directed target arrow and an
opaque assessment code. After: separate ARP evidence panels preserve protocol
reference semantics. The immutable baseline's generated report and earlier
SVG rasters remain under output/v13-audit; the final installed report is identified
in V13-17. No public code enumeration or native model behavior was changed for UI.

## C. Evidence

`tests/test_capture_explorer_polish.py` checks singular/plural, request/reply,
broadcast/unicast, no ARP destination arrow, labels for all nine implemented codes,
privacy/path/payload exclusions, skip links, audited local links and dense fallback.
`test_capture_independent_publication.py` retains pagination/finding references and
independent directional lanes; its expected path count now excludes ARP panels.
Targeted source run: 9 tests passed after final fixture correction. Final installed
full-suite execution, commands and raw XML are recorded in V13-20.
Independent read-only review found no further Explorer semantic/security issue.

The existing independent HTML parser audits every generated link/fragment before
publication. Semantic headings, scoped table headers, descriptive evidence links,
skip navigation, keyboard focus outlines, SVG title/description, scroll regions,
wrapping and responsive CSS are preserved. No classification depends on color.

## D. Privacy, quality and limits

All pages retain the sensitive-network-metadata notice. Capture payloads, input
paths, source comments, interface names and name-resolution/secrets blocks are
not copied to reports. Exact IP/MAC/port/timestamp/owner-review metadata remains
sensitive; no complete anonymization is asserted. Output uses local CSS, no script,
no forms, no external resources and restrictive CSP. JSON review fields remain exact
while HTML applies existing path/bidi display minimization.

Scroll regions preserve large diagrams/tables on narrow screens without shrinking
text to illegibility. Print SVG scales separately. Actual zoom, keyboard interaction,
contrast perception, screen-reader behavior and browser rendering are distinct
verification tasks in V13-17. No synthetic raster or source audit substitutes for
human acceptance. New test counts overlap full-suite counts and are not additive.

## E. Risks and next step

No unresolved confirmed UI correctness defect was found in bounded automated review.
The remaining material gap is actual owner browser acceptance. Open the exact final
installed tutorial in V13-17, record results and correct observed defects before
publication. Source/artifact identities are bound by V13-20, not this prose.
