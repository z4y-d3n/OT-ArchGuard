# OT-ArchGuard 1.1.0 candidate release notes

**Prepared locally; unpublished. Owner review and new hosted CI are pending.**
No release date, public tag, downloadable release or package-index publication is
announced. The existing published stable release remains v1.0.1.

## Changes since v1.0.1

OT-ArchGuard analyzes finite owner-declared IT/OT architectures offline. This
candidate includes the accepted V11-1 through V11-5 implementation and V11-6
release preparation:

- Strict YAML/Unicode diagnostics reject escaped surrogates and out-of-range
  Unicode escapes at the shared validation boundary.
- Offline HTML/SVG reports use deterministic topology-based zone presentation,
  optional zone order, orthogonal transition routes, finite labels, local report
  navigation and explicit diagram omissions. Presentation creates no paths.
- The new `trace` command evaluates one original source and declared TCP/UDP
  listener over its complete destination-port union, with deterministic witnesses
  or bounded structural/policy diagnostics. Optional policy evidence describes
  finite allow/deny overlap and scoped duplicate effects; it makes no global
  redundancy claim. Trace does not assess communication intents.
- Exposure/comparison HTML includes completed finite-scope summaries and
  conservative references to observed declaration changes.
- Report-enabled check/exposure reuse one validated snapshot; compare keeps its
  independently validated baseline and proposal. The
  [V11-4 performance study](v1.1/gate-v11-4.md) records measured workloads and
  variability; it does not promise a universal speedup.
- Independent graph, raw-policy and concrete-port oracles, witness replay,
  metamorphic tests, bounded adverse inputs and atomic-report fault checks extend
  verification. The installed-help test uses a controlled plain terminal.
- Runtime, CLI, engine and distribution metadata now consistently identify the
  local 1.1.0 candidate. V11-6 compares historical artifacts with a narrow version
  allowlist and audits real wheel/source packages and installed module bytes.

## Compatibility

Architecture YAML remains schema 1. Administrative ownership and interface
placement remain distinct. Transport/forwarding is explicit and directed, without
inferred routes, reverse paths or implicit endpoint forwarding. Policies remain
unordered, default deny, with deny precedence and exact TCP/UDP destination ports.
There is no NAT, source-port or stateful-session interpretation.

Legacy report contract remains `report_version: 1`; the trace envelope remains
`trace_version: 1`. The intentional `engine_version` change is 1.0.1 to 1.1.0;
canonical model identities, query results, witnesses, counters and ceilings remain
unchanged from accepted V11-5. The legacy CLI exit meanings are retained. Trace
is an addition since v1.0.1 and exits 0 for a completed query even when unreachable.
See the [public contract inventory](v1.1/public-contract-inventory.md) and its
[V11-6 version addendum](v1.1/gate-v11-6.md).

## Installation and operating systems

Use a separate environment and an owner-reviewed local
`otarchguard-1.1.0-py3-none-any.whl` or `otarchguard-1.1.0.tar.gz` following
[installation and upgrade instructions](installation.md). Candidate hashes are
local evidence, not signatures from a public release channel. Compatible
dependencies must already be available for offline installation.

Local acceptance uses Windows CPython 3.12.14 and 3.14.5; see actual outcomes in
the [V11-6 dossier](v1.1/gate-v11-6.md). The retained hosted matrix targets Windows,
Ubuntu and macOS with Python 3.12/3.14. New V11-6 hosted results are
`PENDING_OWNER_PUSH_AND_PR`; Windows testing establishes no Ubuntu/macOS result.

## Limitations, security and provenance

This is an independent Apache-2.0 project with root commit
`8e6a5bca41a00eb0454e6efdd9a9558e1a7017b2`; the published v1.0.1 identity is
preserved. [Dependency notices](../THIRD_PARTY_NOTICES.md) remain applicable.
The candidate has no new runtime dependency or network integration.

The tool evaluates what declarations describe. It does not establish that a live
industrial network matches them. It is not a live scanner, packet/session
simulator, risk score or IEC 62443 certification system. Return traffic,
authentication, vulnerabilities, availability, compromise, physical risk and
process safety remain unassessed. Resource ceilings reject excessive work; they
are not capacity promises. Static HTML/SVG checks do not establish every browser,
keyboard, print or font behavior. See [limitations](limitations.md).

## Publication and recovery

The owner must review, commit, push, obtain six-way CI, merge, rebuild/audit the
accepted source, approve an annotated tag and separately approve publication.
GitHub Release and package-index publication are separate decisions. Follow the
[owner-only runbook and rollback plan](release-publication-1.1.0.md).

## After v1.1

V1.2 must substantially simplify architecture creation for industrial automation
engineers unfamiliar with YAML: guided authoring, industrial templates,
spreadsheet/CSV import, automatic schema-1 YAML, understandable validation and
progressive visual editing. This is a future requirement; none is implemented or
promised as an existing v1.1.0 capability.
