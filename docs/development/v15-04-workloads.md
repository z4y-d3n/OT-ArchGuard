# V15-04 — Reproduction protocol

Reuse `tools.synthetic_explorer.explorer_workload(root, assets, interfaces,
connectors, sources, hostile=False)`: small `(20,30,40,3)`, medium
`(150,200,250,5)`, larger `(500,600,750,6)`. Hostile uses medium with `hostile=True`.
These finite fictional sizes are measured points, not maximum capacity claims.

`benchmarks.explorer_performance` is a narrow driver over that constructor, not
a replacement benchmark framework. It records exact YAML/sidecar and full input
inventory hashes, constructor/driver hashes, regular installed module hashes,
distribution/native/schema versions, interpreter/platform/CPU/available memory,
dependencies, Git HEAD/tree and dirty status, command, UTC start/end, separate
warmup, individual wall samples and phase timings, median/MAD/min/max, output
inventory/page/link/byte statistics and input immutability. A supplied installation
receipt establishes comparison parity; it is not source authorization.

Prepare the inputs once with the authenticated dev2 installation:

```powershell
.venv-v153-final/Scripts/python.exe -m benchmarks.explorer_performance --inputs output/v15-04/benchmarks/inputs --output output/v15-04/before/block-1 --runtime-receipt output/v15-04/baseline/environment.json --prepare --runs 3 --cases small medium larger adversarial
```

Use the identical driver and input directory with the regular candidate, omit
`--prepare`, pass its `tools/verify_environment.py` receipt, then use fresh
`after/block-1`, `after/block-2`, `before/block-2` destinations with three trials
each. Order is B3→A3→A3→B3, one excluded warmup per case per block. Compare ALL
output file SHA-256 mappings across both runtimes and every repeat. Baseline
installed bytes stay fixed while local tooling changes are recorded honestly.

Measure allocation separately with `--mode allocation --cases larger`; measure
OS process lifetime peak with `--mode rss --cases larger` in another fresh
interpreter. Neither instrumented duration is normal latency. RSS includes imports
and operation/setup; child memory is unmeasured. Do not sum nested phase times.
Do not run builds/suites/profiles concurrently with latency campaigns. OS cache,
antivirus, scheduling and thermals remain uncontrolled; inspect each block and
dispersion before treating small differences as meaningful.

CPU attribution uses the raw specialist drivers under
`output/v15-04/profiles/{architecture,historical}/`. Existing historical producer
scales 1/64/512 are `tools.drift_walkthrough.prepare(..., variations=False)`;
source-bound inputs from one distribution cannot be silently replayed by another.
Capture controls reuse the unchanged driver
`output/v15-03/agent-e/capture_render_benchmark.py` with one warmup and five trials
for supported/limited/dense130; exact evidence/input/output identities are retained.

All raw measurements live in ignored `output/v15-04/`; durable summarized
measurements and disposition belong in acceptance/handoff records. No confidential
capture, large generated report, local environment or binary profile is packaged.
