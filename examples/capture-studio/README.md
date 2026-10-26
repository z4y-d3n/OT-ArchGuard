# Fictional PCAP evidence tutorial

All addresses and traffic are generated, not captured from real equipment.
The packaged `plant.pcap` and `plant.pcapng` contain equivalent ten-record teaching traffic.
`architecture.yaml` declares five fictional assets and two services. The firewall
is inventory context, not a claim about a captured intermediate route. Sensor
visibility is intentionally partial: no session completion or historian traffic.

From an unpacked source distribution with a **regular installed wheel or sdist**:

```text
python -m tools.capture_walkthrough --output "output/capture tutorial"
```

Choose an output that does not exist. The script calls the interpreter's installed
`otarchguard` launcher for inspect, analyze, map and compare. It produces pending
decisions and a separately named fictional-fixture-author reviewed file. Those
decisions demonstrate the contract; they are not real owner approvals.
Open `output/capture tutorial/comparison/index.html` directly. No server or network.
Start with the Overview counts and finding summaries. Follow an observed address
to its related communications, then open the communication's finding and exact
evidence. Associations explain owner assertions; bidirectional groups collect
related tuples without establishing a session. Technical details retain full
identifiers and original packet references, while canonical JSON remains directly
accessible. UTC displays format the original exact timestamps without changing
their rational evidence values.
The final walkthrough generates the ten-record classic capture and an extended
twelve-record PCAPNG with an ARP reply and unsupported Ethernet content. Its
comparison explicitly suppresses declared-service absence because interpretation
is incomplete. The packaged ten-record captures remain a fully interpreted
companion for scoped absence examples; no missing packet proves blocking.

Alternatively copy `plant.pcapng` and `architecture.yaml` from this directory to
any local folder after installing a wheel, and run:

```text
otarchguard capture inspect plant.pcapng
otarchguard capture analyze plant.pcapng --output observed
otarchguard capture map plant.pcapng --model architecture.yaml --output pending.json
```

Review `pending.json` as described in the [user guide](../../docs/pcap-evidence-studio.md).
Save decisions as `reviewed.json`, then:

```text
otarchguard capture compare plant.pcapng --model architecture.yaml --mapping reviewed.json --output comparison
```

Independent expectations: engineering `192.0.2.10` to PLC `.20` TCP502 is model
reachable; HMI `.11` to PLC TCP502 has a declared transport edge but no allow and is
model unreachable. TCP102 has no declared listener. Response-only TCP and UDP do
not establish initiation. ARP and IPv6 are observational only. Addresses `.98` and
`.99` have no declared identity. Historian service TCP4840 is not observed; this
does not prove blocking. Port502 is a Modbus/TCP **hint**, not payload recognition.

To regenerate the exact packaged fixture bytes, use `tools.capture_workloads.write_pcap`,
`write_pcapng` with its default `extended=False`, and `plant_model`; no network or
packet library is involved. The final walkthrough explicitly selects `extended=True`.

The independently produced interoperability corpus is separate from this tutorial:
it combines specification-authored synthetic bytes and Wireshark `text2pcap`
4.6.7 output checked with offline TShark receipts. Neither is real industrial
traffic. See the [corpus policy](../../docs/pcap-evidence-studio.md#capture-corpus-and-use-policy).
The previous six-platform CI accepted `5c4c18d`; a changed UX candidate needs its
own validation and a second owner browser review. Original navigation and
interpretation failures remain recorded until the owner confirms the new report.
