# Changelog

## Unreleased — v1.4 local development foundation

- V14-02 adds explicit byte-preserving workspace-v2 migration, four validated
  attachment kinds, immutable analytical revisions with exact producer semantics,
  and evidence/architecture baseline proposals with scoped local human review,
  revocation, supersession and conflict detection. Historical drift and its
  visualization remain future milestones.
- V14-01 adds EtherNet/IP/limited CIP, classic S7comm, IEC-104, OPC UA Binary
  outer framing and CRC-checked DNP3 to complete seven bounded header subsets.
- Preserve enrichment schema 1; emit decoder revision 2 and strictly consume
  legacy revision 1. Frozen native evidence and workspace/snapshot v1 stay intact.
- Separate development distribution `1.4.0.dev1` from native engine `1.3.0`;
  document analytical revision and scoped-review identities for V14-02.
- Add local-only external laboratory capture verification with exact source
  hashes and TShark receipts. No third-party capture bytes are redistributed.

- Add independent bounded Modbus TCP and Layer-2 PROFINET DCP header enrichment
  through `capture enrich`, preserving observation v2 and reconciliation semantics.
- Add metadata-only immutable evidence workspace initialization, snapshot import,
  duplicate identification, listing, inspection and integrity verification.
- Establish a three-tier development corpus provenance manifest and independent
  synthetic reference checks. External real-world validation remains pending.
- Keep historical comparisons, historical Explorer and final release acceptance
  explicitly unfinished. See the
  [rolling v1.4 acceptance record](docs/development/v14-progress.md).

## 1.3.0 — 2026-10-26 (stable)

Published [v1.3.0](https://github.com/z4y-d3n/OT-ArchGuard/releases/tag/v1.3.0)
is the latest stable release, from accepted integration commit
`10d7de6c416ec6f0ee364c671ebe9292ee69e672`.

- Add bounded passive PCAP/PCAPNG analysis, supported packet metadata, directed
  communication aggregates, related bidirectional groups and conservative port hints.
- Add deterministic offline HTML/CSS/SVG evidence reports and fictional walkthroughs,
  without JavaScript, a web server or remote rendering resources.
- Add explicit hash-bound association review and reconciliation through the existing
  native evaluator, retaining witnesses, diagnostics and stale-evidence checks.
- Correct ARP sender/target and Ethernet-delivery semantics; target-only references
  do not become observed-address identity proposals.
- Reject malformed IPv4 options and malformed/unsupported IPv6 extension semantics
  before exposing transport ports or TCP initiation evidence.
- Replace primary raw JSON presentation with structured summaries, protocol and
  coverage tables, readable review fields, contextual explanations and empty states.
  Canonical JSON and exact identifiers remain available as technical evidence.
- Add descriptive communication labels and reciprocal navigation between observed
  addresses, aggregates, groups, associations, findings and exact evidence, including
  complete paginated relationships and separate index/detail page namespaces.
- Display human-readable UTC timestamps without losing original rational precision,
  and provide summary/category counts consistent with canonical evidence.
- Preserve separate directed diagram lanes, direct evidence links and ARP field
  panels. Distinguish observed traffic from declared-model assessment and uncertainty.
- Bound retained native comparison evidence incrementally, stopping over-budget
  queries before subsequent port intervals and publishing no partial conclusions.
- Add independent binary, semantic, publication and resource regression corpora,
  maximum-frame and metadata workloads, OS peak resident-memory measurements and
  hosted capture benchmarks.
- Freeze versioned capture evidence contracts and verify independent read-only
  consumers. Preserve native YAML schema 1, existing Import Studio, Architecture
  Explorer and historical analytical contracts.
- Verify the final integration in [CI run 40273411275](https://github.com/z4y-d3n/OT-ArchGuard/actions/runs/40273411275):
  all six Windows/Ubuntu/macOS × Python 3.12/3.14 configurations passed, each with
  2,815 installed-wheel tests and 2,815 installed-sdist tests and zero failures,
  errors or skips. Wheel/sdist counts overlap and are not additive.
- Complete the second human browser acceptance with all six criteria passing,
  including the previously failed navigation and interpretation criteria,
  legibility at 200% zoom and offline keyboard operation.

Industrial protocol names inferred from ports remain hints. The release performs
no TCP stream reassembly, deep industrial protocol inspection or application
payload decoding. Independent synthetic and Wireshark-generated reference captures
cover the documented subset; universal producer compatibility and validation
against real operational industrial traffic are not claimed.

See the [published release notes and assets](https://github.com/z4y-d3n/OT-ArchGuard/releases/tag/v1.3.0),
[installation guide](docs/installation.md) and [PCAP Evidence Studio guide](docs/pcap-evidence-studio.md).

The earlier entries below retain their original development and release-preparation
context. Their status wording records that stage, rather than current release availability.

## 1.2.0 (stable-release preparation; unpublished)

Prepare the stable version from accepted V12-08 integration without changing
native schema, analytical semantics, provenance bindings or runtime dependencies.
CI derives wheel/sdist filenames from the build backend and audits, installs and
tests those exact artifacts on the release-preparation branch and its PR.
Publication remains a separate owner decision; this entry is not a release claim.
See [release notes](docs/release-notes-1.2.0.md).

## 1.2.0rc1 (unpublished candidate)

Final V12-08 candidate: complete integrated Import Studio, offline Explorer, quality and
comparison; stricter distribution entry auditing and full installed-sdist CI.
See [candidate notes](docs/release-notes-1.2.0.md). Stable publication requires
separate owner authorization and exact-source acceptance.

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

