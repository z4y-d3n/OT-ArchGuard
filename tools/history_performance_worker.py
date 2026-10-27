"""Fresh-process historical-evidence measurements; never imported by runtime.

Requests and all fixtures are local synthetic development artifacts. Timing,
profiling and allocation tracing are deliberately separate execution modes.
"""

import argparse
import copy
import cProfile
import gc
import hashlib
import importlib.metadata
import json
import os
import platform
import pstats
import shutil
import struct
import subprocess
import sys
import sysconfig
import time
import tracemalloc
from collections import Counter
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

import otarchguard
from benchmarks.capture import process_peak_rss_bytes
from otarchguard.capture.observations import analyze_capture
from otarchguard.capture.reconciliation import compare_capture
from otarchguard.diagnostics import ModelError
from otarchguard.evidence.attachments import build_attachment, model_architecture
from otarchguard.evidence.history import (
    HISTORY_LIMITS,
    initialize_history,
    migrate_workspace,
    read_history,
)
from otarchguard.evidence.lifecycle import (
    create_revision,
    import_attachment,
    list_baselines,
    list_history,
    list_revisions,
    propose_baseline,
    record_review,
    show_object,
    verify_lifecycle,
)
from otarchguard.evidence.reviews import build_baseline, build_review, validate_reviews
from otarchguard.evidence.revisions import build_revision, build_semantics
from otarchguard.evidence.workspace import build_snapshot, initialize_workspace, serialize
from tools.capture_workloads import plant_model, write_pcap


def canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False
    ).encode("ascii")


def identity(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def file_manifest(path: Path) -> dict[str, str]:
    return {
        p.relative_to(path).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(path.rglob("*"))
        if p.is_file()
    }


def request_inputs(request: dict[str, Any]) -> dict[str, str]:
    """Bind every supplied artifact the selected public operation actually reads."""
    result: dict[str, str] = {}
    workspace = Path(request["workspace"])
    result["workspace/presence"] = "directory" if workspace.is_dir() else "absent"
    if workspace.is_dir():
        result.update({"workspace/" + name: sha for name, sha in file_manifest(workspace).items()})
    operation = request["operation"]
    paths: list[str] = []
    if operation in {"migrate", "import_attachment"}:
        paths.append("source")
    if operation in {"propose_baseline", "invalid_reference"}:
        paths.append("scope")
    if operation == "create_revision" and request.get("semantics"):
        paths.append("semantics")
    for name in paths:
        path = Path(request[name])
        if path.is_dir():
            result[name + "/presence"] = "directory"
            result.update({name + "/" + member: sha for member, sha in file_manifest(path).items()})
        else:
            result[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def request_identity(request: dict[str, Any], inputs: dict[str, str]) -> str:
    selection = {
        key: request[key]
        for key in (
            "operation",
            "snapshot_id",
            "analysis_id",
            "baseline_id",
            "model",
            "predecessor",
        )
        if key in request
    }
    return identity({"input_files": inputs, "selection": selection})


def package_identity() -> dict[str, Any]:
    package = Path(otarchguard.__file__).parent
    distribution = importlib.metadata.distribution("otarchguard")
    direct = json.loads(distribution.read_text("direct_url.json") or "{}")
    if package.is_relative_to(Path(__file__).resolve().parents[1] / "src") or direct.get(
        "dir_info", {}
    ).get("editable", False):
        raise ValueError("Performance acceptance requires a regular installed distribution")
    sources = {
        p.relative_to(package).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(package.rglob("*.py"))
    }
    return {
        "module": str(package),
        "distribution": distribution.version,
        "python": platform.python_version(),
        "implementation": sys.implementation.name,
        "direct_url": direct,
        "native_engine": otarchguard.NATIVE_ENGINE_VERSION,
        "source_sha256": sources,
        "source_inventory_sha256": identity(sources),
    }


def _store(workspace: Path, kind: str, value: dict[str, Any]) -> str:
    singular = {
        "snapshots": "snapshot",
        "attachments": "attachment",
        "analyses": "analysis",
        "baselines": "baseline",
        "reviews": "review",
    }[kind]
    oid = str(value[singular + "_id"])
    with (workspace / kind / (oid + ".json")).open("xb") as stream:
        stream.write(serialize(value))
    return oid


def prepare_fixture(
    output: Path,
    collections: int,
    revisions: int = 0,
    review_depth: int = 0,
    packets: int = 1,
    *,
    baselines: int | None = None,
    unreferenced_models: int = 0,
    model_catalog: int | None = None,
) -> dict[str, Any]:
    """Construct bounded synthetic evidence with the selected baseline producer.

    Builders validate every artifact. Direct fixture writes avoid measuring an
    O(n) series of full-workspace public operations during fixture preparation;
    one final public verification proves the resulting complete workspace.
    """
    if baselines is None:
        baselines = review_depth
    catalog = revisions if model_catalog is None else model_catalog
    if not all(
        type(v) is int
        for v in (
            collections,
            revisions,
            review_depth,
            packets,
            baselines,
            unreferenced_models,
            catalog,
        )
    ):
        raise ValueError("Workload parameters require exact integers")
    if not 0 <= collections <= 256 or not 0 <= revisions <= 256 or not 0 <= review_depth <= 64:
        raise ValueError("Workload parameters exceed the finite benchmark envelope")
    if not 0 <= unreferenced_models <= 256 or not 0 <= baselines <= 256:
        raise ValueError("Attachment or baseline axis exceeds the finite benchmark envelope")
    if not revisions <= catalog <= 256:
        raise ValueError("The fixed model catalog must cover every selected revision")
    if not 1 <= packets <= 128 or (
        collections == 0
        and (revisions or review_depth or baselines or unreferenced_models or catalog)
    ):
        raise ValueError("Invalid workload packet or dependency parameters")
    if review_depth > baselines or baselines > revisions + 1:
        raise ValueError("Review chain needs distinct selected analytical revisions")
    output.mkdir(exist_ok=False)
    workspace = output / "history"
    legacy = output / "legacy"
    initialize_history(workspace)
    initialize_workspace(legacy)
    state: dict[str, Any] = {
        "snapshots": {},
        "attachments": {},
        "analyses": {},
        "baselines": {},
        "reviews": {},
    }
    selected: dict[str, Any] | None = None
    revision_ids: list[str] = []
    for index in range(collections):
        capture = output / f"fictional-{index}.pcap"
        write_pcap(capture, count=packets, cardinality=packets if packets > 1 else 0)
        # Independent physical originals: alter an exact classic-PCAP timestamp,
        # then process the actual bytes through the native bounded producer.
        data = bytearray(capture.read_bytes())
        struct.pack_into("<I", data, 24, 1_700_000_000 + index)
        capture.write_bytes(data)
        snapshot = build_snapshot(analyze_capture(capture), f"Fictional performance {index}")
        sid = _store(workspace, "snapshots", snapshot)
        _store(legacy, "snapshots", snapshot)
        state["snapshots"][sid] = snapshot
        analysis = build_revision(snapshot)
        aid = _store(workspace, "analyses", analysis)
        state["analyses"][aid] = analysis
        if selected is None:
            selected = snapshot
            revision_ids.append(aid)
    if selected is not None:
        for index in range(unreferenced_models):
            model = plant_model()
            model["revision"] = f"unreferenced-performance-model-{index}"
            attachment = build_attachment("model", model, selected)
            mid = _store(workspace, "attachments", attachment)
            state["attachments"][mid] = attachment
        for index in range(catalog):
            model = plant_model()
            model["revision"] = f"performance-model-{index}"
            attachment = build_attachment("model", model, selected)
            mid = _store(workspace, "attachments", attachment)
            state["attachments"][mid] = attachment
            if index < revisions:
                analysis = build_revision(selected, {"model": attachment})
                aid = _store(workspace, "analyses", analysis)
                state["analyses"][aid] = analysis
                revision_ids.append(aid)
        scope = {
            "environment": "Fictional finite performance laboratory",
            "purpose": "Synthetic performance review chain",
            "coverage": "Only generated packets; wider visibility unknown",
            "uncertainties": ["No operational or monitoring completeness asserted"],
            "vantage_points": [],
            "protocols": [],
        }
        baseline_ids = []
        for aid in revision_ids[:baselines]:
            baseline = build_baseline("evidence", [aid], scope, state)
            bid = _store(workspace, "baselines", baseline)
            state["baselines"][bid] = baseline
            baseline_ids.append(bid)
        previous = None
        for index, bid in enumerate(baseline_ids[:review_depth]):
            review = build_review(
                bid,
                "approve" if index == 0 else "supersede",
                "Fictional benchmark reviewer",
                "Synthetic measurement only",
                state,
                previous,
            )
            rid = _store(workspace, "reviews", review)
            state["reviews"][rid] = review
            previous = rid
    verified = verify_lifecycle(workspace)
    manifest = file_manifest(workspace)
    receipt = {
        "fixture_version": 1,
        "generator": "baseline native capture/model/revision builders",
        "parameters": {
            "collections": collections,
            "model_revisions": revisions,
            "review_depth": review_depth,
            "baseline_proposals": baselines,
            "unreferenced_models": unreferenced_models,
            "model_catalog": catalog,
            "packets": packets,
        },
        "workspace": str(workspace.absolute()),
        "legacy": str(legacy.absolute()),
        "workspace_manifest_sha256": identity(manifest),
        "file_sha256": manifest,
        "verification": verified,
    }
    (output / "fixture.json").write_bytes(serialize(receipt))
    return receipt


def prepare_fanout_fixture(output: Path, dense_workspace: Path, branches: int) -> dict[str, Any]:
    """Grow distinct mapping/comparison tuples over one known fictional capture.

    Mapping/comparison/revision counts grow together; this is a shared-native-model
    dependency workload, not a claim that one isolated graph edge count varies.
    No baseline approval records are created.
    """
    if type(branches) is not int or not 1 <= branches <= 256:
        raise ValueError("Fan-out branches must be in 1..256")
    verify_lifecycle(dense_workspace)
    source = read_history(dense_workspace)
    root = Path(__file__).resolve().parents[1]
    known_capture = hashlib.sha256(
        (root / "tests/fixtures/protocol-corpus/synthetic-industrial.pcap").read_bytes()
    ).hexdigest()
    original_mapping = next(
        (
            a
            for a in source["attachments"].values()
            if a["kind"] == "mapping" and a["capture_sha256"] == known_capture
        ),
        None,
    )
    if original_mapping is None or not any(
        p["decision"] != "PENDING" for p in original_mapping["payload"]["proposals"]
    ):
        raise ValueError("Fan-out requires reviewed mapping of the committed fictional capture")
    snapshot = next(s for s in source["snapshots"].values() if s["capture_sha256"] == known_capture)
    original_model = source["attachments"][original_mapping["dependencies"]["model"]]
    model = build_attachment("model", original_model["payload"], snapshot)
    if canonical(model) != canonical(original_model):
        raise ValueError("Native model template identity changed")
    enrichment = next(
        (
            a
            for a in source["attachments"].values()
            if a["kind"] == "enrichment" and a["capture_sha256"] == known_capture
        ),
        None,
    )
    validated = model_architecture(model)
    output.mkdir(exist_ok=False)
    workspace = output / "history"
    initialize_history(workspace)
    shutil.copyfile(
        dense_workspace / "snapshots" / (snapshot["snapshot_id"] + ".json"),
        workspace / "snapshots" / (snapshot["snapshot_id"] + ".json"),
    )
    _store(workspace, "attachments", model)
    components = {"model": model}
    if enrichment is not None:
        _store(workspace, "attachments", enrichment)
        components["enrichment"] = enrichment
    for index in range(branches):
        reviewed = copy.deepcopy(original_mapping["payload"])
        for proposal in reviewed["proposals"]:
            if proposal["decision"] != "PENDING":
                proposal["reviewer"] = f"Fictional fan-out reviewer {index}"
                proposal["rationale"] = (
                    f"Synthetic fan-out branch {index}; no operational assertion"
                )
        mapping = build_attachment("mapping", reviewed, snapshot, {"model": model})
        _store(workspace, "attachments", mapping)
        native_comparison = compare_capture(snapshot["observations"], validated, reviewed)
        comparison = build_attachment(
            "comparison", native_comparison, snapshot, {"model": model, "mapping": mapping}
        )
        _store(workspace, "attachments", comparison)
        analysis = build_revision(
            snapshot, {**components, "mapping": mapping, "comparison": comparison}
        )
        _store(workspace, "analyses", analysis)
    verified = verify_lifecycle(workspace)
    manifest = file_manifest(workspace)
    receipt = {
        "fixture_version": 1,
        "generator": "baseline frozen mapping/comparison/revision producers",
        "parameters": {
            "collections": 1,
            "native_models": 1,
            "enrichment": int(enrichment is not None),
            "mapping_branches": branches,
            "comparisons": branches,
            "analytical_revisions": branches,
        },
        "axis_limitations": "Mapping, comparison and revision counts grow together; "
        "shared capture/model stay exact.",
        "template_sha256": identity(file_manifest(dense_workspace)),
        "capture_sha256": known_capture,
        "model_attachment_id": model["attachment_id"],
        "workspace": str(workspace.absolute()),
        "workspace_manifest_sha256": identity(manifest),
        "file_sha256": manifest,
        "verification": verified,
    }
    (output / "fixture.json").write_bytes(serialize(receipt))
    return receipt


def prepare_case(fixture: Path, output: Path, operation: str) -> dict[str, Any]:
    """Prepare trial inputs once with baseline code, outside every timed region."""
    output.mkdir(exist_ok=False)
    source = fixture / "history" if (fixture / "history").is_dir() else fixture
    read_history(source)
    workspace = output / "history"
    shutil.copytree(source, workspace, symlinks=True)
    state = read_history(workspace)
    snapshots = list(state["snapshots"].values())
    analyses = list(state["analyses"].values())
    snapshot = snapshots[0] if snapshots else None
    scope = {
        "environment": "Fictional performance laboratory",
        "purpose": "One exact performance trial",
        "coverage": "Only selected synthetic packets; wider coverage unknown",
        "uncertainties": [],
        "vantage_points": [],
        "protocols": [],
    }
    (output / "scope.json").write_bytes(serialize(scope))
    request: dict[str, Any] = {
        "operation": operation,
        "workspace": str(workspace.absolute()),
        "scope": str((output / "scope.json").absolute()),
    }
    if snapshot is not None:
        request["snapshot_id"] = snapshot["snapshot_id"]
    if analyses:
        request["analysis_id"] = analyses[0]["analysis_id"]
    if operation in {"initialize", "migrate"}:
        request["workspace"] = str((output / "new-history").absolute())
        if operation == "migrate":
            legacy = output / "legacy"
            initialize_workspace(legacy)
            for item in snapshots:
                _store(legacy, "snapshots", item)
            request["source"] = str(legacy.absolute())
    if operation == "import_attachment":
        model = plant_model()
        model["revision"] = "One exact new trial model"
        (output / "model.json").write_bytes(canonical(model))
        request["source"] = str((output / "model.json").absolute())
    if operation in {"create_revision", "reuse_revision"}:
        if snapshot is None:
            raise ValueError("Revision action requires a collection")
        selected: dict[str, Any] = {}
        models = [
            a
            for a in state["attachments"].values()
            if a["kind"] == "model" and a["capture_sha256"] == snapshot["capture_sha256"]
        ]
        if models:
            model = models[0]
            request["model"] = model["attachment_id"]
            selected["model"] = model
        if operation == "create_revision":
            semantics = build_semantics(snapshot, selected, require_complete_scan=True)
            (output / "semantics.json").write_bytes(serialize(semantics))
            request["semantics"] = str((output / "semantics.json").absolute())
        else:
            # Dense fixtures may contain only enrichment/full-component analyses,
            # not the exact snapshot+model/default-semantics subject selected here.
            existing = build_revision(snapshot, selected)
            aid = existing["analysis_id"]
            if aid not in state["analyses"]:
                _store(workspace, "analyses", existing)
                state["analyses"][aid] = existing
            request["analysis_id"] = aid
    if operation in {
        "approve",
        "reject",
        "supersede",
        "revoke",
        "conflict_approval",
        "review_state",
        "show_baseline_text",
    }:
        if not analyses:
            raise ValueError("Review action requires an analysis")
        primary = analyses[0]
        if operation in {"supersede", "conflict_approval"}:
            primary = next(
                (
                    a
                    for a in analyses
                    if any(
                        b["capture_sha256"] == a["capture_sha256"]
                        and b["analysis_id"] != a["analysis_id"]
                        for b in analyses
                    )
                ),
                primary,
            )
        proposal = build_baseline("evidence", [primary["analysis_id"]], scope, state)
        bid = _store(workspace, "baselines", proposal)
        state["baselines"][bid] = proposal
        request["baseline_id"] = bid
        if operation in {"supersede", "revoke", "conflict_approval"}:
            review = build_review(
                bid, "approve", "Fictional benchmark reviewer", "Synthetic measurement only", state
            )
            rid = _store(workspace, "reviews", review)
            state["reviews"][rid] = review
            request["predecessor"] = rid
            if operation in {"supersede", "conflict_approval"}:
                alternative = next(
                    (
                        a
                        for a in analyses
                        if a["capture_sha256"] == primary["capture_sha256"]
                        and a["analysis_id"] != primary["analysis_id"]
                    ),
                    None,
                )
                if alternative is None:
                    raise ValueError("Supersession action requires another interpretation")
                proposal = build_baseline("evidence", [alternative["analysis_id"]], scope, state)
                bid = _store(workspace, "baselines", proposal)
                state["baselines"][bid] = proposal
                request["baseline_id"] = bid
        if operation == "conflict_approval":
            request.pop("predecessor")
    if operation == "corrupt_json":
        member = next((workspace / "snapshots").glob("*.json"))
        member.write_bytes(b'{"truncated":')
    if operation == "unsupported_version":
        manifest = json.loads((workspace / "workspace.json").read_bytes())
        manifest["workspace_version"] = 999
        (workspace / "workspace.json").write_bytes(serialize(manifest))
    if operation == "tampered_object":
        analysis = dict(analyses[0])
        original_id = analysis.pop("analysis_id")
        analysis["observations_sha256"] = "f" * 64
        aid = "analysis-" + identity({"domain": "otarchguard.analysis", "value": analysis})
        analysis["analysis_id"] = aid
        (workspace / "analyses" / (original_id + ".json")).unlink()
        _store(workspace, "analyses", analysis)
    request["input_file_sha256"] = request_inputs(request)
    request["input_identity"] = request_identity(request, request["input_file_sha256"])
    (output / "request.json").write_bytes(serialize(request))
    return request


def run_operation(request: dict[str, Any]) -> dict[str, Any]:
    workspace = Path(request["workspace"])
    operation = request["operation"]
    try:
        if operation == "initialize":
            result = initialize_history(workspace)
        elif operation == "migrate":
            result = migrate_workspace(Path(request["source"]), workspace)
        elif operation == "list_collections":
            result = list_history(workspace)
        elif operation == "list_revisions":
            result = list_revisions(workspace)
        elif operation == "show_revision":
            result = show_object(workspace, "analyses", request["analysis_id"])
        elif operation == "list_baselines":
            result = list_baselines(workspace)
        elif operation == "import_attachment":
            result = import_attachment(
                workspace, request["snapshot_id"], "model", Path(request["source"])
            )
        elif operation in {"create_revision", "reuse_revision"}:
            result = create_revision(
                workspace,
                request["snapshot_id"],
                model=request.get("model"),
                semantics=Path(request["semantics"]) if request.get("semantics") else None,
            )
        elif operation == "propose_baseline":
            result = propose_baseline(workspace, Path(request["scope"]), [request["analysis_id"]])
        elif operation in {"approve", "reject", "supersede", "revoke", "conflict_approval"}:
            result = record_review(
                workspace,
                request["baseline_id"],
                "approve" if operation == "conflict_approval" else operation,
                "Fictional benchmark reviewer",
                "Synthetic measurement only",
                request.get("predecessor"),
            )
        elif operation == "review_state":
            result = {"states": validate_reviews(read_history(workspace))}
        elif operation == "show_baseline_text":
            result = show_object(workspace, "baselines", request["baseline_id"])
        elif operation == "invalid_reference":
            result = propose_baseline(workspace, Path(request["scope"]), ["analysis-" + "f" * 64])
        elif operation == "resource_exhaustion":
            result = read_history(workspace, replace(HISTORY_LIMITS, analyses=0))
        elif operation in {"verify", "corrupt_json", "tampered_object", "unsupported_version"}:
            result = verify_lifecycle(workspace)
        else:
            raise ValueError("Unsupported measured operation")
    except ModelError as error:
        return {"exit_code": 2, "diagnostics": [asdict(d) for d in error.diagnostics]}
    return {"exit_code": 0, "result": result}


def console_arguments(request: dict[str, Any]) -> list[str]:
    workspace = request["workspace"]
    operation = request["operation"]
    if operation == "initialize":
        return ["evidence", "init", workspace, "--version", "2"]
    if operation == "migrate":
        return ["evidence", "migrate", request["source"], workspace]
    if operation == "list_collections":
        return ["evidence", "list", workspace]
    if operation == "list_revisions":
        return ["evidence", "revision", "list", workspace]
    if operation == "show_revision":
        return ["evidence", "revision", "show", workspace, request["analysis_id"]]
    if operation == "list_baselines":
        return ["evidence", "baseline", "list", workspace]
    if operation == "show_baseline_text":
        return ["evidence", "baseline", "show", workspace, request["baseline_id"], "--text"]
    if operation == "import_attachment":
        return ["evidence", "attach", workspace, request["snapshot_id"], "model", request["source"]]
    if operation in {"create_revision", "reuse_revision"}:
        args = ["evidence", "revision", "create", workspace, request["snapshot_id"]]
        if request.get("model"):
            args.extend(["--model", request["model"]])
        if request.get("semantics"):
            args.extend(["--semantics", request["semantics"]])
        return args
    if operation in {"propose_baseline", "invalid_reference"}:
        return [
            "evidence",
            "baseline",
            "propose",
            workspace,
            request["scope"],
            "--revision",
            request["analysis_id"] if operation == "propose_baseline" else "analysis-" + "f" * 64,
        ]
    if operation in {"approve", "reject", "supersede", "revoke", "conflict_approval"}:
        args = [
            "evidence",
            "baseline",
            "approve" if operation == "conflict_approval" else operation,
            workspace,
            request["baseline_id"],
            "--reviewer",
            "Fictional benchmark reviewer",
            "--rationale",
            "Synthetic measurement only",
        ]
        if request.get("predecessor"):
            args.extend(["--predecessor", request["predecessor"]])
        return args
    if operation in {"verify", "corrupt_json", "tampered_object", "unsupported_version"}:
        return ["evidence", "verify", workspace]
    raise ValueError("Operation has no equivalent console command")


def measure(request: dict[str, Any], mode: str, profile_path: Path | None = None) -> dict[str, Any]:
    if mode not in {"timing", "memory", "profile", "console"}:
        raise ValueError("Unknown measurement mode")
    inputs = request_inputs(request)
    if (
        inputs != request["input_file_sha256"]
        or request_identity(request, inputs) != request["input_identity"]
    ):
        raise ValueError("Trial inputs changed after case preparation")
    if mode == "console":
        executable = Path(sysconfig.get_path("scripts")) / (
            "otarchguard.exe" if os.name == "nt" else "otarchguard"
        )
        started = time.perf_counter_ns()
        child = subprocess.run(
            [str(executable), *console_arguments(request)], capture_output=True, timeout=300
        )
        elapsed = time.perf_counter_ns() - started
        return {
            "mode": mode,
            "elapsed_ns": elapsed,
            "cpu_ns": None,
            "python_peak_bytes": None,
            "rss_bytes": None,
            "exit_code": child.returncode,
            "stdout_sha256": hashlib.sha256(child.stdout).hexdigest(),
            "stderr_sha256": hashlib.sha256(child.stderr).hexdigest(),
            "stdout": child.stdout.decode(),
            "stderr": child.stderr.decode(),
            "cpu_limitation": "Child CPU/RSS are not inferred from parent process counters.",
        }
    gc.collect()
    counts: Counter[str] = Counter()
    unique: dict[str, set[str]] = {}
    contexts: dict[int, tuple[Any, dict[str, int]]] = {}

    def record_identities(value: object) -> None:
        if isinstance(value, dict):
            for key in ("snapshot_id", "attachment_id", "analysis_id", "baseline_id", "review_id"):
                if isinstance(value.get(key), str):
                    unique.setdefault(key, set()).add(value[key])

    def metrics(frame: Any, event: str, arg: Any) -> None:
        file = frame.f_code.co_filename.replace("\\", "/")
        name = frame.f_code.co_name
        if event == "call":
            if (
                name
                in {
                    "validate_snapshot",
                    "validate_attachment",
                    "validate_revision",
                    "validate_baseline",
                    "validate_reviews",
                    "build_revision",
                    "build_attachment",
                    "compare_capture",
                    "validate_bytes",
                    "read_history",
                    "_decode",
                    "canonical",
                    "digest",
                    "object_digest",
                    "implementation_identities",
                    "_clone",
                }
                and "/otarchguard/" in file
            ):
                counts[name] += 1
                for value in frame.f_locals.values():
                    record_identities(value)
            if file.endswith("/evidence/validation.py"):
                counts["context_calls." + name] += 1
            if name == "loads" and file.endswith("/json/__init__.py"):
                counts["json_parses"] += 1
            if name == "dumps" and file.endswith("/json/__init__.py"):
                counts["json_serializations"] += 1
        if event == "c_call" and getattr(arg, "__name__", "") in {"openssl_sha256", "sha256"}:
            counts["sha256_calculations"] += 1
        if event == "return" and isinstance(arg, bytes) and name in {"_read_bytes", "read_bytes"}:
            if "/otarchguard/" in file or "/pathlib/" in file or file.endswith("/pathlib.py"):
                counts["file_reads"] += 1
                counts["bytes_read"] += len(arg)
        if event == "return" and file.endswith("/evidence/validation.py"):
            context = frame.f_locals.get("self")
            if context is not None:
                if getattr(context, "_complete", False) and not getattr(context, "_failed", False):
                    previous = contexts.get(id(context), (context, {}))[1]
                    current = getattr(context, "_counts", {})
                    contexts[id(context)] = (
                        context,
                        {key: max(previous.get(key, 0), count) for key, count in current.items()},
                    )
                    for kind in ("snapshots", "attachments", "analyses", "baselines", "reviews"):
                        for value in getattr(context, "_state", {}).get(kind, {}).values():
                            record_identities(value)
                if name == "_attachment" and frame.f_locals.get("aid") in getattr(
                    context, "_validated_attachments", set()
                ):
                    record_identities(arg)
                if name == "_analysis" and frame.f_locals.get("aid") in getattr(
                    context, "_validated_analyses", set()
                ):
                    aid = frame.f_locals["aid"]
                    record_identities(getattr(context, "_state", {}).get("analyses", {}).get(aid))
        if event == "return" and name in {"validate_bytes", "_native"} and "/otarchguard/" in file:
            native_sha = getattr(arg, "sha256", None)
            if isinstance(native_sha, str):
                unique.setdefault("native_model_sha256", set()).add(native_sha)

    warmups = request.get("warmups", 0)
    if type(warmups) is not int or not 0 <= warmups <= 3:
        raise ValueError("Warmups must be an integer in 0..3")
    if warmups and request["operation"] not in {
        "verify",
        "list_collections",
        "list_revisions",
        "show_revision",
        "list_baselines",
        "show_baseline_text",
        "invalid_reference",
        "corrupt_json",
        "unsupported_version",
        "tampered_object",
        "resource_exhaustion",
        "review_state",
    }:
        raise ValueError("Mutating operations cannot reuse an already changed trial case")
    for _ in range(warmups):
        run_operation(request)
    if mode == "memory":
        tracemalloc.start()
    if mode == "profile":
        # Instrumentation never contributes to primary timing samples.
        sys.setprofile(metrics)
    started = time.perf_counter_ns()
    cpu = time.process_time_ns()
    result = run_operation(request)
    elapsed = time.perf_counter_ns() - started
    cpu_elapsed = time.process_time_ns() - cpu
    if mode == "profile":
        sys.setprofile(None)
        for _, context_counts in contexts.values():
            for key, count in context_counts.items():
                counts["context_validations." + key] += count
    peak = tracemalloc.get_traced_memory()[1] if mode == "memory" else None
    if mode == "memory":
        tracemalloc.stop()
    receipt = {
        "mode": mode,
        "warmups": warmups,
        "elapsed_ns": elapsed,
        "cpu_ns": cpu_elapsed,
        "python_peak_bytes": peak,
        "rss_bytes": process_peak_rss_bytes(),
        "outcome": result,
        "outcome_sha256": identity(result),
        "counts": dict(counts),
        "unique_objects": {key: len(ids) for key, ids in unique.items()},
        "unique_objects_scope": "Validator identity arguments plus completed context objects; "
        "rejected operations do not confer trust on visited identities.",
    }
    if profile_path is not None:
        # Profiling a mutation twice is unsafe. This additional profiler pass is
        # restricted to read-only operations and never supplies primary timing.
        if request["operation"] in {
            "verify",
            "list_collections",
            "list_revisions",
            "show_revision",
            "list_baselines",
        }:
            profile = cProfile.Profile()
            profile.runcall(run_operation, request)
            profile.dump_stats(profile_path)
            with profile_path.with_suffix(".txt").open("w", encoding="utf-8") as stream:
                pstats.Stats(profile, stream=stream).sort_stats("cumulative").print_stats(80)
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--mode", choices=["timing", "memory", "profile", "console"], default="timing"
    )
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--identify", action="store_true")
    parser.add_argument("--collections", type=int, default=1)
    parser.add_argument("--revisions", type=int, default=0)
    parser.add_argument("--review-depth", type=int, default=0)
    parser.add_argument("--packets", type=int, default=1)
    parser.add_argument("--baselines", type=int)
    parser.add_argument("--unreferenced-models", type=int, default=0)
    parser.add_argument("--model-catalog", type=int)
    parser.add_argument("--prepare-fanout", type=Path)
    parser.add_argument("--fanout", type=int, default=1)
    parser.add_argument("--case", type=Path)
    parser.add_argument("--operation", default="verify")
    args = parser.parse_args()
    if args.identify:
        result = package_identity()
        args.output.write_bytes(serialize(result))
    elif args.validate:
        result = verify_lifecycle(args.output)
    elif args.prepare_fanout is not None:
        result = prepare_fanout_fixture(args.output, args.prepare_fanout, args.fanout)
    elif args.prepare:
        result = prepare_fixture(
            args.output,
            args.collections,
            args.revisions,
            args.review_depth,
            args.packets,
            baselines=args.baselines,
            unreferenced_models=args.unreferenced_models,
            model_catalog=args.model_catalog,
        )
    elif args.case is not None:
        result = prepare_case(args.case, args.output, args.operation)
    else:
        if args.request is None:
            parser.error("Measurement requires --request")
        request = json.loads(args.request.read_bytes())
        result = measure(
            request, args.mode, args.output.with_suffix(".prof") if args.mode == "profile" else None
        )
        result["environment"] = {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "executable": sys.executable,
            "cpu_count": os.cpu_count(),
            "instrumentation": args.mode,
            "pythonpath": os.environ.get("PYTHONPATH"),
            "source_inventory_sha256": package_identity()["source_inventory_sha256"],
        }
        result["input_identity"] = request["input_identity"]
        args.output.write_bytes(serialize(result))
    print(json.dumps({"status": "completed", "output": str(args.output)}, sort_keys=True))


if __name__ == "__main__":
    main()
