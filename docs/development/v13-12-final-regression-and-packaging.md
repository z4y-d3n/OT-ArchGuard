# V13-12 — Final regression and distribution verification

Date: 2026-10-25. This independent record preserves earlier gate evidence.
The executable source and test corpus are frozen for installed verification.
Final execution receipts, archive identities and source hashes are retained in
`output/v13-audit/`; results are filled after actual execution, never inferred
from the historical 2,533-test result.

## Execution contract

Use Windows CPython 3.14.5, pytest 9.1.1, Ruff 0.17.1, mypy 1.20.2 and setuptools
84.2.1. Runtime dependencies remain Typer, PyYAML and Pydantic; schema remains 1
and development package/runtime version remains 1.2.0. The controlled 1.3.0
transition is described in V13-13 rather than performed here.

Fresh, separate regular environments are under `output/v13-audit/wheel-env` and
`sdist-env`. Install approved verification requirements from local `wheelhouse`
with `--no-index --find-links=wheelhouse`; install the built wheel/sdist with
`--no-index --no-deps --no-build-isolation`. No editable installation is used.
Set TMP/TEMP and pytest's basetemp to a workspace directory. Initial ensurepip
failed in the sandbox default temp; rerunning ensurepip with workspace TMP/TEMP
resolved setup, without downloading or substituting dependencies.

Required final commands:

```text
python -m ruff check .
python -m ruff format --check .
python -m mypy
python -m pip check
python -m pytest -q --basetemp=output/v13-audit/full-tmp --tb=short --junitxml=output/v13-audit/full-suite.xml
python tools/audit_release.py WHEEL SDIST --source-root . --output output/v13-audit/archive-audit.json
python tools/verify_environment.py --output output/v13-audit/wheel-environment.json
python tools/verify_source_checkout.py --output output/v13-audit/source-checkout.json
```

The saved `output/v13-audit/run_checks.py` records expanded interpreter paths,
commands, elapsed times and exit codes. For runtime suites and walkthroughs,
`OTARCHGUARD_OFFLINE_CHECK=1` and absolute `PYTHONPATH=tools/offline` activate the
network-denial harness in child interpreters. This is a Python-operation test,
not evidence of a physical air gap. Source-checkout targeted review uses
`PYTHONPATH=src` separately and is not installed-package acceptance evidence.

## Results

| Verification | Actual result | Receipt |
|---|---|---|
| Full regular installed-wheel suite, network denied | **2,612 passed, 0 failed/errors/skipped**, pytest 503.85 s; driver exit0, 504.774 s | `full-suite.xml`, `full-suite.stdout`, `full-receipt.json` |
| Regular installed-sdist capture suites, network denied | **290 passed, 0 failed/errors/skipped**, exit0 | `sdist-suite.xml`, `sdist-receipt.json` |
| Ruff lint / formatting | PASS, exit0 / exit0 | `quality-receipt.json`, `ruff.stdout`, `format.stdout` |
| Strict mypy | PASS, 145 source files, exit0 | `mypy.stdout`, `quality-receipt.json` |
| pip consistency | No broken requirements, exit0 | `pip-check.stdout` |
| Native historical compatibility | **45 cases, 123 exact artifacts**; typed exit codes/input identities equal | `legacy-comparison.json` |
| Historical source contracts | All 54 files under baseline `tests/` unchanged, including fixtures; pyproject, schema document and native contract bytes unchanged | `legacy-comparison.json` |
| Wheel/sdist member/source/RECORD/metadata audit | PASS, 279 public files, exit0 | `archive-audit.json` (verification stage), `final-archive-audit.json` (final documentation) |
| Fresh installed module/console origin | PASS, both distributions; all 60 modules match reviewed source | `wheel-environment.json`, `sdist-environment.json`, `final-sdist-environment.json` |
| Native consoles and fictional capture walkthroughs outside checkout | PASS for wheel and sdist, all six expected classes; network denied | `outside-receipt.json`, `wheel-walkthrough.json`, `sdist-walkthrough.json` |
| Final installed capture benchmarks | Eight complete, one expected resource rejection | `final-benchmarks/benchmark.json`; V13-11 |
| Hosted six-cell candidate CI | **NOT RUN** | Authorization boundary in V13-13 |
| Actual browser keyboard/zoom/accessibility acceptance | **NOT RUN** | SVG-only inspection and checklist in V13-10 |

The full-suite verification wheel SHA-256 is
`73b94968181a3067165146a7c9f793b6ec450ddbd8801b0ac8348662c2acd319`
(212,266 bytes). That exact wheel is retained as the final wheel; no rebuild is
needed when only development evidence markdown changes. The final sdist is
rebuilt to include the completed records, audited against final committed source,
regularly installed and its 290 capture tests rerun. Final archive hashes/sizes
are in `final-archive-audit.json`, `final-manifest.json` and `SHA256SUMS.txt`.
This avoids a self-referential sdist hash inside its own source documents.

Executable and test bytes were frozen in source identity
`a9c651f4f3e6997ec6d2ef01c9675d8242dc3475`; the suite driver recorded every
Python source/test/tool/benchmark hash before execution. The commit was recorded
during the run without changing those bytes. Only evidence markdown was finalized
afterward. `final-manifest.json` asserts every executed Python hash still equals
the final checkout and both installed module inventories. `source-checkout.json`
binds final committed public bytes, including the completed documents. No code or
test change is accepted on the strength of an earlier executable revision.

The first baseline compatibility driver attempt used a relative output under the
archived baseline's different working directory and failed `validate-json` with
`REPORT_IO_ERROR`. Its partial output is preserved. Supplying an absolute output
resolved the driver error; the baseline's entire installed module inventory was
independently matched to `git archive f52c792` before accepting the 123-artifact
comparison. The initial sdist installation also hit the managed default pip
cache permission boundary; `--no-cache-dir` plus workspace TMP/TEMP resolved it.
These setup failures are not silently counted as successful product checks.

## Verification scope

The 79 new independent tests comprise 23 parser/decoder cases, 43 semantics,
5 publication/visual structure cases and 8 resource cases. They are included in
the full suite and must not be added to its count as separate coverage.
Earlier targeted executions are diagnostic evidence, not a second full-suite
acceptance. Historical test files and expected outputs are preserved.

The archive audit checks exact allowlists, all members, source equality, licenses,
entry points, dependency metadata, source/wheel equivalence and wheel RECORD.
Installed-origin receipts check every production module and the native console.
Generated distributions deliberately retain version 1.2.0 and are local
development artifacts, not replacements for the published v1.2.0 release.
No cross-host archive-byte reproducibility, hosted acceptance or browser PASS is
inferred. Detailed outstanding conditions are in V13-13.
