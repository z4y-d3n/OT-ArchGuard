# OT-ArchGuard v1.4 progress and acceptance record

This is the single rolling implementation/acceptance record. Documentation and code
are in English; owner-facing delivery summaries use Spanish. No v1.4 release,
remote branch, pull request or tag is authorized by this local development work.

## Starting identities

- Stable v1.3.0: `10d7de6c416ec6f0ee364c671ebe9292ee69e672`.
- Reviewed development base: `1febf7a864c074d2a3d3ac78005ea1bf2853009a`.
- Local branch: `codex/v14-00-evidence-lifecycle-foundation`.
- Package identity remains `1.3.0`; this modified development branch is not publishable.
- Baseline CI: all six jobs passed in run `40323647595`; this is baseline evidence,
  not hosted validation of the new development commit.
- Starting test collection: 2,815 tests. The existing local environment contained
  an outdated installed 1.2.0 package; verification must install the audited current
  wheel before claiming installed-package results.

## V14-00 acceptance

Implemented locally:

- Typed bounded protocol interface and separate Modbus TCP / PROFINET DCP decoders.
- Independent enrichment v1 artifact, strict validator and `capture enrich` command.
- Workspace v1 / snapshot v1 with `evidence init/add/list/show/verify`, exact source
  bindings, bounded local publication and explicit duplicate preservation.
- Original synthetic protocol corpus, TShark 4.6.7 receipt, three-tier provenance
  manifest and bounded offline development verifier. Four external candidates remain
  unapproved; no external packet bytes are redistributed.
- Installed-console fictional walkthrough with two independent snapshots and duplicate
  import. Existing v1.3 capture walkthrough also passes.
- Explicit packaging inventories and additive CI foundation step; existing six-job
  OS/Python matrix is unchanged. No hosted candidate run has been dispatched.

Focused verification: 177 new tests passed in 5.21 s, zero failures/errors/skips,
across protocol (56), lifecycle (55), corpus (38), independent audit (26) and
integration (2) tests. Ruff lint/format, strict mypy (177 Python files) and the two
frozen evidence consumers pass. Native v1.2 compatibility passes for 124 captured
files with the pre-existing exact version/module allowlist. Full final installed
wheel/sdist suites and final source/archive receipts are pending below.

Independent review found and corrected DCP service IDs, unrelated-PROFINET labeling,
Modbus register-response framing, unknown payload fields, impossible packet bounds,
timestamp joins, self-reported budgets, lifecycle aggregate joins and filesystem
reparse/mutation checks. Fourteen frozen capture/reader/golden files have identical
SHA-256 bytes against both the reviewed main and immutable v1.3.0 commit.

No original capture is modified or copied into snapshots. No new dependency,
networking, approval assertion or native evaluator behavior is introduced. New v1
contracts are development interfaces, not a final immutable release freeze:
[enrichment](v14-enrichment-contract.md), [lifecycle](v14-evidence-contract.md).

See [architecture decisions](v14-architecture.md) and
[corpus provenance](v14-protocol-corpus.md). No third-party packet capture is
authorized for redistribution merely by appearing in the source-candidate manifest.

## Remaining milestones

1. V14-01: EtherNet/IP/CIP, classic S7comm, IEC-104, OPC UA Binary and DNP3,
   each with bounded framing, independent positive/negative fixtures and tests.
2. V14-02: reviewed enrichment/native-evidence attachments, complete snapshot
   lifecycle and explicit evidence/architecture baseline approval contracts.
3. V14-03: deterministic historical comparisons, coverage compatibility, stable
   findings and exact source joins; never infer blocking from missing observations.
4. V14-04: usable offline historical Explorer, source navigation, accessibility,
   pagination and finite performance measurements; evaluate the known native
   forwarding legend mismatch with a regression.
5. V14-05: legally reviewed actual external captures, pinned payload hashes,
   reference-decoder receipts and documented unsupported real-world cases.
6. V14-06: explicit package/engine-version transition preserving historical native
   witness contracts, final contract freeze/independent consumer, security/resource audits,
   installed wheel/sdist and historical compatibility, full six-configuration
   hosted candidate CI and owner-controlled release decision.

The next local step after the verified foundation is protocol V14-01. Preserve this
checkpoint and require each decoder's focused acceptance before adding its public
supported inventory entry. Do not advertise the development build as a complete
seven-protocol release candidate.
