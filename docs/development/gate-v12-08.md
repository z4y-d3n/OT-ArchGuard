# GATE V12-08 — Final integration and release candidate

Baseline: merged PR #10, integration commit
`6492143cb5c75f9f1ac51b70a7a305011c9d64fe`, tree
`627da481fd596a550ac29372c9ed68319e224fa8`, public-source SHA-256
`2fa528837d62f41c797bc6ba4b0cdbd6abe8e3c80e4246b798b31917170a3792`.
The tree equals the accepted V12-07 portability correction; its implementation
and correction commits remain ancestors. Stable main/tree, independent root and
both annotated tag objects match the protected identities.

V12-08 selects unpublished **1.2.0rc1** and preserves schema 1. It corrects a
release-audit gap: wheel directories and special-file metadata could escape the
previous member audit. All ZIP entries are now checked before payload reading;
noncanonical and case-conflicting archive names are rejected. Permanent adversarial
regressions cover those cases. No analytical algorithm or input trust boundary is
relaxed. The full sdist suite replaces partial installed-sdist CI selection.

Hosted artifact reconciliation also exposed a source identity gap: default Windows
checkout conversion changed public code/document bytes even though functional tests
passed. The final policy preserves exact Git blob bytes with `* -text`, while the
accepted saved-review fixture LF rule and all explicit binary rules remain intact.
No existing public file is renormalized and real owner inputs remain byte-bound.
A pre-build check compares every allowlisted working file with its committed blob;
it fails on drift instead of normalizing it. Real Git regressions exercise true,
false and input autocrlf modes, retained CRLF source and deliberate byte mutation.

Current instructions and examples consistently name the candidate. See
[release notes](../release-notes-1.2.0.md) and
[publication/recovery](../release-publication-1.2.0.md). Historical records retain
their original version and acceptance status. V12-08 closes development scope;
remaining corrections belong to this gate, with no speculative V12-09.

Ignored `output/v1.2-development/v12-08/` holds the independent baseline audit,
raw public GitHub receipts, actual requirements matrix, security/provenance/native
assessment, frozen public source, archive/member inventories, installed Python
3.12/3.14 JUnit, offline tutorials, determinism/performance evidence, browser/manual
records, sanitized review ZIP, acceptance and exact publication proposal. The
final acceptance manifest binds those receipts to the tested commit/source.
This document describes the contract; only executed source-bound evidence can
mark a requirement verified. Local, hosted, browser, owner and publication states
remain independent. Never infer final-candidate CI from V12-07 runs.

Required traceability groups are native validation, TCP/UDP, imports, hostile
parsing, provenance/reconciliation, owner decisions, Explorer, quality, comparison,
security/privacy, determinism, resource/performance, CLI/API, distribution,
documentation, accessibility, offline runtime and CI/publication. Each record in
`release-requirements-matrix.json` identifies its guarantee, ADR, implementation,
positive/negative tests, platform/install relevance, executed receipt, limitation,
blocking classification and actual result. Unexecuted mandatory checks stay open.

Manual review must observe file-URL rendering/CSS, grouped and quality anchors,
baseline/proposed/analysis views, back/forward, moved-directory portability,
keyboard focus/skip/tab order, 200% zoom, narrow layout, table overflow, escaped
Unicode/evidence, console/network behavior and missing-file diagnostics. Record
browser version, OS, site hashes, commands and date. Screen-reader acceptance
requires a suitable real environment; semantic checks alone do not certify WCAG.

The GitHub connector required reauthentication at baseline. Authorized read-only
public API requests established PR #10 merge and exact previous runs/attempts.
Public branch metadata reported main/v1.2 unprotected and no repository rulesets;
no governance was changed. Push/PR, integration merge, stable merge, tags, Releases
and PyPI remain separately controlled. A locally verified candidate is not a
post-merge release candidate and is not a stable release.
