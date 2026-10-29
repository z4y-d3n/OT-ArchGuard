# Installation, parallel upgrade and offline use

**Published stable is [v1.3.0](https://github.com/z4y-d3n/OT-ArchGuard/releases/tag/v1.3.0).**
This guide also prepares a separate **v1.4.0 local release-candidate environment**.
The candidate is not a published stable release. Python metadata requires `>=3.12`;
the required hosted matrix is Windows/Ubuntu/macOS × Python 3.12/3.14. It is not
a claim that every future Python release has been tested.

[Assets](#obtain-and-verify-assets) · [Install](#parallel-installation) ·
[Offline](#optional-completely-offline-setup) · [First run](#verify-declarations-and-reports) ·
[Historical upgrade](#historical-workspaces-and-upgrade) · [Recovery](#revert-or-uninstall)

## Obtain and verify assets

Stable users can download the four assets from the published v1.3.0 release page.
For candidate review, obtain the four **local** files identified by the exact-source
V14-06 handoff. Repository reviewers find them in `output/v146/release-assets/`
after the local rehearsal. Copy all four to `artifacts/` in a review directory:

| Candidate file | Purpose |
|---|---|
| `otarchguard-1.4.0-py3-none-any.whl` | Recommended regular installation |
| `otarchguard-1.4.0.tar.gz` | Source distribution, including examples, docs and verification tools |
| `release-manifest.json` | Source commit/tree, source inventory and archive audit |
| `SHA256SUMS.txt` | SHA-256 for the two distributions and manifest |

There is no download link to a future v1.4 release. Following owner-authorized
publication, obtain assets from the actual published release and compare their
source/checksums with its acceptance record. Local candidate hashes do not accept
a later integration build merely because its filenames are the same.

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

On Linux, run `sha256sum --check SHA256SUMS.txt` from `artifacts/`; on macOS use
`shasum -a 256 -c SHA256SUMS.txt`. Require all three expected entries and retain
all four files. Hashes establish byte identity, not authorship or authenticity;
obtain the files and acceptance record through a trusted source.

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
$CandidatePython = (Get-Command python -ErrorAction Stop).Source
& $CandidatePython --version
& $CandidatePython -m venv .venv-otarchguard-1.4.0
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
but is not part of the six-job hosted matrix. Consult the exact candidate handoff
for actual additional interpreter checks; do not infer unexecuted results.

## Optional completely offline setup

The release ships no dependency wheelhouse. Before disconnecting, prepare a
reviewed complete wheelhouse for the target OS/CPU/Python containing compatible
runtime dependencies and their transitive closure. With application assets in
`artifacts/` and dependency wheels in `wheelhouse/`:

```powershell
& $EnvPython -m pip install --no-index --find-links wheelhouse artifacts/otarchguard-1.4.0-py3-none-any.whl
& $EnvPython -m pip check
```

For offline sdist installation, install the build backend from that wheelhouse
first, then build without isolation:

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

Start the following example in the verified candidate checkout or extracted
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

If evaluation fails, preserve inputs, outputs and logs, stop using the candidate
environment and invoke the retained v1.3.0 executable by its full path. Do not
feed a new historical workspace to an older release and assume compatibility.
To recreate known-good v1.3.0, use its original published assets and a separate
environment, then verify its version, dependency closure and expected examples.

To uninstall only the candidate application:

```powershell
& $EnvPython -m pip uninstall otarchguard
```

This removes the installed distribution; it does not migrate or delete workspaces,
inputs or generated reports, and pip may retain dependency packages. Keep those
data independently backed up. Never remove the retained known-good environment
or alter historical release archives as part of rollback.
