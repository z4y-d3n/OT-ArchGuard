# V15-03 paired rendering measurements

Only complete capture render/audit/publication is measured. Agent E's unchanged
driver `output/v15-03/agent-e/capture_render_benchmark.py` uses one warmup and five
untraced perf_counter trials per case. Analysis/mapping preparation is excluded.
Windows AMD64 / Python 3.12.14; regular before/after installations, identical driver,
fictional capture/JSON and dependencies must match in receipts. Raw individual
measurements, min/max/SD, source/input hashes, page/link/anchor counts and bytes are
in `agent-e/{before,after}/benchmark.json`. No memory/whole-product speedup claim.

Baseline medians: supported 0.2666615 s / 402,392 bytes / 47 pages; limited
0.3391294 s / 452,987 bytes / 53 pages; dense130 2.4412786 s / 3,653,901 bytes /
175 pages. Rows/page 2, 2 and 7 respectively.

## Measured pairs

The initial pair ran during concurrent engineering campaigns and is retained,
including the apparent slowdown. After those heavy campaigns stopped, a second
pair reversed order: candidate first, then the authenticated dev1 installation
created by transition-final. Each block uses the identical driver and one warmup
plus five measurements. No other test suite/benchmark ran during this repeat;
antivirus, OS scheduling and filesystem cache remain uncontrolled. The full-suite
rerun began after both measurement blocks ended.

| Case | Initial before/after median s | Repeat before/after median s | Repeat before min–max s / SD | Repeat after min–max s / SD | Output before/after bytes |
|---|---|---|---|---|---|
| supported | 0.266662 / 0.363625 (+36.4%) | 0.247294 / 0.233129 (-5.7%) | 0.236931–0.266527 / 0.010410 | 0.218147–0.264565 / 0.016704 | 402392 / 405651 (+0.81%) |
| limited | 0.339129 / 0.362709 (+7.0%) | 0.275811 / 0.268877 (-2.5%) | 0.257467–0.287623 / 0.011576 | 0.252087–0.292182 / 0.012931 | 452987 / 456758 (+0.83%) |
| dense130 | 2.441279 / 2.648442 (+8.5%) | 2.222209 / 2.144854 (-3.5%) | 2.182030–2.247978 / 0.024310 | 2.122052–2.229458 / 0.036712 | 3653901 / 3667134 (+0.36%) |

Both series preserve exact input/canonical JSON hashes, page counts 47/53/175,
flow counts 10/12/130 and deterministic repeated bytes. Dependency names/versions
match exactly apart from the intended distribution version. All 97 runtime hashes
are recorded, with only the two authorized changes. Driver SHA-256:
`0d4697c92655d75d7ac8fcbe7500c2053c64a12ff834ef9e120bff90e1800e22`.
Repeat receipts: `agent-e/repeat-{before,after}/benchmark.json`; original series:
`agent-e/{before,after}/benchmark.json`. Runtime: Windows 11 build 26100 AMD64,
Python 3.12.14, regular `.venv-v153-final` and `transition-final/dev1-env`.

The initial slowdown was not reproduced in the quieter reversed-order pair.
These small samples do not establish a speedup or universal absence of regression.
They show no repeatable rendering regression in these selected workloads. Added
navigation increases bytes by under 1%, preserves pages/records and stays within
the original limits. No memory or end-to-end performance claim is made.
Independent Agent E recalculated all statistics and rehashed the actual files
of all 72 warmup/trial sites; their recorded inventories and deterministic
repetitions agree. See `agent-e/final-review.md` for that separate audit.

Scheduling, filesystem cache, antivirus and concurrent engineering work are
uncontrolled. Small timing differences are not a demonstrated speedup/regression.
Navigation adds bounded linear markup; records/pages/canonical data must remain
equal. Repeated generation must remain byte-identical. No performance optimization
or new resource-limit exemption belongs to this gate.
