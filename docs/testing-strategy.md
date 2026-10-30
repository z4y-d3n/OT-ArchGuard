# Verification strategy

## V1.4 release-candidate evidence

For the public-documentation pass, the owner reports that checkpoint
`5c70ae09904687070ecce9374546aff8ae806588` on Draft PR #24 passed all six hosted
jobs. That supplied report is not a new remote query or acceptance of the later
documentation commit. The [documentation handoff](development/v14-06-public-documentation-es.md)
records focused local onboarding, link and source/package checks, plus the
outstanding genuine browser capture. The earlier engineering evidence follows
with its original source identities.

The current local candidate distribution/CLI is `1.4.0`; native engine and the
historical `__version__` alias remain `1.3.0`. The exact V14-05 parent
`ac893bc3174f0a7ace67454d19ad6e61116425af` passed
[push run 40880668115](https://github.com/z4y-d3n/OT-ArchGuard/actions/runs/40880668115),
six Windows/Ubuntu/macOS × Python 3.12/3.14 jobs. Candidate results, actual skips
and exact package identities belong in the
[V14-06 handoff](development/v14-06-handoff-es.md); parent results do not validate
the child source or the eventual integrated release source.

At candidate freeze, run the complete suite once against the frozen source and
again using independently regular-installed wheel and sdist payloads. Keep
interpreter/import paths, exact module hashes, unique collection counts,
PASS/FAIL/ERROR/SKIP, durations and source identity with each receipt. Repeated
wheel/sdist/source executions overlap and are not additional unique tests.
Run focused adversarial/native/protocol/history checks during development;
rerun broader acceptance when a material subsequent change invalidates it.

The legacy verifier retains independent immutable native-v1.2 and V14-04 pins.
The final transition permits only the reviewed `1.4.0.dev1` → `1.4.0` distribution
literal in the exact approved source. Approved-reference and candidate installed
identities are checked separately. All other module bytes/inventories, native
semantics, canonical evidence, HTML appendices and reviewed historical assertions
remain fail-closed. Test forged digests and matched-but-forged outputs as well as
ordinary corruption; agreement between two modified modern copies is not proof.

Historical analytical revisions independently bind exact producer source. A
distribution source change does not authorize rewriting their hashes or approval
chains. Test the explicit [development-workspace upgrade boundary](installation.md#historical-workspaces-and-upgrade).

After committing the complete reviewed public inventory, rehearse four-asset
assembly with `python -m tools.prepare_release --output NEW_DIRECTORY` and reopen
it with `--verify`. Confirm clean source, exact commit/tree, audited wheel/sdist
members, installed payload equality and all three checksum entries. Do not claim
byte-identical archives unless a separate build comparison demonstrated it.

V14-04 semantic HTML already received owner visual acceptance, including high-zoom
inspection. Unchanged renderer bytes let that acceptance remain relevant; static
link/markup checks do not establish a new browser, keyboard, focus or print review.
Changed presentation requires targeted renewed owner inspection.

## Published v1.3 baseline and common verification

The published v1.3.0 source is `10d7de6c416ec6f0ee364c671ebe9292ee69e672`.
Its [release integration CI](https://github.com/z4y-d3n/OT-ArchGuard/actions/runs/40273411275)
passed all six Windows/Ubuntu/macOS × Python 3.12/3.14 configurations. Each
installed-wheel and installed-sdist suite reported 2,815 tests with zero failures,
errors or skips; counts overlap. The final PCAP Evidence Explorer's second real
human browser review passed all six criteria. See the
[release notes](release-notes-1.3.0.md) for that evidence and its limits.

A later documentation or implementation commit requires its own relevant checks
and exact source binding. Published-release CI is not a new execution against that
later commit. Keep source/package hashes, installed import paths, command exits
and raw results together; do not silently update a baseline to make a failure pass.

The current workflow uses native Windows, Ubuntu and macOS runners with Python
3.12/3.14, `fail-fast: false` and no exclusions. PowerShell Core is explicit on
every runner. It builds/audits exact distributions, verifies regular installed
wheel and sdist suites, denies Python network operations in test children, checks
native compatibility and frozen capture consumers, and executes fictional
walkthroughs and benchmarks. Integrity artifacts have 30-day retention;
benchmark artifacts have seven-day retention. The workflow does not publish a
release. Verify [.github/workflows/ci.yml](../.github/workflows/ci.yml) and the
actual run before reporting results.

Architecture Explorer tests cover parsed site/link/resource audits, hostile
native/documentary labels, provenance tampering, output budgets, semantic
landmarks, contrast, deterministic relocation and real installed-console cases.
`python -m tools.explorer_walkthrough --output NEW` runs the shipped fictional
example with the installed distribution; choose an output outside the checkout.
`python -m benchmarks.explorer --output NEW.json` measures bounded sites with
separate allocation samples.

The original V11/V12 gates retain their historical results, including blocked
`file://` automation and then-pending hosted/browser checks. They do not imply
completed manual acceptance of every Architecture Explorer, quality or native
report view. PCAP browser acceptance is separate; static structure/raster checks
do not establish general zoom/focus/print/screen-reader behavior or certification.
Version 1.0.1 measurements remain in the [historical summary](verification.md);
[Gate V11-6](v1.1/gate-v11-6.md) records the later v1.1 history.

After a regular install, run `python tools/verify_environment.py --output
output/environment.json` to verify distribution metadata, actual import location,
all production module hashes and the console from `sysconfig.get_path("scripts")`.
POSIX uses `otarchguard`, Windows uses `otarchguard.exe`; neither assumes it is
beside `sys.executable`.

~~~powershell
New-Item -ItemType Directory -Force output | Out-Null
.\.venv\Scripts\python.exe -m pip install -r tools/verification-requirements.txt
.\.venv\Scripts\python.exe -m pip install --no-build-isolation --no-deps .
$env:OTARCHGUARD_OFFLINE_CHECK='1'
$env:PYTHONPATH=(Join-Path (Get-Location) 'tools/offline')
.\.venv\Scripts\python.exe -m pytest --basetemp=output/pytest --tb=short
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m mypy
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe examples/run_examples.py
~~~

The opt-in Python audit hook denies network operations in tests/child CLIs;
it is verification tooling, not a runtime dependency or physical air gap.

Raw-declaration tiny-graph/per-port oracles independently model states, selectors
and deny precedence. They do not use production graph, partition or decision helpers.
Independently inspect every witness against raw endpoints, edge/state continuity
and permits. Fixed seeds cover cycles, missing permits, denies and protocol separation.

Concrete-port set oracles verify interval union/difference/intersection and small
comparisons. Check identity/reversal, stable IDs, renames, changed definitions,
selector expansion, criticality and independent requirements/prohibitions.
Never alter expected outcomes merely to agree with production.

Exercise strict scalars, duplicate keys/IDs, unsupported features, invalid references,
placement and exact byte/event/depth/entity/association/atom/work budget boundaries.
A rejected analysis must never become successful unreachability.

Run native installed launchers with paths containing spaces. Verify stdout/stderr,
exit 0/1/2, atomic preservation, deterministic reordered/repeated reports, escaping,
static offline markup, hash binding, summary manifests, card containment and exact
state anchors. Parsing/rasterization is distinct from browser rendering.

Release audits compare every allowed packaged source/test/document byte against
the candidate, check metadata/entry points/licenses, and rebuild from the sdist.
Packaging regressions cover unexpected, missing and stale archive contents.

Independent SVG oracles compare parsed geometry with raw declarations: containment,
intersections, bounds, phases/endpoints, direction and parallel/reverse identity.
Fixed-seed graphs, exact summary boundaries and deliberate corrupt-SVG checks
exercise these oracles. HTML checks unique IDs, resolving local links/markers/clips,
captioned tables, escaped hostile labels and prominent critical findings.
Record raster observations separately from actual browser/print verification.

## Gate V11-5 contract captures

The [public inventory](v1.1/public-contract-inventory.md) records the accepted
module signatures, native options, result fields and diagnostic differences.
The [hardening dossier](v1.1/gate-v11-5.md) records historical local evidence and
the separate hosted/owner acceptance boundary.

After `tools/verify_environment.py` confirms the regular installed package, capture
the bounded additional corpus with a fresh output directory:

~~~powershell
python tools/capture_contract.py output/contracts-before
python tools/capture_contract.py output/contracts-after --compare output/contracts-before/manifest.json
~~~

The tool captures 45 native cases, including help/parser misuse, all five report
commands, exact trace outcomes, optional policy evidence and preserved failure
sentinels. It records input/model/module identities, exits and artifact hashes.
Existing captures are never overwritten. Comparison requires equal source-module,
input/model, exit and artifact records; interpreter/platform provenance stays
separate. It never updates a baseline to accommodate a failure. Use fixed
`PYTHONHASHSEED` values 0 and 12345 for separate deterministic process captures.
The earlier 197-artifact corpus remains separate local historical evidence.

For the intentional 1.0.1 to 1.1.0 transition, the historical developer capture
example below uses retained gate-local artifacts and the separate narrow comparator:

~~~powershell
python tools/compare_versioned_contract.py output/gate-v11-6/baseline123 output/gate-v11-6/candidate123-312 --output output/gate-v11-6/compatibility123-312.json
~~~

`capture_contract.py --compare` remains an exact same-version comparison. The
version-aware tool permits only root `/engine_version`, that field in the exact
HTML JSON appendix and the exact trace header engine value. It compares all
remaining bytes, including canonical JSON/SVG, and verifies capture hashes,
input/model identities and exits. Interpreter/platform and the central version
module hash are provenance fields checked separately by the gate's source and
installed audits. It never rewrites baseline files or drops arbitrary version
keys. V11-6 preserves a fresh pre-version baseline separately from candidates.

The added hardening tests use bounded inputs and precise report faults; the
metamorphic seeds are 104729, 130363, 155921 and 196613. Their raw-declaration
oracle enumerates only ports 1..8, or six selected boundary ports. Equivalent
rule splitting, isolated additions and display changes preserve concrete truth;
they need not preserve hashes, work, evidence groups or atom boundaries.
Each new seeded relation includes a controlled permit/deny path with both
reachable and unreachable ports, so an entirely blocked random graph cannot
make every transformation pass without exercising permitted communication.

## V12-06 documentary and compact-site verification

`tests/test_ingestion_documents.py` covers four restricted formats, exact runs/lines/
slides/cells, explicit mapping, evidence-only acknowledgment, mixed-source conflicts,
stale decisions, inert hostile content and ZIP/XML attacks.
`tests/test_explorer_compact.py` covers grouped record/nested-anchor preservation,
hash bucket stability, material medium-workload compaction and byte determinism.
Existing Explorer tests resolve documentary paths through the version-2 location
index; native analytics and standalone reporting regressions remain unchanged.

`benchmarks.documents` records three timing samples and separate allocation/profile
measurements. The exact old Explorer workloads are compared against a preserved
V12-05 installation. Final installed wheel/sdist, module hashes and offline console
walkthroughs bind the current source; preparation runs cannot accept later changes.
At that original V12-06 gate, browser file-origin automation was blocked and
real browser behavior was NOT EXECUTED. That historical result remains distinct
from structural checks and the later PCAP-specific human acceptance.

## V12-07 quality and architecture comparison

The additive `quality` and `compare-architecture` commands assess explicit
model-bound requirements and native/documentary/owner changes. Exact comparative
reachability comes only from explicit before/after native trace evaluation.
Missing evidence is not a vulnerability; changed scope never resolves a finding.
Selected evidence, external owner information and native declarations remain
separate. Split/merge and fuzzy identity inference are unsupported.
See the [seven ADRs](development/v12-07-quality-and-comparison.md) for versioned schemas,
coverage denominators, query comparability, resource ceilings, compact offline
views, installed-console tests, reproducible benchmarks and independent local,
PR, hosted-CI and owner-review acceptance. The original V12-07 file-URL automation
attempt was policy-blocked; static checks do not establish WCAG certification.

## PCAP evidence and final UX regressions

Capture tests independently construct binary containers and challenge header
decoding, metadata bounds, ARP sender/target semantics, malformed/unsupported
evidence, exact timestamps, hashes, owner-decision freshness and native-query scope.
Frozen JSON consumers verify evidence versions independently of presentation.

`tests/test_capture_display.py`, `tests/test_capture_views.py` and
`tests/test_capture_ux_integrity.py` cover exact readable UTC, summary denominators,
structured fields, meaningful links, contextual/dense pagination, unique anchors,
escaping, CSP, deterministic bytes, denied sockets and no-clobber publication.
Keep `tests/test_product_presentation.py::test_trace_documentation_qualifies_completed_queries`:
the README exit-code section must state that Trace exit 0 includes unreachable
results and does not assert that every flow was permitted or assess intents.

From the verified source tree with its regular installed console:

~~~text
python -m tools.capture_walkthrough --output output/capture-verification
python -m tools.read_capture_evidence tests/fixtures/capture-contract-v2/supported
python -m tools.read_capture_evidence tests/fixtures/capture-contract-v2/limited
~~~

Create output parents and use fresh destinations. The capture walkthrough uses
fictional data and explicit fixture-author decisions, not real owner approvals.
The corpus and its finite interoperability limits are documented in the
[PCAP guide](pcap-evidence-studio.md#capture-corpus-and-use-policy).
