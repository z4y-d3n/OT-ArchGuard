# V14-06 — native compatibility and analytical assurance (Agent A)

## Result and scope

No substantiated P0/P1 native analytical defect was found in this investigation.
No production module or native contract was edited. Five focused release
counterexamples were added in `tests/test_v146_native_audit.py`; they supplement
the existing independent raw-declaration/path oracles rather than replace them.
This is internal engineering assurance, not proof of correctness for all inputs.

Parent: `ac893bc3174f0a7ace67454d19ad6e61116425af`. Investigation ran on the local
V14-06 branch before the distribution-version transition. Its installed Python
3.14.5 package was a regular installation under
`.venv/Lib/site-packages/otarchguard`. A complete hash/inventory comparison of its
97 Python modules matched `output/v146/parent-identity.json` exactly. The final
integrator must rerun candidate/package acceptance after changing version bytes;
this pretransition result alone does not verify the final installed candidate.

## Frozen contract inventory

| Contract | Identity and semantics | Consumer / unsupported boundary |
|---|---|---|
| Native YAML | Schema 1; exact primitive types, explicit IPv4 TCP/UDP declarations; canonical UTF-8 sorted JSON; closed port unions | `api`, `loading`, `domain`, `validation`, `normalization`; unsupported semantics abort with an error |
| Graph | Explicit directed interface states: transport egress→ingress; forwarding ingress→egress on a boundary device | `graph`, `reachability`; no application pivot, implicit relay, inferred reverse edge or session completion |
| Policy | Original source and service-bound destination; every traversed edge needs an allow and no matching deny; rule order has no authority | `policy`, `intervals`; exact 1–65535 inclusive domain; disjoint interval atoms, no individual-port expansion |
| Intents | Independent required/prohibited quantified scopes; every required port must be reachable and every prohibited port unreachable | `intents`; partial reachability can fail either kind; conflicting overlapping intent declarations are rejected by validation |
| Witness | Canonical model hash, source, destination, service, protocol, exact atom interval and every edge/endpoint/rule/conduit identity | `reachability.replay`; different revision/hash or altered evidence cannot inherit another model's witness |
| Native report | Report/schema 1; deterministic sorted LF-terminated JSON; model-bound result; engine 1.3.0 | `reporting`; mismatched snapshot/result is rejected, structural validation does not imply evaluated intents |
| Trace | Trace/schema 1; exact selected source/service; engine 1.3.0; `intents_assessed=false` | `trace`, `trace_reporting`; missing scope is invalid, self-asset queries unsupported, no whole-model intent assertion |
| Limits | `RESOURCE_LIMITS` and prospective query reservations followed by charged work counters | Resource exhaustion raises `resource_limit`, never an unreachable or successful result |
| Distribution | Package/CLI identity may advance to 1.4.0; historical `__version__` remains native engine 1.3.0 | Metadata migration must not alter canonical native results, HTML or analytical source inventory |

All 18 inspected contract/engine/report files retained their exact parent bytes
when inspected: `docs/yaml-schema-v1.md` plus `contract.py`, `api.py`, `loading.py`,
`domain.py`, `validation.py`, `normalization.py`, `intervals.py`, `graph.py`,
`policy.py`, `reachability.py`, `intents.py`, `exposure.py`, `comparison.py`,
`policy_evidence.py`, `trace.py`, `reporting.py`, `trace_reporting.py` under
`src/otarchguard/`. Their individual baseline hashes are in the immutable parent
snapshot. The schema document and `contract.py` additionally matched the v1.2
pin `f52c792b683cb499dc7de765b65b5cc897a96854` byte for byte:

| File | SHA-256 |
|---|---|
| `docs/yaml-schema-v1.md` | `a9fc6c96fbe0b91596516d4818a53edd5c9504611a142bcd152a7880460ebcf9` |
| `src/otarchguard/contract.py` | `7f423951e67f8583a4d71dc4ffa5812eb866e6b4244b1f605f9c613662d515ef` |

The approved-presentation reference remains
`117318393ead604a023a24bad7d53eb429faa13f`. This audit did not repin or weaken
the compatibility verifier. Exact installed historical-output reproduction is a
separate integrator acceptance gate.

## Independently checked invariants

The new full-domain fixture declares one explicit link, allows 1–65535 and denies
exactly 1 and 65535. Its literal expected result is three atoms:
`[1,1,false]`, `[2,65534,true]`, `[65535,65535,false]`. This checks both inclusive
extrema, deny precedence, exact interior coverage, original witness edge/rule
identity and byte-identical trace JSON after rule permutation. It does not derive
expected intervals from the production partitioner.

The same partially reachable domain fails a required intent (two failed atoms)
and separately fails a prohibited intent (one failed atom). These independently
authored expectations reject the common erroneous shortcut of negating the
aggregate required-intent result to obtain prohibited intent success.

A second revision with identical topology remains reachable but cannot replay
the first revision's witness or build a report using the first revision's check
result. A prospective three-atom query with a finite predicate ceiling below its
reservation is rejected before a monkeypatched first-atom evaluator can run;
reserved queries and visited states remain zero.

The existing suites also exercise missing permits, explicit denials, structural
absence, cycles, phase alternation, listener binding, independent reverse
initiation, original-endpoint forwarding semantics, unsupported queries,
frontier diagnostics, replay mutations, deterministic ordering, normalization,
scope comparability and common historical port partitions. Their graph/path and
policy oracles inspect raw declarations without invoking production policy or
graph helpers to calculate expected answers.

## Cross-component interpretation review

`capture/reconciliation.py:compare_capture` selects the interval containing the
observed destination port from the unchanged native query. It preserves
`model_sha256`, the original query and selected interval; reviewed endpoints,
unique initial TCP SYN direction, declared service and exact representable source
scope are required before native evaluation. UDP/midstream traffic, multihomed
origins and self queries remain qualified. A reachable declaration is not
interpreted as deployed authorization or successful application exchange.

`drift/architecture.py` requires equivalent SUC, source/destination scope,
interfaces and exact service definitions before native model comparison. It uses
a shared port partition from both models. Missing or incompatible scopes emit
indeterminate findings. Capture-native comparison attachments from different
model hashes are not silently paired as evidence of an infrastructure change.

`evidence/attachments.py:model_architecture` revalidates canonical models through
the native API and checks the component digest. `evidence/revisions.py` records
native schema, engine, comparison versions and exact selected implementation
hashes separately from package distribution identity. These boundaries were
inspected; dedicated history/security agents and final source-replay checks
provide additional acceptance evidence.

## Reproducible verification

From the repository root, using the regular installed parent package:

```powershell
.venv/Scripts/python.exe -m pytest tests/test_v146_native_audit.py tests/test_reachability.py tests/test_reachability_oracle.py tests/test_policy_evidence.py tests/test_trace.py tests/test_normalization.py tests/test_contract.py tests/test_drift_architecture.py --basetemp=.pytest_tmp/v146-native-audit --tb=short --junitxml=output/v146/native-audit.xml -q
.venv/Scripts/python.exe -m ruff check tests/test_v146_native_audit.py
.venv/Scripts/python.exe -m ruff format --check tests/test_v146_native_audit.py
.venv/Scripts/python.exe -m mypy src tests/test_v146_native_audit.py
```

Results: **229 PASS, 0 FAIL, 0 ERROR, 0 SKIP; 50.74 seconds**. The five new cases
are included in 229, not additional to that total. Ruff lint/format pass. Strict
mypy passes for 98 files (97 source modules plus this audit file). A first mypy
invocation on the test file alone could not resolve installed untyped modules;
including the source tree explicitly resolved the analysis environment without
changing type policy or suppressing diagnostics.

## Dispositions and residual limitations

| ID | Severity | Observation | Disposition / verification / residual |
|---|---|---|---|
| A-01 | P2 assurance | Existing native semantics require explicit release counterexamples at both closed-domain extrema and partial-intent interpretation | Five tests added; 229-case focused campaign passes; no production fix needed |
| A-02 | P3 scope | Native supported queries model declared initiation only | Preserve documented limit; no claim of sessions, enforcement, exploitability, physical continuity or compliance |
| A-03 | Required final gate | Distribution transition and exact installed historical compatibility are still integrator work | No pass claimed here for posttransition source, final wheel/sdist or final hosted CI |

No unresolved demonstrated analytical release blocker is reported by Agent A.
