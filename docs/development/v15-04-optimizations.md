# V15-04 — Optimization decisions

## Pre-implementation selection

| Rank/ID | Subsystem/workload | Evidence and root cause | Decision |
|---|---|---|---|
| 1 / T1 | Architecture, existing small/medium/larger | `check_text`: 585,785 calls and 10,377,420 generator iterations in larger; 7.543 s cumulative of 90.261 s instrumented. Python checks the same fixed character ranges on each call. | Experiment with one compiled equivalent character-class search in `explorer_data.py`; keep length check first and identical failure. |
| 2 / A1 | Architecture emitted-site audit | Larger 45.172 s instrumented, including actual reads and HTMLParser. | Retain complete actual-byte verification. No demonstrated safe redundant work. |
| 3 / C1 | SiteWriter compaction | Larger 3.882 s instrumented; split 0.061 s, links 0.225 s. | No rewrite; no measured quadratic traversal. |
| 4 / T2 | Shared BIDI escaping | 2.496 s instrumented; five-module historical renderer identity consequence. | Defer: separate source revision for a small unproven benefit. |
| 5 / H1 | Historical replay/publication | Invocation-private validation reuse already exists; staged and emitted audits have distinct integrity roles. | No removal or cross-run cache. |

Recorded before production changes: 15% remains the aspirational gate target,
but the profile provides no defensible low-risk candidate of that size. T1 is
exceptionally small (one fixed regex, no cache or new trust boundary). Accept T1
only if balanced six-trial/runtime installed comparisons demonstrate at least
3% median improvement in larger generation, exact output bytes across all three
sizes and hostile controls, no reproducible material control/memory regression,
and exhaustive Unicode/error equivalence. A smaller result requires rejection
or further separately documented evidence; profiler percentages are not latency
predictions. Predicted normal improvement is only 2–5% (hypothesis).

Independent oracle: immutable merged V15-03 implementation plus recorded before
site inventories, not candidate-generated expected values. Preserve resource
limit precedence and all diagnostics. No renderer-bound source changes selected;
historical renderer version/digest must stay exact. The dev3 distribution still
changes analytical producer identity and must never inherit dev2 approvals.

Rollback: restore only the local T1/version candidate edits from the fixed
predecessor bytes, retaining failed experiments and measurements. Never reset
unrelated work or change remote history. Final decision and measurements are
recorded in the acceptance record and Spanish handoff.

## Final T1 decision

ACCEPTED for this local milestone. Balanced six-sample larger medians33.318590→
31.271646s (−6.1435%); candidate-first five-sample confirmation34.703024→32.584346s
(−6.1052%). Both exceed the recorded3% exception for a tiny low-risk change;
15% remained aspirational. All5 confirmation candidate times are below all5
baseline times. The43.908725s original trial is retained; no timing was removed.

Original medians small1.174949→1.177159s (+.1881%), medium9.978064→9.235999s,
hostile10.665843→9.279541s. Exact byte inventories across76sites, exhaustive
Unicode/error oracles and current/historical suites pass. Python allocation peak
174062151→174062312bytes; fresh process lifetime RSS229732352→228876288bytes,
with no isolated-RSS or memory-speedup claim. No second target was implemented.

The first full native source comparison failed because its empty source-exception
set contradicted the declared helper delta. This was a verifier omission, not an
accepted analytical difference. The corrected new policy pins both33module maps
and permits only the fixed helper hash; all123 analytical artifacts remain exact.
Seven source/artifact forgery regressions plus independent mutations pass, and
the entire transition rerun passed. Prior policies/oracles remain immutable.
Raw failed attempt and initial archives are retained separately from accepted
`verified-retry` and final documentation closure packages.
