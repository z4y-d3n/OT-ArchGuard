# Release verification checklist

For source version 1.1.0, use the dated [V11-6 dossier](v1.1/gate-v11-6.md)
as historical evidence and the
[owner-only publication/recovery runbook](release-publication-1.1.0.md).
Preparation does not authorize commit, remote operations, tagging or publication.

- [ ] Distinguish source version 1.1.0, historical v1.0.1 and actual publication records.
- [ ] Compare preserved 197/123-artifact baselines with exact engine-only exceptions.
- [ ] Preserve canonical hashes, analytical semantics, counters and ceilings.
- [ ] Confirm package version, schema compatibility and documented changes.
- [ ] Review the explicit public file manifest and documentation links.
- [ ] Retain Apache-2.0 and all required dependency notices.
- [ ] Run tests, Ruff, strict mypy and dependency consistency checks.
- [ ] Verify regular installed packages on the documented Python versions.
- [ ] Run native CLI examples with network operations denied by the test hook.
- [ ] Verify exit codes, report determinism and preservation of existing reports on failure.
- [ ] Build wheel and source distributions and audit every archive member.
- [ ] Compare packaged source, tests, documentation and license files with the source tree.
- [ ] Rebuild from the source distribution and compare wheel payload bytes.
- [ ] Verify Markdown links and document unsupported or unverified behavior.
- [ ] Calculate SHA-256 checksums for the final distribution files.
- [ ] Record working-tree content hashes as well as starting commit provenance.
- [ ] Obtain six current hosted OS/interpreter results on the approved commit.
- [ ] Rebuild/audit accepted post-merge source before separate tagging approval.
- [ ] Obtain separate owner approval for publication destination and exact assets.
- [ ] Verify public tag, downloaded assets and installed behavior after publication.
- [ ] Preserve v1.0.1 assets and the immutable-release recovery procedure.

The [verification summary](verification.md) records the tested environments and
scope. Use the [testing strategy](testing-strategy.md) for reproducible checks.
