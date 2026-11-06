# V15-05 — Installation matrix

Development acceptance uses Windows x64 / Python 3.14.5 and a local wheelhouse.
The [installation guide](../installation.md#v15-development-candidate) gives the
reproduction procedure. Exact commands, exits and environments are retained under
`output/v15-05/`; final commit/tree/archive identities belong in the external
`output/v15-05/final/freeze.json`, avoiding circular self-hashing.

| Scenario | Platform | Source | Actual result |
|---|---|---|---|
| Published stable installation | Windows/POSIX | Published v1.4.0 record in [release checklist](../release-checklist.md#completed-v140-publication-record) | NOT_TESTED in this gate; historical stable evidence retained |
| Development wheel | Windows x64 / Python 3.14.5 | Locally audited dev3 wheel | PASS: regular install, pre-import authorization, 97 exact modules, CLI/help/validate, pip check |
| Development sdist | Windows x64 / Python 3.14.5 | Locally audited dev3 sdist | PASS: regular install with preinstalled backend and no build isolation; same identity/smokes |
| Offline wheelhouse | Windows x64 / Python 3.14.5 | Existing target-compatible local closure/backend | PASS: both installs with no index and local wheels; physical disconnection NOT_TESTED |
| First Explorer | Both regular installations | Fictional model from extracted matching sdist | PASS: each report has 54 files, 52 HTML pages, 781 audited links, zero broken links |
| Historical recovery | Original compatible producer | [V15-04 executed boundary](v15-04-compatibility.md#executed-corrected-transition) | NOT_TESTED anew; historical evidence retained |
| Development Linux/macOS commands | POSIX / Python 3.12 or 3.14 | Same guide and source | Static review only; execution NOT_TESTED locally |

Baseline [main push CI 41918807010](https://github.com/z4y-d3n/OT-ArchGuard/actions/runs/41918807010)
completed successfully in all six Windows/Ubuntu/macOS × Python 3.12/3.14 jobs
for `b62f816a88d8cf61e2798c368e8b277621b5d5bc`. It does not validate the new
documentation commit. V15-05 hosted CI remains pending owner publication.

No claim is made of physical air-gap testing, universal wheelhouse portability,
new browser/keyboard/zoom acceptance or a new online-index installation. Preparing
a closure requires connectivity or a separately supplied complete local mirror.
Preserve original historical environments/workspaces and approvals for replay;
portable bundle integrity does not establish compatible analytical reproduction.

Functional campaign source: `f9d5c15dd287643f67dc3c292e2eb74b75fbfa15`.
Its archives, imports, 42 focused tests and command exits are in
`output/v15-05/candidate/`. The final documentation closure is rebuilt, audited
and regularly reinstalled with the same approved 97 modules; its identities are
in `output/v15-05/final/`. No second full analytical suite is claimed.
Stable release metadata/digests were rechecked through GitHub's read-only API
and match the retained guide (`output/v15-05/stable-assets.json`); that check
is not a fresh stable installation.
