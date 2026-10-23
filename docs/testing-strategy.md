# Verification strategy

For source version 1.1.0, [Gate V11-6](v1.1/gate-v11-6.md) records candidate
history. Final acceptance requires local and hosted receipts for the exact
reviewed commit. Earlier version/gate outcomes below remain historical evidence.

Use matching regular installed wheel environments on Windows Python 3.12/3.14.
Version 1.0.1 results are in the [verification summary](verification.md).

The v1.1 workflow defines native Windows, Ubuntu and macOS runners with Python
3.12/3.14, `fail-fast: false` and no exclusions. The Gate V11-2 dossier records
then-pending hosted verification; use current-commit receipts for acceptance.
Job ID `verify` is retained; expanded displayed check names need owner review
in branch-protection settings against the required current checks.
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

## Gate V11-5 contract captures

The [public inventory](v1.1/public-contract-inventory.md) records the accepted
module signatures, native options, result fields and diagnostic differences.
The [hardening dossier](v1.1/gate-v11-5.md) records historical local evidence and
the separate hosted/owner acceptance boundary.

After `tools/verify_environment.py` confirms the regular installed package, capture
the bounded additional corpus with a fresh output directory:

~~~powershell
python tools/capture_contract.py output/contracts-before
python tools/capture_contract.py output/contracts-after --compare output/contracts-before/manifest.json
~~~

The tool captures 45 native cases, including help/parser misuse, all five report
commands, exact trace outcomes, optional policy evidence and preserved failure
sentinels. It records input/model/module identities, exits and artifact hashes.
Existing captures are never overwritten. Comparison requires equal source-module,
input/model, exit and artifact records; interpreter/platform provenance stays
separate. It never updates a baseline to accommodate a failure. Use fixed
`PYTHONHASHSEED` values 0 and 12345 for separate deterministic process captures.
The earlier 197-artifact corpus remains separate local historical evidence.

For the intentional 1.0.1 to 1.1.0 transition, the historical developer capture
example below uses retained gate-local artifacts and the separate narrow comparator:

~~~powershell
python tools/compare_versioned_contract.py output/gate-v11-6/baseline123 output/gate-v11-6/candidate123-312 --output output/gate-v11-6/compatibility123-312.json
~~~

`capture_contract.py --compare` remains an exact same-version comparison. The
version-aware tool permits only root `/engine_version`, that field in the exact
HTML JSON appendix and the exact trace header engine value. It compares all
remaining bytes, including canonical JSON/SVG, and verifies capture hashes,
input/model identities and exits. Interpreter/platform and the central version
module hash are provenance fields checked separately by the gate's source and
installed audits. It never rewrites baseline files or drops arbitrary version
keys. V11-6 preserves a fresh pre-version baseline separately from candidates.

The added hardening tests use bounded inputs and precise report faults; the
metamorphic seeds are 104729, 130363, 155921 and 196613. Their raw-declaration
oracle enumerates only ports 1..8, or six selected boundary ports. Equivalent
rule splitting, isolated additions and display changes preserve concrete truth;
they need not preserve hashes, work, evidence groups or atom boundaries.
Each new seeded relation includes a controlled permit/deny path with both
reachable and unreachable ports, so an entirely blocked random graph cannot
make every transformation pass without exercising permitted communication.
