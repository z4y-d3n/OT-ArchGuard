# Release verification checklist

Stable [v1.3.0](https://github.com/z4y-d3n/OT-ArchGuard/releases/tag/v1.3.0)
is published from `10d7de6c416ec6f0ee364c671ebe9292ee69e672`. Its
[release notes](release-notes-1.3.0.md) summarize the completed six-configuration CI
and second human browser acceptance. Current documentation can improve after
publication without changing that tag or its wheel, sdist, manifest and checksums.

The checklist below is reusable for a **new exact source or documentation commit**;
unchecked boxes are not outstanding gates for the already published release.
Preparation alone authorizes no remote operation, tag or publication.

## V1.4 candidate acceptance

V14-06 prepares local distribution `1.4.0` with native engine `1.3.0`.
Published stable remains v1.3.0. The [candidate notes](release-notes-1.4.0.md)
and [Spanish owner handoff](development/v14-06-handoff-es.md) identify the exact
candidate evidence and R01–R32 gate dispositions. An owner-controlled gate is
not PASS merely because all local tests passed.

- [ ] Review the exact local candidate source/tree, findings and staged assets.
- [ ] Preserve native v1.2 pin `f52c792b683cb499dc7de765b65b5cc897a96854` and
      approved V14-04 presentation pin `117318393ead604a023a24bad7d53eb429faa13f`.
- [ ] Verify the narrow distribution-only transition rejects every other byte,
      unauthorized module, native-result, HTML-appendix and installed-source change.
- [ ] Retain development workspaces with their exact producer environment; do not
      transfer approval or rewrite digests across the final version transition.
- [ ] Run the local rehearsal from clean committed source into a fresh directory:
      `python -m tools.prepare_release --output output/release-review`.
- [ ] Reopen/re-audit the four completed assets with
      `python -m tools.prepare_release --output output/release-review --verify`.
- [ ] Authorize the owner-controlled Draft PR, then verify six hosted jobs for its
      exact source SHA, event, matrix, conclusions, skips and retained artifacts.
- [ ] Integrate the stack in the documented order; identify the resulting `main`
      SHA/tree and verify it independently, especially after squash/rebase/conflicts.
- [ ] Rebuild/re-audit from that final accepted source. Later source/doc changes
      invalidate earlier source/package hashes; do not reuse earlier asset receipts.
- [ ] Separately authorize the tag and publication; verify public downloads and
      retained v1.3.0 recovery after publication.

V14-04 visual acceptance and the six successful V14-05 parent jobs are relevant
prior evidence, not hosted acceptance of a changed V14-06 or integrated source.
No final stable tag or public v1.4 assets are created by this checklist/rehearsal.

## Reusable exact-source checks

- [ ] Identify the exact reviewed source commit and distinguish it from prior release tags.
- [ ] Preserve existing published tags, package bytes, checksums and historical acceptance records.
- [ ] Compare preserved native/evidence contracts using only documented version-specific exceptions.
- [ ] Preserve canonical hashes, analytical semantics, counters and enforced ceilings.
- [ ] Confirm package version, schema compatibility, implemented features and documented limitations.
- [ ] Review current documentation, example commands, links, fragments and image provenance.
- [ ] Account for every tracked public file in the explicit source/package inventories.
- [ ] Retain Apache-2.0 and all required dependency notices.
- [ ] Run relevant regressions, the full suite, Ruff, strict mypy and dependency checks.
- [ ] Verify regular installed wheel/sdist packages and their actual imported module hashes.
- [ ] Run native CLI examples with network operations denied by the Python test hook.
- [ ] Verify exits, deterministic reports and preservation of existing output on failure.
- [ ] Build only verification artifacts for the selected later source when required; never relabel them as the already published release.
- [ ] Audit every wheel/sdist member, metadata, entry point, license, RECORD and packaged source byte.
- [ ] Verify rebuilt wheel payload correspondence with the selected sdist where applicable.
- [ ] Record actual SHA-256 identities and the source-content hash, not just a moving branch name.
- [ ] Obtain six hosted Windows/Ubuntu/macOS × Python 3.12/3.14 results for the newly approved commit.
- [ ] Distinguish static/raster checks from real human browser, keyboard and interpretation acceptance.
- [ ] Audit any integration/release source separately before owner-controlled tagging or upload.
- [ ] Obtain separate owner authorization for the exact remote operation, destination and assets.
- [ ] After an authorized publication, verify the public tag, downloaded assets and installed behavior.
- [ ] Preserve a known-good environment and an immutable-release recovery path.

See the [verification strategy](testing-strategy.md) for reproducible commands.
The earlier [V11-6 dossier](v1.1/gate-v11-6.md),
[v1.0.1 measurements](verification.md) and
[v1.1](release-publication-1.1.0.md)/[v1.2 recovery runbooks](release-publication-1.2.0.md)
retain their original historical context, including earlier 197/123-artifact
baselines. Those results do not accept a later source automatically.
