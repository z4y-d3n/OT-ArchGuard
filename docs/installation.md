# Installation, parallel upgrade and offline use

**Latest published stable is [v1.5.0](https://github.com/z4y-d3n/OT-ArchGuard/releases/tag/v1.5.0), released November 6, 2026.**
Python `>=3.12` is required. The verified hosted matrix is Windows/Ubuntu/macOS
× Python 3.12/3.14. Keep [v1.4.0](#previous-stable-v140) for previous-stable
recovery and [v1.3.0](#stable-v130-first-run) for older environments.

[Assets](#obtain-and-verify-assets) · [Install](#parallel-installation) ·
[Offline](#optional-completely-offline-setup) · [First run](#verify-declarations-and-reports) ·
[Historical upgrade](#historical-workspaces-and-upgrade) · [Recovery](#revert-or-uninstall)

## Obtain and verify assets

Download the four named uploads from the
[published v1.5.0 release](https://github.com/z4y-d3n/OT-ArchGuard/releases/tag/v1.5.0).
Save them to `artifacts/` in a fresh working directory. GitHub lists its
automatically generated source archives separately.

| Published file | Purpose |
|---|---|
| [`otarchguard-1.5.0-py3-none-any.whl`](https://github.com/z4y-d3n/OT-ArchGuard/releases/download/v1.5.0/otarchguard-1.5.0-py3-none-any.whl) | Recommended regular installation |
| [`otarchguard-1.5.0.tar.gz`](https://github.com/z4y-d3n/OT-ArchGuard/releases/download/v1.5.0/otarchguard-1.5.0.tar.gz) | Source distribution, including examples, docs and verification tools |
| [`release-manifest.json`](https://github.com/z4y-d3n/OT-ArchGuard/releases/download/v1.5.0/release-manifest.json) | Source commit/tree, source inventory and archive audit |
| [`SHA256SUMS.txt`](https://github.com/z4y-d3n/OT-ArchGuard/releases/download/v1.5.0/SHA256SUMS.txt) | SHA-256 for the two distributions and manifest |

Run this PowerShell block in the fresh directory to download all four.

```powershell
$ReleaseAssets = 'https://github.com/z4y-d3n/OT-ArchGuard/releases/download/v1.5.0'
$AssetNames = @(
    'otarchguard-1.5.0-py3-none-any.whl'
    'otarchguard-1.5.0.tar.gz'
    'release-manifest.json'
    'SHA256SUMS.txt'
)
New-Item -ItemType Directory -Path artifacts -ErrorAction Stop | Out-Null
foreach ($AssetName in $AssetNames) {
    Invoke-WebRequest -UseBasicParsing -Uri "$ReleaseAssets/$AssetName" -OutFile "artifacts/$AssetName" -ErrorAction Stop
}
```

The annotated `v1.5.0` tag fixes published source
`14732d12f0a5dde5acf97ca1b552d69cfb12f1e0`. The manifest records that source,
distribution `1.5.0` and frozen native engine `1.3.0`. Its assembly-time acceptance
wording is historical; final publication and CI are recorded in the
[release checklist](release-checklist.md). Later `main` commits do not change
these assets. Do not rebuild and substitute files under the same release identity.

Compare downloads with GitHub's published SHA-256 digests (also recorded here):

| Published file | SHA-256 |
|---|---|
| `otarchguard-1.5.0-py3-none-any.whl` | `ad113d3573f877e29839bc311fa3dd2c47ebad085cc135f3de35ece93b479701` |
| `otarchguard-1.5.0.tar.gz` | `b645d10774e5fc73bdeeaf9744fadfadc1b7a1a24f1993b72319bfc70c54c94d` |
| `release-manifest.json` | `a88ffa7035586f7de4f58e7463d80d4daba8b351acca5de678335b289a664da4` |
| `SHA256SUMS.txt` | `00fe2983421081cb1221f3a532f3ccff823597fd71318e1674df06cb1b616a99` |

First verify the checksum file itself in PowerShell:

```powershell
$ChecksumHash = (Get-FileHash -LiteralPath artifacts/SHA256SUMS.txt -Algorithm SHA256 -ErrorAction Stop).Hash
if ($ChecksumHash -ine '00fe2983421081cb1221f3a532f3ccff823597fd71318e1674df06cb1b616a99') { throw 'Checksum file mismatch' }
```

Verify the complete checksum list before installation or extraction:

```powershell
$ExpectedFiles = @('otarchguard-1.5.0-py3-none-any.whl', 'otarchguard-1.5.0.tar.gz', 'release-manifest.json')
$SeenFiles = @()
foreach ($Line in Get-Content artifacts/SHA256SUMS.txt -ErrorAction Stop) {
    if ($Line -notmatch '^([0-9a-f]{64})  ([A-Za-z0-9._-]+)$') { throw 'Invalid checksum entry' }
    $ExpectedHash = $Matches[1]
    $AssetName = $Matches[2]
    if ($AssetName -notin $ExpectedFiles -or $AssetName -in $SeenFiles) { throw 'Unexpected or duplicate asset' }
    $SeenFiles += $AssetName
    $ActualHash = (Get-FileHash -LiteralPath (Join-Path artifacts $AssetName) -Algorithm SHA256 -ErrorAction Stop).Hash
    if ($ActualHash -ine $ExpectedHash) { throw "Checksum mismatch: $AssetName" }
    Write-Output "Verified $AssetName"
}
if ($SeenFiles.Count -ne $ExpectedFiles.Count) { throw 'Incomplete checksum list' }
```

On Linux, first compare `sha256sum artifacts/SHA256SUMS.txt` with the table;
on macOS use `shasum -a 256 artifacts/SHA256SUMS.txt`. Stop on any mismatch.
Then run `sha256sum --check SHA256SUMS.txt` from `artifacts/` on Linux, or
`shasum -a 256 -c SHA256SUMS.txt` on macOS. Require all three expected entries
and retain all four files. Hashes establish byte identity, not authorship or
authenticity; obtain the files and publication record through a trusted source.

## Parallel installation

Keep any known-good older environment, declaration inputs and development
workspaces. Select an installed interpreter explicitly and confirm Python >=3.12:

```powershell
$InstallPython = (Get-Command python -ErrorAction Stop).Source
& $InstallPython --version
& $InstallPython -m venv .venv-otarchguard-1.5.0
if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed' }
$EnvPython = (Resolve-Path .venv-otarchguard-1.5.0/Scripts/python.exe).Path
```

Use a fresh environment path. Install the verified wheel and check the
dependency closure and CLI version.

```powershell
& $EnvPython -m pip install artifacts/otarchguard-1.5.0-py3-none-any.whl
if ($LASTEXITCODE -ne 0) { throw 'Wheel installation failed' }
& $EnvPython -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Dependency check failed' }
$Otarchguard = Join-Path (Split-Path $EnvPython -Parent) 'otarchguard.exe'
& $Otarchguard --version
```

Expect `1.5.0`. To install from source in a separate fresh environment, use
`& $EnvPython -m pip install artifacts/otarchguard-1.5.0.tar.gz` with that
environment's Python, then repeat the dependency and version checks.
Source installation uses pip build isolation and may obtain `setuptools>=77`.
Both alternatives may obtain compatible runtime and transitive dependencies.
For an extracted, verified sdist, `& $EnvPython -m pip install .` from its
`pyproject.toml` root is another source-installation path. A moving branch or an
uncommitted checkout is not the accepted release source.

Equivalent POSIX commands use `bin/`:

```bash
python3.12 -m venv .venv-otarchguard-1.5.0
.venv-otarchguard-1.5.0/bin/python -m pip install artifacts/otarchguard-1.5.0-py3-none-any.whl
.venv-otarchguard-1.5.0/bin/python -m pip check
.venv-otarchguard-1.5.0/bin/otarchguard --version
```

Python 3.14 can be selected instead. Python 3.13 is admitted by package metadata,
but is not part of the six-job hosted matrix. See the
[published-source CI record](release-checklist.md#completed-v150-publication-record);
do not infer unexecuted interpreter/platform checks.

## Optional completely offline setup

The release ships no dependency wheelhouse. Ordinary installation may download
dependencies; the application wheel alone is insufficient if they are missing.
Before disconnecting, use the target OS/CPU/Python to prepare a complete wheelhouse:

```powershell
& $EnvPython -m pip download --only-binary=:all: --dest wheelhouse artifacts/otarchguard-1.5.0-py3-none-any.whl
```

Review and retain the downloaded dependency closure. With application assets in
`artifacts/` and dependency wheels in `wheelhouse/`:

```powershell
& $EnvPython -m pip install --no-index --find-links wheelhouse artifacts/otarchguard-1.5.0-py3-none-any.whl
& $EnvPython -m pip check
```

For the optional offline sdist path, also download its build backend **before
disconnecting**:

```powershell
& $EnvPython -m pip download --only-binary=:all: --dest wheelhouse 'setuptools>=77'
```

After disconnecting, install that backend from the wheelhouse first, then build
without isolation:

```powershell
& $EnvPython -m pip install --no-index --find-links wheelhouse 'setuptools>=77'
& $EnvPython -m pip install --no-index --find-links wheelhouse --no-build-isolation artifacts/otarchguard-1.5.0.tar.gz
& $EnvPython -m pip check
```

`--no-index` supplies no missing packages. `--no-deps` skips dependency resolution
and should be used only with an independently approved installed closure.
Runtime analysis and static reports need no DNS, sockets, web API, telemetry,
external font, CDN, browser JavaScript or remote rendering service. A test hook
that denies Python network operations is evidence for tested workflows, not a
physical air-gap guarantee.

## Verify declarations and reports

After the wheel installation, extract the matching sdist and use its fictional
model from the same fresh directory. Run these PowerShell steps from the
[Quick Start](../README.md#quick-start--5-minutes) with the environment above.

```powershell
tar -xf artifacts/otarchguard-1.5.0.tar.gz
if ($LASTEXITCODE -ne 0) { throw 'Source archive extraction failed' }
& $Otarchguard explore otarchguard-1.5.0/examples/remote-support/proposed.yaml --output report
if ($LASTEXITCODE -ne 0) { throw 'Explorer report generation failed' }
Invoke-Item .\report\index.html
```

The source archive provides examples, documentation and source. Extracting it
requires only the archive and `tar`. Use a fresh report path for each run.

<a id="candidate-first-report-on-linuxmacos"></a>

### Published first report on Linux/macOS

After downloading and verifying the published v1.5.0 assets as above, use a fresh
folder and an installed Python 3.12 (or select Python 3.14 explicitly):

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install artifacts/otarchguard-1.5.0-py3-none-any.whl
.venv/bin/python -m pip check
.venv/bin/otarchguard --version
tar -xf artifacts/otarchguard-1.5.0.tar.gz
.venv/bin/otarchguard explore otarchguard-1.5.0/examples/remote-support/proposed.yaml --output report
```

Open `report/index.html` in a local browser: `open report/index.html` on macOS
or `xdg-open report/index.html` on a Linux desktop. These are POSIX equivalents
of the Windows Quick Start. Published-source CI passed on both platforms;
that does not establish a manual local-browser review. All report resources are local.

### Further native checks

After installation, preserve the full environment paths and verify identity:

```powershell
& $EnvPython -m pip check
$Otarchguard = Join-Path (Split-Path $EnvPython -Parent) 'otarchguard.exe'
& $Otarchguard --version
& $Otarchguard --help
& $EnvPython -c "import importlib.metadata as m,otarchguard; print(m.version('otarchguard')); print(otarchguard.DISTRIBUTION_VERSION); print(otarchguard.NATIVE_ENGINE_VERSION); print(otarchguard.__version__); print(otarchguard.__file__)"
```

Expect `1.5.0` from the console, distribution metadata and `DISTRIBUTION_VERSION`;
expect `1.3.0` from native engine and historical `__version__`. The import must
resolve inside the selected environment's `site-packages`, not the checkout's
`src/`. Schema-1 native models need no migration.

Start the following example in the verified tagged checkout or extracted
sdist root containing `examples/`. Wheels do not include models/examples;
wheel-only users must provide their own supported model and declared IDs.

```powershell
$Model = (Resolve-Path examples/remote-support/baseline.yaml).Path
New-Item -ItemType Directory -Force output | Out-Null
& $Otarchguard validate $Model
& $Otarchguard check $Model
& $Otarchguard exposure $Model --scenario support_scope --report output/exposure.html
& $Otarchguard trace $Model --source it --service svc_plc --policy-evidence --report output/trace.json --report-format json
```

Inspect each native exit: 0 completes successfully, 1 reports failed intents,
and 2 rejects input/limits/invocation or fails execution. A completed unreachable
or mixed-port trace exits 0 and does not assess intents. Fatal native report
failures preserve old output, so an old report is not evidence of a successful
new run. Keep outputs separate from inputs; see [trace](trace.md) and
[reporting](reporting.md).

Continue through the [Architecture Explorer](../examples/explorer/README.md),
[document import](../examples/import-studio/documents/README.md),
[capture tutorial](../examples/capture-studio/README.md),
[industrial metadata](v14-foundation.md), [historical lifecycle](v14-history.md),
[drift](v14-drift.md) and [Historical Explorer](v14-historical-explorer.md).
Use fresh output directories and exact IDs returned by preceding commands.
Approvals in the synthetic walkthroughs are fictional fixture-author assertions.

## Historical workspaces and upgrade

Native schema-1 declarations remain supported. Workspace-v1 snapshot migration
to workspace-v2 is explicit and preserves source snapshot bytes. It does not
create analytical revisions or approve a baseline.

Stable `1.5.0` is a distinct source-bound historical producer. Original
`1.5.0.dev3` analytical revisions require their compatible source for replay.
The same boundary applies to older producers, including the earlier
`1.4.0.dev1` to `1.4.0` transition. Whole-workspace validation rejects an unknown
implementation even where native semantics are equivalent.

Preserve the original environment and an untouched workspace for inspection
and replay. For new `1.5.0` analysis, create a fresh workspace-v2, import retained
validated observations, attach the required authorized sources, create new
analytical revisions and explicitly review a new baseline. Approvals remain
bound to the original revisions. Preserve their IDs and digests.
See the [V15-06 compatibility record](development/v15-06-compatibility.md).

Portable Explorer integrity verification does not establish source-dependent
replay compatibility, analytical truth or authenticated authorship. Keep the
compatible source environment with evidence that requires reproduction.

## Revert or uninstall

If evaluation fails, preserve inputs, outputs and logs. For supported inputs,
select the retained [v1.4.0 environment](#previous-stable-v140) by its full
executable path. Preserve the exact producer for historical replay, including
older v1.3.0 environments where applicable. Historical workspaces have no
demonstrated safe downgrade path.

To uninstall only the selected v1.5.0 application:

```powershell
& $EnvPython -m pip uninstall otarchguard
```

This removes the installed distribution; it does not migrate or delete workspaces,
inputs or generated reports, and pip may retain dependency packages. Keep those
data independently backed up. Never remove the retained known-good environment
or alter historical release archives as part of rollback.

## Previous stable v1.4.0

For recovery, save the four original [v1.4.0 assets](https://github.com/z4y-d3n/OT-ArchGuard/releases/tag/v1.4.0)
under `artifacts/` in a fresh folder. Compare each file's SHA-256 to the
[v1.4.0 publication record](release-checklist.md#completed-v140-publication-record).
Use the following PowerShell sequence with Python `>=3.12`.

```powershell
python -m venv .venv-v140
.\.venv-v140\Scripts\python.exe -m pip install artifacts/otarchguard-1.4.0-py3-none-any.whl
.\.venv-v140\Scripts\python.exe -m pip check
.\.venv-v140\Scripts\otarchguard.exe --version
tar -xf artifacts/otarchguard-1.4.0.tar.gz
.\.venv-v140\Scripts\otarchguard.exe explore otarchguard-1.4.0/examples/remote-support/proposed.yaml --output report
Invoke-Item .\report\index.html
```

Expect distribution/CLI `1.4.0`, native engine `1.3.0` and YAML schema `1`.
The [pre-closure installation guide](https://github.com/z4y-d3n/OT-ArchGuard/blob/v1.5.0/docs/installation.md#parallel-installation)
preserves the optional v1.4.0 sdist, POSIX and offline installation commands.

### Stable v1.3.0 first run

For older environments, obtain the wheel and source archive from the
[v1.3.0 release](https://github.com/z4y-d3n/OT-ArchGuard/releases/tag/v1.3.0)
and verify them against its published checksums and these distribution digests.

| Archive | Published SHA-256 |
|---|---|
| `otarchguard-1.3.0-py3-none-any.whl` | `ae3ae1f27afeb705ae6b85269d3c451597598184585aa6723f8e5f2ddac5adc3` |
| `otarchguard-1.3.0.tar.gz` | `23313908bfb2f6f2ead24f558562123864532fb2ea72c35b10889b15c50454b8` |

In a fresh folder with both archives under `artifacts/`, use Python `>=3.12`
and Windows PowerShell.

```powershell
python -m venv .venv-stable
.\.venv-stable\Scripts\python.exe -m pip install artifacts/otarchguard-1.3.0-py3-none-any.whl
.\.venv-stable\Scripts\python.exe -m pip check
.\.venv-stable\Scripts\otarchguard.exe --version
tar -xf artifacts/otarchguard-1.3.0.tar.gz
.\.venv-stable\Scripts\otarchguard.exe explore otarchguard-1.3.0/examples/remote-support/proposed.yaml --output stable-report
Invoke-Item .\stable-report\index.html
```

Expected `--version` output: `1.3.0`. The native `explore` command produces a local
declared-model browser; it does not evaluate all operational intents.

<a id="v150-unpublished-stable-candidate"></a>

## Historical V15-06 stable release rehearsal

The [tagged V15-06 procedure](https://github.com/z4y-d3n/OT-ArchGuard/blob/v1.5.0/docs/installation.md#v150-unpublished-stable-candidate)
preserves the original prepublication assembly and installed-package checks.
See the [acceptance record](development/v15-06-acceptance.md) for the rehearsal
results and the [publication record](release-checklist.md#completed-v150-publication-record)
for the subsequent integrated CI and published asset verification.

<a id="v15-development-candidate"></a>

## Historical V15-05 development candidate


At the V15-05 checkpoint, distribution/CLI was **`1.5.0.dev3`**, native engine
`1.3.0` and YAML schema `1`. These instructions preserve the original development
verification procedure for that checkpoint.
Use the exact reviewed committed source, not merely a moving branch name. Record
its SHA/tree with the archives; same-version development archives can differ.

### Build and audit the committed development source

From a clean Git checkout of the reviewed V15-05 commit, with Python >=3.12,
PowerShell and Git available:

```powershell
git status --short --branch
git rev-parse HEAD
git rev-parse 'HEAD^{tree}'
python -m venv .venv-dev-build
$BuildPython = (Resolve-Path .venv-dev-build/Scripts/python.exe).Path
& $BuildPython -m pip install -r tools/verification-requirements.txt
New-Item -ItemType Directory -Force output/dev-candidate | Out-Null
& $BuildPython tools/verify_source_checkout.py --output output/dev-candidate/source.json
& $BuildPython -c "from setuptools import build_meta; build_meta.build_wheel('output/dev-candidate'); build_meta.build_sdist('output/dev-candidate')"
& $BuildPython tools/audit_release.py output/dev-candidate/otarchguard-1.5.0.dev3-py3-none-any.whl output/dev-candidate/otarchguard-1.5.0.dev3.tar.gz --source-root . --output output/dev-candidate/audit.json
Get-FileHash output/dev-candidate/otarchguard-1.5.0.dev3* -Algorithm SHA256
```

Stop on any failed command; choose fresh environment/artifact paths on repeats.
Dependency installation may use the Internet. For a prepared target-specific
wheelhouse, add `--no-index --find-links wheelhouse` to that pip command.
Do not use `tools/prepare_release.py` for dev3: its v1.4.0 guard is intentional.
These archives are local acceptance artifacts, not a stable release assembly.

### Install and make the first development report

Use one regular installation alternative in a new environment. Test the wheel
and sdist separately when accepting both distributions:

```powershell
python -m venv .venv-dev-review
$DevPython = (Resolve-Path .venv-dev-review/Scripts/python.exe).Path
$DevCli = Join-Path (Split-Path $DevPython -Parent) 'otarchguard.exe'
& $DevPython -m pip install output/dev-candidate/otarchguard-1.5.0.dev3-py3-none-any.whl
# OR, in a separate fresh environment:
# & $DevPython -m pip install output/dev-candidate/otarchguard-1.5.0.dev3.tar.gz
& $DevPython -I tools/verify_v15_04_transition.py --source-only --output output/dev-candidate/authorized.json
& $DevPython tools/verify_environment.py --output output/dev-candidate/environment.json
& $DevPython -m pip check
& $DevCli --version
& $DevCli --help
& $DevPython -c "import sys,importlib.metadata as m,otarchguard; print(sys.executable); print(m.version('otarchguard')); print(otarchguard.__file__); print(otarchguard.NATIVE_ENGINE_VERSION)"
New-Item -ItemType Directory -Force output/dev-examples | Out-Null
tar -xf output/dev-candidate/otarchguard-1.5.0.dev3.tar.gz -C output/dev-examples
$DevModel = 'output/dev-examples/otarchguard-1.5.0.dev3/examples/remote-support/proposed.yaml'
& $DevCli validate $DevModel
& $DevCli explore $DevModel --output output/dev-first-report
Invoke-Item output/dev-first-report/index.html
```

Expect metadata/console `1.5.0.dev3`, native engine `1.3.0`, imports from this
environment's `site-packages` and validation/Explorer exits 0. Authorization runs
before importing candidate runtime. The unchanged V15-04 policy compares all 97
physical modules to its approved source, independently of the new archive hashes.
Do not accept an editable install or an import from checkout `src/`.

The model above comes from the extracted matching **sdist**. Wheels contain no
tutorial data. The reviewed repository's `examples/` is another explicit source.
Continue with the existing [capture example](../examples/capture-studio/README.md)
and [historical walkthrough](v14-historical-explorer.md#fictional-walkthrough-and-owner-review);
their `tools` helpers run from the repository or extracted sdist, using the
selected installed Python, existing output parents and fresh destinations.

### Linux and macOS development equivalent

In the same clean reviewed checkout, select `python3.12` (or `python3.14`), create
`.venv-dev-build`, and use `.venv-dev-build/bin/python` for the same dependency,
source-verification, `build_meta` and archive-audit commands above. Replace
PowerShell's directory creation with `mkdir -p output/dev-candidate`. Then:

```bash
python3.12 -m venv .venv-dev-review
.venv-dev-review/bin/python -m pip install output/dev-candidate/otarchguard-1.5.0.dev3-py3-none-any.whl
# Alternative in a separate environment: install the matching .tar.gz instead.
.venv-dev-review/bin/python -I tools/verify_v15_04_transition.py --source-only --output output/dev-candidate/authorized.json
.venv-dev-review/bin/python tools/verify_environment.py --output output/dev-candidate/environment.json
.venv-dev-review/bin/python -m pip check
.venv-dev-review/bin/otarchguard --version
.venv-dev-review/bin/otarchguard --help
.venv-dev-review/bin/python -c "import sys,importlib.metadata as m,otarchguard; print(sys.executable); print(m.version('otarchguard')); print(otarchguard.__file__); print(otarchguard.NATIVE_ENGINE_VERSION)"
mkdir -p output/dev-examples
tar -xf output/dev-candidate/otarchguard-1.5.0.dev3.tar.gz -C output/dev-examples
.venv-dev-review/bin/otarchguard validate output/dev-examples/otarchguard-1.5.0.dev3/examples/remote-support/proposed.yaml
.venv-dev-review/bin/otarchguard explore output/dev-examples/otarchguard-1.5.0.dev3/examples/remote-support/proposed.yaml --output output/dev-first-report
```

Open with `open output/dev-first-report/index.html` on macOS or
`xdg-open output/dev-first-report/index.html` on a Linux desktop. These commands
receive static review here; executed platform results are in the
[V15-05 matrix](development/v15-05-installation-matrix.md).

For offline dev3, substitute the matching local dev3 archive in the
[wheelhouse procedure](#optional-completely-offline-setup). For sdists, preinstall
the backend from that wheelhouse and use `--no-build-isolation`; retain
`--no-index --find-links wheelhouse` for runtime dependency resolution. Run
`pip check` afterwards. This does not prove installation on another target or
physical air-gap isolation.

### Development evidence recovery

Dev1, dev2 and dev3 analytical producers have distinct source identities; a
distribution source change can affect analytical revisions even if native
semantics stay equivalent. V15-05 changes only documentation/inventories and
preserves dev3 runtime bytes, so it introduces no new analytical producer.
Historical renderer identity remains separately versioned as
`1.5.0.dev1-historical-explorer.1` because its bound sources are unchanged.

Keep the original compatible environment, exact source and untouched workspace,
including approvals. A newer runtime rejecting replay does not mean evidence is
lost. Use the original runtime for replay; create and explicitly review new
producer-dependent revisions separately. There is no automatic cross-producer
migration or inherited approval. Portable integrity proves neither authorship nor
compatible analytical replay. See [V15-04 compatibility](development/v15-04-compatibility.md)
and the [original V15-02 contract](development/v15-02-compatibility-contract.md).

## First-run recovery

| Problem | Recovery |
|---|---|
| Python version mismatch | Check the selected interpreter's `--version`; recreate the environment with Python >=3.12. Do not bypass `Requires-Python`. |
| Missing runtime dependency | Install through that environment's `python -m pip`, with the archive and complete dependency closure; run `pip check`. |
| Missing build backend | For source installs, allow build isolation to obtain `setuptools>=77`, or preinstall it from the prepared wheelhouse before `--no-build-isolation`. |
| Wrong environment or editable import | Check `sys.executable`, metadata, module path and the full console path; use a fresh regular installation. Activation alone is insufficient evidence. |
| Wheel-only install lacks examples | Extract the matching verified sdist or use the reviewed repository; do not expect `examples/` in `site-packages`. |
| Occupied output directory | Preserve it and choose a fresh destination; do not treat a previous report as the new run's result. |
| Missing output parent | Create the parent first; leave the report destination itself absent. |
| Invalid model | Run `validate`, inspect its diagnostics and correct the declaration against the [schema](yaml-schema-v1.md); do not suppress errors. |
| Unsupported capture | Check supported linktypes/formats and limits in [PCAP Evidence Studio](pcap-evidence-studio.md); retain unsupported/limited status, never infer blocking or absence. |
| Offline install cannot resolve a package | Prepare the missing target-compatible wheels while connected, including transitive dependencies/backend; retry in a fresh environment. `--no-deps` cannot repair the closure. |
| Wrong source-bound historical runtime | Preserve workspace/approvals and select the retained exact producer for replay; portable verification alone cannot authorize replay in a newer producer. |

