# Release verification checklist

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

The [verification summary](verification.md) records the tested environments and
scope. Use the [testing strategy](testing-strategy.md) for reproducible checks.
