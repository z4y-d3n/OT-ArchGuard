# V15-03 — Reproducible findings and journeys

All sources are fictional. A/B/C independently generated regular-dev1 reports;
no browser interaction failure is inferred from parsed markup. Their scripts,
routes, audits and baseline test JUnit are under `output/v15-03/agent-{a,b,c}`.

| ID / journey / severity | Reproduction and impact | Cause / minimal correction | Verification / risk / disposition |
|---|---|---|---|
| C-01 J2 P2 | Generate frozen supported JSON with rows/page=2; open `agent-c/supported/conversations-2.html`. `conversations.html` falsely has `aria-current=page`; same issue in 36 supported and 42 limited documents. Screen-reader orientation names a different document. | `capture/explorer.py` normalizes filename to family. Retain entrypoint href, mark family `true`, exact document `page`. | Independent page-equality guard and wrong-existing-page mutation; exact source policy delta. Low risk; implemented. |
| C-02 J2 P2 | Open `agent-c/supported/evidence-5.html`: no batch count, record range or adjacent navigation. Browsing adjacent batch requires returning to the index (at least two hops, more when its index page must be located). | Detail loop emits records only. Capture-local native pager with Page N/M, record range and previous/next: one hop. | Complete ordered flow-ID batches, bidirectional continuity, wrong-next/omission mutations. Bounded extra markup, existing limits retained; implemented. |
| B-01 J1/J4 P2 | Architecture and review navigation omit current-page annotations. | Shared document helper; changing its bytes also changes historical renderer source identity. | Valid existing links preserved; defer broader transition. |
| B-02 J4 P2 | Review-generated assessment uses Architecture Explorer branding. | Shared document branding. | Authentic provenance/decisions accessible; defer separate component-specific correction. |
| A-03 J3 P2 | Historical navigation lacks a current-page marker. | Historical document helper. | Scope/finding/evidence/approval routes work; defer separately versioned renderer change. |
| A-04 J2 P3 | Capture example installs stable 1.4.0 but says require CLI 1.3.0. | Engine/distribution wording in tutorial. | Corrected published distribution versus native-engine wording; no runtime change. |
| K-01 J2 assessment | Skip target lacks explicit programmatic focus attribute. No actual browser failure observed. | Add `tabindex=-1` to capture main alongside navigation correction. | Structural assertion only; keyboard acceptance remains NOT_TESTED. |

No P0/P1 demonstrated. Cosmetic preferences are not classified as defects.
No canonical result, status vocabulary, source provenance or authorization changes.
All selected source changes are in `capture/explorer.py` plus development identity
in `__init__.py`. No shared presentation module changes.

## Successful baseline routes

| Journey | Starting command / artifact | Route and result |
|---|---|---|
| J1 | `.venv-v152-wheel/Scripts/python.exe -m otarchguard explore tests/fixtures/boundary-device.yaml --output output/v15-03/agent-a/architecture --trace it:svc_jump --trace it:svc_plc --check --scenario support_scope` | Agent-a native route: overview → assets → it → exact trace → declared rule → overview, five hops. Agent-b provenance route: overview → assets → eng → metadata candidate → owner decision → eng → overview, six hops, all hrefs authenticated against retained candidate/decision identities. |
| J2 | `.venv-v152-wheel/Scripts/python.exe output/v15-03/agent-c/discover.py` | `supported/index.html` → hosts → exact address/communication → finding → `evidence-N.html#flow-ID` → reviewed association → conversation. Six hops; observed traffic and declared reachability remain distinct. All retained IDs/ARP context match frozen JSON. |
| J3 | `.venv-v152-wheel/Scripts/python.exe -m tools.historical_explorer_walkthrough --output output/v15-03/agent-a/historical` | normal overview → scope → communications index → finding → source attachment/evidence → verification → overview. Incomplete/decoder/dense/revoked variants generated; recorded approval and fresh REVOKED authority remain separate. |
| J4 | `.venv-v152-wheel/Scripts/python.exe -m tools.project_walkthrough --output output/v15-03/agent-a/import` | Imported documentary candidate → proposed model → explicit human decision → provenance → validated native Explorer. Rejected/pending proposals do not become declarations. Existing handoff satisfactory; no ingestion change. |

A audited 398 HTML pages / 7,375 links across representative sites, B independently
147 / 2,737, C 100 / 2,316. These overlap and must not be summed as unique pages.
All had zero missing files/fragments, duplicate IDs or external anchor links.
Exact baseline command arrays, artifact paths, anchors and hop evidence are in
each agent's findings and JSON receipts. Browser/keyboard/viewport/print: NOT_TESTED.
