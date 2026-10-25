# Draft v1.3 release notes — not a published release

Historical development notes, superseded by the active
[1.3.0 candidate notes](release-notes-1.3.0.md). Version statements below describe
the earlier development phase and are retained as historical evidence.

PCAP Evidence Studio adds passive local capture inspection, bounded header-only
observations and conversation catalogs, explicit hash-bound identity review,
conservative comparison through the existing evaluator, and offline evidence sites.
Native schema1, policy semantics, historical commands/reports, Import Studio and
Architecture Explorer remain unchanged. No new runtime dependencies.

Format scope is classic PCAP2.4 and documented PCAPNG sections/interfaces/EPB/SPB.
Ethernet/VLAN/raw IP, IPv4/IPv6, TCP/UDP, ARP and ICMP metadata is observational.
Industrial protocol recognition is limited to versioned port hints. No active
capture, reassembly, industrial command decoding, DNS, telemetry, model mutation or
automated authorization is implemented.

Only justified reviewed single-interface IPv4 TCP initiations with exact declared
listeners are evaluated. UDP/response-only TCP, unsupported or damaged evidence
remain explicit uncertainty. Native witnesses do not prove actual packet routes.
Discrepancies are model/evidence disagreements, not incidents or compliance scores.

This development candidate retains package version1.2.0 pending the isolated
version transition and final acceptance. Hosted six-combination candidate CI,
formal owner acceptance, publication and stable tagging require subsequent steps.
Independent hardening corrects malformed IPv4 option handling and IPv6 extension
TLV/padding interpretation, conservatively excludes unimplemented options/routing
headers, and bounds retained native comparison evidence per interval. Observed
communication diagrams now use distinct labeled lanes and precise evidence links.
Independent corpora challenge owner bindings, exact-port caching and uncertainty;
resource measurements distinguish traced allocations from OS peak resident memory.

See [implemented contracts and limitations](pcap-evidence-studio.md), the
[independent audit](development/v13-08-independent-audit.md), and the
[candidate readiness record](development/v13-13-release-candidate-readiness.md)
for executed validation and outstanding acceptance conditions. Earlier gate records
remain historical evidence and are not retroactively changed.
