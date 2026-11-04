# V15-04 — Profiling evidence

All times below are **cProfile-instrumented**, never normal user latency. Nested
cumulative rows overlap and must not be added. Initial production remained exact
merged dev2 for every profile. Regular installation/source hashes matched.

## Architecture (Agent A)

| Existing workload | Total s | Validation s | Render excluding audit s | Actual-site audit s |
|---|---:|---:|---:|---:|
| small 20/30/40/3 | 3.401 | 0.932 | 0.609 | 1.851 |
| medium 150/200/250/5 | 26.059 | 7.110 | 5.500 | 13.407 |
| larger 500/600/750/6 | 90.261 | 24.700 | 20.252 | 45.172 |

Larger reads 2,446 actual HTML files (19.819 s) and parses all of them (23.997 s).
Validation includes distinct required native/provenance/roundtrip artifact checks.
No validation or actual-byte read is dispensable merely because it costs time.

The suspected compactor is not dominant: larger `_compact` 3.882 s including
serialization/write; split 0.061 s; links 0.225 s; diagram approximately 0.005 s.
At medium: indexing 0.038 s, analytical render 0.00002 s (constructor requests no
analytical query), native declarations 0.397 s, evidence 3.994 s; pending page
calls 2,264/0.878 s, document calls 3,069/1.164 s, write 807/0.402 s. These overlap.
Final manifest/publication are retained in raw per-function attribution. No
profile supports a quadratic compaction claim or a diagram optimization.

`check_text` makes 585,785 calls and 10,377,420 Python generator iterations in
larger, 7.543 s cumulative; medium has 161,482 calls. A fixed character-class
search can perform the same rejection with less Python iteration. Profiling
amplifies generator costs: normal benefit is unknown until paired trials.
The separate BIDI loop is deferred because it also changes renderer-bound source.

Raw `output/v15-04/profiles/architecture/`: original driver, pstats, complete
function counts/self/cumulative seconds, phase-summary, fixture/site inventories,
receipts and Agent A's rejected hypotheses. Larger inventory: 2,446 HTML,
71,180 links, 12,028 anchors, 43,170,895 total bytes.

## Historical (Agent B)

Existing `prepare(scale=N, variations=False)` profiles at 1/64/512 give generation
totals 2.198/9.646/61.029 s. Scale512 controlled load 3.696 s; workspace+dependency
graph 10.347 s (acquisition 4.131, validation 6.216); replay 4.357 s (drift build
0.847 nested); render 9.827 s; publication 32.792 s. Source revision validation
occurs twice, approximately 0.022 s, not a material bottleneck.

Publication contains staged and emitted-byte audits totaling 22.837 s, parsing
214 documents = 2 × 107 pages. Four `_structure` calls take 13.711 s cumulatively,
nested across loading, replay and publication identities. Do not count those
again on top of phase totals. Reusing report structure would need a separate
validated lifetime/trust contract; removing a publication audit loses protection.
Final source freshness, complete replay and current approval checks remain.

Outputs scale1/64/512: 37/44/107 HTML; 458,372/2,321,163/15,648,051 bytes;
523/1,380/7,719 links. Workspaces unchanged. Scale512 process lifetime high-water
RSS 175,403,008 bytes includes fixture construction/profiling; it is not isolated
generation allocation. No historical latency speedup is claimed.

Raw `output/v15-04/profiles/historical/`: phase map, driver, `cpu-{1,64,512}`
pstats/full function inventories/input hashes, phase-summary and independent
review. Portable verification and source-bound replay remain separate operations.

## Capture (Agent C)

Existing parser/observation/render indexes are invocation-local and already built
once. No capture hotspot is proved; no capture runtime change is selected. Existing
`benchmarks.capture` timing includes tracemalloc and cannot supply normal latency.
Use the retained V15-03 supported/limited/dense130 driver for untraced controls;
keep navigation/identity and resource adversarial suites. Raw scope/limits and
coverage gaps: `output/v15-04/profiles/capture/agent-c-review.md`.

## Independent methodology (Agent D)

Review found and corrected a missing benchmark output-parent directory before
measurements. RSS mode now requires one case per fresh process. Symmetric
B3→A3→A3→B3 balances mean sample position and gives six trials per runtime.
Independent across-runtime inventories and immutable Unicode diagnostics are
required. Raw note: `output/v15-04/benchmarks/agent-d-review.md`.

## Independent normal historical components and final controls

Candidate producer scale512, one warmup + three untraced samples per operation:
generation17.507562s (MAD.251725), report source replay5.111295s, pure render1.603012s,
link/markup audit3.222572s, portable integrity4.583296s, full source-bundle replay
16.384226s. Components overlap; do not sum or compare these normal numbers with
cProfile totals. Workspace input inventory stayed unchanged. No historical
cross-version speedup is inferred. Raw `profiles/historical/wall-512/receipt.json`.

Capture control medians supported.234291→.219505s, limited.262319→.249705s,
dense1301.951754→1.934180s; no material-regression trigger. Independent physical
audit verifies36sites/3444files/3300HTML/123372links with exact evidence IDs and
canonical/frozen values. These controls do not establish capture speedup.

After the policy-only native provenance correction, all97 runtime hashes remain
identical to the benchmarked candidate. No source-dependent validation was removed.
See acceptance for corrected full verification and the preserved failed attempt.
