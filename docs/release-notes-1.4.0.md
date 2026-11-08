# OT-ArchGuard 1.4.0 — stable release

**[Published November 2, 2026](https://github.com/z4y-d3n/OT-ArchGuard/releases/tag/v1.4.0).**
The annotated `v1.4.0` tag retains source commit
`7d6b158f863308dfcd7d10b673bfbe2692f29b8b`, integrating development PRs #17–#24.
[v1.3.0](https://github.com/z4y-d3n/OT-ArchGuard/releases/tag/v1.3.0) remains the
previous stable release and recovery option. Historical V14-06 reports retain
their original candidate identities and then-pending gates.

## Main capabilities

OT-ArchGuard combines bounded declared-network analysis with passive evidence
and explicit local human review. It operates offline and generates static
HTML/CSS/SVG reports without a server, JavaScript or remote rendering service.

- **Industrial metadata:** seven bounded header/metadata subsets: Modbus TCP,
  PROFINET DCP, EtherNet/IP with limited CIP, classic S7comm, IEC-104, OPC UA Binary
  outer framing and CRC-checked DNP3/TCP. Structural header evidence remains
  separate from port/EtherType hints and malformed, truncated or unsupported input.
- **Historical lifecycle:** immutable metadata collections, explicit workspace-v2
  migration, validated optional attachments, analytical revisions and scoped
  baseline proposal/review with revocation and supersession.
- **Historical drift:** selected evidence and declared-model comparisons retain
  per-domain coverage, explicit alignment, unsupported states and equivalent
  native-query boundaries. Decoder reinterpretation does not establish a physical
  change. Missing packets do not prove blocking, absence or outage.
- **Historical Explorer:** exact source replay precedes publication; static pages
  link domains, findings and evidence. Portable bundle integrity and source-dependent
  analytical reproduction are separate verification operations. Recorded and
  current approval states remain distinct.
- **Semantic presentation and assurance:** structured summaries, tables and
  contextual evidence retain complete canonical technical details. Independent
  fictional corpora, adversarial integrity regressions, source/package audits and
  historical validation/performance work support the documented bounded scope.

Existing native validation, reachability, independent required/prohibited intents,
exposure, trace, Import Studio, Architecture Explorer and capture reconciliation
remain supported. They assess declarations and finite observations, not deployed
firewall authorization or industrial process safety.

## Compatibility and upgrade

Distribution metadata, wheel/sdist filenames and CLI `--version` identify `1.4.0`.
Unchanged native evidence identifies engine `1.3.0`; the historical public
`__version__` alias intentionally remains `1.3.0`. Native YAML schema 1, report/trace
contracts and canonical analytical identities are preserved. Protocol enrichment
schema 1 emits decoder revision 2 and continues strict revision-1 consumption.

There is no native schema migration. Workspace-v1 → workspace-v2 migration is
explicit and preserves snapshot bytes without creating analyses or approvals.
Development analytical revisions bind the exact producer source, including the
distribution identity module. The `1.4.0.dev1` → `1.4.0` source change therefore
does **not** transparently replay old development analyses under the new producer.

Preserve the exact old environment and untouched workspace for reproduction.
Create a fresh `1.4.0` workspace from retained validated observations and authorized
source attachments, create new analyses and explicitly review a baseline. Never
rewrite stored digests/IDs or inherit approvals to bypass source validation. Safe
historical-workspace downgrade has not been demonstrated. Follow
[installation and recovery](installation.md#historical-workspaces-and-upgrade).

## Installation and first run

Download the four assets from the
[published release](https://github.com/z4y-d3n/OT-ArchGuard/releases/tag/v1.4.0):
`otarchguard-1.4.0-py3-none-any.whl`, `otarchguard-1.4.0.tar.gz`,
`release-manifest.json` and `SHA256SUMS.txt`. Verify all four published digests,
the complete checksum list and tagged source identity, then install
one distribution into a new environment alongside the known-good v1.3.0 environment.
See [v1.4.0 installation, offline setup and first run](installation.md#previous-stable-v140).

Python metadata is `>=3.12`. The verified hosted matrix is Windows, Ubuntu and
macOS with Python 3.12/3.14. Admission by metadata is distinct from testing every
interpreter, OS or future version. Installation requires compatible dependencies
and, for source builds, an available `setuptools>=77` backend. Runtime operations
are offline; fully disconnected installation needs a separately prepared wheelhouse.

## Evidence, privacy and limitations

- No TCP stream reassembly, full industrial decoding, application values,
  transaction-success verification, live network scanning or operational command
  execution is provided. DLT_NULL and Linux SLL are unsupported.
- External positive validation remains incomplete for Modbus TCP, PROFINET DCP
  and IEC-104. Original fictional fixtures and approved local laboratory checks
  do not establish universal interoperability or production-plant validation.
- External corpus approval concerns local analysis only. Redistribution rights
  and complete third-party collection provenance remain unestablished. No
  third-party capture bytes are packaged.
- Observed communication, declared paths, reconciliation, analytical inference,
  human review and current approval are different claims. A structurally valid
  header or TCP SYN does not prove successful exchange or authorization.
- Human-review labels are unauthenticated local assertions; workspaces assume a
  single writer. Hashes prove byte identity, not authorship, sensor authenticity
  or general forensic authenticity. No industrial certification or independent
  professional penetration test is claimed.
- Metadata, review rationale and report labels can be sensitive. Inspect an entire
  bundle before sharing. Do not treat imported metadata as anonymized.

Unsupported, not evaluated, indeterminate, negative, no observed evidence, no
declared path and explicitly denied declaration must retain their actual meanings.
See the [protocol guide](v14-foundation.md), [history](v14-history.md),
[drift](v14-drift.md) and [general limitations](limitations.md).

## Verification and owner gates

[Final integrated main run 40991511467](https://github.com/z4y-d3n/OT-ArchGuard/actions/runs/40991511467)
completed successfully for exact release source
`7d6b158f863308dfcd7d10b673bfbe2692f29b8b`: Windows, Ubuntu and macOS, each with
Python 3.12 and 3.14, all six jobs successful. The stable release and its four
assets are published. The [publication record](release-checklist.md) identifies
the annotated tag and digests.

The [V14-06 handoff](development/v14-06-handoff-es.md) and
[documentation pass](development/v14-06-public-documentation-es.md) preserve
engineering checks and candidate acceptance at their original source identities.
Their pending wording is historical, not the current stable publication status.
V14-04 semantic HTML received owner visual acceptance, including high-zoom review.
Static automated checks alone do not establish browser, keyboard, focus or print
acceptance; materially changed pages require renewed targeted human inspection.

Repeated source/wheel/sdist executions are not additional unique tests. Stable
publication does not imply completion of unexecuted browser, external protocol
or production-plant checks. Later documentation commits need their own relevant
checks and six-job hosted CI; they do not change the previously published source
or distribution. See the [reusable checklist](release-checklist.md#reusable-exact-source-checks).

## Reproduction and recovery

Retain the exact source commit/tree, reviewed public inventory, package-member and
installed-module identities, verification receipts and checksums together.
Use the tagged release source for published-artifact verification. Current `main`
can advance independently; building from a later documentation commit would
produce a different source-bound asset set and must not replace v1.4.0 files.
The published manifest's assembly-purpose/acceptance text records the builder's
original scope, not a later publication log. Archive byte reproducibility is not
asserted; source-byte and installed-payload equality are different claims.

For rollback, invoke the retained v1.3.0 executable by full path or reinstall its
original verified asset into a separate environment. Preserve new workspaces and
their compatible producer; no historical-data downgrade guarantee is made.
Use minimal fictional [issue reports](https://github.com/z4y-d3n/OT-ArchGuard/issues)
and omit operational captures, credentials and identifying review text.
