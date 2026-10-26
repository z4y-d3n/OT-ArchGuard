# V1.3 capture benchmark measurements

Run date: 2026-10-25. All seven final-source workers completed successfully in
`output/capture-benchmark-final`: six complete reports and one expected resource
rejection. The earlier `output/capture-benchmark` run preceded TCP option
hardening and is superseded; its timings are not compared here. This second run
was justified by that decoder change, rather than repeated to select a result.

Environment: CPython 3.14.5, Windows 11 build 26100, 64-bit AMD64; 11th Gen
Intel Core i5-11400H @ 2.70 GHz, 12 logical processors. Exact Python build:
`3.14.5 (tags/v3.14.5:5607950, May 10 2026, 10:43:50) [MSC v.1944 64 bit (AMD64)]`.

The final installed-candidate regression suite ran concurrently. These are
single measurements with allocation tracing enabled, without CPU isolation,
frequency control, or filesystem-cache control. They are not capacity or
throughput guarantees. Memory means `tracemalloc` peak Python allocations,
**not process RSS**. Timing includes capture analysis, JSON/HTML generation,
and report link auditing; fixture writing and worker startup are excluded.

Reproduction from the source checkout, with an installed development environment:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
.venv\Scripts\python.exe -m benchmarks.capture --output output/capture-benchmark-final
```

The output directory must be fresh. The benchmark generates fictional captures,
opens no sockets, performs no live capture, and runs each workload in a separate
Python process. `benchmark.json` preserves full precision, fixture hashes,
observation digests, output sizes, and complete rejection diagnostics.

## Executed results

| Workload | Input records | Input bytes | Flows / hosts | Seconds | Traced peak bytes | Report bytes | Result |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| repeated-1k | 1,000 | 68,424 | 10 / 7 | 0.312 | 485,330 | 151,971 | Complete |
| repeated-10k | 10,000 | 684,024 | 10 / 7 | 1.786 | 487,027 | 152,193 | Complete |
| repeated-100k | 100,000 | 6,840,024 | 10 / 7 | 17.094 | 487,147 | 152,405 | Complete |
| repeated-250k | 250,000 | 17,100,024 | 10 / 7 | 44.636 | 487,318 | 152,529 | Complete |
| cardinality-1k | 1,000 | 70,024 | 1,000 / 1,001 | 3.775 | 11,231,180 | 6,855,711 | Complete |
| skew-10k | 10,000 | 684,024 | 1,009 / 1,007 | 5.107 | 11,397,420 | 6,966,483 | Complete |
| cardinality-rejection | 10,000 supplied | 700,024 | Not published | 0.869 | 17,206,871 | None | Expected rejection |

Repeated workloads cycle ten fictional packets: initial SYNs, responses,
midstream TCP, UDP, ARP and IPv6. They preserve ten directed flows rather than
inventing sessions. Cardinality workloads introduce distinct benchmark-range
source addresses. The skewed workload introduces a new source on every tenth
record while the remaining records repeat the demonstration traffic.

The adversarial cardinality workload was rejected before a report was published:
`LIMIT_EXCEEDED`, category `resource_limit`,
`capture_aggregation_bytes: maximum 67108864, observed/planned 67111952.`
Its 10,000-record input was not completely analyzed. The conservative allocation
accounting ceiling is separate from traced actual allocations; neither measures
RSS. No truncated aggregate or negative traffic finding was published.

## Reproducible identities

Fixture SHA-256 values, calculated from the files actually measured:

| Workload | Capture SHA-256 |
| --- | --- |
| repeated-1k | `75c94e806f4c7e41686858e5672e8f27d6190aee77346c9d9fc7e8aabfd8bcaa` |
| repeated-10k | `b5c4fe88d1ac21cd7b911b38f567596dc21f22035b558dfd38815b50248af056` |
| repeated-100k | `0aeb62e99812c09f9e3e9229cff9c385a1d2cd362afd019c3b3fc61df57ea6c1` |
| repeated-250k | `2604c4e06866fd65a4d04fdbf5fff1d4566f442198f0ae266cd9fe06cf3430e7` |
| cardinality-1k | `76a0c245073abf558eb63311dfda29aa5abf9f688a6c76bc291576cdf8ca73fb` |
| skew-10k | `4ed5b1d69b219c81903840a109f250dca85fee92f61806981e6c41f06a21b164` |
| cardinality-rejection | `1ea6fcefadfdc020754a6e07a03e8c79efda14e9efa0870408ab07316e742c07` |

Measured checkout: branch `codex/v13-01-capture-foundation`, base commit
`f52c792b683cb499dc7de765b65b5cc897a96854`, with the implementation present as
uncommitted development changes. Exact relevant source identities:

| File | SHA-256 |
| --- | --- |
| `benchmarks/capture.py` | `f51ab9f3a45a9efe0a60dda345b48b995b051ac47abf810d07f32580038406ea` |
| `tools/capture_workloads.py` | `677cfbe0168110e2b85186dd9a3310c44627fba2400b86466903f836649c1588` |
| `src/otarchguard/capture/observations.py` | `b71b01b5bad677194a41dbd727715d37a3fdd5bc36d03acd0370b2c4af9e8346` |

The final source also reproduced all six observation digests and the exact
rejection diagnostic from the superseded run. That separate check established
semantic invariance for these fixtures; the table uses final-source measurements.

## Scope and limits

Only this Windows/Python environment was measured. Linux, macOS, Python 3.12,
whole-process RSS, maximum-size frames, and operational plant traffic were
**NOT MEASURED**. Results are single synthetic observations under concurrent
test load, without a statistical spread or cross-machine comparison. The largest
completed record count was 250,000; default rejection ceilings are not demonstrated
capacity guarantees. Different conversation cardinality, packet sizes, metadata,
storage and sensor visibility can change resource use substantially.
