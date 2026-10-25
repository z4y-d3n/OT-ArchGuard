# Fictional PCAP evidence tutorial

All addresses and traffic are generated, not captured from real equipment.
`plant.pcap` and `plant.pcapng` contain equivalent ten-record teaching traffic.
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

To regenerate the exact fixture bytes, use `tools.capture_workloads.write_pcap`,
`write_pcapng` and `plant_model`; no network or packet library is involved.
