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

Final installed-suite, compatibility and archive runs are pending at source
freeze. Their completed receipts and exact counts will replace this paragraph.

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
