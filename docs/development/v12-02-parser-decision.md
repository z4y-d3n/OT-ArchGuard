# V12-02 parser and adapter decision

The starting source is committed V12-01 `d95d52ddea1d9789a7b57374673902ed45e700d6`,
tree `9d27f12ce805c8027ab22fe68998d0c344487c2e`, with a clean working tree.
Python 3.12.14 and 3.14.5 verification environments contain neither openpyxl nor
defusedxml. No package acquisition is authorized or necessary for this subset.

Use Python's standard-library ZIP, Expat and ElementTree interfaces
(PSF license, with Expat's MIT runtime component) for a deliberately
restricted transitional OOXML **inventory table** reader. This is not a general
Office implementation. Reject macros, embedded objects, unsupported parts and
relationships, DTDs/entities, non-UTF-8 XML, conflicting archive paths and oversized
resources before interpreting worksheets. Never extract archive members to disk.
Expat callbacks enforce depth/element/text budgets before building a bounded tree.
External relationships are recorded and never followed; external workbook values
are unavailable. Formula cells are identified independently of caches and require
literal owner corrections for mapped fields. Styles are not interpreted as values.
Styled numeric cells are ambiguous and require correction.

This avoids a new runtime/optional dependency and wheelhouse requirement on all
supported Python platforms. Maintenance cost is the explicit small OOXML subset
and its adversarial tests; broader Office compatibility requires another parser
decision. openpyxl (MIT) would still require independent ZIP/XML/resource and
formula controls, an approved offline wheelhouse and cross-version verification.
No openpyxl compatibility or hosted platform result is claimed here.

Generic JSON uses strict UTF-8 JSON, bounded structure and explicit RFC 6901 paths.
Profile version 2 selects `json`, `xlsx`, or `netbox-offline-v1` and named tables.
Version 1 CSV/TSV mappings remain supported. All adapters create evidence through
the shared review/emission engine, which remains the only native declaration path.
Unknown values are excluded from new-format evidence; only explicitly mapped
non-sensitive scalar fields are retained. Sensitive field paths are forbidden.
