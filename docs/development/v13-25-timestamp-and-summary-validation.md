# V13-25 — Timestamp and summary validation

## Timestamp implementation and scope

**PASS for focused local display tests; final installed-candidate verification is
recorded separately in V13-28.** `src/otarchguard/capture/display.py` converts
canonical rational UTC epoch seconds to readable date/time labels entirely in
the presentation layer. It does not modify a timestamp, observation, digest,
identity, protocol record or analytical conclusion. No dependency is added.

For example, `1700000000000007/1000000` displays as
`2023-11-14 22:13:20.000007 UTC`. The test independently verifies the calendar
mapping using `calendar.timegm((2023, 11, 14, 22, 13, 20)) == 1700000000`, then
adds exactly `7/1000000` second with `Fraction`. The expected label is not an
unchecked date copied from the prompt.

The format is explicitly UTC and locale independent. Whole seconds are split
using integer floor division and converted using standard-library Gregorian
calendar arithmetic. No float, `fromtimestamp`, platform `gmtime` range, local
timezone, rounding or truncation is involved. Supported calendar years are
0001 through 9999, including a fraction within their boundary seconds.

| Evidence value | Human-facing behavior |
|---|---|
| Integral second | `1970-01-01 00:00:01 UTC` for `1/1` |
| Microsecond/nanosecond | Entire exact fractional decimal, including leading zeroes |
| Binary resolution | Entire terminating decimal; `7/4` is `00:00:01.75 UTC` |
| Signed time/offset | Floor-second arithmetic; `7/4 - 3 = -5/4` is `1969-12-31 23:59:58.75 UTC` |
| Recurring decimal fraction | Whole UTC second plus exact fractional second, e.g. `1970-01-01 00:00:00 UTC + 1/3 second (exact)` |
| Missing value | `Timestamp not recorded`; no epoch is invented |
| Outside calendar range | `Outside calendar range` with exact rational UTC epoch seconds |
| Invalid recorded text | Explicit invalid timestamp label; escaped original remains available in detail |

Denominators containing only factors 2 and 5 are expanded completely. Tests
include `2**127`, `10**127`, and mixed factors, checked both as `Fraction` and
with an independent high-precision `Decimal` oracle. Other denominators retain
the exact fractional offset rather than receiving an approximate decimal.
Canonical precision describes the recorded value, not demonstrated clock
accuracy or sensor visibility.

`timestamp_html` exposes the readable label first, with the original canonical
rational in a native, keyboard-accessible “Exact recorded time” disclosure.
The original value also remains unchanged in canonical evidence. Plain text and
semantic `details/summary/p/code` markup use the existing HTML safety boundary;
no JavaScript, remote asset, new allowed HTML element or shared native-renderer
change is required.

## Other presentation adapters

The same module supplies semantic lists/properties, contextual empty states,
and collapsed canonical identities. `property_list` accepts **raw** label/value
pairs and escapes them recursively. Callers combining prepared safe links or
markup use the existing `properties` helper instead. Nested ordinary fields
render as definition lists and lists, without JSON serialization. Empty
collections, unavailable values, empty text and booleans have explicit readable
labels. These adapters leave their input objects unchanged.

All strings pass through existing escaping, local-path minimization and
bidirectional-control handling. Hostile HTML-like keys, values, rationale,
identity labels and strings cannot introduce executable elements or attributes.
The module does not infer trust, device identity, successful communication or
native-model reachability.

## Focused verification

Commands actually executed locally on Windows/Python 3.14.5:

```powershell
$env:PYTHONPATH='src'
.venv\Scripts\python.exe -m pytest tests/test_capture_display.py -q --basetemp=.pytest_tmp/display
.venv\Scripts\python.exe -m ruff check src/otarchguard/capture/display.py tests/test_capture_display.py
.venv\Scripts\python.exe -m ruff format src/otarchguard/capture/display.py tests/test_capture_display.py
$env:MYPYPATH='src'
.venv\Scripts\python.exe -m mypy src/otarchguard/capture/display.py tests/test_capture_display.py
```

Actual result: **36 passed in 0.43 seconds**; Ruff and strict mypy passed, then
both files were formatted. These focused counts overlap the subsequent full
installed test suites and must not be added to them.

Tests cover UTC example verification, integer/micro/nanosecond/binary timestamps,
recurring fractions, signed offsets, missing/invalid values, calendar boundaries,
extreme out-of-range values, reconstructed chronological ordering, unchanged raw
precision, deterministic output, native disclosure accessibility, semantic
structured rendering, nested escaping, path withholding and bidi controls.

## Overview and readable count validation

`src/otarchguard/capture/views.py` adds pure HTML views for overview counts,
capture/interface metadata, protocol counts/hints and coverage/scope. Counts come
directly from canonical records or finite category totals; no independent packet
interpretation or model evaluation occurs in presentation. The overview keeps
flow findings and declared-service observations in separate units. An unrequested
comparison displays “Not requested”, rather than inventing zero findings.

Protocol hints are grouped by the existing transport, protocol, port and evidence
category fields, retaining overlapping packet contributions. Tests use a deliberately
overlapping example in which hint counts exceed total packets, and preserve TCP/UDP
as separate rows. The exact required port-association caution appears prominently.
The transport table explains that a category can be known from an IP header even
when transport decoding is incomplete; a transport label is not application success.

Coverage displays the actual packet categories and container-scan status, followed
by visible observation, capture and comparison constraints. Empty capture limitations
have a contextual sentence and do not imply complete sensor visibility. Absence
assessment status, reason and finite scope remain visible outside disclosures.
All actual classification codes have plain explanations. The ambiguous-evidence
description covers both multiple interface candidates and overlapping declared
services, matching the producer's two uses of that code. Unknown future codes
remain unassessed. Full capture identity is preserved in a native disclosure.

Additional commands actually executed:

```powershell
$env:PYTHONPATH='src'
.venv\Scripts\python.exe -m pytest tests/test_capture_views.py tests/test_capture_display.py -q --basetemp=.pytest_tmp/capture-views
.venv\Scripts\python.exe -m ruff check src/otarchguard/capture/views.py tests/test_capture_views.py
$env:MYPYPATH='src'
.venv\Scripts\python.exe -m mypy src/otarchguard/capture/views.py tests/test_capture_views.py
```

Actual result: **44 passed in 0.53 seconds** (36 display plus 8 view tests);
Ruff, formatting and strict mypy passed. This combined count overlaps the earlier
36-case execution and subsequent full suites. Tests check both frozen supported
and limited fixtures, count/category consistency, declaration/flow units, missing
comparison, overlapping hints, empty states, visible scope, all classification
explanations, input immutability, deterministic output and hostile-text escaping.

A subsequent mapping-only API regression verifies that a report supplied with
owner mapping but no comparison displays the actual capture/model/observation
bindings from that mapping. It also checks unchanged canonical JSON bytes,
unchanged input objects and an explicit unrequested-comparison state. The focused
view suite then ran as **9 passed in 0.76 seconds** with Ruff, formatting and strict
mypy passing; this is a later overlapping execution, not an additional total.

## Remaining acceptance

The integration owner records exact final candidate identity with the other UX
and installed-distribution receipts. Focused tests do not constitute browser
acceptance, hosted acceptance or approval to publish. The owner's original
navigation and interpretation FAIL results remain historical facts pending a
separate second human review.
