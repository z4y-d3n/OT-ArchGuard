"""Shared pre-allocation XML budgets. No DTD, entity, PI or resource fetching."""

import re
from typing import Protocol
from xml.etree import ElementTree as ET
from xml.parsers import expat

from otarchguard.diagnostics import check_limit, fail
from otarchguard.ingestion.tabular import _safe_text


class XmlLimits(Protocol):
    @property
    def xml_depth(self) -> int: ...
    @property
    def xml_elements(self) -> int: ...
    @property
    def xml_text(self) -> int: ...
    @property
    def text(self) -> int: ...


class XmlBudget:
    def __init__(
        self, limits: XmlLimits, *, prefix: str = "graph", code: str = "IMPORT_GRAPH_XML"
    ) -> None:
        self.limits = limits
        self.prefix = prefix
        self.code = code
        self.elements = 0
        self.characters = 0

    def parse(self, data: bytes) -> ET.Element:
        # UTF-8 only prevents alternate-encoding bypasses of lexical security checks.
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            fail(self.code, "$", "XML must use UTF-8.")
        declaration = re.match(r"<\?xml\s+[^?]*encoding=['\"]([^'\"]+)", text)
        if declaration and declaration[1].lower() not in {"utf-8", "utf8"}:
            fail(self.code, "$", "Only UTF-8 XML is supported.")
        _safe_text(text)
        builder = ET.TreeBuilder()
        parser = expat.ParserCreate(namespace_separator="}")
        depth = 0

        def name(value: str) -> str:
            return "{" + value if "}" in value else value

        def start(tag: str, attributes: dict[str, str]) -> None:
            nonlocal depth
            depth += 1
            self.elements += 1
            check_limit(f"{self.prefix}_xml_depth", depth, self.limits.xml_depth)
            check_limit(f"{self.prefix}_xml_elements", self.elements, self.limits.xml_elements)
            check_limit(f"{self.prefix}_xml_attributes", len(attributes), 64)
            check_limit(f"{self.prefix}_xml_name", len(tag), self.limits.text)
            self.characters += len(tag)
            for key, value in attributes.items():
                _safe_text(value)
                check_limit(f"{self.prefix}_xml_name", len(key), self.limits.text)
                check_limit(f"{self.prefix}_text", len(value), self.limits.text)
                self.characters += len(key) + len(value)
            check_limit(f"{self.prefix}_xml_text", self.characters, self.limits.xml_text)
            builder.start(name(tag), {name(k): v for k, v in attributes.items()})

        def namespace(prefix: str | None, uri: str | None) -> None:
            prefix, uri = prefix or "", uri or ""
            _safe_text(uri)
            check_limit(f"{self.prefix}_xml_name", len(prefix), self.limits.text)
            check_limit(f"{self.prefix}_xml_name", len(uri), self.limits.text)
            self.characters += len(prefix) + len(uri)
            check_limit(f"{self.prefix}_xml_text", self.characters, self.limits.xml_text)

        def end(tag: str) -> None:
            nonlocal depth
            builder.end(name(tag))
            depth -= 1

        def characters(value: str) -> None:
            _safe_text(value)
            self.characters += len(value)
            check_limit(f"{self.prefix}_xml_text", self.characters, self.limits.xml_text)
            builder.data(value)

        def forbidden(*args: object) -> None:
            fail(self.code, "$", "DTD, entities and processing instructions are forbidden.")

        parser.StartElementHandler = start
        parser.StartNamespaceDeclHandler = namespace
        parser.EndElementHandler = end
        parser.CharacterDataHandler = characters
        parser.StartDoctypeDeclHandler = forbidden
        parser.EntityDeclHandler = forbidden
        parser.ExternalEntityRefHandler = lambda *args: 0
        parser.ProcessingInstructionHandler = forbidden
        try:
            parser.Parse(text, True)
            return builder.close()
        except (expat.ExpatError, ValueError):
            fail(self.code, "$", "Malformed or unsupported XML document.")
