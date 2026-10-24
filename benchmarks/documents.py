"""Offline document parsing, mapping, draft size and allocation measurements."""

import argparse
import cProfile
import hashlib
import json
import time
import tracemalloc
from dataclasses import asdict
from pathlib import Path
from types import CodeType
from typing import Any

from otarchguard.ingestion.documents import DOCUMENT_LIMITS, create_document_draft
from otarchguard.ingestion.records import DocumentProfile
from otarchguard.ingestion.workflow import serialize
from tools.synthetic_documents import docx_parts, package, pptx_parts


def samples(root: Path) -> list[dict[str, Any]]:
    root.mkdir(parents=True, exist_ok=False)
    results = []
    for count in (20, 150, 500):
        labels = [
            "Fictional engineering note " + hashlib.sha256(str(i).encode()).hexdigest()[:32]
            for i in range(count)
        ]
        for adapter in ("txt", "md", "docx", "pptx"):
            path = root / f"{adapter}-{count}.{adapter}"
            if adapter in {"txt", "md"}:
                table = (
                    "id=eng\nname=Engineering Station\nzone=alternate\n"
                    if adapter == "txt"
                    else "|id|name|zone|\n|---|---|---|\n|eng|Engineering Station|alternate|\n"
                )
                path.write_text("\n".join(labels) + "\n" + table, encoding="utf-8", newline="\n")
            else:
                parts = docx_parts() if adapter == "docx" else pptx_parts()
                if adapter == "docx":
                    main = "word/document.xml"
                    parts[main] = parts[main].replace(
                        "<w:sectPr/>",
                        "".join(
                            "<w:p><w:r><w:t>" + value + "</w:t></w:r></w:p>" for value in labels
                        )
                        + "<w:sectPr/>",
                    )
                else:
                    main = "ppt/slides/slide2.xml"
                    parts[main] = parts[main].replace(
                        "</p:txBody>",
                        "".join(
                            "<a:p><a:r><a:t>" + value + "</a:t></a:r></a:p>" for value in labels
                        )
                        + "</p:txBody>",
                        1,
                    )
                path.write_bytes(package(parts))
            profile = DocumentProfile.model_validate(
                dict(
                    profile_version=4,
                    adapter=adapter,
                    select=["*"],
                    tables=[
                        dict(
                            name="assets",
                            entity="asset",
                            collection={
                                "txt": "key-values",
                                "md": "table:1",
                                "docx": "word/document.xml/table:1",
                                "pptx": "slide:257/table:4",
                            }[adapter],
                            fields={
                                "id": {"path": "/id"},
                                "name": {"path": "/name"},
                                "zone_id": {"path": "/zone"},
                            },
                        )
                    ],
                )
            )
            times = []
            for _ in range(3):
                start = time.perf_counter()
                draft = create_document_draft(path, profile)
                times.append(time.perf_counter() - start)
            profiler = cProfile.Profile()
            profiler.runcall(create_document_draft, path, profile)
            # cProfile counters separate parser and shared mapping under profiling overhead.
            functions = {
                entry.code.co_name: entry.totaltime
                for entry in profiler.getstats()
                if isinstance(entry.code, CodeType)
            }
            tracemalloc.start()
            create_document_draft(path, profile)
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            assert draft.document
            results.append(
                dict(
                    adapter=adapter,
                    notes=count,
                    input_bytes=path.stat().st_size,
                    observations=len(draft.document.observations),
                    candidates=len(draft.candidates),
                    draft_bytes=len(serialize(draft)),
                    evidence=draft.document.summary,
                    samples_seconds=times,
                    median_seconds=sorted(times)[1],
                    peak_python_allocations=peak,
                    profiled_parse_seconds=functions.get("text", functions.get("ooxml")),
                    profiled_shared_mapping_seconds=functions.get("map_extracted"),
                    provenance="Exact located text retained in version-5 draft; "
                    "mixed project sidecar measured by installed walkthrough.",
                )
            )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = samples(args.output.with_suffix(""))
    args.output.write_text(
        json.dumps(
            dict(
                samples=result,
                limits=asdict(DOCUMENT_LIMITS),
            ),
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
