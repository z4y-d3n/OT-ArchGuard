# V13-29 — Hosted UX-candidate acceptance boundary

Date: 2026-10-26. Status: **NOT RUN — new specific owner push authorization
required**. The corrected renderer is a new production candidate. The previously
authorized candidate pushes do not authorize publishing this source.

## Historical and new execution are distinct

Six-platform run
[40246239841](https://github.com/z4y-d3n/OT-ArchGuard/actions/runs/40246239841)
passed for `5c4c18da4711c36f4f5750c03009d429551d0cf0`.
`e763f0cb6591dee6b80b6aa846286d2b901a95ae` is its local documentation-only child.
V13-27 independently reconciles both identities and preserved artifacts.
Neither historical evidence record accepts newly changed renderer bytes.

| Corrected-candidate configuration | Actual new hosted state |
| --- | --- |
| Windows / Python 3.12 | NOT RUN |
| Windows / Python 3.14 | NOT RUN |
| Ubuntu / Python 3.12 | NOT RUN |
| Ubuntu / Python 3.14 | NOT RUN |
| macOS / Python 3.12 | NOT RUN |
| macOS / Python 3.14 | NOT RUN |

There is no new successful run ID, tested hosted commit or hosted package selection
to report yet. Local Windows checks and historical green CI are not substitutes.

## Concrete authorization packet

Before any remote write, `output/v13-ux/owner-review.md` and the owner-facing
request must identify the final exact source commit from `source-checkout.json`,
its branch/parent, working-tree state, changed files/diff, completed local
receipts and selected package filenames/sizes/hashes. They must present the
literal proposed non-forced push to the existing candidate branch in
`https://github.com/z4y-d3n/OT-ArchGuard.git` and the expected **Python verification**
six-cell workflow. Inspect the destination ref read-only first and reconcile an
unexpected remote head without force-pushing. Do not substitute a moving branch
name for the exact reviewed commit in the approval explanation.

The authority is remediation-prompt section 14.4: **“Obtain a new specific owner
authorization before any remote write.”** Only the exact requested operation
may follow approval. No `main` modification, PR, merge, stable tag, release,
package upload, branch deletion or settings change is authorized here.

## After authorization

Inspect all six actual jobs and the exact tested revision. Verify complete wheel
and sdist suites, new UX tests, unchanged canonical evidence/consumers, native
compatibility, source and installed-module identities, archive audits, console
walkthroughs, local links and benchmark/resource artifacts. Retain raw receipts
and direct run/job links bound to the final corrected candidate. Missing checks
remain NOT RUN or BLOCKED. Fix actual failures and repeat affected verification.

Update the new acceptance receipt with real outcomes; preserve the old run and
packages. A future integration commit requires independent verification of its
actual source and required CI. Candidate success cannot automatically accept a
different merge or release source. Human browser acceptance remains a separate
requirement even if every hosted job later passes.
