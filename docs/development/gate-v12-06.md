# GATE V12-06 — Document evidence and compact Explorer

The authoritative starting point is clean branch
`codex/v12-05-architecture-explorer`, commit
`508c3bfb60580233bb3618b6100fad0e18ee2468`, public-source identity
`43286e18682e71c6d2130fc192d2455b170a4a3387291c58d83e63eadf245e93`.
V12-05 frozen acceptance and changed-file manifests, stable main/tree, annotated
tags and independent root were checked before creating
`codex/v12-06-document-evidence-explorer`. No owner changes existed.

This gate adds restricted TXT/Markdown/DOCX/PPTX evidence, explicit table/key-value
mapping, project acknowledgment and exact source-location Explorer links. It does
not infer deployed devices, zones, topology or policy from prose. The same native
validator, explicit review and source/stale-review boundaries remain authoritative.
PDF and VSDX are explicitly deferred without new runtime dependencies.

Explorer presentation contract 2 groups low-value documentary detail records into
stable hash buckets with individual anchors and a manifest location index. Native,
source and analysis pages remain separate. The measured medium/larger page-count
reductions exceed the mandatory 40%; rejected observations, conflicts and owner
rationales remain accessible. No JavaScript or server is required. Older generated
sites are preserved; old physical bookmarks are not promised in regenerated sites.

Read the [six design decisions](v12-06-document-evidence-and-explorer.md) for exact
format subsets, reject/exclude policy, budgets, review contract, link compatibility,
privacy, manual browser checklist and measurement limits. Run the
[installed documentary tutorial](../../examples/import-studio/documents/README.md).

Only a successful fresh frozen-source acceptance run accepts the final source.
Ignored `output/v1.2-development/v12-06/final-01/acceptance.json` and
`acceptance-report.md` record the exact verdict, commit, source digest, artifact
hashes, installed-module identities, JUnit counts, Ruff/mypy checks, console
workflows, before/after measurements, source preservation and limitations.
Preparation attempts remain separate. Acceptance hashes do not enter the public
source manifest, avoiding circular identity.

The four installations use only existing approved dependencies. Full installed
wheel tests run on Windows Python 3.12/3.14; focused installed-sdist tests include
all ingestion, review and Explorer cases. Package audits compare every allowed
source and production-module byte. Offline guards actively deny Python socket,
DNS and HTTP operations. All six hosted Windows/Ubuntu/macOS × 3.12/3.14 runs remain
**NOT EXECUTED** until real final-candidate CI evidence exists. YAML is not evidence
that those jobs passed. Stable v1.2.0 release readiness remains blocked.

The browser tool rejected the intended `file://` origin by policy. Browser
rendering, keyboard/zoom/viewport behavior, console/network behavior and assistive
technology remain **NOT EXECUTED**; structural accessibility/security/link tests
are recorded separately. Disk inventory is report-only; no cleanup of owner or
historical evidence is performed. No public-safe redaction claim is made.

No remote push, PR/merge, CI dispatch, main rewrite, tag mutation, dependency
download, publication, industrial-network contact, cloud document processing or
stable v1.2.0 release is performed. Version remains 1.2.0.dev0.

V12-07 can consume qualified documentary observations, explicit owner partitions,
retained conflicts, coverage counts and compact location indexes. Missing evidence
must remain distinct from a proven architecture defect. V12-07 is not implemented.
