"""Version-1 finite-evidence comparability, separate from source validation.

Inputs are privately owned lifecycle-validated records. Equal declarations are
comparison assertions, never authentication of sensors, clocks or asset owners.
"""

from fractions import Fraction
from typing import Any

from otarchguard.drift.contract import Budget, Side, finding, source
from otarchguard.evidence.attachments import canonical


def observation_semantics(side: Side) -> dict[str, Any]:
    """Fields that govern frozen communication metadata, excluding enrichment."""
    semantics = side.analysis["producer_semantics"]
    return {
        name: semantics[name]
        for name in ("observation_version", "capture_version", "catalog_version", "parser_mode")
    } | {
        "implementation_sha256": {
            name: sha
            for name, sha in semantics["implementation_sha256"].items()
            if name
            in {
                "capture/contract.py",
                "capture/parser.py",
                "capture/observations.py",
                "evidence/observations.py",
                "evidence/workspace.py",
            }
        },
        "capture_validation_limits": semantics["capture_validation_limits"],
    }


def protocol_equivalent(reference: Side, candidate: Side) -> bool:
    """No implicit equivalence across decoder revisions, inventories or limits."""
    first, second = reference.attachments.get("enrichment"), candidate.attachments.get("enrichment")
    if first is None or second is None:
        return False
    fields = ("enrichment_version", "decoder_version", "supported_protocols", "limits")
    a, b = first["payload"], second["payload"]
    semantics_a, semantics_b = (
        reference.analysis["producer_semantics"],
        candidate.analysis["producer_semantics"],
    )
    return (
        all(canonical(a[name]) == canonical(b[name]) for name in fields)
        and observation_semantics(reference) == observation_semantics(candidate)
        and semantics_a["implementation_sha256"] == semantics_b["implementation_sha256"]
        and semantics_a["enrichment_validation_limits"]
        == semantics_b["enrichment_validation_limits"]
    )


def _worst(states: list[str]) -> str:
    for state in ("INCOMPARABLE", "INDETERMINATE", "PARTIALLY_COMPARABLE"):
        if state in states:
            return state
    return "COMPARABLE"


def assess(
    reference: Side,
    candidate: Side,
    reference_scope: dict[str, Any],
    candidate_scope: dict[str, Any],
    alignment: str,
    budget: Budget,
) -> dict[str, Any]:
    """Assess supported dimensions without granting authority to their labels."""
    observations = [s.snapshot["observations"] for s in (reference, candidate)]
    coverages = [o["coverage"] for o in observations]
    collections = [s.snapshot["collection"] for s in (reference, candidate)]
    dimensions: list[dict[str, Any]] = []
    evidence = [source(reference), source(candidate)]

    def add(name: str, result: str, values: object, reason: str, consequence: str) -> str:
        budget.charge("work_units")
        dimensions.append(
            {
                "dimension": name,
                "result": result,
                "source_evidence": {"sources": evidence, "values": values},
                "reason": reason,
                "consequence": consequence,
            }
        )
        return result

    independent = reference.analysis["capture_sha256"] != candidate.analysis["capture_sha256"]
    add(
        "physical_collection",
        "COMPARABLE",
        [s.analysis["capture_sha256"] for s in (reference, candidate)],
        "Distinct imported capture identities."
        if independent
        else "The same physical collection is selected twice.",
        ("Distinct identities do not prove independent sensors or authentic collection.")
        if independent
        else (
            "Differences are interpretations of the same collection, not independent observation."
        ),
    )
    add(
        "analytical_revision",
        "COMPARABLE",
        [s.analysis["analysis_id"] for s in (reference, candidate)],
        (
            "Exact validated revisions are selected; revision identity is "
            "separate from collection identity."
        ),
        "Candidate interpretation does not inherit the reference baseline approval.",
    )
    semantic_state = add(
        "producer_semantics",
        "COMPARABLE"
        if observation_semantics(reference) == observation_semantics(candidate)
        else "INCOMPARABLE",
        [s.analysis["producer_semantics_sha256"] for s in (reference, candidate)],
        (
            "Frozen observation parser/consumer versions, sources, mode and "
            "limits are compared explicitly."
        ),
        (
            "Enrichment revisions and analysis options are assessed separately; "
            "original producer provenance is unknown."
        ),
    )
    complete = all(
        o["coverage"]["complete_file_scan"] is True and o["capture"]["unknown_blocks"] == 0
        for o in observations
    )
    container_state = add(
        "container_completeness",
        "COMPARABLE" if complete else "PARTIALLY_COMPARABLE",
        [
            {
                "complete_file_scan": o["coverage"]["complete_file_scan"],
                "unknown_blocks": o["capture"]["unknown_blocks"],
            }
            for o in observations
        ],
        "Container scan completeness is a finite-file property.",
        ("Full file parsing never establishes continuous monitoring or full network visibility."),
    )
    interpretation_state = add(
        "packet_interpretation",
        "COMPARABLE"
        if all(c["uninterpreted_packets"] == 0 for c in coverages)
        else "PARTIALLY_COMPARABLE",
        [
            {name: c[name] for name in ("packets", "interpreted_packets", "uninterpreted_packets")}
            for c in coverages
        ],
        "Raw interpreted and uninterpreted packet denominators are retained.",
        (
            "Uninterpreted bytes may contain relevant communications; no "
            "operational absence conclusion is allowed."
        ),
    )
    framing_state = add(
        "fragmentation_and_truncation",
        "COMPARABLE"
        if all(
            c[name] == 0
            for c in coverages
            for name in ("fragmented", "truncated", "malformed", "capture_records_truncated")
        )
        else "PARTIALLY_COMPARABLE",
        [
            {
                name: c[name]
                for name in ("fragmented", "truncated", "malformed", "capture_records_truncated")
            }
            for c in coverages
        ],
        "Fragmented, truncated and malformed evidence remains explicitly unassessed.",
        ("No stream reconstruction or successful connection/command execution is inferred."),
    )
    linktypes = [sorted({i["linktype"] for i in o["capture"]["interfaces"]}) for o in observations]
    linktype_state = add(
        "linktypes",
        "COMPARABLE"
        if all(set(values) <= {1, 101} for values in linktypes)
        else "PARTIALLY_COMPARABLE",
        linktypes,
        "Frozen observation decoding supports Ethernet 1 and raw IP 101.",
        "Unsupported linktypes cannot provide negative communication evidence.",
    )
    timestamps_known = all(
        c["first_timestamp"] is not None and c["missing_timestamps"] == 0 for c in collections
    )
    order = "INDETERMINATE"
    if not independent:
        order = "SAME_COLLECTION"
    elif timestamps_known:
        if Fraction(collections[0]["last_timestamp"]) < Fraction(collections[1]["first_timestamp"]):
            order = "CANDIDATE_WINDOW_AFTER_REFERENCE"
        elif Fraction(collections[1]["last_timestamp"]) < Fraction(
            collections[0]["first_timestamp"]
        ):
            order = "CANDIDATE_WINDOW_BEFORE_REFERENCE"
        else:
            order = "OVERLAPPING_WINDOWS"
    add(
        "timestamps",
        "PARTIALLY_COMPARABLE" if timestamps_known else "INDETERMINATE",
        collections,
        (
            "Exact rational observed bounds are compared; packet ordering and "
            "synchronized clocks are unattested."
        ),
        (
            "Bounds do not establish continuous exposure, missing-coverage "
            "intervals, rates or operational trends."
        ),
    )
    scope_state = add(
        "observation_scope",
        "INCOMPARABLE"
        if reference_scope["environment"] != candidate_scope["environment"]
        else "COMPARABLE"
        if all(
            reference_scope[k] == candidate_scope[k]
            for k in ("purpose", "coverage", "uncertainties")
        )
        and not reference_scope["uncertainties"]
        else "PARTIALLY_COMPARABLE",
        [reference_scope, candidate_scope],
        ("Exact declared environment, purpose, coverage and uncertainties are compared."),
        ("Matching text is an explicit comparison assertion, not measured sensor coverage."),
    )
    vantage_state = add(
        "vantage_points",
        "INDETERMINATE"
        if not reference_scope["vantage_points"] or not candidate_scope["vantage_points"]
        else "COMPARABLE"
        if reference_scope["vantage_points"] == candidate_scope["vantage_points"]
        else "INCOMPARABLE",
        [reference_scope["vantage_points"], candidate_scope["vantage_points"]],
        (
            "Declared vantage points must be explicit and equivalent for strict "
            "communication comparison."
        ),
        (
            "Different vantage points may reveal different traffic without an "
            "infrastructure change; labels do not authenticate sensors."
        ),
    )
    visibility_state = add(
        "protocol_visibility",
        "INDETERMINATE"
        if not reference_scope["protocols"] or not candidate_scope["protocols"]
        else "COMPARABLE"
        if reference_scope["protocols"] == candidate_scope["protocols"]
        else "PARTIALLY_COMPARABLE",
        [reference_scope["protocols"], candidate_scope["protocols"]],
        ("Protocol visibility is explicitly declared rather than inferred from absent records."),
        ("An unrecognized or unobserved protocol is not proven absent from the network."),
    )
    alignment_state = add(
        "collection_alignment",
        "COMPARABLE" if alignment == "asserted" else "INDETERMINATE",
        alignment,
        "Alignment is an explicit user-selected comparison assertion.",
        ("Unresolved collection alignment permits descriptive finite-dataset differences only."),
    )
    models = [s.attachments.get("model") for s in (reference, candidate)]
    first_model, second_model = models
    same_model = (
        first_model is not None
        and second_model is not None
        and first_model["component_sha256"] == second_model["component_sha256"]
    )
    add(
        "architecture_model",
        "COMPARABLE" if same_model else "PARTIALLY_COMPARABLE" if all(models) else "INDETERMINATE",
        [m["component_sha256"] if m else None for m in models],
        ("Validated canonical model identities are compared separately from observed evidence."),
        (
            "Different models describe declared semantics; they do not prove "
            "deployment changes or physical identity continuity."
        ),
    )
    mappings = [s.attachments.get("mapping") for s in (reference, candidate)]
    asset_state = "PARTIALLY_COMPARABLE" if same_model and all(mappings) else "INDETERMINATE"
    add(
        "reviewed_associations",
        asset_state,
        [m["attachment_id"] if m else None for m in mappings],
        (
            "Asset views require independently ACCEPTed decisions on both sides "
            "and the exact same model identity."
        ),
        (
            "Pending decisions and missing or changed models leave asset "
            "continuity unresolved; equal IP/MAC addresses are insufficient."
        ),
    )
    add(
        "provenance",
        "INDETERMINATE",
        [
            s.analysis["producer_semantics"]["original_producer_provenance"]
            for s in (reference, candidate)
        ],
        (
            "Lifecycle validation establishes structural integrity and supported "
            "joins, not original-capture authenticity."
        ),
        (
            "Sensor identity, device ownership, clock synchronization and "
            "reviewer authority remain unauthenticated assertions."
        ),
    )
    add(
        "baseline_scope",
        "COMPARABLE",
        reference_scope,
        (
            "The reference scope is the exact selected baseline scope; approval "
            "is validated by the caller."
        ),
        (
            "Reference authority applies only to exact approved membership and "
            "scope; no candidate approval is inherited."
        ),
    )
    communication_state = _worst(
        [
            semantic_state,
            container_state,
            interpretation_state,
            framing_state,
            linktype_state,
            scope_state,
            vantage_state,
            visibility_state,
            alignment_state,
        ]
    )
    protocol_state = (
        communication_state if protocol_equivalent(reference, candidate) else "INDETERMINATE"
    )
    add(
        "protocol_decoder",
        protocol_state,
        [
            {
                "selected_semantics": {
                    name: s.analysis["producer_semantics"][name]
                    for name in (
                        "enrichment_version",
                        "decoder_version",
                        "selected_enrichment_limits",
                    )
                },
                "capture_packets": s.snapshot["observations"]["capture"]["packets"],
                "enrichment_accounting": {
                    name: s.attachments["enrichment"]["payload"][name]
                    for name in (
                        "counts",
                        "skipped_packets",
                        "packets_with_records",
                        "limits",
                        "supported_protocols",
                    )
                }
                if "enrichment" in s.attachments
                else None,
            }
            for s in (reference, candidate)
        ],
        (
            "Protocol metadata requires equivalent schema, decoder, inventory, "
            "limits and selected consumer semantics."
        ),
        (
            "Decoder differences are analytical interpretation differences, never "
            "proof of changed industrial traffic."
        ),
    )
    return {
        "overall": _worst([d["result"] for d in dimensions]),
        "dimensions": dimensions,
        "communication_metadata": communication_state,
        "protocol_metadata": protocol_state,
        "asset_continuity": asset_state,
        "temporal_order": order,
        "independent_collections": independent,
        "limitations": [
            (
                "An absent observation never proves traffic absence, blocking, outage "
                "or device removal."
            ),
            ("Collection windows are observed bounds with unattested clocks and unknown gaps."),
            (
                "Counts are raw finite-capture counts; no exposure-normalized "
                "activity is calculated."
            ),
            "Matching scope and vantage labels are unauthenticated comparison assertions.",
        ],
    }


def compare_coverage(reference: Side, candidate: Side, budget: Budget) -> list[dict[str, Any]]:
    "Expose changed raw coverage and observed bounds without inventing exposure."

    def summary(side: Side) -> dict[str, Any]:
        observations = side.snapshot["observations"]
        return {
            "source": source(side),
            "coverage": observations["coverage"],
            "unknown_capture_blocks": observations["capture"]["unknown_blocks"],
            "interfaces": observations["capture"]["interfaces"],
            "collection": side.snapshot["collection"],
        }

    first, second = summary(reference), summary(candidate)
    compared = ("coverage", "unknown_capture_blocks", "interfaces", "collection")
    budget.charge("work_units", len(compared))
    changed = [name for name in compared if canonical(first[name]) != canonical(second[name])]
    if not changed:
        return []
    return [
        finding(
            "COVERAGE_DIFFERENCE",
            "CAPTURE_COVERAGE_CHANGED",
            {"changed_dimensions": changed},
            first,
            second,
            "PARTIALLY_COMPARABLE",
            (
                "Raw packet coverage, interface context or observed timestamp bounds "
                "differ between selected finite datasets; operational absence "
                "assessment is withheld."
            ),
            budget,
            [
                (
                    "A complete file scan is not proof of complete sensor visibility or "
                    "continuous monitoring."
                ),
                (
                    "Observed bounds and raw counts do not establish exposure, packet "
                    "loss, activity rates or operational trends."
                ),
                (
                    "Unobserved communication is not proven absent or blocked; no device "
                    "outage or removal is inferred."
                ),
            ],
        )
    ]
