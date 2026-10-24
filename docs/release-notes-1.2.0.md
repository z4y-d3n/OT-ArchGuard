# OT-ArchGuard 1.2.0 release notes (candidate)

The reviewed source identifies itself as **1.2.0rc1**, an unpublished candidate.
Stable 1.2.0 is reserved for a separately approved, freshly verified source commit.
Published v1.1.0 and its tag remain the recovery baseline. Python 3.12 or later,
Apache-2.0, native YAML schema 1 and the existing validate/check/exposure/compare/
trace commands remain supported. No new runtime dependency is introduced.

## Changes since 1.1.0

Import Studio turns bounded local sources into observations, explicit mappings,
reviewed proposals and native declarations with provenance. Supported families:

| Family | Implemented subset and limits |
| --- | --- |
| CSV/TSV | Explicit encoding/delimiter and field mapping; inert formula-like text |
| JSON | Structured selected inventory; strict duplicate keys and exact numeric tokens |
| NetBox | Offline inventory subset; no live API connection |
| XLSX | Selected literal inventory cells; restricted standard-library OOXML parser |
| draw.io/GraphML | Restricted documentary nodes/connectors; no inferred permission |
| TXT/Markdown | Located text and explicitly selected supported tables/key-values |
| DOCX/PPTX | Restricted transitional OOXML text/tables; no Office execution |

Macros, external relationships, embedded objects and unsupported structures are
rejected or explicitly diagnosed under the format contract. PDF, VSDX and OCR
remain unsupported. See [supported subsets](import-studio.md) and the
[format decisions](development/v1.2-import-formats.md).

Multi-source projects require explicit identity/field conflict resolution.
Owner decisions bind exact source/profile/draft bytes. Mutating real source bytes
invalidates the review. The shipped saved-review fixtures use LF through
`.gitattributes` so Git checkout conversion cannot invalidate that tutorial.
Legacy rounded structured drafts must be regenerated and reviewed under the
[numeric migration contract](development/v12-02r-numeric-policy.md).

Architecture Explorer produces a movable directory of HTML, CSS and inline SVG.
No JavaScript, browser server, remote font or cloud API is required. Contract 2
packs documentary records into bounded groups with individually addressable
anchors and a deterministic location index. Compaction retains the records;
old contract-1 physical bookmarks are not a compatibility guarantee.

Quality assessment uses explicit model-bound requirements, versioned findings
and defined coverage denominators. Missing and unavailable evidence differ;
model-only assessment creates no invented completeness or security score.
Architecture comparison uses explicit one-to-one correspondence or conservative
identifier reuse. No fuzzy matching, automatic split/merge inference or global
vulnerability ranking is implemented. Documentary and owner changes remain
separate from native changes.

Exact comparative TCP/UDP conclusions require explicit queries evaluated against
both validated models. A drawing arrow, forwarding declaration or native edge
alone does not establish allowed communication. Results apply only to the shown
model, direction, protocol and port intervals, not a deployed industrial network.

V12-08 strengthens the distribution auditor: every wheel ZIP entry is inspected,
including directory/link metadata previously omitted by the audit. Canonical names,
case collisions and source archive entries are checked. This closes a verification
gap; it is not a claim that previously accepted distributions contained those entries.
Installed sdist CI now runs the full regression suite. Required integrity artifacts
are retained for 30 days, and a missing artifact is a failure.
Public source checkouts also retain exact Git blob bytes on every OS, including
existing CRLF files, while the saved-review fixture LF policy remains explicit.
CI checks the complete public allowlist against committed bytes before building;
it never normalizes owner documents to obtain matching identities.

## Installation and first use

Use [parallel installation](installation.md), a reviewed candidate archive and an
approved complete dependency closure. Wheel-only installations do not include
tutorial source files. From a checkout or extracted sdist, with its native console
on PATH, the following commands are exercised by installed-distribution acceptance:

```text
otarchguard --version
otarchguard validate tests/fixtures/minimal-valid.yaml
otarchguard quality tests/fixtures/minimal-valid.yaml
python -m tools.project_walkthrough --output NEW_PROJECT_DIRECTORY
python -m tools.document_walkthrough --output NEW_DOCUMENT_DIRECTORY
python -m tools.explorer_walkthrough --output NEW_EXPLORER_DIRECTORY
python -m tools.quality_walkthrough --output NEW_COMPARISON_DIRECTORY
```

Replace each NEW directory with a fresh writable location. Open generated
`index.html` in an ordinary browser. Exit 2 means input, resource or I/O failure;
preserved old output is not evidence of a successful new invocation. A completed
unreachable trace returns 0; failed communication intents return 1.

Setup may require an approved package source. Runtime import, analysis and report
generation work offline. Required bounds are documented in the
[native schema](yaml-schema-v1.md), [import guide](import-studio.md) and
[quality/comparison ADR](development/v12-07-quality-and-comparison.md).

## Verification and limitations

Release acceptance requires exact-commit Windows/Ubuntu/macOS × Python 3.12/3.14
receipts, independently audited wheel/sdist, installed execution, source/module
hashes, deterministic outputs and browser/manual acceptance. Previous gate CI
does not verify this candidate. The [gate report](development/gate-v12-08.md)
describes where actual results and remaining checks are recorded.

Check published SHA-256 values against the approved source and archive manifest.
Hashes detect changes; they do not authenticate authorship. A local candidate or
review ZIP is not a published stable distribution. Archive-byte reproducibility
across different build hosts is not asserted; source, module and canonical output
reproducibility are distinct checks.

This application performs no live discovery, scanning, firewall verification,
traffic measurement or compliance certification. Quality is not a cybersecurity
certificate. Reports may disclose asset names, addresses and selected evidence;
there is no public-safe redaction mode. Original documents are excluded from
Explorer output. No WCAG certification or exhaustive vulnerability scan is claimed.
See [limitations](limitations.md) and the
[controlled publication procedure](release-publication-1.2.0.md).
