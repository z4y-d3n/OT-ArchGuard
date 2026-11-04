# V15-04 — Local acceptance

**READY_FOR_OWNER_REVIEW**. Scoped T1 optimization and local correctness,
compatibility, package and independent audit requirements pass. Owner review
and the exact final SHA's six-job hosted matrix remain pending. No remote write,
PR, merge, tag or release was performed; stable v1.4.0 is untouched.

## Source and version identity

| Identity | Value |
|---|---|
| Approved merged V15-03 | `18cb7e84ef16871daf857af48e3cd003ec8200ba` |
| Baseline tree | `0b512bce31da2b0d9b10160b1a8cdc13ec23fab4` |
| Corrected tested implementation | `3410924d80a2373bdbe75385c07a84a51441b878` |
| Tested implementation tree | `b48ca8cc911195a6188681c8b86223712903d754` |
| Earlier retained implementation experiment | `8657b7a9242ec5964e3e255ebe88df704bb188eb` |
| Final documentation HEAD/tree/archive hashes | External `output/v15-04/final/freeze.json` |
| Distribution / native / YAML schema | `1.5.0.dev3` / `1.3.0` / `1` |
| Local branch | `codex/v15-04-performance-scalability` |

Runtime is identical between the first experiment, corrected policy commit and
documentation closure: 97 physical source hashes, only `__init__.py` and
`explorer_data.py` differ from dev2. The unchanged five-source renderer remains
`1.5.0.dev1-historical-explorer.1`, digest
`442d13378cd61586664e19f51ea6834537b0155c07e48ff5a6173628c5d6ca6b`.
The predecessor's [post-merge CI run](https://github.com/z4y-d3n/OT-ArchGuard/actions/runs/41841310683)
passed all six jobs; that is prior-gate evidence, not candidate hosted approval.

## Requirement to evidence

| Requirement | Actual result | Local evidence under `output/v15-04/` |
|---|---|---|
| Proven bottleneck | 585,785 `check_text` calls / 10,377,420 generator iterations; no quadratic compaction evidence | `profiles/architecture/` pstats, function counts, phase summary |
| Equivalent latency inputs/installations | Same driver/constructor, input inventories, interpreter, 26 non-app dependencies; regular installations | `{before,after}/{block-1,block-2,confirmation}/receipt.json` |
| Worthwhile bounded benefit | Original balanced six-trial median 33.318590→31.271646 s, −6.1435%; independent five-trial confirmation 34.703024→32.584346 s, −6.1052% | `benchmarks/{independent-review,confirmation-review,phase-review}.json` |
| No output omission/change | 76 actual sites / 96,624 files / 1,631,323,668 bytes independently rehashed; zero differences | Agent D physical receipts |
| Memory | Python peak 174,062,151→174,062,312 bytes; fresh process lifetime PeakWorkingSet 229,732,352→228,876,288 bytes | `memory/{allocation,rss}-{before,after}/receipt.json`, `memory/summary.json` |
| Capture controls/navigation | 36 sites / 3,444 files / 3,300 HTML / 123,372 links; canonical bytes, IDs and flow context exact | `profiles/capture/{control-summary,physical-review}.json` |
| Native immutable oracle | 123 non-manifest artifacts exact across 45 cases; both 33-module captured maps pinned; only reviewed helper source exception | `transition/full-retry/transition.json`, `audit/full-transition-independent.json` |
| Current suite, wheel | 4,498 PASS + one sandbox junction skip; zero failure/error | `regressions/wheel-retry.xml` |
| Current suite, sdist | Same 4,499 unique node IDs; 4,498 PASS + same skip; zero failure/error | `regressions/sdist.xml` |
| Real Windows junction rejection | The exact skipped node passes outside sandbox in both installations | `regressions/junction-{wheel,sdist}-retry.xml` |
| Historical exact-version suites | 24 dev2 PASS + 30 dev1 PASS, no skips; unchanged archived policies/contexts | `transition/full-retry/{historical-tests.xml,v15-03/historical-tests.xml}` |
| Producer boundary | Portable old bundle explicitly not analytical replay; dev3 rejects with EVIDENCE_REVISION; original runtime recovers same bundle; 71 historical files unchanged | Full transition and independent F receipt |
| Source/inventory/adversarial negatives | Unicode exhaustive immutable AST oracle, mixed/long/error precedence; missing/extra/forged source, pre-import and poisoned-bytecode negatives | `tests/test_v15_04_{text,transition}.py`, full JUnit |
| Independent meaningful mutation | `search`→`match` accepts interior controls, but self-rehashed PASS source receipt rejected; three native provenance forgeries also rejected | `audit/independent-mutation-verified/`, `audit/native-boundary-mutations/` |
| Lint / formatting / strict types | Ruff PASS; 444 files formatted; mypy PASS on 278 source files | `regressions/fix-{ruff,format,mypy}.log` |
| Dependencies / offline operation | pip check PASS; source/console identity checks; all serial checks carry offline guard | `regressions/dependencies.log`, `final/commands/receipt.json` |
| Wheel/sdist audited and installed | 104 wheel / 559 sdist members, 551 public files, 97 exact installed modules in both environments | `packages/verified-retry/`, independent package receipts |
| Frozen consumers / examples / original corpus | supported/limited consumers, documented examples, original protocol and V145 corpus all exit 0 | Serial command stdout/stderr receipts |
| Nine walkthroughs | project, explorer, document, quality, capture, evidence, evidence_history, drift, historical_explorer all exit 0 | `walkthroughs/`, serial receipts |
| Existing benchmark completion/resource rejection | Native five = three completed + two correct work-limit rejections; quality three deterministic sizes; capture nine = eight complete + one correct aggregation rejection | `benchmarks/{native,quality}.json`, `benchmarks/capture/benchmark.json` |
| Independent skeptical audit | No open P0/P1 implementation finding; final document/archive review separately retained | `audit/` final F record and closure receipts |

There are **4,499 unique current test cases**, not the sum of repeats. Two full
suites plus the two passing junction repetitions give 9,000 executions including
two sandbox skips. Earlier focus and 4,492-case wheel runs are preserved repeats;
54 historical policy tests are reported in their separate versioned contexts.

## Findings and disposition

| Finding/experiment | Disposition |
|---|---|
| Initial candidate timing direction reversed, including 43.908725 s | All samples retained; quiet candidate-first confirmation required and passed; no selection/removal of slow trials |
| Initial V15-04 native allowlist omitted the declared top-level helper change | First full attempt failed closed and is retained in `transition/full/`; exact source-map binding plus literal helper exception and seven regressions added; full corrected `full-retry` passed |
| Forged allowed-helper/baseline/init native manifests | Independent mutation accepted by generic comparator alone but rejected by exact pinned maps; no source authority from self-hashed evidence |
| Benchmark output parent missing / multi-case RSS contamination | Fixed before measurement; RSS requires one case per fresh process |
| Venv bootstrap / initial log redirect / target-only mypy setup attempts | Retained in baseline setup notes; corrected offline installation, directories and full strict source scope; no failed setup counted as passing tests |
| Windows sandbox junction skip | No assertion weakened; exact real junction test passed in both environments outside sandbox with workspace-contained paths |
| Auditor slots-dataclass harness setup error | Failed raw setup retained; corrected asdict harness rerun in a fresh isolated directory; no production/oracle edits |

## Performance verdict and limits

The pre-implementation 15% aspiration had no low-risk profiled candidate. The
exceptionally small T1 experiment had an explicitly recorded ≥3% local threshold;
both campaigns show approximately 6.1% median benefit. The pooled eleven-trial
8.1995% figure is secondary descriptive context, not the headline or a replacement
for either campaign. Original MAD larger 0.160888→0.851891 s; confirmation MAD
0.178273→1.053446 s. File cache, antivirus, thermals and OS scheduling are not fully
controlled. No universal or industrial capacity claim follows. Small control
median +0.1881% is within dispersion; no sustained material latency/output/memory
regression remains in measured controls.

Historical generation/replay/render/audit/portable/source-bundle components were
characterized independently with three untraced trials and a warmup at fictional
producer scale 512; no cross-producer historical speedup is claimed. Necessary
audits/source reads/final freshness were retained. Compaction, BIDI and the broader
import text helper were not optimized. No limits or protocol scope changed.

## Package/source freeze and owner tasks

The tested implementation packages are from `3410924`:
wheel SHA-256 `6fc57e88217adb5b4824e60cee62e7c341ad529a60abdb23c0d983c9eadf3fda`;
sdist SHA-256 `3f86107db81ddf0a30dc68f77f74a805a09f361767d90b4c3feeacc506907aae`.
They are retained separately from later documentation closure archives. Final
archives are audited against their own committed public-source tree and regularly
installed; identical 97-module runtime hashes bind them to the completed functional
suites without falsely attributing old archive bytes to new Markdown. Final
SHA/tree, archive hashes, installation checks, exact public-source checkout and
clean Git status are recorded externally in `final/freeze.json`, avoiding a
self-referential archive/commit hash in its own packaged document.

Owner: review the source diff and new policy's explicit authorization, preserve
the raw local evidence, then publish the exact branch only if accepted. Require
all six Windows/Ubuntu/macOS × Python 3.12/3.14 hosted jobs for the exact final SHA
before merge. No fragile wall-clock CI thresholds were introduced. Publication
commands and the bounded V15-05 proposal are in `v15-04-handoff-es.md`.
