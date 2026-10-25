# V13-13 — Release candidate readiness and owner boundary

Date: 2026-10-25. **PARTIAL**. Local independent hardening and verification do
not grant stable-release approval. Hosted final-candidate CI, actual browser
acceptance, the controlled version transition and formal owner acceptance remain
outstanding. No remote write, PR, tag, merge, release or PyPI operation occurred.

## Reconstructed starting state

The workspace was clean on `codex/v13-01-capture-foundation` at
`4fb9b4863ee59684211e7a3315221ff89102bebb`, tree
`6a01b04641dde69cb28806d05a41bae6ab803a07`. It contains implementation commit
`3d3bbd5fda3c90690478df06085432fb6371abf8` plus one evidence-only commit.
The immutable baseline is `f52c792b683cb499dc7de765b65b5cc897a96854`, tree
`2229b0657128cdb56eb978eb4fb0a5e74fd275f4`. Local ancestry was verified.

Read-only GitHub inspection found only published branch `main` at that baseline,
no open PR, and published release v1.2.0 (release ID 423648898). Annotated tag
object `c9978e93d0490da23d870a76a92d4b990159a46a` peels to the baseline. The API
returned no published implementation commit/check runs for `3d3bbd5` (HTTP422);
candidate hosted CI is **NOT RUN**, not inherited from baseline success.
Receipts are in `output/v13-audit/remote-*.json` and the final readiness manifest.

The three required prior markdown reports, raw XML, package audits, manifests,
benchmarks and generated tutorial sites were available and inspected.
`demo_report.zip` was absent from the repository/output and available attachment
inventory. No identical original ZIP review is claimed. The preserved generated
tutorial comparison site provided a reproducible original-renderer corpus;
before/after SVG-only rasters are separately labeled in V13-10.

## Independent review and local disposition

- A-01 High: malformed IPv4 options retained SYN/ports and could invoke the native
  engine. Corrected; independent invalid-byte and comparison-boundary regressions.
- A-02 Medium: malformed/unsupported IPv6 extension semantics retained transport
  evidence. Corrected with bounded TLV/padding validation and conservative scope.
- R-01 Medium: native evidence was rejected only after complete query construction.
  Corrected with per-interval rejection before retention/next evaluation.
- C-01/C-02 quality: shared diagram corridors and missing finding-to-detail links.
  Corrected with separate labeled lanes, exact codes and evidence navigation.
- C-03 evidence: hosted workflow omitted capture benchmarks. Execution and artifact
  retention are now configured; execution still requires an authorized remote push.

No reviewer reported an unresolved confirmed critical/high defect. The finite
corpora do not constitute a comprehensive security proof. DHCP/NAT/sensor scope,
unauthenticated owner assertions, no reassembly/checksum/application validation,
unsupported analysis, one in-flight native interval, and concurrently hostile
filesystems remain documented limits. No OS memory or filesystem sandbox is
claimed. Reviewer hypotheses about exact-port cache reuse and duplicate valid
IPv4 model identities were resolved by independent tests and validation rules;
no conflicting confirmed finding was concealed.

The exact installed wheel passed **2,612 tests, zero failures/errors/skips**;
the separately installed sdist capture corpus passed **290**. Ruff, formatting,
strict mypy and dependency consistency passed. The independent historical
comparison retained **45 cases / 123 exact artifacts**. Eight final benchmark
workers completed reports and one rejected the intended resource workload.
These overlapping tests are not additive counts. V13-08/09/11/12 have local
engineering evidence; V13-10 and V13-13 remain incomplete because browser and
hosted acceptance are pending. This is **READY FOR OWNER REVIEW** of local work,
not **APPROVED FOR STABLE RELEASE** or **PUBLISHED**.

## Final source and artifact authority

Exact local commit, ancestry, changed files, diff summary, executable/test hashes,
distribution names, SHA-256 values, installation origins and final acceptance
state are recorded in `output/v13-audit/final-manifest.json` and
`source-checkout.json`. V13-12 records the actual commands and results.
The final owner-facing report supplies the exact commit from these receipts.
Only real completed checks support readiness; pending checks remain pending.

## Proposed remote operation — authorization required

Source branch and proposed new destination:
`codex/v13-01-capture-foundation`. From the final verified source commit, the
specific proposed operation is a normal, non-forced creation of that remote
development branch:

```text
git push origin LOCAL_FINAL_COMMIT:refs/heads/codex/v13-01-capture-foundation
```

Replace `LOCAL_FINAL_COMMIT` only with the exact final-manifest commit presented
to the owner. Recheck the destination remains absent immediately before an
authorized push; if it exists or main has moved, stop and reconcile read-only.
The existing `push: codex/v13-*` workflow will run Windows/Ubuntu/macOS with
Python3.12/3.14: full wheel and sdist tests, exact source/archive/environment
audits, walkthroughs, revision provenance, native/quality/capture benchmarks and
retained evidence. No historical ref, main, stable tag or release is modified.
This proposal does not authorize a PR, merge, tag, publication or settings change.
After authorization, inspect all six actual job artifacts and tested commit IDs.

## Controlled version transition, not yet performed

Prepare a separate local change only after owner sequencing is agreed:
`pyproject.toml [project].version` and `src/otarchguard/__init__.py::__version__`
must both become 1.3.0. The current-release assertions in
`tests/test_release_candidate.py::RELEASE_VERSION` must be reviewed against the
intended new release rather than weakening historical expectations. Preserve the
archive-integrity regressions in `tests/test_final_release.py`.
Search all current-release references, update new release/installation records,
and retain historical 1.2.0 evidence unchanged. Archive filenames, dist-info/root,
metadata and CLI identity must agree. Build fresh regular environments; rerun
full installed suites, version-aware compatibility, archive/source/module hashes,
walkthroughs and all six hosted jobs against that actual versioned candidate.
No official v1.3.0 tag or publication is authorized by local development.

## Acceptance conditions and recommendation

1. Authorize the exact development-branch push only after reviewing the final
   commit/diff and local receipts.
2. Inspect all six hosted cells and required artifacts from the actual commit.
3. Execute the permitted local-file browser checklist in V13-10, including
   keyboard, focus, approximately200% zoom and sensitive-report review.
4. Complete the controlled version transition and revalidate affected artifacts.
5. Obtain explicit owner acceptance and separately authorize any stable tag,
   merge/publication or distribution upload.

The current state is suitable for review of the local engineering work and the
specific hosted-validation proposal. It is **not approved for stable release**
and **not published**. Overall status remains **PARTIAL** until the missing
evidence and owner decisions are resolved.
