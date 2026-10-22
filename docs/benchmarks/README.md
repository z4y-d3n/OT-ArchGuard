# Benchmark reproduction

Run from a verified regular installed environment:

~~~powershell
.\.venv\Scripts\python.exe -m benchmarks.run --output output/benchmark.json
~~~

Profiles: routine, sparse, deny-heavy, dense-policy and interval-heavy. One warm-up
precedes at least five untraced timings; a separate fresh operation records traced
Python allocation peak, not RSS. Routine comparison uses identical bytes. Reporting
uses existing evidence and excludes file output. Generation is outside the routine
exposure target. Rejections retain explicit limit diagnostics, not unreachable.

The 30 s / 512 MiB target applies to the documented routine workload only.
See [verification results](../verification.md); no universal capacity claim.
