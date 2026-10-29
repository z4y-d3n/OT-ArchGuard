"""Release audit: hostile late ZIP entries must precede every XML allocation."""

import io
import stat
import zipfile
from pathlib import Path

import pytest

from otarchguard.diagnostics import ModelError
from otarchguard.ingestion.records import DocumentProfile
from otarchguard.ingestion.workflow import create_draft
from otarchguard.ingestion.xlsx import read_workbook
from otarchguard.ingestion.xml_safe import XmlBudget
from tools.synthetic_documents import docx_parts, pptx_parts
from tools.synthetic_inventories import workbook_parts


def _hostile_package(adapter: str, attack: str) -> bytes:
    if adapter == "xlsx":
        parts = workbook_parts({"Inventory": [["id", "name"], ["a", "Fictional"]]})
    else:
        text_parts = docx_parts() if adapter == "docx" else pptx_parts()
        parts = {name: data.encode("utf-8") for name, data in text_parts.items()}
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in parts.items():
            archive.writestr(name, data)
        # The defect is deliberately last: checking only the first XML part
        # must not allocate a tree or disguise the intended rejection.
        info = zipfile.ZipInfo("docProps/core.xml")
        payload = b"<x/>"
        if attack == "traversal":
            info.filename = "../outside.xml"
        elif attack == "symlink":
            info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            payload = b"../../outside.xml"
        elif attack == "directory-payload":
            info.filename = "docProps/"
        elif attack == "ratio":
            info.compress_type = zipfile.ZIP_DEFLATED
            payload = b"<x>" + b"a" * 100_000 + b"</x>"
        elif attack == "nul":
            # Patch both local and central names after writing: ZipInfo's
            # constructor itself truncates a NUL name supplied directly.
            info.filename = "docProps/core.xmlX"
        else:
            raise AssertionError("Unknown finite security fixture")
        archive.writestr(info, payload)
    raw = stream.getvalue()
    if attack == "nul":
        assert raw.count(b"docProps/core.xmlX") == 2
        raw = raw.replace(b"docProps/core.xmlX", b"docProps/core.xml\x00")
    return raw


@pytest.mark.parametrize("adapter", ["xlsx", "docx", "pptx"])
@pytest.mark.parametrize("attack", ["traversal", "symlink", "directory-payload", "ratio", "nul"])
def test_late_archive_attack_rejected_before_any_xml_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, adapter: str, attack: str
) -> None:
    path = tmp_path / ("fictional." + adapter)
    raw = _hostile_package(adapter, attack)
    path.write_bytes(raw)

    def forbidden_tree(self: XmlBudget, data: bytes) -> None:
        raise AssertionError("XML allocation occurred before complete archive preflight")

    monkeypatch.setattr(XmlBudget, "parse", forbidden_tree)
    with pytest.raises(ModelError) as error:
        if adapter == "xlsx":
            read_workbook(path)
        else:
            profile = DocumentProfile.model_validate(
                {"profile_version": 4, "adapter": adapter, "select": ["*"], "tables": []}
            )
            create_draft(path, profile)
    diagnostic = error.value.diagnostics[0]
    if attack == "ratio":
        assert diagnostic.code == "LIMIT_EXCEEDED"
        assert "compression_ratio" in diagnostic.message
    elif attack == "directory-payload":
        assert diagnostic.code in {"IMPORT_XLSX_PART", "IMPORT_DOCUMENT_PART"}
    else:
        assert diagnostic.code in {"IMPORT_XLSX_ARCHIVE", "IMPORT_DOCUMENT_ARCHIVE"}
    assert path.read_bytes() == raw
    assert set(tmp_path.iterdir()) == {path}
