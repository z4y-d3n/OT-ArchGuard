# GATE V12-04: Multi-source architecture reconciliation

This gate implements local Import Projects on the accepted V12-03 source. The
exact final verdict, commit, public-file digest, artifact identities, test counts
and timings are bound in ignored `output/v1.2-development/v12-04/final-01/acceptance.json`.
The public source does not hash its own acceptance receipt. Published v1.1.0 and
all prior acceptance evidence remain recoverable and unchanged.

## A. Baseline and Git

The clean starting branch was `codex/v12-03-graph-evidence`, HEAD
`a35ac92fe271b4547410bfe30b842b0dd57a4e55`. Its canonical public-source identity
matched `3e4c6295d747a1a8c7f17778aa9e72c394c4462aec945565b27653091bfa6f48`.
`main`, both annotated historical tag objects, stable source tree and original
independent root matched the attached gate requirements. Initial environment,
references, prior acceptance hash and full public-file inventory were recorded
before creating `codex/v12-04-multisource-reconciliation`. No owner changes existed.

## B–D. Implementation, usability and security

The [six ADRs and complete contracts](v12-04-projects-and-reconciliation.md) specify
manifest/draft/decision version 1, reusable accepted adapters, source-qualified
catalog identities, exact indexed proposals, explicit owner partitions, conflict
fields, source preferences, reference corrections, resource ceilings, privacy,
stale-review reproduction, native validation and atomic no-overwrite publication.

The actual CLI is `otarchguard import project` with `init`, `inspect`, `preview`,
`map`, `review`, `resolve`, `acknowledge`, and `emit`. Existing single-source
commands retain their versions/behavior. One manifest orchestrates all sources.
Markdown puts conflicts before otherwise complete candidates; `--group` inspects
one proposal. `resolve` replaces exact explicit partitions and resets whole-model
confirmation. Safe connector acknowledgment binds one source's exact member set,
count, digest and rationale, without approving any entity or communication.

The [complete beginner walkthrough](../../examples/import-studio/projects/README.md)
registers CSV metadata, XLSX inventory/zones, JSON interfaces, draw.io nodes/edges
and explicit native context, then emits six reconciled assets with provenance.
It demonstrates a contradictory zone, preferred evidence as a suggestion, an
explicit selected field, named identity/model decisions and evidence-only edges.
JSON + GraphML and XLSX + draw.io variants are independently integration tested.

Remaining friction is deliberate: partitions and conflict/model rationales still
require engineering decisions; there is no interactive editor or fuzzy identity
guessing. Exact aliases can be reused as configuration, never as stale approval.
Selected documentary metadata remains sensitive. Per-field provenance imposes
finite byte/event ceilings; incomplete graph-only mappings can hit the inherited
diagnostic ceiling before project-level limits.

## E. Verification

The final run executes full installed-wheel suites on available Windows Python
3.12.14 and 3.14.5, focused ingestion/review suites on separately installed sdists,
Ruff, formatting, strict mypy, dependency checks, exact distribution audits,
installed module identities and the native console walkthrough in all four
environments. JUnit totals and exit codes in the final receipt are authoritative;
preparation results do not accept the frozen source. New tests cover project
schemas, mixed workflows, mutations, ordering/relocation, owner partitions,
reference renames/rejections, adversarial controls, path aliases, budgets, dense
duplicate labels, exact acknowledgment and partial-output refusal.

Native validation, state-graph construction and exact tracing independently prove
that matched identities, IPs and diagram arrows leave reachability ungranted.
Graph groups cannot declare zones without an explicitly confirmed zone candidate;
inventory and firewall labels cannot invent routing, forwarding or allow/deny rules.
All original engine contracts remain authoritative. Runtime network-denial guard
probes and inherited subprocess enforcement accompany final verification.
Preparation failures and corrections remain in ignored evidence rather than
being counted as successful acceptance.

## F. Performance

`benchmarks.projects` records small, medium, larger and dense-label samples,
per-source/aggregate mapping, draft serialization/validation, emission, template
and sidecar sizes, candidate/proposal/conflict/connector counts, throughput and
determinism. A separate tracemalloc sample records Python allocation peak.
The final performance JSON supplies actual measurements on installed code.
Indexes produce one group per duplicated key; no giant pairwise similarity matrix
exists. Rich retained per-field evidence and JSON serialization dominate space.
Documented ceilings are rejection limits, not general scalability guarantees.

## G. Cross-platform CI

The six existing native Windows/Ubuntu/macOS × Python 3.12/3.14 combinations remain.
Local workflow changes add JUnit receipts, installed-sdist module/console identity,
focused project/adversarial tests and the outside-checkout project walkthrough.
The offline runtime guard remains enabled on all platforms. Provisioning is
separately allowed to obtain approved CI dependencies. No new dependency is added.
WSL probing found no installed subsystem; no Docker/Podman runtime was available.
Hosted platform combinations are NOT EXECUTED in this task. Local Windows success
and reviewed workflow YAML do not prove Ubuntu/macOS compatibility.

Stable v1.2.0 release readiness remains BLOCKED until all six actual hosted runs
pass on the final release candidate, with run/commit/OS/Python, tests/skips,
artifact/install identities and guard evidence, plus separate publication approval.

## H–K. Integrity, verdict, next gate and publication boundary

The final frozen public manifest and changed-file inventory bind every retained
public file. Fresh wheel/sdist audits enforce the exact allowlist and source
bytes. Four noneditable isolated installations verify every production module,
package/console version and artifact hash. The sanitized review ZIP retains the
approved source/test selection, never private evidence or bytecode. Exact hashes
and the selected PASS/PARTIAL/BLOCKED/FAIL verdict live in final acceptance.

Architecture Explorer (V12-05) is not implemented. Its prerequisites now include
stable observation/candidate/group anchors, many-to-one final IDs, original source
locations, field transformations, rejected alternatives, owner resolutions,
evidence-only graphs and native model identity. A future static view must keep
observations, declarations and analytical conclusions visibly distinct, and must
redact sensitive metadata appropriately rather than rendering imported HTML.

No remote push, PR/merge, CI dispatch, main rewrite, tag movement, release/PyPI
publication, new dependency download, live industrial/vendor access, cloud source
processing or stable v1.2.0 publication is authorized or performed here.
