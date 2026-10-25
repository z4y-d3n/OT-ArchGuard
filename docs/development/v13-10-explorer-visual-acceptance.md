# V13-10 — PCAP Evidence Explorer visual acceptance

Recorded 2026-10-25. **PARTIAL: static engineering checks completed; manual browser
acceptance NOT RUN.** This record supplements historical gate evidence and does
not change its outcomes. Candidate commit and final integration receipts are
recorded in V13-12 and V13-13.

## Independent findings and corrections

Reviewer C inspected the renderer, shared CSS/link auditor, publication code,
existing fictional report pages and release workflow independently. The original
source inspected was `4fb9b4863ee59684211e7a3315221ff89102bebb`.

| ID | Priority | Actual behavior at starting source | Correction and evidence |
| --- | --- | --- | --- |
| C-01 | P1 | Overview paths returned to one address column; different aggregates shared horizontal corridors, with no transport/port or per-aggregate evidence label. Long IPv6 text could also compete with the routing corridor. | Each directed aggregate receives its own deterministic horizontal SVG lane with labeled source/destination boxes, transport/ports, record count, exact evidence link and separate comparison code. No intermediate network hops are invented. |
| C-02 | P1 | Findings displayed an opaque flow digest without a link to its packet and native-evaluator evidence. | Every finding now links to the exact `evidence-N.html#flow-ID`, including when page size is reduced. The independent assertion fails against the original renderer loaded from Git and passes after integration. |
| C-03 | P2 | The six-job CI matrix collected historical benchmark families but omitted the new capture benchmark family. | Added `python -m benchmarks.capture --output output/capture-benchmark` under the denied-network harness and retained its `benchmark.json` in each job's benchmark artifact. Workflow execution remains NOT RUN until an authorized remote candidate is available. |

The old R/U diagram marks have been replaced by complete classification codes.
The figure explains packet direction separately from initiation inference and
declared-model assessment. A model-unreachable result is never labeled as a
deployed firewall denial. Complete tables and JSON remain available when the
bounded diagram is omitted. The SVG has a viewBox for scaling, descriptive title
and description, and linked evidence. Each arrow uses a separate y coordinate;
reverse and repeated endpoint relationships remain separate rows.

## Executed static evidence

```text
PYTHONPATH=src python -m pytest tests/test_capture_independent_publication.py --basetemp=output/reviewer-c-tmp-v3 --tb=short -q
python -m ruff check tests/test_capture_independent_publication.py
```

Windows, CPython 3.14: **5 passed, 0 failed, 0 skipped (0.81 s)**; Ruff passed.
The five cases cover:

- Finding-to-evidence links at page sizes 2 and 100.
- Visible source/destination, protocol, decoded ports and exact evidence links
  for every renderable directed aggregate; unique right-facing horizontal lanes,
  SVG viewBox and accessible labeling.
- A concurrent destination created during the audit remains untouched and staging
  is removed.
- An independent audit refusal leaves no published directory or staging residue.

The original-source reproduction executes the first finding-link assertion with
the renderer loaded from
`git show 4fb9b48:src/otarchguard/capture/explorer.py`; it raises `AssertionError`
because none of the finding rows link to a flow anchor. This is separate from a
test merely reproducing the current renderer's output.

The integration owner generated and visually inspected SVG-only before/after
rasters at `output/v13-audit/visual/before.png` (850×492) and `after.png`
(1100×1300). The preserved tutorial observations/comparison are rendered with
the original `4fb9b48` diagram and corrected diagram by
`output/v13-audit/render_visual.py`, then rasterized with bundled Sharp on a white
background. The new lanes show all ten directed aggregates without shared paths,
including reverse flows, IPv6 and ARP, with source/destination, ports and codes.
Raster evidence demonstrates SVG geometry and visible labels;
it does not establish browser CSS, focus order, screen-reader behavior or zoom.

## Confirmed strengths and residual limits

The report has no JavaScript, external assets, forms or network dependencies. It
escapes imported text, uses a restrictive CSP, audits every emitted HTML link and
fragment before publication, and has semantic table headings and scroll regions.
The shared stylesheet supplies focus outlines, a skip link, text wrapping,
responsive rules and print rules. Full JSON retains exact review evidence;
display text minimizes local paths and bidi controls. These are source/static
checks, not an accessibility certification or an assurance that sharing the
sensitive report is safe.

No publication overwrite was reproduced in the supported local Windows checks.
Link/junction checks and staging reduce ordinary filesystem mistakes. They are
not an isolation boundary against a concurrently hostile filesystem. In
particular, a POSIX directory rename can replace an empty destination created
after the final existence check; parent-path replacement also needs OS-level
isolation to exclude. The report must not claim race-free publication on every
platform.

## Owner-executable browser acceptance checklist

Use a permitted local-file browser surface and the final generated fictional
comparison report. Do not introduce a server, proxy or a different browser
surface to evade a local-file restriction. Record browser/version, OS, candidate
identity, results and screenshots for failures.

1. Open `index.html` directly. Verify local CSS loads and no remote resource or
   network request is needed. Confirm the observed-traffic notice and diagram
   distinction from authorization are immediately understandable.
2. Follow each navigation link and inspect Overview, Hosts, Conversations,
   Protocols, Groups, Associations, Findings, Evidence details, Coverage and
   unobserved declared services. Confirm headings, labels and interpretation
   language remain consistent.
3. Compare diagram lanes against the corresponding conversation rows. Check
   source/destination, reverse direction, protocol, ports, counts and comparison
   codes. Open every diagram evidence link and each Findings flow link; confirm
   the correct aggregate, packet references, association decisions and original
   engine witness/diagnostic appear.
4. Use Tab/Shift+Tab and Enter without a pointer. Exercise the skip link,
   navigation, scroll regions, SVG evidence links, table links and pagination.
   Confirm visible focus and a logical order without a trap.
5. At approximately 200% browser zoom and enlarged default text, inspect the
   longest IPv6 addresses, classification codes, hashes and review rationale.
   Confirm no critical text is clipped or overlapped and horizontal scroll
   regions remain usable. Repeat with a narrow viewport.
6. Check dark text/background contrast and that direction/classification can be
   understood without color. If a screen reader is available, verify figure
   names, column headings, link labels and source/destination reading order.
7. Inspect a dense capture with more than 16 addresses or 24 aggregates. Confirm
   the explicit diagram omission and that every aggregate remains reachable in
   paginated tables and canonical JSON.
8. Verify the meaning of reachable, unreachable, pending/unmapped, unsupported,
   uncertain direction and missing observations. No page may describe missing
   traffic as blocking, or model reachability as deployed authorization or
   application success.
9. Optionally print preview the overview and a detail page. Confirm the viewBox
   scales the figure and the accessible tables remain legible.

Acceptance remains pending until the owner records actual browser findings and
the final six-platform candidate evidence is available. No manual browser PASS
is asserted here.
