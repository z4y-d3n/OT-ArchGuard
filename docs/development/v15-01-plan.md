# V15-01 — Product consolidation foundation

This local development gate strengthens existing workflows. It does not authorize
a v1.5 release, remote publication, new protocols or analytical contract changes.

## Source and boundaries

Baseline: clean `main`, upstream `origin/main`,
`c5ada13871043ed52cd43557bc7b222399f7b7eb`. Published v1.4.0 source:
`7d6b158f863308dfcd7d10b673bfbe2692f29b8b`; the annotated tag peels to that
commit. The intervening 19-file diff changes documentation only. Work proceeds
on `codex/v15-01-product-consolidation-foundation`.

Distribution/CLI remains `1.4.0`, native engine `1.3.0`, YAML schema `1`.
The immutable verifier derives all 97 runtime modules from approved V14-04 source
plus its existing single-literal distribution transition. Changing a runtime
module or adding `1.5.0.dev1` would violate that policy. This gate therefore
delivers tutorial tooling, CI coverage and documentation improvements. It defers
the version/source transition to an explicit future contract review; it does not
weaken pins to admit a production change.

Native analysis, capture decoding, immutable history, approval authority, resource
limits, report formats and presentation bytes remain fixed. Offline/passive
operation, no TCP reassembly and existing protocol limitations remain applicable.

## Responsibilities and priorities

| Role | Assignment | Write boundary |
|---|---|---|
| Integrator | Reproduce, select, implement, test, dossier and handoff | Reviewed project changes |
| Agent A | Independent architecture, reliability and contracts | Isolated audit output only |
| Agent B | First-run, four user journeys, documentation | Isolated audit output only |
| Agent C | Repeated benchmark characterization | Isolated outputs; one new typed benchmark driver |
| Agent D | Wheel/sdist, disconnected installs, portability | Isolated builds/environments only |
| Agent E | Skeptical final diff/evidence review | Read-only candidate review |

Four discovery responsibilities use at most three concurrent children; D starts
after A. E starts after integration. No nested delegation or concurrent source
writes. Benchmark timing runs precede package builds and the full test suite.

Priorities: (1) actionable historical tutorial destination diagnostics;
(2) explicit tutorial prerequisites and current installation guidance;
(3) v15 branch push verification with the existing six-job matrix;
(4) reproducible measurement and package evidence. No speculative optimization.

## Acceptance and next gates

Every correction must reproduce a real failure, preserve existing outputs and
receive regression coverage. Require focused tests, full-suite evidence, Ruff,
strict mypy, dependency consistency, exact native/presentation verification,
regular wheel/sdist imports, a real first report and independent review. Hosted
CI for the final SHA and human/browser acceptance are separate owner gates.
See [acceptance](v15-01-acceptance.md) for executed results.

Proposed sequence, based on findings:

1. **V15-02:** explicitly define the development-source/version compatibility
   transition, independent immutable native/presentation oracles and exact
   historical producer boundary before allowing runtime changes. Include the
   demonstrated double-I/O-failure diagnostic case in that review.
2. **V15-03:** refine first-run/evidence navigation using browser and keyboard
   observations; keep semantic outcomes and qualified evidence visible.
3. **V15-04:** investigate measured history/Explorer costs with profiles and
   paired workloads; optimize only reproduced bottlenecks.
4. **V15-05:** harden disconnected distribution and onboarding across the six
   supported CI configurations; consolidate proven documentation friction.
5. **V15-06:** independent adversarial, packaging and owner acceptance before a
   separately authorized release-readiness gate.

These are proposals, not implemented features or release promises.
