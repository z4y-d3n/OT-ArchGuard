# V13-21 — Hosted candidate acceptance

## A. Executive status

**PASS for the tested candidate only.** Recorded 2026-10-25, America/Santiago.
[Python verification run 40246239841](https://github.com/z4y-d3n/OT-ArchGuard/actions/runs/40246239841)
completed successfully for all six configurations, attempt 1, event push. It started
2026-10-25T23:46:09Z and concluded by 2026-10-26T00:11:15Z. Raw timestamps are UTC.

The tested and published candidate is exactly
`5c4c18da4711c36f4f5750c03009d429551d0cf0`, parent
`38c1ec96d95e274e3b9ebdd30ad42a3e8cb84a9e`. Its verified public-source SHA-256 is
`d4c839fc2042e6a77b22831df08668e0317b778dc95d4a5f1c3674d202d50eb7` (327 files).
Every job and downloaded source receipt identifies that exact candidate.

Human browser acceptance remains pending in V13-17. Hosted success is not owner
approval, merge verification, a stable tag or release publication.

## B. Changes and authorization

The owner separately authorized two literal, nonforced candidate-branch pushes:
38c1ec9 and then 5c4c18d. Both succeeded. Only
`refs/heads/codex/v13-01-capture-foundation` changed. Read-only remote verification
confirmed main remains at f52c792b683cb499dc7de765b65b5cc897a96854 and all three
historical tag objects remain unchanged. No PR, merge, tag, release, package upload,
settings change, workflow dispatch or further push was performed.

The first [run 40244859860](https://github.com/z4y-d3n/OT-ArchGuard/actions/runs/40244859860)
tested 38c1ec9: Windows 3.12/3.14 passed completely, but all four POSIX cells failed
strict mypy before runtime suites. The Windows-only RSS benchmark used
`os.name == "nt"`, which did not exclude ctypes.WinDLL/WinError/get_last_error from
POSIX type analysis. The correction changes one executable line in
`benchmarks/capture.py` to `sys.platform == "win32"`; three accompanying markdown
records explained the defect and acceptance snapshot. It does not weaken mypy,
force Windows typing in POSIX jobs, alter production modules/tests/tools, change
contracts or introduce dependencies. Local full strict mypy passed win32/linux/
darwin targets, the Windows RSS helper and nine benchmark workers passed, and the
fresh corrected six-cell run now supplies actual runtime acceptance.

These final markdown updates are a separate **local documentation-only acceptance
record**, identified by the supplemental acceptance manifest. That record has no
hosted run and is not a new tested/published candidate. Its public tree/hash differs
from 5c4c18d even though executable/test/tool/benchmark bytes remain identical.
Do not attach the candidate's CI to that new documentary HEAD. The selected archives
and immutable source/CI receipts remain those built from 5c4c18d. Publishing or
integrating any later identity requires separate authorization and validation.

## C. Independent evidence

| Platform | Matrix / actual Python | Job | Wheel / sdist tests | Result |
|---|---|---|---:|---|
| Windows | 3.12 / 3.12.10 | [121328292552](https://github.com/z4y-d3n/OT-ArchGuard/actions/runs/40246239841/job/121328292552) | 2,746 / 2,746 | PASS |
| Windows | 3.14 / 3.14.9 | [121328292445](https://github.com/z4y-d3n/OT-ArchGuard/actions/runs/40246239841/job/121328292445) | 2,746 / 2,746 | PASS |
| Ubuntu | 3.12 / 3.12.15 | [121328292704](https://github.com/z4y-d3n/OT-ArchGuard/actions/runs/40246239841/job/121328292704) | 2,746 / 2,746 | PASS |
| Ubuntu | 3.14 / 3.14.8 | [121328292619](https://github.com/z4y-d3n/OT-ArchGuard/actions/runs/40246239841/job/121328292619) | 2,746 / 2,746 | PASS |
| macOS | 3.12 / 3.12.10 | [121328292578](https://github.com/z4y-d3n/OT-ArchGuard/actions/runs/40246239841/job/121328292578) | 2,746 / 2,746 | PASS |
| macOS | 3.14 / 3.14.8 | [121328292579](https://github.com/z4y-d3n/OT-ArchGuard/actions/runs/40246239841/job/121328292579) | 2,746 / 2,746 | PASS |

Each job's 28 steps succeeded. Both XML suites independently contain 2,746 cases,
zero errors, failures or skips; counts overlap and are never added across suites
or platforms. Each includes 423 capture cases, including the independent producer
corpus, 62 ARP cases, 28 consumer adversarial cases and three golden-contract cases.

All twelve integrity/benchmark ZIP artifacts were downloaded with their GitHub API
SHA-256 digests, checked before bounded extraction, and independently reopened.
Per-job package bytes, every wheel/sdist member, exact 327 public source hashes,
metadata/version/entry point, wheel RECORD evidence, both installed origins and
60 module hashes agree with the reviewed source. CLI/runtime/distribution/archive
identity is 1.3.0. The corpus/golden manifests and external TShark receipt are exact.
No downloaded runtime code was imported to inspect the artifacts.

Every cell also has independently recomputed native compatibility: 45 cases /
123 analytical artifacts (82 exact, 28 JSON and 13 HTML changes limited to the
explicit engine_version transition), plus its verified provenance manifest.
Baseline modules were checked against pinned Git archive f52c792. Both read-only
golden consumers, project/document/quality/capture/Explorer walkthroughs, denied
Python networking, deterministic output and negative publication checks passed.

Raw run/job/artifact lists, initial failure logs, download receipts, source/archive
inventories, suite XML, per-cell integrity reviews and benchmark summaries are under
`output/v13-hosted/`. Root-reviewed cells are in `run-40246239841-root/`; independent
POSIX 3.14 reviews are in `run-40246239841-review/`. The final
`acceptance-manifest.json` binds these receipts, all artifact IDs/digests, package
identities, selected local archives, tested source and local documentary record.
Original `output/v13-final/` and correction `fix-candidate/` records are preserved;
neither failed-run nor earlier local evidence substitutes for the corrected run.

## D. Quality and resources

In every cell native benchmarks completed three profiles and rejected two expected
limit workloads; quality/comparison completed three deterministic workload sizes
with identical review bytes and no broken links; capture completed eight workloads
and rejected the intended cardinality workload with resource_limit diagnostics.
RSS and traced-allocation measurements remain distinct and positive. These finite
measurements do not establish universal throughput, maximum capacity or OS memory
isolation. Unsupported traffic remains unassessed; no analytical scope was expanded.

Different hosts produce different archive container bytes. Each exact downloaded
archive has its own verified cryptographic identity and matching source; cross-host
reproducible archive-byte equivalence is not claimed. Selected local package bytes
are in `output/v13-hosted/fix-candidate/artifacts/` with their original SHA256SUMS.txt.
They were built from the tested candidate, not renamed old archives or rebuilt from
the later documentation-only HEAD. Reports and retained network/reviewer metadata
remain sensitive; hashes provide integrity, not creator authentication or signatures.

## E. Remaining risks and gaps

There is no missing hosted check for the six accepted cells. Human browser
interaction, focus, zoom, narrow layout and owner visual acceptance remain NOT RUN;
the owner explicitly replied that review is pending. A browser protocol-policy
refusal was preserved without a server/proxy/alternate-surface bypass. Finite
synthetic captures are not broad operational-capture validation or security proof.
An eventual integration/merge commit has not been created or tested and must not
inherit this candidate's acceptance automatically.

## F. Next step

Complete the V13-17 owner checklist and correct actual findings. Preserve the
functional/contract freeze in V13-18/V13-22. The owner separately controls any PR,
publication of the local documentary record, merge, tag, release, package upload
or repository setting. Verify the exact resulting integration source and required
CI before considering publication. No further remote write is authorized here.
