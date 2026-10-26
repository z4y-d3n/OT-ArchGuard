# V13-18 — Evidence contract freeze

## A. Executive status

PASS for the documented finite metadata contracts after final installed verification
recorded in V13-20. This is an interface freeze for read-only future consumers,
not historical-analysis functionality. No evidence database or drift engine is added.

## B. Revisions and compatibility

| Artifact | Version field | Current value | Required root fields |
|---|---|---:|---|
| observations.json | observation_version | 2 | observation_version, catalog_version, capture, hosts, flows, conversations, coverage, aggregation_accounted_bytes, limitations, observations_sha256 |
| capture metadata (nested or inspect stdout) | capture_version | 1 | capture_version, capture_id, sha256, size_bytes, format, interfaces, packets, captured_bytes, original_bytes, blocks, unknown_blocks, limitations |
| mapping.json | association_version | 1 | association_version, capture_sha256, model_sha256, observations_sha256, candidates_sha256, proposals |
| comparison.json | comparison_version | 1 | comparison_version, capture_sha256, model_sha256, observations_sha256, mapping_sha256, association_decisions, findings, declared_services_not_observed, absence_assessment, absence_scope, work, limitations |
| ARP flow metadata | metadata_version | 1 | metadata_version, opcode, operation, sender_protocol_address, target_protocol_address, sender_hardware_address, target_hardware_address, ethernet_source_mac, ethernet_destination_mac, ethernet_delivery |

Protocol catalog is independently versioned by `catalog_version: 1`. Site contract
1 is presentation, not a stable DOM API. CLI envelopes and native model schema
are separate contracts. Required keys/types are exercised by the independent
consumer and golden corpus; source producers remain the authoritative full layout.

Observation v1 historically placed ARP SPA/TPA in source_ip/destination_ip and
aggregated target-only addresses as hosts with Ethernet destination MAC evidence.
It also merged distinct ARP opcodes/claims. V2 preserves those generic flow fields'
historical SPA/TPA meaning, adds explicit ARP metadata (null for other flows),
changes ARP grouping/identities and excludes target-only/unspecified sender entries.
Non-ARP flow/group identity formulas remain unchanged. Host records add sorted
`observation_roles`: packet_source, packet_destination, arp_request_sender,
arp_reply_sender. These are observation roles, never verified ownership.

The analyzer association adapter and frozen consumer explicitly reject v1
observations. Regenerate from the original capture, regenerate mapping proposals
and repeat owner review; no silent reinterpretation or automatic decision migration
is allowed. Association/comparison shapes retain version 1 because their existing
observation hash bindings make prior decisions stale. Observation version is checked
before analysis. Historical v1 outputs may be archived/read under their original
semantics by a separately versioned reader; this consumer deliberately rejects them.

Compatible additions are optional fields that preserve meanings, or independently
versioned optional evidence. Required-key removal, changed meaning/identity formulas,
changed ordering or incompatible enum semantics require a version revision and
explicit migration or rejection policy. Unknown optional fields and unknown future
classification strings are preserved as unassessed by the reader. They never acquire
a positive/negative interpretation from an unfamiliar code. Review input is stricter:
unknown owner-decision fields remain rejected by the product.

## C. Types, ordering and identities

JSON is UTF-8, ASCII escaped, sorted object keys, two-space indentation and one LF
after the final object. Hash inputs instead use compact sorted keys, ASCII escaping,
and separators `,` / `:` without whitespace. Integers are JSON integers (booleans
are not versions/counters); no NaN/Infinity/duplicate keys. Arrays retain their
documented deterministic order. Missing data is explicit null or empty collections,
never fabricated zero-valued timestamps or inferred sessions.

- Capture ID and sha256 are the lowercase SHA-256 of exact original file bytes.
  The original file is not embedded. `format` is pcap/pcapng from its header.
- Interface records contain integer section/interface/linktype/snaplen,
  timestamp_denominator and signed timestamp_offset_seconds. Section/interface
  pairs are unique; interface IDs are local to each section.
- Hosts are sorted by IP text; host ID is `host-` plus digest([ip_version, ip]).
  Each includes ip, ip_version (4/6), packets, source_macs, destination_macs and
  observation_roles. MAC sets are sorted Ethernet observations, not ownership.
- Flows are sorted by ID. Required keys are id, conversation_id, source_ip,
  destination_ip, source_port, destination_port, transport, arp, transport_evidence,
  ip_version, vlans, linktype, status, packets, captured_bytes, original_bytes,
  first_timestamp, last_timestamp, missing_timestamps, interfaces, source_macs,
  destination_macs, samples, samples_omitted, tcp_flags, initiation_evidence,
  initiation_packets, initiation_evidence_omitted, protocol_hints, limitations.
  IPs are canonical text or null, ports integers 0..65535 or null, VLAN IDs 0..4095,
  transport tcp/udp/icmp/icmpv6/arp/unknown, status decoded/truncated/malformed/
  fragmented/unsupported. transport_evidence is TRANSPORT_OBSERVED or UNKNOWN;
  hints are objects with protocol, level=PORT_HINT and port. No confirmed
  application recognition is produced.
- Let E be ordered [(source_ip or "", source_port or -1 when null), (destination_ip
  or "", destination_port or -1 when null)]. Flow ID is `flow-` plus digest of
  [E, transport, ip_version, vlans, status, linktype], appending the complete arp
  object when nonnull. Zero ports remain zero, not -1. ARP operation is request,
  reply or unsupported according to opcode; Ethernet delivery is broadcast,
  multicast or unicast from the actual destination MAC.
- Conversation ID is `conversation-` plus digest([sorted(E), transport,
  ip_version, vlans]), appending arp if present and linktype if both IPs are null.
  Groups are sorted by ID; member flow_ids are sorted. Each has transport,
  ip_version, vlans, linktypes, packets, captured_bytes, original_bytes,
  first_timestamp, last_timestamp, initiation_direction (observed_syn,
  conflicting_syn, uncertain), initiator_flow_id or null, and limitations.
  Packet counts/bytes sum members; these groups are not sessions.
- First/last timestamps are reduced rational UTC second strings `numerator/denominator`
  or null. Packet samples carry one-based index, record/block offset, section,
  interface, captured_length, original_length, and timestamp null or an object
  with unsigned ticks, positive denominator and signed offset_seconds. References
  require the exact capture digest and are not payload copies. Flow samples and
  initiation samples retain first encounters; omitted counters preserve denominators.
- Observation digest excludes only observations_sha256 itself. Added optional
  fields change this integrity digest, even when semantic contract-compatible.
- Each proposal has id, host_id, observed_ip, candidates (sorted asset_id /
  interface_id pairs), decision, selected_asset_id, selected_interface_id, reviewer,
  rationale. IDs are `association_` plus digest of host_id/observed_ip/candidates.
  Templates order proposals by host ID. Owner reviews may reorder proposals while
  preserving every original proposal exactly once; comparison retains that reviewed
  order. Candidate digest covers immutable proposal cores in canonical host-ID
  order, excluding the five mutable decision fields. Decisions are PENDING/ACCEPT/REJECT. Pending
  has empty reviewer/rationale and null selections; other decisions need nonblank
  bounded text; ACCEPT must select an original candidate. No automatic approval.
- Mapping digest covers the complete reviewed object. Model SHA is the existing
  native canonical-model identity. Comparison binds capture, model, observation
  and complete mapping hashes.
  association_decisions exactly copies reviewed proposals; findings retain flow
  order and include flow_id, conversation_id, classification, reason, samples,
  association_decision_ids, capture_sha256, model_sha256, native_result (null or
  original query/selected interval/evidence). Codes are listed in the supported
  product guide, unchanged by human display labels. Finding references join actual
  flows and endpoint decisions; native witnesses assess declarations only.

Coverage requires packets, decoded, truncated, malformed, fragmented, unsupported,
interpreted_packets, uninterpreted_packets, complete_file_scan and
capture_records_truncated. Categories sum to the record count. Resource failure
publishes no report; successful coverage can still explicitly include uninterpreted
packets/unknown blocks. Absence status is scoped/suppressed; unknown content or
snapshot truncation suppresses absence findings. All limitations remain available.
No volatile execution metadata enters these identities.

Defaults are bounded by CaptureLimits and the [supported-format guide](../pcap-evidence-studio.md):
512 MiB input, 1 million records, 256 interfaces, 20,000 hosts/decisions, 50,000
flows/groups, 64 MiB accounted aggregation/output, 8 packet samples per kind per
flow, 8 MiB mapping, 4,096 review characters, 128 native query pairs, cumulative
5 million work units. Earlier budgets may reject before a cardinality ceiling.
The read-only probe bounds individual JSON files to 64 MiB and nesting to 64;
it validates a finite bundle, not every possible native witness or capture byte.

## D. Independent evidence and quality

`tools/read_capture_evidence.py` imports no analyzer/decoder and never opens a
capture. It checks versions, canonical hashes, reconstructed aggregate identities,
interface/sample joins, group and coverage denominators, candidate/review bindings,
and finding references, while preserving unfamiliar optional evidence and codes.
It does not reproduce native model evaluation or validate assertions' truth.
Machine-checkable constraints are executable validation rather than a decorative
JSON Schema that would diverge from the producer.

`tests/fixtures/capture-contract-v2/` freezes six complete artifacts plus hashes.
The supported case covers TCP/UDP, ARP request, IPv6, unmapped endpoints, reviewed
mappings, reachable/unreachable, undeclared service, uncertain direction and
declared services not observed. The limited case adds ARP reply and unsupported
Ethernet evidence; it suppresses absence conclusions. Neither directory contains
raw capture bytes. Exact regeneration uses `python -m tools.freeze_capture_contracts
--output NEW_DIRECTORY`; tests compare every byte and two fixed observation hashes.
Consumer adversarial tests recompute outer hashes to challenge structural joins.
Final installed commands/results and exact source identity are in V13-20.

## E. Risks and next step

Integrity is not authenticity: hashes do not prove creator identity, signed review,
chain of custody, physical ownership or honest source observations. A future reader
must retain uncertainty and scope. Finite golden/adversarial tests are not a proof
of all inputs. Changes remain possible for correctness/security, with explicit
contract handling. V1.4 can consume timestamps, aggregates, classification and
capture/model identities without changing the analyzer; new historical functionality
requires separate design. Final gate status depends on V13-20 verification; human
browser and hosted acceptance remain independent outstanding milestones.
