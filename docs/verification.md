# Version 1.0.1 verification

Local verification uses regular installed wheels on Windows with CPython 3.12.14
and 3.14.5. Python 3.12 is the declared minimum. These results describe the tested
environments and finite fixtures; they do not establish compatibility with every
interpreter, operating system or deployed network.

| Check | Python 3.12.14 | Python 3.14.5 |
| --- | --- | --- |
| Full pytest suite | 608 passed | 608 passed |
| Ruff lint and formatting | Passed | Passed |
| Strict mypy | Passed | Passed |
| Dependency consistency | Passed | Passed |
| Native CLI version/help | Passed | Passed |
| Synthetic example commands | 27 passed | 27 passed |

Tests and example child processes run with the opt-in Python network audit hook.
It rejects Python network operations; it does not simulate a physical air gap.
The 27 generated JSON/HTML reports, including embedded SVG, are byte-identical
between the tested interpreters.

Distribution verification checks the explicit file manifest, archive member safety,
metadata, entry points, mandatory notices and wheel RECORD digests. Packaged
source, tests and documents match the source tree. A wheel rebuilt from the source
distribution has the same member contents as the directly built wheel.
See [release checks](release-checklist.md) and [testing strategy](testing-strategy.md).

## Measured routine workload

The fixed routine workload contains 200 assets, 400 interfaces, 1,200 edges,
200 policy rules, 25 services and 10 origins. Each profile uses one warm-up,
five untraced timings and a separate operation for traced Python allocation peak.

| Measurement | Python 3.12.14 | Python 3.14.5 |
| --- | --- | --- |
| Maximum routine exposure time | 1.166017 s | 1.052099 s |
| Peak traced Python allocations | 7,392,801 bytes | 7,599,713 bytes |

The 30 s / 512 MiB target applies to this routine workload. Traced allocation peak
is not process RSS, and resource ceilings are rejection limits, not capacity
promises. Sparse, deny-heavy, dense-policy and interval-heavy profiles are also
exercised by the benchmark runner. See [benchmark reproduction](benchmarks/README.md).

## Verification boundaries

Python 3.13, other operating systems, installation on a fresh OS, physical air-gap
operation and broader browser/print coverage have not been verified. Static markup
and image checks do not establish browser rendering behavior. Hosted CI results
are not part of these local results.

The escaped unpaired-Unicode-surrogate issue remains: the API can raise
UnicodeEncodeError and the CLI returns a generic exit-2 execution diagnostic.
Existing output is preserved. See [limitations](limitations.md).
