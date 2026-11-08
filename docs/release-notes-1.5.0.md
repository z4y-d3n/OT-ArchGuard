# OT-ArchGuard 1.5.0 — stable release

[OT-ArchGuard v1.5.0](https://github.com/z4y-d3n/OT-ArchGuard/releases/tag/v1.5.0)
was published on November 6, 2026 at 03:42:51 UTC. The annotated `v1.5.0` tag
(object `7468378077e64e321f58b101759d296688ed0a89`) resolves to commit
`14732d12f0a5dde5acf97ca1b552d69cfb12f1e0`.

The v1.5 development gates improve evidence-centered navigation and diagnostic
presentation, distinguish recorded from current historical review authority,
preserve source-bound historical reproduction, optimize bounded Explorer text
validation, and consolidate regular package installation/recovery documentation.
V15-06 advances distribution/CLI `1.5.0.dev3` to `1.5.0` with a separate source
authorization and stable-only four-asset assembler. It adds focused safety
regressions without changing native analytical semantics.

Retained v1.4 capabilities include native architecture validation, directional
reachability/intent/policy traces, Architecture Explorer, reviewed Import Studio,
passive PCAP/PCAPNG evidence, historical collections/revisions/baselines,
coverage-aware drift and Historical Evidence & Drift Explorer.

Python >=3.12 is required. Supported CI targets are Windows, Ubuntu and macOS
with Python 3.12/3.14. Runtime requirements remain Typer, PyYAML and Pydantic;
there are no new dependencies. See [installation](installation.md#obtain-and-verify-assets)
for regular wheel/sdist installation and target-specific offline prerequisites.
Native engine and legacy `__version__` remain `1.3.0`, YAML schema `1`.

Analysis reads local files and remains offline/passive: no scanning, live
capture, device access, telemetry, server or remote rendering. Dependency
acquisition is a separate preparation step. Reports are bounded static HTML.

Interpretation boundaries remain explicit:

- Reachability concerns supported declared IPv4 TCP/UDP initiation. It proves
  neither physical connectivity/isolation, deployed enforcement, session
  completion, exploitability, compromise nor process impact. Completeness is
  an unverified owner declaration; absent real-world edges were not checked.
- Invalid/unsupported/resource-rejected input stops evaluation. A qualified
  negative within the model differs from inability to evaluate.
- Observed traffic does not establish authorization; finite absence does not
  establish blocking. Reviewed IP/asset mappings do not authenticate identity.
- Protocol metadata covers bounded headers for Modbus TCP, PROFINET DCP,
  EtherNet/IP with limited CIP, classic S7comm, IEC-104, OPC UA Binary and
  DNP3/TCP. Unsupported/truncated variants abstain. No TCP reassembly,
  transaction reconstruction or successful command-execution claim is made.
- Stable source is a new historical producer because `__init__.py` changes.
  Existing dev3 revisions/approvals remain bound to their original source;
  preserve that environment for replay. Portable bundle integrity alone proves
  neither analytical reproduction nor authenticated authorship. A source change
  does not imply different physical traffic. Historical renderer identity is
  unchanged because its five bound modules are byte-identical.
- Resource ceilings, existing evidence schemas, v1.4 assets and historical
  reference policies remain unchanged. No certification or security-level
  assessment is claimed.

## Verification and published assets

[Integrated-source CI run 42157555998](https://github.com/z4y-d3n/OT-ArchGuard/actions/runs/42157555998)
completed successfully for the tagged commit. All six jobs passed on Windows,
Ubuntu and macOS with Python 3.12 and 3.14.

The four uploaded files were downloaded independently and checked against
GitHub's published sizes and SHA-256 digests:

| Published asset | SHA-256 |
|---|---|
| [`otarchguard-1.5.0-py3-none-any.whl`](https://github.com/z4y-d3n/OT-ArchGuard/releases/download/v1.5.0/otarchguard-1.5.0-py3-none-any.whl) | `ad113d3573f877e29839bc311fa3dd2c47ebad085cc135f3de35ece93b479701` |
| [`otarchguard-1.5.0.tar.gz`](https://github.com/z4y-d3n/OT-ArchGuard/releases/download/v1.5.0/otarchguard-1.5.0.tar.gz) | `b645d10774e5fc73bdeeaf9744fadfadc1b7a1a24f1993b72319bfc70c54c94d` |
| [`release-manifest.json`](https://github.com/z4y-d3n/OT-ArchGuard/releases/download/v1.5.0/release-manifest.json) | `a88ffa7035586f7de4f58e7463d80d4daba8b351acca5de678335b289a664da4` |
| [`SHA256SUMS.txt`](https://github.com/z4y-d3n/OT-ArchGuard/releases/download/v1.5.0/SHA256SUMS.txt) | `00fe2983421081cb1221f3a532f3ccff823597fd71318e1674df06cb1b616a99` |

The release verifier confirmed the checksum list, manifest, archive members
and source inventory against the immutable tag. See the
[completed publication record](release-checklist.md#completed-v150-publication-record).
These checks establish byte integrity and source correspondence.

Executed candidate checks and their original scope are recorded in
the [acceptance dossier](development/v15-06-acceptance.md),
[safety matrix](development/v15-06-safety-assurance.md) and
[compatibility record](development/v15-06-compatibility.md). Those records
retain the original local Windows scope, including one junction-permission skip.
Live OT validation, deployed isolation or enforcement, broader external
protocol validation and browser/accessibility certification remain unverified.

This page records publication on current `main`. The
[tagged release notes](https://github.com/z4y-d3n/OT-ArchGuard/blob/v1.5.0/docs/release-notes-1.5.0.md)
and the copy in the sdist preserve the original prepublication wording as part
of the immutable release snapshot.
