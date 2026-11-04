# V15-03 compatibility — policy 1

Exact merged predecessor `a3cf2f2e226b7a0fe985816cbaafb6ec6527b2f5`,
tree `0e2c748edd6196a67a6cdee6f29b5aee639bb1a5`. The authorization boundary
is review of `tools/verify_v15_03_transition.py` and its literal SHA-256 policy;
candidate receipts are not signatures and cannot authorize themselves.

The two changed runtime modules are `__init__.py` (distribution 1.5.0.dev2) and
`capture/explorer.py` (honest navigation, detail pagination, focusable skip target).
All other 95 modules are exact predecessor bytes; no additions/removals/resources.
Native engine/alias 1.3.0, YAML schema 1, capture/drift analytical schemas unchanged.
Project metadata permits only the distribution-version literal replacement.

Historical renderer remains `1.5.0.dev1-historical-explorer.1`, digest
`442d13378cd61586664e19f51ea6834537b0155c07e48ff5a6173628c5d6ca6b`.
None of its five bound source files changes. A distribution version change is not
a renderer change. The seven V15-02 limitations and old bundle-version matrix stay.

`evidence/revisions.py` binds `__init__.py`; dev2 creates a distinct producer despite
unchanged analytical semantics. Old bundles remain portable-integrity verifiable;
dev2 must reject old source replay with EVIDENCE_REVISION. The original regular
dev1 environment recovers replay. Original revisions, baselines, approval/revocation
and files remain byte-identical. No approval transfers; source change is not traffic
change. New producer results require their own human review.

Authoritative entry is `python -I tools/verify_v15_03_transition.py --output NEW`.
It pins Git outside checkout, tree and entire runtime inventory, validates
protected predecessor tests/tools/schema, then checks regular installed metadata,
location and physical source bytes before import. Authenticated immutable old
policy helpers/comparator are compiled from Git bytes, avoiding mutable helpers
and cached bytecode. Fresh cache prefixes protect authoritative runtime imports.
Version assertions in two current tests and the defective capture current-page
assertion are the only permitted predecessor-test changes. Their transformation
or exact reviewed digest is explicit. Analytical oracles/fixtures are unchanged.

V15-02 verifier and its 30 test cases stay byte-identical and execute in an archived
merged predecessor with its regular dev1 installation. Current pytest explicitly
ignores that version-specific file; this is reported separately, never described as
the old verifier approving dev2. The unchanged old verifier in turn authenticates
its original V14/predecessor sources. Dev2 native capture must equal dev1 outputs
with zero allowed native module changes. Canonical PCAP JSON and identified evidence
text are independently compared against merged predecessor rendering.

Negative tests challenge unauthorized changed/unchanged modules, unknown resources,
missing sources, old policy/test/fixture/schema edits, self-rehashed fixtures,
forged installed metadata, pre-import malicious source, unchecked malicious pyc,
stdlib shadowing, wrong existing page/record links, duplicate/missing anchors,
pagination and omitted evidence. Published v1.4 references/assets remain untouched.
Future gates require another reviewed policy; these hashes must not be widened.
