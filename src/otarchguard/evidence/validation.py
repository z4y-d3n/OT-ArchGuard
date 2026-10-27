"""Operation-private validation of the complete historical dependency graph.

The frozen attachment/revision producers remain the public standalone contracts.
This consumer builds the same expected envelopes while retaining completed native
and dependency validation only for one acquired, privately owned workspace image.
No cache survives an independent lifecycle operation or trusts an imported ID.
"""

import copy
import hashlib
import json
from collections.abc import Iterator, Mapping
from typing import TYPE_CHECKING, Any, cast

from otarchguard.api import ValidatedArchitecture, validate_bytes
from otarchguard.capture.contract import CAPTURE_LIMITS
from otarchguard.capture.reconciliation import _reviewed, compare_capture
from otarchguard.diagnostics import ModelError, check_limit, fail
from otarchguard.evidence.attachments import (
    ATTACHMENT_LIMITATIONS,
    KINDS,
    _clone,
    _validate_enrichment,
    canonical,
    object_digest,
)
from otarchguard.evidence.attachments import (
    validate_attachment as _standalone_attachment,
)
from otarchguard.evidence.history import HISTORY_LIMITS
from otarchguard.evidence.observations import digest, identity
from otarchguard.evidence.reviews import validate_baseline, validate_reviews
from otarchguard.evidence.revisions import REVISION_LIMITATIONS, build_semantics
from otarchguard.evidence.workspace import validate_snapshot

if TYPE_CHECKING:
    from otarchguard.evidence.history import _HistoryImage

_KINDS = ("snapshots", "attachments", "analyses", "baselines", "reviews")
_MALFORMED = (KeyError, TypeError, ValueError, AttributeError, IndexError, RecursionError)


def _bounded_copy(state: dict[str, Any]) -> dict[str, Any]:
    """Check caller-owned JSON before copying, without allocating a wide stack.

    The file reader already performs these checks for an acquired image. Direct
    Python validation callers need the same finite boundary before ``deepcopy``.
    Unknown root data is not part of lifecycle graph semantics and is ignored,
    as by the original pure graph validator. The per-object minimum canonical
    byte estimate never rejects a valid canonical/pretty storage representation.
    """
    if type(state) is not dict:
        fail("EVIDENCE_GRAPH", "$", "Malformed or unsupported historical dependency graph.")
    selected: dict[str, Any] = {}
    total = 0
    for kind in _KINDS:
        objects = state.get(kind)
        if type(objects) is not dict:
            fail("EVIDENCE_GRAPH", "$", "Malformed or unsupported historical dependency graph.")
        check_limit("history_" + kind, len(objects), getattr(HISTORY_LIMITS, kind))
        for name, value in objects.items():
            if type(name) is not str:
                fail("EVIDENCE_GRAPH", "$", "Historical object map keys must be JSON strings.")
            check_limit("evidence_text_characters", len(name), 4096)
            stack: list[tuple[Iterator[Any], int, int | None]] = [(iter((value,)), 0, None)]
            active: set[int] = set()
            nodes = planned = 0
            while stack:
                iterator, depth, container_id = stack[-1]
                try:
                    item = next(iterator)
                except StopIteration:
                    stack.pop()
                    if container_id is not None:
                        active.remove(container_id)
                    continue
                nodes += 1
                check_limit("evidence_nodes", nodes, HISTORY_LIMITS.nodes)
                if type(item) in {dict, list}:
                    check_limit("evidence_depth", depth + 1, HISTORY_LIMITS.depth)
                    if id(item) in active:
                        fail("EVIDENCE_GRAPH", "$", "Cyclic in-memory evidence is unsupported.")
                    # Every immediate child costs at least one node; reject an
                    # excessive width before creating/iterating those children.
                    check_limit("evidence_nodes", nodes + len(item), HISTORY_LIMITS.nodes)
                    active.add(id(item))
                    planned += 2 + max(0, len(item) - 1)
                    if type(item) is dict:
                        planned += len(item)  # colons
                        for key in item:
                            if type(key) is not str:
                                fail("EVIDENCE_GRAPH", "$", "Evidence JSON keys must be strings.")
                            check_limit("evidence_text_characters", len(key), 4096)
                            planned += len(json.dumps(key, ensure_ascii=True))
                            check_limit(
                                "history_object_bytes", planned, HISTORY_LIMITS.object_bytes
                            )
                        children = iter(item.values())
                    else:
                        children = iter(item)
                    stack.append((children, depth + 1, id(item)))
                elif type(item) is str:
                    check_limit("evidence_text_characters", len(item), 4096)
                    planned += len(json.dumps(item, ensure_ascii=True))
                elif item is None:
                    planned += 4
                elif type(item) is bool:
                    planned += 4 if item else 5
                elif type(item) is int:
                    # A conservative lower bound avoids an enormous decimal
                    # conversion before applying the existing object byte limit.
                    check_limit(
                        "history_object_bytes",
                        (item.bit_length() * 3) // 10,
                        HISTORY_LIMITS.object_bytes,
                    )
                    try:
                        planned += len(str(item))
                    except ValueError:
                        fail("EVIDENCE_GRAPH", "$", "Evidence integer exceeds safe JSON limits.")
                else:
                    fail("EVIDENCE_GRAPH", "$", "Evidence requires exact JSON primitive types.")
                check_limit("history_object_bytes", planned, HISTORY_LIMITS.object_bytes)
            total += planned
            check_limit("history_workspace_bytes", total, HISTORY_LIMITS.workspace_bytes)
        selected[kind] = objects
    return copy.deepcopy(selected)


def _attachment_error(condition: bool, message: str) -> None:
    if not condition:
        fail("EVIDENCE_ATTACHMENT", "$", message)


def _revision_error(condition: bool, message: str) -> None:
    if not condition:
        fail("EVIDENCE_REVISION", "$", message)


class _ValidationContext:
    """A bounded operation capability; never return or retain it across API calls.

    ``state`` is copied for a direct in-memory validation call. The internal
    ``_from_image`` factory transfers ownership of a newly read image without
    duplicating its observation bodies. Neither construction path accepts a
    caller-supplied validated flag. Previously validated objects are never
    mutated; adding an object replaces only its containing map.
    """

    def __init__(self, state: dict[str, Any]) -> None:
        self._initialize(_bounded_copy(state))

    @classmethod
    def _from_image(cls, image: "_HistoryImage") -> "_ValidationContext":
        result = cls.__new__(cls)
        result._initialize(image.state)
        return result

    def _initialize(self, state: dict[str, Any]) -> None:
        self._state = state
        self._snapshots: dict[str, dict[str, Any]] = {}
        self._validated_attachments: set[str] = set()
        self._validating_attachments: set[str] = set()
        self._validated_analyses: set[str] = set()
        self._validated_baselines: set[str] = set()
        self._native_inputs: dict[str, ValidatedArchitecture] = {}
        self._native_models: dict[str, ValidatedArchitecture] = {}
        self._native_bytes = 0
        self._semantics_base: dict[str, Any] | None = None
        self._statuses: dict[str, str] | None = None
        self._complete = False
        self._failed = False
        self._counts = dict.fromkeys(
            (
                "snapshots",
                "attachments",
                "analyses",
                "baselines",
                "native_models",
                "mappings",
                "comparisons",
            ),
            0,
        )

    @property
    def statuses(self) -> dict[str, str]:
        if not self._complete or self._statuses is None:
            fail("EVIDENCE_GRAPH", "$", "Complete validation is required before review resolution.")
        return dict(self._statuses)

    def _member(self, kind: str, oid: str) -> dict[str, Any]:
        if kind not in _KINDS or not isinstance(oid, str):
            fail("EVIDENCE_ID", "$", "Use an exact supported historical object identity.")
        result = self._state[kind].get(oid)
        if result is None:
            fail("EVIDENCE_NOT_FOUND", "$", "Exact dependency is not present in this workspace.")
        return result  # type: ignore[no-any-return]

    def validate(self) -> None:
        """Validate every object, including unreferenced attachments and analyses."""
        if self._failed:
            fail("EVIDENCE_GRAPH", "$", "A failed validation context cannot be reused.")
        if self._complete:
            return
        try:
            for kind in _KINDS:
                check_limit(
                    "history_" + kind, len(self._state[kind]), getattr(HISTORY_LIMITS, kind)
                )
            for snapshot in self._state["snapshots"].values():
                validate_snapshot(snapshot)
                capture = snapshot["capture_sha256"]
                if capture in self._snapshots:
                    fail("EVIDENCE_WORKSPACE", "$", "Duplicate physical collection identity.")
                self._snapshots[capture] = snapshot
                self._counts["snapshots"] += 1
            for aid in sorted(self._state["attachments"]):
                value = self._state["attachments"][aid]
                self._snapshot(value.get("capture_sha256"))
                for dependency in value.get("dependencies", {}).values():
                    if dependency is not None:
                        self._member("attachments", dependency)
                self._attachment(aid)
            for aid in sorted(self._state["analyses"]):
                value = self._state["analyses"][aid]
                snapshot = self._snapshots.get(value.get("capture_sha256"))
                if snapshot is None or snapshot["observations_sha256"] != value.get(
                    "observations_sha256"
                ):
                    fail("EVIDENCE_REVISION", "$", "Exact revision observations are unavailable.")
                for name, component in value.get("components", {}).items():
                    if component is not None and name != "policy":
                        self._member("attachments", component["attachment_id"])
                self._analysis(aid)
            for bid, baseline in self._state["baselines"].items():
                validate_baseline(baseline, self._state)
                self._validated_baselines.add(bid)
                self._counts["baselines"] += 1
            self._statuses = validate_reviews(self._state)
            self._complete = True
        except _MALFORMED:
            self._failed = True
            fail("EVIDENCE_GRAPH", "$", "Malformed or unsupported historical dependency graph.")
        except BaseException:
            self._failed = True
            raise

    def _snapshot(self, capture: str, observations: str | None = None) -> dict[str, Any]:
        snapshot = self._snapshots.get(capture)
        if snapshot is None:
            fail("EVIDENCE_ATTACHMENT", "$", "Attachment physical collection is unavailable.")
        if observations is not None and snapshot["observations_sha256"] != observations:
            fail("EVIDENCE_REVISION", "$", "Exact revision observations are unavailable.")
        return snapshot

    def _native(self, data: bytes) -> ValidatedArchitecture:
        # The key is calculated from actual, bounded input bytes, never a claimed
        # native/model/attachment digest. Only a successful native result is kept.
        input_sha = hashlib.sha256(data).hexdigest()
        if input_sha in self._native_inputs:
            return self._native_inputs[input_sha]
        validated = validate_bytes(data)
        previous = self._native_models.get(validated.sha256)
        if previous is None:
            # Cache bounds must not become stricter evidence-input limits. A
            # candidate import may be idempotent despite a new YAML presentation
            # at the workspace object ceiling. Validate it normally and retain
            # no additional cache entry when the operation's cache is full.
            if (
                len(self._native_models) < HISTORY_LIMITS.attachments
                and self._native_bytes + len(validated.canonical_json)
                <= HISTORY_LIMITS.workspace_bytes
            ):
                self._native_bytes += len(validated.canonical_json)
                self._native_models[validated.sha256] = validated
            self._counts["native_models"] += 1
        else:
            # A normalized digest never substitutes for checking actual content.
            _attachment_error(
                previous.canonical_json == validated.canonical_json,
                "Native model identity mismatch.",
            )
            validated = previous
        if len(self._native_inputs) < HISTORY_LIMITS.attachments:
            self._native_inputs[input_sha] = validated
        return validated

    def _dependency(self, kind: str, aid: str | None, snapshot: dict[str, Any]) -> dict[str, Any]:
        _attachment_error(aid is not None, "Required validated " + kind + " attachment is absent.")
        assert aid is not None
        dependency = self._member("attachments", aid)
        _attachment_error(
            dependency.get("kind") == kind, "Attachment dependency has the wrong type."
        )
        self._attachment(aid)
        _attachment_error(
            dependency["capture_sha256"] == snapshot["capture_sha256"]
            and dependency["observations_sha256"] == snapshot["observations_sha256"],
            "Attachment metadata or identity mismatch.",
        )
        return dependency

    def _attachment_body(
        self,
        kind: str,
        payload: dict[str, Any] | bytes,
        snapshot: dict[str, Any],
        dependencies: Mapping[str, str],
    ) -> dict[str, Any]:
        _attachment_error(kind in KINDS, "Unsupported analytical attachment type.")
        _attachment_error(
            set(dependencies) <= {"model", "mapping"}, "Unsupported attachment dependency."
        )
        references: dict[str, str | None] = {"model": None, "mapping": None}
        if kind == "model":
            data = payload if isinstance(payload, bytes) else canonical(payload)
            validated = self._native(data)
            retained = json.loads(validated.canonical_json)
            component_sha256 = validated.sha256
        else:
            _attachment_error(
                type(payload) is dict, "This attachment requires a JSON metadata object."
            )
            assert isinstance(payload, dict)
            retained = payload
            if kind == "enrichment":
                _validate_enrichment(retained, snapshot)
                component_sha256 = str(retained["enrichment_sha256"])
            else:
                model = self._dependency("model", dependencies.get("model"), snapshot)
                references["model"] = model["attachment_id"]
                validated = self._native(canonical(model["payload"]))
                _attachment_error(
                    validated.sha256 == model["component_sha256"], "Native model identity mismatch."
                )
                if kind == "mapping":
                    _reviewed(snapshot["observations"], validated, retained, CAPTURE_LIMITS)
                    self._counts["mappings"] += 1
                    component_sha256 = digest(retained)
                else:
                    mapping = self._dependency("mapping", dependencies.get("mapping"), snapshot)
                    if mapping["dependencies"]["model"] != model["attachment_id"]:
                        _standalone_attachment(
                            mapping, snapshot, {"model": model, "mapping": mapping}
                        )
                    _attachment_error(
                        mapping["dependencies"]["model"] == model["attachment_id"],
                        "Comparison mapping and selected model attachments differ.",
                    )
                    references["mapping"] = mapping["attachment_id"]
                    expected = compare_capture(
                        snapshot["observations"], validated, mapping["payload"]
                    )
                    self._counts["comparisons"] += 1
                    _attachment_error(
                        canonical(expected) == canonical(retained),
                        "Native comparison differs from independently replayed dependencies.",
                    )
                    component_sha256 = object_digest("otarchguard.native-comparison.v1", retained)
        result = {
            "attachment_version": 1,
            "kind": kind,
            "capture_sha256": snapshot["capture_sha256"],
            "observations_sha256": snapshot["observations_sha256"],
            "component_sha256": component_sha256,
            "dependencies": references,
            "payload": retained,
            "limitations": list(ATTACHMENT_LIMITATIONS),
        }
        result["attachment_id"] = "attachment-" + object_digest("otarchguard.attachment", result)
        return result

    def _attachment(self, aid: str) -> dict[str, Any]:
        value = self._member("attachments", aid)
        if aid in self._validated_attachments:
            return value
        _attachment_error(
            aid not in self._validating_attachments, "Attachment dependency graph is cyclic."
        )
        self._validating_attachments.add(aid)
        try:
            # Clone exactly once at this boundary, retaining every frozen strict
            # JSON type, Unicode, node, depth and output-resource check.
            checked = _clone(value)
            _attachment_error(
                type(checked.get("attachment_version")) is int
                and checked["attachment_version"] == 1
                and identity(checked.get("attachment_id"), "attachment-"),
                "Unsupported attachment version or identity.",
            )
            snapshot = self._snapshot(cast(str, checked.get("capture_sha256")))
            # Resolve every declared dependency even when the kind would not use
            # it, matching globally validating lifecycle behavior.
            dependencies = {
                name: self._member("attachments", dependency)["attachment_id"]
                for name, dependency in checked.get("dependencies", {}).items()
                if dependency is not None
            }
            expected = self._attachment_body(
                checked["kind"], checked["payload"], snapshot, dependencies
            )
            _attachment_error(
                canonical(checked) == canonical(expected),
                "Attachment metadata or identity mismatch.",
            )
            self._validated_attachments.add(aid)
            self._counts["attachments"] += 1
            return value
        except ModelError:
            raise
        except (
            ValueError,
            KeyError,
            TypeError,
            AttributeError,
            IndexError,
            OverflowError,
            RecursionError,
        ):
            fail("EVIDENCE_ATTACHMENT", "$", "Invalid or inconsistent analytical attachment.")
        finally:
            self._validating_attachments.discard(aid)

    def _semantics(
        self,
        snapshot: dict[str, Any],
        selected: Mapping[str, dict[str, Any]],
        options: dict[str, Any],
    ) -> dict[str, Any]:
        _revision_error(
            type(options) is dict
            and set(options) == {"require_complete_scan", "require_reviewed_mapping"},
            "Unsupported analysis options.",
        )
        _revision_error(
            all(type(option) is bool for option in options.values()),
            "Analysis options must be exact booleans.",
        )
        if self._semantics_base is None:
            self._semantics_base = build_semantics(snapshot)
        result = copy.deepcopy(self._semantics_base)
        enrichment = selected.get("enrichment")
        result["enrichment_version"] = (
            enrichment["payload"]["enrichment_version"] if enrichment else None
        )
        result["decoder_version"] = enrichment["payload"]["decoder_version"] if enrichment else None
        result["selected_enrichment_limits"] = (
            copy.deepcopy(enrichment["payload"]["limits"]) if enrichment else None
        )
        result["analysis_options"] = dict(options)
        return result

    def _revision_body(
        self,
        snapshot: dict[str, Any],
        attachments: Mapping[str, str],
        semantics: dict[str, Any] | None,
    ) -> dict[str, Any]:
        _revision_error(set(attachments) <= set(KINDS), "Unsupported analytical component.")
        selected: dict[str, dict[str, Any]] = {}
        components: dict[str, Any] = {kind: None for kind in KINDS}
        components["policy"] = None
        for kind, aid in attachments.items():
            component = self._attachment(aid)
            _revision_error(component.get("kind") == kind, "Analytical component type mismatch.")
            _attachment_error(
                component["capture_sha256"] == snapshot["capture_sha256"]
                and component["observations_sha256"] == snapshot["observations_sha256"],
                "Attachment metadata or identity mismatch.",
            )
            selected[kind] = component
            components[kind] = {"attachment_id": aid, "sha256": component["component_sha256"]}
        # An attachment's dependencies must also be the exact selected analytical
        # components; having another valid model somewhere in the workspace is
        # insufficient for a revision that selects a mapping or comparison.
        for component in selected.values():
            for dependency, aid in component["dependencies"].items():
                if aid is not None:
                    if dependency not in selected or selected[dependency]["attachment_id"] != aid:
                        # On a rejected cross-selection, obtain the exact native
                        # contract diagnostic rather than invent a new error code.
                        _standalone_attachment(
                            component,
                            snapshot,
                            {k: v for k, v in selected.items() if k in {"model", "mapping"}},
                        )
                    _attachment_error(
                        dependency in selected and selected[dependency]["attachment_id"] == aid,
                        "Required validated " + dependency + " attachment is absent."
                        if dependency not in selected
                        else "Attachment metadata or identity mismatch.",
                    )
        if semantics is None:
            options = {"require_complete_scan": False, "require_reviewed_mapping": False}
            semantics = self._semantics(snapshot, selected, options)
        else:
            semantics = _clone(semantics)
            options = semantics["analysis_options"]
        expected = self._semantics(snapshot, selected, options)
        _revision_error(
            canonical(semantics) == canonical(expected),
            "Unsupported or inconsistent producer semantics; "
            "a source digest alone grants no authority.",
        )
        if options["require_complete_scan"]:
            observations = snapshot["observations"]
            _revision_error(
                observations["coverage"]["complete_file_scan"] is True
                and observations["capture"]["unknown_blocks"] == 0,
                "The selected analysis requires a complete supported container scan.",
            )
        if options["require_reviewed_mapping"]:
            mapping = selected.get("mapping")
            _revision_error(
                mapping is not None, "The selected analysis requires an owner-reviewed mapping."
            )
            assert mapping is not None
            _revision_error(
                all(p["decision"] != "PENDING" for p in mapping["payload"]["proposals"]),
                "The selected analysis forbids pending association decisions.",
            )
        result = {
            "analysis_version": 1,
            "capture_sha256": snapshot["capture_sha256"],
            "observations_sha256": snapshot["observations_sha256"],
            "components": components,
            "producer_semantics": semantics,
            "producer_semantics_sha256": object_digest(
                "otarchguard.producer-semantics.v1", semantics
            ),
            "limitations": list(REVISION_LIMITATIONS),
        }
        result["analysis_id"] = "analysis-" + object_digest("otarchguard.analysis", result)
        return result

    def _analysis(self, aid: str) -> None:
        if aid in self._validated_analyses:
            return
        try:
            value = _clone(self._member("analyses", aid))
            _revision_error(
                type(value.get("analysis_version")) is int
                and value["analysis_version"] == 1
                and identity(value.get("analysis_id"), "analysis-"),
                "Unsupported analytical revision version or identity.",
            )
            snapshot = self._snapshots.get(cast(str, value.get("capture_sha256")))
            if snapshot is None or snapshot["observations_sha256"] != value.get(
                "observations_sha256"
            ):
                fail("EVIDENCE_REVISION", "$", "Exact revision observations are unavailable.")
            components = {
                name: self._member("attachments", component["attachment_id"])["attachment_id"]
                for name, component in value.get("components", {}).items()
                if component is not None and name != "policy"
            }
            expected = self._revision_body(snapshot, components, value["producer_semantics"])
            _revision_error(
                canonical(value) == canonical(expected),
                "Analytical revision metadata or identity mismatch.",
            )
            self._validated_analyses.add(aid)
            self._counts["analyses"] += 1
        except (
            ValueError,
            KeyError,
            TypeError,
            AttributeError,
            IndexError,
            OverflowError,
            RecursionError,
        ):
            fail("EVIDENCE_REVISION", "$", "Invalid, stale or unsupported analytical revision.")

    def build_attachment(
        self,
        kind: str,
        payload: dict[str, Any] | bytes,
        snapshot_id: str,
        model: str | None = None,
        mapping: str | None = None,
    ) -> dict[str, Any]:
        self.validate()
        snapshot = self._member("snapshots", snapshot_id)
        dependencies = {
            k: v for k, v in {"model": model, "mapping": mapping}.items() if v is not None
        }
        for aid in dependencies.values():
            self._member("attachments", aid)
        try:
            # Detach caller input once before any memoized result can be used.
            checked = payload if isinstance(payload, bytes) else _clone(payload)
            return _clone(self._attachment_body(kind, checked, snapshot, dependencies))
        except (
            ValueError,
            KeyError,
            TypeError,
            AttributeError,
            IndexError,
            OverflowError,
            RecursionError,
        ):
            fail("EVIDENCE_ATTACHMENT", "$", "Invalid or inconsistent analytical attachment.")

    def build_revision(
        self,
        snapshot_id: str,
        components: Mapping[str, str] | None = None,
        semantics: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.validate()
        try:
            return _clone(
                self._revision_body(
                    self._member("snapshots", snapshot_id), components or {}, semantics
                )
            )
        except (
            ValueError,
            KeyError,
            TypeError,
            AttributeError,
            IndexError,
            OverflowError,
            RecursionError,
        ):
            fail(
                "EVIDENCE_REVISION",
                "$",
                "Invalid, stale or unsupported analytical revision inputs.",
            )

    def add(self, kind: str, value: dict[str, Any]) -> None:
        """Validate one copy-on-write addition without revalidating unchanged data."""
        self.validate()
        if kind not in _KINDS:
            fail("EVIDENCE_OBJECT", "$", "Unsupported historical object kind.")
        checked = _clone(value)
        singular = {
            "snapshots": "snapshot",
            "attachments": "attachment",
            "analyses": "analysis",
            "baselines": "baseline",
            "reviews": "review",
        }[kind]
        oid = checked[singular + "_id"]
        previous = self._state[kind].get(oid)
        if previous is not None:
            if canonical(previous) != canonical(checked):
                fail("EVIDENCE_EXISTS", "$", "Existing evidence cannot be overwritten.")
            return
        check_limit("history_" + kind, len(self._state[kind]) + 1, getattr(HISTORY_LIMITS, kind))
        original = self._state
        self._state = {**original, kind: {**original[kind], oid: checked}}
        try:
            if kind == "snapshots":
                validate_snapshot(checked)
                capture = checked["capture_sha256"]
                if capture in self._snapshots:
                    fail(
                        "EVIDENCE_DUPLICATE_CAPTURE",
                        "$",
                        "Physical collection already exists; create a revision.",
                    )
                self._snapshots[capture] = checked
                self._counts["snapshots"] += 1
            elif kind == "attachments":
                self._attachment(oid)
            elif kind == "analyses":
                self._analysis(oid)
            elif kind == "baselines":
                validate_baseline(checked, self._state)
                self._validated_baselines.add(oid)
                self._counts["baselines"] += 1
                self._statuses = validate_reviews(self._state)
            else:
                self._statuses = validate_reviews(self._state)
        except BaseException:
            # A failed prospective operation cannot leave a reusable success
            # capability. The caller must discard this context after failure.
            self._complete = False
            self._failed = True
            self._state = original
            raise
