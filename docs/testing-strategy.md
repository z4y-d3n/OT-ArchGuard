# Verification strategy

Use matching regular installed wheel environments on Windows Python 3.12/3.14.
Version 1.0.1 results are in the [verification summary](verification.md).

The v1.1 workflow defines native Windows, Ubuntu and macOS runners with Python
3.12/3.14, `fail-fast: false` and no exclusions. Hosted Gate V11-2 outcomes are
**pending remote verification**. Job ID `verify` is retained; expanded displayed
check names need owner review in branch-protection settings after the first run.
PowerShell Core is explicit on every runner; offline paths use forward slashes.
Artifacts include OS/Python identity and expire in seven days. No release upload
is performed. See [Gate V11-2](v1.1/gate-v11-2.md).

After a regular install, run `python tools/verify_environment.py --output
output/environment.json` to verify distribution metadata, actual import location,
all production module hashes and the console from `sysconfig.get_path("scripts")`.
POSIX uses `otarchguard`, Windows uses `otarchguard.exe`; neither assumes it is
beside `sys.executable`.

~~~powershell
.\.venv\Scripts\python.exe -m pip install -r tools/verification-requirements.txt
.\.venv\Scripts\python.exe -m pip install --no-build-isolation --no-deps .
$env:OTARCHGUARD_OFFLINE_CHECK='1'
$env:PYTHONPATH=(Join-Path (Get-Location) 'tools/offline')
.\.venv\Scripts\python.exe -m pytest --basetemp=output/pytest --tb=short
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m mypy
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe examples/run_examples.py
~~~

The opt-in Python audit hook denies network operations in tests/child CLIs;
it is verification tooling, not a runtime dependency or physical air gap.

Raw-declaration tiny-graph/per-port oracles independently model states, selectors
and deny precedence. They do not use production graph, partition or decision helpers.
Independently inspect every witness against raw endpoints, edge/state continuity
and permits. Fixed seeds cover cycles, missing permits, denies and protocol separation.

Concrete-port set oracles verify interval union/difference/intersection and small
comparisons. Check identity/reversal, stable IDs, renames, changed definitions,
selector expansion, criticality and independent requirements/prohibitions.
Never alter expected outcomes merely to agree with production.

Exercise strict scalars, duplicate keys/IDs, unsupported features, invalid references,
placement and exact byte/event/depth/entity/association/atom/work budget boundaries.
A rejected analysis must never become successful unreachability.

Run native installed launchers with paths containing spaces. Verify stdout/stderr,
exit 0/1/2, atomic preservation, deterministic reordered/repeated reports, escaping,
static offline markup, hash binding, summary manifests, card containment and exact
state anchors. Parsing/rasterization is distinct from browser rendering.

Release audits compare every allowed packaged source/test/document byte against
the candidate, check metadata/entry points/licenses, and rebuild from the sdist.
Packaging regressions cover unexpected, missing and stale archive contents.

Independent SVG oracles compare parsed geometry with raw declarations: containment,
intersections, bounds, phases/endpoints, direction and parallel/reverse identity.
Fixed-seed graphs, exact summary boundaries and deliberate corrupt-SVG checks
exercise these oracles. HTML checks unique IDs, resolving local links/markers/clips,
captioned tables, escaped hostile labels and prominent critical findings.
Record raster observations separately from actual browser/print verification.
