# Scope and known limitations

The development Architecture Explorer supports native models and matching project
provenance version 1. Other sidecar versions fail explicitly; model-only mode has
no documentary origins. It never imports old HTML as analytical truth. Its bounded
diagrams disclose omissions and keep complete linked records; exceeding a file,
text or site budget rejects the complete generation. Default output contains
sensitive selected architecture/evidence; no public-safe redaction mode or universal
secret detector exists. Local-file browser behavior, 200% zoom, actual keyboard
focus and assistive technology remain unverified because the available browser
tool blocks `file://`. Structural accessibility/resource/link tests do not establish
WCAG certification or browser network behavior. See the
[Explorer ADRs](development/v12-05-architecture-explorer.md).

This checks finite owner-declared IPv4 TCP/UDP initiation paths. It does not discover
deployed inventory, topology, bypasses, listeners, enforcement or vulnerabilities.
Completeness, classification, criticality and origin assumptions remain declarations.

There is no return-path/session, authentication, exploitability, compromise probability,
availability, timing, physical impact or process-safety determination. Security-level
evidence is unassessed, not zero. No security score or deployable remediation is produced.

Unsupported: IPv6, non-TCP/UDP protocols, source ports, NAT, ordered/stateful rules,
routing tables/VRFs, VLAN/L2 behavior, application relays, same-interface forwarding,
multiple administrative owners and protected/multizone conduits. Unsupported/resource-
limited evaluation is an error, never successful unreachability.

Static diagram ordering, long/shared-looking routes and large-topology summaries
have presentation limits. Full evidence and omissions remain available. No new
browser/print claim follows from parsing or static images.

The v1.1 renderer uses explicit-topology ordering, orthogonal tracks and finite
clipped labels. Routes can cross or share endpoint strokes; dense layouts can be
tall. Summary mode retains complete analysis/inventory. Actual browser focus,
responsive layout and printing remain unverified in Gate V11-2, as does hosted
Linux/macOS acceptance. See its [manual checklist](v1.1/gate-v11-2.md) and
[report options](reporting.md).

A historical v1.0.1 invalid-text issue remains in that release: escaped unpaired Unicode surrogates can cause
UnicodeEncodeError in the validation API. The CLI returns a generic exit-2 execution
diagnostic and preserves existing output. This issue remains in version 1.0.1.

Version 1.1.0 includes the V11-1 Unicode/escape correction;
the historical v1.0.1 release was not replaced.

Ceilings are rejection limits, not capacity promises. Reports retain evidence in
memory. Benchmark memory is traced Python allocations, not RSS. Python 3.13,
other platforms, fresh OS/physical air gap and broader browser coverage remain
unverified. See the [verification summary](verification.md) for the tested scope.
