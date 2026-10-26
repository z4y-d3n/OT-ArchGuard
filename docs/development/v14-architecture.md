# V14-00 architecture decision: independent evidence layers

Status: implemented foundation, development contract. This is not a release candidate.

## Baseline and compatibility

The starting checkout was clean at `8acce281e4b627ca74c5ee42df8c9cffd3f06fc0`
on `codex/docs-v1.3.0-final-portfolio-closure`. After an explicit fetch, reviewed
`origin/main` was `1febf7a864c074d2a3d3ac78005ea1bf2853009a`. The annotated
`v1.3.0` tag resolves to `10d7de6c416ec6f0ee364c671ebe9292ee69e672`.
The six baseline jobs passed in [run 40323647595](https://github.com/z4y-d3n/OT-ArchGuard/actions/runs/40323647595).
Development starts on `codex/v14-00-evidence-lifecycle-foundation` from that main.

The [v1.3 evidence freeze](v13-18-evidence-contract-freeze.md) remains authoritative.
Observation v2, capture v1, associations v1, native comparisons v1 and catalog v1
retain their identities, ordering and meanings. Existing analysis/reconciliation
code does not consume enrichment. No mappings are approved or carried forward.
YAML schema 1 and the native evaluator remain unchanged.

The package retains `1.3.0` in this local foundation. A trial development-version
change altered native result engine strings inside frozen capture comparison
goldens. It was reverted without changing the fixtures or historical tests.
A reviewed package/engine-version compatibility transition is required before any
development distribution or release candidate is shared. Branch and artifact
implementation versions distinguish this unfinished work; it is not publishable.

## Decisions

1. `capture/protocols/` consumes transient packet records through the existing
   bounded `scan_capture` callback. It produces separate enrichment version 1
   metadata. It neither modifies observations nor changes eligibility for native
   architecture reconciliation. The first supported subsets are Modbus TCP and
   Ethernet/VLAN PROFINET DCP. The remaining five protocols are explicit backlog.
2. `evidence/` imports local observation v2 JSON into content-bound, immutable
   snapshot objects. The workspace is a transparent file directory, with bounded
   validation, explicit duplicate handling and no raw packet capture copies.
   Snapshot identity excludes filesystem paths and wall-clock import time.
3. Separate command groups reflect separate trust boundaries: `capture enrich`
   emits header evidence; `evidence` manages historical metadata. Historical
   snapshots remain useful without enrichment and enrichment without a workspace.
4. Development corpus tooling lives under `tools/`, outside the runtime package.
   Public availability does not establish redistribution permission. No runtime
   download, active industrial networking, TCP stream reconstruction or arbitrary
   payload export is introduced.

## Interpretation and failure boundaries

Structural validity describes a supported frame subset, not authenticity, a valid
session, authorization or command execution. Read/write function categories have
unassessed request/response direction unless independently established. Port hints
remain hints. Partial and unsupported inputs abstain; a failed capture scan must
not publish a successful artifact. Per-record results and source references are
bounded, deterministic and payload-free.

Hashes establish content integrity, not truth or creator identity. A self-consistent
forged metadata file can still contain false assertions. Snapshot ingestion validates
the supported metadata contract but does not reopen or authenticate the original
capture. Owner-approved baselines, associations, architecture attachments and drift
interpretation require separate future contracts and validation before use.

Workspace safety assumes a local single writer. Link and regular-file checks protect
against accidental and ordinary malicious inputs; they are not an OS sandbox against
an attacker concurrently replacing arbitrary filesystem ancestors. Resource ceilings
bound supported inputs and output; timing measurements are finite observations.

## Acceptance scope

V14-00 requires working decoding, CLI integration, deterministic snapshot ingestion,
independent fixtures, corpus provenance infrastructure, regression tests and a local
verified commit. Version-1 development artifacts are documented with their producers;
a final immutable v1.4 contract freeze and independent lifecycle reader are still
required before release acceptance. The full seven-protocol product, approved
baselines, historical drift engine, offline historical Explorer, portable bundles,
external real-world validation and hosted candidate CI remain later milestones.
