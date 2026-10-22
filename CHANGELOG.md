# Changelog

## 1.0.1

- Restrict source distributions to an explicit public file manifest.
- Audit archive members, package metadata, entry points, license notices and
  wheel RECORD digests against the corresponding source files.
- Check wheel payload consistency when rebuilding from the source distribution.
- Add regression coverage for unexpected, missing and stale packaged files.
- Clarify installation, analysis semantics, reports and known limitations.

Schema 1, analysis algorithms, resource limits and CLI exit meanings remain
unchanged. Python 3.12 is the minimum; local verification covers Windows Python
3.12.14 and 3.14.5. The invalid-Unicode diagnostic issue remains documented in
[limitations](docs/limitations.md). See [verification](docs/verification.md) and
[release notes](docs/release-notes-1.0.1.md).
