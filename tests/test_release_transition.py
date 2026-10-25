"""Current release transitions must not normalize unrelated historical evidence."""

import pytest

from tools.compare_versioned_contract import compare_artifact


def test_current_transition_allows_only_the_explicit_engine_field() -> None:
    before = b'{"engine_version": "1.2.0", "schema_version": 1, "owner_note": "1.2.0"}\n'
    after = before.replace(b'"engine_version": "1.2.0"', b'"engine_version": "1.3.0"')
    assert compare_artifact(before, after, "1.2.0", "1.3.0") == "ENGINE_VERSION_JSON"
    with pytest.raises(ValueError):
        compare_artifact(
            before,
            after.replace(b'"owner_note": "1.2.0"', b'"owner_note": "1.3.0"'),
            "1.2.0",
            "1.3.0",
        )
    with pytest.raises(ValueError):
        compare_artifact(before, after)
