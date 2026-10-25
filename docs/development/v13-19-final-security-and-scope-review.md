# V13-19 — Final bounded security and product-scope review

Date: 2026-10-25. Starting source: `dfcb6d9d6c2c1b3b475f1f6a64b193362cabed98`.
Status: **PASS within the reviewed subset**, subject to the integrated installed
regression in V13-20. This review is not security certification or a promise that
future correctness maintenance will be unnecessary.

## Changes and independent evidence

The prior V13-08 parser corrections and V13-11 incremental native-evidence budget
were reviewed against their regression tests. They were not redesigned. The
remaining ARP interpretation issue is corrected and tested in V13-15; unsupported
and incomplete observations cannot become native reachability conclusions.
V13-14 independently challenges capture framing and decoder interoperability;
V13-18 documents the public contract boundary. The exact final commit and
installed source/artifact identities are recorded in V13-20.

One additional evidence-quality finding was confirmed:

| Finding | Classification | Correction and impact |
| --- | --- | --- |
| `tools.capture_contract` labeled checkout-source hashes as production hashes even when another regular installed distribution supplied the runtime | Important but nonblocking product-provenance defect; corrected before final acceptance | Hash the actually imported package modules. The pinned-baseline verifier independently compares the complete installed baseline module inventory with `git archive f52c792b683cb499dc7de765b65b5cc897a96854`. No runtime analytical behavior changes. |
| Hosted workflow did not reproduce the native baseline/candidate artifact comparison | Validation gap; corrected workflow, execution pending authorization | Reuse the versioned contract comparator with explicit `1.2.0` to `1.3.0` arguments. Only root `engine_version` and its exact HTML rendering may differ. Explicitly record the reviewed `cli.py` additive registration and `reachability.py` observer changes in the provenance allowlist. No other analytical artifact differences are allowed. |

The comparator retains its historical defaults and strict serialization checks.
It rejects changes to arbitrary text, SVG, schema versions, nested data or other
fields. Eight focused comparator tests passed, with six installed-version cases
deselected until the final 1.3.0 installation. Ruff and strict mypy passed for
the three updated verification tools (mypy with `MYPYPATH=src`). An initial mypy
invocation without source discovery reported missing typing information from the
old regular installation; the corrected invocation checked the actual source.

Targeted security regression, with source imports and the Python network-denial
harness, ran:

```powershell
$env:PYTHONPATH='src;tools/offline'
$env:OTARCHGUARD_OFFLINE_CHECK='1'
.venv\Scripts\python.exe -m pytest tests/test_capture_parser.py tests/test_capture_reconciliation.py tests/test_capture_independent_resources.py -q --basetemp=output/v13-final/security-review-tmp --tb=short --junitxml=output/v13-final/security-review.xml
```

Actual result: **163 passed in 4.34 seconds**, no skips/failures. Raw receipts:
`output/v13-final/security-review.xml` and `security-review.stdout`. These tests
overlap the final full suite and must not be added to its total. They support
review of changed source; they do not replace final regular installed-package
acceptance. Windows CPython 3.14.5 was used. Other platforms are NOT RUN here.

## Reviewed boundaries

| Area | Assessment and practical limit |
| --- | --- |
| Binary framing and reads | File/record/block/interface/option ceilings precede large reads; invalid framing aborts, while damaged packet metadata remains explicitly classified. Unknown link types and blocks cannot supply fabricated ports. Fixed-seed mutation tests produce controlled results. |
| Protocol interpretation | Malformed/fragmented/truncated metadata clears authoritative ports and initiation evidence. Supported metadata does not prove a receiving stack accepted a packet. Checksums, reassembly and complete TCP/IP option semantics remain outside scope. |
| Native amplification | Shared query/work ceilings and per-interval retained-evidence accounting prevent per-query resets and late unbounded result retention. One native interval is in flight before its charge, and there is no OS RSS enforcement. |
| Owner review | Bounded UTF-8 JSON, duplicate-key/NaN rejection, depth/node/text limits, exact version types, immutable candidate facts, complete proposal sets and capture/model/observation hashes reject stale or forged decisions. Reviewer text is an assertion, not authenticated approval. |
| Filesystem behavior | Input regular-file/descriptor identity checks and symlink/junction rejection detect ordinary replacement. Fresh mapping outputs use no-clobber writing; complete report staging is audited before publication. A trusted local single-writer directory is required. Concurrent hostile path-ancestor replacement and mapped remote filesystem behavior are not proven safe. |
| Injection and privacy | Renderer escaping, fixed filenames, local links and restrictive CSP prevent interpreted capture/review text from becoming scripts or remote resources. Payloads, comments, secrets blocks, source paths and interface names are omitted. IP/MAC/port/timestamp/reviewer metadata remains sensitive. |
| Failure publication | Fatal parsing, resource and staging failures do not publish a successful partial report or alter the input/model. Generic CLI exception diagnostics avoid traceback and local-path disclosure. Prior valid outputs remain separate evidence. |
| Offline behavior | Runtime code introduces no socket, resolver, upload or telemetry path. Network-denial tests support this claim for Python operations; they do not establish a physical air gap or OS sandbox. |
| Determinism and contracts | Capture timestamps remain exact evidence; execution times and local paths are excluded from canonical artifacts. Canonical digests detect content changes, not authorship. Final golden/consumer checks are in V13-18 and installed verification is in V13-20. |
| Packaging and platforms | Explicit public-source and archive member audits remain mandatory. The new version and installed-source provenance are checked for wheel and sdist. Six hosted cells and actual human browser acceptance remain separate outstanding gates. |

No unresolved release-blocking defect was demonstrated in this bounded review.
Residual filesystem, sensor-visibility, NAT/DHCP/address-reuse, spoofing and session
uncertainty limits are documented product boundaries, not inferred successes.
Accessibility structure and links are mechanically checkable; human interaction
and rendering remain V13-17. No WCAG certification is claimed.

## Industrial inspection and functional scope

Deep industrial protocol inspection is a **future enhancement**, not a release
dependency. Current transport metadata, explicit port hints and declared-service
comparison serve the present architecture-evidence use case without parsing
industrial commands. Adding command recognition would require protocol variants,
message fragmentation/reassembly, partial-stream treatment, parser budgets,
malformed application inputs, privacy controls, independently validated corpora and
new false-interpretation boundaries. It must not convert conventional ports into
confirmed application or successful process-operation claims.

Historical analysis, drift detection, multi-capture management, live capture and
deployed-firewall verification are intentionally unsupported. Any v1.4 industrial
inspection proposal requires separate demonstrated need, design and owner approval.
Security fixes and correctness corrections remain possible after functional freeze.

## Next step

Complete the exact 1.3.0 installed regression and artifact audit in V13-20. Execute
V13-21 only after specific owner authorization for the reviewed remote write.
The reviewed subset is suitable for functional closure when those distinct final
acceptance requirements and V13-17 human checks are honestly accounted for.
