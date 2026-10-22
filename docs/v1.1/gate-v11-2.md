# Gate V11-2 — deterministic presentation and native CI

## 1. Executive engineering summary

Gate V11-2 improves SVG geometry, static offline HTML and the native CI matrix.
This is local v1.1 development with application version 1.0.1 and schema 1.
Owner acceptance and all six hosted CI outcomes remain pending. No commit, push,
tag, publication, remote workflow or GitHub-settings change is authorized here.

Local implementation and available installed verification are complete: **1,056
tests pass on each supported local interpreter**, with analytical equivalence,
determinism, offline walkthroughs, static checks, benchmarks and package integrity.
Remote CI and actual browser/print/accessibility checks remain explicitly pending.

## 2. Initial Git state and identity

The checkout was clean on `main` at
`1c3d00a44949e425e757ad503881faf9fccb0083`, equal to local `origin/main`.
It contains V11-1 commit `38e27c9`. No remote fetch was performed; equality describes
the existing local remote-tracking reference. Branch `codex/gate-v11-2` was created
from that main commit. The approved sole root is
`8e6a5bca41a00eb0454e6efdd9a9558e1a7017b2`.
Annotated tag `v1.0.1` is object `39c855ad6204953495fdca4a7058fd53a3ba8f8c`,
peeling to that root. `EXPECTED_ROOT_SHA` remains referenced unchanged; its remote
value was not read or modified.

## 3. Frozen analytical invariants

No domain, normalization, loading, graph, policy, reachability, intervals, intent,
exposure, comparison or resource-limit implementation is changed. Explicit edges,
ownership/placement, source/destination identity, phases, direction, default deny,
deny overrides, finite scope and witnesses retain their established semantics.
No proximity, forwarding, relay, trust rank or security level is inferred.
Canonical bytes/model hashes and analytical report version 1 remain unchanged.
Runtime dependencies, schema 1, Apache-2.0 and application version 1.0.1 remain.

## 4. Existing presentation and baseline

The old renderer already provided zone containers, state-specific ports,
orthogonal paths, boundary attachments, escaped titles and summary manifests.
Those capabilities are preserved, not claimed as new. Positioning/serialization
were interleaved; default ordering privileged external scope and IDs; distant
routes used global bottom shelves; shared gutter tracks obscured edge identity;
HTML lacked local navigation, comparison SVG IDs were duplicated, introduced
prohibitions lacked an early summary, and there were no print/focus styles.

Before source changes both regular V11-1 installations reproduced all **176**
prior fingerprints. New captures add actual baseline/proposed comparisons for
three example families: **182** fingerprints per interpreter. Canonical data,
JSON/HTML/SVG, hashes and full declarations (including endpoint/placement IDs)
are retained in ignored `output/gate-v11-2/baseline312/` and `baseline314/`.
The established historical corpus is in ignored `output/gate-v11-1/`.

## 5. FE-03 implementation

Presentation calculates immutable geometry before SVG serialization. Zone order
uses explicit declared transitions. Each edge gets distinct side tracks and a
numbered local shelf, exact state endpoints, metadata and an ID/conduit key.
Cards show administrative ownership separately from placement; repeated boundary
attachments visibly say “Same boundary asset.” Existing useful `data-*` IDs are
retained, with source/target phases and conduit IDs added. Only actual interface
anchors receive circles; crossings never receive junction symbols.

## 6. FE-04 implementation

HTML begins with status/scope and the required interpretation sentence, then
critical required/prohibited findings, diagrams, independent outcomes/comparison
evidence, intervals/witnesses, inventory, omissions, limitations and unchanged JSON.
Introduced and resolved prohibited interval records are counted separately.
Validation explicitly leaves evaluation unassessed; counts do not assert universal
security. Baseline/proposed provenance and IDs stay separate.

## 7. Geometry architecture and immutable records

Frozen slotted dataclasses are `Point`, `Rect`, `Label`, `Anchor`, `InterfaceRow`,
`Attachment`, `ZoneBox`, `Transition`, `DevicePlacement`, `Omissions` and `Layout`.
They hold all bounds, placements, anchors, polylines, labels, identities and limits.
`calculate_layout` creates them; `serialize_svg` only emits their geometry and
fixed styles/markup. It does not invoke analytical graph construction.

## 8. Zone order and fallbacks

Kahn ordering operates on the explicit directed cross-placement zone relation.
Stable ID heaps break ready-node ties, including disconnected/isolated zones.
If a cycle leaves no ready node, the smallest remaining ID breaks that drawing
cycle; no analytical edge is removed. Duplicate relations do not overweight pairs.
No zone-name, subnet, trust, Purdue or security-rank heuristic is used.

## 9. Public option grammar and provenance

All four commands accept repeatable `--zone-order ZONE_ID` only with an HTML
`--report`. Unknown IDs use `INVALID_REFERENCE`; repeats and meaningless
combinations use `INVALID_VALUE`, category `invalid_input`, exit 2, preserving
existing output. Comparison validation uses the union; absent IDs are not invented.
Specified IDs precede deterministic remaining IDs. HTML shows preferences, full
effective order and visible order. Standalone SVG shows the visible order.
Python helpers add keyword-only `zone_order=(...)`; `build_report`/JSON are unchanged.

## 10. Orthogonal routing and complexity

Cards stack in one column per zone. Gutters reserve eight-unit per-edge tracks on
the appropriate ingress/egress side. Every transition has six points: anchor,
side track, horizontal shelf, destination track, target anchor. Shelves lie below
all cards within the affected zone interval. First-fit integer shelves may be
reused by disjoint spans; edge IDs break ties. Numbered labels avoid long edge text
near arrowheads; full IDs/conduits remain in a separate key and accessible titles.

Zone relation construction and ordering use O(I + (Z+E) log Z) work (including
stable adjacency sorting); preference filtering adds O(ZR) for R requested IDs,
bounded by the existing 1,000-zone ceiling. Detailed routing uses O(E² + EZ), E <= 48 and
Z <= 12. Placement indexing is linear plus stable sorting; card/label work is
bounded by existing limits. There is no exponential route search, recursive SCC
walk or new layout dependency. Crossings and endpoint stroke overlaps remain
possible and explicitly disclosed. One-column zones can create tall diagrams.

## 11. Boundary-device representation

One asset ID and owner appear on every placement attachment. The accessible
device-to-interface map is sorted by placement/asset and includes exact interface
IDs, including empty owner-only records. Ownership-only cards have no invented
ports. Attachment copies receive no generated link or implied forwarding.
Transport remains egress→ingress; declared forwarding remains ingress→egress.

## 12. Summary thresholds and omissions

Full mode includes exact thresholds: 12 zones, 24 assets, 24 interfaces, 48 edges.
One above any threshold activates summary. All attachment cards/interfaces/edges
are then omitted. At most the first 12 canonical zone IDs remain visible, reordered
for presentation. This preserves the exact existing JSON omission membership.
HTML/SVG disclose counts including attachment cards; HTML/JSON retain exact IDs,
all declarations and findings. Summary does not change analytical scope or invent
simplified edges. Unused conduits remain in the existing omission manifest.

## 13. HTML structure, navigation and accessibility

Generated local fragment links, a skip link, hierarchical headings, snapshot and
evidence references, semantic tables/captions/column headers, focus styles and
focusable scroll regions operate without scripts. Comparison SVG markers and
label clips are namespaced by snapshot. Automated tests verify unique IDs and
resolving link/marker/clip targets. Findings use words and borders as well as color.
Actual screen-reader behavior and keyboard focus are **not verified**.

## 14. Offline security, labels and print

All declaration/evidence strings pass through existing XML-safe HTML escaping.
Only generated SVG, fixed CSS and safe fragment IDs are trusted markup. CSP
retains default-src none, inline styles only, no base URL and no forms. No script,
remote font, image, external stylesheet or network resource is introduced.
Full untrusted text remains inert in titles/tables/escaped JSON.

Code-point display budgets are conservative estimates, not pixel measurements.
Finite clipping regions prevent label spill under different local fonts. Full
text remains accessible elsewhere. Long static explanatory text wraps into finite
lines. Screen diagrams retain intrinsic size with horizontal scrolling. Narrow
viewport and monochrome print rules are implemented; printed wide diagrams may
shrink, with full identifiers retained in inventory. Browser print behavior is
**not verified**; no browser conformance or accessibility certification is claimed.

## 15. Modified and added public files

Modified: `.github/workflows/ci.yml`, `src/otarchguard/{diagrams,reporting,cli}.py`,
`tests/test_reporting.py`, `README.md`, `docs/{reporting,testing-strategy,
installation,verification,limitations}.md`, `MANIFEST.in`, `tools/public-files.txt`.
Added: `tests/test_diagram_geometry.py`, `tests/test_presentation.py`,
`tools/verify_environment.py`, and this report. Generated evidence remains ignored.

## 16. Independent geometry verification

Test-side rectangle/segment predicates and an SVG M/H/V parser independently
check containment, card intersections, bounds, source/target phases and anchors,
direction, conduit/type identity, distinct parallel/reverse geometry and absence
of false junction circles. They compare against raw input dictionaries, not the
production planner. Twenty-four fixed seeds cover irregular/dense/cyclic/sparse
graphs; explicit tests cover boundary ownership-only cards, no interfaces, exact
summary boundaries, long IDs, Unicode and hostile text. Corrupt endpoints,
direction, extra junction circles and undersized bounds deliberately fail the
oracle. Frozen records are also checked. The final installed focused suites pass
**108 tests** on each interpreter (3.12: 12.01 s; 3.14: 12.48 s).

## 17. Actual visual inspection

Eleven original SVGs were rasterized with bundled sharp 0.35.5 / libvips 8.18.7
(librsvg 2.63.2) on Windows AMD64,
at width 1400 pixels. Source fixtures, SVG/HTML/PNG outputs and tool versions are
in ignored `output/gate-v11-2/visuals/`; `rasterization.json` records dimensions.
Inspected flat (1400×1774), segmented (1400×1144), remote support (1400×1471),
boundary (1400×1423), dense 48-edge (1400×1450), disconnected (1400×545),
cycles/reverse/parallel (1400×1022), no-interface (1400×1064), long Unicode/hostile
labels (1400×1463), summary (1400×158), and short multilingual labels (1400×1188).
The last render visibly includes Spanish accents, Chinese, Greek, Arabic, a
supplementary emoji and combining `e` + acute, within their card regions.

Generated files use `output/gate-v11-2/visuals/<stem>.svg`, `.png` and `.html`:

| Stem | Original declared input |
| --- | --- |
| flat | `examples/flat-plant/proposed.yaml` |
| segmented | `examples/segmented-plant/proposed.yaml` |
| remote-support | `examples/remote-support/proposed.yaml` |
| boundary | `tests/fixtures/boundary-device.yaml` |
| dense | Ignored `visuals/dense.yaml`, generated original 48-edge model |
| disconnected | Ignored `visuals/disconnected.yaml`, five zones with one declared edge |
| cycles-reverse | Ignored `visuals/cycles-reverse.yaml`, explicit cycle/reverse/parallel edges |
| empty | Ignored `visuals/empty.yaml`, one asset without an interface |
| long-unicode | Ignored `visuals/long-unicode.yaml`, long multilingual and hostile-looking names |
| summary | Ignored `visuals/summary.yaml`, thirteen zones |
| unicode-short | Ignored `visuals/unicode-short.yaml`, visible short multilingual names |

Confirmed cards/anchors remain visible, edges retain separate numbered routes,
and no reviewed route passes through an unrelated card. Corrections from the
review: static footer sentences now wrap instead of truncating; the short boundary
identity label is fully visible; external scope styling is retained. Dense and
summary whole-image thumbnails necessarily scale text down; HTML keeps intrinsic
SVG width and scrolling. Generic endpoint icons were replaced by labeled cards;
no device capability is inferred from either style.

Three actual comparison HTMLs were generated with critical findings; their markup,
references and evidence are tested. Browser opening of the local `file://` report
was blocked by the environment URL policy; no alternate-browser or server workaround
was attempted. HTML visual rendering, keyboard, narrow viewport and print behavior
are **not verified**. Owner checklist: open locally offline; Tab through skip/TOC/
scroll/details controls; follow snapshot/evidence links; inspect at 375/1280-pixel
viewports and 200% zoom; print preview in monochrome; expand witnesses/JSON as
needed; verify long identifiers and critical findings remain readable.

## 18. Valid-model analytical equivalence

Before/after verification compares 99 canonical/hash/JSON fingerprints, including
the prior corpus and three real family comparisons. JSON retains intent/exposure/
comparison results, exact intervals, diagnostic classifications and witnesses.
The full regression independently verifies replay, policy semantics, canonical
identity, native exits and atomic report failures. All **99** analytical
fingerprints match the captured baseline on both final installations. The
analytical implementation files are unchanged. Extra U+0897 accepted-text evidence
also has identical canonical/model hashes across interpreters.

## 19. Determinism

Tests cover repeated/reordered declarations, repeated preferences, namespaced
comparison outputs and unmutated JSON envelopes. Candidate captures compare new
HTML/SVG bytes across interpreters, while intentional visual changes are excluded
from old-renderer equality. No clocks, random IDs or machine paths enter reports.
All **182** candidate fingerprints match across installed Python 3.12/3.14:
99 unchanged analytical/canonical/hash observations and 83 new HTML/SVG
observations. The extra U+0897 case also matches. Repeated renders and reordered
inputs pass the report tests. Captures live in `output/gate-v11-2/final312/` and
`final314/`, distinct from historical baselines and the superseded first candidate.

## 20. Full local test results

Available environments are Windows AMD64 CPython **3.12.14** and **3.14.5**, regular
non-editable installs. Source-only development checks are not installed acceptance.
Observed final candidate results (exit 0 unless noted):

| Check | CPython 3.12.14 | CPython 3.14.5 | Evidence / limitation |
| --- | --- | --- | --- |
| Focused presentation tests | 108 passed; 12.01 s | 108 passed; 12.48 s | `final*/focused.stdout.log` |
| Full pytest | 1,056 passed; 213.28 s | 1,056 passed; 222.01 s | `final*/pytest.stdout.log`; Python offline guard enabled |
| Ruff lint / format | Passed; 76 files checked | Passed; 76 files checked | `final*/ruff-*.stdout.log` |
| Strict mypy | Passed; 52 source files | Passed; 52 source files | `final*/mypy.stdout.log` |
| pip check | Passed | Passed | `final*/pip-check.stdout.log` |
| Native offline walkthrough | 27 expected 0/1 exits | 27 expected 0/1 exits | `final*/examples.stdout.log`; no exit 1 is reclassified as 0 |
| Installed identity | 21 modules match reviewed source | 21 modules match reviewed source | `final*/installed.json`; native console version exit 0 |
| Before/after analytical evidence | 99 identical | 99 identical | `final*/fingerprints.json` |
| Cross-interpreter output | 182 identical + UCD case | 182 identical + UCD case | HTML/SVG equality is for the new renderer |
| Fixed benchmark runner | Passed; exit 0 | Passed; exit 0 | `final*/benchmark.json`; five timings plus separate allocation run |

The 3.12 routine exposure maximum is **1.237571 s**, peak traced Python allocation
**7,392,801 bytes**. On 3.14 they are **1.086750 s** and **7,599,713 bytes**.
Both meet the unchanged 30 s / 512 MiB target. The target is for
the routine exposure pipeline; it is not a comparison/report or process-RSS claim.
Sparse/deny-heavy workloads complete; dense-policy/interval-heavy workloads retain
controlled ceiling rejection evidence. Actual OS is Windows 11 build 26100, AMD64.
Linux/macOS are not locally tested.
The two final ten-step installed verification drivers each return exit 0.
No local subprocess timeout recurred. No tests were skipped or marked optional.

## 21. Static analysis and installed-package evidence

Candidate packaging changes only staged distribution metadata to
`1.0.1.dev2+gate.v11.2`; source/application version stays 1.0.1. No candidate is
published. Installed verification records actual imports, distribution metadata,
native console paths and hashes for all 21 production modules, matching source.
Both imports resolve to each interpreter's `site-packages/otarchguard`; metadata
is non-editable and native consoles resolve through that interpreter's scripts
scheme. The candidate wheel SHA-256 is
`fb2aff7f7536e8b505c89375d593538c22d3aa9428a08847a004f2a15695f6d9`.
Ruff, mypy and dependency results are recorded in section 20. No mandatory
runtime/verification dependency was introduced.

## 22. Six-job GitHub Actions implementation

`verify` uses `runs-on: matrix.os`, three native hosted OS values and two explicit
Python strings, with `fail-fast: false`, no exclusions and no allowed failures.
Checkout full history/nonpersistent credentials, read-only permissions, existing
action versions, expected-root validation, regular installation, lint/format/mypy,
pip check, full tests/native CLI, offline examples, distribution audits and fixed
benchmarks remain required. Installed identity is explicitly checked. Artifact
names include OS/Python and retention is seven days. Each job installs once; no
coverage is deduplicated away. Workflow display name changes to Python verification;
job ID remains `verify`. Owner should review expanded required-check names.

## 23. Portability review

PowerShell Core is explicitly selected on all runners; scripts no longer rely on
Windows' default shell. Offline PYTHONPATH uses workspace + `/tools/offline`, valid
on each runner. UTF-8 is explicit. Existing console resolution already uses
sysconfig and native executable names, and copied-launcher fixtures preserve mode
with copy2. Temp paths/spaces, atomic replacement, file preservation, subprocess
exits, line endings, network guard and native console behavior remain tested.
No confirmed runtime platform defect was found locally; Linux/macOS behavior
requires hosted execution. No production workaround for an assumed OS issue was added.

The shell choice is supported by the primary
[GitHub workflow syntax documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#defaultsrun)
which lists `pwsh` for all platforms. This documentation check does not substitute
for executing this project's matrix on the hosted images.

## 24. Windows timeout incident assessment

Reviewed integration 30-second guards and the focused 90-second dense-policy
comparison guard, plus example/native-launcher setup. The prior passing rerun
does not establish an application defect. No current timeout was reproduced during
development checks; final suite results follow. No blanket deadline increase,
retry, skip or assertion weakening was introduced. Local full suites run one
interpreter at a time to avoid self-imposed contention. Hosted contention remains
an observation to investigate if it recurs; retain child/process evidence then.

## 25. Remote CI status

No hosted workflow was triggered or claimed successful.

| Native runner | Python | Actual status |
| --- | --- | --- |
| windows-latest | 3.12 | PENDING REMOTE CI |
| windows-latest | 3.14 | PENDING REMOTE CI |
| ubuntu-latest | 3.12 | PENDING REMOTE CI |
| ubuntu-latest | 3.14 | PENDING REMOTE CI |
| macos-latest | 3.12 | PENDING REMOTE CI |
| macos-latest | 3.14 | PENDING REMOTE CI |

## 26. Package and Git integrity

The explicit allow-list and MANIFEST match all **97** tracked/new public files.
Exact candidate wheel/sdist audits pass on both interpreters, including metadata,
licenses, entry point, all member safety, source bytes and wheel RECORD digests.
The sdist rebuild produces identical wheel member contents. All 21 installed/wheel
production modules match reviewed source; only staged distribution version
metadata differs. Final report/document bytes are refreshed into the candidate
sdist; the installed wheel remains unchanged. See ignored
`archive-audit-final-312.json`, `archive-audit-final-314.json`, `package-integrity.json`
and `boundary.json` under `output/gate-v11-2/`.

HEAD/main/root/tag and the three original published archive checksums match the
initial state. `git diff --check` passes; nothing is staged. Public changes are
limited to the 17 files listed in section 15. No private material, cache or local
evidence enters the public manifest. No history rewrite, commit or release occurs.

## 27. Security and licensing implications

Runtime remains offline, with no mandatory dependency or new active content.
Apache-2.0 and third-party notices are unchanged. No private research/standards
materials were accessed or copied. Drawings are original synthetic declarations.
No standards conformity, deployed correctness, exploitability, risk reduction,
physical connectivity or safety assurance is claimed. The Python audit hook
guards tested Python operations, not complete OS-level network isolation.

## 28. Remaining limitations and unsuccessful attempts

Dense routes may cross/overlap at endpoints; one-column zones can be tall. Fonts
and glyph shaping vary by platform. Visual labels may truncate; full identities
remain in evidence. Large reports still retain evidence in memory. No streaming,
general layout engine, JavaScript dashboard or Gate V11-3 feature is introduced.
Browser/print/accessibility behavior and six remote combinations remain pending.

Routine development failures were corrected: first reporting checks rejected all
href attributes from the old no-navigation contract; tests now permit only safe
local fragment links and validate every target. Static typing caught variable
type reuse and importlib path typing; these were corrected. Initial PowerShell
profile access errors were avoided with `login=false`. Branch creation needed the
sandbox's approved Git-reference escalation. Local-browser file URL access was
denied; raster review remained available. No security restriction was bypassed.

Independent cross-version inspection found a presentation defect in the first
candidate: Python 3.12's Unicode 15 and Python 3.14's Unicode 16 classified U+0897
differently, changing visible text/SVG hashes. A valid name `A` + 30 U+0897 + `Z`
produced SHA-256 `fba53a7c5931f613d14932f820ba7d56fdac744f37580e45b9e785f3cb2cb9e3`
on 3.12 and `cc5fa485b8578f06e383dac5694ba24f0bff2e3bfb16d409275057fb9d22f372`
on 3.14. The corrected budget counts scalars conservatively and does not consult
runtime combining/east-Asian-width tables. Both source checks now produce the
first hash; a fixed-budget regression catches the old 3.14 behavior. This can
shorten combining sequences visually, with full original text retained in titles
and evidence. The earlier `dev1` installation/evidence is kept separately from
the final `dev2` acceptance. No analytical or canonical-text normalization changed.
The new regression was deliberately run against the pre-fix `dev1` wheel archive
on Python 3.14: **one expected failure**, native pytest exit 1, retained in
`output/gate-v11-2/ucd-red.log`. Archive import is red-test evidence, not a regular
installed-package acceptance claim. The superseded 3.12 `dev1` suite passed
1,055 tests before the extra UCD regression; final acceptance uses `dev2` only.

## 29. Principal commands and evidence

Commands used PowerShell without startup profiles, from the authoritative checkout.

```powershell
git status --porcelain=v1
git branch -vv
git log -6 --oneline
git merge-base --is-ancestor 38e27c9 main
git rev-parse main origin/main
git rev-list --max-parents=0 HEAD
git cat-file -p v1.0.1
git rev-list -n 1 v1.0.1
git switch -c codex/gate-v11-2
py -0p
Get-FileHash dist/* -Algorithm SHA256
$env:PYTHONPATH = (Resolve-Path tools/offline).Path
$env:OTARCHGUARD_OFFLINE_CHECK = '1'
.venv-verify312/Scripts/python.exe output/gate-v11-2/capture.py baseline312
.venv-verify314/Scripts/python.exe output/gate-v11-2/capture.py baseline314
```

`py -0p` reported no registered interpreters; direct environment executables
identified the two supported local versions. Ignored `capture.py` reuses the
historical V11-1 input corpus; it is local verification tooling, not a dependency.
Development source checks temporarily used resolved `src` PYTHONPATH, never for
installed acceptance:

```powershell
.venv-verify312/Scripts/python.exe -m pytest tests/test_diagram_geometry.py tests/test_presentation.py tests/test_reporting.py -k 'not native_installed' -q --basetemp=output/gate-v11-2/source-final-focused --tb=short
.venv-verify312/Scripts/python.exe output/gate-v11-2/visuals.py
```

Bundled Node executed ignored `output/gate-v11-2/render.cjs` with installed sharp;
no rasterizer or browser was downloaded. The staged wheel build and final
installations used:

```powershell
.venv-verify312/Scripts/python.exe output/gate-v11-2/package.py
New-Item -ItemType Directory -Force output/gate-v11-2/temp312 | Out-Null
$env:TEMP = (Resolve-Path output/gate-v11-2/temp312).Path
$env:TMP = $env:TEMP
.venv-verify312/Scripts/python.exe -m pip install --no-index --no-deps --force-reinstall output/gate-v11-2/artifacts/otarchguard-1.0.1.dev2+gate.v11.2-py3-none-any.whl
.venv-verify312/Scripts/python.exe output/gate-v11-2/verify.py final312
New-Item -ItemType Directory -Force output/gate-v11-2/temp314 | Out-Null
$env:TEMP = (Resolve-Path output/gate-v11-2/temp314).Path
$env:TMP = $env:TEMP
.venv-verify314/Scripts/python.exe -m pip install --no-index --no-deps --force-reinstall output/gate-v11-2/artifacts/otarchguard-1.0.1.dev2+gate.v11.2-py3-none-any.whl
.venv-verify314/Scripts/python.exe output/gate-v11-2/verify.py final314
```

The driver saves exact executable/argument arrays, native exits and elapsed times
in `final*/checks.json`, with separate stdout/stderr logs. It uses resolved
`tools/offline` PYTHONPATH, the Python network guard, explicit UTF-8, `NO_COLOR=1`
and `TERM=dumb`. Expanded principal checks for 3.12 (3.14 uses the matching
interpreter and `final314` output names) are:

```powershell
.venv-verify312/Scripts/python.exe tools/verify_environment.py --output output/gate-v11-2/final312/installed.json
.venv-verify312/Scripts/python.exe -m pytest tests/test_diagram_geometry.py tests/test_presentation.py tests/test_reporting.py -q --basetemp=output/gate-v11-2/final312-focused --tb=short
.venv-verify312/Scripts/python.exe output/gate-v11-2/capture.py final312
.venv-verify312/Scripts/python.exe -m pytest -q --basetemp=output/gate-v11-2/final312-pytest --tb=short
.venv-verify312/Scripts/python.exe -m ruff check .
.venv-verify312/Scripts/python.exe -m ruff format --check .
.venv-verify312/Scripts/python.exe -m mypy
.venv-verify312/Scripts/python.exe -m pip check
.venv-verify312/Scripts/python.exe examples/run_examples.py
.venv-verify312/Scripts/python.exe -m benchmarks.run --output output/gate-v11-2/final312/benchmark.json
.venv-verify312/Scripts/python.exe output/gate-v11-2/integrity.py --rebuild
git diff --check
```

Final packaging/Git commands include:

```powershell
.venv-verify312/Scripts/python.exe output/gate-v11-2/package.py --sdist-only
.venv-verify312/Scripts/python.exe output/gate-v11-2/package/tools/audit_release.py output/gate-v11-2/artifacts/otarchguard-1.0.1.dev2+gate.v11.2-py3-none-any.whl output/gate-v11-2/artifacts/otarchguard-1.0.1.dev2+gate.v11.2.tar.gz --source-root output/gate-v11-2/package --output output/gate-v11-2/archive-audit-final-312.json
.venv-verify314/Scripts/python.exe output/gate-v11-2/package/tools/audit_release.py output/gate-v11-2/artifacts/otarchguard-1.0.1.dev2+gate.v11.2-py3-none-any.whl output/gate-v11-2/artifacts/otarchguard-1.0.1.dev2+gate.v11.2.tar.gz --source-root output/gate-v11-2/package --output output/gate-v11-2/archive-audit-final-314.json
.venv-verify312/Scripts/python.exe output/gate-v11-2/integrity.py --rebuild
git diff --check
git status --short
git diff --stat
```

The deliberate red regression used Python 3.14 with `dev1` archive + offline guard
in PYTHONPATH, then `-m pytest tests/test_diagram_geometry.py::test_label_budget_is_independent_of_runtime_unicode_database -q --basetemp=output/gate-v11-2/ucd-red --tb=short`.
Its expected exit 1 is distinct from all passing final checks. Ignored
verification scripts and historic captures are owner-local evidence, not required
by a fresh checkout's public tests.

## 30. Acceptance checklist

- [x] Geometry is separate from analysis, deterministic, bounded and immutable.
- [x] Exact declared IDs, endpoints, phases, conduits and logical devices remain.
- [x] Cycles/disconnected zones and explicit order have deterministic behavior.
- [x] Parallel/reverse transitions stay distinct; no phantom ports/forwarding.
- [x] Exact summary thresholds and omissions are tested and disclosed.
- [x] Required interpretation sentence is visible in SVG and HTML.
- [x] Critical requirements/prohibitions precede favorable exposure evidence.
- [x] Safe static navigation, escaping, offline CSP and complete JSON remain.
- [x] Independent geometry and corrupt-output oracles run successfully in development.
- [x] Eleven actual SVG rasterizations inspected; visual corrections made.
- [x] Browser/print/responsive limitations explicitly marked not verified.
- [x] Six native CI combinations and existing verification safeguards defined.
- [x] Final full installed checks and analytical equivalence recorded.
- [x] Final package/Git integrity review completed.
- [ ] Actual six-way hosted verification and owner acceptance.

## 31. Owner-facing summary and next actions

Local implementation and available verification are complete for owner review. The owner
decides whether checks are sufficient and whether to accept documented limitations.

1. Review Gate V11-2 and the manual browser checklist.
2. Authorize a local commit.
3. Push the development branch.
4. Let GitHub Actions execute all six native combinations.
5. Review failures or approve the PR.
6. Merge only after required checks succeed, or an explicit documented exception.

## 32. Gate V11-3 starting conditions

Begin advanced finite-scope analysis, trace and explainability only after owner
acceptance and successful CI integration (or an explicit owner exception).
Retain canonical/report baselines, geometry/security regressions and installed
verification. No V11-3 work is performed by this gate.
