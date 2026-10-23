# Installation, parallel upgrade and offline use

The local **1.1.0 candidate is unpublished**. Published stable remains v1.0.1.
Owner-reviewed candidate archives and their local hashes are review artifacts,
not authentication by a public release channel. Python 3.12 is the minimum.
Windows CPython 3.12.14 and 3.14.5 are locally tested. New Ubuntu/macOS acceptance
awaits owner push/PR; see [candidate verification](v1.1/gate-v11-6.md).

## Parallel installation

Keep the known-good environment and declarations. Create a separate virtual
environment using an explicitly selected Python installation. Windows uses
`Scripts/python.exe` and `Scripts/otarchguard.exe`; POSIX uses `bin/python` and
`bin/otarchguard`. Activation is optional. For example, with an approved local
interpreter, create an empty parallel environment:

```powershell
.\.venv-verify312\Scripts\python.exe -m venv output/gate-v11-6/fresh312
```

A fresh environment needs compatible dependencies. On an authorized connected
machine the owner can prepare and review a complete OS/CPU/Python-specific
wheelhouse, retaining upstream distributions and notices. No wheelhouse is
shipped. With that prerequisite, install the reviewed candidate and closure:

```powershell
.\output\gate-v11-6\fresh312\Scripts\python.exe -m pip install --no-index --find-links wheelhouse otarchguard==1.1.0
```

The wheelhouse command is a conditional owner procedure: no complete dependency
wheelhouse was available for executing it here. The gate freshly installs the
candidate in the two dedicated existing verification environments using their
approved dependencies. It does not claim fresh-OS acceptance.

## Reviewed wheel or source archive

With approved dependencies already installed, these offline paths are tested.
Use the wheel **or** source command; use the 314 environment for Python 3.14:

```powershell
.\.venv-verify312\Scripts\python.exe -m pip install --no-index --no-deps --force-reinstall output/gate-v11-6/candidate/otarchguard-1.1.0-py3-none-any.whl
.\.venv-verify312\Scripts\python.exe -m pip install --no-index --no-deps --no-build-isolation --force-reinstall output/gate-v11-6/candidate/otarchguard-1.1.0.tar.gz
.\.venv-verify312\Scripts\python.exe -m pip check
.\.venv-verify312\Scripts\otarchguard.exe --version
.\.venv-verify312\Scripts\otarchguard.exe --help
.\.venv-verify312\Scripts\python.exe tools/verify_environment.py --output output/gate-v11-6/installation-check.json
```

Source installation also requires the approved `setuptools>=77` backend already
installed. `--no-deps` does not supply dependencies; `pip check` must pass.
No command above contacts an index. Do not use editable installation as acceptance
evidence. Confirm native console and imported module paths belong to the chosen
environment; runtime, native version and installed metadata must all be 1.1.0.

## Verify declarations and reports

Schema-1 inputs need no migration. Validate copies of existing models and compare
complete finite results, retaining their canonical hashes. Examples and fixtures
are in the checkout/sdist; the wheel contains runtime modules and notices.

```powershell
New-Item -ItemType Directory -Force output | Out-Null
.\.venv-verify312\Scripts\otarchguard.exe validate tests/fixtures/minimal-valid.yaml
.\.venv-verify312\Scripts\otarchguard.exe check tests/fixtures/minimal-valid.yaml
.\.venv-verify312\Scripts\otarchguard.exe exposure tests/fixtures/minimal-valid.yaml --scenario engineering_scope --report output/candidate-exposure.html
.\.venv-verify312\Scripts\otarchguard.exe trace tests/fixtures/minimal-valid.yaml --source eng --service svc_plc --policy-evidence --report output/candidate-trace.json --report-format json
.\.venv-verify312\Scripts\python.exe examples/run_examples.py
```

Inspect exit status. Exit 1 is completed failed-intent evidence; exit 2 is a failed
invocation and preserves any old report. A completed unreachable trace exits 0.
Reports are offline without remote scripts/assets. An old preserved report is
not evidence of a successful new run. See [reporting](reporting.md).

## Revert

If evaluation fails, preserve candidate inputs/results/logs, stop using its
environment and invoke the retained known-good v1.0.1 executable by full path.
No in-place downgrade or declaration rewrite is needed. If recreating stable is
necessary, use the owner's authenticated original v1.0.1 archive and matching
dependency wheelhouse; verify its historical version and behavior. Never rename
candidate archives or replace stable assets. Follow the
[publication and recovery runbook](release-publication-1.1.0.md).
