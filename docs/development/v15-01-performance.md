# V15-01 — Performance characterization

Measurements characterize the existing product; no optimization was implemented
and no speedup is claimed. The candidate keeps all production Python bytes equal
to baseline `c5ada13871043ed52cd43557bc7b222399f7b7eb`. Changes to tutorial CLI
preflight and CI do not alter benchmarked native/history/render operations.

Agent C reuses deterministic project workloads with one excluded warmup and
five untraced measured executions per operation, followed by a separate traced
allocation execution. Raw timings, medians, dispersion, fixture/output hashes,
dependency and machine details are retained in the machine-readable receipt.
Python `tracemalloc` peaks are Python allocations. OS process RSS high-water
marks are lifetime/process observations, not isolated workload allocations.
OS cache state, scheduling, thermals and unrelated machine activity are not
controlled; no industrial capacity or throughput guarantee follows.

The [committed machine-readable receipt](../../benchmarks/receipts/v15-01-windows.json)
contains all 24 PASS workloads, 120 measured timings, excluded warmups, fixture
hashes, output identities, source commit/tree, working-tree status, package
inventory and memory details. All timed outputs matched their warmup identity;
all three source workspaces remained byte-identical. There were zero workload
failures or skips. The two child-console operations have no child-memory result.

Executed November 2, 2026, 15:16:57–15:33:01 America/Santiago on Windows AMD64,
CPython 3.12.14, 12 logical processors (Intel64 Family 6 Model 141), 33,980,125,184
physical bytes and 15,235,645,440 available bytes at start. Production package
1.4.0/engine 1.3.0 was regularly installed and matched all 97 source module hashes
before and after measurement. The receipt honestly records concurrent uncommitted
tooling/documentation edits; this is a baseline of byte-identical runtime, not a
claim that the entire measured working tree was clean. Package builds and tests
were kept out of the timing window. Other OS activity remained uncontrolled.

The actual raw driver/command/hash are retained in
`output/v15-01/performance/measure.py` and its receipt. The reviewed typed driver
`benchmarks/foundation.py` preserves the workloads and adds durable per-trial
checkpoints, honest pending/error status and explicit optional allocation skips.
Repeat from the reviewed **Git checkout root**, containing this driver and its
matching source, with a regular installed runtime and Git available:

```console
python -m benchmarks.foundation --output output/v15-01-repeat
```

Choose a fresh destination. Full execution takes substantially longer than the
sum of untraced medians because fixture preparation, output hashing and separate
allocation tracing are outside the timed scopes. Do not confuse tracing latency
with normal user latency. Raw local sites/logs remain ignored under
`output/v15-01/performance/`.

The full benchmark requires checkout metadata. Archive-only replay is not
supported by this driver; do not run an extracted copy inside another repository
and attribute its ancestor's Git identity to that copy. The three historical
tutorials are separately tested from the extracted sdist. The typed driver's
Ruff/format/strict-mypy and CLI help checks passed; unknown allocation names and
`-O` were rejected with exit 2 before creating output. Its complete matrix was
not rerun after typing/checkpoint refinements; the receipt identifies the actual
original measured script, and Agent E independently reviewed correspondence.

Historical scale 1/64/512 means the existing fictional producer scale from
`tools.drift_walkthrough.prepare`, not 512 collections or an engine maximum.
Keep exact source environments for analytical replay. Baseline characterization
does not establish regression freedom on other platforms or Python versions.

## Executed baseline

Seconds are medians and median absolute deviations (MAD); allocation peaks are
MiB from a separate tracemalloc trial, not process RSS.

| Operation | Median s | MAD s | Python peak MiB |
|---|---:|---:|---:|
| native-validation-routine | 1.140491 | 0.013486 | 7.05 |
| native-trace-routine | 1.147208 | 0.000757 | 7.05 |
| architecture-explorer-small | 1.293360 | 0.028894 | 40.09 |
| architecture-explorer-medium | 10.059015 | 0.007347 | 44.22 |
| architecture-explorer-larger | 34.596008 | 0.613896 | 166.00 |
| capture-parsing-index-repeated-10k | 0.358991 | 0.003743 | 0.34 |
| bounded-industrial-mixed-700 | 0.051947 | 0.000285 | 5.12 |
| historical-lifecycle-validation-1 | 0.111761 | 0.001091 | 0.42 |
| historical-drift-1 | 0.117378 | 0.001001 | 0.82 |
| historical-source-replay-1 | 0.160266 | 0.000916 | 1.22 |
| historical-explorer-generation-1 | 1.014884 | 0.013834 | 33.44 |
| historical-portable-verification-1 | 0.304174 | 0.008302 | 32.49 |
| historical-lifecycle-validation-64 | 0.450762 | 0.005181 | 3.72 |
| historical-drift-64 | 0.478506 | 0.002907 | 5.63 |
| historical-source-replay-64 | 0.722224 | 0.003166 | 8.00 |
| historical-explorer-generation-64 | 3.138869 | 0.025580 | 39.80 |
| historical-portable-verification-64 | 0.799747 | 0.024719 | 34.27 |
| historical-lifecycle-validation-512 | 2.882279 | 0.011427 | 26.39 |
| historical-drift-512 | 3.126835 | 0.004990 | 39.90 |
| historical-source-replay-512 | 4.950312 | 0.031679 | 56.30 |
| historical-explorer-generation-512 | 17.667184 | 0.039240 | 85.56 |
| historical-portable-verification-512 | 4.393033 | 0.014356 | 47.04 |
| installed-cli-startup-version | 0.579956 | 0.009387 | unmeasured child |
| installed-cli-first-validation | 0.616941 | 0.031431 | unmeasured child |

## Candidate comparison and prioritized investigation

There is no paired before/after runtime comparison: candidate runtime and
presentation source are identical. No quantitative speedup, slowdown or 15%
regression verdict is inferred from that fact. The changed tutorial preflight
adds filesystem prerequisite checks before scenario execution; focused regressions
validate its behavior. The unchanged installed native CLI startup baseline is
about 0.58 s on this machine.

1. Profile larger Architecture Explorer generation (34.60 s vs medium 10.06 s)
   and separate graph layout, rendering, publication and link auditing. This
   measurement identifies a user-visible cost, not its proven root cause.
2. Profile historical generation/replay at producer scale 512 (17.67/4.95 s),
   including existing complete validation and serialization. Reuse source digests
   and output oracles in paired tests before considering reuse/caching.
3. Inspect CLI import startup only if onboarding evidence makes its 0.58 s
   material. Lazy imports would change source identity and need V15-02 review.

No repeated-parsing, cache, traversal or serialization hypothesis is promoted to
a proven defect without a profile. No new cache, concurrency, algorithm or
runtime dependency was introduced. Resource-rejection semantics remain covered
by the unchanged adversarial suite rather than weakened for benchmarks.
