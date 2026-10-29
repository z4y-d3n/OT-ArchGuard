# V14-01 finite enrichment measurements

Executed on Windows 11 AMD64 / Python 3.14.5 using
`python -m benchmarks.protocols --output output/NEW_DIRECTORY`.
Inputs are independently authored fictional frames in `tools/protocol_workloads.py`.
Each measurement includes bounded capture scanning, enrichment construction and
pretty serialization, with tracemalloc enabled. Validation runs after timing.

| Workload | Input bytes | Retained records | Pretty JSON bytes | Seconds | Peak Python allocations | Process peak RSS |
|---|---:|---:|---:|---:|---:|---:|
| Modbus 1,000 | 82,024 | 1,000 | 1,189,652 | 0.529 | 3,980,046 | 48,513,024 |
| EtherNet/IP 1,000 | 98,024 | 1,000 | 1,303,675 | 0.524 | 4,102,765 | 49,467,392 |
| S7comm 1,000 | 95,024 | 1,000 | 1,237,665 | 0.559 | 4,026,264 | 49,467,392 |
| IEC104 1,000 | 76,024 | 1,000 | 1,121,637 | 0.453 | 3,737,064 | 49,569,792 |
| OPC UA 1,000 | 98,024 | 1,000 | 1,218,676 | 0.574 | 3,975,144 | 50,331,648 |
| DNP3 1,000 | 80,024 | 1,000 | 1,397,642 | 0.580 | 4,425,136 | 50,331,648 |
| DCP 1,000 | 46,024 | 1,000 | 1,048,548 | 0.326 | 3,440,516 | 50,331,648 |
| Mixed 7 | 599 | 7 | 10,587 | 0.009 | 147,125 | 50,331,648 |
| Mixed 700 | 57,524 | 700 | 852,491 | 0.322 | 2,761,463 | 50,331,648 |
| Mixed 7,000 | 575,024 | 7,000 | 8,519,687 | 3.106 | 27,794,655 | 84,889,600 |
| Mixed 21,000 supplied | 1,725,024 | Fatal rejection | No artifact | 4.953 | 29,474,408 | 109,481,984 |
| Bad CRC 1,000 | 80,024 | 1,000 malformed | 1,200,633 | 0.452 | 3,791,373 | 109,481,984 |
| View 16,385 bytes | 16,479 | 1 unsupported | 3,037 | 0.024 | 185,513 | 109,481,984 |
| Unsupported outer 1,000 | 62,024 | 0; aggregate skip | 1,888 | 0.051 | 138,770 | 109,481,984 |

The mixed 21,000 workload reaches the **metadata-byte** ceiling first
(`enrichment_metadata_bytes`, planned/observed 16,777,694 vs 16,777,216).
It is not a successful 20,000-record artifact or a demonstrated record-count
ceiling. Independent tests separately lower the record limit to prove rejection.
The view-byte case emits an explicit unsupported record. Per-packet iteration
limits bound coalesced-message records; aggregate exhaustion is fatal.

Output scales with per-record packet provenance and limitations, not just input
payload size. At 700/7,000 mixed packets the retained JSON grows approximately
linearly, around 1.22 KB per record. These are different workloads from V14-00's
roughly 3.43 MB/315 KB example; no speed or compression improvement is claimed.

RSS is the process lifetime high-water mark, includes interpreter/imports and
earlier workloads, and is not an isolated per-operation delta. Python allocation
peaks are a different measure. These single finite traced observations establish
neither throughput guarantees nor hostile-input worst-case timing bounds.

## Summary and evidence tradeoff

Schema 1 retains canonical aggregate counters and detailed bounded records with
exact packet references. Suppressed outer traffic has bounded reason counters;
unsupported candidate frames retain explicit evidence within the same ceilings.
Dropping record provenance would change reproducibility and artifact meaning.
No compact-output redesign is made in this milestone. A future additive summary
artifact must have its own explicit version, source-artifact digest and documented
bounded-example policy; it must not replace detailed schema-1 evidence silently.
