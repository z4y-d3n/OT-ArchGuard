# V14-06 contract freeze and acceptance inventory

Parent `ac893bc3174f0a7ace67454d19ad6e61116425af`; immutable starting identities
are in [baseline](v14-06-baseline.json). The only permitted production delta is
the exact distribution literal in `__init__.py`: `1.4.0.dev1` to `1.4.0`.
Native engine and historical `__version__` remain `1.3.0`. The other 96 Python
modules, all renderers and all schema implementations retain their parent bytes.

## Common contracts

Canonical JSON uses each subsystem's existing sorted serialization and exact
type rules. Snapshot, attachment, analysis, baseline, review and bundle identities
bind their documented canonical envelopes and content hashes; they are not
interchangeable. Source bytes and module inventories are compared independently
with Git objects and package members. See the source implementations and the
[native](v14-06-native-audit.md), [pipeline](v14-06-pipeline-audit.md) and
[security](v14-06-security-audit.md) audits for independently checked examples.

Each subsystem retains its existing finite byte, count, nesting, work or output
ceilings, recorded in `contract.py`, `capture/contract.py`,
`capture/protocols/contract.py`, ingestion budgets and historical/drift limits.
An exhausted ceiling is a resource error, never an unreachable/negative result.
No ceiling or format version is increased for this milestone. Single-writer
local publication and regular local paths remain assumptions; hostile concurrent
administrators and universal crash durability are outside the contract.

## Producers, consumers and version boundaries

| Contract | Producer → consumer; identity | Supported / unsupported boundary | Publication, verification and compatibility |
|---|---|---|---|
| Native YAML schema 1 | loading/API → graph, policy, reachability, intents; canonical model SHA | Explicit declared IPv4 TCP/UDP architecture, exact inclusive ports; unsupported scope aborts | Frozen v1.2 schema/contract, native engine 1.3.0; no package-version substitution in evidence |
| Native reports and trace 1 | native evaluators → JSON/HTML/read-only consumers; model/query/witness identities | Structural versus permitted path; independent required/prohibited outcomes; declared initiation only | Exact analytical artifacts and HTML JSON appendices; immutable v1.2 and approved V14-04 references |
| Import Studio versions 1–5 | supported tabular/structured/graphical/document adapters → draft/review/reconciliation/Explorer | Bounded metadata extraction, explicit profile, source provenance and review; no Office execution or inferred operational truth | Profiles 1–4 and graphical/document subsets 1 remain unchanged; safe inert output, conflicts require review |
| Capture 1 / observations 2 / catalog 1 | bounded PCAP/PCAPNG parser → evidence Studio, reconciliation, historical collections | Supported Ethernet/VLAN/IP metadata; NULL/SLL unsupported, no TCP reassembly or success inference | Frozen capture consumers and deterministic evidence; partial capture never proves absence |
| Association / native comparison 1 | reviewed endpoint mapping → conservative native reconciliation | Only eligible explicitly reviewed IPv4 TCP initiation scope; port hints and observed SYNs are qualified | Source/model/evidence hashes bind review; declared reachability does not establish deployed authorization |
| Enrichment 1 / decoder 2 | seven bounded header decoders → historical revisions/drift/Explorer | Modbus, DCP, ENIP/limited CIP, classic S7, IEC104, OPC UA Binary, DNP3/TCP; unsupported/truncated abstention | Exact original-packet reproduction where available; limits/decoder mismatch means reinterpretation; no private process values or command-success claim |
| Workspace 1 / snapshot 1 | capture observations → physical collection storage | Canonical capture/label identities; no analysis/approval implied | Existing v1 observation storage remains verifiable; documented v1 import into v2 does not invent producer provenance |
| Workspace 2 / attachment 1 | history + validated attachments → complete lifecycle dependency graph | Explicit model/mapping/comparison/enrichment dependencies; missing even unselected dependencies can reject fresh interpretation | Content-addressed objects, bounded reads and exact dependency checks; single writer |
| Analysis 1 / semantics 1 | exact selected producer source + limits + components → baseline/drift | New interpretation differs from physical collection; unknown implementation is unsupported | Exact selected source hashes include `__init__.py`; dev1 revisions require retained dev1 environment. No automatic rehash/migration |
| Baseline/review 1 | exact membership/scope + local review records → current-authority checks | Human reviewer names unauthenticated; modified analyses cannot inherit approval | Recorded review facts retained; current authority freshly checks supersession/revocation; no ownership authentication claim |
| Drift 1 / comparability policy 1 | baseline, candidates, coverage, context → historical findings | Observed differences, source comparability, native scope equivalence; no physical-change inference from decoder mismatch | Canonical source-dependent replay; forged rehashed evidence and missing dependencies reject |
| Historical Explorer 1 | source-verified drift → static bundle + portable verifier | Explicit recorded versus current approval; sensitive evidence remains sensitive | Exact file inventory/hash/link/markup checks; portable integrity does not prove source replay or current approval |
| Architecture Explorer 2 / semantic HTML | frozen renderers → offline user inspection | Inert HTML/CSS/SVG, explicit labels, accessible tables and local evidence links | Previous owner visual acceptance retained as prior evidence; unchanged renderer bytes plus exact presentation reproduction; no new zoom/browser claim |
| Package / CLI 1.4.0 | reviewed committed source → wheel/sdist/install | Python >=3.12 metadata; actual local 3.12/3.14 and six hosted target configurations distinguished | Strict package inventories, unique metadata, regular installed modules; local preparation is separate from hosted/main/publication acceptance |

## Deliberate version transition

The historical verifier derives candidate module hashes from the immutable
approved presentation source `117318393ead604a023a24bad7d53eb429faa13f` by
one exact token replacement. It checks the full 97-module checkout and installed
inventory, native version, distribution metadata and regular package location.
The approved package is installed separately without modification. Captures bind
their respective source hashes while canonical results and all thirteen approved
HTML outputs remain exact. The v1.2 reference remains
`f52c792b683cb499dc7de765b65b5cc897a96854`.

The historical test exception advances only its exact distribution assertion;
all original engine/API and presentation exceptions remain bounded. Rehashed
forged manifests, unauthorized test edits, source/reference substitutions, module
additions/deletions, altered engine/results/HTML and installed/source mismatches
are rejected by the combined existing and V14-06 adversarial suites.

The new distribution changes historical exact-source analysis identity. This is
disclosed as V146-B01, with preserved development environments and fresh stable
workspaces/revisions/review. Native byte compatibility does not imply analysis-ID
or cross-producer workspace compatibility.
