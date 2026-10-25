# V13-17 — Local browser acceptance

## A. Executive status

**PARTIAL. Human browser acceptance NOT RUN.** Automated site/link/semantic checks
and any permitted browser tool observations are engineering evidence only. A human
reviewer must actually execute the checklist below before a manual PASS is recorded.

## B. Representative installed report

Final regular-install walkthrough output and exact local entry point:
`output/v13-final/wheel-tutorial/comparison/index.html`.
It is reproduced by the fresh 1.3.0 installed console through
`python -m tools.capture_walkthrough --output NEW_DIRECTORY`. It includes reachable
and discrepant declared initiation, unmapped endpoints, undeclared service, uncertain
TCP/UDP, ARP request/reply, IPv6, unsupported Ethernet and native evaluator details.

Unsupported content properly suppresses declared-service absence assessment.
Showing a missing-service conclusion in that same incomplete scope would be
misleading. A companion supported-only report at
`output/v13-final/absence-site/index.html` uses the frozen supported corpus to
demonstrate scoped declared-services-not-observed. Both are fictional evidence.
Raw records, codes, packet references, hashes and owner-assertion caveats remain
accessible. Dense fallback can be checked in `output/v13-final/dense-site/index.html`.

Source commit, installed module hashes, walkthrough commands and audit receipts
are retained by V13-20. These ignored local reports are not publication artifacts.

## C. Owner acceptance record

Record reviewer/date, browser/version, OS, source commit and report path. For each
item enter PASS/FAIL, and retain screenshots/notes for failures. No result below
is preapproved; current result for every human item is **NOT RUN**.

| # | Human check | Result |
|---|---|---|
| 1 | Open index.html directly; local styling works without remote requests | NOT RUN |
| 2 | Inspect Overview, addresses, conversations, groups, protocols, findings, associations, evidence, coverage and absence pages | NOT RUN |
| 3 | Follow diagram, finding, pagination and evidence links; verify exact target aggregate | NOT RUN |
| 4 | Compare every diagram count/endpoint/port with the underlying record | NOT RUN |
| 5 | ARP request/reply distinguish sender/target protocol fields and broadcast/unicast delivery; no inferred target device or response | NOT RUN |
| 6 | Read model discrepancy, uncertain direction, unsupported and scoped/suppressed absence wording | NOT RUN |
| 7 | Navigate using Tab, Shift+Tab and Enter; visible focus, logical order, no trap, working skip link | NOT RUN |
| 8 | At approximately 200% zoom retain all essential text and usable scroll regions | NOT RUN |
| 9 | Repeat at a narrow viewport, including longest IPv6/hash/reviewer strings | NOT RUN |
| 10 | Confirm essential labels are not clipped, overlapped or dependent on color | NOT RUN |
| 11 | Dense overview explicitly omits diagram while full table/JSON remain available | NOT RUN |
| 12 | Sensitive-metadata warning remains visible on every page | NOT RUN |
| 13 | Optional screen reader / print preview; record actual scope | NOT RUN |

## D. Tooling and risks

No server, proxy or browser-safety bypass is authorized. Only a permitted direct
local-file browser surface may be used. A refusal is retained as a tooling limit;
another automation surface must not be used to evade it. SVG rasterization and
structural audits cannot establish interaction acceptance. See V13-20 for actual
automated executions, and the final owner report for any permitted browser result.

## E. Next step

The owner must execute the human checklist on the final report and return the
results. Correct any actual failures, regenerate affected artifacts and repeat
affected checks. Hosted validation remains an independent owner-authorized gate.
