# Gate V11-4 — evidence-driven performance engineering

## 1. Executive engineering summary and local status

Local engineering and verification are complete for owner review. One narrow
optimization removes the second complete input-validation pass from native
check/exposure/comparison report workflows. Analytical algorithms, actual work,
reservations, canonical identities and existing output contracts are preserved.
FE-09 adds reproducible attribution; FE-10 removes redundant validation; FE-11
reuses bounded immutable inputs; FE-12 characterizes finite capacity and adds
deterministic regression safeguards. Hosted V11-4 CI and owner acceptance remain
pending separate authorization. No later gate is begun.

Second-session native check/JSON medians (Windows only):

| Python | Case | Before s | After s | Reduction |
| --- | --- | --- | --- | --- |
| 312 | routine | 2.815 | 1.672 | 40.6% |
| 312 | dense-policy | 15.396 | 7.778 | 49.5% |
| 314 | routine | 2.909 | 1.796 | 38.3% |
| 314 | dense-policy | 14.833 | 8.074 | 45.6% |

Both final installed suites pass 1,216 tests; 197 compatibility artifacts per interpreter are byte-identical.

## 2. Initial repository state, accepted baseline and immutable identities

The checkout was clean on main, tracking origin/main, at
`46cca6487e67341ff79a3c2844dede6dd2e5fd21`. A successful
`git fetch origin main --no-tags` confirmed zero commits ahead/behind. This merge
includes accepted V11-3 commit `ba2c591`; historical main `659a2d4` is not the
V11-4 baseline. Newly created development branch: `codex/gate-v11-4`.

The sole root remains `8e6a5bca41a00eb0454e6efdd9a9558e1a7017b2`.
Annotated v1.0.1 tag object `39c855ad6204953495fdca4a7058fd53a3ba8f8c`
still dereferences to that root. Git fsck found only an existing dangling tree,
not corruption. EXPECTED_ROOT_SHA was not changed; the workflow reference is
byte-preserved, and the remote variable was not independently queried.

Application/project version 1.0.1, schema 1, report/trace contract 1, Apache-2.0
and the published stable release remain unchanged. No stable archive was rebuilt
or overwritten. No files are staged; no commit, push, merge, tag or publication
occurred.

## 3. Frozen semantics and source inspection

Administrative owning zones and interface placement remain distinct. Every
transport/forwarding transition remains explicit and directed. No implicit relay,
routing, subnet connectivity, reverse connectivity or boundary forwarding is
introduced. Unordered rules retain original-endpoint selectors, edge associations,
default deny, deny precedence and exact TCP/UDP destination-port intervals.

Only cli.py changes in production. The domain, loading, parsing, validation,
normalization, graph, policy, intervals, reachability, intents, exposure, comparison,
flows, policy evidence, summaries, report renderers, diagrams, contracts and
diagnostics retain accepted source bytes. Inspection covered their actual calls,
existing tests/oracles, examples, benchmarks, verification tools, manifests,
packaging and workflow. The ignored baseline inventory records source hashes and
definitions across all source/test/tool modules. No private historical technical
reference or backup implementation was accessed.

## 4. Native call graph and frequency of work

All input paths use the bounded reader, strict YAML preflight/scans/replay, typed
parsing, reference/structure validation, normalization, canonical JSON and SHA-256.
YAML safety passes and independent public API validation are necessary trust
boundaries. They were not weakened.


| Command | Analytical work | Presentation |
| --- | --- | --- |
| validate | One validated snapshot; no search | Optional structural report/SVG |
| check | One engine for requested intent services; quantified queries | JSON stdout; optional bound report |
| exposure | One engine/budget for scenario plus independent intents | Flows, destination aggregation, optional finite summary/report |
| compare | Two validated snapshots; one peer-partitioned engine per side | Comparable flow, inventory, definition and intent deltas; two-snapshot report |
| trace | One selected query; optional complete finite policy evidence | Version-1 JSON and optional offline HTML |


Per engine: service lookup, exact atoms, graph, compiled endpoint selectors and
sparse rule-edge associations. Per source/service query: atom reservations and
evaluation. Per atom: deterministic BFS, atom-local edge decisions, selected witness
construction/replay or failed permitted/structural searches and bounded frontier.
Optional evidence independently checks every declared edge/selected atom, including
off-witness edges. Independent intent work/reservations are retained even where a
scenario selects the same pair. Reports bind hashes, serialize escaped evidence,
prepare deterministic geometry and atomically write a sibling temporary file.

## 5. Profiling methodology, modes and limitations

The public opt-in benchmarks.profile harness uses perf_counter_ns, process_time_ns,
cProfile/pstats, tracemalloc, GC, statistics, platform and sys. One warm-up precedes
five measured untraced samples. Tiny read/hash operations use batches of 20;
other operations preserve fresh engine lifetimes. GC is outside each timed batch.
Medians, MAD, ranges and all samples are retained. Separate single-operation
tracemalloc observations are Python allocations, not process RSS.

Full attribution measures actual pipeline functions with prepared inputs. Inclusive
phases overlap and must not be summed. Rule compilation includes selector expansion
and association preparation. Canonical serialization retains its public normalization
boundary. cProfile records search, witness/replay, frontier, policy evidence and
aggregation self/cumulative costs; these instrumented costs also overlap.

Native launcher wall timing includes startup/imports, input, analysis, selected
report generation/writing, captured output and exit. Native child CPU/allocation
are explicitly unavailable, not substituted with parent CPU. Separate in-process
complete check/JSON-report runs include input and writing but exclude interpreter
and import startup; their CPU and allocation labels remain distinct.

Confirmation repeats selected native report operations and prevalidated analytical
controls with the same per-operation sampling method, omitting repeated attribution
of unchanged parsing/rendering code. Missing phases are unmeasured, not zero.
The second baseline/candidate session restores verified regular baseline wheels,
then candidate wheels, and repeats routine/sparse/mixed/dense-policy confirmation
on both interpreters. Suites/builds never run concurrently with timing comparisons.

No CPU affinity, governor, background OS load or process RSS was controlled/measured.
Windows CPU timer quantization produces some zero short samples. Submillisecond
differences and small changes within variation are inconclusive. Results are local
Windows observations, not Linux/macOS or universal latency/scalability guarantees.
See [reproduction methodology](../benchmarks/performance.md).

## 6. Fresh baseline verification and environment

Both accepted non-editable installations were verified before optimization:
CPython 3.12.14 and 3.14.5, Windows AMD64, Intel Core i5-11400H @ 2.70 GHz,
12 logical CPUs. Python 3.12 uses the available bundled base runtime; 3.14 uses
the locally installed base runtime. Actual site-packages imports, console launchers,
distribution metadata and every production-module hash matched accepted source.
Distribution was 1.0.1.dev3+gate.v11.3; application version was 1.0.1.

Fresh accepted suites: **1,197 passed** on 3.12 in **306.02 s**, and **1,197 passed**
on 3.14 in **328.81 s**. Baseline lint/format, strict typing, pip check, installed
walkthroughs and compatibility capture passed. All 197 captured artifacts were
byte-identical across interpreters. Historical V11-3 timings were not substituted
for these new measurements.

## 7. Complete before-change workload dimensions and work

The table describes the prevalidated selected trace (one source/service pair);
query atoms are interval records, not individual ports. Additional optional policy
work is shown separately. Dimensions and work agree across interpreters.


| Case | Assets | Ifaces | Edges | Rules | Assoc. | Services | Atoms | Query visits | Query checks | Policy rows | Policy checks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| minimal | 2 | 2 | 1 | 1 | 1 | 1 | 1 | 4 | 1 | 1 | 1 |
| mixed | 3 | 3 | 1 | 3 | 3 | 4 | 1 | 5 | 3 | 1 | 3 |
| tcp-udp | 2 | 2 | 1 | 2 | 2 | 2 | 1 | 4 | 2 | 1 | 2 |
| comparison | 3 | 3 | 3 | 1 | 3 | 2 | 1 | 5 | 2 | 3 | 3 |
| boundary | 5 | 7 | 8 | 5 | 12 | 4 | 1 | 9 | 2 | 8 | 12 |
| blocked | 2 | 2 | 1 | 0 | 0 | 1 | 1 | 5 | 0 | 1 | 0 |
| absent | 2 | 2 | 0 | 0 | 0 | 1 | 1 | 2 | 0 | 0 | 0 |
| routine | 200 | 400 | 1200 | 200 | 1200 | 25 | 1 | 52 | 38 | 1200 | 1200 |
| sparse | 200 | 400 | 240 | 200 | 240 | 25 | 1 | 38 | 29 | 240 | 240 |
| deny-heavy | 200 | 400 | 1200 | 200 | 1200 | 25 | 1 | 98 | 35 | 1200 | 1200 |
| dense-policy | 200 | 400 | 1200 | 200 | 120000 | 25 | 1 | 59 | 400 | 1200 | 120000 |
| interval-heavy | 200 | 400 | 1200 | 200 | 1200 | 25 | 426 | 25139 | 2131 | 511200 | 511200 |
| mixed-intervals | 3 | 3 | 1 | 3 | 3 | 4 | 6 | 27 | 18 | 6 | 18 |


The corpus covers explicit boundary devices, multiple sources/listeners, TCP/UDP,
multi-hop forwarding, mixed reachable/blocked intervals, structural absence,
allow/deny overlap and duplicate scoped effects. The observed-difference comparison
uses the existing flat-plant baseline/proposal (two lost intervals), not identity
comparison alone. Routine scenario scope is 10 origins × 25 services plus its
independent intent checks. Input/model SHA-256 identities, effective ceilings and
raw synthetic inputs are retained locally. Dense and interval-heavy full-scope
exposure/comparison retain controlled prospective rejection.

Final report review identified that the original `mixed` fixture profile selected
its first sorted service (`svc_absent`), not its mixed-port listener. Those valid
structural-absence observations are retained. A separately recorded supplement,
`mixed-intervals`, explicitly selects `eng` → `svc_plc`: six atoms, 27 query visits,
18 query predicates and six/18 additional policy rows/predicates. Accepted wheels
were restored and checked before its baseline timing on both interpreters, then
candidate wheels were restored for the same comparison. Its complete policy trace
fingerprint equals the pre-change 197-artifact corpus/hash-seed trace. Thus the
supplement has pre-change semantic evidence and fresh explicit baseline/candidate
timing; it is not mislabeled as part of the earlier measurement session.

## 8. Per-phase cost attribution and ranked candidates

Fresh Python 3.12 routine phase medians (seconds; inclusive phases overlap):


| Measured phase | Median wall s | Wall MAD s | Peak Python MiB |
| --- | --- | --- | --- |
| input_read | 0.000130 | 0.000008 | 0.215 |
| yaml_parse | 1.054593 | 0.011741 | 1.862 |
| typed_parse | 0.016345 | 0.000340 | 1.499 |
| structure_validation | 0.008279 | 0.000195 | 0.138 |
| normalization | 0.017940 | 0.000144 | 2.627 |
| canonical_serialization | 0.022364 | 0.000145 | 2.627 |
| sha256 | 0.000126 | 0.000003 | 0.000 |
| graph | 0.003642 | 0.000043 | 0.439 |
| policy_compile_including_associations | 0.005560 | 0.000004 | 3.474 |
| partition | 0.000163 | 0.000014 | 0.007 |
| engine_prepare | 0.010495 | 0.000885 | 3.800 |
| trace_plain | 0.010986 | 0.000238 | 3.809 |
| trace_policy | 0.012661 | 0.000137 | 3.818 |
| exposure_prevalidated | 0.057871 | 0.000963 | 4.204 |
| comparison_prevalidated | 0.133517 | 0.004682 | 4.671 |
| report_json | 0.011178 | 0.000112 | 2.371 |
| report_html | 0.090755 | 0.000317 | 6.422 |
| report_svg | 0.001206 | 0.000043 | 0.148 |
| report_write | 0.002784 | 0.000009 | 0.012 |


Supplemental aggregation measurements below use completed results and the final
candidate's **byte-identical analytical modules**, after full-suite timing work.
They distinguish helper costs from whole-API engine/query time; they are not
before/after optimization comparisons. Helpers use one warm-up, five batches of
20 calls and a separate single-call allocation observation. Full API cProfile
records separately attribute exposure/flow merging, comparison catalogs/fields,
intent comparison and interval differences. Public profiling helpers and a
reproduction example are documented in the methodology.


| Python | Case | Aggregation helper | Wall s | CPU s | Peak Python MiB |
| --- | --- | --- | --- | --- | --- |
| 312 | routine | flow_observations | 0.001493 | 0.001563 | 0.220 |
| 312 | routine | flow_difference_gained | 0.002733 | 0.003125 | 0.265 |
| 312 | routine | flow_difference_lost | 0.002688 | 0.002344 | 0.265 |
| 312 | routine | completed_exposure_summary | 0.002527 | 0.002344 | 0.279 |
| 312 | routine | completed_comparison_explanation | 0.000025 | 0.000000 | 0.024 |
| 312 | comparison | flow_observations | 0.000023 | 0.000000 | 0.006 |
| 312 | comparison | flow_difference_gained | 0.000026 | 0.000000 | 0.005 |
| 312 | comparison | flow_difference_lost | 0.000027 | 0.000000 | 0.006 |
| 312 | comparison | completed_exposure_summary | 0.000043 | 0.000000 | 0.007 |
| 312 | comparison | completed_comparison_explanation | 0.000007 | 0.000000 | 0.002 |
| 314 | routine | flow_observations | 0.001470 | 0.001563 | 0.229 |
| 314 | routine | flow_difference_gained | 0.002816 | 0.002344 | 0.276 |
| 314 | routine | flow_difference_lost | 0.002741 | 0.003125 | 0.276 |
| 314 | routine | completed_exposure_summary | 0.002446 | 0.002344 | 0.292 |
| 314 | routine | completed_comparison_explanation | 0.000027 | 0.000000 | 0.026 |
| 314 | comparison | flow_observations | 0.000024 | 0.000000 | 0.006 |
| 314 | comparison | flow_difference_gained | 0.000026 | 0.000000 | 0.006 |
| 314 | comparison | flow_difference_lost | 0.000031 | 0.000000 | 0.006 |
| 314 | comparison | completed_exposure_summary | 0.000045 | 0.000000 | 0.007 |
| 314 | comparison | completed_comparison_explanation | 0.000007 | 0.000000 | 0.002 |


Supplemental routine comparison cProfile on Python 3.12 (instrumented, overlapping costs):


| Module | Function | Calls | Self s | Cumulative s |
| --- | --- | --- | --- | --- |
| exposure.py | evaluate_scope | 2 | 0.000354 | 0.325799 |
| flows.py | observations | 4 | 0.000144 | 0.008683 |
| flows.py | merge | 16 | 0.001895 | 0.018994 |
| comparison.py | _catalogs | 2 | 0.002269 | 0.008296 |
| comparison.py | _fields | 2029 | 0.006564 | 0.015449 |
| comparison.py | _intent_comparisons | 1 | 0.000020 | 0.000141 |
| flows.py | difference | 6 | 0.000572 | 0.012084 |


Instrumented routine check/HTML attribution confirms two validate_file/load_bytes
calls, four normalization calls, and one analytical graph/policy preparation.
After snapshot reuse, report check performs one validation and two normalizations;
the accepted normalizer/canonicalizer boundary remains unchanged. Comparison keeps
two independent validations instead of four. Mandatory graph/query/evidence work
is not removed. Raw cProfile records separate search, witness, replay and frontier
functions; no nonexistent pipeline phase is invented.

Ranked candidates: (1) repeated native report validation; (2) duplicate normalization
inside validated identity preparation; (3) policy-evidence overhead; (4) repeated
report conversions; (5) SVG preparation. The first candidate dominates avoidable
native report cost: routine validation is about 1.10 s; dense validation about
7.70 s, whereas their native check/JSON baselines are about 2.80 s and 15.60 s.

Only candidate 1 is accepted. A normalization-only fast path is deferred: routine
normalization is about 0.018 s within roughly 1.10 s validation, and a new internal
canonicalization precondition has limited end-to-end value here. Policy decision
memoization, cross-query reuse and reservation changes could alter public actual
work or analytical meaning; they require separate compatibility/semantic review.
Existing preparation is already run-local. No broad algorithm rewrite, new pruning,
parallel search, report redesign or SVG change is attempted.

## 9. Actual modification and snapshot lifetime

Report-enabled check/exposure validate once and call their existing architecture
APIs; comparison validates both paths once and calls compare_architectures. The
private report helper receives those completed immutable snapshots. It retains
kind/arity/hash checks, zone-order validation, escaping and atomic write guards.
The original file APIs and paths without reports retain their accepted flow;
validate and trace already reused their snapshots.

Lifetime is exactly one command invocation, bounded to one or two validated inputs.
There is no global, filename, timestamp, persistent disk or query-result cache.
No invalidation protocol or cache hit/miss field is added. Every independent input
boundary still validates. If an input changes after evaluation, the report remains
bound to the evaluated bytes rather than rereading a different declaration.
Comparisons preserve distinct baseline/proposal identities.

## 10. Before/after native report and analytical controls

First-session medians in seconds. Reduction is (before-after)/before. Native check
includes a JSON report and process startup. Trace columns use prevalidated inputs,
fresh engines and no process startup. Unchanged analytical code means small control
timing differences are observations, not attributed optimization benefits.



### Python 3.12


| Case | Native before | Native after | Absolute saving | Reduction | Plain trace before/after | Policy trace before/after |
| --- | --- | --- | --- | --- | --- | --- |
| minimal | 0.605351 | 0.587988 | 0.017363 | 2.9% | 0.000201 / 0.000182 | 0.000223 / 0.000214 |
| mixed | 0.623986 | 0.619170 | 0.004816 | 0.8% | 0.000220 / 0.000212 | 0.000238 / 0.000248 |
| tcp-udp | 0.606027 | 0.590155 | 0.015871 | 2.6% | 0.000210 / 0.000257 | 0.000223 / 0.000213 |
| comparison | 0.630396 | 0.600618 | 0.029779 | 4.7% | 0.000210 / 0.000194 | 0.000239 / 0.000252 |
| boundary | 0.676909 | 0.621888 | 0.055021 | 8.1% | 0.000274 / 0.000269 | 0.000294 / 0.000281 |
| blocked | 0.605992 | 0.591981 | 0.014011 | 2.3% | 0.000159 / 0.000155 | 0.000188 / 0.000242 |
| absent | 0.598080 | 0.605007 | -0.006926 | -1.2% | 0.000143 / 0.000186 | 0.000177 / 0.000181 |
| routine | 2.797033 | 1.768711 | 1.028322 | 36.8% | 0.010986 / 0.011038 | 0.012661 / 0.012818 |
| sparse | 2.107699 | 1.340453 | 0.767246 | 36.4% | 0.007917 / 0.008861 | 0.009088 / 0.008327 |
| deny-heavy | 2.921269 | 1.762654 | 1.158615 | 39.7% | 0.012616 / 0.011973 | 0.013772 / 0.013117 |
| dense-policy | 15.598894 | 8.133095 | 7.465799 | 47.9% | 0.017277 / 0.018879 | 0.069937 / 0.068875 |
| interval-heavy | 3.455022 | 2.232163 | 1.222859 | 35.4% | 0.030024 / 0.030668 | 0.603924 / 0.586181 |
| mixed-intervals | 0.599665 | 0.643851 | -0.044186 | -7.4% | 0.000398 / 0.000328 | 0.000380 / 0.000391 |


### Python 3.14


| Case | Native before | Native after | Absolute saving | Reduction | Plain trace before/after | Policy trace before/after |
| --- | --- | --- | --- | --- | --- | --- |
| minimal | 0.672139 | 0.824691 | -0.152552 | -22.7% | 0.000223 / 0.000245 | 0.000294 / 0.000244 |
| mixed | 0.748896 | 0.809308 | -0.060413 | -8.1% | 0.000281 / 0.000221 | 0.000256 / 0.000247 |
| tcp-udp | 0.654465 | 0.613353 | 0.041112 | 6.3% | 0.000216 / 0.000216 | 0.000264 / 0.000247 |
| comparison | 0.640848 | 0.725151 | -0.084303 | -13.2% | 0.000202 / 0.000214 | 0.000255 / 0.000251 |
| boundary | 0.697880 | 0.737195 | -0.039315 | -5.6% | 0.000257 / 0.000366 | 0.000289 / 0.000320 |
| blocked | 0.696095 | 0.662970 | 0.033125 | 4.8% | 0.000184 / 0.000184 | 0.000209 / 0.000177 |
| absent | 0.577332 | 0.668286 | -0.090954 | -15.8% | 0.000159 / 0.000146 | 0.000164 / 0.000193 |
| routine | 2.939598 | 1.800425 | 1.139173 | 38.8% | 0.010668 / 0.010572 | 0.012365 / 0.013202 |
| sparse | 2.165260 | 1.403574 | 0.761686 | 35.2% | 0.007968 / 0.007941 | 0.008820 / 0.009275 |
| deny-heavy | 2.689179 | 1.796063 | 0.893116 | 33.2% | 0.009748 / 0.011436 | 0.011645 / 0.013142 |
| dense-policy | 15.678926 | 8.042889 | 7.636037 | 48.7% | 0.020751 / 0.020946 | 0.073297 / 0.071773 |
| interval-heavy | 3.342027 | 2.276768 | 1.065260 | 31.9% | 0.031083 / 0.032081 | 0.595670 / 0.611780 |
| mixed-intervals | 0.647660 | 0.653996 | -0.006336 | -1.0% | 0.000326 / 0.000372 | 0.000360 / 0.000399 |


## 11. Second-session confirmation and variability

Each cell is median wall seconds ± median absolute deviation. Fresh baseline
wheel restoration was checked against the initial accepted module hashes before
this session. Candidate provenance was checked again after restoration.


| Python | Case | Native operation | Before median ± MAD | After median ± MAD | Reduction |
| --- | --- | --- | --- | --- | --- |
| 312 | routine | check_json | 2.814656 ± 0.020706 | 1.672337 ± 0.058704 | 40.6% |
| 312 | routine | exposure_html | 3.225648 ± 0.014675 | 1.985383 ± 0.027435 | 38.5% |
| 312 | routine | compare_json | 5.235344 ± 0.008497 | 3.022324 ± 0.023385 | 42.3% |
| 312 | sparse | check_json | 2.034153 ± 0.003107 | 1.290876 ± 0.030133 | 36.5% |
| 312 | mixed | check_json | 0.607814 ± 0.005882 | 0.505118 ± 0.005062 | 16.9% |
| 312 | dense-policy | check_json | 15.396055 ± 0.087020 | 7.778486 ± 0.131639 | 49.5% |
| 314 | routine | check_json | 2.909307 ± 0.022736 | 1.796066 ± 0.031841 | 38.3% |
| 314 | routine | exposure_html | 3.041259 ± 0.022851 | 2.136425 ± 0.009933 | 29.8% |
| 314 | routine | compare_json | 5.016999 ± 0.067739 | 3.094618 ± 0.010790 | 38.3% |
| 314 | sparse | check_json | 2.171782 ± 0.032581 | 1.411549 ± 0.025883 | 35.0% |
| 314 | mixed | check_json | 0.705169 ± 0.012098 | 0.669916 ± 0.006824 | 5.0% |
| 314 | dense-policy | check_json | 14.832775 ± 0.139552 | 8.074492 ± 0.042071 | 45.6% |


Native routine controls (seconds; no optimization benefit is claimed):


| Python | Control | Session 1 baseline | Session 1 candidate | Session 2 baseline | Session 2 candidate |
| --- | --- | --- | --- | --- | --- |
| 312 | startup | 0.522657 ± 0.009363 | 0.583035 ± 0.006287 | 0.531792 ± 0.015321 | 0.597721 ± 0.016401 |
| 312 | validate | 1.617923 ± 0.016303 | 1.739079 ± 0.022226 | 1.697765 ± 0.049331 | 1.671607 ± 0.052718 |
| 312 | trace_plain | 1.700437 ± 0.043346 | 1.703719 ± 0.016286 | 1.676950 ± 0.012481 | 1.639136 ± 0.034373 |
| 312 | trace_policy | 1.608181 ± 0.022047 | 1.755833 ± 0.104567 | 1.738916 ± 0.058289 | 1.587923 ± 0.011468 |
| 314 | startup | 0.670126 ± 0.018473 | 0.691239 ± 0.016599 | 0.662019 ± 0.014830 | 0.651323 ± 0.009798 |
| 314 | validate | 1.759162 ± 0.006614 | 1.790658 ± 0.055598 | 1.763167 ± 0.007665 | 1.774745 ± 0.017885 |
| 314 | trace_plain | 1.775477 ± 0.016739 | 1.836268 ± 0.012422 | 1.795618 ± 0.015606 | 1.770108 ± 0.030177 |
| 314 | trace_policy | 1.808417 ± 0.007909 | 1.760289 ± 0.006375 | 1.778980 ± 0.054769 | 1.769471 ± 0.015666 |


Grouped routine startup observations showed an apparent roughly 60-ms candidate
increase on 3.12, so an additional isolated probe alternated candidate/baseline/
candidate/baseline/candidate regular installations on each interpreter. Every
block verified selected production hashes, warmed once and recorded nine native
--version samples. No suites/builds ran concurrently. Adjacent restored-baseline
to following-candidate pairs are shown below; the original increase did not
reproduce. This supports measurement-sequence/system variability as an inference,
not a proven diagnosis of its underlying OS cause. No repeatable material startup
regression was established. Import-time traces confirmed identical imported-module
sets, with no new startup dependency. All grouped observations are retained above.


| Python | Alternating blocks | Baseline median ± MAD | Candidate median ± MAD | Candidate change |
| --- | --- | --- | --- | --- |
| 312 | 1 → 2 | 0.577563 ± 0.010135 | 0.577825 ± 0.014932 | +0.05% |
| 312 | 3 → 4 | 0.568166 ± 0.013888 | 0.566530 ± 0.009100 | -0.29% |
| 314 | 1 → 2 | 0.665921 ± 0.027941 | 0.648938 ± 0.014964 | -2.55% |
| 314 | 3 → 4 | 0.653922 ± 0.007966 | 0.650335 ± 0.018562 | -0.55% |


The first-session 3.14 minimal check/JSON result also appeared 22.7% slower
(0.672139 → 0.824691 s). A separate alternating-installation probe repeated that
exact native minimal check/report workload with nine samples after one warm-up.
Baseline→candidate pairs were 0.693151→0.658487 s and 0.688135→0.677624 s.
The first-session slowdown did not reproduce; no tiny-workload speedup is claimed.
Together with preserved startup/validate/trace controls, this rules out treating
one grouped block as evidence of a persistent regression. Underlying OS/session
variation remains an inference, not a diagnosed mechanism.



Startup, unreported traces, prevalidated analysis and the fixed API benchmark are
controls, not claimed speedups. Removing a validated reread principally improves
report-enabled commands. No universal runtime guarantee or causal claim about
minor unchanged-phase variation is made. Machine-local records retain all ranges,
CPU samples and maxima for independent review.

## 12. Allocation observations

Separate complete in-process check/JSON-report workflow measurements (not native
process RSS; startup/imports excluded). Each run includes input and atomic writing.


| Python | Case | Wall before | Wall after | CPU before/after | Peak MiB before | Peak MiB after |
| --- | --- | --- | --- | --- | --- | --- |
| 312 | routine | 2.230033 | 1.152709 | 2.234375 / 1.156250 | 7.601 | 7.096 |
| 312 | sparse | 1.389281 | 0.764140 | 1.390625 / 0.765625 | 5.514 | 5.061 |
| 312 | mixed | 0.035976 | 0.022261 | 0.031250 / 0.015625 | 5.081 | 5.061 |
| 314 | routine | 2.217408 | 1.124635 | 2.203125 / 1.125000 | 7.721 | 7.295 |
| 314 | sparse | 1.438097 | 0.736552 | 1.437500 / 0.718750 | 5.569 | 5.176 |
| 314 | mixed | 0.038393 | 0.023686 | 0.046875 / 0.031250 | 5.201 | 5.176 |


Separate prevalidated policy-on trace allocation peaks (MiB):


| Case | 3.12 before/after | 3.14 before/after |
| --- | --- | --- |
| minimal | 0.010 / 0.010 | 0.010 / 0.010 |
| mixed | 0.012 / 0.012 | 0.012 / 0.012 |
| tcp-udp | 0.011 / 0.011 | 0.010 / 0.010 |
| comparison | 0.011 / 0.011 | 0.011 / 0.011 |
| boundary | 0.017 / 0.017 | 0.017 / 0.017 |
| blocked | 0.008 / 0.008 | 0.009 / 0.009 |
| absent | 0.008 / 0.008 | 0.008 / 0.008 |
| routine | 3.818 / 3.818 | 3.843 / 3.843 |
| sparse | 3.555 / 3.555 | 3.571 / 3.571 |
| deny-heavy | 3.820 / 3.820 | 3.845 / 3.845 |
| dense-policy | 5.663 / 5.663 | 5.686 / 5.686 |
| interval-heavy | 4.314 / 4.314 | 4.356 / 4.356 |
| mixed-intervals | 0.018 / 0.018 | 0.018 / 0.018 |


These observations establish no whole-process memory maximum. Native child memory
is unmeasured. No unbounded retained collection is introduced; the only new retained
references are the invocation's one/two already validated snapshots. Large bounded
reports and complete policy evidence can still allocate substantially.

## 13. Exact compatibility and independent oracle evidence

All **197 accepted artifacts** are byte-identical on each final interpreter and
across the final interpreters: canonical JSON/hashes, legacy JSON/HTML, SVG,
native stdout/stderr/exits, current native report summaries, trace JSON/HTML,
finite policy evidence, Unicode, invalid inputs, exact resource boundaries and
preserved-report sentinels. This extends the historical 141-file corpus with
56 native report/failure artifacts; it is finite evidence, not proof for all inputs.

For all 13 profiled workload/query cases on both interpreters, complete policy trace JSON
fingerprints, query work, additional policy work, input/model identities, overlapping
native stdout/stderr/exit fingerprints and generated native report bytes agree.
The second session repeats equality checks for its four inputs. Capacity input,
dimensions, outcomes and actual work agree at all 27 points. No difference is
waived on Boolean reachability alone.

The focused installed suite and full suites retain raw-declaration graph/per-port
oracles, independent witness replay, unordered allow/deny truth tables, raw-rule
matching/overlap/scoped-duplicate oracles, concrete-port comparison properties,
structural-versus-policy diagnostics and deliberately corrupt evidence detection.
Existing deterministic reordered-declaration and resource-boundary assertions are
not weakened. No oracle expected answer is derived from a new optimized matcher.

## 14. Work ceilings, reservations and failure integrity

Every ResourceLimits field/default and reservation formula is unchanged. Actual
Work.visit and predicate calls retain their meaning. For Q atom queries, V states,
E edges and A associations, prospective bounds remain 3*Q*(V+E) visits and Q*A
predicate checks. Optional evidence reserves complete edge/atom and association/atom
work in addition to the maximum of reserved or actual query work. It still examines
all declared edges, not just witness edges. No counters are synthesized, reset,
omitted or relabeled to manufacture equivalence.

The fixed dense/interval-heavy full-scope failures remain resource errors, never
partial success or unreachable classifications. Full boundary tests cover exact
and one-over limits. Native invalid/unsupported/I/O/execution/resource failures
retain exit 2 and no successful stdout; failed intents retain exit 1; completed
unreachable traces retain exit 0. Atomic failures preserve old binary reports and
clean temporary siblings. Paths containing spaces/Unicode, output/input collisions,
render/replace failures and escaping remain covered. The existing report resource
fault injection now targets the report path's architecture API; all original
failure assertions remain intact.

## 15. Capacity study and fixed benchmark

Twenty-seven finite Python 3.12 points vary nine axes. All sampled points completed;
the separate full-scope dense/interval-heavy cases retain controlled rejection.
The following ranges are observed medians/peaks, not fitted complexity or capacity
certification. Inventory changes also add interfaces; sparse edge sweeps remove
now-empty associations/rules; scope counts differ from declared service inventory.


| Axis | Parameters | Before wall range s | After wall range s | Largest after peak MiB |
| --- | --- | --- | --- | --- |
| inventory | 1, 3, 8 | 0.012148–0.023256 | 0.011845–0.021316 | 13.250 |
| edges | 1, 3, 8 | 0.005396–0.010082 | 0.004993–0.008828 | 3.736 |
| rules | 1, 3, 8 | 0.005763–0.011914 | 0.005429–0.010572 | 3.126 |
| sources | 1, 3, 8 | 0.021605–0.047176 | 0.022121–0.041971 | 4.107 |
| services | 1, 3, 8 | 0.019027–0.029296 | 0.017150–0.027221 | 3.895 |
| associations | 1, 3, 8 | 0.011330–0.012541 | 0.010269–0.012308 | 3.818 |
| atoms | 1, 3, 8 | 0.030719–0.045755 | 0.031575–0.045838 | 0.562 |
| deny_density | 1, 3, 8 | 0.011543–0.013425 | 0.011171–0.011533 | 3.818 |
| frontier | 1, 20, 25 | 0.001308–0.001404 | 0.001306–0.001447 | 0.209 |


The frontier sweep includes 1/20/25 parallel denied edges under the unchanged
20-entry sample ceiling. Inventory, edges, associations, atom count and source/service
products are distinct cost dimensions; declared counts below ceilings do not
guarantee completion time. No linear/quadratic scaling law or universal maximum
model size is inferred. Supported initiation evidence does not establish deployed
communication success.

The unchanged fixed routine exposure benchmark retains its maximum wall-time
30-second / traced-Python 512-MiB checks and its full bytes→validation/hash→analysis
pipeline. No stage is excluded or threshold increased. Fresh fixed-run observations:


| Python | Before maximum s | After maximum s | Before peak MiB | After peak MiB | Unchanged target passed |
| --- | --- | --- | --- | --- | --- |
| 312 | 1.123794 | 1.297474 | 7.050 | 7.050 | True |
| 314 | 1.159622 | 1.223381 | 7.248 | 7.248 | True |


## 16. Regression safeguards and test counts

Nineteen new collected tests: 12 command/format/input-change snapshot-binding and
validation-count cases; three consecutive same-path success/invalid/changed-policy
isolation cases; three resource-rejection/report-preservation/recovery cases; and
one deterministic fake-clock test proving wall/CPU batches are separate from traced
allocation. Counts directly verify the claimed optimization. No new timing threshold
or exploratory sweep is added to CI. Existing tests are retained, with the one
fault-injection target adjusted to the newly used architecture boundary.


| Python | Full installed tests | Pytest seconds | Ruff lint/format | Strict mypy | pip check | Provenance | Offline examples |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 312 | 1216 | 304.51 | pass | pass | pass | pass | pass |
| 314 | 1216 | 327.78 | pass | pass | pass | pass | pass |


The focused optimization/oracle suite passed all **251 tests** in **62.95 s** before
performance confirmation.
Full installed suites include the independent analytical oracles, native error/report
tests, resource failures, deterministic SVG/HTML and distribution integrity tests.
Hash-seed 0/12345 on both interpreters reproduces identical mixed-policy trace JSON
and HTML. Source production bytes remain identical to the tested candidate after
documentation-only final rebuilding and reinstall verification.

## 17. Regular installed candidate and distribution provenance

Candidate distribution identifier: `1.0.1.dev4+gate.v11.4`; application remains
1.0.1. Source pyproject.toml is unchanged. The explicit public manifest is copied
to ignored staging; the sole source/staging metadata difference is a byte-preserving
distribution-version substitution there. Builds use available 3.12/3.14 environments.
Wheel installation is non-editable, offline, no-dependency and in dedicated existing
verification environments. Workspace-local TEMP/TMP prevent unrelated temp writes.

tools/verify_environment.py checks real site-packages imports, native scripts,
metadata, non-editable direct_url provenance and every production-module SHA-256.
Final module hashes match reviewed source and the tested candidate. Archive audits
verify all 112 explicit public files, exact source/test/doc bytes, wheel RECORD,
entry points, dependency constraints, licenses and absence of unreviewed members.
Generated measurements/builds/logs remain ignored and outside public artifacts.
Final ignored integrity records bind archive hashes and installation provenance.

## 18. Six-way CI, security and license

The workflow is byte-unchanged: Windows/Ubuntu/macOS × Python 3.12/3.14,
fail-fast false, no exclusions/continue-on-error, read-only permissions, protected
checkout/root verification, installed checks, lint/format/strict mypy/pip check,
offline full suite/examples, exact distribution audit, unchanged fixed benchmark
and unique per-matrix artifacts. No hosted V11-4 job has been dispatched or claimed
successful. Local performance establishes no cross-platform speed guarantee.

Apache-2.0 and third-party notices remain unchanged. No new mandatory dependency,
runtime network operation, telemetry, external service, native extension, process
pool, persistent cache or resource increase is introduced. The tool remains an
independent declared IT/OT architecture analyzer, not deployed-network simulation,
certification, firewall generation, exploitability or risk scoring.

## 19. Unsuccessful attempts and deferred work

Initial fetch hit the filesystem sandbox's read-only Git boundary; the explicitly
authorized refresh/branch creation succeeded through the approved Git invocation.
Early harness formatting/type issues were corrected; one-file mypy initially saw
untyped installed imports, so the established full configured source check was used.
The fake-clock test now imports tracemalloc directly for strict typing. An initial
documentation patch context mismatch made no changes and was corrected. These are
tooling attempts, not passing acceptance evidence or failed analytical candidates.
The first-service mixed-fixture selection oversight was caught in final report
review and corrected with the explicitly scoped supplement described above;
original observations were retained. The profiling-only scope addition received
fresh lint/type/targeted verification; production bytes did not change.
The supplemental Markdown Python example initially needed Ruff formatting;
it was corrected and both interpreters' final static checks were rerun.

Full dense parser/allocation attribution took several minutes per interpreter;
confirmation therefore repeats relevant operations and analytical controls instead
of all unchanged attribution phases. No sample count or fixed threshold was reduced.
The normalization fast path was rejected before implementation. No failed production
optimization was retained, and no high-risk traversal/policy/partition rewrite was
performed. Future decision caching/pruning or work-reservation changes require a
separate VERY HIGH reasoning task and independent semantic/public-counter review.

## 20. Residual bottlenecks and practical limits

Strict YAML loading remains the dominant large native input cost. Interpreter/import
startup dominates tiny commands. Complete interval-heavy policy evidence still
performs 511,200 additional rows/checks; it is not limited to witnesses. Repeated
analytical work that is publicly counted remains intentional. Large evidence/report
serialization and geometry remain costs; no general output-size/RSS bound is claimed.
Native child CPU/RSS, controlled hosted performance, and broader hardware/OS behavior
are unverified. Existing accessibility/browser/print observations are not expanded
by this gate because report bytes/geometry are preserved.

## 21. Exact principal reproduction commands

Use corresponding 314 executables for the second locally available interpreter.
Before/after timings require regular baseline/candidate installations and stable
input identities; all exact local subprocess argument arrays and exits are retained
in ignored evidence, not required runtime dependencies.

```powershell
git fetch origin main --no-tags
git switch -c codex/gate-v11-4 main
.venv-verify312/Scripts/python.exe tools/verify_environment.py --output output/environment312.json
.venv-verify312/Scripts/python.exe -m benchmarks.profile --output output/before312/results.json --capacity
.venv-verify312/Scripts/python.exe -m benchmarks.profile --output output/after312/results.json --confirmation --capacity
.venv-verify312/Scripts/python.exe -m benchmarks.profile --output output/workflow312/results.json --profiles routine sparse mixed --report-workflow
.venv-verify312/Scripts/python.exe -m ruff check .
.venv-verify312/Scripts/python.exe -m ruff format --check .
.venv-verify312/Scripts/python.exe -m mypy
.venv-verify312/Scripts/python.exe -m pip check
$env:OTARCHGUARD_OFFLINE_CHECK = '1'
$env:PYTHONPATH = (Join-Path (Get-Location) 'tools/offline')
.venv-verify312/Scripts/python.exe -m pytest -q --tb=short --basetemp=.pytest_tmp/gate4-312
.venv-verify312/Scripts/python.exe examples/run_examples.py
.venv-verify312/Scripts/python.exe -m benchmarks.run --output output/fixed312.json
git diff --check
git fsck --full
git rev-list --max-parents=0 HEAD
git rev-parse 'v1.0.1^{}'
```

Candidate build in explicit public-file staging only:

```powershell
python -c "from setuptools import build_meta; build_meta.build_wheel('output/artifacts'); build_meta.build_sdist('output/artifacts')"
python -m pip install --no-index --no-deps --force-reinstall output/artifacts/otarchguard-1.0.1.dev4+gate.v11.4-py3-none-any.whl
python tools/audit_release.py output/artifacts/otarchguard-1.0.1.dev4+gate.v11.4-py3-none-any.whl output/artifacts/otarchguard-1.0.1.dev4+gate.v11.4.tar.gz --source-root . --output output/archive-audit.json
```

The local driver additionally captures/computes exact compatibility fingerprints,
restores accepted/candidate wheels for the second session, checks hash seeds and
audits the final public staging bytes. Staging uses the documented development
metadata only; never apply that substitution to authoritative source.

## 22. Modified/added files and documentation

Six modified tracked files: src/otarchguard/cli.py, tests/test_reporting.py,
docs/reporting.md, docs/benchmarks/README.md, MANIFEST.in and tools/public-files.txt.
Four new public files: benchmarks/profile.py, tests/test_preparation.py,
docs/benchmarks/performance.md and this report. Total: **10 files**, **19 new tests**.
README claims, stable version/license, workflow and analytical production modules
are unchanged. Documentation explains measurement categories, finite capacity,
optional policy cost, snapshot lifetime, practical commands and residual limits;
existing links are preserved.

## 23. Acceptance checklist and owner conclusion

- [x] Accepted V11-3 baseline/root/tag/identity verified; clean starting state recorded.
- [x] Actual bottlenecks measured; before-change evidence and variability retained.
- [x] Meaningful low-risk report optimization and second-session confirmation.
- [x] Public outputs, canonical hashes, intervals, witnesses, policies and work preserved.
- [x] No resource/reservation change, unbounded cache, dependency or semantic feature.
- [x] Independent oracles, snapshot/isolation/error/report safeguards and fixed targets pass.
- [x] Full regular installed suites on Python 3.12 and 3.14; lint/format/strict typing/pip check.
- [x] Installed/module/archive provenance, public manifest, offline examples and Git audits.
- [x] Six native CI combinations preserved; no unexecuted hosted result claimed.
- [x] No Git staging, commit, push, merge, tag, release, publication or later-gate work.
- [ ] Owner acceptance and separately authorized hosted six-way CI integration.

This gate is locally complete for review, with the scope and measurement limitations
above. Review the CLI diff, preparation tests, public profiling method and this
report alongside ignored raw evidence. Commit/push/PR/CI/merge remain separate
owner decisions. Gate V11-5 should start only after owner acceptance and successful
six-way integration, retaining this exact baseline, byte corpus, installed provenance,
resource oracles and performance methods. No V11-5 work is performed here.

