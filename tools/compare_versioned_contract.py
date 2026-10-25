"""Compare preserved native captures with explicit, exact version-only exceptions."""

import argparse
import hashlib
import html
import json
import re
from pathlib import Path
from typing import Any

OLD = "1.0.1"
NEW = "1.1.0"


def compare_json(before: bytes, after: bytes, old: str = OLD, new: str = NEW) -> None:
    """Only /engine_version may change; preserve every other value and byte."""
    left = json.loads(before)
    right = json.loads(after)
    if not isinstance(left, dict) or not isinstance(right, dict):
        raise ValueError("Changed JSON must be a version-bearing envelope")
    if left.get("engine_version") != old or right.get("engine_version") != new:
        raise ValueError("Unexpected /engine_version transition")
    expected = {**left, "engine_version": new}
    if json.dumps(expected, sort_keys=True) != json.dumps(right, sort_keys=True):
        raise ValueError("Non-version JSON difference")
    token = f'"engine_version": "{old}"'.encode()
    if (
        before.count(token) != 1
        or before.replace(token, token.replace(old.encode(), new.encode())) != after
    ):
        raise ValueError("Unexplained JSON serialization difference")


def compare_artifact(before: bytes, after: bytes, old: str = OLD, new: str = NEW) -> str:
    if before == after:
        return "EXACT_BYTES"
    if before.startswith(b"<!doctype html>"):
        left, right = before.decode("utf-8"), after.decode("utf-8")
        pattern = (
            r'(<section id="(?:json-evidence|json)">.*?<pre>)(.*?)'
            r"(</pre></details></section></main>)"
        )
        a, b = list(re.finditer(pattern, left, re.S)), list(re.finditer(pattern, right, re.S))
        if len(a) != 1 or len(b) != 1:
            raise ValueError("Expected exactly one complete HTML JSON appendix")
        compare_json(html.unescape(a[0][2]).encode(), html.unescape(b[0][2]).encode(), old, new)
        token = f"&quot;engine_version&quot;: &quot;{old}&quot;"
        appendix = a[0][2]
        if appendix.count(token) != 1:
            raise ValueError("Unexpected HTML engine token count")
        expected = (
            left[: a[0].start(2)]
            + appendix.replace(token, token.replace(old, new))
            + left[a[0].end(2) :]
        )
        if '<section id="json">' in left:
            header = f"<p>Status: complete; trace version 1; engine {old}; schema 1.</p>"
            if expected.count(header) != 1:
                raise ValueError("Unexpected trace version header")
            expected = expected.replace(header, header.replace(old, new))
        if expected != right:
            raise ValueError("Non-version HTML difference")
        return "ENGINE_VERSION_HTML"
    try:
        compare_json(before, after, old, new)
    except (ValueError, UnicodeError) as error:
        raise ValueError("Unexplained artifact difference") from error
    return "ENGINE_VERSION_JSON"


def compare_captures(
    baseline: Path,
    candidate: Path,
    *,
    old: str = OLD,
    new: str = NEW,
    allowed_module_changes: frozenset[str] = frozenset(),
) -> dict[str, Any]:
    if any(re.fullmatch(r"[a-z_]+\.py", name) is None for name in allowed_module_changes):
        raise ValueError("Module change exceptions must name exact native Python modules")
    before = {p.name: p.read_bytes() for p in baseline.iterdir() if p.is_file()}
    after = {p.name: p.read_bytes() for p in candidate.iterdir() if p.is_file()}
    if before.keys() != after.keys():
        raise ValueError("Capture file inventories differ")
    results = {}
    for name in sorted(before):
        if name == "manifest.json":
            left, right = json.loads(before[name]), json.loads(after[name])
            if left.keys() != right.keys():
                raise ValueError("Capture manifest fields differ")
            for record, files in ((left, before), (right, after)):
                actual = {n: hashlib.sha256(d).hexdigest() for n, d in files.items() if n != name}
                if record["artifacts"] != actual:
                    raise ValueError("Capture manifest hashes do not match actual bytes")
            for field in ("inputs", "exits"):
                if json.dumps(left[field], sort_keys=True) != json.dumps(
                    right[field], sort_keys=True
                ):
                    raise ValueError(f"Changed capture {field}")
            modules = set(left["production_sha256"])
            if modules != set(right["production_sha256"]):
                raise ValueError("Production module inventory changed")
            if not allowed_module_changes <= modules:
                raise ValueError("Module change exception is absent from the captured inventory")
            for module in modules - {"__init__.py"} - allowed_module_changes:
                if left["production_sha256"][module] != right["production_sha256"][module]:
                    raise ValueError(f"Production module changed: {module}")
            # Interpreter/platform are capture provenance, not analytical artifacts.
            if set(left) != {
                "python",
                "platform",
                "production_sha256",
                "inputs",
                "exits",
                "artifacts",
            }:
                raise ValueError("Unknown capture manifest field")
            results[name] = "VERIFIED_CAPTURE_PROVENANCE"
        else:
            try:
                results[name] = compare_artifact(before[name], after[name], old, new)
            except ValueError as error:
                raise ValueError(f"{name}: {error}") from error
    return {
        "status": "PASS",
        "baseline": str(baseline),
        "candidate": str(candidate),
        "artifacts": results,
        "count": len(results),
        "baseline_version": old,
        "candidate_version": new,
        "allowed_module_changes": sorted(allowed_module_changes),
        "allowlist": [
            "/engine_version",
            "HTML JSON appendix /engine_version",
            "trace HTML exact engine header",
            "capture provenance metadata",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--baseline-version", default=OLD)
    parser.add_argument("--candidate-version", default=NEW)
    parser.add_argument("--allow-module-change", action="append", default=[])
    args = parser.parse_args()
    result = compare_captures(
        args.baseline,
        args.candidate,
        old=args.baseline_version,
        new=args.candidate_version,
        allowed_module_changes=frozenset(args.allow_module_change),
    )
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Version-only compatibility PASS: {result['count']} files")


if __name__ == "__main__":
    main()
