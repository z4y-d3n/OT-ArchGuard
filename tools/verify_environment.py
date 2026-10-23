"""Record and enforce regular installed-package identity on native CI interpreters."""

import argparse
import hashlib
import importlib.metadata as metadata
import json
import os
import platform
import subprocess
import sys
import sysconfig
from pathlib import Path

import otarchguard

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    distribution = metadata.distribution("otarchguard")
    module = Path(otarchguard.__file__).resolve().parent
    expected = Path(str(distribution.locate_file("otarchguard"))).resolve()
    if module != expected or module.is_relative_to(ROOT / "src"):
        raise RuntimeError("Verification requires the regular installed package")
    direct = json.loads(distribution.read_text("direct_url.json") or "{}")
    if direct.get("dir_info", {}).get("editable", False):
        raise RuntimeError("Editable installations are not acceptance evidence")
    source_hashes = {
        p.relative_to(ROOT / "src/otarchguard").as_posix(): hashlib.sha256(
            p.read_bytes()
        ).hexdigest()
        for p in (ROOT / "src/otarchguard").rglob("*.py")
    }
    installed_hashes = {
        p.relative_to(module).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in module.rglob("*.py")
    }
    if installed_hashes != source_hashes:
        raise RuntimeError("Installed production modules differ from reviewed source")
    console = Path(sysconfig.get_path("scripts")) / (
        "otarchguard.exe" if os.name == "nt" else "otarchguard"
    )
    if not console.is_file():
        raise RuntimeError("Active interpreter's installed console is missing")
    result = subprocess.run(
        [str(console), "--version"], capture_output=True, text=True, check=False, timeout=30
    )
    if result.returncode or result.stderr or result.stdout.strip() != otarchguard.__version__:
        raise RuntimeError("Native installed console version check failed")
    record = {
        "python": platform.python_version(),
        "python_build": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "executable": sys.executable,
        "prefix": sys.prefix,
        "scripts": sysconfig.get_path("scripts"),
        "console": str(console),
        "module": str(module),
        "distribution": distribution.version,
        "application": otarchguard.__version__,
        "direct_url": direct,
        "installed_module_sha256": installed_hashes,
        "source_module_sha256": source_hashes,
        "native_version_exit": result.returncode,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(
        f"Verified {distribution.version}; Python {platform.python_version()}; "
        f"{platform.system()} {platform.machine()}"
    )


if __name__ == "__main__":
    main()
