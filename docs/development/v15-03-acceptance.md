# V15-03 acceptance record

Candidate evidence is retained under ignored `output/v15-03/`. This document is
updated after the stable integrated source is verified. Historical and current
campaigns are counted separately; repeated focused/sdist runs overlap.

| Requirement | Evidence / status |
|---|---|
| Authenticated V15-02 merge | PASS: PR27, a3cf2f2, exact tree; hosted run41741064369 six SUCCESS |
| J1 first-run architecture | PASS structural/generated journey: agent-a/agent-b receipts |
| J2 capture | Baseline reproduced C-01/C-02; candidate journey tests required |
| J3 historical | PASS baseline normal/incomplete/decoder/dense/revoked walkthrough |
| J4 import/review | PASS baseline authentic human-review/provenance handoff; preserved |
| Canonical preservation | Predecessor independent rendering + frozen native comparison required |
| Source transition | Exact two changed/95 unchanged modules; installed pre-import check required |
| Historical preservation | Old portable/replay rejection/recovery and unchanged inventory required |
| Accessibility semantics | Independent structural tests required; browser NOT_TESTED |
| Responsive/keyboard/zoom/print | NOT_TESTED: browser policy blocks local-file protocol |
| Security | Existing hostile labels/CSP/path/bidi/resource tests retained |
| Completeness | Ordered flow batches, records, anchors, links and mutations required |
| Installed product | Regular wheel/sdist audit, identities and affected suite required |
| Performance | Paired five-trial complete-render receipts required |
| Independent F review | Required after stable candidate |
| Candidate hosted CI | NOT_TESTED: requires six jobs for actual submitted SHA; no push authorized |
| Owner manual acceptance | NOT_TESTED; explicit checklist in accessibility/handoff |

Raw command logs retain nonzero attempts as well as successful reruns. Initial
sandbox V15-02 preflight failed during ensurepip; normal-process retry is retained
separately. Neither initial failure nor unexecuted browser checks are reported PASS.
