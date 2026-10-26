# V13-22 — Feature completion and release readiness

## A. Executive status

**ENGINEERING VERIFIED — OWNER ACCEPTANCE PENDING** for candidate
`5c4c18da4711c36f4f5750c03009d429551d0cf0`. The implementation is feature complete
within its declared supported subset. Corrected hosted run 40246239841 passed all
six OS/Python configurations; each wheel and sdist suite passed 2,746 cases without
errors, failures or skips, and all retained artifacts were independently verified.
Human browser acceptance remains pending. Feature complete, locally tested, hosted
validated, human accepted, merged and published are distinct milestones. No owner
approval for stable release publication is recorded.

The owner authorized only the exact candidate pushes 38c1ec9 and 5c4c18d. This final
documentation-only acceptance record is local and has no hosted CI of its own;
its separate identity is in the supplemental manifest. Tested candidate, selected
archive source and evidence-record commit must not be conflated.

## B. Completed functionality and supported scope

- Passive offline PCAP2.4 and documented PCAPNG framing, streaming bounds,
  cryptographic file identity and transparent unsupported-content accounting.
- Ethernet/VLAN, raw IP, IPv4/IPv6 header observations, TCP/UDP/ICMP/ICMPv6,
  explicit ARP protocol claims and Ethernet delivery; conservative port hints.
- Deterministic directed aggregates, conversation groups, timestamps/counters,
  bounded packet references and unresolved observed-address provenance.
- Exact model association proposals, explicit evidence-bound owner decisions,
  strict stale/invalid review rejection and unchanged authoritative architecture.
- Conservative native reconciliation of justified reviewed IPv4 TCP initial-SYN
  evidence, retaining original selected interval/witness/diagnostics and uncertainty.
- Audited offline HTML/CSS/SVG Explorer, readable classifications/exact codes,
  ARP field panels, linked complete evidence, pagination and dense fallback.
- Versioned evidence contracts, golden regeneration and independent read-only
  consumption without raw captures. Observation2/capture1/catalog1/association1/
  comparison1/site1; native schema1 remains unchanged.

The exact supported formats/features and rejection ceilings are in
[the product guide](../pcap-evidence-studio.md). V13-14's independently generated
synthetic corpus and V13-15's ARP tests define accepted interoperability/semantics;
no universal producer/protocol support is claimed. V13-18 freezes public meanings,
ordering, integrity rules and revision/rejection policy for future v1.4 readers.

## C. Evidence and release artifacts

V13-20 binds the exact versioned source, full separately installed wheel/sdist
suites, strict quality checks, historical compatibility, console walkthroughs,
archive audits and module hashes. The release manifest and SHA256SUMS.txt bind
the actual selected `otarchguard-1.3.0-py3-none-any.whl` and
`otarchguard-1.3.0.tar.gz` bytes returned by the backend. Final release notes,
changelog, installation guide and fictional tutorial are packaged source.

V13-21 records [the corrected six-cell run](https://github.com/z4y-d3n/OT-ArchGuard/actions/runs/40246239841)
as PASS for 5c4c18d, with exact source, package and per-job identities. The earlier
run's four POSIX typing failures and two Windows successes remain historical
evidence; they are not substituted for the accepted candidate. The one-line
benchmark guard correction is validated by the fresh run without changing the
analytical core or public evidence meanings. The local correction-candidate
archives and hosted artifacts are tied to 5c4c18d; a later documentation-only HEAD
is not a new selected archive source and is not claimed to have that CI.

V13-17 records human checklist items as NOT RUN, with the owner's explicit pending
review response. Static/raster/browser-tool observations do not replace human
acceptance. The final supplemental manifest and checksums are under
`output/v13-hosted/`; immutable prior manifests remain available for provenance.

## D. Quality and known limitations

NAT, DHCP/IP reuse, spoofed claims, transit MACs, partial sensor visibility,
duplicates, capture loss and incomplete session evidence limit conclusions.
No live capture/scanning, deep industrial inspection, reassembly/checksum validation,
application success inference, deployed firewall verification, historical analysis,
drift detection or multi-capture lifecycle is included. Unsupported/ambiguous data
remains unassessed; absent traffic never proves blocking. ARP target mentions
never prove device existence or response. Owner mappings assert finite evidence
identity, not cryptographic authenticity or physical ownership.

Resource accounting is conservative rejection behavior, not an OS RSS cap. One
native interval may be in flight before evidence accounting. Filesystem checks
are local single-writer safeguards, not isolation from a concurrently hostile
filesystem; POSIX publication races retain documented limits. Network metadata
and exact review text remain sensitive; no complete anonymization or security/
accessibility certification is claimed. Independent finite corpora are not a proof
against all malformed captures or decoders.

## E. Unresolved issues and maintenance policy

No confirmed unresolved critical/high analyzer defect remains within the reviewed
supported subset. The benchmark platform-typing failure was corrected and all six fresh hosted
configurations passed. Human acceptance and owner-controlled integration/publication
remain outstanding.
Outstanding concrete acceptance
requirements are six-cell hosted CI, actual human browser checklist and owner
review. If either reveals a defect, fix it and repeat affected validation before
claiming release readiness. Deep industrial inspection remains a possible v1.4
proposal requiring demonstrated value and separate owner approval, not a hidden
v1.3 release dependency.

Freeze planned feature development of the analytical core and public meanings.
Security fixes and correctness corrections remain allowed; new functionality
requires demonstrated need and explicit scope. Contract-breaking corrections
require a documented revision and migration or rejection. Future maintenance
cannot be ruled out. V1.4 can build readers on these frozen interfaces without
redesigning the core, subject to closing the outstanding acceptance evidence.

## Final acceptance checklist

| Requirement | Recorded state and evidence |
|---|---|
| PCAP / PCAPNG accepted subset, independent interoperability | PASS locally; V13-14 and installed suites in V13-20 |
| Accurate metadata/aggregates, explicit unsupported content, conservative port hints | PASS locally; parser/observation/interoperability/semantic tests |
| ARP sender/target/delivery and target-only exclusion | PASS locally; V13-15, V13-16 and frozen consumer |
| Explicit owner mapping and unchanged native evaluator semantics | PASS locally; strict decision tests and 45-case historical comparison |
| No authorization from observed traffic, blocking from absence, or session success inference | PASS within tested scope; semantic tests, notices and scoped/suppressed absence |
| Readable labels/count grammar/ARP panels, exact codes, privacy warnings | PASS static engineering; V13-16; human visual review pending |
| Evidence links, pagination and complete dense fallback | PASS automated site audits; human navigation pending |
| Browser keyboard/focus/200% zoom/narrow layout/accessibility interaction | NOT RUN; V13-17, owner explicitly pending review |
| Determinism, hostile input, budgets, fatal-output preservation, denied Python networking | PASS locally; installed regression and fixed resource receipts |
| Historical native regression, new capture/ARP tests and read-only future consumer | PASS locally; V13-18 / V13-20, counts overlap |
| Runtime 1.3.0, archive metadata, regular installs, source/module identity and checksums | V13-20 final audit and release-manifest.json are authoritative |
| Six hosted final-candidate configurations | PASS for exact 5c4c18d; V13-21 and independently verified artifacts |
| Final owner approval before release publication | NOT GRANTED; only exact candidate pushes 38c1ec9 and 5c4c18d authorized/performed |

## F. Owner-controlled next step

Complete the human checklist. The two authorized candidate pushes and all six
corrected hosted checks are finished. Review the separate local documentation-only
record before any separately authorized publication or integration of that identity.
PR creation, merge, tags, release, PyPI upload, branch deletion or settings changes
each require separate specific authorization. Reverify a resulting integration
commit; candidate-branch success does not automatically validate a merge commit.
