"""Independent immutable Unicode, diagnostic precedence and display-byte oracle."""

import ast
from collections.abc import Callable
from types import SimpleNamespace
from typing import Any, cast

import pytest

from otarchguard.diagnostics import ModelError, check_limit, fail
from otarchguard.explorer_data import EXPLORER_LIMITS, check_text
from otarchguard.explorer_html import escape
from tools import verify_v15_04_transition as policy


@pytest.fixture(scope="module")
def predecessor_text() -> Callable[[str], None]:
    source = policy.reference()["src/otarchguard/explorer_data.py"]
    tree = ast.parse(source)
    (function,) = [
        n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "check_text"
    ]
    namespace: dict[str, Any] = {
        "check_limit": check_limit,
        "fail": fail,
        "EXPLORER_LIMITS": SimpleNamespace(text_characters=4096),
    }
    exec(
        compile(ast.Module(body=[function], type_ignores=[]), "immutable-dev2-text", "exec"),
        namespace,
    )
    return cast(Callable[[str], None], namespace["check_text"])


def outcome(function: Callable[[str], None], value: str) -> object:
    try:
        function(value)
    except ModelError as error:
        return error.diagnostics
    return None


def test_every_unicode_codepoint_matches_immutable_predecessor(
    predecessor_text: Callable[[str], None],
) -> None:
    # Includes lone surrogates, noncharacters, astral scalars and every control.
    for codepoint in range(0x110000):
        value = chr(codepoint)
        assert outcome(check_text, value) == outcome(predecessor_text, value), hex(codepoint)


@pytest.mark.parametrize(
    "value",
    [
        "",
        "\t\n\r",
        "x" * 4096,
        "x" * 4097,
        "\x00" + "x" * 4096,
        "x" * 4096 + "\ud800",
        "é e\u0301 \U0001f30d \u202e \u2066 ::ffff:192.0.2.1",
        *[
            prefix + char + suffix
            for char in "\x00\x08\x0b\x0c\x1f\x7f\x9f\ud800\udfff"
            for prefix, suffix in (("", "end"), ("middle", "end"), ("start", ""))
        ],
    ],
)
def test_mixed_strings_and_resource_error_precedence(
    predecessor_text: Callable[[str], None], value: str
) -> None:
    assert outcome(check_text, value) == outcome(predecessor_text, value)


def test_exact_safe_display_and_bidi_bytes() -> None:
    assert EXPLORER_LIMITS.text_characters == 4096
    assert escape('<tag a="x"> & é\u202e\u2066\U0001f30d') == (
        "&lt;tag a=&quot;x&quot;&gt; &amp; é[U+202E][U+2066]\U0001f30d"
    )
    with pytest.raises(ModelError) as error:
        escape("x" * 4096 + "\x00")
    assert error.value.diagnostics[0].code == "LIMIT_EXCEEDED"
