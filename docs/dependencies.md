# Dependencies and licenses

Runtime: Typer for CLI, PyYAML for bounded parsing, Pydantic for strict records.
The standard library provides addressing, hashing, graphs, intervals and serialization.
There are no mandatory cloud, telemetry, scanning, browser or LLM dependencies.
Architecture Explorer uses the same dependency closure plus the
standard library for static HTML/CSS/SVG, hashing, input checks and link auditing.
It adds no browser tooling, framework, graph-rendering package or runtime service.

| Dependency | Range | License / purpose |
| --- | --- | --- |
| Typer | >=0.16,<1 | MIT with retained bundled notices / CLI |
| PyYAML | >=6,<7 | MIT / YAML |
| Pydantic | >=2.12,<3 | MIT / records |
| setuptools | >=77 | MIT / build only |
| pip | 26.2.2 verification pin | MIT / approved installation tooling, not runtime |
| pytest | >=8,<10 | MIT / tests |
| types-PyYAML | >=6,<7 | Apache-2.0 with upstream notices / typing |
| Ruff | >=0.11,<1 | MIT / lint/format |
| mypy | >=1.15,<2 | MIT / typing |

Exact verification pins are in tools/verification-requirements.txt. Ranges do not
prove every combination. Full tested closure and embedded-component notices are in
[THIRD_PARTY_NOTICES](../THIRD_PARTY_NOTICES.md). Dependencies are installed separately,
not vendored. Offline redistribution retains complete upstream licenses.

Offline analysis does not install dependencies. A wheelhouse must contain the
complete runtime/transitive closure for the target OS, CPU and Python; source
installation also needs its build backend. See the [offline installation procedure](installation.md#optional-completely-offline-setup)
for `--no-index`, `--find-links`, `pip check` and the limits of `--no-deps`.
