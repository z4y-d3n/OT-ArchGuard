# V15-02 — Controlled source evolution

Baseline: merged `main` at `b3adcc9de21dfff6ad58946028a241844ff88294`,
tree `b2a2ec908d02cc36339a7a3d2d3cd736671db3e0`. GitHub PR #26 is merged;
reviewed `867516be2c274a12d251c89bc0310a441b91da45` is an ancestor and has
the same tree. Initial checkout was clean at that reviewed head. Read-only
GitHub metadata and `git fetch --no-tags origin main` established integration.
Branch: `codex/v15-02-compatibility-evolution`.

## Architecture decision before runtime edits

Preserve the V14 verifier and all immutable Git references. Add a separately
versioned V15 verifier, deriving the full 97-module inventory from the exact
merged predecessor and binding four reviewed replacement SHA-256 values in
reviewable verifier code. Receipts are evidence, never authorization inputs.
Protect predecessor tests, fixtures, schemas and independent oracle utilities.
Only two current-distribution test literals may advance; historical copies stay
in Git. Run the original verifier against isolated predecessor source and its
regular installation. Compare every candidate native artifact against that
verified predecessor; authorize the reporting source change only after exact
97-module validation. See [compatibility contract](v15-02-compatibility-contract.md).

## Scope and sequence

1. Independent read-only investigations A (compatibility), B (Explorer),
   C (report I/O), D (packaging/CI).
2. Add transition policy and adversarial checks.
3. Distribution `1.5.0.dev1`; native engine/alias `1.3.0`, YAML schema `1`.
4. Local semantic vertical Major limitations list and new renderer revision.
5. Preserve primary report diagnostics across secondary cleanup I/O failures.
6. Installed wheel/sdist, full suite, static checks, immutable historical/native
   comparison, fictional workflows, paired timings and raw receipts.
7. Independent Agent E skeptical audit, corrections, final source/package audit,
   Spanish owner handoff and clean local commit.

Integrator owns all tracked edits. At most three specialists run concurrently;
no concurrent shared-file modifications. Auditor does not modify production or
expected evidence. Raw outputs remain ignored under `output/v15-02/`.

No native analytical, capture, schema, historical revision, approval or shared
presentation-helper changes; no new protocol, caching or algorithm refactoring.
No remote write, PR, merge, tag, release or historical asset replacement.

Local acceptance requires exact source/installed identities, positive and
negative transition tests, unchanged native output, new renderer portable and
source replay, report failure preservation, package inventories, static checks
and no unresolved blocking independent finding. Hosted six-job CI and human
browser acceptance remain separate owner gates.
