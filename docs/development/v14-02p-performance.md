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

Final runtime implementation freeze:
`4cb2da9b95fab48c9077696dfcde0ecc60e8adb9`. All controlled comparisons below
bind the original installed production inventory to `bc3ff41` and the optimized
inventory to this exact production commit. A later fixture-only correction
prepares a missing idempotent-reuse prerequisite using the original producer;
it changes no runtime module. Each receipt records its exact harness commit and
tool hashes separately. Later delivery edits change documentation and measurement
receipts only; source/package audits distinguish delivery from implementation.

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

Workload names identify the base template. Mutation cases add the minimum
proposal/review prerequisites outside timing, so not every `original83` case has
exactly 83 files at its measured boundary; each case's full input manifest binds
its actual content. `review_state` measures generic inventory integrity followed
by the public pure review resolver, not complete analytical lifecycle validation.
`verify`, lifecycle listing/inspection and mutation retain their full documented
global analytical guarantee. The resolver timing must not be presented as a
replacement for full verification.
The `show_baseline_text` label denotes JSON baseline inspection through the direct
API and actual text rendering through the console; those two rows are separate
measurements, not identical presentation workloads. Fresh-write benchmarks require
`ADDED`, while reuse requires `ALREADY_PRESENT`, in API and console modes alike.

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

The pure revision axis selects 16/64/128 model-bound revisions from an identical
128-model catalog. The review-depth axis holds 64 revisions, 64 models and 64
proposals fixed while adding 16/32/64 review records. Baseline-count comparisons
include a separate zero-proposal case with that same 64-model catalog. The model
attachment axis retains identical snapshot/revision bytes and adds unreferenced
models, which remain subject to full verification. Shared-model fan-out uses
16/32/64 distinct reviewed mapping/comparison/revision branches over the same
committed fictional capture and exact model, with no approvals. Those three
branch counts co-vary and are explicitly reported as a coupled dependency
workload. The packet/metadata axis also changes observation cardinality; it does
not isolate JSON padding or claim a pure byte-size cost. Fixtures and input
manifests retain these parameters rather than labeling every workload by C alone.
Collection scaling retains one bare analytical revision per physical collection;
their total counts therefore grow together while revisions per collection stay
fixed. Pure revision scaling instead holds physical collection count at one.

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

The first complete-matrix attempt on P7, `output/v142p-acceptance/`, stopped at
the dense idempotent-reuse case after 58 completed rows. Both implementations
created the requested model-only revision because that exact revision was absent
from this template. The expected-outcome guard rejected the benchmark rather than
accepting equal successful writes as evidence of reuse. The correction prepares
that exact prerequisite with the baseline producer before binding trial inputs;
a regression checks `ALREADY_PRESENT` and unchanged artifact bytes. The incomplete
run and its interruption note are retained and excluded from final acceptance.

Method references: [Python 3.14 profiling](https://docs.python.org/3.14/library/profile.html),
[allocation tracing](https://docs.python.org/3.14/library/tracemalloc.html),
[Python 3.12 pathlib](https://docs.python.org/3.12/library/pathlib.html) and
[Python 3.14 pathlib](https://docs.python.org/3.14/library/pathlib.html).
Local measurements and implementation inspection establish the reported causes;
documentation is not a substitute for running each interpreter.

## Independent adversarial review and rejected shortcuts

Six responsibilities were covered in coordinated waves with three subagents:
profiling/acceptance, filesystem/serialization, dependency validation, review
resolution, independent cache/security challenges and final source audit. The
integration owner reviewed their interfaces and retained one source freeze.

The audit challenged same-size/mtime replacement, content changed after an
earlier successful operation, rehashed foreign dependencies, altered mappings,
scope/approval confusion, invalid unreferenced objects, caller/return-value
aliasing, cache poisoning, native replay separation and exact error precedence.
I/O cases cover bounded sentinel reads, truncation/growth, identity replacement,
duplicate keys, nonregular paths, disk-full/interrupted publication and migration
source changes. Review cases retain conflict/fork/cycle/terminal-state rejection
and lack of approval carry-forward. A fresh operation always repeats required
native validation and replay.

The final read-only auditor checked all 20 directive questions against actual
source hashes and executed focused receipts. Source/security verdict: no
unresolved finding within the documented threat model. Full installed acceptance
and performance were explicitly left pending at that review, rather than inferred
from source inspection. Its original receipt is
`output/v142p-final-independent-audit.json`; final dispositions below add executed
package and measurement evidence without rewriting that earlier observation.

Rejected designs include stat-only freshness, persistent approval/data caches,
skipping unreferenced objects or native replay, changing producer source hashes,
removing the second physical publication check and trusting caller validity flags.
The aggregate-ASCII false rejection and concrete-observer prototype bypass were
actual counterexamples, corrected and preserved with regression tests. Repeated
snapshot validation at the storage/semantic boundary remains deliberately intact:
the private image contains mutable Python values, so skipping the consumer check
solely because acquisition checked them would require a different ownership proof.

## Small independent corpus maintenance

The existing local `cisa-opcua-gap` capture has exact SHA
`030950345b2c79eaf3bedf8a04c2325cfe4a5d8b40225d250ed693daf350b6b6`,
83,524 bytes and PCAPNG magic `0a0d0d0a`. Only its erroneous `capture_type` registry
field changes from `pcap` to `pcapng`. Original bytes, source identity, licensing
and redistribution restrictions remain unchanged. Corpus integrity verification
now succeeds; 55 corpus/external-tool tests pass. Receipt:
`output/v142p-corpus-correction.json`. No new decoder support or external capture
acquisition is part of this work.

## Reproduction commands

Use regular, noneditable installations with the pinned verification dependencies.
Keep the original environment and original benchmark receipts. The harness rejects
the wrong interpreter family or source inventory, changed inputs, unexpected
success/failure, and different public or persistent results. Choose fresh output
directories; the existing acceptance directories must be preserved. The original
83-file source can be reproduced with the unchanged `benchmarks/evidence_history.py`
on the original installation; the dense fictional source comes from the unchanged
`tools/evidence_history_walkthrough.py` producers. Their identities are recorded
in the comparison receipts. Synthetic scaling fixtures use only baseline builders.

The following PowerShell commands repeat the final measurement selection:

```powershell
$perfArgs = @(
  '--baseline-python', '.venv-v142-wheel/Scripts/python.exe',
  '--optimized-python', '.venv-v142p-wheel/Scripts/python.exe',
  '--baseline-commit', 'bc3ff41df4fd7c200ec659724aa8c928f549b443',
  '--optimized-commit', '4cb2da9b95fab48c9077696dfcde0ecc60e8adb9'
)
$fixtureArgs = @(
  '--reference-workspace', 'output/v142-history-benchmark-source/history',
  '--dense-workspace', 'output/v142-installed-history-walkthrough/first/history'
)
python -m benchmarks.history_performance @perfArgs @fixtureArgs --output output/reproduce-v142p-primary --scales --modes timing console --trials 3
python -m benchmarks.history_performance @perfArgs --output output/reproduce-v142p-scaling --dense-workspace output/v142-installed-history-walkthrough/first/history --scales 0 1 16 64 128 256 --fanout-scales 16 32 64 --operations verify list_collections list_revisions --axis-operations verify review_state --modes timing --trials 3
python -m benchmarks.history_performance @perfArgs @fixtureArgs --output output/reproduce-v142p-memory --scales --modes memory --trials 3
python -m benchmarks.history_performance @perfArgs @fixtureArgs --output output/reproduce-v142p-profile --scales --operations verify --modes profile --trials 1
```

Run these stages serially, before heavy regression suites. The parent interpreter
must have the verification dependencies and a regular installed application;
workers set offline Python hooks and isolated local temporary paths themselves.
For a new machine, rebuild/install from the declared immutable revisions and
retain the new environment and power-plan receipts rather than claiming the
same hardware/cache conditions.

## Final measured results and acceptance

Controlled installed comparisons, scaling, memory and final package gates are
recorded here after execution. Until those records exist, optimization acceptance
and V14-03 readiness remain pending.
