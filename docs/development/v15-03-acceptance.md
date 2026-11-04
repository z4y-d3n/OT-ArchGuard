# V15-03 acceptance record

Verdict: **READY_FOR_OWNER_REVIEW**. Scoped local implementation and verification
complete; actual browser/owner acceptance and six hosted jobs for the submitted
candidate SHA remain explicitly NOT_TESTED.

Candidate evidence is retained under ignored `output/v15-03/`. Implementation
commit `91f1d354f4d03ec202f6fd15b6ff6760d1d4f899`, tree
`2556ba23761c3b9049725c70181335c880743d36`, fixes the final production and test
bytes. CI-only commit `19b552fe5892b45c768d8cbd897568e7d289a230` reorders the
sdist pytest options to preserve the original immutable CI guard, with identical
arguments. Its tree is `1d1e3204df831593b5ad5c273ca87e6121abe68e`. The later
closure commit changes documentation only. Final HEAD/tree,
public inventory and archive hashes are in final-freeze.json/source-final.json.
Historical and current campaigns are counted separately; repetitions overlap.

| Requirement | Evidence / status |
|---|---|
| Authenticated V15-02 merge | PASS: PR27, a3cf2f2, exact tree; hosted run41741064369 six SUCCESS |
| J1 first-run architecture | PASS structural/generated journey: agent-a/agent-b receipts |
| J2 capture | PASS: C-01/C-02 fixed; exact identity and adjacent-batch tests, review/capture + dense/limited artifacts |
| J3 historical | PASS baseline normal/incomplete/decoder/dense/revoked walkthrough |
| J4 import/review | PASS baseline authentic human-review/provenance handoff; preserved |
| Canonical preservation | PASS: exact predecessor PCAP JSON/identified record text; 123 native artifacts EXACT_BYTES plus verified manifest provenance |
| Source transition | PASS: transition-final/transition.json; exact two changed/95 unchanged modules, isolated installed pre-import authorization |
| Historical preservation | PASS: unchanged V15-02 verifier on dev1; 30 unchanged tests; EVIDENCE_REVISION/recovery and unchanged old inventory |
| Accessibility semantics | PASS structural: exact page/family/current-pager markers, main focus target; browser NOT_TESTED |
| Responsive/keyboard/zoom/print | NOT_TESTED: browser policy blocks local-file protocol |
| Security | PASS focused/sdist: hostile labels/CSP/path/bidi/resource tests; malicious source/unchecked pyc rejected before import; valid rehashed false reachability rejected |
| Completeness | PASS: ordered flow batches, index/detail pagination, records/anchors and mutations; seven final sites 486 pages / 14,408 links / zero errors |
| Installed product | PASS: audited regular wheel/sdist, all 97 physical module hashes, metadata/console; 258 extracted-sdist affected cases |
| Performance | PASS deterministic/canonical/output budget; paired timing evidence and explicit uncertainty in performance.md |
| Independent F review | PASS: no unresolved demonstrated P0/P1; agent-f/findings.md and final-receipts.md |
| Candidate hosted CI | NOT_TESTED: requires six jobs for actual submitted SHA; no push authorized |
| Owner manual acceptance | NOT_TESTED; explicit checklist in accessibility/handoff |

## Campaign receipts

- Current version suite: **4,453 PASS, 0 FAIL, 0 ERROR, 0 SKIP**, 748.82 s,
  full-final.log/full-final.xml. Explicit `--ignore=tests/test_v15_transition.py` because
  that immutable policy checks dev1, with all 30 cases executed unchanged separately.
- New regression cases: 40 unique, all included in the current campaign.
- Focused integrated: 83 PASS, zero FAIL/ERROR/SKIP, focused-final.xml.
- Extracted sdist + regular installed sdist: 258 PASS, zero FAIL/ERROR/SKIP,
  sdist.xml; actual test root output/v15-03/extracted/otarchguard-1.5.0.dev2.
- Independent F: 40 PASS, zero FAIL/ERROR/SKIP, agent-f/tests.xml; same 40 new cases.
- Historical dev1: 30 PASS in 26.25 s, transition-final/historical-tests.xml;
  source and original assertions unchanged. Separate versioned-source campaign.
- Full native/history transition PASS, transition-final/transition.json;
  nested v15-02/transition.json retains its original V14 contract and meaning.
- Ruff lint/format, strict mypy (274 source files), pip check PASS. Python
  3.12.14 Windows AMD64. No candidate Linux/macOS/3.14 execution claimed.
- Final wheel/sdist source/metadata/license/RECORD/inventory audit: archive-final.json.
  Regular runtime identities: environment-wheel.json/environment-sdist.json;
  isolated authorization: authorized-final.json/authorized-sdist.json.
- Real wheel J1/J2/J3/J4 walkthroughs and extracted-sdist capture/history: all
  exit 0, review/exits.json and sdist-walkthrough-exits.json. Frozen supported/
  limited evidence consumer and original protocol corpus also exit 0.

Campaign-summary.json deduplicates JUnit identities and records test-source hashes;
focused, sdist and independent runs must not be added as extra unique cases.
Current 4,453 plus historical 30 = **4,483 unique cases**. All 83 focused, 258
sdist and 40 independent cases overlap the current campaign completely. The 40
new regression cases are already included in those 4,453. Both complete runs
overlap; the first failed run is superseded, not an additional unique campaign.
The 14,408 review links are anchor (`a`) links. Product audits also count each
local stylesheet (`link`), so their totals differ by the number of HTML pages;
this counting distinction is not evidence loss.
F also changed exactly one finding link to a different existing flow. All files,
anchors and canonical JSON still passed graph/integrity checks, but the unchanged
contextual-identity oracle rejected it at the finding-to-flow assertion. Raw script,
original/mutated sites and receipt: agent-f/wrong-existing-record.*. This isolated
mutation experiment is not an additional unique pytest case.

## Reproduction commands

```powershell
.venv-v153-final/Scripts/python.exe -I tools/verify_v15_03_transition.py --output output/v15-03/NEW-transition
.venv-v153-final/Scripts/python.exe -m pytest --ignore=tests/test_v15_transition.py --basetemp=output/v15-03/NEW-tmp --tb=short --junitxml=output/v15-03/NEW-full.xml
.venv-v153-final/Scripts/python.exe -m ruff check .
.venv-v153-final/Scripts/python.exe -m ruff format --check .
.venv-v153-final/Scripts/python.exe -m mypy
.venv-v153-final/Scripts/python.exe -m pip check
.venv-v153-final/Scripts/python.exe tools/verify_source_checkout.py --output output/v15-03/NEW-source.json
```

Offline campaigns set OTARCHGUARD_OFFLINE_CHECK=1 and PYTHONPATH to tools/offline;
the isolated verifier builds its own guarded child environment. Exact child command
arrays/exit codes/stdout/stderr are retained in transition-final/commands.json.
Sdists run their extracted tools/tests with GIT_DIR fixed to the repository.

## Nonpassing attempts and outstanding gates

Initial sandbox preflight failed during ensurepip; normal-process retry of the
unchanged V15-02 verifier PASS. Initial candidate focused run: 32 FAIL/48 PASS
because span was outside the allowed inert HTML elements; corrected locally with
an allowed paragraph, without changing shared safety rules. Sandboxed wheel
reinstall failed moving its console executable and temporarily removed that
runtime; initial transition and concurrent collect-only then failed with missing
package. These receipts are superseded by fresh .venv-v153-final, not erased.
Initial archive-audit.json binds the rejected earlier renderer; final archive
acceptance uses archive-final.json, after corrected archive-implementation.json.
First full campaign: 4,452 PASS and 1 FAIL in 815.56 s. The original CI guard
expected a fixed pytest command prefix; placing --ignore after --basetemp fixes
the option order without altering its effect or the test. Related CI/foundation
rerun: 17 PASS. A new complete campaign retains a separate full-final.xml receipt.

Browser local-file policy rejection, real responsive/keyboard/zoom/print and owner
acceptance remain NOT_TESTED. Candidate hosted six-job CI requires publication by
the owner and the exact submitted SHA. None of these is converted to PASS.
