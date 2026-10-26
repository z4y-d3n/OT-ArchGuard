# OT-ArchGuard v1.3.0 — published stable release

[Stable v1.3.0](https://github.com/z4y-d3n/OT-ArchGuard/releases/tag/v1.3.0)
was published on 2026-10-26 from immutable release commit
`10d7de6c416ec6f0ee364c671ebe9292ee69e672`. It introduces PCAP Evidence Studio
while preserving native YAML schema 1, Import Studio, Architecture Explorer and
the existing analytical contracts. Runtime dependencies remain Typer, PyYAML and
Pydantic; Python 3.12 or later is required.

## PCAP Evidence Studio

- Bounded passive inspection of the documented classic PCAP 2.4 and PCAPNG subset.
- Header-only observations for supported Ethernet/VLAN, raw IP, IPv4/IPv6,
  TCP/UDP, ARP and ICMP/ICMPv6 metadata.
- Deterministic observed-address catalogs, directed aggregates and related
  bidirectional groups, without inferring established sessions.
- Explicit, hash-bound owner review connecting observed addresses to exact
  declared assets and interfaces, with stale-evidence rejection.
- Conservative comparison through the existing native reachability evaluator,
  retaining the original witnesses and diagnostics for eligible observations.
- Offline HTML/CSS/SVG reports with no JavaScript, server or remote resources.

ARP sender/target protocol fields and Ethernet delivery remain distinct. A target
reference does not establish a device, response or address ownership. Port-based
industrial protocol names remain hints, not confirmed application recognition.
See the [supported subset and trust boundaries](pcap-evidence-studio.md).

Only justified, owner-reviewed IPv4 TCP initial-SYN observations from
single-interface source assets with exact declared destination listeners are
eligible for native evaluation. UDP,
response-only TCP, unsupported or damaged metadata and ambiguous identities remain
explicitly unassessed. Observed traffic is not proof of authorization, successful
application exchange, a route taken or deployed firewall behavior. Missing traffic
does not prove blocking or service unavailability.

## Completed Explorer UX

The final evidence interface replaces primary raw JSON with structured summaries,
protocol/coverage tables, readable review fields and explicit empty states.
Communication labels identify endpoints, transport and available ports. Reciprocal
links connect addresses, aggregates, groups, associations, findings and exact
evidence, including complete paginated relationships.

UTC presentation preserves original rational precision. Canonical JSON, exact
identifiers and bounded packet references remain available as technical evidence.
Separate directed diagram lanes and ARP sender/target/delivery panels retain
their original meaning; no arrow claims a physical route or authorization.

## Correctness and evidence contracts

Independent hardening checks malformed IPv4 options and IPv6 extension TLVs before
retaining transport evidence, excludes unsupported interpretations and accounts
for native comparison evidence incrementally. Resource failures publish no
successful partial findings.

Native YAML remains schema 1. Capture, protocol catalog, association, comparison
and site contracts are version 1; observations are version 2. Identity rules and
compatibility policy are recorded in the
[evidence contract freeze](development/v13-18-evidence-contract-freeze.md).
Hashes establish byte integrity and source binding, not authenticated authorship
or cryptographic approval of owner assertions.

## Release verification and human acceptance

The [final integration CI](https://github.com/z4y-d3n/OT-ArchGuard/actions/runs/40273411275)
tested exact release commit `10d7de6c416ec6f0ee364c671ebe9292ee69e672`.
All six Windows/Ubuntu/macOS × Python 3.12/3.14 configurations passed, with
2,815 installed-wheel tests and 2,815 installed-sdist tests per configuration,
zero failures, errors or skips, and successful quality/package/source audits.
Wheel and sdist counts overlap and are not additive.

The final PCAP Evidence Explorer completed a second real human browser review:
all six criteria passed, including navigation, interpretation, legibility at
200% zoom and offline keyboard operation. The original four PASS/two FAIL review
and the earlier `5c4c18d` candidate CI remain historical milestones, not unresolved
current release requirements. Their original records are preserved in the
[UX baseline](development/v13-23-ux-findings-and-baseline.md) and
[source reconciliation](development/v13-27-source-and-release-provenance.md).
Later documentation commits do not become part of the immutable released source
or inherit CI results executed against a different commit.

## Download and installation

The [published release](https://github.com/z4y-d3n/OT-ArchGuard/releases/tag/v1.3.0)
provides:

- `otarchguard-1.3.0-py3-none-any.whl`
- `otarchguard-1.3.0.tar.gz`
- `release-manifest.json`
- `SHA256SUMS.txt`

Use the published files and hashes, not earlier candidate archives with the same
versioned filenames. Follow the [installation guide](installation.md) for checksum
verification, a fresh regular environment, `pip check` and version confirmation.
The [fictional capture tutorial](../examples/capture-studio/README.md) explains
the packaged ten-record samples and the extended twelve-record walkthrough.

## Supported scope and remaining limits

Independent interoperability uses original specification-authored synthetic
fixtures and Wireshark `text2pcap` 4.6.7 output with offline TShark 4.6.7 receipts.
Origins, licensing and hashes are documented in the
[corpus policy](pcap-evidence-studio.md#capture-corpus-and-use-policy).
No real industrial capture or downloaded operational corpus was tested. These
finite cases establish tested-subset behavior, not universal producer or plant
compatibility. No operational capture or Wireshark code is redistributed.

There is no live capture, scanning, intrusion detection, TCP stream reassembly,
deep industrial protocol inspection or application-payload decoding. Partial
sensor visibility, capture loss, NAT, DHCP/address reuse and spoofed metadata can
limit conclusions. Reports retain sensitive metadata and owner-review text; they
are not completely anonymized or formally security/accessibility certified.

Historical analysis, architecture drift detection and multi-capture evidence
lifecycle management are future capabilities, not v1.3 features. Optional
industrial-protocol enrichment requires separate feasibility review. Security
fixes, correctness corrections and compatibility maintenance remain possible.
