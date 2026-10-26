# Fictional PCAP evidence tutorial

This released example uses generated documentation addresses and traffic, not
real equipment or an operational capture. Obtain these files from the verified
[published v1.3.0 source distribution](https://github.com/z4y-d3n/OT-ArchGuard/releases/tag/v1.3.0)
or an already obtained checkout at tag `v1.3.0`:

- `plant.pcap` and `plant.pcapng`: equivalent ten-record teaching captures.
- `architecture.yaml`: five fictional assets and two declared services.

The declared firewall is inventory context, not evidence of a captured intermediate
route. Sensor visibility is intentionally partial: the samples establish neither
session completion nor historian traffic. A wheel contains the application but
not these example inputs. Follow the [installation guide](../../docs/installation.md)
to verify published assets and install Python 3.12 or later in a separate environment.

## Packaged ten-record workflow

Copy all three files into a writable working directory, then run the regular
installed console from that directory. Use fresh destination names:

~~~text
otarchguard --version
otarchguard capture inspect plant.pcapng
otarchguard capture analyze plant.pcapng --output observed
otarchguard capture map plant.pcapng --model architecture.yaml --output pending.json
~~~

Require version `1.3.0`. `inspect` reports container/interface/record metadata;
`analyze` produces `observations.json` and an offline evidence site.
`map` writes proposals, all awaiting explicit owner review. No identity or
network authorization is accepted automatically.

Review `pending.json` using the
[association decision contract](../../docs/pcap-evidence-studio.md#association-decisions).
For this fictional model only, an exact candidate can be selected with
`decision: "ACCEPT"`, its proposed asset/interface IDs and an explicit reviewer
and rationale. Leave unmatched or unresolved proposals `PENDING` with null
selections and empty reviewer/rationale. Only decision fields may change; keep
every proposal and all binding hashes intact. Save the reviewed copy as
`reviewed.json`, then run:

~~~text
otarchguard capture compare plant.pcapng --model architecture.yaml --mapping reviewed.json --output comparison
~~~

Accepting the unique exact-address candidates produces the expected categories
below; leaving decisions unresolved instead produces unmapped evidence. Real
captures require actual owner decisions. Fictional fixture-author choices do not
authenticate an operational identity or substitute for that review.

Open `comparison/index.html` directly in a local browser and keep the complete
folder together. No server, JavaScript or network service is needed after
generation. Start at Overview, follow an observed address to its communications,
then open a finding, group, association or exact evidence detail. UTC text retains
the original precise timestamps; technical disclosures and canonical JSON preserve
full identifiers and packet references. Bidirectional groups are related tuples,
not proven sessions.

## Expected interpretation

| Observation | Expected meaning after the fictional exact candidates are accepted |
| --- | --- |
| Engineering `192.0.2.10` → PLC `192.0.2.20` TCP/502 | Compatible with the declared model's reachability |
| HMI `192.0.2.11` → PLC TCP/502 | Declared transport edge exists but no matching allow; model discrepancy |
| TCP/102 initiation | No declared listener matches that destination port |
| Response-only TCP and UDP | Initiation direction remains uncertain |
| ARP and IPv6 | Observational evidence outside native reachability evaluation |
| Unmodeled addresses `192.0.2.98` and `192.0.2.99` | No accepted declared identity |
| Historian service TCP/4840 | Not observed in the packaged, fully interpreted ten-record scope |

TCP/502 is a Modbus/TCP **port hint**, not payload recognition. A model discrepancy
does not prove a deployed firewall violation. Missing historian traffic does not
prove blocking or service unavailability. ARP targets do not prove device existence,
ownership or response. No packet proves successful application communication.

## Extended twelve-record walkthrough

From the verified source distribution or checkout root, with a **regular installed
wheel or sdist** selected by the same interpreter:

~~~text
python -m tools.capture_walkthrough --output "output/capture tutorial"
~~~

Create the parent `output/` directory first and choose a destination that does
not exist. The script calls that interpreter's installed `otarchguard` launcher
for inspect, analyze, map and compare. It creates a ten-record classic PCAP and
an extended twelve-record PCAPNG containing an additional ARP reply and unsupported
Ethernet content. It writes both a pending template and a separately named
`fictional-reviewed.json` whose reviewer/rationale explicitly identify generated
teaching decisions.

Open `output/capture tutorial/comparison/index.html`. The extended comparison
checks six categories: model-compatible, model discrepancy, undeclared service,
unmapped endpoint, uncertain direction and unsupported observation. Its
declared-service absence assessment is **suppressed** because some packet content
is uninterpreted. The packaged ten-record captures remain the fully interpreted
companion for scoped absence examples. Neither absence nor suppression proves
that a service is blocked.

To reproduce the packaged fixture bytes, use `tools.capture_workloads.write_pcap`,
`write_pcapng` with its default `extended=False`, and `plant_model`. The extended
walkthrough deliberately selects `extended=True`. Neither generator uses a sniffer,
network service or external packet library.

## Release verification and scope

The immutable released source is `10d7de6c416ec6f0ee364c671ebe9292ee69e672`.
Its [final integration CI](https://github.com/z4y-d3n/OT-ArchGuard/actions/runs/40273411275)
passed all six Windows/Ubuntu/macOS × Python 3.12/3.14 configurations, with
2,815 tests per installed wheel/sdist suite and zero failures, errors or skips;
the suite counts overlap. The final evidence interface also passed its second
human browser review on all six criteria, including navigation and interpretation.
The earlier failed criteria remain historical evidence, not open release gates.

This browser acceptance concerns the product presentation. It is separate from
the fictional association decisions in this example and does not certify those
decisions for real equipment. Later documentation changes do not alter released
package bytes or inherit a different commit's CI result.

The independent interoperability corpus is also fictional: specification-authored
bytes and Wireshark `text2pcap` 4.6.7 output checked against offline TShark receipts.
It is not real industrial traffic or proof of universal capture compatibility.
See the [corpus policy](../../docs/pcap-evidence-studio.md#capture-corpus-and-use-policy).
