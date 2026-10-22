# Scope and known limitations

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

A known invalid-text issue remains: escaped unpaired Unicode surrogates can cause
UnicodeEncodeError in the validation API. The CLI returns a generic exit-2 execution
diagnostic and preserves existing output. This issue remains in version 1.0.1.

Ceilings are rejection limits, not capacity promises. Reports retain evidence in
memory. Benchmark memory is traced Python allocations, not RSS. Python 3.13,
other platforms, fresh OS/physical air gap and broader browser coverage remain
unverified. See the [verification summary](verification.md) for the tested scope.
