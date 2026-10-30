"""Presentation adapters for immutable capture evidence, without analytical inference.

UTC labels use exact rational/integer arithmetic. A decimal expansion is emitted
only when it terminates; recurring fractions retain their exact fractional offset.
Dates outside Python's proleptic Gregorian years 0001..9999 retain exact epoch
seconds instead of overflowing or silently rounding. Canonical records are never
modified. All HTML adapters escape strings through the existing safety boundary.
"""

import re
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime, timedelta
from fractions import Fraction

from otarchguard.explorer_html import escape, identity_details, properties, structured_value

_RATIONAL = re.compile(r"-?\d+/[1-9]\d*\Z")
_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
_MIN_SECOND = (datetime(1, 1, 1, tzinfo=UTC) - _EPOCH).days * 86_400
_MAX_SECOND = (datetime(9999, 12, 31, tzinfo=UTC) - _EPOCH).days * 86_400 + 86_399
_WORDS = {
    "ip": "IP",
    "ipv4": "IPv4",
    "ipv6": "IPv6",
    "mac": "MAC",
    "utc": "UTC",
    "id": "ID",
    "sha256": "SHA-256",
    "tcp": "TCP",
    "udp": "UDP",
    "arp": "ARP",
}


def _fractional_decimal(remainder: int, denominator: int) -> str | None:
    """Return the complete terminating fractional digits, or None if recurring."""
    twos = (denominator & -denominator).bit_length() - 1
    rest = denominator >> twos
    fives = 0
    while rest % 5 == 0:
        fives += 1
        rest //= 5
    if rest != 1:
        return None
    scale = max(twos, fives)
    return f"{remainder * (10**scale // denominator):0{scale}d}"


def format_utc_timestamp(value: str | None) -> str:
    """Return a readable exact UTC label; never use platform timestamp conversion.

    Fractional offsets use floor-second decomposition, including before the epoch.
    Thus -1/4 is 1969-12-31 23:59:59.75 UTC, not 1970-01-01 minus a mislabelled
    decimal. Recurring fractions are explicitly offsets after a whole UTC second.
    Malformed values remain visibly invalid rather than becoming invented dates.
    """
    if value is None:
        return "Timestamp not recorded"
    if not isinstance(value, str) or _RATIONAL.fullmatch(value) is None:
        return "Invalid recorded timestamp"
    try:
        instant = Fraction(value)
    except (ValueError, ZeroDivisionError, OverflowError):
        return "Invalid recorded timestamp"
    whole, remainder = divmod(instant.numerator, instant.denominator)
    if not _MIN_SECOND <= whole <= _MAX_SECOND:
        return f"Outside calendar range · {value} UTC epoch seconds (exact)"
    date = _EPOCH + timedelta(seconds=whole)
    label = (
        f"{date.year:04d}-{date.month:02d}-{date.day:02d} "
        f"{date.hour:02d}:{date.minute:02d}:{date.second:02d}"
    )
    if not remainder:
        return label + " UTC"
    digits = _fractional_decimal(remainder, instant.denominator)
    if digits is not None:
        return label + "." + digits + " UTC"
    fraction = Fraction(remainder, instant.denominator)
    return f"{label} UTC + {fraction.numerator}/{fraction.denominator} second (exact)"


def timestamp_html(value: str | None) -> str:
    """Readable UTC plus keyboard-accessible exact canonical text, without mutation."""
    readable = escape(format_utc_timestamp(value))
    if value is None:
        return readable
    return (
        readable
        + '<details class="technical"><summary>Exact recorded time</summary><p><code>'
        + escape(value)
        + "</code> UTC epoch seconds</p></details>"
    )


def field_label(value: object) -> str:
    """Convert a record key to ordinary text while retaining familiar acronyms."""
    words = str(value).replace("_", " ").split()
    if not words:
        return "Unnamed field"
    label = " ".join(_WORDS.get(word.lower(), word) for word in words)
    return label[0].upper() + label[1:]


def empty_state(message: str = "None recorded.") -> str:
    return '<p class="muted">' + escape(message) + "</p>"


def bullet_list(values: Iterable[object], *, empty: str = "None recorded.") -> str:
    """Render list values as escaped semantic items, never as serialized JSON."""
    items = ["<li>" + render_value(value, empty=empty) + "</li>" for value in values]
    return "<ul>" + "".join(items) + "</ul>" if items else empty_state(empty)


def property_list(rows: Iterable[tuple[object, object]], *, empty: str = "None recorded.") -> str:
    """Render raw label/value pairs; callers must not pass already-rendered markup."""
    values = [(field_label(label), render_value(value, empty=empty)) for label, value in rows]
    return properties(values) if values else empty_state(empty)


def render_value(value: object, *, empty: str = "None recorded.") -> str:
    """Display retained records through the shared semantic evidence renderer."""

    def scalar(item: object, field: str) -> str:
        if item is None:
            return empty_state("Not available.")
        if isinstance(item, str) and not item:
            return empty_state("Not recorded.")
        if isinstance(item, bool):
            return "Yes" if item else "No"
        return escape(item)

    if isinstance(value, Mapping):
        value = dict(value)
    return (
        structured_value(value, scalar)
        if isinstance(value, (dict, list, tuple))
        else scalar(value, "")
    )


def identity(label: str, value: str) -> str:
    """Keep full canonical identity in a native disclosure, using existing escaping."""
    return identity_details(label, value)
