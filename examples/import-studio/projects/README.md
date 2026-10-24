# Fictional multi-source onboarding

The `mixed` directory contains only invented industrial data: an engineering
workstation, PLC, HMI, historian, firewall label, switch, two zones and interfaces.
CSV, XLSX and draw.io disagree about the engineering workstation's zone. None
of these documents supplies network permission. The native model context declares
no transport, forwarding, rules or services.

Use an installed 1.2.0.dev0 console. Copy `mixed` to a writable working directory
and run these commands from inside that copy. Every output must have a new name.

1. Inspect `project.json`. It registers four explicit source paths, each adapter
   and profile, `context.json`, and a preferred zone evidence suggestion. For a
   new project use `otarchguard import project init --output my-project.json`,
   then register your own local files and profiles there.

2. Inspect and preview all registered sources together:

   ```text
   otarchguard import project inspect project.json
   otarchguard import project preview project.json
   otarchguard import project map project.json --output draft.json
   otarchguard import project review draft.json --decisions decisions.json --report review.md
   ```

3. Read `review.md`. It lists the contradictory zone claim first and proposes
   same-ID/name relationships without accepting any of them. Copy a group ID from
   the report for `otarchguard import project review draft.json --group GROUP_ID`.

4. Compare `decisions.json` with `tutorial-decisions.json`. The latter contains
   explicit choices made by a fictional owner for these exact synthetic bytes.
   Same-entity partitions list all contributing qualified members. The selected
   `zone_id` field points to the workbook observation. All conflicting originals
   remain in evidence. Separate partitions with different final IDs would mean
   keep separate. `OWNER_REJECTED` rejects a partition; `EVIDENCE_ONLY` retains it
   outside declarations. A real project requires your engineering decisions.

   To resolve one selected entity from the CLI instead of editing its partition,
   repeat `--member` with the exact candidate IDs shown in the report:

   ```text
   otarchguard import project resolve draft.json --decisions decisions.json --member QUALIFIED_ID_1 --member QUALIFIED_ID_2 --canonical-id my_plc --reviewer "Owner" --rationale "Reviewed these observations as one device" --output resolved.json
   ```

   Add `--field-source zone_id=QUALIFIED_ID` for a selected conflicting observation,
   `--set name=CorrectedName` for a literal correction, or
   `--reference zone_id=QUALIFIED_ZONE_ID` for an explicitly reviewed renamed target.
   This command resets whole-model confirmation. It never confirms other entities.

5. Acknowledge the drawing's five connectors in one explicit operation:

   ```text
   otarchguard import project acknowledge draft.json --decisions decisions.json --source topology --reviewer "Synthetic owner" --rationale "Keep documentary connectors as evidence only" --output acknowledged.json
   ```

   The response and decision file disclose every connector ID and the exact set
   digest. All entities and `model_confirmed` remain unresolved. Trying to emit
   this file fails. There is no traffic authorization or accept-all shortcut.

6. For this tutorial only, inspect the completed fictional owner choices and emit:

   ```text
   otarchguard import project emit draft.json --project project.json --decisions tutorial-decisions.json --output accepted
   otarchguard validate accepted/architecture.yaml
   ```

   For a real project, complete your own partitions, final canonical IDs,
   field/reference corrections and conflict rationales in the decisions file;
   set the named reviewer, `model_confirmed: true`, and model rationale only after
   reviewing all declarations and the hash-bound native context. Then emit using
   that file. A source/profile/context mutation invalidates previous confirmation.

7. Inspect `accepted/architecture.provenance.json`: `catalog.sources` retains each
   original observation/profile/location, `identity_index` maps observations to
   the six final assets, `decisions` explains identity and field resolutions, and
   `declarations` records exact accepted fields. Connector graphs remain evidence.
   The sidecar's model hash is the native validator's model identity. Native schema
   validity establishes declared consistency, not real-world network completeness.

The development tool `python -m tools.project_walkthrough --output output/tutorial`
executes these installed-console steps from a separate copied working directory,
also proving unresolved review, stale source and overwrite refusal. Regenerate
the fictional fixture with `python -m tools.synthetic_projects NEW_DIRECTORY`.
That tool creates explicit tutorial decisions only for its known fictional scenario;
the application has no generic approval generator.
