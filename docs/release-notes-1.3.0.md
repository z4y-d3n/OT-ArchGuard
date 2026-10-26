# OT-ArchGuard 1.3.0 — unpublished release candidate

PCAP Evidence Studio adds passive local capture inspection, bounded header-only
observations, conversation catalogs, explicit evidence-bound identity review,
comparison through the existing declared-model evaluator, and offline HTML/SVG
evidence reports. Native YAML schema 1 and existing Import Studio, Architecture
Explorer and analytical contracts remain supported. Runtime dependencies are
unchanged: Typer, PyYAML and Pydantic.

The active package, CLI and distribution metadata identify version **1.3.0**.
This version transition does not establish owner approval, hosted acceptance,
stable tagging or publication. Historical 1.2.0 development archives must not be
renamed or published as 1.3.0. Final built filenames and SHA-256 identities come
from the actual build and release manifest.

Six-platform hosted CI passed for exact candidate
`5c4c18da4711c36f4f5750c03009d429551d0cf0` in
[run 40246239841](https://github.com/z4y-d3n/OT-ArchGuard/actions/runs/40246239841).
Every wheel and sdist suite reported 2,746 passing tests with no failures, errors
or skips; the counts overlap and are not additive. Its local documentation-only
child `e763f0cb6591dee6b80b6aa846286d2b901a95ae` has no hosted run of its own.
The later human browser review passed four criteria and failed navigation and
interpretation. The UX remediation therefore requires a new exact-source
candidate, packages and validation, followed by a second human review. Earlier
green CI does not accept the changed renderer.

## Supported evidence

The accepted subset includes classic PCAP 2.4 and documented PCAPNG
sections/interfaces/Enhanced Packet Blocks/Simple Packet Blocks. Ethernet, VLAN,
supported raw IP, IPv4/IPv6, TCP/UDP, ARP and ICMP metadata remain observational.
ARP sender/target protocol fields and Ethernet delivery are distinct; a target
reference never establishes that a device exists, responded or owns an address.
Protocol labels associated with ports remain hints, not confirmed application
recognition. See the [supported subset](pcap-evidence-studio.md) and
[independent interoperability record](development/v13-14-capture-interoperability.md).

Independent interoperability used synthetic specification-authored fixtures and
Wireshark `text2pcap` 4.6.7 output with offline TShark 4.6.7 reference receipts.
The original fictional fixtures, origins, licenses and hashes are documented in
the [corpus policy](pcap-evidence-studio.md#capture-corpus-and-use-policy).
No real industrial capture or downloaded public operational corpus was tested.
This establishes tested-subset behavior rather than universal producer or plant
coverage. No operational capture or Wireshark code is redistributed.

Only justified, owner-reviewed single-interface IPv4 TCP initial-SYN observations
with exact declared listeners are eligible for native evaluation. UDP, response-only
TCP, damaged or unsupported metadata and ambiguous identities remain explicitly
unassessed. An observed packet does not prove a completed session, authorization,
application success, route taken or deployed firewall behavior. Missing traffic
does not prove blocking or service unavailability.

## Correctness and contracts

Independent hardening validates malformed IPv4 options and IPv6 extension TLVs
before retaining transport evidence, excludes unsupported interpretations, and
charges native comparison evidence incrementally. ARP evidence retains explicit
sender/target and link-delivery metadata. Explorer provides readable classification
labels with exact codes and evidence references retained in details and JSON.
Versioned machine-readable contracts, identity rules and compatibility policy are
defined in the [evidence contract freeze](development/v13-18-evidence-contract-freeze.md).
Hashes establish byte integrity and source identity; they do not authenticate
the creator or cryptographically sign owner review assertions.

## Installation and remaining acceptance

The focused UI correction replaces primary raw-JSON displays with readable
counts, statuses and structured evidence; it adds contextual navigation, meaningful
communication labels, precise UTC presentation and finding explanations. Exact
identifiers, packet references, rational timestamps and canonical JSON remain
available. The existing directed lanes and ARP sender/target/delivery distinction
are retained. Technical rendering checks support the second human review and
cannot turn the original navigation or interpretation FAIL into PASS.

Use a fresh regular environment with Python 3.12 or later and the actual audited
wheel or sdist. Verify `otarchguard --version` reports `1.3.0`, run `pip check`,
and retain the prior working installation during evaluation. See the
[installation guide](installation.md) and [fictional tutorial](../examples/capture-studio/README.md).

No live capture, active discovery, scanning, cloud service, telemetry, industrial
command decoding, historical comparison, drift detection or multi-capture lifecycle
management is introduced. NAT, DHCP/address reuse, partial sensor visibility,
capture loss and spoofed metadata limit conclusions. Network metadata and review
text may themselves be sensitive; reports are not completely anonymized.

The [final regression](development/v13-20-version-transition-and-final-regression.md),
[hosted acceptance](development/v13-21-hosted-candidate-acceptance.md),
[browser acceptance](development/v13-17-local-browser-acceptance.md), and
[readiness decision](development/v13-22-feature-complete-and-release-readiness.md)
record the earlier stage. The
[source reconciliation](development/v13-27-source-and-release-provenance.md)
supersedes its stale outstanding-CI wording without changing historical outcomes.
New candidate verification and second human acceptance are separate milestones;
neither follows automatically from the earlier passing run. Merge, tags, GitHub
Release, package uploads and repository settings require separate owner authorization.
