# V15-04 — Explicit compatibility boundary

The new `tools/verify_v15_04_transition.py` policy fixes merged dev2 commit
`18cb7e84ef16871daf857af48e3cd003ec8200ba`, tree
`0b512bce31da2b0d9b10160b1a8cdc13ec23fab4`. Its explicit literal SHA-256 replacements
authorize only `__init__.py` (distribution `1.5.0.dev3`) and `explorer_data.py`
(equivalent text rejection). The other 95 runtime modules must match the immutable
Git archive; missing/extra/non-Python runtime members fail closed.

The policy is reviewable authorization code, not a signature. Candidate receipts
and newly generated hashes cannot authorize themselves. Owner review of this new
policy remains required. Historical V15-03/V15-02 policies and fixtures remain
byte-identical, including their original approved hashes and meanings.

The installed-byte check executes authenticated archived helper source in isolated
Python, checks physical source before importing candidate runtime, rejects editable
or wrong-version installations and routes bytecode to a fresh private location.
The new policy protects predecessor tools/tests/fixtures/schema and permits only
the exact three dev2→dev3 metadata assertions. New tests exercise unauthorized
modules, missing/extra resources, forged rehashed fixtures, shadowing, malicious
installed source and stale unchecked-hash bytecode.

Full verification installs exact archived dev2 in its own environment, runs the
unchanged V15-03 verifier and exact dev2 transition suite there. That verifier
recursively preserves dev1 policy testing and immutable native-v1.4 references.
Current wheel/sdist suites exclude both exact-version predecessor test files and
retain their archived executions; no old assertion is weakened or deleted.

Native engine stays `1.3.0`, YAML schema `1`; capture/observation/analysis schemas
are unchanged. Five renderer-bound sources remain exact, so historical renderer
`1.5.0.dev1-historical-explorer.1` and digest
`442d13378cd61586664e19f51ea6834537b0155c07e48ff5a6173628c5d6ca6b`
remain correct. The text helper outside that source set changes no display bytes.

`evidence/revisions.py` includes `__init__.py` in producer identity: dev3 is a new
producer even with native/HTML equivalence. New revisions bind that producer;
dev2 objects/approvals remain unchanged and cannot confer dev3 replay authority.
Full transition requires portable dev2 bundle integrity in dev3, incompatible
producer rejection (`EVIDENCE_REVISION`), original-runtime analytical recovery and
unchanged complete historical inventory. Hashes do not authenticate authorship;
portable integrity is never represented as analytical replay. No physical traffic
change follows from a producer-version difference.

Execution outcomes and installed wheel/sdist identities are recorded in the final
acceptance record. Raw evidence: `output/v15-04/transition/`, including Agent E's
independent read-only plan and the final command-by-command historical chain.

The native capture manifest inventories 33 top-level source modules. V15-04 pins
both complete captured maps (including `__init__.py`) to immutable dev2 and exact
authorized dev3 hashes, then permits only the reviewed `explorer_data.py` source
delta in the unchanged native comparator. Every non-manifest artifact must still
be `EXACT_BYTES`. Seven regression cases challenge forged allowed-helper/init or
native-module hashes, missing/extra modules, and self-rehashed changed output.

The first full transition attempt stopped because its native source allowlist was
empty despite the declared helper change. Both historical gates had passed and
an independent inspection found all 123 native artifacts identical, but that
diagnosis did not authorize acceptance. The failed attempt remains under
`output/v15-04/transition/full/`; the corrected complete rerun is recorded
separately. Neither old policy nor immutable comparator was changed.

## Executed corrected transition

`transition/full-retry/transition.json` PASS; unchanged archived dev2/dev1 suites
24/30PASS without skips; independent native123artifact comparison exact across
45cases and both33module source maps pinned. Old bundle portable verification
explicitly reports analytical_reproductionFalse; current producer rejects old
workspace with EVIDENCE_REVISION, original runtime recovers same bundle ID and
all71historical files remain byte-identical. Approval transfer is false.
Both current4499-case suites pass with one identical sandbox skip each, resolved
by the unchanged real junction test passing outside sandbox in both runtimes.
No runtime/source-producer/renderer byte changes occur in documentation closure;
its package/source identities are recorded independently in final/freeze.json.
