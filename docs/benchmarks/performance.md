# Performance attribution and bounded capacity

Run the opt-in profiler from a regular installed environment whose production
module hashes match the reviewed source:

```powershell
python tools/verify_environment.py --output output/profile/environment.json
python -m benchmarks.profile --output output/profile/results.json --capacity
python -m benchmarks.profile --output output/confirmation/results.json --confirmation
python -m benchmarks.profile --output output/workflow/results.json --profiles routine sparse mixed --report-workflow
```

The default deterministic corpus includes minimal, mixed intervals, explicit
boundary devices, blocked policy, absent structure, mixed TCP/UDP, observed-change
comparison, routine, sparse, deny-heavy, dense-policy and interval-heavy declarations.
Inputs and their SHA-256 identities
are written beside the measurements. Select a subset with `--profiles routine
interval-heavy`; at least five measured repetitions are required.

One warm-up precedes untraced wall and process CPU samples. Garbage collection
runs outside each timed batch. A separate fresh operation records peak traced
Python allocation; this is **not process RSS**. Native installed subprocess
measurements include startup, imports, analysis, output capture and process exit.
Child CPU and child allocation are explicitly unavailable in that mode. Parent
CPU time is never substituted. Timer quantization can produce zero CPU samples
for short phases. Compare samples, medians, median absolute deviations and ranges.

The phase microbenchmarks isolate actual functions using prepared inputs. Their
times overlap and must not be added to reconstruct an end-to-end command.
The input-read microbenchmark uses Path.read_bytes on a known bounded synthetic
fixture; native commands retain the production ceiling-plus-one-byte reader.
In-process report workflow allocation includes Typer's argument/output/exit
capture machinery, so it does not isolate analytical object allocation.
YAML loading includes the accepted parser preflights. Rule compilation includes
selector expansion and association preparation; these are not separate pipeline
passes. Canonical serialization includes the public canonicalizer's normalization
boundary. SHA-256 is measured separately. Engine preparation includes partition,
graph and compiled policy. cProfile records all production functions, including
search, witness/replay, frontier and evidence costs, with self and cumulative
times; these contain instrumentation overhead and are not native CLI timings.

Prevalidated traces use a fresh run-local engine for each operation, with and
without optional policy evidence. The harness checks exact intervals, witnesses
and query work agree between those modes. Evidence traverses every declared edge
in the selected finite domain; it can cost much more than finding a witness.
Exposure and comparison include aggregation and independent intent checks.
JSON, HTML and SVG rendering are timed separately from atomic report writing.

The same helpers support focused aggregation attribution using completed results:

```python
import json
from functools import partial

from benchmarks.profile import attribution, measure, workload
from otarchguard.api import validate_bytes
from otarchguard.comparison import compare_architectures
from otarchguard.exposure import exposure_architecture
from otarchguard.flows import observations

snapshot = validate_bytes(workload("routine"))
result = exposure_architecture(snapshot, "scope")
costs = {
    "observations": measure(partial(observations, result.queries), 5, 20),
    "exposure_calls": attribution(partial(exposure_architecture, snapshot, "scope")),
    "comparison_calls": attribution(partial(compare_architectures, snapshot, snapshot, "scope")),
}
print(json.dumps(costs, indent=2))
```

Use a separately validated proposal for observed-difference comparisons. Inspect
flow merge/difference, catalog/field changes and intent aggregation self/cumulative
costs separately from engine preparation/search. Completed summaries/explanations
can likewise be passed to `measure`; they perform no new reachability analysis.
Store such exploratory observations in ignored output directories.

`--report-workflow` separately measures complete in-process `check` with a JSON
report, including reading, evaluation, rendering and writing. It excludes process
and import startup, and observes Python allocation across the whole workflow.
It must not be labeled native subprocess allocation or RSS. Broad dense-policy
parser/allocation profiles can take several minutes; select focused profiles for
routine iteration and keep exploratory evidence in ignored output directories.

`--confirmation` repeats prevalidated analytical controls and native report
operations using the same per-operation warm-up, repetitions and clocks. It
omits independent attribution measurements of unchanged parsing/rendering
functions, and limits non-routine native cases to check/JSON reports. Missing
phases in this mode are unmeasured, not zero. Use full attribution for initial
hotspot discovery and comparable focused confirmation for subsequent changes.

The fixed benchmark remains `python -m benchmarks.run --output
output/benchmark.json`. Its existing 30-second maximum and 512-MiB traced Python
allocation target apply only to its routine exposure pipeline. The profiler adds
no new timing assertion to CI. Deterministic operation counts, independent
analytical oracles and byte comparisons provide portable regression safeguards.

Capacity depends on declared assets/interfaces/edges, rule-edge associations,
services, source/service pairs and exact atoms. The optional finite capacity
sweeps vary these workload dimensions and retain controlled rejections. Model
count limits do not guarantee execution time. Current prospective reservations
remain `3 * atom_queries * (states + edges)` visits and `atom_queries *
associations` predicate checks, together with actual work checks. Diagnostic
evidence adds its complete planned scope. No limit or reservation is relaxed by
preparation reuse. A resource error is not an unreachable result.

Capacity parameters are 1/3/8, except the 1/20/25-edge frontier sweep. Inventory
adds 25 times the parameter in isolated assets/interfaces; edges retain 100 times
the parameter in transport edges plus forwarding, filtering invalid associations;
rules retain 20 times the parameter. Sources/services select that many scenario
entities; associations cap each rule's edge list; atoms retain that many
interval-heavy rules; deny density denies every parameter-th rule. The frontier
uses parallel denied transitions. These families change concrete workload
dimensions and outcomes; their parameters are not fitted scaling coefficients.

Do not run competing measurements concurrently with suites or builds. Use the
same interpreter, input identities, methods and comparable machine load; repeat
key comparisons in a second session. Small differences inside observed variation
are inconclusive. Local Windows observations establish no Linux/macOS speed
guarantee. See [Gate V11-4](../v1.1/gate-v11-4.md) for measured evidence and limits.
