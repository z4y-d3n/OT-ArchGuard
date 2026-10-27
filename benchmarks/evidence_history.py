"""Finite synthetic historical-workspace measurements, without network traffic."""

import argparse
import json
import platform
import time
import tracemalloc
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any

from benchmarks.capture import process_peak_rss_bytes
from otarchguard.capture.observations import analyze_capture
from otarchguard.diagnostics import ModelError
from otarchguard.evidence.attachments import build_attachment
from otarchguard.evidence.history import (
    HISTORY_LIMITS,
    migrate_workspace,
    publish_object,
    read_history,
)
from otarchguard.evidence.lifecycle import (
    create_revision,
    list_history,
    list_revisions,
    load_state,
    propose_baseline,
    record_review,
    validate_state,
    verify_lifecycle,
)
from otarchguard.evidence.workspace import add_snapshot, initialize_workspace, serialize
from tools.capture_workloads import plant_model, write_pcap


def measure(name: str, operation: Callable[[], Any]) -> dict[str, Any]:
    tracemalloc.start()
    started = time.perf_counter()
    result = operation()
    elapsed = time.perf_counter() - started
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "name": name,
        "elapsed_seconds": elapsed,
        "traced_peak_bytes": peak,
        "process_peak_rss_bytes": process_peak_rss_bytes(),
        "result": result,
    }


def benchmark(output: Path, collections: int = 16, revisions: int = 16) -> dict[str, Any]:
    if not 2 <= collections <= 32 or not 2 <= revisions <= 32:
        raise ValueError("Finite benchmark requires 2..32 collections and revisions")
    output.mkdir(exist_ok=False)
    source = output / "legacy"
    initialize_workspace(source)
    for index in range(collections):
        capture = output / f"fictional-{index}.pcap"
        write_pcap(capture, count=index + 1)
        observations_path = output / f"observations-{index}.json"
        observations_path.write_bytes(serialize(analyze_capture(capture)))
        add_snapshot(source, observations_path, f"Fictional benchmark collection {index}")
    workspace = output / "history"
    results = [measure("migrate-many-snapshots", lambda: migrate_workspace(source, workspace))]
    state = read_history(workspace)
    selected = next(iter(state["snapshots"].values()))
    selected_id = selected["snapshot_id"]
    revision_ids: list[str] = []

    def append_revisions() -> dict[str, Any]:
        for index in range(revisions):
            model = plant_model()
            model["revision"] = f"finite_benchmark_{index}"
            attachment = build_attachment("model", model, selected)
            publish_object(workspace, "attachments", attachment, validate_state)
            revision = create_revision(workspace, selected_id, model=attachment["attachment_id"])
            revision_ids.append(revision["analysis"]["analysis_id"])
        return {"new_revisions_one_collection": len(revision_ids)}

    results.append(measure("attach-models-and-revise-one-collection", append_revisions))

    def cover_membership() -> dict[str, Any]:
        for snapshot in state["snapshots"].values():
            create_revision(workspace, snapshot["snapshot_id"])
        scope = {
            "environment": "Fictional finite benchmark",
            "purpose": "Performance measurement only",
            "coverage": "Generated packets only; wider visibility unknown",
            "uncertainties": ["No operational representativeness asserted"],
            "vantage_points": [],
            "protocols": [],
        }
        scope_path = output / "scope.json"
        scope_path.write_bytes(serialize(scope))
        validated = load_state(workspace)
        selected_members: dict[str, str] = {}
        for analysis in validated["analyses"].values():
            selected_members.setdefault(analysis["capture_sha256"], analysis["analysis_id"])
        result = propose_baseline(workspace, scope_path, list(selected_members.values()))
        return {"baseline_members": len(result["baseline"]["members"])}

    results.append(measure("baseline-membership-all-collections", cover_membership))

    def chain() -> dict[str, Any]:
        scope = json.loads((output / "scope.json").read_bytes())
        scope["purpose"] = "Finite fictional review chain"
        chain_scope = output / "chain-scope.json"
        chain_scope.write_bytes(serialize(scope))
        previous: str | None = None
        last_baseline = ""
        for index, revision_id in enumerate(revision_ids[:8]):
            proposal = propose_baseline(workspace, chain_scope, [revision_id])["baseline"]
            last_baseline = proposal["baseline_id"]
            action = "approve" if index == 0 else "supersede"
            review = record_review(
                workspace,
                last_baseline,
                action,
                "Fictional benchmark reviewer",
                "Synthetic measurement only",
                predecessor=previous,
            )["review"]
            previous = review["review_id"]
        assert previous is not None
        record_review(
            workspace,
            last_baseline,
            "revoke",
            "Fictional benchmark reviewer",
            "End finite benchmark",
            predecessor=previous,
        )
        verified = verify_lifecycle(workspace)
        return {"review_records": verified["reviews"], "chain_approvals": min(8, revisions)}

    results.append(measure("verify-approval-supersession-revocation-chain", chain))
    results.append(
        measure(
            "list-collections",
            lambda: {"collections": list_history(workspace)["physical_collections"]},
        )
    )
    results.append(
        measure("list-revisions", lambda: {"revisions": len(list_revisions(workspace)["analyses"])})
    )
    results.append(
        measure(
            "repeat-full-verification-three-times",
            lambda: [verify_lifecycle(workspace) for _ in range(3)],
        )
    )

    def invalid_reference() -> dict[str, Any]:
        try:
            propose_baseline(workspace, output / "scope.json", ["analysis-" + "f" * 64])
        except ModelError as error:
            return {"status": "rejected", "code": error.diagnostics[0].code}
        raise AssertionError("Invalid reference was accepted")

    def resource_rejection() -> dict[str, Any]:
        try:
            read_history(workspace, replace(HISTORY_LIMITS, analyses=1))
        except ModelError as error:
            return {"status": "rejected", "code": error.diagnostics[0].code}
        raise AssertionError("Resource ceiling did not reject excessive history")

    results.append(measure("invalid-reference-rejection", invalid_reference))
    results.append(measure("resource-ceiling-rejection", resource_rejection))
    files = [p for p in workspace.rglob("*") if p.is_file()]
    final = read_history(workspace)
    snapshot_bytes = sum(p.stat().st_size for p in (workspace / "snapshots").iterdir())
    result = {
        "measurement_version": 1,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "fictional_only": True,
        "configured_collections": collections,
        "configured_revisions_one_collection": revisions,
        "results": results,
        "workspace": {
            "object_files": len(files),
            "total_bytes": sum(p.stat().st_size for p in files),
            "snapshot_bytes": snapshot_bytes,
            "objects_by_kind": {
                k: len(final[k])
                for k in ("snapshots", "attachments", "analyses", "reviews", "baselines")
            },
            "new_revision_objects_do_not_embed_observations": all(
                "observations" not in a for a in final["analyses"].values()
            ),
            "observation_bytes_not_duplicated_in_one_collection_revisions": len(
                serialize(selected["observations"])
            )
            * revisions,
            "largest_object_bytes": max(p.stat().st_size for p in files),
        },
        "verification_complexity": (
            "Full bounded inventory and dependency validation per public operation; "
            "no persistent index."
        ),
        "limitations": [
            "Finite traced runs, not scalability or throughput guarantees.",
            "RSS is process lifetime high-water mark; operations share one interpreter.",
            "Python allocation peak differs from RSS; tracemalloc overhead affects timing.",
            "Inputs are small synthetic captures; results do not establish production capacity.",
        ],
    }
    (output / "benchmark.json").write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--collections", type=int, default=16)
    parser.add_argument("--revisions", type=int, default=16)
    args = parser.parse_args()
    result = benchmark(args.output, args.collections, args.revisions)
    print(
        json.dumps({"workspace": result["workspace"], "results": result["results"]}, sort_keys=True)
    )


if __name__ == "__main__":
    main()
