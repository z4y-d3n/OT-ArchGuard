"""Bounded UTF-8 YAML event parsing without YAML object constructors."""

import re
from collections.abc import Iterator
from pathlib import Path

import yaml
from yaml.events import (
    AliasEvent,
    DocumentStartEvent,
    Event,
    MappingEndEvent,
    MappingStartEvent,
    ScalarEvent,
    SequenceEndEvent,
    SequenceStartEvent,
)
from yaml.tokens import DirectiveToken

from otarchguard.contract import RESOURCE_LIMITS, DiagnosticCategory, ResourceLimits
from otarchguard.diagnostics import check_limit, fail

type YamlValue = None | bool | int | str | list[YamlValue] | dict[str, YamlValue]

_INTEGER = re.compile(r"-?(0|[1-9][0-9]*)", re.ASCII)
_FLOAT = re.compile(
    r"[-+]?(?:[0-9]+\.[0-9]*|\.[0-9]+)(?:[eE][-+]?[0-9]+)?|[-+]?[0-9]+[eE][-+]?[0-9]+"
)
_SPECIAL_FLOAT = re.compile(r"[-+]?\.(?:inf|nan)", re.IGNORECASE | re.ASCII)


def _reject_directives(source: str) -> None:
    for token in yaml.scan(source, Loader=yaml.SafeLoader):
        if isinstance(token, DirectiveToken):
            fail("YAML_FEATURE", "$", "YAML directives are forbidden.")


def _scalar(event: ScalarEvent, path: str) -> YamlValue:
    value = event.value
    if event.style is not None:
        return value
    if value in ("true", "false"):
        return value == "true"
    if value in ("null", "~", ""):
        return None
    if _INTEGER.fullmatch(value):
        try:
            return int(value)
        except ValueError:
            fail("INVALID_VALUE", path, "Integer exceeds the interpreter's safe digit limit.")
    if _FLOAT.fullmatch(value) or _SPECIAL_FLOAT.fullmatch(value):
        fail("TYPE_MISMATCH", path, "Floating-point scalars are not accepted; quote intended text.")
    return value


def _build(event: Event, events: Iterator[Event], path: str) -> YamlValue:
    if isinstance(event, ScalarEvent):
        return _scalar(event, path)
    if isinstance(event, SequenceStartEvent):
        items: list[YamlValue] = []
        for child in events:
            if isinstance(child, SequenceEndEvent):
                return items
            items.append(_build(child, events, f"{path}[{len(items)}]"))
    if isinstance(event, MappingStartEvent):
        mapping: dict[str, YamlValue] = {}
        for key_event in events:
            if isinstance(key_event, MappingEndEvent):
                return mapping
            if not isinstance(key_event, ScalarEvent):
                fail("TYPE_MISMATCH", path, "Mapping keys must be string scalars.")
            key = _scalar(key_event, path)
            if not isinstance(key, str):
                fail("TYPE_MISMATCH", path, "Mapping keys must be strings.")
            # Never echo arbitrary keys in messages. Field paths retain their location.
            child_path = f"{path}.{key}"
            if key == "<<":
                fail("YAML_FEATURE", child_path, "YAML merge keys are forbidden.")
            if key in mapping:
                fail("DUPLICATE_KEY", child_path, "Duplicate mapping key.")
            mapping[key] = _build(next(events), events, child_path)
    fail("YAML_SYNTAX", path, "Expected a scalar, sequence or mapping.")


def load_bytes(data: bytes, limits: ResourceLimits = RESOURCE_LIMITS) -> YamlValue:
    """Parse one bounded document; return primitives only, not a validated model."""
    check_limit("input_bytes", len(data), limits.input_bytes)
    try:
        source = data.decode("utf-8")
    except UnicodeDecodeError:
        fail("YAML_SYNTAX", "$", "Input must be UTF-8.")
    try:
        depth = documents = 0
        for count, event in enumerate(yaml.parse(source, Loader=yaml.SafeLoader), 1):
            check_limit("parser_events", count, limits.parser_events)
            if isinstance(event, DocumentStartEvent):
                documents += 1
                if documents > 1:
                    fail("MULTIPLE_DOCUMENTS", "$", "Exactly one YAML document is required.")
            if isinstance(event, AliasEvent) or getattr(event, "anchor", None) is not None:
                fail("YAML_FEATURE", "$", "YAML anchors and aliases are forbidden.")
            if getattr(event, "tag", None) is not None:
                fail("YAML_FEATURE", "$", "Explicit YAML tags are forbidden.")
            if isinstance(event, (MappingStartEvent, SequenceStartEvent)):
                depth += 1
                check_limit("nesting_depth", depth, limits.nesting_depth)
            elif isinstance(event, (MappingEndEvent, SequenceEndEvent)):
                depth -= 1
        if documents != 1:
            fail("YAML_SYNTAX", "$", "Exactly one nonempty YAML document is required.")
        # Also catches unknown directives that the YAML parser would otherwise ignore.
        # Scan only after depth/event checks; no complete token collection is retained.
        _reject_directives(source)
        events = iter(yaml.parse(source, Loader=yaml.SafeLoader))
        for event in events:
            if isinstance(event, DocumentStartEvent):
                return _build(next(events), events, "$")
    except yaml.MarkedYAMLError as error:
        # Recognize directives even when their requested YAML version prevents
        # the parser from emitting a DocumentStartEvent.
        try:
            _reject_directives(source)
        except yaml.YAMLError:
            pass
        mark = error.problem_mark
        fail(
            "YAML_SYNTAX",
            "$",
            "Malformed YAML; check syntax at the reported location.",
            line=mark.line + 1 if mark is not None else None,
            column=mark.column + 1 if mark is not None else None,
        )
    except yaml.YAMLError:
        fail("YAML_SYNTAX", "$", "Malformed YAML.")
    fail("YAML_SYNTAX", "$", "No document content.")


def load_file(path: Path, limits: ResourceLimits = RESOURCE_LIMITS) -> YamlValue:
    """Read at most ceiling+1 bytes, including when file size changes during reading."""
    try:
        with path.open("rb") as stream:
            data = stream.read(limits.input_bytes + 1)
    except OSError:
        fail("READ_ERROR", "$", "Cannot read the architecture file.", DiagnosticCategory.IO_ERROR)
    return load_bytes(data, limits)
