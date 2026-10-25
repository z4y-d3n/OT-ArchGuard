# 1.2.0rc1 (unpublished candidate)

Final V12-08 candidate: complete integrated Import Studio, offline Explorer, quality and
comparison; stricter distribution entry auditing and full installed-sdist CI.
See [candidate notes](docs/release-notes-1.2.0.md). Stable publication requires
separate owner authorization and exact-source acceptance.

# Changelog

## 1.1.0

This entry describes source version 1.1.0. Consult the owner-published release
record for publication status and exact audited asset checksums.

- Reject escaped Unicode surrogates and out-of-range YAML escapes with controlled
  diagnostics while preserving valid declared text and canonical identities.
- Improve deterministic offline HTML/SVG layout, zone presentation ordering,
  bounded labels, report navigation and explicit omission evidence.
- Add exact communication trace, optional finite policy evidence, completed
  scenario summaries and conservative comparison change descriptions.
- Reuse validated snapshots for report-enabled check, exposure and comparison.
  Historical measurements and their scope are in the V11-4 dossier.
- Expand independent graph/policy/per-port oracles, metamorphic verification,
  adverse-input and atomic-report failure coverage; normalize test help rendering.
- Prepare consistent 1.1.0 runtime/distribution identity, version-aware historical
  comparisons, audited packages and owner-controlled publication/rollback steps.

Schema 1, report version 1, trace version 1, default deny, deny precedence, exact
TCP/UDP initiation semantics and resource ceilings are retained. Trace is new
since v1.0.1; completed unreachable trace queries exit 0 without assessing intents.
See [release notes](docs/release-notes-1.1.0.md).

## 1.0.1

- Restrict source distributions to an explicit public file manifest.
- Audit archive members, package metadata, entry points, license notices and
  wheel RECORD digests against the corresponding source files.
- Check wheel payload consistency when rebuilding from the source distribution.
- Add regression coverage for unexpected, missing and stale packaged files.
- Clarify installation, analysis semantics, reports and known limitations.

Schema 1, analysis algorithms, resource limits and CLI exit meanings remain
unchanged. Python 3.12 is the minimum; local verification covers Windows Python
3.12.14 and 3.14.5. The invalid-Unicode diagnostic issue remains documented in
[limitations](docs/limitations.md). See [verification](docs/verification.md) and
[release notes](docs/release-notes-1.0.1.md).
