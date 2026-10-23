"""Capture bounded installed native contract evidence; compare without updating baselines."""

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sysconfig
from pathlib import Path
from typing import Any

import yaml

from otarchguard.api import validate_file
from otarchguard.reporting import architecture_svg

ROOT = Path(__file__).resolve().parents[1]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def capture(output: Path) -> dict[str, Any]:
    """Require a fresh directory. Every native operation has a 30-second bound."""
    output.mkdir(parents=True, exist_ok=False)
    console = Path(sysconfig.get_path("scripts")) / (
        "otarchguard.exe" if os.name == "nt" else "otarchguard"
    )
    if not console.is_file():
        raise RuntimeError("A regular installed native console is required")
    source = ROOT / "tests/fixtures/minimal-valid.yaml"
    sources = {"minimal": source, "mixed": ROOT / "examples/trace/communication.yaml"}
    for name in ("missing_permit", "explicit_deny", "absent"):
        raw = yaml.safe_load(source.read_bytes())
        raw["rules"] = [] if name != "explicit_deny" else raw["rules"]
        if name == "explicit_deny":
            raw["rules"][0]["effect"] = "deny"
        if name == "absent":
            raw["transport_edges"] = []
        path = output / (name + ".yaml")
        path.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8", newline="\n")
        sources[name] = path
    inputs = {}
    for name, path in sources.items():
        snap = validate_file(path)
        inputs[name] = {"input_sha256": digest(path.read_bytes()), "model_sha256": snap.sha256}
        (output / (name + "-canonical.json")).write_bytes(snap.canonical_json)
        (output / (name + ".svg")).write_bytes(architecture_svg(snap).encode("utf-8"))
    cases: list[tuple[str, list[str]]] = []
    for command in ("validate", "check", "exposure", "compare", "trace"):
        args = [command, str(source)]
        if command == "compare":
            args += [str(source)]
        if command in {"compare", "exposure"}:
            args += ["--scenario", "engineering_scope"]
        if command == "trace":
            args += ["--source", "eng", "--service", "svc_plc"]
        cases += [(command + "-help", [command, "--help"]), (command, args)]
        for suffix, options in (
            ("unknown", ["--unknown-contract-option"]),
            ("missing-value", ["--report"]),
            ("bad-enum", ["--report-format", "xml"]),
        ):
            cases.append((command + "-" + suffix, [*args, *options]))
        for format in ("json", "html"):
            report = output / (command + "." + format)
            cases.append(
                (
                    command + "-" + format,
                    [*args, "--report", str(report), "--report-format", format],
                )
            )
    for name in ("mixed", "missing_permit", "explicit_deny", "absent"):
        for evidence in (False, True):
            label = f"trace-{name}-policy-{int(evidence)}"
            cases.append(
                (
                    label,
                    [
                        "trace",
                        str(sources[name]),
                        "--source",
                        "eng",
                        "--service",
                        "svc_plc",
                        *(["--policy-evidence"] if evidence else []),
                        "--report",
                        str(output / (label + ".html")),
                    ],
                )
            )
    for name in ("invalid-missing-reference", "unsupported-model"):
        report = output / (name + ".sentinel")
        report.write_bytes(b"\x00\xffprior evidence\r\n")
        cases.append(
            (
                name,
                [
                    "validate",
                    str(ROOT / "tests/fixtures" / (name + ".yaml")),
                    "--report",
                    str(report),
                ],
            )
        )
    exits = {}
    environment = {
        **os.environ,
        "NO_COLOR": "1",
        "TERM": "dumb",
        "COLUMNS": "100",
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
    }
    for label, args in cases:
        result = subprocess.run(
            [str(console), *args], cwd=ROOT, env=environment, capture_output=True, timeout=30
        )
        (output / (label + ".stdout")).write_bytes(result.stdout)
        (output / (label + ".stderr")).write_bytes(result.stderr)
        exits[label] = result.returncode
        expected = (
            2
            if any(
                x in label
                for x in (
                    "unknown",
                    "missing-value",
                    "bad-enum",
                    "invalid-missing",
                    "unsupported-model",
                )
            )
            else 0
        )
        if result.returncode != expected or b"Traceback" in result.stderr:
            raise RuntimeError(f"Unexpected native contract outcome: {label}")
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "production_sha256": {
            p.name: digest(p.read_bytes()) for p in sorted((ROOT / "src/otarchguard").glob("*.py"))
        },
        "inputs": inputs,
        "exits": exits,
        "artifacts": {p.name: digest(p.read_bytes()) for p in sorted(output.iterdir())},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "output", type=Path, help="New directory; existing evidence is never replaced"
    )
    parser.add_argument("--compare", type=Path, help="Existing capture manifest.json")
    args = parser.parse_args()
    record = capture(args.output)
    (args.output / "manifest.json").write_text(
        json.dumps(record, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    if args.compare:
        baseline = json.loads(args.compare.read_bytes())
        for field in ("production_sha256", "inputs", "exits", "artifacts"):
            if record[field] != baseline[field]:
                raise RuntimeError(f"Unexplained contract difference: {field}; baseline preserved")
    print(f"Captured {len(record['exits'])} native cases; {len(record['artifacts'])} artifacts")


if __name__ == "__main__":
    main()
