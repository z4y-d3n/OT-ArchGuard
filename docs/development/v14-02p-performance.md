# V14-02P performance and security acceptance

This consolidated record preserves V14-02's original measurements and documents
an additive optimization of its historical consumer. Distribution remains
1.4.0.dev1; native engine semantics remain 1.3.0. No drift or historical Explorer
functionality is introduced. Final installed-package and timing results are
recorded below after execution; a design proposal alone is not acceptance.

## Immutable reference and initial investigation

Starting checkpoint: `bc3ff41df4fd7c200ec659724aa8c928f549b443`, clean, on the
completed V14-02 branch. Tested implementation: `3724062639b63c0d37e4b29ea11eabbf25bc4f5f`.
The original branch, commits, benchmark implementation and receipts are preserved.
Optimization branch: `codex/v14-02p-history-performance-hardening`, branched from
that exact checkpoint rather than main or V14-01. Stable v1.3.0 still peels to
`10d7de6c416ec6f0ee364c671ebe9292ee69e672`.

Remote dependency refs were fetched. Draft #18 remains based on Draft #17,
with exact heads `bdf51dc54f991ab9edc1a09176b5e55b2ad0df6e` and
`3201f5d39db4c9bb4fbd565dd62fcc28145800b4`. All six V14-01 checks passed in
run 40417348042. No V14-02/V14-02P hosted result is inherited from that run;
no push, PR creation, merge, tag, workflow dispatch or publication is authorized.

Fresh pre-edit measurements used the original regular installed wheel against
the original 83-file / 721,436-byte workspace. Untraced verify trials were
6.194 / 6.260 / 5.982 s, median 6.194 s, median CPU 6.141 s. List collections
median was 3.146 s; list revisions median 2.938 s. These are fresh baseline
observations, separate from the prior checkpoint's traced and untraced receipts.
Raw initial receipt and cProfile: `output/v142p-baseline-profile/`.

Measured bottlenecks, not inferred solely from elapsed time:

| Work in one original full verification | Actual count |
|---|---:|
| Complete workspace acquisitions | 2 |
| Workspace object reads | 166, for 83 files |
| Snapshot validations | 160, for 16 snapshots |
| Attachment validations | 64, for 16 model attachments |
| Analytical revision validations | 64, for 32 analyses |
| Native model validations | 64, for 16 native models |
| Implementation inventories recomputed | 64 |
| Baseline validations / review resolutions | 18 / 3 |
| Logical file reads including implementation sources | 2,342 |
| Total bytes read including implementation sources | 20,513,144 |
| JSON parses / serializations | 838 / 105,621 |
| SHA-256 calls | 6,897 |

The count profile is heavily instrumented and does not establish end-user
latency. cProfile located native YAML parsing and oversized buffered reads as
material costs, alongside repeated defensive copies and schema/hash work.
This rejects the hypothesis that disk I/O alone explains the slowdown.

## Compatibility decision: preserve producer bytes

`evidence/attachments.py`, `evidence/revisions.py`, `evidence/workspace.py` and
`evidence/observations.py` participate in the frozen analytical semantics source
inventory. They remain byte-identical. Native parsing, enrichment, association,
comparison, policy and reachability sources also remain unchanged. No approved
analysis ID, producer manifest, snapshot, attachment, baseline or review changes.

The new optimized consumer is a separate implementation of the same checked
contract, using frozen helpers, constants and authoritative native validation.
Its complete implementation identity belongs in installed-module inventories
and execution receipts; it does not rewrite historical producer identities.
Differential tests compare exact bytes, IDs, manifests, joins, results, native
witnesses and diagnostics with the original installed distribution.

## Operation-private ownership and trust boundary

Every independent public lifecycle operation acquires a new complete workspace.
The acquisition checks every member, including unreferenced objects, and retains
parsed objects plus exact raw byte lengths and SHA-256 receipts. Raw input buffers
are released after decoding. The public state shape remains unchanged.

An internal validation context owns that acquisition for one invocation. It
validates each distinct dependency, reuses completed native model validation and
resolves reviews once for inspection. It never accepts a caller's validated flag,
file name, size, timestamp or self-reported digest as structural authority.
No persistent or module-global cache exists. Public returned dictionaries cannot
seed a later operation's validity. Standalone frozen validators still perform
their full independent checks.

Direct in-memory calls undergo a bounded values-only node/depth/type preflight
before copying. Per-object ASCII budgets remain unchanged. Aggregate estimates
for preserved snapshots use a conservative UTF-8 minimum because their accepted
raw storage may be compact/unescaped; new objects retain mandatory ASCII storage.
This does not replace the actual raw byte ceiling in acquisition/publication.
Escaped lone surrogates and canonical scalar/surrogate-pair equivalents retain
their frozen meanings; no text is normalized to make an input fit a budget.

New values are detached before they can interact with cached dependencies.
Prospective state uses copy-on-write membership maps; the acquisition still
describes the original committed files. Any failed validation poisons that
context. A failed write returns no successful approval or misleading partial
result. Cached successes never authorize another capture, observation, model,
mapping, semantics configuration or review scope.

Review and baseline builders retain the exact canonical fields. Private review
record construction is followed by complete prospective graph validation before
publication or result return. The public standalone review builder still checks
the complete graph itself. List summaries reuse the one resolved graph and a
bounded per-subject history index instead of resolving it once per baseline.
Terminal states, conflicts, predecessors, cycles and no carry-forward semantics
are unchanged. No current-baseline pointer is introduced.

## Filesystem and publication design

Reads request at most the checked open-file size plus one rejection sentinel,
subject to the unchanged maximum. They retain regular-file, inode/device, size,
mtime and same-API ctime comparisons, pre/post path checks, reparse/symlink
rejection and bounded decoding. A short or grown read fails safely. Windows
`lstat` and `fstat` ctime fields are never compared as if they had identical
semantics. Tiny inputs no longer request a 64-MiB temporary buffer.

Writes retain a second physical acquisition immediately before publication:
the complete bounded directory membership and each original member's exact
byte SHA are checked again. This is stronger than the old capacity-only reread;
it is not a stat-only freshness shortcut. It avoids repeated parsing/native
replay while preserving content freshness and exact raw-size accounting.
Atomic no-replace publication remains unchanged. Idempotent no-ops are fresh
validated reads and never overwrite existing objects.

The final path refinement is restricted to the pre/post checks inside historical
byte reads. One fresh non-following metadata record per ancestor supplies the
same link/reparse checks as the repeated original queries. There is no metadata
cache. Any observed unsafe component fails immediately; a later safe observation
cannot erase it. Reparse tags are interpreted only with the reparse attribute.
Custom Path implementations, replaced concrete-class or OS observers, unsupported
lexical paths and other filesystem errors delegate to the frozen path policy.
Observer guards compare exact function identity, including WindowsPath overrides.
Root/directory, migration and frozen publication checks retain their original
policy. Independent probes found and corrected prototype observer and unsafe-
retry counterexamples before integration. Forty-five dedicated product cases
cover these boundaries; a 292-case focused run passed on both Windows Python
versions. Existing real junctions and created file/directory/dangling symlinks
were inspected; creating a new junction was unavailable on this host. Helper-
only measurements reduced 30 metadata queries to 10 on a ten-component path,
with roughly 2.5–2.7x helper speedup. These are microbenchmarks, not end-to-end
claims. Probe receipts remain under `output/v142p-path-candidate-probe/`.

Migration still reopens and compares the source and destination bytes, preserves
original snapshots verbatim, and publishes the destination manifest last. No
physical migration integrity check was removed. Failure artifacts remain for
manual inspection, with no destructive recovery or automatic repair.

The existing local single-writer model remains. This is not OS sandboxing,
authenticated organizational authority or a privileged hostile-writer defense.

## Measurement method and reproducibility

The installed-worker harness is `benchmarks/history_performance.py` with
`tools/history_performance_worker.py`. It verifies each installed production
module against the declared Git commit before preparing fixtures; it also
records implementation identities after measured operations. Baseline builders
generate all synthetic cases. Each paired trial receives byte-identical copied
inputs, prepared outside the measured region. Original benchmark fixtures are
copied, never regenerated using optimized producer semantics.

Primary measurements use uninstrumented direct public APIs, independent operation
contexts and alternating baseline/optimized processes. Read-only timing has an
explicit warmup; mutation timing always starts from a fresh case. Console
measurements include cold process startup. Profiling and tracemalloc run in
separate modes and never supply primary speedup claims. Fresh-process RSS
includes interpreter/import cost; it is distinct from traced operation allocation.

Every comparison checks public outcomes, structured errors/exit codes and exact
persistent artifact byte manifests before accepting its timing samples. Raw
trials, medians, min/max, spread and median absolute deviation are retained.
An attractive timing with a differential mismatch is an automatic failure.

Host: Windows 11 AMD64, Intel Core i5-11400H @ 2.70 GHz. The pre-existing active
power plan was Maximum performance (`2d4d6631-5ed2-452e-9c1a-4df6b43ced8a`).
Primary before/after comparisons use the same Python 3.14.5 interpreter family
and pinned verification dependencies. Dedicated Windows Python 3.12.14 testing
uses the bundled runtime in an isolated regular environment. OS cache, antivirus
and scheduling noise are not forcibly controlled; raw spread is disclosed.
Heavy regression jobs do not run concurrently with final timing comparisons.

Independent collection, revision, review-depth, baseline-count, unreferenced-model
and metadata-size axes are generated by baseline code. Review depth varies with
both revision and baseline counts held fixed; baseline count varies at fixed
revision count; unreferenced model count does not add analytical revisions.
Case parameters and all input byte identities are retained. No linear-complexity
claim is inferred from a workload that changes more than one axis.

One experimental aggregate preflight was rejected during independent audit:
ASCII-escaped estimates could overcharge valid compact UTF-8 snapshots. A real
21,881-byte accepted workspace reproduced the issue. The first comparison run
was intentionally stopped after eight paired rows; its incomplete data remains
under `output/v142p-primary/` with an interruption note and is not acceptance.
The conservative UTF-8 floor correction and four independent boundary proofs
passed on Windows Python 3.12.14 and 3.14.5 before restarting final comparisons.

A second incomplete comparison, `output/v142p-primary-final/`, was stopped after
28 paired rows to integrate the independently reviewed path refinement. Its
raw trials and interruption note remain available; it is also excluded from final
acceptance. Final comparisons use one frozen implementation for every row.

Method references: [Python 3.14 profiling](https://docs.python.org/3.14/library/profile.html),
[allocation tracing](https://docs.python.org/3.14/library/tracemalloc.html),
[Python 3.12 pathlib](https://docs.python.org/3.12/library/pathlib.html) and
[Python 3.14 pathlib](https://docs.python.org/3.14/library/pathlib.html).
Local measurements and implementation inspection establish the reported causes;
documentation is not a substitute for running each interpreter.

## Small independent corpus maintenance

The existing local `cisa-opcua-gap` capture has exact SHA
`030950345b2c79eaf3bedf8a04c2325cfe4a5d8b40225d250ed693daf350b6b6`,
83,524 bytes and PCAPNG magic `0a0d0d0a`. Only its erroneous `capture_type` registry
field changes from `pcap` to `pcapng`. Original bytes, source identity, licensing
and redistribution restrictions remain unchanged. Corpus integrity verification
now succeeds; 55 corpus/external-tool tests pass. Receipt:
`output/v142p-corpus-correction.json`. No new decoder support or external capture
acquisition is part of this work.

## Final measured results and acceptance

Controlled installed comparisons, scaling, memory and final package gates are
recorded here after execution. Until those records exist, optimization acceptance
and V14-03 readiness remain pending.
