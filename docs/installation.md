# Installation, parallel upgrade and offline use

**Latest published stable is [v1.4.0](https://github.com/z4y-d3n/OT-ArchGuard/releases/tag/v1.4.0), released November 2, 2026.**
Keep [v1.3.0](https://github.com/z4y-d3n/OT-ArchGuard/releases/tag/v1.3.0) as the
previous stable/recovery option. Python metadata requires `>=3.12`;
the verified hosted matrix is Windows/Ubuntu/macOS × Python 3.12/3.14. It is not
a claim that every future Python release has been tested.

[Assets](#obtain-and-verify-assets) · [Install](#parallel-installation) ·
[Offline](#optional-completely-offline-setup) · [First run](#verify-declarations-and-reports) ·
[Historical upgrade](#historical-workspaces-and-upgrade) · [Recovery](#revert-or-uninstall)

## Obtain and verify assets

Download the four named assets from the
[published v1.4.0 release](https://github.com/z4y-d3n/OT-ArchGuard/releases/tag/v1.4.0),
using its **Assets** list rather than GitHub's automatically generated source
archives. Copy all four matching files to `artifacts/` in a fresh working directory:

| Published file | Purpose |
|---|---|
| `otarchguard-1.4.0-py3-none-any.whl` | Recommended regular installation |
| `otarchguard-1.4.0.tar.gz` | Source distribution, including examples, docs and verification tools |
| [`release-manifest.json`](https://github.com/z4y-d3n/OT-ArchGuard/releases/download/v1.4.0/release-manifest.json) | Source commit/tree, source inventory and archive audit |
| [`SHA256SUMS.txt`](https://github.com/z4y-d3n/OT-ArchGuard/releases/download/v1.4.0/SHA256SUMS.txt) | SHA-256 for the two distributions and manifest |

The annotated `v1.4.0` tag fixes published source
`7d6b158f863308dfcd7d10b673bfbe2692f29b8b`. The manifest records that source,
distribution `1.4.0` and frozen native engine `1.3.0`. Its assembly-time acceptance
wording is historical; final publication and CI are recorded in the
[release checklist](release-checklist.md). Later `main` commits do not change
these assets. Do not rebuild and substitute files under the same release identity.

Compare downloads with GitHub's published SHA-256 digests (also recorded here):

| Published file | SHA-256 |
|---|---|
| `otarchguard-1.4.0-py3-none-any.whl` | `fdaaa37e920c63ed0d0b5fc6b07361de9f4df6957bf885c4e9f8a6ac59051abf` |
| `otarchguard-1.4.0.tar.gz` | `1636ebc32aa009becaeb1b21d02cc7942588f5872070949d52a38581626778f2` |
| `release-manifest.json` | `a8b0ccf323589c554ba2fa3e8f88f34621ae540e795c0eb7807216add5ef89aa` |
| `SHA256SUMS.txt` | `a7474178f5472acb646eeef0c7b5c1f94ec657644bf376ca9cde0afa0ab351f8` |

First verify the checksum file itself in PowerShell:

```powershell
$ChecksumHash = (Get-FileHash -LiteralPath artifacts/SHA256SUMS.txt -Algorithm SHA256 -ErrorAction Stop).Hash
if ($ChecksumHash -ine 'a7474178f5472acb646eeef0c7b5c1f94ec657644bf376ca9cde0afa0ab351f8') { throw 'Checksum file mismatch' }
```

Verify the complete checksum list before installation or extraction:

```powershell
$ExpectedFiles = @('otarchguard-1.4.0-py3-none-any.whl', 'otarchguard-1.4.0.tar.gz', 'release-manifest.json')
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

For known-good v1.3.0 recovery, the published distribution SHA-256 values are:

| Archive | SHA-256 |
|---|---|
| `otarchguard-1.3.0-py3-none-any.whl` | `ae3ae1f27afeb705ae6b85269d3c451597598184585aa6723f8e5f2ddac5adc3` |
| `otarchguard-1.3.0.tar.gz` | `23313908bfb2f6f2ead24f558562123864532fb2ea72c35b10889b15c50454b8` |

These hashes describe published v1.3.0 assets only. Do not relabel another archive.

## Parallel installation

Keep the known-good v1.3.0 environment, declaration inputs and development
workspaces. Select an installed interpreter explicitly and confirm Python >=3.12:

```powershell
$InstallPython = (Get-Command python -ErrorAction Stop).Source
& $InstallPython --version
& $InstallPython -m venv .venv-otarchguard-1.4.0
$EnvPython = (Resolve-Path .venv-otarchguard-1.4.0/Scripts/python.exe).Path
```

Use a fresh environment path; activation is optional. Run **one** installation
alternative, using the already verified files:

```powershell
& $EnvPython -m pip install artifacts/otarchguard-1.4.0-py3-none-any.whl
# OR install independently from the source distribution:
& $EnvPython -m pip install artifacts/otarchguard-1.4.0.tar.gz
```

Source installation uses pip build isolation and may obtain `setuptools>=77`.
Both alternatives may obtain compatible runtime and transitive dependencies.
For an extracted, verified sdist, `& $EnvPython -m pip install .` from its
`pyproject.toml` root is another source-installation path. A moving branch or an
uncommitted checkout is not the accepted release source.

Equivalent POSIX commands use `bin/`:

```bash
python3.12 -m venv .venv-otarchguard-1.4.0
.venv-otarchguard-1.4.0/bin/python -m pip install artifacts/otarchguard-1.4.0-py3-none-any.whl
.venv-otarchguard-1.4.0/bin/python -m pip check
.venv-otarchguard-1.4.0/bin/otarchguard --version
```

Python 3.14 can be selected instead. Python 3.13 is admitted by package metadata,
but is not part of the six-job hosted matrix. See the
[published-source CI record](release-notes-1.4.0.md#verification-and-owner-gates);
do not infer unexecuted interpreter/platform checks.

## Optional completely offline setup

The release ships no dependency wheelhouse. Ordinary installation may download
dependencies; the application wheel alone is insufficient if they are missing.
Before disconnecting, use the target OS/CPU/Python to prepare a complete wheelhouse:

```powershell
& $EnvPython -m pip download --only-binary=:all: --dest wheelhouse artifacts/otarchguard-1.4.0-py3-none-any.whl
```

Review and retain the downloaded dependency closure. With application assets in
`artifacts/` and dependency wheels in `wheelhouse/`:

```powershell
& $EnvPython -m pip install --no-index --find-links wheelhouse artifacts/otarchguard-1.4.0-py3-none-any.whl
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
& $EnvPython -m pip install --no-index --find-links wheelhouse --no-build-isolation artifacts/otarchguard-1.4.0.tar.gz
& $EnvPython -m pip check
```

`--no-index` supplies no missing packages. `--no-deps` skips dependency resolution
and should be used only with an independently approved installed closure.
Runtime analysis and static reports need no DNS, sockets, web API, telemetry,
external font, CDN, browser JavaScript or remote rendering service. A test hook
that denies Python network operations is evidence for tested workflows, not a
physical air-gap guarantee.

## Verify declarations and reports

For a first report from a wheel and matching source archive, use the
[published v1.4.0 Quick Start](../README.md#quick-start--5-minutes). The source archive
contains the fictional models; the wheel contains the runtime application.
Extracting examples does not install the source or require Git. Choose fresh
environment and report directories.

### Stable v1.3.0 first run

This is the **previous stable release and rollback path**. Obtain and verify the
published v1.3.0 wheel and source archive using that
release's manifest and `SHA256SUMS.txt`. In a fresh folder with both archives
under `artifacts/`, use Python >=3.12 and Windows PowerShell:

```powershell
python -m venv .venv-stable
.\.venv-stable\Scripts\python.exe -m pip install artifacts/otarchguard-1.3.0-py3-none-any.whl
.\.venv-stable\Scripts\python.exe -m pip check
.\.venv-stable\Scripts\otarchguard.exe --version
tar -xf artifacts/otarchguard-1.3.0.tar.gz
.\.venv-stable\Scripts\otarchguard.exe explore otarchguard-1.3.0/examples/remote-support/proposed.yaml --output stable-report
Invoke-Item .\stable-report\index.html
```

This uses the previous published release. Expected
`--version` output: `1.3.0`. The native `explore` command produces a local
declared-model browser; it does not evaluate all operational intents.

<a id="candidate-first-report-on-linuxmacos"></a>

### Published first report on Linux/macOS

After downloading and verifying the published v1.4.0 assets as above, use a fresh
folder and an installed Python 3.12 (or select Python 3.14 explicitly):

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install artifacts/otarchguard-1.4.0-py3-none-any.whl
.venv/bin/python -m pip check
.venv/bin/otarchguard --version
tar -xf artifacts/otarchguard-1.4.0.tar.gz
.venv/bin/otarchguard explore otarchguard-1.4.0/examples/remote-support/proposed.yaml --output report
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

Expect `1.4.0` from the console, distribution metadata and `DISTRIBUTION_VERSION`;
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

Existing `1.4.0.dev1` analytical revisions bind the producer's exact source,
including `__init__.py`. The distribution-only transition to `1.4.0` therefore
makes those revisions incompatible with this producer. Whole-workspace validation
rejects an unknown implementation even when the underlying native semantics are
unchanged. Do not rewrite hashes, analysis IDs, reviews or approvals to bypass it.

Preserve the exact old environment and an untouched copy of its workspace for
inspection/replay. For new `1.4.0` work, create a fresh workspace-v2, import retained
validated observations, attach the required authorized sources, create new
analytical revisions and explicitly review a new baseline. Retain the old
workspace as historical evidence. There is no automatic cross-source approval
migration or demonstrated safe downgrade of historical data.

Portable Explorer integrity verification does not establish source-dependent
replay compatibility, analytical truth or authenticated authorship. Keep the
compatible source environment with evidence that requires reproduction.

## Revert or uninstall

If evaluation fails, preserve inputs, outputs and logs, stop using the new v1.4.0
environment and invoke the retained v1.3.0 executable by its full path. Do not
feed a new historical workspace to an older release and assume compatibility.
To recreate known-good v1.3.0, use its original published assets and a separate
environment, then verify its version, dependency closure and expected examples.

To uninstall only the selected v1.4.0 application:

```powershell
& $EnvPython -m pip uninstall otarchguard
```

This removes the installed distribution; it does not migrate or delete workspaces,
inputs or generated reports, and pip may retain dependency packages. Keep those
data independently backed up. Never remove the retained known-good environment
or alter historical release archives as part of rollback.
## v1.5.0 unpublished stable candidate

Current source identifies distribution/CLI `1.5.0`, native engine `1.3.0`, schema
`1`. It is unpublished. Published v1.4.0 instructions above remain valid.
From clean committed V15-06 source, using fresh output/environment paths:

```powershell
python -m venv .venv-v15-review
$CandidatePython = (Resolve-Path .venv-v15-review/Scripts/python.exe).Path
& $CandidatePython -m pip install -r tools/verification-requirements.txt
& $CandidatePython -I tools/prepare_v15_release.py --output output/v15-candidate-assets
if ($LASTEXITCODE -ne 0) { throw 'Assembly failed' }
& $CandidatePython -I tools/prepare_v15_release.py --verify --output output/v15-candidate-assets
if ($LASTEXITCODE -ne 0) { throw 'Asset verification failed' }
& $CandidatePython -m pip install --no-index --no-deps output/v15-candidate-assets/otarchguard-1.5.0-py3-none-any.whl
if ($LASTEXITCODE -ne 0) { throw 'Install failed' }
& $CandidatePython -I tools/verify_v15_06_transition.py --source-only --output output/v15-candidate-authorized.json
if ($LASTEXITCODE -ne 0) { throw 'Source authorization failed' }
& $CandidatePython tools/verify_environment.py --output output/v15-candidate-environment.json
& $CandidatePython -m pip check
& .venv-v15-review/Scripts/otarchguard.exe --version
& .venv-v15-review/Scripts/otarchguard.exe --help
& .venv-v15-review/Scripts/otarchguard.exe validate examples/remote-support/proposed.yaml
& .venv-v15-review/Scripts/otarchguard.exe explore examples/remote-support/proposed.yaml --output output/v15-first-report
```

Stop on every failed command. Dependencies are installed first; for a prepared
offline target add `--no-index --find-links wheelhouse` to their installation.
Independently install the matching `otarchguard-1.5.0.tar.gz` in another fresh
environment with the same dependencies and `--no-index --no-deps
--no-build-isolation`, then repeat authorization/environment/CLI checks.
Helpers/examples come from reviewed source or the matching extracted sdist;
wheels contain runtime modules only. Open the generated local `index.html`.

For Linux/macOS select `python3.12` or `python3.14`, use `bin/python` and
`bin/otarchguard`, and adapt shell syntax. Local Windows results do not validate
these platforms. The exact candidate and integrated source need six hosted jobs.
Use the new V15-06 policy/assembler; the old V15-04 policy and v1.4 assembler
intentionally reject stable source and must not be relaxed.

Stable source is a distinct historical producer. Preserve original environments
and workspaces; old approvals never transfer automatically. Portable integrity
and compatible-source replay remain separate. Consult the
[compatibility record](development/v15-06-compatibility.md) and
[owner procedure](development/v15-06-handoff-es.md).

## V15 development candidate

At the historical V15-05 checkpoint distribution/CLI was **`1.5.0.dev3`**; native engine remains
`1.3.0`, YAML schema `1`. This is unpublished development verification. The
v1.4.0 instructions above continue to describe the published stable release.
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

