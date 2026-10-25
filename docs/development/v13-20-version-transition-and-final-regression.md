# V13-20 — Version transition and final installed regression

## A. Executive status

**PASS for local version transition and integrated regression.** Final execution
results are recorded below and in the local release manifest.
The active package/runtime identity is **1.3.0**. Historical release references
and immutable tags remain unchanged. No publication is authorized.

## B. Source and package identity

Starting commit: dfcb6d9d6c2c1b3b475f1f6a64b193362cabed98. Implementation and final
evidence commits, parents, changed files, source inventory and exact archive hashes
are in `output/v13-final/release-manifest.json`. The final source receipt checks
every public checkout byte against Git blobs. Installed module inventories must
equal every reviewed production module. Verification hashes all Python source,
tests, tools and benchmark files before the suites and checks them at finalization.

Version changes are limited to active pyproject/runtime/assertions, current release
guidance and freshly generated metadata. Native YAML schema 1, runtime dependency
set, historical documents and published releases remain preserved. Observation
contract v2 deliberately corrects ARP semantics; association/comparison remain1.

Actual build-backend filenames are captured in `build-result.json`; artifacts are
under `output/v13-final/artifacts/` (final selected rebuilds under `final-artifacts/`
if evidence documentation changes). Archives are built, never renamed old binaries.
Wheel metadata, installed distribution, console and runtime must agree on 1.3.0.

## C. Execution contract and raw receipts

Windows CPython 3.14.5. Separate fresh regular environments:
`output/v13-final/wheel-env` and `sdist-env`; each installs approved dependencies
from local wheelhouse with no index and installs the corresponding archive with
no dependencies/build isolation/cache. No editable installation. Workspace TMP/TEMP
and explicit pytest basetemp avoid the managed default-temp permission boundary.
The saved local `verify.py` driver uses argv lists, records commands, exit codes,
duration, stdout/stderr and source hashes, and activates `tools/offline` plus
`OTARCHGUARD_OFFLINE_CHECK=1` for product suites/benchmarks/walkthroughs. This is
Python-operation denial, not proof of an OS air gap.

Required checks: full wheel suite and independently installed full sdist suite;
Ruff lint/format, strict mypy, pip check; immutable baseline comparison; archive
allowlist/member/RECORD/source equality; installed console/module provenance;
outside-checkout walkthrough; independent interoperability; ARP/contract/adversarial
tests; fixed capture benchmarks; no-network assertions and deterministic golden
regeneration. Suites overlap and must never be added together.

## D. Actual results

| Check | Actual result | Receipt |
|---|---|---|
| Initial regular wheel full suite | 2,745 passed, zero failed/errors/skipped; 556.95 s pytest | wheel-suite.xml / stdout, wheel-receipt.json |
| Independently installed initial sdist full suite | 2,745 passed, zero failed/errors/skipped; 557.00 s pytest | sdist-suite.xml / stdout, sdist-receipt.json |
| Final corrected regular-wheel full suite | 2,746 passed, zero failed/errors/skipped; 497.90 s pytest, driver exit0 | final-wheel-suite.xml / stdout, final-wheel-receipt.json |
| Ruff / format / strict mypy / pip check | PASS; mypy 155 files | quality-receipt.json and named stdout/stderr |
| Initial archive/member/source/metadata/RECORD audit | PASS, 327 public files | archive-audit.json |
| Regular installed modules, distribution and console | PASS, version 1.3.0; every production module equals source | wheel-environment.json, wheel-/sdist-outside-environment.json |
| Outside-checkout console walkthrough and independent evidence consumer | PASS for both distributions, denied Python networking | outside-receipt.json, wheel-/sdist-outside-*.stdout |
| Immutable native baseline | 45 cases; 123 analytical artifacts: 82 exact bytes, 28 exact engine-version JSON changes, 13 exact engine-version HTML changes; manifest independently verified | legacy/comparison.json, legacy-receipt.json |
| Capture resource workloads | Eight complete, one intended budget rejection, no unexpected failure | benchmarks/benchmark.json, benchmarks-receipt.json |
| Direct local-file browser attempt | BLOCKED by URL protocol policy; human review explicitly pending | browser-attempt.json |

The first full runs bind implementation commit
`a0a0a4b00df3c0c628b55625c3426f8210fb27cd`. A subsequent independent review found
that the read-only consumer rejected valid owner-reordered proposals. The correction
is identified by Git prefix `3aa9d98` (full identity in the release manifest). It changes only
`tools/read_capture_evidence.py`, its adversarial test and explanatory prose;
every production module is byte-identical to the first full runs. Candidate cores
are hashed in canonical host-ID order, while reviewed decision order and mapping
digest remain exact. A product-generated reordered review regression passes.
The consumer+golden subset passed 31 cases. The additional 2,746-test full-wheel run
binds all corrected executable/test bytes at
`3aa9d98bce8eff28c3822616fcd9163a1ed54e6f`. The final evidence commit changes
documentation only; the release manifest verifies every executed Python hash
against final source. Fresh selected archives are rebuilt from that exact final
committed source, then audited. Every final wheel member must equal the corresponding
member from the full-tested wheel, even if ZIP container timestamps differ. Final
regular installs verify all 60 module hashes again. Final sdist affected capture,
consumer, release and source-checkout suites are separately recorded in
`final-sdist-targeted.xml` and `final-sdist-targeted-receipt.json`; their actual
count/exit are authoritative in the release manifest, never added to full counts.
No executable change may be accepted through documentation-only equivalence.

The resource workers were separate processes but ran alongside the two full suites.
Their timings are contextual measurements, not isolated capacity/throughput claims.
Both full suites overlap and are never summed. The historical comparator records
124 files including its provenance manifest; only 123 are analytical artifacts.
All 54 historical test/fixture files retain exact baseline bytes except the narrowly
authorized active RELEASE_VERSION assertion. Native schema/contract bytes and
project settings other than the release version are checked exactly.

Hosted Windows/Ubuntu/macOS on Python3.12/3.14 is NOT RUN in this gate and cannot
be inferred from local Windows3.14 tests. Human browser acceptance remains NOT RUN.
Subsequent owner-authorized publication of38c1ec9 did start hosted run40244859860;
its actual failed POSIX typing checks and in-progress Windows snapshot are recorded
in V13-21. The local benchmark guard correction changes no production module,
evidence contract or test. A separate correction-candidate archive/source manifest
is retained under `output/v13-hosted/fix-candidate/`; original V13-20 artifacts and
receipts are preserved as historical exact38c1ec9 evidence.

## E. Risks

Synthetic captures establish the supported subset, not broad operational traffic
validation. Hash equivalence permits preserving valid executable-test evidence
when only development evidence prose changes; final sdist must nevertheless be
rebuilt and audited against final committed source. Cross-host archive byte
reproducibility is not claimed. No artifact from a different final integration
commit is approved for publication without revalidation.

## F. Next step

Present exact reviewed source/diff and normal nonforced branch push for owner
authorization in V13-21. Human acceptance is independently required by V13-17.
Final functional/readiness status is V13-22; publication remains owner-controlled.
