# Release verification checklist

Latest stable [v1.4.0](https://github.com/z4y-d3n/OT-ArchGuard/releases/tag/v1.4.0)
is published. Previous stable [v1.3.0](https://github.com/z4y-d3n/OT-ArchGuard/releases/tag/v1.3.0)
remains available from `10d7de6c416ec6f0ee364c671ebe9292ee69e672` for recovery.
Current documentation can improve after publication without changing either
release's tag, source, wheel, sdist, manifest or checksums.

The checklist below is reusable for a **new exact source or documentation commit**;
unchecked boxes are not outstanding gates for the already published release.
Preparation alone authorizes no remote operation, tag or publication.

## Completed v1.4.0 publication record

| Publication fact | Verified identity |
|---|---|
| Owner-controlled publication date | November 2, 2026 (`2026-11-02T15:08:48Z`) |
| Published source commit | `7d6b158f863308dfcd7d10b673bfbe2692f29b8b` |
| Annotated tag | `v1.4.0`, tag object `4821b751eb4963018b0e68edadb85f351e5dfbb4`, resolving to that source commit |
| Stable GitHub Release | [OT-ArchGuard v1.4.0](https://github.com/z4y-d3n/OT-ArchGuard/releases/tag/v1.4.0), public, neither draft nor prerelease |
| Integrated-source CI | [main push run 40991511467](https://github.com/z4y-d3n/OT-ArchGuard/actions/runs/40991511467), six successful jobs for the published SHA |
| Matrix | Windows, Ubuntu and macOS × Python 3.12 and 3.14 |
| Version distinctions | Distribution/CLI `1.4.0`; frozen native engine `1.3.0`; native YAML schema `1`; Python metadata `>=3.12` |

PRs #17–#24 are merged. The release has these four uploaded assets; the two
automatically generated GitHub source archives are separate:

| Asset | Bytes | Published SHA-256 |
|---|---:|---|
| `otarchguard-1.4.0-py3-none-any.whl` | 362303 | `fdaaa37e920c63ed0d0b5fc6b07361de9f4df6957bf885c4e9f8a6ac59051abf` |
| `otarchguard-1.4.0.tar.gz` | 2290498 | `1636ebc32aa009becaeb1b21d02cc7942588f5872070949d52a38581626778f2` |
| `release-manifest.json` | 131636 | `a8b0ccf323589c554ba2fa3e8f88f34621ae540e795c0eb7807216add5ef89aa` |
| `SHA256SUMS.txt` | 280 | `a7474178f5472acb646eeef0c7b5c1f94ec657644bf376ca9cde0afa0ab351f8` |

See [download verification and installation](installation.md#obtain-and-verify-assets).
The manifest binds the tagged source and records assembly-time purpose/acceptance
limits; publication does not rewrite that historical text. The checksum list has
exactly three entries: wheel, sdist and manifest. Its own digest is recorded above.

The published source is an immutable historical snapshot. Current `main` continues
with documentation/development and requires its own checks. Later commits do not
invalidate the original release identities and must not cause v1.4.0 assets to be
rebuilt, relabelled or replaced. Hash identity alone is not evidence authenticity.

<a id="v14-candidate-acceptance"></a>

## Historical development acceptance

The [V14-06 handoff](development/v14-06-handoff-es.md),
[readiness report](development/v14-06-readiness.md),
[public-documentation handoff](development/v14-06-public-documentation-es.md) and
[Spanish publication runbook](development/v14-06-publication-runbook-es.md) retain
their original checkpoint identities, R01–R32 dispositions and then-pending gates.
They are historical engineering evidence, not current instructions to republish.
This publication record does not mark every earlier checkbox PASS or infer
unrecorded owner decisions, browser checks or external protocol tests.

V14-04 owner visual acceptance remains specific to its reviewed presentation.
Native v1.2 pin `f52c792b683cb499dc7de765b65b5cc897a96854` and approved V14-04
presentation pin `117318393ead604a023a24bad7d53eb429faa13f` remain unchanged.
Development workspaces retain their exact producer; stable installation does not
transfer approvals or authorize rewriting evidence digests.

## Reusable exact-source checks

- [ ] Identify the exact reviewed source commit and distinguish it from prior release tags.
- [ ] Preserve existing published tags, package bytes, checksums and historical acceptance records.
- [ ] Compare preserved native/evidence contracts using only documented version-specific exceptions.
- [ ] Preserve canonical hashes, analytical semantics, counters and enforced ceilings.
- [ ] Confirm package version, schema compatibility, implemented features and documented limitations.
- [ ] Review current documentation, example commands, links, fragments and image provenance.
- [ ] Account for every tracked public file in the explicit source/package inventories.
- [ ] Retain Apache-2.0 and all required dependency notices.
- [ ] For documentation-only changes, run focused Markdown/link, inventory and affected presentation/compatibility checks; run full-suite, Ruff, strict mypy and dependency gates for release/implementation acceptance as applicable.
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
