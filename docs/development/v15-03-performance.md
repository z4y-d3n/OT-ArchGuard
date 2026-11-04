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
175 pages. Rows/page 2, 2 and 7 respectively. Candidate results and interpretation
are recorded in the acceptance/handoff after execution.

Scheduling, filesystem cache, antivirus and concurrent engineering work are
uncontrolled. Small timing differences are not a demonstrated speedup/regression.
Navigation adds bounded linear markup; records/pages/canonical data must remain
equal. Repeated generation must remain byte-identical. No performance optimization
or new resource-limit exemption belongs to this gate.
