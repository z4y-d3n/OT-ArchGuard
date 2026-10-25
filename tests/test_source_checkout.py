"""Real Git checkout conversion must not change packaged public source bytes."""

import os
import subprocess
from pathlib import Path

import pytest

from tools.verify_source_checkout import verify

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("autocrlf", ["true", "false", "input"])
def test_committed_public_bytes_survive_git_checkout(tmp_path: Path, autocrlf: str) -> None:
    source = tmp_path / "repo"
    source.mkdir()
    env = {**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}

    def git(*args: str) -> None:
        subprocess.run(
            ["git", "-c", "core.autocrlf=false", *args],
            cwd=source,
            env=env,
            check=True,
            capture_output=True,
        )

    git("init", "--template=", "--initial-branch=fixture")
    (source / ".gitattributes").write_bytes((ROOT / ".gitattributes").read_bytes())
    (source / "code.py").write_bytes(b"name = 'synthetic'\n")
    (source / "legacy.txt").write_bytes(b"preserved\r\n")
    names = frozenset({".gitattributes", "code.py", "legacy.txt"})
    git("add", ".")
    git(
        "-c",
        "user.name=Synthetic test",
        "-c",
        "user.email=fixture@example.invalid",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "--no-verify",
        "-m",
        "Synthetic bytes",
    )
    output = tmp_path / "checkout"
    output.mkdir()
    git(
        "-c",
        "core.autocrlf=" + autocrlf,
        "checkout-index",
        "--all",
        "--prefix=" + output.as_posix() + "/",
    )
    for name in names:
        assert (output / name).read_bytes() == (source / name).read_bytes()
    assert verify(source, names)["status"] == "passed"
    (source / "code.py").write_bytes(b"name = 'synthetic'\r\n")
    with pytest.raises(ValueError, match="checkout bytes"):
        verify(source, names)
