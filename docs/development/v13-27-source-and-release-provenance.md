# V13-27 — Source, package and acceptance provenance reconciliation

Date: 2026-10-26. Status: **PASS for historical provenance reconstruction;
new UX-candidate acceptance pending**. This supplementary record supersedes stale
current-status wording without rewriting V13-14–22 or their execution outcomes.

## Verified lineage

The starting checkout was clean on `codex/v13-01-capture-foundation`, HEAD
`e763f0cb6591dee6b80b6aa846286d2b901a95ae`. Its single parent is exactly
`5c4c18da4711c36f4f5750c03009d429551d0cf0`, whose parent is
`38c1ec96d95e274e3b9ebdd30ad42a3e8cb84a9e`. No reset, rebase, cherry-pick or
history replacement was used. The new work continues this lineage.

| Identity | Verified meaning |
| --- | --- |
| `5c4c18da4711c36f4f5750c03009d429551d0cf0` | Previously hosted-validated candidate and selected historical package source |
| `e763f0cb6591dee6b80b6aa846286d2b901a95ae` | Local documentation-only child; no hosted run of its own |
| Corrected UX candidate | New renderer/test/documentation source; exact final commit and package identities belong to the new regression/manifest record |
| Final integration/release source | Not yet selected or merged; requires its own exact identity and applicable validation |
| Published stable v1.3 package bytes | None; no stable tag, GitHub Release or PyPI upload is authorized by this remediation prompt |

`git diff 5c4c18d e763f0c` changes only
`docs/development/v13-21-hosted-candidate-acceptance.md` and
`docs/development/v13-22-feature-complete-and-release-readiness.md`:
156 insertions, 129 deletions. Production, tests, tools, benchmarks, workflows,
package metadata and public inventory are byte-identical. The source trees are
different: `ce64cd4e285910ca7fbd736ec7a2df67cdba685b` and
`01d53a98f519b22c633043b11ed11a08274c5b38`, respectively.

The public-source SHA-256 identities, recomputed from the pinned Git blobs and
the 327-file manifest using sorted compact JSON of file hashes, are:

- Candidate `5c4c18d`: `d4c839fc2042e6a77b22831df08668e0317b778dc95d4a5f1c3674d202d50eb7`.
- Documentation record `e763f0c`: `a7329200fa486ed133d9f6244ba51666c52b913ba666dcdd1898acfcc7e9013b`.

Equal executable bytes do not make packages built from these two complete source
trees interchangeable as source provenance. The new rendering changes require
fresh packages and verification even though the application version stays 1.3.0.

## Hosted evidence independently rechecked

Read-only GitHub connector calls reconfirmed six completed successful jobs in
[run 40246239841](https://github.com/z4y-d3n/OT-ArchGuard/actions/runs/40246239841),
28 successful steps per job. All 12 listed integrity/benchmark artifacts bind
`head_sha` to `5c4c18d`. A read-only comparison of the remote candidate branch
with that SHA returned `identical`, zero commits ahead/behind. The direct shell
`git ls-remote` attempt failed DNS; the connector result is the remote evidence,
not an invented successful shell receipt.

| Job | Job ID | Historical result |
| --- | ---: | --- |
| Windows / Python 3.12 | 121328292552 | SUCCESS |
| Windows / Python 3.14 | 121328292445 | SUCCESS |
| Ubuntu / Python 3.12 | 121328292704 | SUCCESS |
| Ubuntu / Python 3.14 | 121328292619 | SUCCESS |
| macOS / Python 3.12 | 121328292578 | SUCCESS |
| macOS / Python 3.14 | 121328292579 | SUCCESS |

The preserved ZIPs were rehashed against the live GitHub artifact digests. All
12 matched. Each of the six integrity ZIPs was reopened independently:
`ci-revision.json` and `source-checkout.json` identify `5c4c18d` and its exact
public-source digest above. Each wheel-suite and sdist-suite XML reports **2,746
tests, zero failures/errors/skips**. These overlapping suites must not be added
together as independent tests. This is a new examination of historical receipts,
not a new execution of those suites or CI for the corrected renderer.

Raw read-only receipts and the independent recheck are preserved under
`output/v13-ux/provenance/`: `live-github-metadata.json`,
`remote-branch-comparison.json`, `review.py` and `review.json`.
The original `output/v13-hosted/acceptance-manifest.json` remains unchanged.

## Historical package selection

The selected historical local packages are under
`output/v13-hosted/fix-candidate/artifacts/`, from `5c4c18d`:

| Actual archive | Bytes | SHA-256 |
| --- | ---: | --- |
| `otarchguard-1.3.0-py3-none-any.whl` | 214153 | `6f3c789a61bda15863fa31db00d5c981d156a86f7e978f1387ca3dfdb104d030` |
| `otarchguard-1.3.0.tar.gz` | 890756 | `c7a9985f7fb92576a9711b969624c0f567d6b9d44cb84c8939c8ad23531ee828` |

The recheck matched all 60 wheel Python modules to the pinned Git source and
confirmed version metadata 1.3.0. All 327 public sdist source files match the
same pinned source bytes. Hosted archives have their own recorded hashes;
cross-host archive-byte reproducibility is not claimed.

`output/v13-final/release-manifest.json` is an earlier record for source
`38c1ec9`, with different selected archive bytes. It must not be treated as the
manifest of `5c4c18d`, `e763f0c` or the corrected UX candidate. The historical
acceptance manifest and `fix-candidate/manifest.json` distinguish this correctly.
The remediation must produce a new source/package selection and checksum record;
it must not overwrite, relabel or rename these earlier packages.

## Original human review and reproduction fixture

The owner's new prompt supplies authoritative human results. They supersede the
old record's then-current "pending review" status, while preserving that record
as an accurate account of what was known at the time:

| Criterion | Original owner result | Second review |
| --- | --- | --- |
| Immediate comprehension | PASS | PENDING |
| Communication diagram | PASS | PENDING |
| Navigation and traceability | FAIL | PENDING |
| Interpretation of analytical results | FAIL | PENDING |
| Legibility | PASS | PENDING |
| Offline operation and keyboard navigation | PASS | PENDING |

The original two FAIL results remain unresolved human-acceptance requirements
until the owner reviews the newly generated report. Link resolution, automated
rendering tests and static screenshots cannot turn them into PASS.

The attachment directory for the remediation contains only its pasted prompt;
no `demo_pcap.zip` or screenshot image was found in the accessible attachments
inventory. Those unavailable attachments were not inspected. The existing report
named in the prompt was inspected directly at
`output/v13-final/wheel-tutorial/comparison/index.html`. Its twelve-record fictional
capture SHA-256 is `0c4c4c320bda1bde2991bf3ed21980f1e61736c7ee2e07a7ca75ec390e12362d`;
the original overview HTML SHA-256 is
`7b9ff82ea251b7eeb35f1f554ad2bbbe05fd8e1b9ccd58fd24a801f3286480fa`.
Its six observed classification categories match the preserved walkthrough
expectations. The actual HTML reproduces the reported JSON-based protocol and
coverage sections, an empty limitation array, and primary rational timestamps.

An additional offline reproduction used the preserved regular installed renderer
after verifying its source bytes against `5c4c18d`. Regenerating from the original
three canonical JSON artifacts into a fresh directory produced **all 14 files
byte-identical** to the original report, including the overview hash above.
`output/v13-ux/provenance/original-render-reproduction.json` records this result;
it is static rendering evidence, not human browser acceptance.

This establishes the workspace reproduction fixture and its underlying evidence.
It does not assert byte equivalence with the unavailable ZIP or interpretation
of screenshot crops. The original report is preserved; corrected reports require
new output directories and independently recorded hashes.

## Editorial correction and next acceptance boundary

Historical V13-22 contains both the correct successful hosted result and a stale
sentence listing six-cell CI as still outstanding. The precise current statement
is: **six-platform hosted CI passed for `5c4c18d` in run `40246239841`; the subsequent
UX-remediation candidate requires its own verification before release approval**.
This record and the active README, guide and release notes provide the correction
without changing historical tags or earlier gate outcomes.

The interoperability achievement is independently produced **synthetic** coverage:
specification-authored fixtures and Wireshark `text2pcap` 4.6.7 output, compared
with offline TShark 4.6.7 receipts. No real industrial capture or downloaded public
operational corpus was tested. Origins, original Apache-2.0 fixture licensing,
integrity, privacy and future real-corpus permission requirements are documented
in the active guide. No universal producer compatibility, complete sensor
visibility, payload recognition, authenticated ownership, deployed firewall proof,
WCAG certification or comprehensive security certification follows from this corpus.

New local verification and package provenance belong to the new final regression
record. New hosted execution is NOT RUN until a separately authorized exact
candidate push. A second real human browser review remains PENDING. Merge,
tags, release publication, uploads and repository settings require their own
specific authorization. Final integration and publication identities must never
be inferred from the previous candidate's green CI or equal runtime version.
