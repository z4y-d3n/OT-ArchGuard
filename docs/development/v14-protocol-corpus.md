# V14 protocol corpus provenance

Current V14-01 inventory and actual external laboratory validation supersede the
historical V14-00 review below: see [external corpus evidence](v14-external-corpus.md).
The manifest now includes reviewed local-analysis references with actual byte
identities; their raw bytes remain outside Git and release archives. Tier 2 is
still empty because redistribution rights are not established per capture.

This is the initial V14-00 corpus review, dated 2026-10-26. Real-world industrial
capture validation remains pending. No external packet bytes are redistributed.

## Corpus tiers and current decisions

The independently versioned, machine-readable inventory is
`tests/fixtures/protocol-corpus/manifest.json` (`manifest_version: 1`).

| Tier | Meaning | Current inventory |
|---|---|---|
| 1 | Original, independently authored synthetic fixtures | One 339-byte PCAP containing four fictional frames |
| 2 | External fixtures with reviewed redistribution rights | Empty; no permission has been established |
| 3 | External reference candidates; bytes excluded from packages | Four source/candidate records, all unapproved |

Unknown facts are JSON `null`. Candidate source labels and protocol families are
research leads, not verified observations. Approval labels in this development
manifest record a local review assertion, not source authenticity or legal advice.

### Original synthetic fixture

`synthetic-industrial.pcap` is generated exactly by `synthetic_capture()` in
`tests/test_protocol_corpus.py`, without importing product parsers, serializers or
capture generators. The fixture has two Modbus TCP records, one PROFINET DCP
Identify request, and one unrelated PROFINET FrameID. Addresses use RFC 5737
documentation space and locally administered fictional MAC addresses. All process
values are zero. It contains no real topology, credentials or external traffic.

The fixture SHA-256 is
`9c76cfdb752a20f1a4b3d932352d6f68c514539677def2af800bcc5d41c63559`.
The fixture and original generator are covered by this repository's Apache-2.0
license. IPv4/TCP checksums are zero: the fixture tests header structure and does
not establish checksum correctness or session success.

`tshark-receipt.json` was produced from the exact bytes by
`TShark (Wireshark) 4.6.7 (v4.6.7-0-gb439fb7b47a9)`. It retains only allowlisted
header metadata. TCP desegmentation was disabled. Its ordered `fields`, `arguments`
and packet rows record the reproducible invocation; append `-e FIELD` for every
listed field, replace the literal `INPUT` with the local fixture path, and invoke
that TShark version. The input identity binds the receipt to the fixture. Tests
verify independent Modbus FC3 and DCP service 5 metadata and the unrelated FrameID
negative. Product enrichment emits three records and skips the unrelated fourth
frame as `NON_DCP_PROFINET_FRAME_ID`; it does not assign that traffic a DCP label.
Ordinary tests read the receipt and do not require Wireshark installed.

An independent reference decoder and synthetic packets do not constitute
real-world interoperability validation. They also do not justify claiming support
for every field the reference decoder recognizes.

### External source review

| Source | Inspected identity | Decision and missing evidence |
|---|---|---|
| [automayt/ICS-pcap](https://github.com/automayt/ICS-pcap/tree/13b7ae335529146b40535c2d7aa756886040d8ad) | Commit `13b7ae335529146b40535c2d7aa756886040d8ad` | Candidate only. Reviewed tree has no LICENSE file. README credits mixed upstream sources; a repository-wide grant would not automatically establish each capture's rights. |
| [Wireshark DCP index](https://wiki.wireshark.org/PROFINET/DCP) | Mutable public index referencing `ChangeIPUsingDCP.pcap` | Candidate only. Collector, exact payload digest, immutable source and per-capture permission remain unknown. |
| [Wireshark SampleCaptures](https://wiki.wireshark.org/SampleCaptures) | Mutable index referencing IEC104, S7comm and DNP3 samples | Candidate index only. The DNP3 section credits pcapr.net by bwilkerson. No payload acquired or permission inferred from public availability. |
| [CISA ICSNPP](https://github.com/cisagov/ICSNPP/tree/12b5d2416dcdbf5fb8225f6b268ea8ec1867af4d) | Commit `12b5d2416dcdbf5fb8225f6b268ea8ec1867af4d` | Reference to Zeek parsers and scripts; no Python runtime dependency or implementation copied. Root code LICENSE is BSD-3-Clause. Each submodule capture requires its own provenance review. |

The inspected ICS-pcap `MODBUS/Modbus/Modbus.pcap` blob is a **Git LFS pointer**.
Its advertised OID is recorded as unverified contextual text, not the manifest's
verified `sha256`. The pointer advertises 8,337 payload bytes; the actual bytes
have not been downloaded, hashed or tested. A 129-byte pointer is not a capture.

Before promoting an external entry, record original author/collector, exact source
and revision, actual payload SHA-256 and size, license scope, attribution, privacy
review, decoder expectations, negative cases and independent tool version. Keep
Tier 3 bytes outside source and release archives. Promote to Tier 2 only with an
explicitly reviewed redistribution grant. Preserve unavailable sources as a setup
outcome rather than silently replacing expected bytes.

## Offline verification tool

The development tool uses only the standard library and never fetches URLs,
resolves names, starts packet analysis or extracts archives:

```powershell
python -m tools.protocol_corpus --manifest tests/fixtures/protocol-corpus/manifest.json
python -m tools.protocol_corpus --manifest tests/fixtures/protocol-corpus/manifest.json --verify synthetic-industrial --file tests/fixtures/protocol-corpus/synthetic-industrial.pcap
```

It rejects candidates, future versions, duplicate JSON keys/identities, nonfinite
numbers, malformed bounded fields, unsafe relative filenames, non-HTTPS source
references, changed byte identities and LFS pointers. Reads reject symlinks and
Windows reparse points and check ordinary file changes. Limits are 128 KiB per
manifest, 64 entries, 4,096 characters per text, 32 values per list and 16 MiB per
local file. JSON diagnostics do not print capture payloads.

This is single-user development integrity checking, not a defense against a
malicious filesystem administrator. A hash cannot authenticate a collector or
establish redistribution rights. Verification of local bytes requires an already
validated manifest; `verify_file()` is a helper for that workflow.

An opt-in downloader is deliberately **not implemented** while all external
entries are unapproved. The next acquisition milestone must enforce an exact
manifest allowlist, reviewed HTTPS source/redirect destinations, actual expected
hashes, download/file-count limits, atomic no-overwrite publication and no archive
extraction. Product analysis must never initiate that workflow.

## Framing references and scope

| Protocol | Authoritative or independently maintained reference | Initial corpus scope |
|---|---|---|
| Modbus TCP | [Modbus Organization TCP/IP Implementation Guide V1.0b, MBAP sections 3.1.2–3.1.3](https://www.modbus.org/file/secure/messagingimplementationguide.pdf) | Two complete fictional FC3 messages; no process-value interpretation |
| PROFINET DCP | [Apache PLC4X schema at commit 60ef1313a6c06b09a8fabb932e3ed077e79ceacd](https://apache.googlesource.com/plc4x/+/60ef1313a6c06b09a8fabb932e3ed077e79ceacd/protocols/profinet/src/main/resources/protocols/profinet/profinet.mspec) | One fictional L2 Identify AllSelector and one unrelated PROFINET FrameID |
| EtherNet/IP / limited CIP | ICSNPP enip source reference above | No fixture or real-world coverage claimed in V14-00 |
| Classic S7comm | Wireshark SampleCaptures / ICSNPP s7comm references above | External candidate only |
| IEC 60870-5-104 | Wireshark SampleCaptures reference above | External candidate only |
| OPC UA Binary | ICSNPP opcua-binary reference above | Source reference only |
| DNP3 | Wireshark SampleCaptures / ICSNPP dnp3 references above | External candidate only |

The PLC4X schema was consulted as a framing reference; no implementation was
copied. DCP is Layer 2 EtherType `0x8892`, with FrameID distinctions, not a TCP/UDP
port parser. The synthetic fixture intentionally includes unrelated PROFINET
traffic to test this boundary.
