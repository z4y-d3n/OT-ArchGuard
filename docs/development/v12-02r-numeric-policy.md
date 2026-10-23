# V12-02R exact numeric evidence

JSON decimal/exponent tokens previously passed through binary64 `float`. This
rounded values and could emit nonzero `1e-400` as `0.0`. XLSX had the same path;
some precision guards blocked emission but retained already-rounded raw evidence.
The retained reproduction records demonstrate both cases on accepted V12-02.

New parsers share a bounded numeric-token implementation. Canonical integer tokens
remain arbitrary-precision Python integers (maximum 64 source characters). Decimal,
exponent and integer negative-zero tokens use an immutable tagged record:

```json
{"numeric_token": "0.10000000000000001", "numeric_category": "number"}
```

The original category remains `number` or `integer`, never `string`. Proposed native
text is the exact source lexeme, modified only by an explicit profile transform.
`1.0`, `1.00` and `1e0` retain distinct representations and candidate identities.
`-0` retains its sign. Boolean, null, zero and numeric-looking strings stay distinct.
No binary float enters new inventory evidence. Pydantic validates token grammar,
category and bounds; serialization/reloading preserves the tagged representation.
Source dictionaries cannot opt into numeric semantics by imitating this tag.

Tokens follow strict JSON numeric grammar and remain at most 64 characters. Explicit
exponents are bounded to -9,999 through 9,999. The token is never expanded to fixed
decimal form or evaluated arithmetically. Thus `1e309`, `1e-400` and `1e-9999` remain
finite compact JSON evidence; `1e10000`, nonfinite names and malformed numbers fail.
This changes the former binary-float overflow test into an actual exponent-budget
test; source byte/depth/record/field/scalar and generated-evidence budgets do not rise.

XLSX retains the exact OOXML token, not a promise to recover the original Excel
user entry or displayed number. Styled, merged, formula/date and precision-sensitive
cells still require literal correction/rejection. Nonzero magnitudes outside the
normal Excel range (approximately 2.2250738585072014e-308 to 1.7976931348623157e308)
also require correction. A temporary exact Decimal comparison enforces that range;
Decimal values never enter evidence or native serialization. Formula caches remain
excluded. Long integer raw evidence remains exact even when emission is blocked.

Structured drafts now use **import version 3**. Mapping profiles stay at version 2,
decisions at version 1, development package at `1.2.0.dev0`, native schema and
trace/report contracts at version 1. Version-1 CSV/TSV evidence remains unchanged.
Old structured version-2 drafts are explicitly rejected by load/review/emit with
`IMPORT_LEGACY_DRAFT`. Re-map the original source with the existing profile and
create fresh owner decisions. Historical rounded values cannot be upgraded to exact
evidence from a serialized draft alone. Hash binding is never weakened or migrated.
Native fields remain their original strict types; numeric controls cannot coerce
versions, port integers, IDs or owner corrections into unintended native values.
