# V15-02 — Historical Explorer vertical limitations

The original overview called the shared structured-value helper. Its semantic
`ul.evidence-values` inherits `.compact-evidence .evidence-values{display:flex;
flex-wrap:wrap}`, allowing statements to share a horizontal row. Shared CSS and
other compact lists remain unchanged.

The overview now emits one `ul.major-limitations` and an escaped `li` per string.
The renderer validates a list of strings before rendering. Local CSS specifies
block layout, native `disc outside` markers, 1.4rem indentation, .5rem item
spacing, normal whitespace and anywhere wrapping. Existing responsive and print
rules apply; no scripts or external resources were introduced.

Independent literal oracle, unchanged in canonical `drift/contract.py`:

1. Differences describe selected finite evidence and declared models, not deployment changes.
2. Unobserved traffic is not proven absent, blocked or evidence of an offline device.
3. Raw addresses and matching labels do not establish physical device or sensor identity.
4. Packet counts are raw counts, not rates or normalized activity trends.
5. Capture authenticity, clock synchronization and reviewer authority are unattested.
6. Protocol headers do not prove command execution, application success or authorization.
7. No incident, attribution, industrial safety or risk severity is determined.

New renderer revision: `1.5.0.dev1-historical-explorer.1`.
Five-file installed source digest:
`442d13378cd61586664e19f51ea6834537b0155c07e48ff5a6173628c5d6ca6b`.
Both old `.1`/`.2` revisions remain accepted for portable integrity. Unknown
revisions fail closed. Exact replay additionally requires matching analytical
producer and renderer sources; portable validation is not replay or provenance.

Tests independently compare all unrelated HTML bytes against the renderer loaded
from predecessor Git. They cover exact seven-item order, hostile/long text,
invalid types, deterministic output, preserved inputs, inert pages, navigation,
class isolation and CSS at desktop/narrow/print effective widths. Static CSS does
not prove actual browser geometry or assistive-technology behavior.

Fresh fictional owner report:
`output/v15-02/owner-review/revoked/index.html`.
The walkthrough verifies exact replay, portable integrity, unchanged canonical
report/workspace, deterministic bundles and recorded approval/current revocation.
Original `output/v15-01/major-limitations-2026-11-03/site` remains untouched.

Human acceptance is **PENDING**: seven vertical visible bullets; indentation and
spacing; 100%/200% zoom; narrow-width overflow and long wrapping; keyboard focus;
Overview/evidence links; approval/revocation distinction; offline use and print.
No real browser inspection is claimed by the automated parser.
