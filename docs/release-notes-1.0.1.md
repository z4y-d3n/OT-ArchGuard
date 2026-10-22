# OT-ArchGuard 1.0.1

Version 1.0.1 is a maintenance update to offline architecture validation,
TCP/UDP initiation reachability, communication-intent checks, exposure comparison
and JSON/HTML/SVG reporting. It retains schema 1, analysis semantics, resource
limits and CLI exit codes.

Distribution checks use an explicit public file manifest, reject unexpected archive
members and compare packaged source, tests and documentation with the source tree.
They also verify metadata, console entry points, license notices and wheel RECORD
digests. Rebuilding from the source distribution checks wheel payload consistency.

Python 3.12 or later is required. Local verification covers regular installed
packages on Windows Python 3.12.14 and 3.14.5, with 608 tests passing on each,
static checks and 27 synthetic example commands. See [verification results](verification.md)
and [installation](installation.md).

Analysis applies to finite declared IPv4 TCP/UDP initiation paths. It does not
discover deployed networks or establish session behavior, exploitability,
availability or process safety. Escaped unpaired Unicode surrogates can still
produce a generic exit-2 diagnostic instead of a validation diagnostic.
See the full [limitations](limitations.md).
