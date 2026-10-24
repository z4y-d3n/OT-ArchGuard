"""Bounded exact indexes produce explainable proposals, never authoritative merges."""

import ipaddress
import unicodedata
from collections import defaultdict

from otarchguard.diagnostics import check_limit, fail
from otarchguard.ingestion.project_records import CatalogSource, MatchGroup, ProjectManifest
from otarchguard.ingestion.records import ImportCandidate, StructuredCandidate
from otarchguard.ingestion.tabular import digest

type Candidate = ImportCandidate | StructuredCandidate
type Catalog = dict[str, tuple[str, Candidate]]


def catalog(sources: tuple[CatalogSource, ...]) -> Catalog:
    result: Catalog = {}
    for source in sources:
        for candidate in source.evidence.candidates:
            key = source.id + "::" + candidate.candidate_id
            if key in result:
                fail("PROJECT_IDENTITY", "$", "Duplicate source-qualified candidate identity.")
            result[key] = source.id, candidate
    return dict(sorted(result.items()))


def observed(candidate: Candidate) -> dict[str, str]:
    # Missing/null/empty/type-invalid values are retained in evidence, not assertions.
    return {
        f.field: f.normalized_value
        for f in candidate.fields
        if f.normalized_value != "" and f.state not in {"UNRESOLVED", "UNSUPPORTED"}
    }


def reconcile(
    sources: tuple[CatalogSource, ...],
    manifest: ProjectManifest,
    maximum: int = 4096,
) -> tuple[tuple[MatchGroup, ...], tuple[MatchGroup, ...]]:
    candidates = catalog(sources)
    indexes: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    values = {key: observed(candidate) for key, (_, candidate) in candidates.items()}
    for key, (_, candidate) in candidates.items():
        if candidate.entity == "connection":
            continue
        for field in ("id", "name", "ipv4"):
            value = values[key].get(field)
            if value:
                if field == "ipv4":
                    try:
                        value = str(ipaddress.IPv4Interface(value).ip)
                    except ValueError:
                        continue
                indexes[candidate.entity, field, value].append(key)
        identity = values[key].get("id")
        if identity:
            folded = unicodedata.normalize("NFC", identity).casefold()
            indexes[candidate.entity, "normalized_id_collision", folded].append(key)

    proposals: list[MatchGroup] = []
    conflicts: list[MatchGroup] = []

    def group(
        members: tuple[str, ...],
        field: str,
        value: str,
        code: str,
        alias: bool = False,
    ) -> None:
        if len(set(members)) != len(members) or not set(members) <= candidates.keys():
            fail("PROJECT_ALIAS", "$", "Alias requires distinct existing qualified candidates.")
        if len({candidates[k][1].entity for k in members}) != 1:
            fail("PROJECT_ALIAS", "$", "An alias cannot equate different entity families.")
        # Group sets, not O(n squared) pairs. Duplicate labels cannot explode a matrix.
        differences = tuple(
            sorted(
                f
                for f in {f for k in members for f in values[k]}
                if f != "id" and len({values[k][f] for k in members if f in values[k]}) > 1
            )
        )
        payload = {"members": members, "field": field, "value": value, "code": code}
        proposal = MatchGroup(
            group_id="match_" + digest(payload),
            category="OWNER_DECLARED_ALIAS"
            if alias
            else "EXPLICIT_ID_MATCH"
            if field == "id"
            else "EXACT_ATTRIBUTE_MATCH",
            code=code,
            field=field,
            value=value,
            members=members,
            differences=differences,
            explanation=(
                "Configured alias proposes identity; current owner confirmation remains required."
                if alias
                else f"Exact mapped {field} evidence agrees; identity remains unconfirmed."
            ),
        )
        proposals.append(proposal)
        same_source = len({candidates[k][0] for k in members}) < len(members)
        ambiguous_name = field == "name" and len({values[k].get("id") for k in members}) > 1
        blocking = (
            field in {"ipv4", "normalized_id_collision"}
            or same_source
            or ambiguous_name
            or (field == "id" and bool(differences))
        )
        if blocking:
            conflicts.append(
                proposal.model_copy(
                    update={
                        "group_id": "conflict_" + digest(payload),
                        "category": "CONFLICT",
                        "code": "REUSED_ADDRESS"
                        if field == "ipv4"
                        else "NORMALIZATION_COLLISION"
                        if field == "normalized_id_collision"
                        else "REPEATED_SOURCE_RECORD"
                        if same_source
                        else "AMBIGUOUS_NAME"
                        if ambiguous_name
                        else "CONTRADICTORY_ATTRIBUTES",
                        "explanation": "Review observations; source order cannot resolve them.",
                    }
                )
            )
        check_limit("project_proposals", len(proposals), maximum)
        check_limit("project_conflicts", len(conflicts), maximum)

    for (_, field, value), members in sorted(indexes.items()):
        if len(members) < 2:
            continue
        if field == "normalized_id_collision" and len({values[k]["id"] for k in members}) < 2:
            continue
        group(tuple(sorted(members)), field, value, "MATCHING_" + field.upper())
    aliases = sorted(manifest.aliases, key=lambda a: tuple(sorted(a.members)))
    seen: set[tuple[str, ...]] = set()
    for alias in aliases:
        alias_members = tuple(sorted(alias.members))
        if alias_members in seen:
            fail("PROJECT_ALIAS", "$", "Duplicate alias sets are forbidden.")
        seen.add(alias_members)
        group(alias_members, "alias", alias.rationale, "CONFIGURED_ALIAS", True)
    return tuple(sorted(proposals, key=lambda g: g.group_id)), tuple(
        sorted(conflicts, key=lambda g: g.group_id)
    )
