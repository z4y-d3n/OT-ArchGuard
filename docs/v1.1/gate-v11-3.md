# Gate V11-3 — exact communication trace and finite evidence

## 1. Executive engineering summary

FE-05 exposes the existing exact query evaluator through typed APIs, a native
`trace` command, versioned JSON and static offline HTML. FE-06 adds opt-in finite
duplicate-effect, allow/deny-overlap and no-match evidence. FE-07 aggregates
completed scenario queries; FE-08 references observed declaration and outcome
changes without causal attribution. Owner review and new hosted CI are pending.
Application version 1.0.1, schema 1 and the existing analytical engine are retained.

## 2. Initial Git state and baseline commit

The initial checkout was clean on `main`, tracking `origin/main`, at
`659a2d4403c58bcdea8dd56826dfa8ba278c3a05`. Fetching `origin main --no-tags`
confirmed that baseline. It includes V11-1 merge `1c3d00a` and V11-2 merge
`659a2d4`. Local branch `codex/gate-v11-3` was created from main; there was no
preexisting branch to overwrite. No reset, commit, push, merge or publication was
performed. The independent root is
`8e6a5bca41a00eb0454e6efdd9a9558e1a7017b2`.
The annotated v1.0.1 tag object is
`39c855ad6204953495fdca4a7058fd53a3ba8f8c`, targeting that root.

## 3. Frozen analytical invariants

No changes to domain, validation, normalization, intervals, graph, policy,
reachability, intents, exposure, comparison, flows or resource-limit definitions.
Administrative ownership differs from interface placement. Transport and
forwarding are explicit directed state transitions. There is no implicit relay,
reverse route, session or source-port behavior. Rules remain unordered with
default deny and deny precedence over original endpoint/protocol/destination-port
matches on associated edges. Canonical serialization and model hashes are retained.

## 4. Existing engine interfaces reused

`api.validate_bytes/file` supplies completed immutable ValidatedArchitecture
snapshots. `ReachabilityEngine(validated, frozenset({service_id}), limits)` builds
the existing state graph, exact service atoms, compiled selectors and sparse rule
associations. `evaluate(source, service)` supplies QueryResult/IntervalResult,
Witness/WitnessStep/Endpoint and UnreachableDiagnostics/BlockedEdge.
Engine replay, deterministic BFS, capacity reservation and Work counters are
unchanged. Existing `flows.observations`, ExposureResult and ComparisonResult
supply aggregation evidence. The trace serializers reuse report escaping,
static styling, evidence tables and atomic `write_report`.

## 5. FE-05 architecture and implementation

`trace.py` validates query identities and destination assertions, creates one
run-local engine, evaluates one source/service pair and adapts every exact atom.
It does not evaluate intents or copy graph-search logic. `trace_reporting.py`
serializes immutable results independently of computation. A trace-only report
uses the same validated input result without a presentation reread.

## 6. Exact trace CLI grammar

```text
otarchguard trace MODEL --source ASSET --service SERVICE
    [--destination ASSET] [--policy-evidence]
    [--report PATH] [--report-format html|json]
```

HTML is the report default. An explicitly supplied format requires a report
path. Parser usage errors use structured diagnostics for this new command.
No interactive prompt or network access is used.

## 7. Public trace API

`otarchguard.trace.trace_architecture`, `trace_bytes` and `trace_file` follow the
existing module-specific API organization. They accept custom ResourceLimits,
keyword destination_asset_id and policy_evidence. Expected invalid inputs raise
ModelError. Results are frozen typed dataclasses; no renderer, persistent cache or
filesystem state is required for analysis. See [the API contract](../trace.md).

## 8. Trace-version-1 JSON contract

The separate envelope includes trace_version, engine_version, schema_version,
status, model_sha256, intents_assessed, bound scope, exact intervals,
policy_evidence, evaluator work, resource_ceilings and interpretation. Required
fields, discriminated statuses, nested records and nullability are documented in
[trace.md](../trace.md#version-1-contract). Completion has no overall `passed`
field. A not-requested optional analysis contains only `status: not_requested`.
JSON uses sorted keys, ASCII escaping, two-space indentation and final LF;
the native command writes bytes to avoid Windows newline translation.

## 9. Exit-code behavior

Trace exits 0 for completed reachable, unreachable and mixed outcomes. Invalid,
unsupported, resource, I/O and execution failures exit 2 with structured stderr,
no successful stdout and no successful partial artifact. Existing exit-1 intent
semantics remain unchanged in check/exposure/compare.

## 10. Service/destination binding

The declared service fixes final asset, ingress interface, TCP/UDP protocol and
port union. Destination is an equality assertion. Unknown/malformed identities,
mismatch, self-asset queries and origins lacking interfaces are controlled errors.
The evaluator retains the original source and final destination through forwarding.

## 11. Exact interval evaluation

Trace preserves all evaluator atoms, including boundaries introduced by other
declared services/rules. It does not sample an arbitrary port or coalesce witness
records. Disjoint service ranges remain disjoint. Independent tests enumerate
every integer port in a small union, checking coverage, ordering, non-overlap and
agreement with raw-declaration reachability under TCP/UDP deny precedence.

## 12. Witness generation and replay

Existing engine witnesses retain model hash, exact endpoints, service, protocol,
interval and ordered transport/forwarding transitions. States retain interface
and phase; endpoints retain owning asset, placement zone and IPv4. Declared
conduit IDs and matching allows remain intact. Raw-declaration witness replay
checks continuity, every edge association and predicate, and exact bound ingress.
A witness establishes one supported initiation route; uniqueness, session success,
physical distance and deployed routing are unassessed.

## 13. Structural/policy frontier explanations

Unreachable records retain no_structural_path versus no_permitted_path,
structural_path_exists and explicit_deny/missing_permit frontier entries.
A structural absence is not labeled a firewall deny. Reachable intervals do not
fabricate blocked alternatives. Reverse-only declarations do not create a route.

## 14. Diagnostic truncation and limitations

The existing diagnostic_edges_per_query ceiling, ordering, actual frontier count
and truncated flag are retained. Tests include multiple frontier edges and limits
of zero/one. Frontier evidence establishes no unique root cause, exhaustive list
of all blocking rules, minimal cut or guaranteed fix. Unsupported queries and
resource failures are not classified as unreachable.

## 15. FE-06 policy-evidence scope and findings

`policy_evidence_for_query` uses the same compiled predicates and exact atoms.
Its scope states original source, bound destination/service, protocol, declared
port union, all examined declared edge IDs, rule IDs, association count and limits.
Edges outside a witness are included without alternate-path enumeration.
Same-effect rules are grouped only for identical nonempty matching domains.
Domains are factored as associated edges × matching port union, valid because
schema-1 rule predicates are identical on all explicitly associated edges.
This avoids pairwise rule comparisons and association/atom signature products.
Allow/deny overlaps retain exact atom intervals and matching rule IDs under deny
precedence. No-match findings mean no match in this domain, not globally unused.
No rule removal, optimization or redundancy counterfactual is performed.

## 16. Independent policy predicate oracle

The new raw-rule oracle uses source/destination selectors, administrative zone
membership, protocols, edge associations and individual integer ports directly
from synthetic dictionaries. It imports no production compiler, matcher,
PortSet or diagnostic helper for expected answers. Thirty-six seeds, two origins
and TCP/UDP listeners check exact matching domains, duplicate allows/denies,
partial overlaps, different edges, disjoint matches, outside-scope differences,
no-match findings and declaration reordering. Separate tests exercise zone
selectors, unknown/unsupported scope and rejection before predicate enumeration.

## 17. FE-07 aggregation semantics

`summarize_exposure` aggregates completed scenario queries only. It distinguishes
query pairs, exact interval records, summed individual ports, distinct reachable
assets and source/destination/service/protocol tuples. Cross-owner-zone tuples
use administrative asset ownership, separately labeled from interface placement.
Unavailable IDs, noncomparable services, excluded self pairs and unevaluated
present pairs remain explicit; outside-scope counts are null. It performs no
new reachability evaluation and never substitutes an overall security score.
Criticality remains an owner annotation in existing exposure evidence.

## 18. FE-08 change interpretation

`explain_comparison` references existing inventory/field/SUC changes and counts
existing interval, pair and asset deltas. Gained ports in an already reachable
pair and new pair access to an already reachable asset are distinguished.
Changes are described as co-occurring, with no unique causal attribution.
Existing classified declaration diffs, changed service definitions, unavailable
entities and required/prohibited intent findings remain separate evidence.

## 19. HTML report structure and security

Trace HTML includes identity, bound scope, exact interval table, ordered witness
details, bounded frontier evidence, optional policy scope/findings, work/ceilings,
interpretation and complete JSON. It has static navigation, keyboard-accessible
details, responsive tables, print CSS, escaping and restrictive CSP; no JavaScript,
external resource or inferred route drawing. Existing diagram geometry is untouched.
Native exposure/comparison HTML adds completed-result summary tables. Programmatic
callers opt in with `html_report(..., analysis=completed_result)`; the typed result
must match the envelope. Existing JSON is unchanged. HTML parser tests verify CSP,
safe fragment links and absence of active injected markup. Manual cross-browser,
screen-reader and printed-page inspection are not claimed.

## 20. Work/resource accounting

Trace work is exactly engine query_atoms, state_edge_visits and
edge_rule_atom_checks before optional diagnostics. Additional policy work reports
actual/planned edge-atom evaluations and predicate checks. The helper debits shared
engine counters. Before expansion, conservative reserved query work (or actual
work if larger) plus complete diagnostic bounds must fit the unchanged limits.
Signature grouping is sparse and non-quadratic. Report serialization does not
silently discard findings for a display budget. Existing ceilings bound work,
not a measured universal maximum-memory or maximum-report-size guarantee.

## 21. Modified and added files

Production additions: `trace.py`, `trace_reporting.py`, `policy_evidence.py`,
`summaries.py`. Production edits: CLI registration/trace boundary and additive
HTML reporting. New tests: `test_trace.py`, `test_trace_cli.py`,
`test_policy_evidence.py`, `test_summaries.py`. Other changes: the synthetic trace
YAML, installed example walkthrough, README, examples README, reporting/trace
documentation, this report, MANIFEST.in and tools/public-files.txt. No existing
test assertion is relaxed or deleted. Detailed machine evidence remains ignored.
The final change set contains eight modified tracked files and eleven new public
files (19 total). No files are staged.

## 22. New tests and coverage

There are 141 new collected tests. The accepted suite had 1,056 tests; the combined
suite has 1,197. New tests cover adapters, binding, exact ports, raw graph/witness
and policy oracles, error categories, resources, frontier truncation, deterministic
serialization, native CLI/report preservation, concrete summaries and conservative
explanations. The full suite retains accepted Unicode, report geometry, resource,
offline, integrity and native installed-console regressions.

## 23. Independent graph/interval oracle results

Thirty-six fixed-seed tiny state graphs × two sources × two protocols provide
144 trace comparisons over each disjoint seven-port union. Expected paths come
from raw transitions and recursive simple-path enumeration, independent of the
production graph, policy decision and port partitioner. Every returned witness is
independently replayed. Structural searches are checked using all-permitted raw
transitions. In-test deliberate reachable-flag inversion and fabricated witness
allow IDs trigger expected AssertionErrors; these demonstrate the oracle assertions
reject corrupt evidence without modifying production code.

## 24. Before/after analytical equivalence

Before implementation, 33 accepted cases produced 120 saved files on Python 3.12.
Before changing its accepted installation, Python 3.14 captured an expanded corpus:
36 native cases and 141 files, including mixed policy, Unicode, exact custom
resource boundaries and the routine/sparse/deny-heavy workloads. Baseline installed
modules were verified against the accepted checkout. Final byte comparisons are
recorded with individual hashes in ignored local evidence.
The corpus includes all original documented architecture families, boundary-device
and minimal fixtures, required/prohibited intents, exposures and comparisons.
Additive native exposure/comparison HTML summaries are the only intended old-report
presentation extension; existing programmatic HTML without the opt-in is preserved.

Observed on both final installations: all **141 expanded baseline files are
byte-identical** (36 native command cases plus canonical, JSON report, legacy
HTML, SVG and resource/workload artifacts). The comparison records each file's
SHA-256; no differences were found. Native stdout, exits, model hashes and
analytical evidence therefore agree for this concrete corpus. This is finite
compatibility evidence, not a claim about every possible valid input.

## 25. Deterministic output verification

Repeated trace evaluations and reordered declarations are tested, including exact
intervals, witness choice, policy ordering and work counters. JSON and HTML contain
no clocks, random identifiers, hostnames or input absolute paths. Native byte
stdout equals JSON report bytes, including LF on Windows. Cross-interpreter and
hash-seed evidence is recorded locally. Existing canonical JSON, hashes, diagrams,
reports and four-command stdout are compared with the accepted baseline.

Observed for the mixed synthetic trace with policy evidence on both interpreters
and PYTHONHASHSEED 0/12345: JSON 10,186 bytes, SHA-256
`c731e4a392f4eecb15f5418d479332a9f5b0ceb73f16cc3529fad03c850bbb97`;
HTML 32,959 bytes, SHA-256
`f59d52b91f90074ff6838e7e5884aa0854553016e60ee5f039090e400ab8cfb9`.
All four subprocess outputs and all four HTML artifacts were byte-identical.

## 26. Native CLI failure/report-preservation checks

Native subprocess tests exercise missing options, invalid identifiers, unknown
IDs, self-query, destination mismatch, malformed/unsupported input, nonexistent
files, input overwrite, directory output and missing output parent. Existing
binary sentinels survive. Successful unreachable/mixed traces exit 0. Fault
injection exercises os.replace failure, execution failure and policy resource
exhaustion; no stdout success or unexpected report temporary file remains.
These injected failures are identified as test injection, not naturally observed
application incidents. Paths with spaces and Unicode are exercised.

## 27. Python 3.12 local verification

Regular environment `.venv-verify312`, CPython 3.12.14, Windows AMD64, using the
bundled Python base runtime. Development distribution
`1.0.1.dev3+gate.v11.3`, application 1.0.1. Final checks and elapsed times are
recorded in ignored `output/gate-v11-3/final312/checks.json` and separate logs.
Observed: 141 focused tests passed in 57.34 s; all 1,197 tests passed in
291.74 s. Ruff lint, strict mypy, pip check, installed identity and all installed
synthetic walkthroughs passed. The initial format check found only the new
Markdown Python example; the corrected tree passes Ruff format check.

## 28. Python 3.14 local verification

Regular environment `.venv-verify314`, CPython 3.14.5, Windows AMD64, using the
installed local Python base runtime. The same non-editable candidate and production
bytes are used. Final checks and elapsed times are recorded in ignored
`output/gate-v11-3/final314/checks.json`.
The launcher `py -0p` found no registered interpreters; direct environment
executables were used. No private backup implementation was read or used.

Observed: 141 focused tests passed in 59.13 s; all 1,197 tests passed in
310.80 s. Ruff lint/format, strict mypy, pip check, installed identity and all
installed synthetic walkthroughs passed. Both environments import production
modules from their own site-packages; every module hash matches reviewed source.

| Final local check | Python 3.12.14 | Python 3.14.5 |
| --- | --- | --- |
| New focused tests | 141 passed | 141 passed |
| Full installed suite | 1,197 passed | 1,197 passed |
| Ruff lint and corrected final format check | exit 0 | exit 0 |
| Strict mypy (60 Python source files) | exit 0 | exit 0 |
| pip check | exit 0 | exit 0 |
| Installed import/module/native-console verification | exit 0 | exit 0 |
| Offline installed synthetic walkthroughs | exit 0 | exit 0 |
| Expanded compatibility capture | exit 0; 141 identical files | exit 0; 141 identical files |
| Fixed benchmark contract | exit 0 | exit 0 |
| Trace performance/rejection observations | exit 0 | exit 0 |

## 29. Installed-package integrity evidence

Both accepted installations were first checked with tools/verify_environment.py.
The development build is staged only under ignored output, copying the explicit
public manifest and changing only staging distribution metadata to
1.0.1.dev3+gate.v11.3. Source pyproject.toml and application version remain 1.0.1.
The wheel is installed without dependencies or an index as a regular distribution.
Verification checks metadata, non-editable provenance, actual site-packages import
location, every production-module SHA-256 and the interpreter's native console.
No stable release archive is overwritten, repackaged or published.

## 30. Six-way CI preservation and remote status

The workflow is unchanged: native Windows/Ubuntu/macOS × Python 3.12/3.14,
fail-fast false, no exclusions/continue-on-error, read-only permissions, protected
checkout settings, EXPECTED_ROOT_SHA verification, installed checks, lint/format,
strict typing, pip check, offline full pytest, installed walkthroughs, package
audit, fixed benchmarks and unique OS/Python artifacts. New tests and trace
walkthroughs run through existing full-suite/example steps. The repository variable
was not changed; its remote value was not independently queried in this gate.
The owner's reported six successful V11-2 jobs are historical evidence only.
No V11-3 hosted run was dispatched; no new hosted outcome is claimed.

## 31. Performance observations

Local trace measurements cover mixed, routine, sparse, dense-policy and
interval-heavy models, with and without policy evidence. Five untraced runs
record wall and CPU seconds; a separate run records peak traced Python allocation,
not operating-system RSS. Trace uses a prevalidated snapshot; the unchanged fixed
benchmark measures its existing pipeline. Both verification jobs may run
concurrently, so timings are observations under shared load, not optimization
claims. CPU: Intel Core i5-11400H @ 2.70GHz; Windows AMD64. Detailed interpreter,
platform, logical CPU and work counters are recorded (12 logical CPUs).
Gate V11-4 optimization is not begun.

The unchanged fixed benchmark runner exits 0 on both interpreters. Routine
exposure maximum wall time / separate peak traced allocation: 3.12 **1.198699 s /
7,392,801 bytes**, 3.14 **1.666075 s / 7,599,713 bytes**. Both meet the existing
30-second / 512-MiB target. Sparse and deny-heavy profiles complete;
dense-policy and interval-heavy full-scope profiles retain controlled resource
rejection. The target is not a report, comparison or process-RSS claim.

Trace median wall seconds over five runs, using a prevalidated snapshot:

| Profile | 3.12 plain | 3.12 policy on | 3.14 plain | 3.14 policy on | Largest policy-on traced peak across interpreters (bytes) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Mixed | 0.000306 | 0.000335 | 0.000317 | 0.000352 | 18,632 |
| Routine | 0.010285 | 0.011542 | 0.009319 | 0.011278 | 4,029,928 |
| Sparse | 0.006789 | 0.007509 | 0.006821 | 0.008068 | 3,744,320 |
| Dense policy | 0.017660 | 0.065486 | 0.018552 | 0.066323 | 5,962,624 |
| Interval heavy | 0.028822 | 0.715883 | 0.029278 | 0.582832 | 4,567,264 |

Actual work is identical between interpreters for these inputs:

| Profile | Query atoms | Query state/edge visits | Query predicate checks | Additional policy edge/atom evaluations | Additional predicate checks |
| --- | ---: | ---: | ---: | ---: | ---: |
| Mixed | 6 | 27 | 18 | 6 | 18 |
| Routine | 1 | 52 | 38 | 1,200 | 1,200 |
| Sparse | 1 | 38 | 29 | 240 | 240 |
| Dense policy | 1 | 59 | 400 | 1,200 | 120,000 |
| Interval heavy | 426 | 25,139 | 2,131 | 511,200 | 511,200 |

CPU measurements are separate in the detailed records. Windows process CPU
timer quantization yields zero for some sub-millisecond runs; zero is not a
claim of no CPU work. Policy-on interval-heavy median CPU is 0.718750 s on 3.12
and 0.593750 s on 3.14. The custom one-check budget rejects the two-check combined
trace/evidence plan as a resource error before diagnostic predicate enumeration.
Broad capacity, maximum output size and performance optimization remain V11-4 work.

## 32. Packaging and public manifest verification

The explicit public manifest and MANIFEST.in include all new sources, tests,
example and docs. Candidate wheel/sdist audits check exact members, source bytes,
RECORD hashes, requirements, entry point and licensing. Staged distribution
metadata is the documented sole metadata difference from the authoritative tree.
The final candidate audit passes with all 108 explicit public files, complete
wheel RECORD checks and no unreviewed members. Production-module hashes match
both installed environments. Generated reports, local paths, logs, temporary inputs
and environments remain ignored and outside published contents.

## 33. Security and licensing implications

Apache-2.0, third-party notices and independent identity are unchanged. No new
mandatory dependency or runtime network operation is introduced. No private
technical reference material is accessed. Conclusions remain declared finite
initiation evidence: no standards certification, deployed connectivity,
exploitability, session success, operational safety or reduced physical/financial
risk is asserted. Model text remains escaped in HTML and ASCII-safe JSON.

## 34. Known limitations

Only TCP/UDP IPv4 initiation and schema-1 explicit transitions are supported.
Self-asset trace queries are unsupported. Frontiers are bounded and do not prove
unique causes. Policy evidence includes every declared edge and can be materially
more expensive than a witness search; resource rejection is fatal and complete.
No global redundancy, rule-removal simulation, counterfactual, alternate-path
enumeration, optimization or remediation is implemented. Summary APIs trust
completed typed evaluator evidence. Programmatic legacy HTML includes new summaries
only when its matching typed analysis is supplied. Manual browser/accessibility/
print inspection and new hosted native OS verification are pending.

## 35. Failed attempts and final corrections

An initial pytest baseline used a nested basetemp whose parent did not yet exist:
763 tests passed and 293 fixture setup errors were infrastructure failures, not
acceptance evidence. A subsequent baseline attempt overlapped a failed package
replacement and is also excluded from acceptance (936 passed, 120 failed).
The baseline captures and verified accepted installation remained available on
3.14; final isolated installed suites supersede those attempts. The failed pip
replacement used the sandbox system temp and partially uninstalled the 3.12
distribution. Reinstalling with workspace-local TEMP/TMP restored it; checked
workspace-local stale uninstall directories were removed. No release artifact
or report sentinel was damaged.

Initial FE-05 tests caught a Pydantic port-record JSON adapter error; frozen
plain port records fixed it. The installed Typer version vendors its parser;
using a direct click import failed, so structured trace usage handling now uses
the command's native exit classification without adding dependencies. A baseline
helper's shared dictionary produced forbidden YAML aliases; that local helper
now emits independent declarations. A Markdown Python example needed Ruff
formatting; it was corrected. All these initial failures are retained in ignored
logs and excluded from final passing evidence. No blanket timeout increase,
retry, test skip or weakened analytical assertion was used.

The final source/staging byte comparison also detected Windows newline conversion
in the staging-only pyproject metadata edit. The helper now replaces the version
in raw bytes, preserving every other byte; the final rebuild and audits verify
that the distribution version is the sole source/staging difference.

## 36. Exact principal verification commands

From the authoritative checkout, with corresponding 314 executables for 3.14:

```powershell
git fetch origin main --no-tags
git switch -c codex/gate-v11-3 main
.venv-verify312/Scripts/python.exe tools/verify_environment.py --output output/gate-v11-3/baseline-environment312.json
.venv-verify314/Scripts/python.exe tools/verify_environment.py --output output/gate-v11-3/baseline-environment314.json
.venv-verify312/Scripts/python.exe output/gate-v11-3/compatibility.py baseline
.venv-verify314/Scripts/python.exe output/gate-v11-3/compatibility.py baseline314
.venv-verify312/Scripts/python.exe output/gate-v11-3/build_candidate.py
$env:TEMP = (Resolve-Path output/gate-v11-3/tmp).Path
$env:TMP = $env:TEMP
.venv-verify312/Scripts/python.exe -m pip install --no-index --no-deps --force-reinstall output/gate-v11-3/candidate-source/output/artifacts/otarchguard-1.0.1.dev3+gate.v11.3-py3-none-any.whl
.venv-verify312/Scripts/python.exe output/gate-v11-3/verify.py final312
.venv-verify314/Scripts/python.exe output/gate-v11-3/verify.py final314
git diff --check
git status --short
git rev-list --max-parents=0 HEAD
git rev-parse 'v1.0.1^{}'
```

The ignored driver records each exact executable/argument array, native exit and
elapsed wall time, and sets OTARCHGUARD_OFFLINE_CHECK=1, PYTHONPATH to tools/offline,
UTF-8, NO_COLOR and TERM=dumb. Its principal steps are:

```powershell
.venv-verify312/Scripts/python.exe tools/verify_environment.py --output output/gate-v11-3/final312/installed.json
.venv-verify312/Scripts/python.exe -m ruff check .
.venv-verify312/Scripts/python.exe -m ruff format --check .
.venv-verify312/Scripts/python.exe -m mypy
.venv-verify312/Scripts/python.exe -m pip check
.venv-verify312/Scripts/python.exe -m pytest tests/test_trace.py tests/test_trace_cli.py tests/test_policy_evidence.py tests/test_summaries.py -q --tb=short --basetemp=.pytest_tmp/final312-focused
.venv-verify312/Scripts/python.exe -m pytest -q --tb=short --basetemp=.pytest_tmp/final312
.venv-verify312/Scripts/python.exe examples/run_examples.py
.venv-verify312/Scripts/python.exe output/gate-v11-3/compatibility.py final312-compatibility
.venv-verify312/Scripts/python.exe -m benchmarks.run --output output/gate-v11-3/final312/benchmark.json
.venv-verify312/Scripts/python.exe output/gate-v11-3/performance.py output/gate-v11-3/final312/trace-performance.json
.venv-verify312/Scripts/python.exe output/gate-v11-3/compare_evidence.py final312-compatibility final314-compatibility
.venv-verify312/Scripts/python.exe output/gate-v11-3/determinism.py
.venv-verify312/Scripts/python.exe output/gate-v11-3/integrity.py
```

Local evidence helpers are ignored verification utilities, not package/runtime
dependencies or required files for the public test suite.

## 37. Acceptance checklist

- [x] Exact existing evaluator reused; analytical/schema/version/ceiling definitions retained.
- [x] FE-05 CLI/API, exact coverage, binding, independent graph/port/witness evidence.
- [x] Structural versus policy blockage; explicit deny versus missing permit; truncation.
- [x] Separate trace-version-1 contract and completion exit semantics.
- [x] FE-06 exact scoped evidence, independent predicates and prospective budgets.
- [x] FE-07 typed finite summaries with explicit units/unavailable/excluded/unassessed data.
- [x] FE-08 observed-change references without causal/counterfactual claims.
- [x] Static escaped offline trace HTML and atomic report-preservation checks.
- [x] Full installed verification on both local interpreters recorded above.
- [x] Compatibility, distribution/source integrity and complete diff review.
- [x] Six native CI combinations and root verification retained.
- [x] No commit, push, tag, publication, release change or later-gate work.
- [ ] New hosted six-way CI and owner acceptance (separate authorization).

## 38. Owner-facing summary

Implementation and local verification are complete for owner review. Final
compatibility, integrity and performance evidence are recorded above. Review the trace
contract, finite diagnostic scope, example reports and documented limitations.
Local commit, push, new hosted CI, PR and merge remain owner-authorized next steps.

## 39. Recommended Gate V11-4 starting conditions

Begin only after V11-3 owner acceptance and six-way hosted CI integration or an
explicit owner exception. Retain installed provenance, canonical/report baselines,
raw-declaration oracles and exact work counters. Profile the optional all-declared-
edge evidence separately from trace search and presentation. Investigate measured
redundant analysis work without changing semantics, ceilings or public contracts.
