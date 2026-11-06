# V15-06 — source and compatibility boundary

Merged V15-05 predecessor is dynamically verified PR #30 integration:
`7c5d6cb5c0efd6ee5946943bf8b83e12e98a9057`, tree
`e2c40a52a3f5d9370d2053474d9f2aab1d1463b4`.
The PR head is `9c4bb795a6ec1426aec4f902bd21e7b027148e6b`; it is not the
predecessor pin. Its six final-candidate jobs passed in run 42138952966.
Raw API merge/run/job evidence is `output/v15-06/preflight/github.json`.
The final PR head and merged predecessor have the same exact tree
`e2c40a52a3f5d9370d2053474d9f2aab1d1463b4`; `git diff` between them is empty.
Those six successful jobs therefore cover the integrated predecessor's source
bytes. The separate post-merge run 42143670810 is retained in
`preflight/merged-main-jobs.json`; its status is not substituted for candidate CI.

## Reviewed stable authorization

`tools/verify_v15_06_transition.py`, policy `V15-06.1`, authenticates the exact
Git predecessor/tree, reconstructs its 97-module inventory and authorizes only
the reviewed SHA-256 of `__init__.py`. That module changes solely
`DISTRIBUTION_VERSION = "1.5.0.dev3"` to `"1.5.0"`. The other 96 modules,
native engine `1.3.0`, legacy version API, YAML schema `1`, evidence schemas and
resource limits remain byte-identical. Project metadata and two current-version
test literals receive only that exact version substitution.

Every pre-existing test/tool except the explicit public-file inventory and those
two assertions remains authenticated against Git. In particular V15-04/V15-03/
V15-02 verifiers, their negative tests, native comparator, frozen capture fixtures
and YAML schema document are unchanged. CI's exact reviewed hash is separately
pinned; its six OS/Python jobs and offline/history requirements remain present.
CI authorizes stable source using V15-06 and executes old suites only in their
matching archived environments.

Regular installed source is hashed before candidate import. Isolated entry and
a fresh bytecode prefix prevent checkout shadowing and stale/malicious `.pyc`
execution. Missing/extra modules/resources, changed source, altered protected
evidence, forged native manifests/artifacts, malformed/duplicate metadata,
forged entry points/dependencies and editable installs are rejected. The policy
is reviewed authorization, not a cryptographic authorship signature; a receipt
cannot authorize the source that generated it.

The v1.5 assembler also reuses predecessor checkout/audit/assembly primitives by
compiling authenticated Git bytes directly. Protected mutable helper source or
unchecked helper bytecode cannot run before its source check. Positive/negative
cache-injection controls verify that boundary; the original v1.4 tool is intact.
Invoke the assembler as `python -I tools/prepare_v15_release.py`; nonisolated
entry is rejected. Its reviewed V15-06 policy is also compiled directly from
source, avoiding both policy and predecessor helper caches.

## Analytical and historical evidence

Full verification installs the merged predecessor in an archived dev3 environment
and runs unchanged V15-04 authorization and its tests. That policy recursively
executes V15-03, V15-02 and immutable native-v1.2/v1.4 compatibility references.
The stable candidate's native capture is compared to the independently executed
predecessor capture: artifact inventories, input hashes, exits and source maps
must match; every analytical artifact must be `EXACT_BYTES`. No analytical source
exception is allowed. Frozen capture/evidence/protocol fixtures are unchanged.

Changing `__init__.py` creates a distinct source-bound historical producer.
The full transition creates a fictional dev3 workspace and Explorer, verifies its
portable integrity with stable code, expects stable lifecycle replay rejection
`EVIDENCE_REVISION`, and recovers analytical reproduction with original dev3.
Workspace/source references, baselines, approvals and site bytes must retain
their complete original hash inventory. Approval transfer is false. This proves
the tested old→new boundary; it does not infer changed physical traffic.

All five renderer-bound modules remain byte-identical. Historical renderer stays
`1.5.0.dev1-historical-explorer.1`, digest
`442d13378cd61586664e19f51ea6834537b0155c07e48ff5a6173628c5d6ca6b`.
The seven Historical Explorer limitations and recorded/current approval
distinction remain intact. Portable integrity does not authenticate authorship
or establish compatible-source analytical reproduction.

Results and raw commands: `output/v15-06/compatibility/verified/transition.json`,
`commands.json`, `command-*.stdout`/`.stderr`, `historical-tests.xml` and recursive
`v15-04/v15-03/v15-02/` receipts. Final source/installed policy is separately
rechecked after the final documentation freeze; see [acceptance](v15-06-acceptance.md).
