"""Offline project orchestration, portable paths and independently bounded control I/O."""

import hashlib
import re
import unicodedata
from dataclasses import asdict, dataclass, replace
from pathlib import Path, PurePosixPath, PureWindowsPath

from pydantic import ValidationError

from otarchguard.contract import RESOURCE_LIMITS
from otarchguard.diagnostics import check_limit, fail
from otarchguard.domain import Record
from otarchguard.ingestion.project_records import (
    CatalogSource,
    ProjectDraft,
    ProjectManifest,
)
from otarchguard.ingestion.reconciliation import catalog, reconcile
from otarchguard.ingestion.records import MappingProfile
from otarchguard.ingestion.structured import StructuredLimits
from otarchguard.ingestion.tabular import IMPORT_LIMITS, digest, read_regular
from otarchguard.ingestion.workflow import create_draft, load_profile, serialize
from otarchguard.loading import load_bytes


@dataclass(frozen=True)
class ProjectLimits:
    manifest_bytes: int = 65536
    sources: int = 16
    source_bytes: int = 16 * 1024 * 1024
    evidence_items: int = 100_000
    candidates: int = 5000
    proposals: int = 4096
    conflicts: int = 4096
    connectors: int = 8000
    draft_bytes: int = 32 * 1024 * 1024
    control_events: int = 1_200_000
    decisions: int = 5000
    sidecar_bytes: int = 40 * 1024 * 1024
    depth: int = 40


PROJECT_LIMITS = ProjectLimits()


def _no_links(path: Path) -> None:
    # Include ancestors: a regular leaf reached through a link is still unsupported.
    absolute = path.absolute()
    for part in (absolute, *absolute.parents):
        if part.is_symlink() or part.is_junction():
            fail("PROJECT_PATH", "$", "Project paths must not traverse symlinks or junctions.")


def project_path(root: Path, name: str) -> Path:
    path = PurePosixPath(name)
    if (
        not name
        or path.is_absolute()
        or PureWindowsPath(name).is_absolute()
        or path.as_posix() != name
        or any(c in name for c in "\\:*?<>|\x00")
        or any(ord(c) < 32 or 127 <= ord(c) <= 159 for c in name)
        or any(p in {".", ".."} or p.endswith((".", " ")) for p in path.parts)
        or any(
            re.fullmatch(r"(?i)(con|prn|aux|nul|com[0-9]|lpt[0-9])(?:\..*)?", p) for p in path.parts
        )
    ):
        fail("PROJECT_PATH", "$", "Use a portable relative file path inside the project root.")
    target = root / name
    _no_links(target)
    if not target.resolve().is_relative_to(root.resolve()):
        fail("PROJECT_PATH", "$", "Project input escapes its root.")
    return target


def _canonical_manifest(manifest: ProjectManifest) -> ProjectManifest:
    ids = [s.id for s in manifest.sources]
    if len(set(ids)) != len(ids):
        fail("PROJECT_SOURCE_ID", "$", "Source IDs must be unique.")
    for field, source in manifest.preferred_sources.items():
        if (
            field
            not in {
                "asset.id",
                "asset.name",
                "asset.role",
                "asset.zone_id",
                "asset.kind",
                "interface.id",
                "interface.ipv4",
                "interface.asset_id",
                "interface.placement_zone_id",
                "zone.id",
                "zone.name",
            }
            or source not in ids
        ):
            fail("PROJECT_PRECEDENCE", "$", "Use a supported entity.field and declared source ID.")
    return manifest.model_copy(
        update={
            "sources": tuple(sorted(manifest.sources, key=lambda s: s.id)),
            "aliases": tuple(
                sorted(
                    (
                        a.model_copy(update={"members": tuple(sorted(a.members))})
                        for a in manifest.aliases
                    ),
                    key=lambda a: (a.members, a.rationale),
                )
            ),
        }
    )


def load_manifest(path: Path) -> ProjectManifest:
    _no_links(path)
    value = load_bytes(
        read_regular(path, PROJECT_LIMITS.manifest_bytes),
        replace(
            RESOURCE_LIMITS,
            input_bytes=PROJECT_LIMITS.manifest_bytes,
            parser_events=20000,
        ),
    )
    try:
        manifest = ProjectManifest.model_validate(value)
    except ValidationError:
        fail("PROJECT_MANIFEST", "$", "Invalid version-1 project manifest; see project reference.")
    return _canonical_manifest(manifest)


def check_project_envelope(value: Record | dict[str, object], maximum: int) -> None:
    check_limit("project_control_bytes", len(serialize(value)), maximum)
    payload = value.model_dump(mode="json") if isinstance(value, Record) else value

    def events(item: object, depth: int = 0) -> int:
        if isinstance(item, (dict, list)):
            depth += 1
            check_limit("project_depth", depth, PROJECT_LIMITS.depth)
        if isinstance(item, dict):
            return 2 + sum(1 + events(child, depth) for child in item.values())
        if isinstance(item, list):
            return 2 + sum(events(child, depth) for child in item)
        return 1

    check_limit("project_control_events", 4 + events(payload), PROJECT_LIMITS.control_events)


def load_project_record[T: Record](path: Path, record_type: type[T]) -> T:
    from otarchguard.ingestion.json_inventory import parse_json

    _no_links(path)
    # Project drafts/decisions use JSON only. Manifests retain bounded strict YAML support.
    payload = parse_json(
        read_regular(path, PROJECT_LIMITS.draft_bytes),
        StructuredLimits(
            source_bytes=PROJECT_LIMITS.draft_bytes,
            depth=PROJECT_LIMITS.depth,
            records=PROJECT_LIMITS.control_events,
            scalars=PROJECT_LIMITS.control_events,
            text=4096,
        ),
    )
    try:
        record = record_type.model_validate(payload)
    except (ValidationError, ValueError):
        fail("PROJECT_CONTROL", "$", "Invalid versioned project control JSON.")
    check_project_envelope(record, PROJECT_LIMITS.draft_bytes)
    return record


def create_project(path: Path) -> ProjectDraft:
    manifest = load_manifest(path)
    check_limit("project_sources", len(manifest.sources), PROJECT_LIMITS.sources)
    root = path.absolute().parent
    source_names = {s.path for s in manifest.sources}
    profile_names = {s.profile for s in manifest.sources}
    other_names = profile_names | ({manifest.model_context} if manifest.model_context else set())
    if len(source_names) != len(manifest.sources) or source_names & other_names:
        fail(
            "PROJECT_PATH_COLLISION",
            "$",
            "Source files must be distinct from sources and controls.",
        )
    names = source_names | other_names
    if path.name in names:
        fail("PROJECT_PATH_COLLISION", "$", "A project cannot include itself as input.")
    folded = [unicodedata.normalize("NFC", n).casefold() for n in sorted(names)]
    if len(set(folded)) != len(folded):
        fail("PROJECT_PATH_COLLISION", "$", "Case/Unicode-colliding project paths are forbidden.")
    paths = {n: project_path(root, n) for n in sorted(names)}
    # Reject hard-link aliases too; shared profiles may be named once by several sources.
    identities: set[tuple[int, int]] = set()
    for target in [path, *paths.values()]:
        read_regular(target, RESOURCE_LIMITS.input_bytes)
        stat = target.stat()
        file_key = stat.st_dev, stat.st_ino
        if file_key in identities:
            fail("PROJECT_PATH_COLLISION", "$", "Repeated file aliases are forbidden.")
        identities.add(file_key)
    aggregate = sum(paths[s.path].stat().st_size for s in manifest.sources)
    check_limit("project_source_bytes", aggregate, PROJECT_LIMITS.source_bytes)
    sources: list[CatalogSource] = []
    counts = {"source_bytes": 0, "candidates": 0, "connectors": 0, "evidence_items": 0}
    for source in manifest.sources:
        source_path = paths[source.path]
        profile_path = paths[source.profile]
        profile_bytes = read_regular(profile_path, RESOURCE_LIMITS.input_bytes)
        profile = load_profile(profile_path)
        if isinstance(profile, MappingProfile):
            valid = (
                source.adapter in {"csv", "tsv"}
                and source_path.suffix.lower() == "." + source.adapter
            )
        else:
            valid = source.adapter == profile.adapter
        if not valid:
            fail("PROJECT_ADAPTER", source.id, "Declared adapter and mapping profile disagree.")
        before = read_regular(source_path, IMPORT_LIMITS.source_bytes)
        evidence = create_draft(source_path, profile)
        if (
            hashlib.sha256(before).hexdigest() != evidence.source.sha256
            or before != read_regular(source_path, IMPORT_LIMITS.source_bytes)
            or profile_bytes != read_regular(profile_path, RESOURCE_LIMITS.input_bytes)
        ):
            fail("PROJECT_SOURCE_CHANGED", source.id, "Input changed while assembling the project.")
        sources.append(
            CatalogSource(
                id=source.id,
                path=source.path,
                profile_path=source.profile,
                profile_sha256=hashlib.sha256(profile_bytes).hexdigest(),
                evidence=evidence,
            )
        )
        counts["source_bytes"] += evidence.source.byte_count
        counts["candidates"] += len(evidence.candidates)
        counts["evidence_items"] += sum(len(c.fields) for c in evidence.candidates)
        if evidence.graph:
            counts["connectors"] += len(evidence.graph.edges)
            counts["evidence_items"] += len(evidence.graph.edges) + len(evidence.graph.nodes)
        for key, count in counts.items():
            check_limit("project_" + key, count, getattr(PROJECT_LIMITS, key))
    context = {}
    context_sha = None
    if manifest.model_context:
        data = read_regular(paths[manifest.model_context], RESOURCE_LIMITS.input_bytes)
        value = load_bytes(data)
        if not isinstance(value, dict):
            fail("PROJECT_CONTEXT", "$", "Owner native model context must be a mapping.")
        context = value
        context_sha = hashlib.sha256(data).hexdigest()
    proposals, conflicts = reconcile(tuple(sources), manifest, PROJECT_LIMITS.proposals)
    check_limit("project_conflicts", len(conflicts), PROJECT_LIMITS.conflicts)
    counts.update(proposals=len(proposals), conflicts=len(conflicts), sources=len(sources))
    draft = ProjectDraft(
        project_draft_version=1,
        manifest=manifest,
        manifest_sha256=digest(manifest.model_dump(mode="json")),
        sources=tuple(sources),
        context=context,
        context_sha256=context_sha,
        proposals=proposals,
        conflicts=conflicts,
        accounting=counts,
    )
    catalog(draft.sources)  # Independent qualified-ID uniqueness check.
    if load_manifest(path) != manifest:
        fail("PROJECT_SOURCE_CHANGED", "$", "Manifest changed during mapping.")
    check_project_envelope(draft, PROJECT_LIMITS.draft_bytes)
    return draft


def project_digest(draft: ProjectDraft) -> str:
    return digest(draft.model_dump(mode="json"))


def protected_output(manifest_path: Path, outputs: tuple[Path, ...]) -> None:
    manifest = load_manifest(manifest_path)
    root = manifest_path.absolute().parent
    protected = [
        manifest_path,
        *(project_path(root, s.path) for s in manifest.sources),
        *(project_path(root, s.profile) for s in manifest.sources),
    ]
    if manifest.model_context:
        protected.append(project_path(root, manifest.model_context))
    for output in outputs:
        _no_links(output)
        resolved = output.resolve()
        if any(p.resolve() == resolved or p.resolve().is_relative_to(resolved) for p in protected):
            fail("PROJECT_OUTPUT", "$", "Output overlaps protected project input paths.")


def project_limits() -> dict[str, int]:
    return asdict(PROJECT_LIMITS)
