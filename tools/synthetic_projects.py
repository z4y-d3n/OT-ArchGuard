"""Reproducible fictional projects and explicit tutorial owner decisions; no customer data."""

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from otarchguard.ingestion.project import create_project
from otarchguard.ingestion.project_records import EntityDecision, ProjectDecisions, ProjectDraft
from otarchguard.ingestion.project_review import (
    acknowledge_connectors,
    connector_sets,
    project_template,
)
from otarchguard.ingestion.reconciliation import catalog, observed
from otarchguard.ingestion.workflow import serialize
from tools.synthetic_graphs import DEVICES, drawio_xml, graphml_xml
from tools.synthetic_inventories import workbook_parts, zip_parts

ASSET_CONSTANTS = {
    "kind": "endpoint",
    "scope": "internal",
    "domain_classification": "iacs",
    "safety_classification": "unassessed",
    "criticality": "unspecified",
}
ZONE_CONSTANTS = {
    "purpose": "Fictional control cell",
    "scope": "internal",
    "grouping_rationale": "Synthetic owner declaration",
    "safety_designation": "unassessed",
}


def write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n"
    )


def synthetic_project(
    root: Path,
    *,
    count: int = 6,
    graph: str = "drawio",
    contradictory: bool = True,
    formats: tuple[str, ...] = ("csv", "xlsx", "json", "graph"),
) -> Path:
    """Generate only fictional files in a fresh or explicitly supplied test directory."""
    root.mkdir(parents=True, exist_ok=True)
    devices = (
        list(DEVICES)
        if count == 6
        else [(f"n{i}", f"Synthetic {i}", "Device") for i in range(count)]
    )
    sources: list[dict[str, str]] = []
    asset_fields = {"id": "id", "name": "name", "role": "role", "zone_id": "zone"}
    if "csv" in formats:
        rows = ["id,name,role,zone"] + [
            f"{key},{label},{role},{'alternate' if contradictory and i == 0 else 'control'}"
            for i, (key, label, role) in enumerate(devices)
        ]
        (root / "metadata.csv").write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")
        write_json(
            root / "metadata-profile.json",
            {
                "profile_version": 1,
                "entity": "asset",
                "fields": asset_fields,
                "constants": ASSET_CONSTANTS,
            },
        )
        sources.append(
            {
                "id": "metadata",
                "path": "metadata.csv",
                "adapter": "csv",
                "profile": "metadata-profile.json",
            }
        )
    if "xlsx" in formats:
        tables = {
            "Assets": [
                ["id", "name", "role", "zone"],
                *[[k, n, r, "control"] for k, n, r in devices],
            ],
            "Zones": [["id", "name"], ["control", "Control"], ["alternate", "Alternate"]],
        }
        (root / "inventory.xlsx").write_bytes(zip_parts(workbook_parts(tables)))
        write_json(
            root / "inventory-profile.json",
            {
                "profile_version": 2,
                "adapter": "xlsx",
                "tables": [
                    {
                        "name": "assets",
                        "collection": "Assets",
                        "entity": "asset",
                        "fields": {
                            field: {"path": header} for field, header in asset_fields.items()
                        },
                        "constants": ASSET_CONSTANTS,
                    },
                    {
                        "name": "zones",
                        "collection": "Zones",
                        "entity": "zone",
                        "fields": {"id": {"path": "id"}, "name": {"path": "name"}},
                        "constants": ZONE_CONSTANTS,
                    },
                ],
            },
        )
        sources.append(
            {
                "id": "inventory",
                "path": "inventory.xlsx",
                "adapter": "xlsx",
                "profile": "inventory-profile.json",
            }
        )
    if "json" in formats:
        write_json(
            root / "interfaces.json",
            {
                "interfaces": [
                    {
                        "id": "if_" + key,
                        "asset": key,
                        "zone": "control",
                        "ip": f"10.{i // 65000}.{i // 250 % 250}.{i % 250 + 1}/16",
                    }
                    for i, (key, _, _) in enumerate(devices)
                ]
            },
        )
        write_json(
            root / "interfaces-profile.json",
            {
                "profile_version": 2,
                "adapter": "json",
                "tables": [
                    {
                        "name": "interfaces",
                        "collection": "/interfaces",
                        "entity": "interface",
                        "fields": {
                            f: {"path": "/" + p}
                            for f, p in {
                                "id": "id",
                                "asset_id": "asset",
                                "placement_zone_id": "zone",
                                "ipv4": "ip",
                            }.items()
                        },
                    }
                ],
            },
        )
        sources.append(
            {
                "id": "interfaces",
                "path": "interfaces.json",
                "adapter": "json",
                "profile": "interfaces-profile.json",
            }
        )
    if "graph" in formats:
        text = drawio_xml(count=count) if graph == "drawio" else graphml_xml(count=count)
        (root / ("topology." + graph)).write_text(text, encoding="utf-8", newline="\n")
        write_json(
            root / "topology-profile.json",
            {
                "profile_version": 3,
                "adapter": graph,
                "scopes": ["page1" if graph == "drawio" else "plant"],
                "connections": "evidence_only",
                "unknown_policy": "diagnose",
                "tables": [
                    {
                        "name": "nodes",
                        "collection": "nodes",
                        "entity": "asset",
                        "fields": {
                            "id": {"path": "/id"},
                            "name": {
                                "path": "/label" if graph == "drawio" else "/attributes/label"
                            },
                        },
                        "constants": {**ASSET_CONSTANTS, "role": "Device", "zone_id": "control"}
                        if count > 100
                        else {},
                    }
                ],
            },
        )
        sources.append(
            {
                "id": "topology",
                "path": "topology." + graph,
                "adapter": graph,
                "profile": "topology-profile.json",
            }
        )
    context: dict[str, Any] = {
        "schema_version": 1,
        "architecture_id": "synthetic_project",
        "revision": "owner_review_1",
        "suc": {
            "id": "synthetic_cell",
            "name": "Fictional control cell",
            "purpose": "Import tutorial",
            "controlled_process": "Imaginary control process",
            "boundary_description": "Fictional inventory only",
            "completeness_assertion": "Documentation exercise; no real deployment assertion",
            "external_dependencies": [],
            "access_points": [],
        },
        **{
            name: []
            for name in (
                "conduits",
                "transport_edges",
                "forwarding_edges",
                "services",
                "rules",
                "intents",
                "scenarios",
            )
        },
    }
    if "xlsx" not in formats:
        context["zones"] = [
            {"id": key, "name": key, **ZONE_CONSTANTS} for key in ("control", "alternate")
        ]
    if "csv" not in formats and "xlsx" not in formats:
        context["assets"] = [
            {"id": k, "name": n, "role": r, "zone_id": "control", **ASSET_CONSTANTS}
            for k, n, r in devices
        ]
    write_json(root / "context.json", context)
    manifest = root / "project.json"
    write_json(
        manifest,
        {
            "project_version": 1,
            "project_id": "fictional-control-network",
            "sources": sources,
            "model_context": "context.json",
            "preferred_sources": {"asset.zone_id": "inventory"} if "xlsx" in formats else {},
        },
    )
    return manifest


def tutorial_decisions(draft: ProjectDraft) -> ProjectDecisions:
    """Explicit choices for the known fictional fixture, never a production accept-all API.

    The fictional owner equates the fixture's same-ID records, selects inventory zone
    evidence, retains diagram-only nodes without declarations, and grants no traffic.
    Real projects require the owner's engineering review of every such choice.
    """
    assert draft.manifest.project_id == "fictional-control-network"
    candidates = catalog(draft.sources)
    grouped: dict[tuple[str, str], list[str]] = defaultdict(list)
    for key, (_, c) in candidates.items():
        if c.entity != "connection":
            grouped[c.entity, observed(c).get("id", "")].append(key)
    decisions = []
    has_inventory = any(s.id in {"inventory", "metadata"} for s in draft.sources)
    for (entity, canonical_id), members in sorted(grouped.items()):
        evidence_only = entity == "asset" and not has_inventory
        selections = {}
        for field in {f.field for key in members for f in candidates[key][1].fields} - {"id"}:
            values = {
                observed(candidates[key][1])[field]
                for key in members
                if field in observed(candidates[key][1])
            }
            if len(values) > 1:
                selected = next(
                    key
                    for key in members
                    if key.startswith("inventory::") and field in observed(candidates[key][1])
                )
                selections[field] = selected
        decisions.append(
            EntityDecision(
                members=tuple(sorted(members)),
                decision="EVIDENCE_ONLY" if evidence_only else "OWNER_CONFIRMED",
                canonical_id=canonical_id,
                field_sources=selections,
                rationale=(
                    "Fictional owner equates these fixture records and confirms fields; "
                    "inventory zone controls this tutorial conflict."
                ),
            )
        )
    template = project_template(draft)
    owner = template.model_copy(
        update={
            "reviewer": "Synthetic owner",
            "model_confirmed": True,
            "model_rationale": "Fictional inventory declaration; no inferred permissions.",
            "entities": tuple(decisions),
            "conflicts": tuple(
                c.model_copy(
                    update={
                        "resolved": True,
                        "rationale": "Fictional owner reviewed and selected inventory evidence.",
                    }
                )
                for c in template.conflicts
            ),
        }
    )
    for source, connectors in connector_sets(draft).items():
        if connectors:
            owner = acknowledge_connectors(
                draft,
                owner,
                source,
                owner.reviewer,
                "Retain fictional connectors as documentary evidence only.",
            )
    return owner


def create_tutorial(root: Path) -> None:
    manifest = synthetic_project(root)
    draft = create_project(manifest)
    (root / "tutorial-decisions.json").write_bytes(serialize(tutorial_decisions(draft)))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    create_tutorial(parser.parse_args().output)
