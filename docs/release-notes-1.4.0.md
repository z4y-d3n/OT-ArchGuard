# OT-ArchGuard 1.4.0 — local release candidate

**Unpublished candidate. Published stable remains
[v1.3.0](https://github.com/z4y-d3n/OT-ArchGuard/releases/tag/v1.3.0).**
Local preparation, a version string and a green parent run do not authorize a tag,
merge or publication. The [Spanish owner handoff](development/v14-06-handoff-es.md)
records candidate source/package identities, executed results and remaining gates.

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

Use the audited local candidate assets identified by the handoff:
`otarchguard-1.4.0-py3-none-any.whl`, `otarchguard-1.4.0.tar.gz`,
`release-manifest.json` and `SHA256SUMS.txt`. No future download URL is presented
as a published release. Verify all checksums and source identity, then install
one distribution into a new environment alongside the known-good v1.3.0 environment.
See [wheel/sdist/offline installation](installation.md) and the
[README first run](../README.md#quick-start--5-minutes).

Python metadata is `>=3.12`. The required hosted matrix is Windows, Ubuntu and
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

The exact V14-05 parent `ac893bc3174f0a7ace67454d19ad6e61116425af` passed
[push run 40880668115](https://github.com/z4y-d3n/OT-ArchGuard/actions/runs/40880668115),
six Windows/Ubuntu/macOS × Python 3.12/3.14 jobs. These results belong to the parent.
For V14-06, the owner reports six successful hosted jobs for
`5c70ae09904687070ecce9374546aff8ae806588` on Draft PR #24. The later
[documentation pass](development/v14-06-public-documentation-es.md) requires CI
for its own exact SHA; the supplied checkpoint status was not queried remotely
during that local-only pass.
V14-04 semantic HTML received owner visual acceptance, including high-zoom review.
Static automated checks alone do not establish browser, keyboard, focus or print
acceptance; materially changed pages require renewed targeted human inspection.

The V14-06 handoff records actual unique tests, wheel/sdist runs, quality checks,
offline workflows, historical verifier results, performance evidence and skips.
Repeated executions are not additional unique tests. Do not infer final candidate
CI results from parent CI or final merged-source acceptance from a Draft PR.

The owner must review the local documentation candidate, authorize its push to
the existing V14-06 Draft PR, verify six hosted jobs for its exact SHA, integrate
the stack, accept the exact resulting release
source and rebuild/audit its assets before separately authorizing tag/publication.
See the [release checklist](release-checklist.md).

## Reproduction and recovery

Retain the exact source commit/tree, reviewed public inventory, package-member and
installed-module identities, verification receipts and checksums together.
`python -m tools.prepare_release --output NEW_DIRECTORY` rehearses local assembly
from clean committed source; add `--verify` to reopen/audit that asset set.
It does not publish or create a tag. Archive byte reproducibility is not asserted
unless independently demonstrated; source-byte and installed-payload equality
are different claims.

For rollback, invoke the retained v1.3.0 executable by full path or reinstall its
original verified asset into a separate environment. Preserve new workspaces and
their compatible producer; no historical-data downgrade guarantee is made.
Use minimal fictional [issue reports](https://github.com/z4y-d3n/OT-ArchGuard/issues)
and omit operational captures, credentials and identifying review text.
