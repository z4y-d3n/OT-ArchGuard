# v1.4 development foundation

This is a local v1.4 development checkpoint, package/CLI `1.4.0.dev1`.
The unchanged native engine retains identity `1.3.0` to preserve frozen evidence.
The legacy Python `__version__` remains that engine alias; use
`DISTRIBUTION_VERSION`, installed distribution metadata or `--version` for the
development product identity.
The stable release is v1.3.0; this modified branch is not a stable distribution.
The following operations are implemented; historical comparisons and baseline
approval are not yet available.

## Independent protocol metadata

```console
otarchguard capture enrich authorized-local.pcap --output protocol-enrichment.json
```

The command scans local PCAP/PCAPNG through the existing bounded reader and emits
the independent version-1 enrichment JSON to stdout and, optionally, a fresh file.
It never overwrites a destination. No packet bytes are exported. Supported subsets
are Modbus TCP on 502, EtherNet/IP/limited CIP on 44818, classic S7comm on 102,
IEC-104 on 2404, OPC UA Binary on 4840, DNP3 on 20000, and Layer-2 PROFINET DCP
over EtherType `0x8892`, including supported VLAN envelopes. TCP only; UDP and
implicit I/O remain unsupported. Complete records must
fit in the bounded packet view. The Python interface permits explicit Modbus
selection on another port; the CLI does not perform speculative protocol searches.

`STRUCTURALLY_VALID` means only that the supported frame subset was validated.
`PORT_HINT` and `ETHERTYPE_HINT` are suggestions. `TRUNCATED`, `MALFORMED` and
`UNSUPPORTED_VARIANT` never acquire a positive interpretation. A write-type label
does not establish request direction or execution. Segmentation, fragmentation,
unsupported outer headers and configured record/view limits cause abstention or
controlled failure. No stream reconstruction, transaction matching, application
values, ownership assertions or native evaluator results are added.

Enrichment binds the exact capture SHA-256. `observations_sha256` is null in this
slice because enrichment is independent of the existing observation artifact.
It must not be treated as an approval of newly decoded meanings by a historical
mapping reviewer. Enrichment schema 1 now emits decoder revision 2; the strict
reader also accepts the original two-protocol decoder revision 1.

The artifact's `counts` separates each protocol and recognition status, for example
`"iec104:STRUCTURALLY_VALID": 1` and `"s7comm:UNSUPPORTED_VARIANT": 2`.
Counts describe retained records; `skipped_packets` separately explains unsupported
outer frames and noncandidate traffic. A header category is not an asset, approval
or successful industrial operation. Secure OPC UA bodies remain opaque. DNP3
addresses are protocol addresses. See the exact [EtherNet/IP/S7 subsets](development/v14-enip-s7.md)
and [IEC104/OPC UA/DNP3 subsets](development/v14-iec-opc-dnp.md),
[external capture evidence](development/v14-external-corpus.md) and
[version decision](development/v14-version-identity-adr.md).

## Immutable snapshot import

Create the existing offline observations report first, then import its metadata:

```console
otarchguard capture analyze examples/capture-studio/plant.pcap --output capture-site
otarchguard evidence init evidence-workspace
otarchguard evidence add evidence-workspace capture-site/observations.json --label "Fictional reference"
otarchguard evidence list evidence-workspace
otarchguard evidence verify evidence-workspace
otarchguard evidence show evidence-workspace snapshot-EXACT_DIGEST_FROM_LIST
```

The final command requires the exact `snapshot-` identity returned by `add` or
`list`; the placeholder is not a literal usable identity. `show` returns the full
preserved metadata. `verify` reports `VERIFIED_METADATA`: it validates supported
contract structure and internal hashes, without reopening the original capture.
It does not prove original capture availability, collection authority or truth.

Workspaces contain a version-1 `workspace.json` and immutable version-1 snapshots
under `snapshots/`. Snapshots include exact observation v2 metadata, capture and
observation digests, a bounded label, exact rational collection-time bounds and
missing timestamp counts. No raw capture is copied. Import time and absolute local
paths do not enter generated snapshot identity. The supplied label is content-bound;
renaming an input file does not change its capture identity.

Repeated capture SHA-256 returns `DUPLICATE_CAPTURE`. The first snapshot and label
remain intact; the response indicates whether observation hashes and labels match.
This is not evidence merging or deduplication of packets within separate captures.
Snapshot IDs are deterministic; they are not a chronological sort order.

Expected failures return exit 2 with structured diagnostics and no successful JSON
on stdout. Local publication uses atomic no-replace rename on Windows and
no-replace hardlinks on POSIX; unsupported filesystems fail closed.
The workspace assumes a local single writer.
An interrupted `.pending-*.tmp` entry blocks validation with `EVIDENCE_INTERRUPTED`;
review and move the uncommitted temporary file outside the workspace before retrying.
Do not modify committed snapshot files as a recovery procedure.

Derived evidence can contain sensitive addresses, topology, labels and imported
metadata text. Review it before sharing. Hashes provide integrity, not authenticity.
The lifecycle storage consumer rejects unknown extension fields and never rewrites
the source observation to remove them; its v1 policy is narrower than the frozen
read-only probe. Unknown codes in supported text fields do not become assessments.
The lifecycle currently imports observations only: enrichment attachments, reviewed
associations, native comparisons, explicit baselines, drift, reports and bundles
require subsequent contracts. No association is carried across capture periods.

See [architecture decisions](development/v14-architecture.md),
[corpus provenance](development/v14-protocol-corpus.md) and
[remaining acceptance work](development/v14-progress.md).

## Reproduce the original fictional demonstration

After installing the current local wheel, run from this source checkout:

```console
python -m tools.evidence_walkthrough --output output/evidence-walkthrough
```

The output directory must be new. The tool exercises the installed console,
generates existing offline capture reports for two fictional collections, exports
independent enrichment, imports two snapshots, demonstrates duplicate handling
and verifies the workspace. Its first four-frame input has an independent
TShark receipt in the original synthetic corpus. `walkthrough.json` records the
executed commands and exact source identities; it is an execution receipt, not
an analytical history contract. It does not perform a historical comparison.
