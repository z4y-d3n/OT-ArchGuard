# ADR V14-01: distribution identity and native engine semantics

Status: implemented for the local development checkpoint; no release authorized.

## Problem and decision

V14-00 used the distribution string in canonical native evidence. Advancing the
package version therefore changed frozen capture-comparison bytes despite an
unchanged evaluator. V14-01 separates two explicit constants in `otarchguard`:

- `__version__ = "1.4.0.dev1"`: distribution metadata and `--version`.
- `NATIVE_ENGINE_VERSION = "1.3.0"`: the unchanged native evaluator/report identity.

The native CLI JSON, report writer, trace dataclass, Explorer canonical queries
and capture reconciliation use the latter. Their schemas, canonical fields,
ordering, meanings and hashes remain unchanged. The native Explorer footer also
retains the engine identity. Existing historical evidence is never rewritten.
An engine identity describes semantics, not the complete installed distribution.
It is not a claim that this development package is the stable v1.3.0 release.

The package now has an unambiguous development identity. Local wheel/sdist audits
must use `1.4.0.dev1` archives; there is no new publishable `1.3.0` artifact.
There is no added field in frozen legacy JSON to identify the distribution.
Execution receipts can separately record installed package metadata and source
digests without entering frozen analytical identity.

## Compatibility verification

The existing release identity test changes only the expected distribution value
and splits its three engine assertions into a fixed `1.3.0` value. No golden,
packet, observation, comparison or native expected assessment is changed.
The immutable v1.2 verifier checks these exact test substitutions. It also proves
that the three extra native-module exceptions are **exact import substitutions**
(`NATIVE_ENGINE_VERSION as __version__`); arbitrary code changes still fail.
The pre-existing CLI/reachability exceptions and root engine transition from
v1.2 to v1.3 remain explicit. The native compatibility comparator is unchanged.

New tests independently assert the different product/engine values and actual
report/trace output. Installed wheel/sdist suites exercise the existing frozen
capture comparison and independent evidence readers. The local acceptance report
records actual outcomes; this ADR does not substitute for execution evidence.

## Future changes

A change to native evaluation, policy evidence, canonical query semantics or
native report meanings requires a reviewed engine identity/contract transition.
Distribution bumps alone must not change `NATIVE_ENGINE_VERSION`. Parser,
enrichment and lifecycle identities are separate component versions. V14-01
emits enrichment schema 1 with decoder revision 2, retains strict revision-1
consumption, and leaves snapshot/workspace version 1 intact. The final v1.4
contract freeze, six-platform candidate CI and owner release decision remain
release blockers. A development version is not a release acceptance claim.
