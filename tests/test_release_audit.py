"""Release archive allow-list rejects private/generated/traversal payloads."""

import pytest

from tools.audit_release import check_member


@pytest.mark.parametrize("wheel", [False, True])
@pytest.mark.parametrize(
    "name",
    [
        "../LICENSE",
        "/LICENSE",
        "src/private/secret.md",
        "docs/standard.pdf",
        "output/result.json",
        ".venv/config.txt",
        "docs/.env",
        "src/a.pyc",
        "src\\a.py",
        "C:/secret.md",
        "src/otarchguard/__pycache__/a.py",
    ],
)
def test_archive_rejects_private_generated_and_unsafe_paths(name: str, wheel: bool) -> None:
    with pytest.raises(ValueError):
        check_member(name, wheel=wheel)


def test_wheel_rejects_nonruntime_payload() -> None:
    with pytest.raises(ValueError):
        check_member("tests/test_loading.py", wheel=True)
    check_member("otarchguard/loading.py", wheel=True)
    check_member("otarchguard-1.0.1.dist-info/licenses/LICENSE", wheel=True)
    check_member("tests/fixtures/minimal-valid.yaml", wheel=False)
    check_member("docs/images/flat-plant-proposed.png", wheel=False)
