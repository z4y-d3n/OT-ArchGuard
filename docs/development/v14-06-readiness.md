# V14-06 release-readiness register

Final functional acceptance at `40ffbeab422dcf13f57d4fb9bc6e61a95d08642e`:
three complete suites each report 4,370 PASS and one environmental SKIP, no
FAIL/ERROR. The final current R01–R32 matrix is in
[the Spanish handoff](v14-06-handoff-es.md). The initial table below preserves
the starting assessment rather than claiming those gates are still unexecuted.

Candidate preparation only. Published stable remains v1.3.0. Parent:
`ac893bc3174f0a7ace67454d19ad6e61116425af`; exact public-source baseline and
97 production hashes are retained in `output/v146/parent-source.json` and
`output/v146/parent-identity.json`. Never replace this baseline after a failure.

## Classification and evidence policy

P0 blocks release: incorrect supported results, lost evidence, false authority,
security failures within the stated trust model, broken installation or
unverifiable artifacts. P1 is a significant supported-workflow defect; fix it or
record an independently reviewed concrete deferral. P2 is a bounded useful quality
improvement. P3 is future scope. Each finding records ID, capability, reproduction,
expected/actual behavior, severity, source, disposition, verification and residual
limits. Unexecuted gates never count as passes.

## Initial gates (before implementation)

| Gates | Requirement | Initial state |
|---|---|---|
| R01 | Exact local and published parent; six-job CI | PASS; parent-ci.json |
| R02 | Clean local child branch | PASS at creation |
| R03–R08 | Capability, semantics, boundaries and security | NOT EXECUTED |
| R09–R10 | Distribution transition and fail-closed legacy gate | NOT EXECUTED |
| R11–R15 | Wheel, sdist, inventories, dependencies, offline | NOT EXECUTED |
| R16–R23 | Workflows, presentation, docs, performance, hashes, suite | NOT EXECUTED |
| R24 | Independent final review | NOT EXECUTED |
| R25–R28 | Data rights, limits, rollback, staged assets | NOT EXECUTED |
| R29 | Owner acceptance | OWNER ACTION REQUIRED |
| R30 | Six-job CI for exact child SHA | OWNER ACTION REQUIRED |
| R31 | Integrated main acceptance | OWNER ACTION REQUIRED |
| R32 | No unauthorized remote mutation | PASS; local-only constraint |

## Finding register

| ID / severity | Capability; reproduction; expected versus actual | Source and disposition | Verification / residual |
|---|---|---|---|
| V146-R01 / P0 preparation blocker | Stable distribution with preserved native semantics should pass the legacy gate; old gate required the dev1 approved package hash and distribution assertions | `verify_legacy_candidate.py`: derive exactly one literal delta from unchanged approved pin; separate approved/candidate installs; bind full source inventory | CLOSED: 16 new gate cases plus existing adversaries; installed legacy reproduction passes 110 analytical artifacts and 13 exact approved HTML files |
| V146-E01 / P1 | Recomputed RECORD with duplicated singleton metadata, extra matched console script or wrong WHEEL profile should reject; original auditor accepted these manipulated real archives | Narrow archive metadata/entrypoint validation; agent E report provides real fixtures and dispositions | Focused adversarial regressions and final full archive/install campaign; no runtime module change |
| V146-B01 / P1 documentation | Development historical workspace should have an explicit upgrade boundary; exact changed init identity rejects interpretation while storage bytes survive | Preserve exact-source fail-closed policy; installation/history/notes now require retained dev environment and fresh stable revisions/review | CLOSED/documented limitation: four pipeline cases and independent review accept this contract boundary; no automatic migration promised |
| V146-E02 / P1 | New rehearsal's two backend hooks reused mutable `sys.argv`; sdist was written outside requested staging path | Cache destination before either build hook; staged assets remain unavailable until completed audit | Real four-asset rehearsal passes on first freeze; caught before candidate acceptance |
| V146-F01 / P1 | Independent reviewer coordinated one malformed Metadata-Version across all three records; uniqueness-only validation still accepted it | Require exact reviewed core metadata profile 2.4, justified by approved setuptools/PEP 639 license fields; add coordinated malformed/unknown cases | Initial just-started runs interrupted and retained; corrected freeze passes all three full suites and 41 packaging cases |
| V146-A01 / P2 | Full inclusive port-domain extrema and partial intent outcomes need independent release examples | Five native counterexamples; no engine modification | CLOSED: focused 229 PASS and all three final candidate suites pass |
| V146-SEC-001 / P2 | Late hostile ZIP member must reject before any XML tree allocation | 15 cross-adapter preallocation cases; no parser modification | Focused 430 PASS / one environmental junction SKIP; finite internal assurance |
| V146-D01–D03 / P1 documentation | Primary guides described implemented history/drift as future or prior visual/CI acceptance as pending, and omitted source upgrade boundary | Current guidance corrected; historical milestone records retained | Local links/PowerShell parsing and installed candidate examples; no new browser acceptance claim |

Every row is a bounded observation. All remaining acceptance states are tracked
in the final Spanish handoff; no unexecuted gate is promoted by this register.

## Ownership

Integrator owns version metadata, compatibility verifier, CI, shared inventories,
release assembly and Spanish handoff. A owns native audit tests/report; B owns
capture/history integration audit tests/report; C owns security audit tests/report;
D owns public documentation and onboarding; E owns packaging/performance audit
tests/report. Production changes require integrator review. The final reviewer
is separate and read-only. Available slots require two investigation waves.
