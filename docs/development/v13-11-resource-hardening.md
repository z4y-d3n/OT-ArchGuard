# V13-11 — Resource hardening and measured workloads

Date: 2026-10-25. Status: **local resource verification completed within the
documented scope; cross-platform measurements remain NOT RUN**. Historical
measurements and gates are preserved. These measurements are observations, not
capacity, throughput, RSS-isolation or operational-plant guarantees.

## Confirmed correction R-01

**Medium — late native evidence rejection, corrected.** Before this correction,
`capture/reconciliation.py` called `ReachabilityEngine.evaluate()` to construct
all interval witnesses, then applied `_evidence_allocation` before `asdict`.
This protected dictionary expansion but did not reject excessive retained native
results as they accumulated. The native work ceilings made the workload finite;
the defect was delayed enforcement of the capture evidence budget, not unbounded
parsing or a demonstrated OS memory escape.

Independent bounded reproduction:

- 94-byte synthetic capture; 65,508-byte validated YAML model.
- 30 intermediate boundary devices, 62 interfaces, 61 explicit edges and 250
  additional single-port rules; 500 native port intervals and 30,500 witness
  steps. Native work stayed within its ceiling: 92,000 visits and 155,500 rule
  predicate checks.
- At a deliberately small 65,536-byte evidence-accounting ceiling, the complete
  query already occupied 8,766,437 current traced bytes, with peak 8,775,939 bytes,
  before rejection of a conservative 129,857,024-byte evidence charge.

The narrow correction adds an optional keyword-only `interval_observer` to
`ReachabilityEngine.evaluate`, defaulting to `None`. The capture adapter reserves
the query envelope and charges each exact native interval before retaining it;
an over-budget interval aborts before evaluating the next atom. Search, policy,
interval partitioning, witnesses and diagnostics retain their existing semantics.
The observer does not replace native results.

The same probe after correction rejected the first interval at an accounting
charge of 260,736 bytes; traced peak was 453,498 bytes. These are single traces of
the comparison operation, excluding fixture writing and model loading. They are
not whole-process RSS measurements. The probe and raw before/after results are
`output/v13-audit/native-transient-probe.py` and
`output/v13-audit/native-transient-comparison.json`.

The new regression
`tests/test_capture_independent_resources.py::test_capture_native_budget_stops_before_retaining_all_intervals`
demonstrably failed against the earlier installed candidate: all three intervals
were evaluated instead of one. It passes against corrected source, evaluating
one interval before the resource error. No partial comparison is returned.

One native interval remains in flight before its charge can be measured. Native
graph/policy creation and model loading also precede the interval observer;
their existing entity/work ceilings remain separate from capture evidence
accounting. This change provides neither an enforced RSS cap nor OS isolation.

## Measurement method and environment

The nine final workers ran through `benchmarks.capture` in separate processes.
`output/v13-audit/final-benchmarks/benchmark.json` retains full-precision timings,
actual fixture SHA-256, observation digests, record/interface counts, output bytes
and rejection diagnostics. Eight workers completed; the adversarial cardinality
worker rejected as expected. Its supplied record count is not a parsed count.
The metadata workload correctly records zero packet records and 256 sections.

Environment: Windows 11 build 26100, CPython 3.14.5, MSC v.1944 64-bit AMD64;
Intel Family 6 Model 141 Stepping 1, 12 logical processors. Exact Python build:
`3.14.5 (tags/v3.14.5:5607950, May 10 2026, 10:43:50) [MSC v.1944 64 bit (AMD64)]`.
The full installed regression suite ran concurrently. There was no CPU isolation,
frequency control, filesystem-cache control or statistical repetition.

- Elapsed time includes capture analysis, JSON/HTML generation and site link
  audit; it excludes worker startup and fixture writing. Tracing was enabled.
- `tracemalloc` peak measures traced Python allocations over that timed scope.
- Process resident peak is the worker lifetime Windows
  `GetProcessMemoryInfo().PeakWorkingSetSize`, including startup, fixture writing
  and instrumentation. It is not a workload delta or interchangeable with traced
  allocations. The implementation uses Linux `ru_maxrss * 1024` and macOS
  `ru_maxrss` bytes on those platforms; those branches were not executed here.
- Each worker has its own lifetime high-water mark, so earlier workloads do not
  contaminate another worker's resident peak.
- These final workers used the regular verified wheel installation and active
  socket/DNS-denial harness. The earlier source-checkout exploratory measurement
  under `output/v13-audit/benchmarks/` is preserved separately. It preceded final
  source identity closure (one decoder comment changed during that run), so the
  final installed measurement supersedes it; no executable decoder logic changed
  between the two measurements. This is not statistical repetition or a selected
  best-of comparison.

Reproduction requires a fresh output directory:

```powershell
$env:PYTHONPATH = (Resolve-Path tools/offline).Path
$env:OTARCHGUARD_OFFLINE_CHECK = '1'
.\output\v13-audit\wheel-env\Scripts\python.exe -m benchmarks.capture --output output/v13-audit/final-benchmarks
```

## Executed results

All memory and output columns below are bytes. Times are rounded only in this
table; raw JSON retains full precision.

| Workload | Supplied packet records / sections | Input bytes | Flows / hosts | Seconds | Traced peak | Process resident peak | Report bytes | Result |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| repeated-1k | 1,000 / 1 | 68,424 | 10 / 7 | 0.302 | 487,836 | 38,805,504 | 158,738 | Complete |
| repeated-10k | 10,000 / 1 | 684,024 | 10 / 7 | 1.702 | 489,376 | 38,883,328 | 158,970 | Complete |
| repeated-100k | 100,000 / 1 | 6,840,024 | 10 / 7 | 15.640 | 489,552 | 39,235,584 | 159,192 | Complete |
| repeated-250k | 250,000 / 1 | 17,100,024 | 10 / 7 | 38.928 | 489,723 | 39,018,496 | 159,316 | Complete |
| cardinality-1k | 1,000 / 1 | 70,024 | 1,000 / 1,001 | 3.431 | 11,231,180 | 60,608,512 | 6,855,711 | Complete |
| skew-10k | 10,000 / 1 | 684,024 | 1,009 / 1,007 | 4.948 | 11,397,420 | 60,801,024 | 6,966,483 | Complete |
| cardinality-rejection | 10,000 supplied / 1 | 700,024 | Not published | 0.836 | 17,206,871 | 76,103,680 | None | Expected rejection |
| maxframe-64 | 64 / 1 | 16,778,264 | 1 / 0 | 0.113 | 667,679 | 39,202,816 | 32,154 | Complete |
| metadata-sections-256 | 0 / 256 | 16,789,504 | 0 / 0 | 0.131 | 539,365 | 39,137,280 | 118,325 | Complete |

The maximum-frame workload contains 64 captures of 262,144 bytes each. The frames
carry an unsupported Ethernet type, so the measured result exercises bounded
reading/aggregation without fabricating transport observations. The metadata
workload has one 64-KiB framed option area in each section's interface block and
no packet blocks. It measures processing/discarding metadata, not packet decoding.

The cardinality worker rejected with `LIMIT_EXCEEDED`, category `resource_limit`:
`capture_aggregation_bytes: maximum 67108864, observed/planned 67111952.`
No `cardinality-rejection-site` directory was published. No truncated aggregate
was converted into a successful report or absence assessment.

Benchmark source SHA-256:

| File | SHA-256 |
|---|---|
| `benchmarks/capture.py` | `22634de5e627747a92b2e54827607b015b5a9d265e35211e644f1702c6e1ac25` |
| `capture/observations.py` | `8489541dafa887ecccde3dd0aa0d00fc84674516206f81e887e56f9bf548e8e6` |
| `capture/explorer.py` | `d3a797c6148f6f11300da4dff11dda54c5f98273db89c2b73b7c65cdff51ba92` |

These files remained unchanged during the benchmark workers. The benchmark does
not call capture reconciliation, whose incremental correction is independently
covered above. Final commit/source identities are recorded by V13-12/V13-13.

## Independent boundary tests and allocation assessment

`tests/test_capture_independent_resources.py`: **8 passed, 0 failed, 0 skipped**
in 0.60 seconds against corrected source; Ruff check/format and strict mypy pass.
Two cases independently verify that both boundary writers produce deterministic
bytes and observations, with correct metadata/packet counts and valid offline
sites. Five CLI cases lower packet-size, packet-count, interface-count,
metadata-size and block-size ceilings; all reject with exit 2, preserve capture
and pre-existing data, and leave neither a final report nor a staging directory.
The eighth case checks incremental native rejection.

```powershell
$env:PYTHONPATH = 'src;.'
$env:MYPYPATH = 'src'
.\.venv\Scripts\python.exe -m pytest tests/test_capture_independent_resources.py -q --basetemp .pytest_tmp/independent-resources-02 --tb=short
.\.venv\Scripts\python.exe -m mypy --strict tests/test_capture_independent_resources.py
.\.venv\Scripts\python.exe -m ruff check tests/test_capture_independent_resources.py
.\.venv\Scripts\python.exe -m ruff format --check tests/test_capture_independent_resources.py
```

| Stage | Enforced accounting and residual allocation scope |
|---|---|
| Capture reading/decoding | File, packet, block, option, record/interface and IPv6-extension limits apply. Input is streamed; bounded packet/block bytes and option slices can coexist transiently. |
| Host/flow/conversation aggregation | Separate cardinality ceilings plus conservative retained-allocation charges; sampled references disclose omissions. A large record count alone does not imply a large retained flow count. |
| Mapping/validation | Exact host/interface proposals; host-by-interface work check; bounded JSON bytes/depth/nodes and review text. No topology or model mutation. |
| Native queries | Pair count, port-atom, state/edge and rule-work limits; cumulative incremental evidence accounting; one in-flight native interval and native graph/policy storage remain outside the evidence charge. |
| Cached results/serialization | One native query conversion per source/service pair; exact selected port intervals; cumulative repeated-result output charge. Existing adversarial tests cover shared queries and repeated output amplification. |
| HTML/JSON generation | Total bytes, file count and per-HTML-page caps; staged complete report, audited links, fresh-destination publication. JSON/string construction can allocate transient buffers before byte rejection; byte limits are not RSS isolation. |

Existing shared-result and amplification tests in `test_capture_reconciliation.py`
and the 43-case independent semantic corpus are part of the final regression
suite; their counts are not added to its full-suite total as independent runs.

Unmeasured: Linux/macOS RSS implementations, Python 3.12, maximum file/record
ceilings as successful capacity, real plant traffic, statistically stable
performance, and adversarial filesystem isolation. For untrusted co-tenant
workloads, OS-level process/memory isolation remains an external deployment
control. No sandbox, physical air gap or universal memory bound is claimed.
