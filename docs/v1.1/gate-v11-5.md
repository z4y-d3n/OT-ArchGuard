# Gate V11-5 — release hardening and contract stability

## 1. Executive summary

**GATE V11-5 — LOCALLY COMPLETE; OWNER REVIEW REQUIRED**

The accepted implementation has no production-source changes. FE-13 inventories
the existing public interfaces; FE-14 adds bounded adversarial and transaction
fault checks; FE-15 extends independent concrete-port/metamorphic verification;
FE-16 adds reproducible installed contract captures and distribution provenance;
FE-17 records the remaining release-candidate decision boundary.

There are 120 new collected tests (113 original gate cases plus seven final-review
oracle regressions), plus one assertion extending every existing
entity/association boundary case to include one unit of headroom. No confirmed
Critical or High product defect was found in the exercised scope. This is bounded
verification evidence, not proof that no defect exists. Owner acceptance and new
hosted six-way CI remain pending. No version promotion or later-gate work occurred.

Evidence labels used below: **verified fact** = direct Git/source inspection;
**local measurement** = current executed evidence; **historical** = earlier dossier;
**NOT_VERIFIED** = no current execution evidence; **limitation** = explicit scope
boundary; **future action** = separately authorized owner work.

## 2. Gate scope and change classification

| Class | Work in this gate | Disposition |
| --- | --- | --- |
| A: behavior-preserving production fix | none required by reproduced failures | no production edit |
| B: tests/documentation/verification | two test modules, resource assertion, contract capture tool, inventory/dossier/testing guide, exact manifests | implemented |
| C: observable contract change | no existing API/CLI/output/ordering change proposed | no implementation |
| D: mathematical/security-semantic change | no reproduced issue requiring one | no implementation or approval request |

No new analytical feature, dependency, cache, rendering design, resource ceiling,
reservation formula or CI behavior is introduced. The new opt-in verification
tool is development tooling, not a runtime facility or new analytical contract.

## 3. Current baseline SHA

Verified starting main, fetched origin/main and development HEAD:
`8c6d46dd0dea127044232d2b44e6bd11d2af3f53`.
The checkout was clean on main tracking origin/main, with zero ahead/behind.
Created local branch `codex/gate-v11-5` from that main. No owner changes were reset,
cleaned, overwritten or staged. The initial sandbox denial of FETCH_HEAD was
followed by successful authorized Git fetch and branch creation.

## 4. V11-4 integration confirmation

Fetched main is merge PR #4, with parents accepted V11-3 main and V11-4 commit
`121de2e`. `git merge-base --is-ancestor 121de2e main` exits 0. The historical
`46cca6487e67341ff79a3c2844dede6dd2e5fd21` is not this gate's starting HEAD.
The user's integration statement is corroborated by fetched Git ancestry.
Earlier GitHub connector queries required reauthentication, so prior hosted job
outcomes were NOT_VERIFIED during that audit. The local-only final review makes
no new remote query. Integration ancestry is not substituted for CI results.

## 5. Independent-root verification

The sole root is `8e6a5bca41a00eb0454e6efdd9a9558e1a7017b2`.
`git fsck --full` exits 0 and reports two dangling trees; no corruption was
reported. History was not rewritten. EXPECTED_ROOT_SHA workflow references are
byte-preserved; the remote repository variable was not queried or changed.

## 6. Stable tag verification

v1.0.1 remains an annotated tag, object
`39c855ad6204953495fdca4a7058fd53a3ba8f8c`, dereferencing to the independent root.
No tag or stable release asset was moved, created, rebuilt, replaced or published.
The earlier read-only `git ls-remote` operation independently confirmed that remote
main, tag object and peeled tag target matched these local identities at that time;
see output/gate-v11-5/remote-refs.txt. This is historical evidence, not an instruction
to refresh remote state during the local-only final review.

## 7. Frozen version/schema/contract identities

| Identity | Verified retained value |
| --- | --- |
| Authoritative project and application/engine | 1.0.1 |
| Architecture schema | 1 |
| Legacy report contract | report_version 1 |
| Exact trace contract | trace_version 1 |
| Staging-only development distribution | 1.0.1.dev5+gate.v11.5 |
| License | Apache-2.0 |

No authoritative version or schema edit occurred. Source pyproject.toml is
byte-identical to baseline. Development staging changes only its distribution
version using raw-byte substitution; installed application remains 1.0.1.

## 8. Source code inspection scope

Inspection covered validation/API, bounded loading and strict scalar/Unicode
handling, parsing/domain/reference validation, normalization/canonical identities,
interface-state graph, exact partition/policy/query work, deterministic search and
witness replay, intent/exposure/comparison adapters, finite policy evidence,
summaries, report binding/escaping/writing and SVG declarations. Existing oracle,
resource, CLI, presentation, preparation and archive tests were reviewed, together
with examples, benchmarks, package metadata, release instructions and CI.

All 25 production Python modules retain accepted SHA-256 identities, recorded in
`output/gate-v11-5/baseline-hashes.json` and `final-integrity.json`, alongside
metadata/workflow/license hashes. No private implementation, reference data or
backup was accessed. Inspection and tests are not a formal security certification.

## 9. Public API inventory

The maintained [contract inventory](public-contract-inventory.md) records exact
source signatures, parameter defaults, return records, work/resources and support
boundaries. Explicitly documented trace/report/summary interfaces are distinguished
from established typed validation/analysis adapters and incidental importable
helpers. Package root is not treated as exporting all module helpers.

File, byte and prevalidated check/exposure/comparison calls produce equal typed
results including counters. Existing trace adapter tests cover the same boundary.
Prevalidated snapshots trust completed validation; forged Python records are
outside the untrusted YAML boundary. API unexpected exceptions can propagate;
the CLI's sanitized catch-all is not claimed as an API exception guarantee.

## 10. Native CLI contract inventory

| Command | Required input/scope | Optional scope | Completion exit |
| --- | --- | --- | --- |
| validate | architecture path | none | 0 |
| check | architecture path | declared intents | 0 or 1 |
| exposure | architecture, --scenario | none | 0 or 1 |
| compare | baseline, proposed, common scenario OR explicit origins/services | repeatable --origin/--service | 0 or 1 |
| trace | architecture, --source, --service | --destination equality assertion; --policy-evidence | 0 including unreachable |

All support --report and --report-format html/json, default html. First four
support HTML-only --zone-order. Trace rejects explicit format without report;
legacy commands retain their accepted ignore behavior. Scalar repeat options
retain last value; repeated set IDs undergo domain distinctness checks.

## 11. Structured output contract inventory

The inventory transcribes result field shapes, sorted JSON output, ordered exact
intervals/witness steps/rule IDs, snapshot roles, complete resource records and
policy-evidence discrimination. Normative authorities remain schema/report/trace
documentation, not an independent duplicate schema. Canonical model bytes are
compact sorted literal UTF-8; JSON evidence is sorted and ASCII escaped, with
report/trace indentation and LF termination. Canonical IDs include declared text.

Validation stdout contains status/schema/engine/model hash/scope. Other legacy
commands add versions to typed results; trace uses its distinct version-1
envelope. Comparison retains separate baseline/proposed identities. Counters
retain their units and conservative admission bounds.

## 12. Diagnostic and exit-code matrix

| Event | Exit | stderr | stdout/report |
| --- | --- | --- | --- |
| Completed validation/analysis, all intents pass | 0 | empty | complete evidence |
| Failed required/prohibited intent | 1 | empty | completed failure evidence/report |
| Completed unreachable/mixed trace | 0 | empty | complete trace, no fabricated passed flag |
| Invalid/unsupported model | 2 | invalid_input/unsupported_model JSON diagnostics | no successful stdout/new report |
| Resource rejection | 2 | resource_limit / LIMIT_EXCEEDED | no successful partial evidence |
| Read/report I/O | 2 | io_error / READ_ERROR or REPORT_IO_ERROR | prior output preserved |
| Renderer/serializer/unexpected execution | 2 | execution_error / INTERNAL_ERROR, sanitized | prior output preserved |
| Invalid native parser options | 2 | trace JSON INVALID_VALUE; legacy Typer usage | no successful stdout |

Diagnostic fields: category, code, location, message, nullable line/column.
ModelError sorts by location/code. The full code vocabulary is in the inventory.
Parser usage diagnostics are not falsely described as universally structured.

## 13. Golden compatibility baseline

Before adding tests, both regular V11-4 installations passed provenance checks.
One fresh accepted capture per interpreter reproduced **197/197 historical
artifacts**, including canonical models, CLI stdout/exits, JSON/HTML/SVG,
finite work, trace/policy evidence, invalid/unsupported diagnostics and sentinels.
No baseline output was rewritten to make a difference pass.

The new public `tools/capture_contract.py` captures **45 native cases / 123
artifacts**, with input/model/module SHA-256, exits and output hashes. It adds
help/parser misuse for every command, all report formats, explicit missing-permit,
deny and structural absence, mixed trace/policy cases and failure sentinels.
All existing/new baseline directories are preserved separately. Comparison
requires equal bytes/hashes and exits, not merely equal final Booleans.

Fresh legacy evidence is under `output/gate-v11-4/gate5-baseline312-compatibility`
and its 314 counterpart; candidate captures use `gate5-final...`. Additional
baseline manifests are under `output/gate-v11-5/expanded-baseline312` / 314.
These are ignored local evidence, not packaged golden data or private references.
`final-integrity.json` also records input raw hashes across public examples and
fixtures. New capture baseline raw outcomes were reviewed against minimal raw
declarations: no edge => no structural path; no rule => missing permit; deny =>
explicit deny; complete trace still exits 0. Existing independent oracles verify
the richer mixed and policy families. Independent owner review remains pending.

## 14. Threat model

Untrusted surfaces are local architecture YAML and local input/output paths.
Bounded event parsing, strict domain/reference validation, immutable snapshots,
bounded analytical work and escaped deterministic evidence form the implemented
boundary. Impacts considered: exhaustion, uncontrolled exceptions, wrong finite
truth, misleading hashes/witnesses, corrupted output, input overwrite and active
markup. Trusted assumptions include interpreter/dependencies, local filesystem
integrity and ordinary single-process execution. Arbitrary hostile multitenant
hosting, concurrent hostile filesystem mutation and OS compromise are not certified.
No live scanning, controller exploitation, packet simulation or compliance result
is implied.

## 15. Adversarial input families

New bounded cases cover whitespace, collection/scalar roots, nested unexpected
mapping, recursive aliases, explicit binary tags, Boolean/collection mapping keys,
multiple documents, raw NUL, malformed/overlong/truncated/surrogate/out-of-range
UTF-8, escaped surrogates/out-of-range escapes, numeric/type substitutions and
5,000-digit integers. Each repeats and compares controlled diagnostics.
Existing loading/validation/Unicode suites supply duplicate keys/IDs, selectors,
references, placement, intervals, feature/protocol rejection and valid Unicode.
Existing generated graph families cover cycles, dense/parallel transitions and
disconnected paths. No open-ended fuzzing or dependency was added.

## 16. Unicode and YAML findings

No reproduced parser escape or Unicode regression. V11-1 protections remain
byte-preserved. Valid combining/confusable/bidi/separator/supplementary text and
noncharacters are not rejected simply for being non-ASCII. Raw YAML-forbidden
controls fail; accepted XML-incompatible display values retain replacement-only
rendering without changing canonical declared text. Identifiers remain ASCII
schema syntax. There is no separate scalar-length ceiling: the existing total
input-byte/event/depth bounds apply; long safe integers meet interpreter digit
rejection. No new Unicode policy was introduced.

## 17. Resource-boundary findings

Existing limits/defaults and reservation code are byte-identical. Small injected
byte/depth/event limits test one below/exact/one above observed demand. Existing
entity/edge/association cases now also verify one unit of headroom. Existing atom,
actual-work/frontier and pathological-workload tests remain active. New raw
single-edge checks independently derive four interface-phase states plus one edge:
one atom reserves 3*(4+1)=15 visits; complete evidence adds one row. One associated
rule reserves one predicate plus one evidence predicate. Budgets 15/16/17 visits
and 1/2/3 predicates demonstrate controlled rejection and complete admission.
Actual successful query counters are 1 atom, 4 visits, 1 predicate; evidence adds
one row and one predicate. No counters were copied as expected oracle answers.

## 18. Fault-injection findings

All five commands are exercised against renderer, serializer, temporary creation,
partial write and atomic replacement OSError injection: **25 cases**. Private
exception text is absent; fatal stdout is empty; exit/category match the accepted
boundary; existing destination and input bytes survive; no temporary sibling is
left. A separate denied-read check verifies sanitized READ_ERROR. Existing tests
cover missing parent, directory target, input collision, resource/validation
failure, invalid zone order and failed/recovered invocations.

## 19. Atomic report integrity

Construction/serialization precede write_report. It rejects resolved input/output
collisions, creates a unique sibling, closes it and uses os.replace, then attempts
cleanup in finally. New partial-write tests write 17 bytes before failure and
verify the original report survives. Unicode/spaces in paths work. Guarantees are
per-artifact replacement on the tested Windows filesystem, not multi-file
transactions, fsync durability, cross-process locking or cleanup after hard kill.
OS refusal of cleanup and hostile concurrent filesystem changes remain outside
the controlled-failure guarantee demonstrated by tests.

## 20. Independent graph oracle

The retained test_reachability_oracle oracle creates directed raw interface-phase
transitions and recursively enumerates simple paths. Expected connectivity does
not call production graph/search/compiler/partition helpers. Fixed 36-seed tiny
graphs and two sources/listeners include cycles and boundary forwarding. Existing
trace tests independently distinguish permitted versus structural paths.

## 21. Independent policy oracle

Raw selectors match original source/destination assets, owner zones, protocol,
concrete destination port and explicit edge associations. Truth is allow present
and no deny; default deny is explicit. The oracle does not use production decide
or compiled policy. Tests retain protocol separation, parallel-edge associations,
multiple matching rules and off-witness finite scope.

## 22. Per-port oracle

After final-review correction, coverage() derives its complete expected port
domain directly from the selected original raw YAML service declaration. The
returned scope and trace intervals must each cover exactly that domain, without
overlapping or duplicate concrete ports. Every reported Boolean, including
unreachable ports, is compared with the independent raw oracle. Reachable
intervals require a replayable witness and no diagnostics; unreachable intervals
require diagnostics and no witness. Seven corrupted-trace regression cases reject
missing/extra scope ports, missing/extra/duplicate interval ports, and incorrect
reachable or unreachable truth values.

The production interval result is expanded only for small selected unions and
compared with independent raw per-port truth. Existing seeds use 1..8 and disjoint
unions; new TCP/UDP edge cases use 1..3 and 65533..65535, with deny at 2/65534.
Expected permitted set is 1,3,65533,65535 for the matching protocol, and empty for
the other protocol. A permit on one edge cannot authorize its parallel peer.
No test enumerates all 65,535 ports for each graph or uses production answers as truth.

## 23. Witness replay

Retained raw replay verifies original start, edge direction/type, state phases,
asset/placement/IP/conduit identity, every matching allow and absence of deny,
final service/interface/protocol/port binding. New relations replay all returned
witnesses. Deliberately mutated witness tests remain active to demonstrate oracle
sensitivity. Deterministic selected routes and exact interval evidence are
compared as bytes in the baseline corpus, not only as reachability truth.

## 24. Finite policy evidence

The retained 36-seed raw_matches oracle derives exact edge/port domains, duplicate
same-effect groups, overlap IDs/intervals and no-match rules without compiler
reuse. New extreme-port/parallel cases check the examined-edge universe and
overlap scope. Query intervals and query work remain equal with evidence on/off;
additional work is separate. Combined prospective rejection occurs before
diagnostic enumeration. No global redundancy/removal/counterfactual claim is made.

## 25. Metamorphic test results

| Relation | Precise invariant and allowed differences | Evidence |
| --- | --- | --- |
| Declaration reorder | same canonical typed trace and selected witness | retained seeds plus four new seeds |
| Isolated declarations | same selected concrete-port truth; hash/inventory/work may differ | new isolated asset/interface |
| Additional permit | reachable port set cannot shrink with topology fixed | retained 12 seeds |
| Additional deny | reachable port set cannot grow | retained 12 seeds |
| Equivalent interval coverage | splitting rules preserves concrete truth; IDs/atoms/evidence/work may differ | four new seeds |
| Display text | same truth; canonical hash/witness provenance may change | four new seeds |
| Stable rerun | equal typed exact evidence | new and retained seeds/captures |
| Hash seed | same canonical/stdout/report bytes in distinct processes | 0/12345 captures on both interpreters |

New seeds: 104729, 130363, 155921, 196613. Models have six interfaces, four assets,
at most 31 transitions and 92 rules before splitting; services enumerate eight
ports. A controlled permit edge and all-edge deny on ports 3..4 guarantee exact
mixed truth (reachable 1,2,5,6,7,8), so these relations cannot pass only because
every random route is blocked. All are well within unchanged ceilings. No
unexpected generated failure required a minimized product counterexample.

## 26. Determinism results

The fresh 197-artifact baseline agrees across interpreters and with history.
Additional baseline 123-artifact captures agree across interpreters. Four candidate
captures (3.12/3.14 x PYTHONHASHSEED 0/12345) compare every artifact and exit with
the accepted additional baseline, using distinct output parents. Tests also use
Unicode/spaces filenames, reordered declarations and stable reruns. Legitimate
platform/interpreter provenance remains outside byte comparisons. Deterministic
diagnostics do not include unrelated private exception text. Locale/platforms
beyond these executed environments remain unverified.

## 27. Offline report safety

All five HTML report types receive script/img/event-handler/javascript-link text
in zone/asset/revision/completeness/scenario descriptions. Parsed HTML rejects
active/remote elements and attributes, validates fragment references and observes
CSP; SVG is parsed as XML with declared edge identities. The schema has no free
service-name field; unsafe IDs are rejected through identifier validation.
Existing tests inspect local navigation/markers/clips, headings/captioned semantic
tables, omissions, network denial and JSON appendices. Static CSS/CSP is fixed;
user data cannot become stylesheet content. Runtime source contains no network
or telemetry facility; Python network operations are denied during acceptance.
This hook does not establish a physical air gap or OS-wide network isolation.

## 28. SVG and HTML stability

Existing golden SVG/HTML bytes are unchanged. Raw declaration/geometry oracles
retain exact transport/forwarding edges, endpoint phases, placement versus owner
labels, parallel/reverse identities, no synthetic hops, namespaces and omission
disclosure. No geometry, typography or navigation redesign occurred. Static
responsive/print/focus styles and semantic tables were inspected/tested. Actual
desktop/narrow/zoom/browser/print interaction was NOT_VERIFIED; no local server or
new rendering dependency was introduced. This allowed limitation is nonblocking
for the unchanged presentation contract, subject to owner review.

## 29. Python API compatibility

All production module hashes match accepted source and both installations. This
preserves signatures, dataclass fields/defaults, exception construction and valid
serialization beyond the sampled inventory. New adapter equality checks include
work; immutable snapshot and result binding remain checked by preparation tests.
No incidental private helper was newly exposed. A corpus is finite evidence,
not a promise for arbitrary invalid Python argument objects or forged models.

## 30. Installed CLI verification

Native console launchers come from each active interpreter's sysconfig scripts
directory, never a PATH/module fallback. New native tests cover help, unknown
option, absent value, enum error, empty ID, nonexistent input and repeated scalar
format for all five commands, using Unicode/spaces paths. Existing tests add
missing required scope, destination equality, report-without-format dependencies,
intent exits, resource failures and policy evidence. Public offline examples
exercise minimal/boundary, all three comparison families, trace and report modes.

## 31. Packaging and manifest audit

The two exact manifests add five intended public files: inventory, dossier, two
test modules and capture tool, yielding **117 public files**. No required runtime
data file exists beyond Python modules. Archive allowlist/source-byte/RECORD and
metadata checks pass for staged wheel/sdist; rebuilding the wheel from extracted
sdist produces identical member contents. Manifests use ordinal ordering, avoiding
unrelated reorder churn. No generated output, environment, credentials, private
document, backup, log or archived wheel enters the payload.

## 32. Dependency/license audit

Runtime requirements remain Typer >=0.16,<1, PyYAML >=6,<7, Pydantic >=2.12,<3.
Build/dev declarations, verification pins, Apache-2.0 LICENSE and third-party
notices are unchanged. Metadata and packaged license bytes are audited, and pip
check verifies the installed closure. No upgrade or new mandatory dependency was
needed. No online vulnerability-advisory assessment or independent legal opinion
is claimed; offline license inventory/metadata review is the scope of this gate.

## 33. Windows portability review

Current Windows regular installs use Python 3.12.14 and 3.14.5. Native executable
resolution, UTF-8 subprocesses, Unicode/spaces paths, tempfile close-before-replace,
LF deterministic artifacts, file collisions and controlled write errors are
executed. Input/output operations use Path and os.replace. Filename length,
case sensitivity, ACL behavior on other filesystems and locale variants beyond
the tested environment are not generalized from these observations.

## 34. Ubuntu/macOS CI readiness

CI is byte-identical: Windows/Ubuntu/macOS x Python 3.12/3.14, fail-fast false,
read-only permissions, protected checkout/root checks, regular install/provenance,
Ruff/format/mypy/pip check, offline full suite/examples, archive audit, fixed
benchmarks and unique per-matrix artifacts. push, pull_request and manual triggers
remain: a branch push plus PR can independently run two six-way matrices. That is
an accepted coverage/cost tradeoff, not silently optimized here. New V11-5 hosted
results are PENDING because no commit/push/dispatch is authorized.

## 35. Performance-regression verification

The production preparation/report pipeline is unchanged. Retained deterministic
call-count tests require one validation for check/exposure and two for compare
reports, including files changed after evaluation. No cache was added. The fixed
benchmark uses its unchanged default sample count, 30-second/512-MiB routine
thresholds, and pathological controlled rejections. It runs after each suite and
example/corpus pass; exhaustive V11-4 profiling/capacity sweeps are not repeated.
Timings are local observations; traced allocation is not process RSS.

Python 312: routine maximum **1.241089 s**, separate peak traced allocation **7,392,801 bytes**; runner **PASS**. Complete fixed workload record: `output/gate-v11-5/312/benchmark-results.json`.

Python 314: routine maximum **1.246125 s**, separate peak traced allocation **7,599,713 bytes**; runner **PASS**. Complete fixed workload record: `output/gate-v11-5/314/benchmark-results.json`.

## 36. Documentation/example audit

Reviewed public README, install/release procedures, schema/domain/algorithms,
resource table, reporting/trace, dependencies, limitations, testing and benchmark
documentation, examples and the V11-3/V11-4 dossiers. Local Markdown target paths
resolve across the 117-file public inventory. Historical release/gate reports
remain historical, including their then-pending hosted status. The new inventory
distinguishes canonical UTF-8 from ASCII-escaped evidence and legacy usage errors
from trace JSON. No deployed connectivity, causal attribution, certification,
global redundancy or physical-risk claim is added. Existing synthetic example
models were not edited to make verification pass.

## 37. New tests and rationale

| File/family | New collected tests | Purpose |
| --- | ---: | --- |
| test_release_hardening.py hostile bytes | 20 | controlled repeated failures |
| parser boundaries | 9 | small byte/depth/event admission boundaries |
| denied input read | 1 | sanitized I/O boundary |
| five commands x five report faults | 25 | preserved report/input and cleanup |
| native negative matrix | 25 | exit/stdout/stderr and encoding |
| native help/repeated scalar | 5 | installed option behavior |
| hostile HTML/XML display | 15 | parsed inactive output, exact SVG edge |
| test_release_metamorphic.py seeded relations | 4 | isolation/display/splitting/order/rerun |
| extreme protocol/parallel edge cases | 2 | independent concrete truth/finite evidence |
| adapter equivalence | 1 | file/bytes/prevalidated results and work |
| raw reservation/evidence boundaries | 6 | prospective versus actual work |
| final-review corrupted-trace regressions | 7 | raw-domain independence, exact coverage, duplicate rejection and both truth values |
| Total | 120 | concrete invariants, no count-only expansion |

Existing resource envelope cases additionally assert one unit of headroom.
The initial focused new suite passed **113 tests in 28.89 s**. Final review found
all four new unaugmented random seeds were blocked; the fixtures were strengthened
with the controlled mixed-truth path above. The revised semantic module passed
**13 tests in 2.03 s**. Complete suites were then repeated on both interpreters
because this was an executable test change, retaining the earlier full logs in
`output/gate-v11-5/prior312` and `prior314`. This extra verification addresses an
identified coverage weakness, not a production defect or arbitrary repeated run.
Initial Ruff formatting and strict-mypy complaints concerned only
new test/tool formatting and imported tempfile visibility; they were corrected
without suppressions. No failed product outcome or golden mismatch was concealed.
The five native empty-ID cases were also tightened to reach identifier/scope
validation rather than an unrelated missing-report precondition; the focused
five-case rerun passed before the final complete suites.

## 38. Full test counts per interpreter

| Interpreter | Current full installed pytest | Status |
| --- | --- | --- |
| Python 312 | 1336 passed in 555.04s | PASS |
| Python 314 | 1336 passed in 589.96s | PASS |

Before these two final-review corrections, the full installed suites passed 1,329
tests in 351.76 s (3.12) and 366.66 s (3.14). Those historical results are retained
under output/gate-v11-5/312 and /314. Final-review focused checks pass all **20
tests** on each interpreter, including the unchanged TCP/UDP extreme-port cases;
new full-suite and static-check receipts are retained separately under
output/gate-v11-5/final-review/312 and /314.

Historical V11-4 count is 1,216 on each interpreter; it is not substituted for
the current run. Current suites include retained independent oracles, preparation,
resource, contract, distribution, Unicode, presentation and native subprocess tests.

## 39. Ruff/mypy/dependency results

| Check | Python 3.12 | Python 3.14 |
| --- | --- | --- |
| environment | PASS | PASS |
| ruff | PASS | PASS |
| format | PASS | PASS |
| mypy | PASS | PASS |
| dependencies | PASS | PASS |
| pytest | PASS | PASS |
| examples | PASS | PASS |
| corpus | PASS | PASS |
| benchmark | PASS | PASS |

Exact arguments, exits, stdout/stderr and elapsed wall time are retained per
interpreter under output/gate-v11-5/312 and /314. No unexecuted operation is marked
PASS. Acceptance runs set OTARCHGUARD_OFFLINE_CHECK=1 and tools/offline PYTHONPATH.
For the final-review corrections, installed provenance, Ruff lint/format, strict
mypy, dependency consistency and focused tests were rerun under both interpreters;
their receipts are under output/gate-v11-5/final-review/312 and /314. Fresh native
captures match all 123 accepted artifacts per interpreter, and all 2,320 existing
golden/evidence files retain identical hashes. Example and benchmark rows retain
the earlier executed measurements of unchanged production code; those operations
were not repeated for this test/documentation-only correction.

## 40. Wheel/sdist provenance

Earlier artifacts remain in ignored output/gate-v11-5/candidate-source/output/artifacts.
The corrected final-review candidate uses a separate ignored staging directory,
output/gate-v11-5/final-review/candidate-source/output/artifacts. Artifacts are
named otarchguard-1.0.1.dev5+gate.v11.5-py3-none-any.whl and
otarchguard-1.0.1.dev5+gate.v11.5.tar.gz. Both verification environments use regular
non-editable installs with --no-index --no-deps, workspace-local TEMP/TMP, and
source-module SHA comparison through verify_environment.py. Final archive SHA-256,
size, member hashes and source-byte equality are in **archive-audit.json**; rebuilt
wheel payload hashes are in **rebuild-evidence.json**. Dossier-only final rebuilds
may change archive hashes without changing tested production bytes. Archive hashes
are intentionally recorded externally to avoid self-referential dossier hashes.
The final-review archive/source audit and rebuilt wheel payload evidence are
retained separately in output/gate-v11-5/final-review/archive-audit.json and
rebuild-evidence.json; the consolidated local-only verification receipt is
output/gate-v11-5/final-review/results.json. The manifests retain all 117 public
files, with no membership changes. Only the test module and this dossier differ
from the pre-correction public-file hashes; production and public-contract files
are unchanged. Earlier archive and golden evidence is preserved.
No universal byte-reproducible archive/timestamp claim is made.
Full pytest is run from the authoritative version-1.0.1 checkout against the
regular development wheel. The staging-only dev5 sdist is archive-audited and
rebuilt; its full suite is not independently claimed as executed from that
directory. Version-specific archive fixtures retain the authoritative stable
identity until a separately authorized version transition reviews them.

## 41. Confirmed defects

No confirmed product defect was reproduced by the bounded campaign. The accepted
legacy-versus-trace parser diagnostic difference and legacy ignored report-format
option are observable existing contracts, not changed as cleanup. No Critical or
High issue is being hidden behind a passing Boolean or a removed test.

## 42. Fixed defects

No production fix was needed. The gate adds evidence and documentation only.
New-harness formatting/type issues were fixed and checked; they are not counted
as resolved application vulnerabilities. No existing failing assertion was
weakened and no baseline was regenerated to absorb an unexplained difference.

## 43. Unresolved findings

| ID | Severity/type | Evidence / root cause | Disposition / residual action |
| --- | --- | --- | --- |
| V5-E01 | verification gap | GitHub connector requires reauthentication; historical runs unavailable | owner may review prior hosted runs; fetched ancestry is verified |
| V5-E02 | required future acceptance | new V11-5 branch not committed/pushed | execute six-way hosted CI after owner authorization |
| V5-E03 | known presentation limitation | no actual browser/zoom/print session executed | optional owner smoke review; unchanged bytes, static checks pass |
| V5-E04 | external assessment boundary | no online advisory or fresh-OS dependency review | no vulnerability-free or universal installation claim |

These are evidence/acceptance limits, not newly confirmed Critical/High product
defects with invented reproducers. No approval was requested to alter semantics.

## 44. Deferred high-risk semantic changes

None was required by a confirmed defect. No BFS, tie-break, interval, precedence,
reservation, resource or scope change was undertaken. V11-4 deferred normalization
fast paths, policy caching and broader optimization remain future work requiring
their own evidence/compatibility review; they are not release prerequisites
invented by this gate.

## 45. Known limitations

Declared finite IPv4 TCP/UDP initiation only; no NAT, source ports, session state,
reverse route inference, endpoint relay, application proxy, live inventory,
deployed security/compliance, exploitability or physical-risk determination.
Self-asset trace is unsupported. Diagnostics are bounded frontiers, not unique
root causes. Policy diagnostics examine finite all-declared-edge scopes and may
be expensive. Reports retain complete evidence in memory; input/work rejection
ceilings do not promise a universal RSS/output-size bound. Python 3.13, other
dependency combinations, fresh operating systems, full browser/print behavior
and new hosted OS results are not established by the Windows runs. Trusted local
filesystem/concurrency/durability assumptions remain those in section 19.

## 46. Release-blocker matrix

| Item | Status | Scope / remaining action |
| --- | --- | --- |
| Confirmed Critical defects | PASS | zero found in exercised scope; no universal absence claim |
| Confirmed High defects | PASS | zero found in exercised scope |
| Unauthorized production/contract change | PASS | no production bytes changed |
| Current local acceptance | PASS | see executed checks, compatibility and integrity |
| New six-way hosted CI | PENDING | owner-authorized commit/push/PR/check review |
| Owner independent acceptance | PENDING | review dossier, tests, capture tool and evidence |
| Public RC/version transition | NOT_APPLICABLE | outside V11-5 authorization |

## 47. v1.1 release-candidate readiness checklist

| Category | Required condition | Status | Supporting evidence | Limitations | Remaining action |
| --- | --- | --- | --- | --- | --- |
| Semantic correctness | Independent oracles green | PASS | sections 38-40; per-interpreter logs | Finite tiny models; no universal proof | None locally |
| Supported input | Adversarial validation green | PASS | sections 38-40; per-interpreter logs | Bounded deterministic families | None locally |
| Resource safety | Existing limits preserved | PASS | sections 38-40; per-interpreter logs | No universal memory capacity claim | None locally |
| Public APIs | No unauthorized incompatibilities | PASS | sections 38-40; per-interpreter logs | Source bytes and adapter equivalence | Owner review |
| Native CLI | Commands/exits/diagnostics stable | PASS | sections 38-40; per-interpreter logs | Pinned installed dependency closure | Owner review |
| JSON contracts | Frozen shapes and values preserved | PASS | sections 38-40; per-interpreter logs | Finite artifact coverage plus unchanged source | None locally |
| Trace contract | Version-1 exact evidence preserved | PASS | sections 38-40; per-interpreter logs | No deployed/session meaning | None locally |
| Offline reports | Safe and deterministic | PASS | sections 38-40; per-interpreter logs | Static parsed safety, browser unverified | Optional browser smoke |
| Package provenance | Source/installed bytes verified | PASS | sections 38-40; per-interpreter logs | Regular local installs | None locally |
| License | Apache-2.0 obligations retained | PASS | sections 38-40; per-interpreter logs | Not legal opinion | Retain upstream notices |
| Stable version | v1.0.1 unchanged | PASS | sections 3-7, 31-36, 41-43 | No published asset modified | Separate future version decision |
| Git identity | Independent root preserved | PASS | sections 3-7, 31-36, 41-43 | Remote variable value unqueried | None locally |
| Documentation | Supported claims accurate | PASS | sections 3-7, 31-36, 41-43 | Local path links; historical reports labeled | Owner review |
| Python 3.12 | Local verification green | PASS | sections 38-40; per-interpreter logs | Windows only | Hosted native combinations |
| Python 3.14 | Local verification green | PASS | sections 38-40; per-interpreter logs | Windows only | Hosted native combinations |
| Six-way CI | Configuration preserved; hosted results required | PENDING | section 34; owner handoff | No new hosted execution | Authorized push/CI review |
| Critical findings | Zero unresolved | PASS | sections 3-7, 31-36, 41-43 | Within exercised scope | Owner independent review |
| High findings | Zero unresolved or owner-accepted | PASS | sections 3-7, 31-36, 41-43 | Within exercised scope | Owner independent review |
| Owner approval | Separate review | PENDING | section 34; owner handoff | Uncommitted local work | Explicit acceptance |

## 48. Precise reproduction commands

From the authoritative checkout, use corresponding 314 executables for 3.14.
Existing captures are immutable evidence: choose a new directory for reproduction.
Do not perform the staging version replacement in authoritative pyproject.toml.
Final review is strictly local: do not contact GitHub or any remote Git service.
The following Git commands inspect existing local objects and cached tracking
references only; they do not establish the current state of a remote server.
No remote Git command or connector operation was used for these final-review
corrections. Earlier remote operations described above remain historical facts.

```powershell
git status --short
git branch -vv
git rev-parse --abbrev-ref 'main@{upstream}'
git rev-list --left-right --count main...origin/main
git rev-parse HEAD origin/main
git rev-list --max-parents=0 HEAD
git rev-parse 'v1.0.1^{}'
.venv-verify312/Scripts/python.exe tools/verify_environment.py --output output/environment-check312.json
$env:OTARCHGUARD_OFFLINE_CHECK='1'
$env:PYTHONPATH=(Join-Path (Get-Location) 'tools/offline')
$env:PYTHONUTF8='1'
$env:PYTHONIOENCODING='utf-8'
.venv-verify312/Scripts/python.exe -m pytest -q --tb=short --basetemp=.pytest_tmp/gate5-review312
.venv-verify312/Scripts/python.exe -m ruff check .
.venv-verify312/Scripts/python.exe -m ruff format --check .
.venv-verify312/Scripts/python.exe -m mypy
.venv-verify312/Scripts/python.exe -m pip check
.venv-verify312/Scripts/python.exe examples/run_examples.py
$env:PYTHONHASHSEED='0'
.venv-verify312/Scripts/python.exe tools/capture_contract.py output/review-contract312 --compare output/gate-v11-5/expanded-baseline312/manifest.json
.venv-verify312/Scripts/python.exe -m benchmarks.run --output output/review-fixed312.json
git diff --check
git fsck --full
```

The local ignored driver `output/gate-v11-5/run.py` preserves exact subprocess
argument arrays, exit codes and logs. `baseline` captures the accepted installation
once; `final` runs provenance/static/dependency/full-suite/examples/legacy corpus/
fixed benchmark sequentially per interpreter. `determinism.py` captures the new
corpus under both seeds/interpreters. `audit.py` verifies frozen source/Git/manifest
and local link identities. `build.py --install` copies only the public manifest,
substitutes the staging-only version, builds/audits archives, rebuilds from sdist
and installs regular wheels. These ignored helpers are local evidence conveniences;
the public capture, verification/audit tools, tests and documented commands are
sufficient to reproduce the substantive checks without private inputs.
`recheck.py` preserves the original full-run records, then repeats static checks
and both full suites with the strengthened fixtures and distinct temporary
directories. Those suites run concurrently; the retained benchmark measurements
ran sequentially before this repeat, without concurrent suites. Test-only fixture
changes do not alter the byte-identical production or benchmark source whose
example/corpus/provenance/performance evidence is retained.

For a manifest-only staging directory, build/audit there:

```powershell
python -c "from setuptools import build_meta; build_meta.build_wheel('output/artifacts'); build_meta.build_sdist('output/artifacts')"
python tools/audit_release.py output/artifacts/otarchguard-1.0.1.dev5+gate.v11.5-py3-none-any.whl output/artifacts/otarchguard-1.0.1.dev5+gate.v11.5.tar.gz --source-root . --output output/archive-audit.json
```

## 49. Modified and added file inventory

| File | Change |
| --- | --- |
| docs/v1.1/public-contract-inventory.md | new source-derived interface inventory |
| docs/v1.1/gate-v11-5.md | new 51-section engineering dossier/readiness checklist |
| docs/testing-strategy.md | new bounded capture/reproduction guidance |
| tests/test_release_hardening.py | new 100 adversarial/failure/native/markup cases |
| tests/test_release_metamorphic.py | new 20 independent relation/API/work and corrupted-trace cases |
| tests/test_resource_envelope.py | extra headroom assertion for ten existing dimensions |
| tools/capture_contract.py | new opt-in deterministic installed evidence capture |
| MANIFEST.in | add five intended public files |
| tools/public-files.txt | same exact additions |

Production modules, pyproject.toml, CI, licenses, examples and existing oracles are
unchanged. Generated builds/evidence remain ignored, not public payload files.

## 50. Owner-facing acceptance recommendation

The codebase is locally ready for a release-candidate preparation decision, subject to independent owner review and subsequent hosted native acceptance. This is not a public-release authorization.

Review the two new test files, public capture tool, resource headroom assertion,
contract inventory, manifests and this dossier. Evidence paths above identify
already executed checks; owner review need not rerun every suite. Remaining
authorized-next decisions are independent acceptance, then separately authorized
commit, push, PR, six-way hosted checks, merge and checkout synchronization.
No files are staged and no commit/push/merge/tag/publication occurred.
This final-review session is local-only. Historical remote checks above are not
instructions to repeat them; remote integration and later gates require separate
owner authorization outside this review.

### Explicit local acceptance checklist

- [x] Correct post-V11-4 baseline confirmed.
- [x] Independent root preserved.
- [x] Stable v1.0.1 tag preserved.
- [x] `EXPECTED_ROOT_SHA` untouched.
- [x] Application version untouched.
- [x] Schema 1 untouched.
- [x] Report and trace version contracts untouched.
- [x] Public interfaces inventoried.
- [x] No unauthorized public API changes.
- [x] No unauthorized CLI changes.
- [x] Existing compatibility corpus preserved.
- [x] Any expanded golden corpus independently reviewed.
- [x] All independent analytical oracles pass.
- [x] Metamorphic invariants pass for supported bounded inputs.
- [x] Adversarial YAML cases produce controlled behavior.
- [x] Unicode protections remain intact.
- [x] Resource bounds remain unchanged.
- [x] Prospective resource reservations remain intact.
- [x] Exact TCP/UDP interval semantics remain intact.
- [x] Deny precedence remains intact.
- [x] Witness evidence remains exact.
- [x] Optional policy evidence remains complete.
- [x] Report failure does not corrupt existing artifacts.
- [x] Native exit-code behavior is preserved.
- [x] Fatal diagnostics do not leak private exception detail.
- [x] JSON/HTML/SVG output remains deterministic.
- [x] Offline HTML contains no active or remote resources.
- [x] Diagram edges represent declared transitions only.
- [x] V11-4 validated-snapshot reuse remains effective.
- [x] Fixed performance benchmarks pass without increased thresholds.
- [x] Full pytest passes under Python 3.12.
- [x] Full pytest passes under Python 3.14.
- [x] Ruff lint passes.
- [x] Ruff formatting passes.
- [x] Strict mypy passes.
- [x] Dependency checks pass.
- [x] Installed native CLI examples pass.
- [x] Wheel and sdist audit passes.
- [x] Public manifest exactly matches intended files.
- [x] No private material or generated output is packaged.
- [x] CI six-way matrix remains intact.
- [x] No unexecuted hosted CI result is claimed.
- [x] Confirmed Critical findings are resolved or explicitly block acceptance.
- [x] Confirmed High findings are resolved or explicitly disclosed.
- [x] Complete Gate V11-5 engineering report exists.
- [x] Release-candidate readiness matrix is complete.
- [x] No commit, push, merge, tag or publication occurred.
- [x] No Gate V11-6 implementation was begun.

New hosted results and independent owner review are explicitly pending in section
47; they are not checked as completed by the local acceptance checklist.

## 51. Requirements for subsequent Gate V11-6

Begin only under separate owner authorization after reviewing this uncommitted
gate, approved integration and all required six-way native checks. Confirm final
source/archive provenance, branch-protection names and root/tag constraints;
resolve any newly discovered blockers. Make the public version/RC/tag/release
asset decision explicitly and auditably at that later gate. Nothing in V11-5
authorizes publication, signing, promotion to 1.1.0/rc1, stable-asset replacement,
changelog finalization as a release or starting V11-6 implementation.
