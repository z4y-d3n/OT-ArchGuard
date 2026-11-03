# V15-02 compatibility contract — policy 1

The authorization boundary is review of this gate's verifier and exact changed
source digests. SHA-256 receipts are not signatures or authenticated provenance.
An actor replacing both policy and tests can redefine a local check; independent
review of policy changes is required. Candidate-generated hashes cannot authorize
candidate source.

Authoritative entry is `python -I tools/verify_v15_transition.py`: Python isolated
mode excludes checkout/user import shadowing. Normal CLI invocation is rejected
before non-builtin imports. Oracle helpers are loaded by their validated absolute
paths only after checking predecessor bytes; candidate capture also runs isolated.
Installed metadata, import location and all 97 physical module hashes are checked
before runtime code may execute. Fresh cache prefixes prevent unreviewed cached
bytecode from replacing approved source; the comparator compiles immutable Git
bytes directly. Git is resolved outside the candidate checkout. Unit-level imported API checks
assume their caller already has a trusted interpreter; they are not a substitute
for the isolated command.

## Immutable references

Native: `f52c792b683cb499dc7de765b65b5cc897a96854`.
V14 presentation: `117318393ead604a023a24bad7d53eb429faa13f`.
Published v1.4.0 source: `7d6b158f863308dfcd7d10b673bfbe2692f29b8b`.
Reviewed predecessor: `867516be2c274a12d251c89bc0310a441b91da45`.
Merged predecessor: `b3adcc9de21dfff6ad58946028a241844ff88294`.
The last two have identical trees. Existing V14 verifier and recorded acceptance
retain their original meaning; they are executed on the predecessor, never
relabeled as accepting changed V15 source.

## Permitted transition

Exactly four of 97 Python modules change, without additions/removals:

| Module | Purpose | Invariants |
|---|---|---|
| `__init__.py` | Distribution `1.5.0.dev1` | Engine/alias `1.3.0` |
| `drift/explorer_render.py` | Vertical seven-item list, new renderer revision | Findings, escaping, bounds, links |
| `drift/explorer_bundle.py` | Accept exact new revision alongside old `.1`/`.2` | Strict inert bundle validation |
| `reporting.py` | Primary/secondary I/O diagnostic precedence | Atomic replacement, input protection, old bytes |

Reviewed SHA-256 inventory (before → candidate):

- `__init__.py`:
  `dfea43564e1416d2996e5007a29da17f2d97603f5883c48c9c3aec9f70a8289c` →
  `91cd2607f08d671a1468ee9919cd64617cd0fe86a3dcd5828c9d3c047ffa8626`.
  Protected by distribution/engine separation tests and real producer rejection/recovery.
- `drift/explorer_render.py`:
  `1b78f6ac1c10cb43d90009808b99deb6a211538a290ccf21872e771aa017f6ba` →
  `992d28705eaf4ccb0035016ac743b3a95955d0760851d54dd748503f456868d0`.
  Protected by the literal seven-statement oracle, predecessor HTML comparison,
  escaping/bounds/layout tests and exact source replay.
- `drift/explorer_bundle.py`:
  `06f2d8d9851e8a7323759d6d0440055c98f539c16701fb2e84f0f619e9bb2a0c` →
  `107c20d7d1eb3bf22c8b4f6184dda9de5fed4fdfec14161c5a77e89948b75ad4`.
  Protected by the explicit old/new/unknown revision matrix and retained adversarial
  bundle/publication/source-reproduction tests.
- `reporting.py`:
  `df801098089626078c2326e4ef9b4e86c8ec3c316fd81106f38046c4b5da41a4` →
  `1354cd77579e36911b59ab0618ee173fa687fff96ef410219d60d8d78136c85d`.
  Protected by ten new deterministic I/O cases, preserved reporting/security tests
  and exact predecessor native HTML/JSON/console output.

The verifier records predecessor and approved candidate hashes for each module,
and the complete unchanged inventory. Existing tests/fixtures and native schema
are independently read from predecessor Git, with only exact current-version
literal changes in `test_v141_identity.py` and `test_release_candidate.py`.
The former also sources its synthetic historical-verifier fixture from the
immutable published v1.4 source, rather than copying current development
metadata. This exact fixture-only adaptation preserves every original guard
and assertion; its full byte transformation is reviewed in V15 policy.
Analytical expectations and the original historical tools remain byte-identical.
Package project metadata permits exactly its distribution-version literal change.

Native reachability, deny precedence, intents, exposure, trace, witness,
comparison and resource rejection semantics remain unchanged. Unsupported or
resource-rejected evaluation never means successful unreachability. All seven
passive industrial subsets and malformed/truncated/unsupported distinctions
remain unchanged. Independent predecessor captures must match native HTML,
JSON, stdout, stderr and exits exactly; the report writer's source digest change
does not permit output differences.

## Producer and renderer boundaries

`evidence/revisions.py` binds 34 installed sources, including `__init__.py`.
The development distribution therefore creates a new analytical producer and
new revision identities despite unchanged native semantics. No old revision,
physical collection, baseline membership, review, approval or revocation is
rewritten. Old producer replay fails closed with `EVIDENCE_REVISION`; the original
regular runtime/source environment is the recovery path. New producer trust
requires new review. An interpretation change is not physical traffic change.

Renderer identity is `1.5.0.dev1-historical-explorer.1`; its installed five-file
source digest is independently checked. Old `1.4.0-historical-explorer.1` and `.2`
retain portable structural/integrity acceptance. Unknown revisions fail closed.
Portable integrity establishes neither analytical replay nor authenticated
approval. Old bundles remain unchanged and require their original compatible
runtime for exact replay. New bundles require the matching producer and renderer
for deterministic source reproduction. A rehashed false HTML claim can be
internally consistent and still fail source reproduction.

## Positive, negative and future policy

Positive verification binds checkout, regular installation, package metadata,
renderer digest and immutable native-output oracles. Negative tests reject
unauthorized edits/additions/removals, changed schema/expectations/oracle tools,
rehashed forged fixtures, unapproved renderer source, mismatched installation
and metadata. Existing adversarial bundle, producer and archive tests remain.

Future gates must add a separately versioned reviewed transition and independent
evidence. Do not update this gate's hashes to admit later changes. Unsupported
cross-producer replay has no universal migration guarantee. No published v1.4
tag/assets or historical verifier acceptance is reassigned to this candidate.
