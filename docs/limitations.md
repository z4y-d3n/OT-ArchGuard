# Scope and known limitations

OT-ArchGuard distinguishes declared architecture analysis, imported documentary
evidence and passive capture observations. These sources have different trust
boundaries. The published scope is summarized in the
[v1.3.0 release notes](release-notes-1.3.0.md); the
[PCAP guide](pcap-evidence-studio.md) specifies capture observations separately
from the native evaluator.

## Import Studio and Architecture Explorer

Document support is restricted text/structure extraction, without rendered page
numbers, OCR, inherited presentation text, automatic network inference or complete
Office coverage. Active/embedded/external structures fail closed or are explicitly
diagnosed as excluded under the
[subset policy](development/v12-06-document-evidence-and-explorer.md).
PDF/VSDX remain unsupported. Explorer contract 2 groups records: sharing a page
also shares its other evidence, and old physical bookmarks may change after
regeneration. The manifest location index identifies current record anchors.

Architecture Explorer supports native models and matching project provenance
version 1. Other sidecar versions fail explicitly; model-only mode has no
documentary origins. It never imports old HTML as analytical truth. Its bounded
diagrams disclose omissions and keep complete linked records; exceeding a file,
text or site budget rejects complete generation. Default output contains sensitive
selected architecture/evidence; no public-safe redaction mode or universal secret
detector exists.

The original Explorer development gates recorded blocked `file://` automation,
not completed browser/assistive-technology acceptance. Keep that historical scope
separate from the final PCAP Evidence Explorer's second real human review, which
passed all six criteria. Neither structural tests nor those finite human checks
establish universal accessibility, browser-network behavior or WCAG certification.
See the [Explorer ADRs](development/v12-05-architecture-explorer.md).

## Native declared-model analysis

The native evaluator checks finite owner-declared IPv4 TCP/UDP initiation paths.
It does not discover deployed inventory, topology, bypasses, listeners, enforcement
or vulnerabilities. Completeness, classification, criticality and origin
assumptions remain declarations.

There is no return-path/session, authentication, exploitability, compromise
probability, availability, timing, physical impact or process-safety determination.
Security-level evidence is unassessed, not zero. No security score or deployable
remediation is produced.

The native model/evaluator does not support IPv6, non-TCP/UDP initiation queries,
source-port policy selectors, NAT, ordered/stateful rules, routing tables/VRFs,
VLAN/L2 behavior, application relays, same-interface forwarding, multiple
administrative owners or protected/multizone conduits. Unsupported/resource-limited
evaluation is an error, never successful unreachability. This native scope does
not prohibit the separate PCAP reader from retaining supported IPv6, ARP, VLAN,
ICMP and source-port metadata as observations without native evaluation.

Static diagram ordering, long/shared-looking routes and large-topology summaries
have presentation limits. Full evidence and omissions remain available. No new
browser/print claim follows from parsing or static images. The native renderer
(introduced in v1.1) uses explicit-topology ordering, orthogonal tracks and finite
clipped labels. Routes can cross or share endpoint strokes; dense layouts can be
tall. Summary mode retains complete analysis/inventory. The original
[Gate V11-2 manual checklist](v1.1/gate-v11-2.md) records its then-unverified browser
and hosted scope; it is not the current release's CI status. See
[report options](reporting.md) for the implemented presentation contract.

A historical v1.0.1 invalid-text issue remains in that release: escaped unpaired
Unicode surrogates can cause UnicodeEncodeError in the validation API. Its CLI
returns a generic exit-2 execution diagnostic and preserves existing output.
Version 1.1.0 includes the V11-1 correction; the historical v1.0.1 release was not
replaced.

## Passive capture evidence

PCAP Evidence Studio is not live monitoring, active discovery or intrusion
detection. It performs no TCP stream reassembly, deep industrial-protocol
inspection or application-payload decoding. Port associations remain hints.
Observed traffic does not prove authorization, session/application success, actual
packet routes or deployed firewall behavior. Missing traffic does not prove
blocking. ARP target references do not prove device existence, ownership or response.

Partial sensor visibility, capture loss, unmodeled NAT, DHCP/address reuse and
spoofed metadata limit interpretation. Association hashes bind finite evidence;
they do not cryptographically authenticate the reviewer or the asserted identity.
Header metadata and owner-review text can be sensitive. No complete anonymization
or formal compliance/security certification is claimed. Independent synthetic and
Wireshark-generated specimens cover the documented subset, not every producer or
real industrial-plant traffic.

## Resource and platform evidence

Ceilings are rejection limits, not capacity promises. Native detailed reports
retain evidence in memory; bounded Explorer/capture sites have their own output
ceilings. Native performance profiling reports traced Python allocations, not RSS.
Capture benchmarks separately record OS lifetime peak resident memory. Neither is
an OS-enforced memory cap.

The published release passed Windows, Ubuntu and macOS CI with Python 3.12/3.14.
Python 3.13 and combinations outside that matrix, fresh-OS/physical-air-gap
deployment and broader browser/print/assistive-technology coverage are not implied.
See the [release verification](release-notes-1.3.0.md#release-verification-and-human-acceptance).
The [v1.0.1 verification summary](verification.md) remains historical evidence.

## Quality and architecture comparison

The `quality` and `compare-architecture` commands assess explicit model-bound
requirements and native/documentary/owner changes. Exact comparative reachability
comes only from explicit before/after native trace evaluation. Missing evidence
is not a vulnerability; changed scope never resolves a finding. Selected evidence,
external owner information and native declarations remain separate. Split/merge
and fuzzy identity inference are unsupported. See the
[seven ADRs](development/v12-07-quality-and-comparison.md) for versioned schemas,
coverage denominators, query comparability, resource ceilings and compact views.

Historical analysis, architecture drift detection and multi-capture evidence
lifecycle management are future work, not implemented v1.3 capabilities. Optional
industrial-protocol enrichment requires a separate feasibility review.
