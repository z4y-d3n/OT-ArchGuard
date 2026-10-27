# Historical evidence and explicit baseline review

This development workflow is offline. It preserves one physical collection for
each exact capture SHA, several immutable analytical interpretations, and
separate local human assertions. It does not perform historical drift analysis.
See the [versioned contracts and trust limits](development/v14-history-contract.md).

## Migrate without changing the source

```console
otarchguard evidence verify legacy-workspace
otarchguard evidence migrate legacy-workspace history-workspace
otarchguard evidence verify legacy-workspace
otarchguard evidence verify history-workspace
otarchguard evidence list history-workspace
```

The destination must be new. Existing snapshots retain their exact original
bytes, IDs, labels, observation hashes and capture identities. Migration creates
no analyses or approvals. Failed destinations remain uncommitted for manual
inspection; preserve or quarantine them and retry into another fresh path.

For new work, explicitly initialize version 2 and add validated observations:

```console
otarchguard evidence init history-workspace --version 2
otarchguard evidence add history-workspace observations.json --label "Reviewed period label"
```

The default `evidence init` still creates a v1 workspace. List output separates
physical collections from analytical revisions; labels have no review authority.

## Select exact analytical inputs

Use exact IDs returned by preceding commands in place of uppercase placeholders:

```console
otarchguard evidence attach history-workspace SNAPSHOT_ID enrichment protocol-enrichment.json
otarchguard evidence revision create history-workspace SNAPSHOT_ID --enrichment ENRICHMENT_ATTACHMENT_ID
otarchguard evidence attach history-workspace SNAPSHOT_ID model architecture.yaml
otarchguard evidence attach history-workspace SNAPSHOT_ID mapping associations.json --model MODEL_ATTACHMENT_ID
otarchguard evidence attach history-workspace SNAPSHOT_ID comparison comparison.json --model MODEL_ATTACHMENT_ID --mapping MAPPING_ATTACHMENT_ID
otarchguard evidence revision create history-workspace SNAPSHOT_ID --enrichment ENRICHMENT_ATTACHMENT_ID --model MODEL_ATTACHMENT_ID --mapping MAPPING_ATTACHMENT_ID --comparison COMPARISON_ATTACHMENT_ID
otarchguard evidence revision list history-workspace --capture CAPTURE_SHA256
otarchguard evidence revision show history-workspace ANALYSIS_ID
```

Observations are always present through the preserved collection. All four
additional components are optional until required by a selected dependency;
comparison requires model and reviewed mapping. Each component is validated
through its native contract. A model with no reviewed mapping is allowed and
does not assert physical address ownership. An enrichment null observation
binding is preserved honestly. Different supported decoder revisions, models
or enforced analytical options produce different analyses of the same capture.

The default producer-semantics manifest is returned inside each analysis. To
choose stricter supported options, save that manifest, change only
`analysis_options.require_complete_scan` and/or
`analysis_options.require_reviewed_mapping` to true, and pass it with
`revision create ... --semantics semantics.json`. The conditions are enforced.
Arbitrary parser modes, altered implementation hashes and unsupported limits
are rejected. Original capture-processing provenance remains unattested when
the frozen imported observations do not provide it.

## Propose, inspect and explicitly decide

Save a bounded scope document, for example this entirely fictional assertion:

```json
{
  "environment": "Fictional training site",
  "purpose": "Reference for future offline comparison",
  "coverage": "Only selected packets; loss and continuous visibility unknown",
  "uncertainties": ["No production deployment or complete visibility asserted"],
  "vantage_points": [],
  "protocols": []
}
```

```console
otarchguard evidence baseline propose history-workspace scope.json --revision ANALYSIS_A --revision ANALYSIS_B
otarchguard evidence baseline review history-workspace BASELINE_ID --text
otarchguard evidence baseline approve history-workspace BASELINE_ID --reviewer "Fictional training reviewer" --rationale "Fictional exercise only"
otarchguard evidence baseline show history-workspace BASELINE_ID
otarchguard evidence baseline list history-workspace
```

Use `--kind architecture --model MODEL_ATTACHMENT_ID` for an architecture
baseline. Evidence baselines require at least one exact analysis and allow only
one interpretation per physical collection. Architecture baselines require a
validated model. Both may explicitly link model and evidence, without proving
that the deployed infrastructure matches the declaration.

A proposal is `PROPOSED`, never implicitly approved. Only the distinct approval
command records the human assertion. Reviewer labels are unauthenticated local
claims; they are not organizational authorization or digital signatures. The
examples above approve only fictional exercise inputs. Select and review real
evidence yourself before using the commands on an operational baseline.

For a changed interpretation, propose a different exact baseline under the same
scope, inspect it, and explicitly supersede or revoke the exact old approval:

```console
otarchguard evidence baseline supersede history-workspace NEW_BASELINE_ID --predecessor OLD_APPROVAL_REVIEW_ID --reviewer "Fictional training reviewer" --rationale "Select the fictional successor interpretation"
otarchguard evidence baseline revoke history-workspace NEW_BASELINE_ID --predecessor SUCCESSOR_REVIEW_ID --reviewer "Fictional training reviewer" --rationale "Withdraw fictional reference selection"
otarchguard evidence verify history-workspace
```

Original decisions remain inspectable. Supersession requires identical scope
and kind, one exact active predecessor and a different proposal. Changed scope
requires independent review. Contradictory active decisions fail closed.
Rejected/revoked exact baseline identities are terminal; a new selection needs
a distinct proposal. There is no mutable global current-baseline pointer.

## Reproduce the complete fictional acceptance scenario

After installing the current package, run from the source repository:

```console
python -m tools.evidence_history_walkthrough --output output/my-history-walkthrough
python -m benchmarks.evidence_history --output output/my-history-benchmark
```

Each output path must be new. The walkthrough generates two distinct synthetic
physical captures, migrates v1 snapshots byte-for-byte, selects multiple
interpretations of one capture, attaches an actual validated model, reviewed
mapping and native comparison, and proposes evidence/architecture baselines.
It exercises explicit fictional approval, supersession and revocation, negative
cross-capture/stale approval cases, and repeats the scenario to compare canonical
identities with an independent JSON/hash consumer. No third-party packet bytes,
downloads, devices or real owner approvals are needed.
