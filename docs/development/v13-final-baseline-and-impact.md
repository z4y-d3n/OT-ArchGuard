# Final consolidation baseline and change impact

Date: 2026-10-25. Starting worktree clean on
`codex/v13-01-capture-foundation`, HEAD
`dfcb6d9d6c2c1b3b475f1f6a64b193362cabed98`, parent
`a9c651f4f3e6997ec6d2ef01c9675d8242dc3475`.
The complete prior development workspace, tests, built distributions and
`output/v13-audit/final-manifest.json` were present. No reconstruction was needed.
No AGENTS.md files were found in the repository. The baseline
`f52c792b683cb499dc7de765b65b5cc897a96854` is an ancestor; local main and the
cached origin/main point there. Tag v1.2.0 is preserved. Remote state is checked
separately before any proposed publication; cached refs are not live evidence.

The package/runtime initially identify as 1.2.0. Historical receipts report
2,612 full-wheel tests, 290 overlapping sdist capture tests, and 45 historical
cases / 123 identical artifacts. These remain historical results, not the new
candidate's results. Existing CI defines Windows, Ubuntu and macOS on Python
3.12 and 3.14. Hosted execution and human browser acceptance remain open.

## Bounded impact

- Independently generated capture interoperability and differential verification
  supplement the project's synthetic fixtures; no runtime decoder is added.
- Correct ARP sender/target semantics, host eligibility and diagram labels.
  Any changed public identities require an explicit observation contract revision.
- Improve human labels and packet grammar without changing classification codes.
- Freeze evidence contracts with golden records and an independent read-only
  consumer; preserve unknown/unsupported evidence and exact integrity bindings.
- Transition active package/runtime/documentation to 1.3.0, preserving historical
  release evidence; rebuild regular wheel/sdist installations and verify them.
- Recheck affected security, packaging, source and historical contracts. Do not
  repeat unrelated audits without changed bytes or a demonstrated risk.

The integration owner owns Explorer, contract freeze, manifests and final
verification. Independent reviewers own interoperability fixtures, ARP analysis,
and bounded security/release review. Each gate report records actual outcomes.
No remote write, PR, merge, tag, release or upload is authorized by this work.
