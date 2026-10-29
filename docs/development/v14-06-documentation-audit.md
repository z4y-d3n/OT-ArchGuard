# V14-06 — Documentation and onboarding assurance

Subagent D reviewed current user guidance. This is a documentation/command audit,
not final installed-candidate acceptance or a new human browser review.

## Findings and dispositions

| ID | Capability and reproduction | Expected / actual | Severity | Disposition and evidence | Residual limit |
|---|---|---|---|---|---|
| V146-D01 | Read parent README and `docs/v14-foundation.md`; compare with implemented CLI and owner acceptance | Current guide describes implemented history/Explorer and completed prior acceptance / still calls Explorer future and browser acceptance pending | P1 documentation | Corrected current guidance, product capability summary, candidate notes and checklist; original milestone reports retain historical context | Child CI and integrated source remain separate owner gates |
| V146-D02 | Read parent `docs/limitations.md` and primary capture guidance | Distinguish published v1.3 from candidate bounded enrichment/history / future-work wording can be read as the current product scope | P1 documentation | Add current-candidate limits and separate capture-observation versus enrichment signposts | Seven subsets remain bounded; external positive Modbus/DCP/IEC104 gaps remain visible |
| V146-D03 | Upgrade a development producer identity to final package identity; inspect revision source binding (pipeline agent reproduction) | Preserve exact-source replay and explain operational upgrade / earlier primary install guide lacked this boundary | P1 onboarding | Installation, README, history, Explorer and candidate notes require retained dev environment/workspace and new final-version analyses/review | No automatic cross-source approval migration or demonstrated historical-data downgrade |

The version transition does not justify weakening producer hashes or rewriting
stored analyses/approvals. No production or presentation changes were made by D.

## Public documents changed

- `README.md`: current candidate identity, complete capability map, seven bounded
  subsets, historical interpretation boundaries, truthful first run and prior CI.
- `CHANGELOG.md`: capability-organized unpublished 1.4 entry; old milestone notes
  remain explicitly historical.
- `docs/installation.md`: candidate asset selection, complete checksum verification,
  wheel/sdist, offline dependency closure, exact installed identity, parallel
  environments, examples, historical upgrade, uninstall and v1.3 recovery.
- `docs/release-notes-1.4.0.md`: new candidate release notes, compatibility, privacy,
  tested-versus-declared Python scope, limitations and owner gates.
- `docs/release-checklist.md` and `docs/testing-strategy.md`: exact-source freezes,
  separate installed payloads, narrow historical gate, local four-asset rehearsal,
  parent/child/integration CI distinctions and owner acceptance.
- `docs/v14-foundation.md`, `docs/v14-history.md`,
  `docs/v14-historical-explorer.md`: current capability/visual status, corpus limits
  and exact-source development-workspace boundary.
- `docs/limitations.md` and `docs/pcap-evidence-studio.md`: current v1.4 scope while
  preserving published v1.3 capture semantics and historical evidence.
- `examples/README.md`: verified-source selection and explicit environment-path
  substitution for parallel candidate installation.

## First-run acceptance map

These mappings identify the smallest existing guides/harnesses for each required
user path. Final candidate execution and package identities belong to the
integrator's handoff; rows do not assert unexecuted final acceptance.

| Path | Current user guidance / acceptance evidence |
|---|---|
| 1. Discover repository | README purpose, intended declared/passive review scope |
| 2. Understand capabilities | README capability table and candidate notes |
| 3. Understand exclusions | README limits; limitations and protocol guide |
| 4. Select installation | Installation candidate/stable distinction and asset table |
| 5. Install wheel | Installation parallel wheel command; final package campaign |
| 6. Verify installation | Console/metadata/native/import-path command and pip check |
| 7. Native model check | Six D smoke commands; `examples.run_examples` for final replay |
| 8. Architecture Explorer | `examples/explorer/README.md`; `tools.explorer_walkthrough` |
| 9. Documentary import | `examples/import-studio/documents/README.md`; `tools.document_walkthrough` |
| 10. Fictional PCAP | `examples/capture-studio/README.md`; `tools.capture_walkthrough` |
| 11. Industrial metadata | `docs/v14-foundation.md`; seven bounded subsets and abstentions |
| 12. Historical workspace | History init-v2/add and explicit v1 migration |
| 13. Analytical revisions | History attachment dependencies and exact revision IDs |
| 14. Baseline and review | History proposal/inspection/explicit local decision |
| 15. Historical comparison | `docs/v14-drift.md`; `tools.drift_walkthrough` |
| 16. Historical Explorer | Explorer command and fictional walkthrough |
| 17. Portable verification | `explore-verify NEW_DIRECTORY` help and interpretation |
| 18. Source reproduction | `explore-verify ... --workspace WORKSPACE`; compatible producer required |
| 19. Unsupported results | Protocol statuses, drift comparability, native exit semantics |
| 20. Revert or uninstall | Retained v1.3 executable/assets; no workspace downgrade claim |

## Executed evidence

1. `.venv/Scripts/python.exe -m pytest tests/test_product_presentation.py::test_trace_documentation_qualifies_completed_queries -q --basetemp=output/v146/documentation-pytest`:
   **1 PASS**, 0.43 s. README retains the exact Trace-exit interpretation required
   by the existing regression. No test assertions were changed.
2. Six regular-installed native commands under the Python offline hook: version,
   help, validate/check remote-support baseline, exposure `support_scope` to HTML,
   and trace source `it`/service `svc_plc` to JSON. All exit 0 with empty stderr;
   `output/v146/documentation-onboarding.json` and command outputs retain evidence.
   Installed identity was **1.4.0.dev1**: this validates unchanged native command
   syntax/semantics and is explicitly **not** final-version installation acceptance.
3. `capture enrich --help` and `evidence drift explore-verify --help` confirm the
   documented options and interpretation boundaries against the regular parent
   console. Final installation checks remain required after transition.
4. PowerShell's parser checks **12** fenced PowerShell blocks in README, installation,
   candidate notes and testing strategy; `output/v146/documentation-powershell.json`
   records the block count and zero syntax errors. Parsing is not command execution
   or POSIX platform verification.
5. `git diff --check` on D's existing tracked documents passes.
6. Local Markdown targets/fragments across **17** current public documents and
   example READMEs: **171** references checked, **171** resolve after the integrator
   created the explicit pending handoff scaffold. Link existence does not accept
   the handoff's pending evidence. Rerun
   `python output/v146/documentation-link-audit.py` after final handoff changes; the
   strict script exits nonzero on any missing target/fragment and writes
   `output/v146/documentation-links.json`. External URLs were not independently
   fetched by D; parent CI/public release identities use integrator's verified data.

Renderer bytes and accepted layouts were not changed. Prior V14-04 human visual
acceptance remains relevant; D performed no new browser, zoom, focus, keyboard,
print or accessibility-certification acceptance.
