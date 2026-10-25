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

## Supported evidence

The accepted subset includes classic PCAP 2.4 and documented PCAPNG
sections/interfaces/Enhanced Packet Blocks/Simple Packet Blocks. Ethernet, VLAN,
supported raw IP, IPv4/IPv6, TCP/UDP, ARP and ICMP metadata remain observational.
ARP sender/target protocol fields and Ethernet delivery are distinct; a target
reference never establishes that a device exists, responded or owns an address.
Protocol labels associated with ports remain hints, not confirmed application
recognition. See the [supported subset](pcap-evidence-studio.md) and
[independent interoperability record](development/v13-14-capture-interoperability.md).

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
record actual results and outstanding requirements. Six hosted OS/Python cells
and human browser checks must not be inferred from local tests. Merge, tags,
GitHub Release, package uploads and repository settings require separate owner
authorization.
