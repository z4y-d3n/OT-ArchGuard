# Installation, parallel upgrade and offline use

**[v1.3.0](https://github.com/z4y-d3n/OT-ArchGuard/releases/tag/v1.3.0) is the latest
stable release.** It requires **Python 3.12 or later**. Windows, Ubuntu and macOS
with Python 3.12 and 3.14 passed the
[final integration CI](https://github.com/z4y-d3n/OT-ArchGuard/actions/runs/40273411275)
for release commit `10d7de6c416ec6f0ee364c671ebe9292ee69e672`. Other interpreter
versions are not part of that six-configuration verification.

[Download and verify](#download-and-verify-release-assets) ·
[Parallel installation](#parallel-installation) ·
[Offline setup](#optional-completely-offline-setup) ·
[Verification](#verify-declarations-and-reports) · [Revert](#revert)

## Download and verify release assets

Use the published assets attached to
[release v1.3.0](https://github.com/z4y-d3n/OT-ArchGuard/releases/tag/v1.3.0):

- [`otarchguard-1.3.0-py3-none-any.whl`](https://github.com/z4y-d3n/OT-ArchGuard/releases/download/v1.3.0/otarchguard-1.3.0-py3-none-any.whl): recommended installation archive.
- [`otarchguard-1.3.0.tar.gz`](https://github.com/z4y-d3n/OT-ArchGuard/releases/download/v1.3.0/otarchguard-1.3.0.tar.gz): source distribution, including examples.
- [`release-manifest.json`](https://github.com/z4y-d3n/OT-ArchGuard/releases/download/v1.3.0/release-manifest.json): source, package and verification provenance.
- [`SHA256SUMS.txt`](https://github.com/z4y-d3n/OT-ArchGuard/releases/download/v1.3.0/SHA256SUMS.txt): checksums for both distributions and the release manifest.

Download all four files into a working directory's `artifacts/` folder. For example,
in PowerShell:

~~~powershell
$ReleaseUrl = 'https://github.com/z4y-d3n/OT-ArchGuard/releases/download/v1.3.0'
$ReleaseFiles = @('otarchguard-1.3.0-py3-none-any.whl', 'otarchguard-1.3.0.tar.gz', 'release-manifest.json', 'SHA256SUMS.txt')
New-Item -ItemType Directory -Force artifacts | Out-Null
foreach ($ReleaseFile in $ReleaseFiles) {
    Invoke-WebRequest -Uri "$ReleaseUrl/$ReleaseFile" -OutFile (Join-Path artifacts $ReleaseFile) -ErrorAction Stop
}
~~~

Verify all entries before installing or extracting:

~~~powershell
Get-Content artifacts/SHA256SUMS.txt | Where-Object { $_.Trim() } | ForEach-Object {
    $ExpectedHash, $FileName = $_ -split '\s+', 2
    $ActualHash = (Get-FileHash -LiteralPath (Join-Path artifacts $FileName.TrimStart('*')) -Algorithm SHA256 -ErrorAction Stop).Hash
    if ($ActualHash -ine $ExpectedHash) { throw "Checksum mismatch: $FileName" }
    Write-Output "Verified $FileName"
}
~~~

On Linux, run `sha256sum --check SHA256SUMS.txt` from `artifacts/`.
On macOS, use `shasum -a 256 -c SHA256SUMS.txt` there instead.
Keep all three listed files alongside the checksum file for these checks.

The published distribution hashes are:

| Archive | SHA-256 |
| --- | --- |
| `otarchguard-1.3.0-py3-none-any.whl` | `ae3ae1f27afeb705ae6b85269d3c451597598184585aa6723f8e5f2ddac5adc3` |
| `otarchguard-1.3.0.tar.gz` | `23313908bfb2f6f2ead24f558562123864532fb2ea72c35b10889b15c50454b8` |

Obtain the archives and checksum file from the trusted release page. Checksums
establish byte identity, not authenticity by themselves. Earlier candidate
archives with the same versioned filenames have different hashes; use the
published assets above.

## Parallel installation

Keep the known-good environment and copies of declarations. From your working
directory, select an installed Python explicitly and confirm it is at least 3.12:

~~~powershell
$Python = (Get-Command python).Source
& $Python --version
& $Python -m venv .venv-otarchguard-1.3.0
$EnvPython = (Resolve-Path .venv-otarchguard-1.3.0/Scripts/python.exe).Path
~~~

Use a new environment path for each evaluation; activation is optional.
A fresh environment has no application dependencies. Installation can access
your configured package index for compatible runtime dependencies and, for a
source build, the `setuptools>=77` backend. Runtime analysis and generated reports
require no network service. For disconnected installation, prepare the complete
wheelhouse described below.

## Choose one installation source

Run **one** of these alternatives. The published wheel is recommended:

~~~powershell
& $EnvPython -m pip install artifacts/otarchguard-1.3.0-py3-none-any.whl
# OR the verified published source distribution:
& $EnvPython -m pip install artifacts/otarchguard-1.3.0.tar.gz
~~~

Source installation uses pip's build isolation and may download the build backend.
For an already obtained checkout at `v1.3.0` or an extracted verified sdist, run
`& $EnvPython -m pip install .` from the root containing `pyproject.toml`.
Do not treat another branch or uncommitted changes as the published source.

On POSIX, the equivalent wheel installation uses the selected interpreter:

~~~bash
python3.12 -m venv .venv-otarchguard-1.3.0
.venv-otarchguard-1.3.0/bin/python -m pip install artifacts/otarchguard-1.3.0-py3-none-any.whl
.venv-otarchguard-1.3.0/bin/python -m pip check
.venv-otarchguard-1.3.0/bin/otarchguard --version
~~~

Python 3.14 can be selected instead. POSIX launchers live in `bin/` rather than
`Scripts/`; the variable syntax elsewhere in this guide is PowerShell-specific.

## Optional completely offline setup

No dependency wheelhouse is shipped. Prepare an approved complete wheelhouse for
the target OS/CPU/Python, including compatible runtime dependencies and their
transitive dependencies. With the verified application wheel in `artifacts/`
and dependency wheels in `wheelhouse/`:

~~~powershell
& $EnvPython -m pip install --no-index --find-links wheelhouse artifacts/otarchguard-1.3.0-py3-none-any.whl
~~~

For offline checkout/sdist installation, also supply the build backend locally.
Install `setuptools>=77` from the prepared wheelhouse, then use the source command
with `--no-index --find-links wheelhouse --no-build-isolation`. Disabling build
isolation requires that backend to be installed in the chosen environment.

`--no-index` supplies no missing packages. `--no-deps` skips dependency resolution
and does not prove correctness; use it only with an already approved dependency
closure. A prepared wheelhouse is separate from the release assets and is not a
claim of fresh-OS acceptance.

## Verify declarations and reports

After installation, from the working directory:

~~~powershell
& $EnvPython -m pip check
$Otarchguard = Join-Path (Split-Path $EnvPython -Parent) 'otarchguard.exe'
& $Otarchguard --version
& $Otarchguard --help
~~~

Require version 1.3.0 and a successful dependency check. Use the full native
executable path so an unrelated installation cannot be selected. Schema-1 models
need no migration.

For the bundled example below, start in a verified checkout or extracted sdist
root containing `examples/`; keep the absolute `$EnvPython` and `$Otarchguard`
paths above. A wheel does not include examples. Wheel-only users must supply
their own model and use its declared scenario, asset and service IDs instead.

~~~powershell
$Model = (Resolve-Path examples/remote-support/baseline.yaml).Path
New-Item -ItemType Directory -Force output | Out-Null
& $Otarchguard validate $Model
& $Otarchguard check $Model
& $Otarchguard exposure $Model --scenario support_scope --report output/exposure.html
& $Otarchguard trace $Model --source it --service svc_plc --policy-evidence --report output/trace.json --report-format json
~~~

Inspect the native exit status. Exit 1 is completed failed-intent evidence;
exit 2 is a failed invocation that preserves any old report. A completed
unreachable trace exits 0. Reports use offline HTML/SVG without remote scripts
or assets; JSON trace contains the finite query evidence. An old preserved report
does not establish a successful new run. See [reporting](reporting.md) and
[trace](trace.md). Keep output files separate from model inputs.

The final PCAP Evidence Explorer's second human browser review passed all six
criteria, including navigation, interpretation, legibility and offline keyboard
operation. See the [published release record](https://github.com/z4y-d3n/OT-ArchGuard/releases/tag/v1.3.0)
for release verification and the [capture guide](pcap-evidence-studio.md) for the
supported passive-analysis subset.

## Revert

If evaluation fails, preserve inputs/results/logs, stop using the new environment
and invoke the retained known-good executable by full path. No in-place downgrade
or declaration rewrite is needed. If recreating a historical v1.0.1 environment,
use its authenticated original archive and compatible dependencies, then verify
its historical version and behavior. Never rename archives or replace historical
assets. The historical [v1.2 publication and recovery runbook](release-publication-1.2.0.md)
provides earlier recovery context.
