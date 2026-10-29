# V14-03 independent semantic and security audit

Date: 27 October 2026. This audit evaluates the locally integrated V14-03
implementation against the master directive. It is a focused independent review,
not a substitute for the integration owner's full distribution, performance and
hosted-CI acceptance receipts.

## Evidence examined

The review covered the final `drift/contract.py`, `engine.py`, `comparability.py`,
`communications.py`, `protocols.py`, `architecture.py` and `reports.py`, their
historical lifecycle boundaries, the fictional walkthrough, and the new
architecture, security, adversarial, observation and alignment tests.

The branch is `codex/v14-03-historical-drift-analysis`, based on
`b25347494a74fb0b2952b11c4cbb69b0a9eb75d6`. At audit time, implementation changes
were initially uncommitted and HEAD still identified that base. The integration
owner subsequently froze the reviewed runtime in local commit
`1750f275b0808380ef942184f40cf6a8ba2d5402`. A targeted
`git diff --exit-code` confirmed no changes from that base in native model APIs,
domain records, normalization, reachability, existing architecture comparison,
capture reconciliation, protocol decoders, lifecycle/history/validation,
revision/review/attachment/observation/workspace consumers, or frozen
`capture-contract-v2` fixtures. The frozen `v1.3.0` tag still peels to
`10d7de6c416ec6f0ee364c671ebe9292ee69e672`.

The final focused command was:

```text
python -m pytest tests/test_drift_architecture.py tests/test_drift_security.py tests/test_drift_alignment.py -q --basetemp .pytest_tmp/drift_final_independent_audit --tb=short
```

With the repository `src` selected explicitly, Windows Python 3.14 completed
**70 tests, 70 passed, no failures/errors/skips, in 26.43 seconds**. These include
the 25 architecture and 27 security cases previously executed by this reviewer;
those 52 overlapping cases are not additional unique tests. The final alignment
run also exercises malformed self-hashed summaries and reproduction after later
unrelated proposals/reviews. Earlier architecture/native reachability/oracle/CLI
verification passed 127 cases. Focused Ruff lint, format checks and strict mypy
over the drift package and this reviewer's two test modules passed.

No full-suite, wheel/sdist, benchmark or six-platform success is claimed by those
focused results. Their actual receipts belong in the consolidated acceptance
handoff. The existing six-job OS/Python matrix remains present; the inspected CI
diff adds installed drift walkthrough execution/artifacts without removing gates.

## Findings and corrections

One confirmed integrity defect was found during independent testing:
`publish` verified an internally cloned report but subsequently serialized the
original caller-owned object. Mutation at the final source-check boundary could
therefore publish content that had not been replayed. The integration owner
corrected publication to take an owned defensive copy before validation and
publication. The adversarial mutation regression now passes and verifies the
published file against the unchanged expected report.

An integration defect in newly authored native evidence was also corrected:
dataclass conversion retained tuples, whereas report inputs require exact JSON
primitive types. Native query evidence is now converted to JSON primitives before
entering a report, and an exact-clone regression covers the nested representation.
Neither correction changes frozen producer semantics.

Native assessment work is conservatively reserved across both models and both
state/rule counters before evaluation; nested evidence references and bounded
representative summaries are accounted. Resource failures abort the operation.
These are finite rejection budgets, not measured RSS or latency guarantees.

No unresolved integrity, authorization-state or semantic correctness defect was
identified in the final inspected runtime. Performance/distribution acceptance
remains dependent on its separately executed evidence, rather than on that result.

## Non-negotiable review questions

| # | Assessment and practical limit |
|---|---|
| 1 | Physical capture SHA, analytical revision ID and review ID remain distinct. Two interpretations of one capture are one collection; no independent corroboration is invented. |
| 2 | Normal public comparison validates the full lifecycle and requires the exact baseline's effective approval and introducing review. No latest-baseline selection exists. |
| 3 | Revocation and supersession reject fresh current-reference comparisons/publication. Existing reports replay their recorded graph and separately disclose current authority. Both cases have passing regressions. |
| 4 | Exact decoder equivalence is required for protocol-category comparisons. Revision 1 versus 2 becomes analytical interpretation, including on the same physical capture. |
| 5 | Directional raw header relationships and bounded aggregate observations are compared. Conversation groups and native initial-SYN evidence do not become reconstructed TCP sessions. |
| 6 | IP/MAC equality does not establish a device. Asset annotations require independent ACCEPT decisions with equivalent asset/interface declarations in one exact model, and retain unauthenticated continuity limitations. |
| 7 | Canonical native collections support exact-ID additions/removals/field changes. Formatting/order produces no delta. Renamed labels produce added/removed declarations, without heuristic asset matching. |
| 8 | The native evaluator and its engine identity remain unchanged. Explicit equivalent queries use native peer partitions; changed query semantics, missing origins/services and self-asset queries abstain. |
| 9 | Seven-family protocol fields remain categorical header metadata. Write-type recognition, secure opaque messages and link CRCs do not establish execution, success, authorization or authenticity. |
| 10 | Reference-only/candidate-only means a finite dataset observation difference. It never establishes blocking, an outage, removal or a network-wide absence. |
| 11 | Container/packet interpretation, framing, linktypes, scope, vantage points, visibility and exact observed time bounds are explicit dimensions. Missing/changed coverage reduces comparability; clocks, collection gaps and loss remain unverified. |
| 12 | Declared architecture, observed communications, native model assessment, analytical interpretation and coverage remain separately typed. Changed models are not proof of changed deployment. |
| 13 | Findings carry exact source identities and bounded flow/packet/component references, with omitted counts where samples are limited. Full source support remains in validated original artifacts. |
| 14 | Verification reconstructs results through the supported lifecycle and recorded review graph and requires exact canonical equality. A self-consistent report hash alone grants no authority. Dependencies and the exact supported implementation must remain available. |
| 15 | Per-dimension consequences, domain statuses, abstentions and unsupported interpretations are retained. The overall state may remain indeterminate even when a narrow metadata domain is comparable. |
| 16 | Rehashed findings/counts/approval/source/implementation attacks, invalid joins, missing dependencies, stale authority, path attacks, interrupted writes and malformed JSON have controlled rejection tests. Self-consistent false original metadata cannot be authenticated without outside evidence. |
| 17 | Revision/collection/key/finding/record/reference/query/work/output ceilings are enforced; caller limits can only narrow them. Source lifecycle ceilings are preserved. No guaranteed machine-memory or response-time limit is claimed. |
| 18 | Targeted baseline diffs confirm preserved historical source bytes and frozen fixtures. Complete compatibility acceptance additionally depends on the owner's full installed-suite receipts. |
| 19 | Operation-private lifecycle acquisition and reuse remain intact; frozen optimized historical consumers are unchanged. Actual retained-performance claims require the final paired V14-02P regression measurements; this audit does not infer speed from source equality alone. |
| 20 | Focused verification passed. Full source/wheel/sdist suites, exact installed-module identities, packaging audits and dependency checks require their actual final receipts before local milestone acceptance. |
| 21 | V14-04 has validated offline report/inspect/verify interfaces, source IDs, domain records, comparability matrices, bounded references and current-versus-recorded authority. No historical Explorer is implemented. |
| 22 | Supported behavior and limitations are explicit in the technical contract. Optional historical creation against revoked references and an ordered-series feature are not implemented; existing historically generated reports remain verifiable after authority changes. Neither optional feature is needed for the implemented normal approved-baseline workflow. |

## Acceptance gates A–N

| Gate | Independent audit disposition |
|---|---|
| A — Historical contracts | Targeted source/fixture preservation confirmed. Full historical installed regression evidence is an integration acceptance dependency. |
| B — Comparability | Implemented with per-dimension sources/reasons/consequences and explicit domain states. Strict mode gates communication scope/coverage; it does not certify all domains or provenance. |
| C — Communications | Directional finite-capture differences, metadata aggregation, raw counts and bounded references are implemented. No physical continuity or session-completion inference. |
| D — Architecture | Validated canonical native record comparisons implemented, without formatting deltas or invented native entities. |
| E — Native assessment | Explicit paired equivalent declared queries reuse the unchanged evaluator. Existing capture-native artifacts are compared only within equivalent reviewed same-model scope; unsupported results abstain. |
| F — Industrial protocols | All seven supported families participate under exact decoder/consumer equivalence and supported privacy allowlists. No decoding expansion. |
| G — Review authority | Current exact approval enforced; revocation/supersession, no candidate inheritance and historical/current separation tested. |
| H — Uncertainty | Coverage/sensor/identity/clock limitations remain explicit. Descriptive one-sided records never become operational absence claims. |
| I — Persistence | Standalone versioned canonical report, exact replay, fresh external output and atomic no-overwrite publication implemented. Workspace-v2 categories are unchanged. |
| J — Security | Independent focused attack campaign passes after the publication-mutation correction. Assumes local single-writer use; signatures, authenticated reviewers and privileged filesystem races are outside the established contract. |
| K — Performance | Bounded implementation and benchmark harness reviewed. Final measured drift scaling and paired historical regression receipts must establish this gate. |
| L — Distribution | Six-platform matrix preserved and drift walkthrough added. Final local wheel/sdist/source inventories, suite results and dependency checks must establish this gate; hosted V14-03 CI is unexecuted until owner publication. |
| M — Reproducibility | Literal fictional wire/model oracles, independent domain-separated hash calculation, byte-identical repeats, source-preservation and historical replay tests are present. Exact installed walkthrough receipt is an integration dependency. |
| N — Scope integrity | Passive offline metadata/model comparison only. No incident detection, active OT execution, deployment validation, attribution or industrial safety certification. |

## Interpretation and downstream constraints

The public authority-bearing APIs are `drift.engine.compare` and the report
generate/publish/verify/inspect workflows over a real validated workspace.
`Side`, normalization helpers and native comparison helpers are internal
operation-owned representations; constructing one does not bypass lifecycle
validation in a public report workflow. `read_report` and `summarize` alone do
not authenticate sources or establish current approval. The CLI inspection and
summary workflows verify source reproduction before presenting results.

Frozen native capture reconciliation remains limited to reviewed, decoded IPv4
TCP observations with unique initial-SYN direction and exactly representable
origins/listeners. Arbitrary UDP, midstream TCP, fragments, IPv6, ARP and unresolved
or ambiguous identities do not gain positive native conclusions. Declared native
queries are a separate model-only operation and retain native TCP/UDP semantics.

Matching scope/vantage labels are explicit user assertions, not authenticated
sensors. Capture metadata does not attest original collection parameters, packet
loss, continuous exposure or the truth of imported capture hashes. Observed
rational timestamp bounds support ordering of the selected reported windows,
with unverified clocks and gaps; they do not justify rates or trends. Review
labels do not provide organizational PKI. Report hashes bind context and content
but are neither signatures nor proof of historical creation time.

V14-04 consumers must distinguish unchanged support records from differences and
abstentions, and recorded approval from current approval. A reproducible report
can legitimately have `currently_approved_reference: false`. A future engine
change requires an explicit compatible historical reader; this implementation
does not silently reinterpret reports from different source semantics. Source
dependency loss fails closed. None of these constraints should be hidden by a
future visualization.
