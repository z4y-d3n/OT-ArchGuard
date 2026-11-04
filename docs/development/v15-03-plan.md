# V15-03 — Evidence-centered navigation

Base: merged PR #27, `a3cf2f2e226b7a0fe985816cbaafb6ec6527b2f5`,
tree `0e2c748edd6196a67a6cdee6f29b5aee639bb1a5`. Initial local branch
was clean `codex/v15-02-compatibility-evolution` at `e01b5cf`; its tree
equals the merge tree. Dedicated branch: `codex/v15-03-evidence-centered-ux`.
Hosted baseline run 41741064369 completed successfully in all six configurations.
Python: regular `.venv-v152-wheel/Scripts/python.exe`, 3.12.14, distribution
1.5.0.dev1, native engine 1.3.0, YAML schema 1.

Independent discovery A (journeys), B (Architecture/import), C (PCAP), D
(historical/compatibility), E (installation/performance) is read-only; integrator
owns source changes. F challenges the stable candidate without editing it.
Raw discovery, reports and commands are retained under `output/v15-03/agent-*`.

## Selected scope and transition boundary

Actual frozen supported/limited PCAP sites reproduce two P2 deficiencies:
family links falsely announce another document as current page, and evidence
detail batches lack adjacent-batch navigation and page/record orientation.
Correct these together in `capture/explorer.py`; retain exact canonical JSON,
IDs, evidence joins, filenames, security and resource rejection.

Advance only distribution metadata and `__init__.py` to 1.5.0.dev2. Native
engine/schema remain 1.3.0/1. Historical renderer stays
`1.5.0.dev1-historical-explorer.1`: none of its five bound sources changes.
The changed distribution source creates a new analytical producer; old revisions
require their original runtime for replay. Approval never transfers.

A separate V15-03 policy pins the merged predecessor tree and exact two-module
delta, rejects any other module/resource, verifies installed bytes before import,
and executes the untouched V15-02 verifier/tests in the archived dev1 environment.
Current tests explicitly exclude the version-specific `test_v15_transition.py`;
its unchanged assertions are executed separately against their exact source.
Two current distribution literals and the misleading PCAP navigation assertion
receive narrowly reviewed test adaptations. Historical fixtures/oracles stay fixed.

## Exclusions and acceptance

No shared HTML/CSS rewrite, new protocol, ingestion refactor, analytical change,
cross-report filesystem links, GUI framework or remote mutation. Architecture
and import handoffs already reach authentic evidence. Their current-page
orientation and review branding are recorded as deferred P2 issues. Historical
navigation and seven vertical limitations remain unchanged.

Acceptance requires independent before/after canonical comparisons, exact
flow-link identities, complete graph/pager and mutation tests, frozen native
oracles, historical rejection/recovery, lint/format/mypy/dependencies, current
suite plus preserved historical suite, audited regular wheel/sdist installations,
fictional walkthroughs, paired rendering measurements and skeptical review.
Browser rendering/keyboard/zoom/print and owner review have separate outcomes;
static tests cannot establish browser PASS. New hosted CI requires the eventual
submitted SHA and remains pending without a push.
