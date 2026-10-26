# UX remediation — analytical contract and security preservation

## Status and scope

**PASS for targeted local engineering checks; final installed/hosted and second
human acceptance remain separate requirements.** This
independent review owns presentation regression tests, not production rendering.
No parser, observation, association, reconciliation, native evaluator or frozen
JSON fixture was modified for this review. The report covers the contract and
security work requested by gates V13-27/V13-28 of the UX-remediation prompt.

The baseline is local documentation-only commit
`e763f0cb6591dee6b80b6aa846286d2b901a95ae`, whose parent is hosted candidate
`5c4c18da4711c36f4f5750c03009d429551d0cf0`. The earlier hosted run is historical
evidence; it does not validate new rendering code. Final source/package provenance,
full regression and hosted results belong to their respective supplementary records.

## Authoritative human feedback

The owner's original six outcomes remain:

| Criterion | Original owner result | Second owner review |
|---|---|---|
| Immediate comprehension | PASS | PENDING |
| Communication diagram | PASS | PENDING |
| Navigation and traceability | FAIL | PENDING |
| Interpretation of analytical results | FAIL | PENDING |
| Legibility | PASS | PENDING |
| Offline operation and keyboard navigation | PASS | PENDING |

These outcomes come from the owner-supplied remediation prompt. Automated link
audits, screenshot inspection and this test suite cannot convert either FAIL into
a human PASS. No original review date or browser version is invented here.

## Preserved baseline evidence

The existing reviewed-example report was available at
`output/v13-final/wheel-tutorial/comparison/index.html`. All fourteen files were
copied to a new ignored evidence directory, without changing the original:
`output/v13-ux/integrity-baseline/`. The original observations file has SHA-256
`66302056dcbd760322b96ab82a15446ea689a2947fc7afa8037f2f14861cdf1a`, exactly
matching the frozen **limited** observation fixture. The original tutorial uses
its own fictional owner-review strings, so its mapping and comparison bytes are
retained separately rather than falsely equated to the golden bundle.

`baseline-hashes.json` records every original report file and all seven frozen
fixture files. It also records these baseline analytical module identities:

| Module | SHA-256 |
|---|---|
| `capture/parser.py` | `460ac34c0df3184d55b1f325ef1b2851256c0b89762910145b0d7c67642de096` |
| `capture/observations.py` | `9a6ce4376a807ba72a1af195b2d4dc59693494c19fb7d2a6cc7870efd158fddd` |
| `capture/reconciliation.py` | `9533662627858783d175f0b58aa063102c74a30ad091370ddb7baa4c7ea27f6c` |
| `capture/contract.py` | `dc90ef11cdbf328904226c9d0a910b2cefd87c977b69e3ffa518c70aabadaedc` |

The exact baseline renderer was read from Git without modifying the checkout and
saved as `explorer-baseline.py`. Its SHA-256 is
`04a998b3ce48fe918e31db2d47f88a1729a24196f1b86933fe6df0b3fa73c5fb`.

## Independent red regression reproduction

`tests/test_capture_ux_integrity.py` uses its own HTML tree/link inspector, not the
product's `audit_site` as its oracle. The exact baseline renderer was loaded into
an isolated Python process and the new tests executed against it. The complete
baseline execution with the final test file reported **11 failed, 13 passed in
6.20 seconds**. These are
intentional UX regression failures, not a claim that historical analytical tests
failed. Raw receipt:
`output/v13-ux/integrity-baseline/old-renderer-final-tests-pytest.txt`. The exact
test file used is saved beside the receipt as `test-capture-ux-integrity-final.py`.
The earlier 21-case reproduction (8 failed, 13 passed) is retained separately.

The old renderer fails on default-visible JSON, opaque finding-link labels,
rational primary timestamps, missing contextual joins at normal/paginated sizes,
missing secondary/current navigation, dense address-to-aggregate traceability,
address-index fragments for an ARP-only report, executive denominators, and
absence-fragment discovery. Security, deterministic output,
frozen analytical bytes, offline operation, no overwrite and fail-closed resource
checks already pass the old renderer and remain preservation requirements.

## Frozen evidence and identity checks

Both independently readable supported/limited golden bundles are rendered directly.
For each bundle, the tests require byte-for-byte equality of generated
`observations.json`, `mapping.json` and `comparison.json` with the original fixtures,
no mutation of the supplied Python records, and successful consumption by the
existing standalone read-only evidence consumer. This preserves capture/model
hashes, flow/group/association identities, classifications, native witnesses,
diagnostics, packet references, ordering and all contract version fields together.

The analytical source-hash test separately rejects changes to the four capture
core modules above. It does not certify every possible future input; the full
historical, parser, reconciliation and installed-package suites remain required.
The independent goldens must not be regenerated to accommodate presentation changes.

## Navigation and safety checks

The **24 new test cases** check all local destinations, unique fragment IDs, exact contextual
joins between addresses, aggregates, groups, findings, owner decisions and detailed
evidence, including pagination. A 130-aggregate synthetic report exercises the
diagram fallback and complete paginated address relationships. Bounded previews are
accepted only when their `All N related communications` entry targets the exact
host's first reference and table pagination reaches the full correct relationship
set. Global navigation is not used as a substitute for contextual traceability.
The evidence index is independently followed through its own pagination.
An ARP-only request
independently checks that its target remains a reference, without an address or
association catalog entry. Complete access is checked, not just preview links.
Exact overview counts are checked against both frozen cases, including a zero
missing-service count when absence assessment is suppressed. Distinct valid service
IDs `svc_a` and `svc-a` exercise fragment uniqueness without changing canonical
service identities or analytical evidence.

Hostile text is inserted directly at the rendering boundary independently of the
strict owner-review parser: HTML-like owner text, asset/interface display values,
protocol hints, capture metadata, long rationale text, local paths and bidi controls.
Tests require escaping, explicit bidi placeholders, path redaction, no injected
elements or event attributes, restrictive CSP and local stylesheet references.
Unsupported controls/surrogates and unsafe canonical IDs must fail before publication.
No-clobber destinations and output budgets must preserve existing evidence.

Rendering is repeated with socket creation and name resolution denied. Complete
site bytes must be identical. The independent markup audit forbids active embedded
content, remote destinations and asset references, and confirms visible focus and
responsive CSS. These are engineering checks, not browser-network instrumentation,
formal accessibility certification or human keyboard acceptance.

## Integrated execution and pending evidence

Development command, with `PYTHONPATH=src` and a fresh local pytest temporary path:

```text
.venv/Scripts/python.exe -m pytest tests/test_capture_ux_integrity.py -q --basetemp=.pytest_tmp/ux-integrity-integrated
```

Actual integrated source result on Windows/Python 3.14.5: **24 passed in 16.41
seconds**. Ruff lint/format and strict mypy passed for the new test file.
`output/v13-ux/integrity-final/verification-summary.json` records the tool result,
source identities, commands, and a separate rendering of the original retained
tutorial. All three original tutorial analytical JSON files remained byte-identical:

| Artifact | Preserved SHA-256 |
|---|---|
| `observations.json` | `66302056dcbd760322b96ab82a15446ea689a2947fc7afa8037f2f14861cdf1a` |
| `mapping.json` | `c66a7f059346ef2d138e5a1420db4d9f9080eb1d1b63c9e712b20728e93f8389` |
| `comparison.json` | `4d97ae6acebdfcf0fe96d333f45a41910fa94568795459c4c013fae17297b57e` |

That supplementary tutorial rendering passed the product audit with 12 HTML pages,
110 anchors, 617 internal links and zero broken links. The independent test suite
separately audits supported, limited, dense and paginated outputs. Counts overlap
the final regression suite and must not be summed as independent tests.

Full installed-package tests and new hosted CI must refer to the exact corrected
candidate. Both original human FAILs remain pending until the owner's second review.
