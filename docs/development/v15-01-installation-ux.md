# V15-01 — Installation and user journeys

Public stable remains v1.4.0. This branch's local archives are development
verification candidates with unchanged runtime version; they are not replacement
release assets. Python metadata is >=3.12; local execution is Windows/Python
3.12.14. POSIX commands and the Windows/Ubuntu/macOS × 3.12/3.14 matrix receive
static review here; unexecuted combinations require hosted CI for the final SHA.

## Installation matrix

Agent D independently audits fresh non-editable wheel and sdist environments,
the complete locally resolved dependency closure and setuptools backend. Installs
run with `--no-index --find-links wheelhouse` and a Python socket guard in the
entry processes. Pip build isolation may replace `PYTHONPATH` in backend children;
this is local-only dependency resolution, not a universal network sandbox or a
claim of physical disconnection. An online-index installation
is not inferred from it. Published downloads, hashes and release assets are not
modified or silently rebuilt.

Executed clean source: `b3bc51271c94a67d01aa8328aa215d4dbea45673`.
Archive audit, regular wheel, build-isolated sdist and preinstalled-backend sdist
all passed. Each environment imported its own site-packages, matched all 97
runtime module hashes, passed dependency consistency/version/help/validate, and
generated its first Explorer outside the checkout from the extracted fictional
example. The actual extracted sdist passed all 16 new regressions and all three
historical CLI walkthroughs. See [acceptance](v15-01-acceptance.md) and the
[concise receipt](v15-01-evidence.json). The full sdist suite and an online-index
install were not executed. The initial ensurepip temporary-directory failure and
successful retry into fresh environments remain in the raw package receipt.
Original `.venv-v146-*` environments are preserved; old producer-source revisions
are not rehashed and approvals are not transferred. Existing version-transition
tests distinguish object-integrity verification from compatible analytical replay.

## Reviewed journeys

| Journey | Observed behavior / action |
|---|---|
| B1 first report | README distinguishes four verified assets, wheel runtime, sdist fictional examples, dependency downloads and offline analysis. Installed `explore examples/remote-support/proposed.yaml` completed locally; 52 HTML pages, zero audited broken links. An Explorer is not proof all intents pass. |
| B2 declared architecture | Local overview → assets/interfaces → source context and explicit trace/intent evidence. Semantic HTML contains captions, scoped headers, skip link, focus rules, wrapping and print styles. |
| B3 passive capture | Overview/inventory/conversations/findings/metadata retain observations, hints, unresolved mapping and coverage separately from permissions. Existing capture walkthrough exercises retained evidence navigation. |
| B4 historical investigation | Exact revision selection → explicitly scoped local review → drift → finding/evidence → portable integrity/source replay are documented. Tutorials had reproducible destination tracebacks; the shared preflight now explains recovery without altering scenarios. |

Agent B checked 17 user-facing documents and 207 local target links with no
missing target files. This is not an anchor or browser accessibility result.
The current structured-inventory install command now points to v1.4.0; explicit
historical references remain historical. Three historical guides explain source/
sdist tools, installed interpreter, parent creation and fresh output directories.

The browser tool rejected the local `file:` URL under its access policy. No
browser/keyboard/200% zoom/narrow viewport/IPv6/long-identity/print/screen-reader
PASS is claimed. Static checks and complete generated-link audits remain useful
but do not establish those properties; owner steps are in the
[Spanish handoff](v15-01-handoff-es.md).
