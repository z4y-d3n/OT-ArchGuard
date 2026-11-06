# OT-ArchGuard 1.5.0 — unpublished stable candidate

Publication is pending owner review, exact integrated-source CI and final asset
assembly. No publication date, final release SHA or asset URLs are assigned here.
Published stable remains v1.4.0.

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
there are no new dependencies. See [installation](installation.md#v150-unpublished-stable-candidate)
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

Executed verification, exact local limits and unexecuted checks are recorded in
the [acceptance dossier](development/v15-06-acceptance.md),
[safety matrix](development/v15-06-safety-assurance.md) and
[compatibility record](development/v15-06-compatibility.md). Passing local tests
does not establish other platforms' results or universal correctness.

The intended release contains exactly a wheel, sdist, `release-manifest.json`
and `SHA256SUMS.txt`. Local rehearsals are source-bound candidates. Final
integrated-source rebuilding and explicit owner authorization are prerequisites
to an annotated tag and GitHub Release; see the
[handoff](development/v15-06-handoff-es.md).
