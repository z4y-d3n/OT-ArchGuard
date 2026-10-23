"""Run every documented example through the installed CLI; no network or extra packages."""

import json
import os
import subprocess
import sysconfig
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(arguments: list[str], expected: int) -> dict[str, object]:
    executable = Path(sysconfig.get_path("scripts")) / (
        "otarchguard.exe" if os.name == "nt" else "otarchguard"
    )
    if not executable.is_file():
        raise FileNotFoundError(f"Installed console launcher missing: {executable}")
    result = subprocess.run(
        [str(executable), *arguments], capture_output=True, text=True, check=False, timeout=30
    )
    if result.returncode != expected or result.stderr:
        raise RuntimeError(
            f"Unexpected result for {arguments}: {result.returncode} {result.stderr}"
        )
    payload: dict[str, object] = json.loads(result.stdout)
    print(f"exit={result.returncode} {' '.join(arguments)}")
    return payload


def main() -> None:
    output = ROOT / "output/examples"
    output.mkdir(parents=True, exist_ok=True)
    trace_model = ROOT / "examples/trace/communication.yaml"
    for listener, outcomes in (
        ("svc_allowed", {True}),
        ("svc_blocked", {False}),
        ("svc_absent", {False}),
        ("svc_plc", {True, False}),
    ):
        result = run(
            [
                "trace",
                str(trace_model),
                "--source",
                "eng",
                "--service",
                listener,
                "--policy-evidence",
                "--report",
                str(output / f"trace-{listener}.html"),
            ],
            0,
        )
        intervals = result["intervals"]
        assert isinstance(intervals, list)
        assert {item["reachable"] for item in intervals} == outcomes
    for family, scenario in (
        ("segmented-plant", "plant_scope"),
        ("flat-plant", "plant_scope"),
        ("remote-support", "support_scope"),
    ):
        directory = ROOT / "examples" / family
        for path in sorted(directory.glob("*.yaml")):
            expected = 0 if path.stem == "baseline" else 1
            stem = f"{family}-{path.stem}"
            run(
                [
                    "validate",
                    str(path),
                    "--report",
                    str(output / f"{stem}-validation.json"),
                    "--report-format",
                    "json",
                ],
                0,
            )
            run(["check", str(path), "--report", str(output / f"{stem}-check.html")], expected)
            run(
                [
                    "exposure",
                    str(path),
                    "--scenario",
                    scenario,
                    "--report",
                    str(output / f"{stem}-exposure.json"),
                    "--report-format",
                    "json",
                ],
                expected,
            )
        for format in ("json", "html"):
            run(
                [
                    "compare",
                    str(directory / "baseline.yaml"),
                    str(directory / "proposed.yaml"),
                    "--scenario",
                    scenario,
                    "--report",
                    str(output / f"{family}-comparison.{format}"),
                    "--report-format",
                    format,
                ],
                1,
            )


if __name__ == "__main__":
    main()
