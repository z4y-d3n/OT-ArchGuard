# Installation, parallel upgrade and offline use

This guide describes source version **1.1.0**, requiring Python 3.12 or later.
Consult the owner-published release record for availability, exact source tag and
audited asset checksums. Use a reviewed checkout or already obtained wheel/sdist;
compare obtained archives with that record when available. A checksum establishes
byte identity, not authenticity by itself. Historical Windows CPython 3.12.14 and
3.14.5 results are in [Gate V11-6](v1.1/gate-v11-6.md); final platform acceptance
requires evidence for the exact reviewed commit.

## Parallel installation

Keep the known-good environment and copies of declarations. In PowerShell, start
in the reviewed checkout or extracted sdist root (containing `pyproject.toml` and
`examples/`). For wheel-only installation, use a working directory containing
`artifacts/` and your model instead. Select an installed Python explicitly:

```powershell
$Python = (Get-Command python).Source
& $Python --version
& $Python -m venv .venv-otarchguard-1.1.0
$EnvPython = (Resolve-Path .venv-otarchguard-1.1.0/Scripts/python.exe).Path
```

Confirm the selected interpreter is Python 3.12 or later before creating the
environment. Use a new environment path for each evaluation; activation is
optional. On POSIX, use the selected `python3` interpreter with `-m venv`, and
replace `Scripts/python.exe` / `Scripts/otarchguard.exe` with `bin/python` /
`bin/otarchguard`; the variable syntax above is PowerShell-specific.

A fresh environment has no application dependencies. The installation commands
below resolve declared dependencies from an authorized package source and may
need setup-time network access. For offline setup, use the complete wheelhouse
procedure below or an environment with the approved compatible dependencies
already installed. Runtime analysis and generated HTML require no network.

## Choose one installation source

Run **one** of these alternatives using `$EnvPython` above. Checkout installation
runs from its root; archive paths are relative to the working directory. Put
already obtained, reviewed archives in `artifacts/`; no download is implied.
Source checkout/sdist commands require `setuptools>=77` already installed in the
chosen environment because build isolation is disabled. Obtain that backend
through your approved setup procedure before selecting a source installation.

```powershell
# Reviewed source checkout:
& $EnvPython -m pip install --no-build-isolation .
# OR already obtained wheel:
& $EnvPython -m pip install artifacts/otarchguard-1.1.0-py3-none-any.whl
# OR already obtained source distribution:
& $EnvPython -m pip install --no-build-isolation artifacts/otarchguard-1.1.0.tar.gz
```

## Optional completely offline setup

No dependency wheelhouse is shipped. This alternative is conditional on an
approved complete wheelhouse for the target OS/CPU/Python, including runtime
dependencies and their transitive dependencies. Source installation additionally
needs the build backend available locally. With the obtained application wheel
in `artifacts/` and dependency wheels in `wheelhouse/`, from the working directory:

```powershell
& $EnvPython -m pip install --no-index --find-links wheelhouse artifacts/otarchguard-1.1.0-py3-none-any.whl
```

For offline checkout/sdist installation with the backend already installed, use
the corresponding source command above with `--no-index --find-links wheelhouse`
added. `--no-index` supplies no missing packages. `--no-deps` skips dependency
resolution and does not prove correctness; use it only with an already approved
dependency closure. The complete-wheelhouse alternative requires separately
supplied artifacts and is not a claim of fresh-OS acceptance.

## Verify declarations and reports

After installation, from the same working directory:

```powershell
& $EnvPython -m pip check
$Otarchguard = (Resolve-Path .venv-otarchguard-1.1.0/Scripts/otarchguard.exe).Path
& $Otarchguard --version
& $Otarchguard --help
```

Require version 1.1.0 and a successful dependency check. Use the full native
executable path so an unrelated installation cannot be selected. Schema-1 models
need no migration. Set `$Model` to a copy of your existing schema-1 model; the
checkout/sdist example below uses its supplied remote-support model. A wheel
does not include examples; wheel-only users must supply their own model and use
its declared scenario, asset and service IDs in place of the example IDs.

```powershell
$Model = (Resolve-Path examples/remote-support/baseline.yaml).Path
New-Item -ItemType Directory -Force output | Out-Null
& $Otarchguard validate $Model
& $Otarchguard check $Model
& $Otarchguard exposure $Model --scenario support_scope --report output/exposure.html
& $Otarchguard trace $Model --source it --service svc_plc --policy-evidence --report output/trace.json --report-format json
```

Inspect the native exit status. Exit 1 is completed failed-intent evidence;
exit 2 is a failed invocation that preserves any old report. A completed
unreachable trace exits 0. Reports use offline HTML/SVG without remote scripts
or assets; JSON trace contains the finite query evidence. An old preserved report
does not establish a successful new run. See [reporting](reporting.md) and
[trace](trace.md). Keep output files separate from model inputs.

## Revert

If evaluation fails, preserve inputs/results/logs, stop using the new environment
and invoke the retained known-good executable by full path. No in-place downgrade
or declaration rewrite is needed. If recreating a historical v1.0.1 environment,
use its authenticated original archive and compatible dependencies, then verify
its historical version and behavior. Never rename archives or replace historical
assets. Follow the [publication and recovery runbook](release-publication-1.1.0.md).
