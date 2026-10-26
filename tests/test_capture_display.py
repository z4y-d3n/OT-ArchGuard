"""Exact timestamp and safe semantic presentation, independent of packet parsing."""

import calendar
import copy
import re
from datetime import UTC, datetime
from decimal import Decimal, localcontext
from fractions import Fraction
from html import unescape
from html.parser import HTMLParser

import pytest

from otarchguard.capture.display import (
    bullet_list,
    empty_state,
    field_label,
    format_utc_timestamp,
    identity,
    property_list,
    render_value,
    timestamp_html,
)


@pytest.mark.parametrize(
    "value, expected",
    [
        ("0/1", "1970-01-01 00:00:00 UTC"),
        ("1/1", "1970-01-01 00:00:01 UTC"),
        ("1700000000000007/1000000", "2023-11-14 22:13:20.000007 UTC"),
        ("1700000000123456789/1000000000", "2023-11-14 22:13:20.123456789 UTC"),
        ("7/4", "1970-01-01 00:00:01.75 UTC"),
        ("-1/1", "1969-12-31 23:59:59 UTC"),
        ("-1/4", "1969-12-31 23:59:59.75 UTC"),
        ("-5/4", "1969-12-31 23:59:58.75 UTC"),
        ("1/3", "1970-01-01 00:00:00 UTC + 1/3 second (exact)"),
        ("-1/3", "1969-12-31 23:59:59 UTC + 2/3 second (exact)"),
        ("13/12", "1970-01-01 00:00:01 UTC + 1/12 second (exact)"),
        (None, "Timestamp not recorded"),
    ],
)
def test_readable_utc_is_exact_and_deterministic(value: str | None, expected: str) -> None:
    assert format_utc_timestamp(value) == expected
    assert format_utc_timestamp(value) == format_utc_timestamp(value)


def test_prompt_microsecond_example_has_independent_calendar_oracle() -> None:
    # calendar.timegm independently verifies the specified calendar/epoch mapping;
    # the formatter itself uses rational arithmetic and datetime + timedelta.
    seconds = calendar.timegm((2023, 11, 14, 22, 13, 20))
    assert seconds == 1_700_000_000
    value = Fraction(seconds) + Fraction(7, 1_000_000)
    assert value == Fraction("1700000000000007/1000000")
    assert format_utc_timestamp(str(value)) == "2023-11-14 22:13:20.000007 UTC"


@pytest.mark.parametrize("denominator", [2**127, 10**127, 5**37, 2**12 * 5**7])
def test_all_supported_terminating_precision_is_retained(denominator: int) -> None:
    value = f"1/{denominator}"
    label = format_utc_timestamp(value)
    assert label.startswith("1970-01-01 00:00:00.") and label.endswith(" UTC")
    fraction = label.removeprefix("1970-01-01 00:00:00").removesuffix(" UTC")
    assert Fraction(fraction) == Fraction(value)
    # A separate standard-library decimal oracle is exact at this precision.
    with localcontext() as context:
        context.prec = 200
        assert Decimal(fraction) == Decimal(1) / Decimal(denominator)


@pytest.mark.parametrize(
    "value, prefix",
    [
        ("-62135596800/1", "0001-01-01 00:00:00"),
        ("253402300799/1", "9999-12-31 23:59:59"),
        ("253402300799999999999/1000000000", "9999-12-31 23:59:59.999999999"),
    ],
)
def test_calendar_boundaries_do_not_depend_on_operating_system(value: str, prefix: str) -> None:
    assert format_utc_timestamp(value) == prefix + " UTC"


@pytest.mark.parametrize(
    "value", ["-62135596801/1", "253402300800/1", f"{2**127}/1", f"{-(2**127)}/3"]
)
def test_out_of_range_dates_preserve_labeled_exact_epoch_seconds(value: str) -> None:
    assert format_utc_timestamp(value) == (
        f"Outside calendar range · {value} UTC epoch seconds (exact)"
    )
    html = timestamp_html(value)
    assert value in html and "Outside calendar range" in html


def test_signed_offset_is_already_part_of_canonical_rational_time() -> None:
    # PCAPNG tick=7, binary denominator=4 and signed offset=-3 -> -5/4.
    instant = Fraction(7, 4) - 3
    assert format_utc_timestamp(str(instant)) == "1969-12-31 23:59:58.75 UTC"


def test_readable_dates_preserve_earliest_latest_ordering_and_never_round() -> None:
    values = [
        "-1/1",
        "0/1",
        "999999999/1000000000",
        "1/1",
        "1700000000000007/1000000",
        "1700000000000008/1000000",
    ]
    labels = [format_utc_timestamp(value) for value in values]
    reconstructed = []
    epoch = datetime(1970, 1, 1, tzinfo=UTC)
    for label in labels:
        whole = datetime.strptime(label[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
        seconds = (whole - epoch).days * 86_400 + (whole - epoch).seconds
        tail = label[19:].removesuffix(" UTC")
        reconstructed.append(Fraction(seconds) + (Fraction(tail) if tail else 0))
    assert reconstructed == [Fraction(value) for value in values]
    assert reconstructed == sorted(reconstructed)


@pytest.mark.parametrize("value", ["", "1/0", "not-time", "NaN", "1.25", "<script>bad()</script>"])
def test_invalid_time_is_explicit_and_its_raw_text_is_escaped(value: str) -> None:
    assert format_utc_timestamp(value) == "Invalid recorded timestamp"
    html = timestamp_html(value)
    assert "Invalid recorded timestamp" in html
    assert "<script>" not in html


def test_timestamp_html_keeps_canonical_value_in_native_disclosure() -> None:
    value = "1700000000000007/1000000"
    html = timestamp_html(value)
    assert html.startswith("2023-11-14 22:13:20.000007 UTC")
    assert "<summary>Exact recorded time</summary>" in html
    assert "<code>" + value + "</code> UTC epoch seconds" in html
    assert value == "1700000000000007/1000000"
    assert timestamp_html(None) == "Timestamp not recorded"


class _Elements(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[str] = []
        self.attributes: list[tuple[str, str | None]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append(tag)
        self.attributes.extend(attrs)


def test_semantic_display_escapes_nested_fields_and_never_serializes_json() -> None:
    value: dict[str, object] = {
        'source_ip"><img src=x onerror=bad()>': "<script>fetch('https://invalid')</script>",
        "source_macs": ["02:00:00:00:00:10", "<svg onload=bad()>"],
        "owner_review": {"reviewer": 'A & "B"', "rationale": "Claim only", "accepted": False},
        "limitations": [],
        "missing_value": None,
    }
    before = copy.deepcopy(value)
    rendered = render_value(value)
    assert value == before
    assert "<dl" in rendered and "<dt>" in rendered and "<dd>" in rendered
    assert "<ul>" in rendered and "<li>" in rendered
    assert "None recorded." in rendered and "Not available." in rendered
    assert "[]" not in rendered and "{&quot;" not in rendered
    assert "&lt;script&gt;" in rendered and "&lt;svg" in rendered
    assert "A &amp; &quot;B&quot;" in rendered
    parser = _Elements()
    parser.feed(rendered)
    assert set(parser.tags) <= {"dl", "dt", "dd", "ul", "li", "p"}
    assert all(name == "class" for name, _ in parser.attributes)


def test_list_properties_and_identity_adapters_escape_raw_inputs() -> None:
    raw = "<a href='https://invalid'>unsafe</a>"
    assert "&lt;a" in bullet_list([raw])
    assert "<a " not in property_list([("Rationale", raw)])
    assert "No additional limitations." in bullet_list([], empty="No additional limitations.")
    assert "<summary>" in identity("Capture SHA-256", "a" * 64)
    assert "a" * 64 in identity("Capture SHA-256", "a" * 64)
    assert "a" * 12 + "…" in unescape(identity("Capture SHA-256", "a" * 64))
    assert "&lt;a" in identity("Identity", raw)
    assert render_value(0) == "0" and render_value(True) == "Yes"
    assert render_value(False) == "No" and "Not recorded." in render_value("")
    assert "None recorded." in empty_state() and "None recorded." in property_list([])
    assert field_label("source_ip") == "Source IP"
    assert field_label("capture_sha256") == "Capture SHA-256"


def test_display_preserves_existing_path_and_bidirectional_control_minimization() -> None:
    rendered = render_value({"rationale": "C:/Users/private/secret.txt \u202eunsafe"})
    assert "C:/Users/private" not in rendered
    assert "[local path withheld]" in rendered and "[U+202E]" in rendered
    assert "\u202e" not in rendered
    assert re.search(r"<script|<img|<svg|onload=", render_value("<script>bad</script>")) is None
