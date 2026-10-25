# V13-20 — Version transition and final installed regression

## A. Executive status

Final execution results are recorded below and in the local release manifest.
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

Results will be finalized from actual receipts after the integrated execution.
Hosted Windows/Ubuntu/macOS on Python3.12/3.14 is NOT RUN in this gate and cannot
be inferred from local Windows3.14 tests. Human browser acceptance remains NOT RUN.

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
