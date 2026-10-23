"""Adversarial graphical sources exercise real default and reduced resource limits."""

import base64
import zlib
from dataclasses import replace
from pathlib import Path

import pytest

from otarchguard.diagnostics import ModelError
from otarchguard.ingestion.graphical import GRAPH_LIMITS, GraphLimits, read_graph
from otarchguard.ingestion.records import GraphProfile
from otarchguard.ingestion.workflow import create_draft
from tools.synthetic_graphs import compressed_model, drawio_xml, graph_profile, graphml_xml


def reject(
    tmp_path: Path,
    text: str | bytes,
    adapter: str = "drawio",
    *,
    code: str | None = None,
    limits: GraphLimits = GRAPH_LIMITS,
) -> ModelError:
    file = tmp_path / ("hostile." + adapter)
    file.write_bytes(text.encode() if isinstance(text, str) else text)
    with pytest.raises(ModelError) as error:
        read_graph(file, adapter, limits)
    if code:
        assert error.value.diagnostics[0].code == code
    return error.value


@pytest.mark.parametrize("adapter", ["drawio", "graphml"])
@pytest.mark.parametrize(
    "attack",
    [
        "dtd",
        "entity",
        "pi",
        "utf16",
        "bad_utf8",
        "wrong_root",
        "depth",
        "elements",
        "attributes",
        "namespace",
        "source_bytes",
    ],
)
def test_xml_security(tmp_path: Path, adapter: str, attack: str) -> None:
    xml = drawio_xml() if adapter == "drawio" else graphml_xml()
    limits = GRAPH_LIMITS
    if attack == "dtd":
        xml = '<!DOCTYPE x SYSTEM "file:///never-read">' + xml
    elif attack == "entity":
        xml = '<!DOCTYPE x [<!ENTITY x "expansion">]>' + xml
    elif attack == "pi":
        xml = '<?instruction execute="no"?>' + xml
    elif attack == "utf16":
        reject(tmp_path, xml.encode("utf-16"), adapter)
        return
    elif attack == "bad_utf8":
        reject(tmp_path, xml.encode() + b"\xff", adapter)
        return
    elif attack == "wrong_root":
        xml = '<svg xmlns="http://www.w3.org/2000/svg"/>'
    elif attack == "depth":
        xml = "<a>" * 25 + "</a>" * 25
    elif attack == "elements":
        xml = "<a>" + "<b/>" * 150_001 + "</a>"
    elif attack == "attributes":
        xml = "<a " + " ".join(f'k{i}="x"' for i in range(65)) + "/>"
    elif attack == "namespace":
        xml = '<a xmlns:p="' + "n" * 4000 + '">' + "<p:b/>" * 2200 + "</a>"
    else:
        xml = "x" * (1024 * 1024 + 1)
    reject(tmp_path, xml, adapter, limits=limits)


@pytest.mark.parametrize("payload", ["!bad", "====", "AA=", "AB==", "", "YWJj\n", "YWJj=", "é"])
def test_base64_rejected(tmp_path: Path, payload: str) -> None:
    reject(tmp_path, f'<mxfile><diagram id="p">{payload}</diagram></mxfile>')


def raw_stream(data: bytes) -> bytes:
    compressor = zlib.compressobj(wbits=-15)
    return compressor.compress(data) + compressor.flush()


@pytest.mark.parametrize(
    "attack",
    [
        "truncated",
        "trailing",
        "concatenated",
        "zlib",
        "gzip",
        "corrupt",
        "percent",
        "utf8",
        "double",
        "nested",
        "entity",
        "bomb",
    ],
)
def test_compressed_hostile_payload(tmp_path: Path, attack: str) -> None:
    payload = raw_stream(b"%3CmxGraphModel%3E%3Croot%2F%3E%3C%2FmxGraphModel%3E")
    if attack == "truncated":
        payload = payload[:-1]
    elif attack == "trailing":
        payload += b"trailing"
    elif attack == "concatenated":
        payload += payload
    elif attack == "zlib":
        payload = zlib.compress(b"text")
    elif attack == "gzip":
        compressor = zlib.compressobj(wbits=31)
        payload = compressor.compress(b"text") + compressor.flush()
    elif attack == "corrupt":
        payload = b"\xff\xff\xff"
    elif attack == "percent":
        payload = raw_stream(b"%3CmxGraphModel%XX")
    elif attack == "utf8":
        payload = raw_stream(b"%FF")
    elif attack == "double":
        payload = raw_stream(b"%253CmxGraphModel%253E")
    elif attack == "nested":
        payload = base64.b64decode(
            compressed_model('<mxfile><diagram id="p">abc</diagram></mxfile>')
        )
    elif attack == "entity":
        payload = base64.b64decode(
            compressed_model('<!DOCTYPE x [<!ENTITY x "y">]><mxGraphModel><root/></mxGraphModel>')
        )
    elif attack == "bomb":
        payload = raw_stream(b"A" * (GRAPH_LIMITS.page_bytes + 1))
    text = base64.b64encode(payload).decode()
    reject(
        tmp_path,
        f'<mxfile><diagram id="p">{text}</diagram></mxfile>',
        code="LIMIT_EXCEEDED" if attack == "bomb" else None,
    )


@pytest.mark.parametrize(
    "attack",
    [
        "page_duplicate",
        "cell_duplicate",
        "cycle",
        "parent_missing",
        "plugin",
        "stencil",
        "svg",
        "attachment",
        "bad_flag",
        "contradiction",
    ],
)
def test_drawio_unsupported(tmp_path: Path, attack: str) -> None:
    xml = drawio_xml(pages=2)
    if attack == "page_duplicate":
        xml = xml.replace('id="page2"', 'id="page1"')
    elif attack == "cell_duplicate":
        xml = xml.replace('id="hmi"', 'id="plc"')
    elif attack == "cycle":
        xml = xml.replace('id="0"', 'id="0" parent="1"')
    elif attack == "parent_missing":
        xml = xml.replace('parent="area_a"', 'parent="missing"')
    elif attack == "plugin":
        xml = xml.replace("<mxfile>", '<mxfile plugins="custom">')
    elif attack == "stencil":
        xml = xml.replace('style="swimlane;', 'style="shape=stencil(abc);')
    elif attack in {"svg", "attachment"}:
        xml = xml.replace("</root>", f"<{attack}/></root>")
    elif attack == "bad_flag":
        xml = xml.replace('vertex="1"', 'vertex="yes"')
    else:
        xml = xml.replace("<mxfile>", '<mxfile compressed="true">')
    reject(tmp_path, xml)


@pytest.mark.parametrize(
    "attack",
    [
        "namespace",
        "nested",
        "port",
        "hyperedge",
        "extension",
        "node_duplicate",
        "key_duplicate",
        "unknown_key",
        "bad_default",
        "bad_direction",
        "missing_direction",
        "number",
        "integer",
        "boolean",
    ],
)
def test_graphml_unsupported(tmp_path: Path, attack: str) -> None:
    xml = graphml_xml()
    if attack == "namespace":
        xml = xml.replace('xmlns="http://graphml.graphdrawing.org/xmlns"', 'xmlns="urn:other"')
    elif attack in {"nested", "port", "hyperedge", "extension"}:
        content = {
            "nested": '<graph id="nested" edgedefault="directed"/>',
            "port": '<port name="tcp"/>',
            "hyperedge": "<hyperedge/>",
            "extension": '<svg xmlns="urn:extension"/>',
        }[attack]
        xml = xml.replace("</node>", content + "</node>", 1)
    elif attack == "node_duplicate":
        xml = xml.replace('id="hmi"', 'id="plc"')
    elif attack == "key_duplicate":
        xml = xml.replace('id="role"', 'id="label"')
    elif attack == "unknown_key":
        xml = xml.replace('key="label"', 'key="unknown"')
    elif attack == "bad_default":
        xml = xml.replace("</default>", "</default><default>1</default>")
    elif attack == "bad_direction":
        xml = xml.replace('source="eng"', 'directed="both" source="eng"')
    elif attack == "missing_direction":
        xml = xml.replace('edgedefault="directed"', "")
    elif attack == "number":
        xml = xml.replace("0.10000000000000001", "NaN")
    elif attack == "integer":
        xml = xml.replace('attr.type="double"', 'attr.type="int"')
    else:
        xml = xml.replace('attr.type="double"', 'attr.type="boolean"')
    reject(tmp_path, xml, "graphml")


@pytest.mark.parametrize("adapter", ["drawio", "graphml"])
@pytest.mark.parametrize("budget", ["nodes", "edges", "pages", "text", "diagnostics"])
def test_resource_boundaries(tmp_path: Path, adapter: str, budget: str) -> None:
    xml = drawio_xml() if adapter == "drawio" else graphml_xml()
    limits = replace(GRAPH_LIMITS, **{budget: 0 if budget == "diagnostics" else 1})
    if budget == "pages":
        xml = (
            drawio_xml(pages=2)
            if adapter == "drawio"
            else xml.replace("</graphml>", '<graph id="other" edgedefault="directed"/></graphml>')
        )
    if budget == "diagnostics":
        xml = xml.replace('target="fw"', 'target="missing"')
    reject(tmp_path, xml, adapter, code="LIMIT_EXCEEDED", limits=limits)


def test_aggregate_decompression_and_unselected_pages(tmp_path: Path) -> None:
    xml = drawio_xml(compressed=True, pages=2)
    single = tmp_path / "single.drawio"
    single.write_text(drawio_xml(compressed=True))
    size = read_graph(single, "drawio").expanded_bytes
    reject(
        tmp_path,
        xml,
        limits=replace(GRAPH_LIMITS, expanded_bytes=size * 2 - 1),
        code="LIMIT_EXCEEDED",
    )
    xml = drawio_xml(pages=2).replace(
        "</mxfile>", '<diagram id="unselected">evil</diagram></mxfile>'
    )
    file = tmp_path / "unselected.drawio"
    file.write_text(xml)
    with pytest.raises(ModelError):
        create_draft(file, graph_profile("drawio"))


def test_real_default_node_and_page_limits(tmp_path: Path) -> None:
    reject(tmp_path, graphml_xml(count=1001), "graphml", code="LIMIT_EXCEEDED")
    reject(tmp_path, drawio_xml(compressed=True, pages=17), code="LIMIT_EXCEEDED")


def test_real_default_aggregate_expansion_limit(tmp_path: Path) -> None:
    # Each page fits 2 MiB; five percent-encoded whitespace pages exceed 8 MiB total.
    payload = compressed_model("<mxGraphModel><root>" + " " * 600_000 + "</root></mxGraphModel>")
    xml = (
        "<mxfile>"
        + "".join(f'<diagram id="p{i}">{payload}</diagram>' for i in range(5))
        + "</mxfile>"
    )
    reject(tmp_path, xml, code="LIMIT_EXCEEDED")


def test_private_key_alias_and_mapping_semantics(tmp_path: Path) -> None:
    file = tmp_path / "private.graphml"
    file.write_text(graphml_xml().replace('attr.name="role"', 'attr.name="password"'))
    with pytest.raises(ModelError) as error:
        create_draft(file, graph_profile("graphml"))
    assert error.value.diagnostics[0].code == "IMPORT_PRIVATE_FIELD"
    file.write_text(graphml_xml())
    data = graph_profile("graphml").model_dump(mode="json")
    data["tables"][0]["collection"] = "edges"
    with pytest.raises(ModelError):
        create_draft(file, GraphProfile.model_validate(data))
