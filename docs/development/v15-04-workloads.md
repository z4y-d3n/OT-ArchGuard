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

## Exact retained workload and environment identities

Driver SHA-256: `7128d50086ee93623f78cb12a87afb69720b5dc6e31bf79daf122f327d5d412e`. Constructor SHA-256: `bc3a4d583335fb799a3a952ae81b8f030879ce82d05299babb88373845e48439`.
Windows 11 build 26100 AMD64 / CPython 3.12.14; Intel64 Family 6 Model 141
Stepping 1, 12 logical CPUs. Physical RAM 33,980,125,184 bytes, available at first
baseline start 12,236,644,352 bytes. Relevant identical dependencies: PyYAML6.0.3,
pydantic2.14.1/core2.50.1, typer0.27.3; pytest9.1.1, Ruff0.17.1, mypy1.20.2,
setuptools84.2.1, pip26.2.2. Complete 27-distribution inventory is in each receipt;
only otarchguard changes dev2→dev3.

| Case | Raw YAML SHA-256 | Provenance SHA-256 |
|---|---|---|
| small | `0306ae1b26506b015b7a523a19443cfcc80f6bf1f4228d7a3b40d29f0b2d4560` | `7e93986a5510be38ebd0ab1276a82aef41f75e0218c3e821a0cbec7e3332549b` |
| medium | `709388dce7524d9d87cbb4a3aacd0dbd3bc518042c5c39a355657ef3edebfc5a` | `625cf970c2d9154c44d4c7920c78a3b1fc2c5fecd55677d40ba40688f58f56f7` |
| larger | `5eadc6419520b36e618ac7c184f50009f40a218efdd5316320f27bc51745ada8` | `f391cb718824cbc85e892dee13b4411a21435a21c4a56d1188798d83c7aa43ab` |
| adversarial | `709388dce7524d9d87cbb4a3aacd0dbd3bc518042c5c39a355657ef3edebfc5a` | `d18ecc4fd8d4507cc6861503c4e28d44ea8c9abe2b13a0b1a25f5d7c9bdecc73` |

58 measured generations + 18 excluded warmups produced the 76 physically audited
sites. Normal latency uses six samples/runtime/case; larger additionally has five
confirmation samples/runtime. Original noisy runs remain. Git HEAD/tree in a
receipt describe the driver checkout; the measured runtime is identified by its
separate regular-installed 97-module inventory. The policy correction at3410924
changes no runtime byte, driver or constructor from the measured implementation.
Full per-file inputs/output SHA mappings remain in raw receipts, not as claimed
self-authorizing source approval. `final/facts.json` carries compact inventory
digests defined as SHA256 of sorted compact JSON filename→filehash maps.
