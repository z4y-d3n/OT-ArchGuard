# Offline historical evidence comparison

V14-03 compares an explicitly approved historical baseline with selected analytical
revisions. It describes declared models, finite captured communications and
analytical interpretation independently. Missing traffic does not prove blocking
or outage. The [technical contract](development/v14-drift-contract.md) defines
comparability, source authority, report reproduction and resource ceilings.

Run the complete fictional example with a regular installed package:

```text
python -m tools.drift_walkthrough --output output/my-drift-walkthrough
```

The demonstration creates an invented controller/HMI/engineering segment, two
independent packet collections, native models, independently reviewed mappings,
analytical revisions and a fictional approved baseline. The candidate retains
one relationship, adds an unresolved endpoint relationship, omits one reference
relationship and changes a bounded Modbus header category and declared policy.
It verifies deterministic reproduction, incomplete coverage, decoder reinterpretation
of the same capture and revocation without modifying the earlier report.
All reviewer labels and packets are fictional; no network access is needed.

For your own existing workspace-v2, choose exact identities using `evidence list`,
`evidence revision list` and `evidence baseline show`. Supply an explicit context:

```json
{
  "context_version": 1,
  "pairs": [{
    "reference_analysis_id": "analysis-<exact reference digest>",
    "candidate_analysis_id": "analysis-<exact candidate digest>",
    "candidate_scope": {
      "environment": "Declared environment",
      "purpose": "Comparison purpose",
      "coverage": "Finite capture; continuous monitoring unknown",
      "uncertainties": ["Packet loss unknown"],
      "vantage_points": ["Owner asserted sensor label"],
      "protocols": ["modbus_tcp"]
    },
    "alignment": "asserted",
    "rationale": "Explicitly reviewed correspondence of these selected collections",
    "native_queries": [{"source_asset_id": "eng", "service_id": "svc_plc"}]
  }]
}
```

Scope lists must be unique and sorted. Reference scope comes from the exact approved
baseline. `alignment: "unresolved"` retains uncertainty. Unpaired selected sources
are reported separately; the engine never guesses correspondence. Query lists can
be empty. Exact native IDs must exist with equivalent definitions for paired
evaluation. Candidate assertions do not authenticate sensor or device identity.

```text
otarchguard evidence drift compare WORKSPACE BASELINE_ID --candidate CANDIDATE_ID --context context.json --output drift.json --mode qualified --text
otarchguard evidence drift inspect WORKSPACE drift.json
otarchguard evidence drift verify WORKSPACE drift.json
otarchguard evidence drift summarize WORKSPACE drift.json
```

Repeat `--candidate` and `--reference` to select multiple exact members. Omitting
`--reference` selects every member of that explicit baseline. Pair alignment is
one-to-one; multiple interpretations of one capture cannot inflate collection
counts. For an architecture baseline select `--candidate-model ATTACHMENT_ID`;
the reference is the baseline's exact model attachment. Reports must be fresh
JSON files outside the workspace; an existing destination is never replaced.

`strict` requires equivalent supported communication scope/coverage and complete
alignment. `qualified` retains partial differences and limitations. `descriptive`
labels finite dataset descriptions. Unsupported protocol/model domains still
abstain; no mode supplies missing evidence or bypasses source validation.

Communication rows include unchanged support as `OBSERVED_IN_BOTH`; native query
rows can include `REACHABILITY_UNCHANGED`. They are not new changes. Counts are
raw finite-capture counts. Protocol category recognition does not establish
successful commands, authorization or an incident. Declared model changes do not
establish deployed changes. Exact rational timestamps describe observed bounds,
with unknown clock synchronization and coverage between packets.

Verification requires the original metadata dependencies and supported comparison
implementation. It recomputes all findings and the canonical identity. A later
revoked/superseded baseline can leave a reproducible historical report while
`currently_approved_reference` becomes false. Fresh comparison requires current
approval. Reports and reviews are integrity-bound local assertions, without
authenticated authorship, creation time or sensor identity.
