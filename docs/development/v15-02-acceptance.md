# V15-02 — Local acceptance record

Implementation verification is in progress. This document is finalized after
the full installed-runtime campaign and independent audit. No pending check is
represented as PASS.

Baseline is merged `b3adcc9de21dfff6ad58946028a241844ff88294`; see
[plan](v15-02-plan.md) and [compatibility contract](v15-02-compatibility-contract.md).
Raw receipts remain local and ignored under `output/v15-02/`; they are not
included in public distributions.

| Requirement | Evidence |
|---|---|
| Exact 97-module transition, protected historical inputs | `tools.verify_v15_transition`, `test_v15_transition.py` |
| Original V14 contract | Unchanged verifier on isolated predecessor |
| Independent exact native outputs | Predecessor/candidate capture comparison |
| Producer boundaries and recovery | Real old installed workspace, new rejection, old replay |
| Seven-statement UX and renderer identity | `test_v15_renderer_ux.py`, fresh walkthrough |
| F06 primary/secondary diagnostics | Pre-fix receipts, `test_v15_report_reliability.py` |
| Regular packages and source identity | Archive audit and environment receipts |
| Regression/static quality | Full JUnit, Ruff, formatting, strict mypy, pip check |
| Performance | Paired `benchmarks.v15_transition`, same driver/input scales |
| Independent skeptical review | Agent E audit and dispositions |

Hosted Windows/Ubuntu/macOS × Python 3.12/3.14 and human browser acceptance
remain owner gates. No push, remote PR, merge, tag or release is authorized.
