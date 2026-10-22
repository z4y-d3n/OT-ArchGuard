# Third-party dependency notices

Original OT-ArchGuard work is Apache-2.0. This does not relicense dependencies,
their bundled components or trademarks.
The application wheel contains OT-ArchGuard code and its license documents;
it does **not** vendor dependency code. Pip installs dependencies separately.
Preserve each dependency distribution's license/attribution files when providing
an offline wheelhouse or otherwise redistributing those distributions.

## Tested runtime dependency closure

Inspected installed distribution metadata and license files from the approved
Windows Python 3.12.14 / 3.14.5 verification environments:

| Distribution | Tested version | License |
| --- | --- | --- |
| Typer | 0.27.3 | MIT; bundled `typer/_click` is BSD-3-Clause, Copyright 2014 Pallets |
| PyYAML | 6.0.3 | MIT |
| Pydantic | 2.14.1 | MIT |
| pydantic-core | 2.50.1 | MIT |
| annotated-doc | 0.0.5 | MIT |
| annotated-types | 0.8.0 | MIT |
| typing-inspection | 0.4.4 | MIT |
| typing_extensions | 4.16.0 | PSF-2.0 |
| rich | 15.0.0 | MIT |
| markdown-it-py | 4.2.0 | MIT; retains additional upstream markdown-it MIT notice |
| mdurl | 0.1.2 | MIT |
| Pygments | 2.21.0 | BSD-2-Clause |
| shellingham | 1.5.4 | ISC |
| colorama (Windows) | 0.4.6 | BSD-3-Clause |

The wheelhouse dependencies retain their own upstream license texts. In particular,
Typer's embedded Click notice remains under `typer/_click/LICENSE.txt`; it must
not be replaced by Typer's MIT label alone. No dependency files are stripped or
rewritten by the application packaging process.

## Development/build tools

pytest 9.1.1, Ruff 0.17.1, mypy 1.20.2, setuptools 84.2.1, iniconfig 2.3.1,
pluggy 1.7.0, mypy_extensions 1.1.0 and librt 0.16.0 report MIT licenses.
types-PyYAML 6.0.12.20260906 is Apache-2.0; packaging 26.3 is
Apache-2.0 OR BSD-2-Clause; pathspec 1.1.1 is MPL-2.0. Pip is MIT
(25.0.1 / 26.1.1 in the respective interpreters). These tools are not application
runtime dependencies. Setuptools and pip carry their own vendored notices;
redistributing those tools requires preserving their complete distributions.
The types-PyYAML/typeshed license file also retains an MIT notice for parts of
typeshed; preserve that complete file rather than using its metadata label alone.

No project-specific NOTICE file is required to carry copied third-party source:
none is bundled in the application. This document is an inventory, not a substitute
for upstream licenses. Tested metadata and shipped notice presence were audited;
this is not an independent legal review of every native/transitive upstream
component. Future resolved versions require a renewed license/dependency audit.

The project does not distribute proprietary reference content. Its license
does not grant rights to independently protected material.
