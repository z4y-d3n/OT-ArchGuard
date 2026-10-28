"""Narrow HTML/SVG safety boundary and complete-site link/resource validation."""

import hashlib
import html
import json
import re
import time
from collections import defaultdict
from collections.abc import Callable, Sequence
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath

from otarchguard.diagnostics import check_limit, fail
from otarchguard.explorer_data import EXPLORER_LIMITS, check_text

CSS = """*{box-sizing:border-box}html{color:#172d3e;background:#f2f5f7;
font:100%/1.6 system-ui,sans-serif}body{margin:0}header,nav,main,footer{padding:1rem 3%;
max-width:100rem;margin:auto}header{border-bottom:4px solid #375b75;background:#fff}
h1{font-size:1.9rem;line-height:1.25}h2{font-size:1.35rem;margin-top:2rem}
h3{font-size:1.1rem}a{color:#124f7c;text-decoration:underline;text-underline-offset:.18em}
a:hover{color:#763d00}a:focus-visible,[tabindex]:focus-visible,summary:focus-visible{
outline:3px solid #854700;outline-offset:3px}nav ul,.cards{display:flex;flex-wrap:wrap;
gap:.75rem 1.5rem;list-style:none;padding:0}nav{border-bottom:1px solid #657b8b}
.cards>li{background:white;border:1px solid #657b8b;padding:1rem;flex:1 1 14rem}
.notice{border-left:5px solid #7c530b;padding:.6rem 1rem;background:#fff7e5}
.legend{border:1px solid #657b8b;padding:1rem;background:white}.legend li{margin:.5rem}
.scroll{overflow:auto;max-width:100%;border:1px solid #657b8b;background:white}
table{border-collapse:collapse;width:100%;min-width:34rem}caption{text-align:left;
font-weight:700;padding:.75rem}th,td{text-align:left;vertical-align:top;padding:.65rem;
border-bottom:1px solid #c1cbd2}th{background:#e5edf2}th[scope=row]{width:25%}
code,pre{font-family:ui-monospace,Consolas,monospace;font-size:.94em}
code,td,li,p,dd,h1,h2,a{overflow-wrap:anywhere}pre{white-space:pre-wrap;overflow-wrap:anywhere}
.skip{position:absolute;left:-10000px}.skip:focus{position:static;display:block;padding:1rem}
svg{display:block;max-width:none}figure{margin:1.5rem 0}figcaption{padding:.5rem}
.documentary{stroke:#505c66;stroke-dasharray:7 5}.declared{stroke:#174f7b}
.diagram-line{fill:none;stroke-width:3}.analytical{stroke:#653b78;stroke-width:5}
.muted{color:#40596b}footer{border-top:1px solid #657b8b;font-size:.9rem}
.properties{display:block;margin:.5rem 0}.properties>dt{font-weight:600;min-width:0;
margin-top:.6rem;border-bottom:1px solid #c1cbd2;
overflow-wrap:anywhere}.properties>dt::first-letter{text-transform:uppercase}
.properties>dt::after{content:":"}.properties>dd{margin:0 0 .5rem;min-width:0}
.properties .properties{margin:.2rem 0}.properties ul{margin:.2rem 0;padding-left:0;
list-style-position:inside}.properties li{margin:.35rem 0}
details{margin:.5rem 0}summary{cursor:pointer;font-weight:600}.identity code{font-size:.85em}
@media(max-width:640px){header,nav,main,footer{padding:1rem}h1{font-size:1.5rem}
nav ul{gap:1rem}.cards{display:block}.cards li{margin:.6rem 0}}
@media(max-width:480px){.properties>dt{margin-top:.4rem}}
@media print{html{background:white;color:black}nav,.skip{display:none}a{color:black}
.scroll{overflow:visible}svg{max-width:100%;height:auto}table{min-width:0}}
"""

_PATH = re.compile(
    r"(?i)(?:file://\S+|(?<![a-z0-9_])[a-z]:[\\/]\S*|\\\\[^\s<>]+|/(?:home|users|tmp|var|private|etc)/[^\s<>]*)"
)
_BIDI = frozenset(range(0x202A, 0x202F)) | frozenset(range(0x2066, 0x206A))
_ALLOWED_ELEMENTS = frozenset(
    "html head meta link title body a header p h1 h2 h3 nav ul li main section dl dt dd div "
    "table caption thead tr th tbody td aside footer figure figcaption pre code br svg "
    "desc defs marker path clippath rect g text circle details summary h4 ol".split()
)

# Opt-in prototype styles only. CSS and properties() retain their existing output.
COMPACT_CSS = """
.compact-evidence{min-width:0;max-width:100%;overflow-wrap:anywhere}
.compact-evidence .compact-fields{display:flex;flex-wrap:wrap;align-items:baseline;
gap:.2rem 1.25rem;margin:.3rem 0 .5rem;padding:0}
.compact-evidence .compact-field{flex:0 1 auto;min-width:0;max-width:100%}
.compact-evidence .compact-wide{flex-basis:100%}
.compact-evidence .compact-field>dt,.compact-evidence .compact-field>dd{display:inline;
margin:0;padding:0;overflow-wrap:anywhere;white-space:normal}
.compact-evidence .compact-field>dt{font-weight:650}
.compact-evidence .evidence-group{margin:.4rem 0;padding:0;border:0;background:transparent}
.compact-evidence .evidence-heading{font-size:1rem;line-height:1.35;margin:.45rem 0 .25rem;
padding:0 0 .15rem;border-bottom:1px solid #c1cbd2;overflow-wrap:anywhere}
.compact-evidence .evidence-records{list-style:none;padding:0;margin:.35rem 0}
.compact-evidence .evidence-records>li{margin:.4rem 0;padding:0;border:0}
.compact-evidence .evidence-values{display:flex;flex-wrap:wrap;gap:.1rem 1.4rem;
padding-left:1.1rem;margin:.2rem 0;list-style:disc}
.compact-evidence .evidence-values>li{margin:0;max-width:100%;overflow-wrap:anywhere}
.compact-evidence code{white-space:normal;overflow-wrap:anywhere}
.compact-evidence details{margin:.2rem 0}
@media(max-width:480px){.compact-evidence .compact-fields{gap:.2rem .8rem}}
@media print{.compact-evidence .evidence-heading{break-after:avoid}
.compact-evidence .evidence-records>li{break-inside:auto}}
"""

# Scoped to the F1 exposure prototype; other tables retain their existing CSS.
EXPOSURE_TABLE_CSS = """
.exposure-tables{min-width:0;max-width:100%}
.exposure-tables table{width:max-content;min-width:100%;max-width:none}
.exposure-tables th,.exposure-tables td{padding:.35rem .5rem;line-height:1.4;
overflow-wrap:anywhere;vertical-align:top;min-width:7ch;max-width:36rem}
.exposure-tables th[scope=row]{width:auto;font-weight:600}
.exposure-tables h3{margin:1rem 0 .4rem}.exposure-tables h4{margin:.8rem 0 .35rem}
.exposure-tables p{margin:.4rem 0}.exposure-tables .scroll{margin:.5rem 0 1rem}
.exposure-tables code{white-space:normal;overflow-wrap:anywhere}
@media print{.exposure-tables table{width:100%;min-width:0;table-layout:fixed}
.exposure-tables th,.exposure-tables td{min-width:0;max-width:none;font-size:8pt}
.exposure-tables .scroll{overflow:visible}.exposure-tables thead{display:table-header-group}
.exposure-tables tr{break-inside:avoid}.exposure-tables h3,.exposure-tables h4{break-after:avoid}}
"""


def escape(value: object) -> str:
    """Only text and quoted-attribute contexts; never URLs, CSS, markup or JS."""
    text = str(value)
    check_text(text)
    text = _PATH.sub("[local path withheld]", text)
    text = "".join(f"[U+{ord(c):04X}]" if ord(c) in _BIDI else c for c in text)
    return html.escape(text, quote=True)


def link(path: str, label: object) -> str:
    # All destinations come from renderer IDs, never imported URL-like values.
    if re.fullmatch(r"[a-z0-9-]+\.html(?:#[a-z0-9-]+)?|#[a-z0-9-]+", path) is None:
        raise ValueError("Unsafe internal destination")
    return f'<a href="{path}">{escape(label)}</a>'


def table(
    caption: str,
    headings: tuple[str, ...],
    rows: Sequence[tuple[str, ...]],
    *,
    row_headers: bool = False,
) -> str:
    if not rows:
        return '<p class="muted">None in this view.</p>'
    return (
        '<div class="scroll" tabindex="0" role="region" aria-label="'
        + escape(caption)
        + '"><table><caption>'
        + escape(caption)
        + "</caption><thead><tr>"
        + "".join(f'<th scope="col">{escape(h)}</th>' for h in headings)
        + "</tr></thead><tbody>"
        + "".join(
            "<tr>"
            + "".join(
                f'<th scope="row">{cell}</th>' if row_headers and index == 0 else f"<td>{cell}</td>"
                for index, cell in enumerate(row)
            )
            + "</tr>"
            for row in rows
        )
        + "</tbody></table></div>"
    )


def properties(rows: Sequence[tuple[str, str]]) -> str:
    """Semantic nested properties; values are already escaped renderer markup."""
    return (
        '<dl class="properties">'
        + "".join(f"<dt>{escape(label)}</dt><dd>{value}</dd>" for label, value in rows)
        + "</dl>"
    )


def compact_value(
    value: object,
    leaf: Callable[[object, str], str],
    *,
    sort_keys: bool = False,
) -> str:
    """Opt-in evidence prototype; leaf markup must use the caller's trusted escaping.

    Adjacent scalar fields share a compact definition list. Objects retain their
    section hierarchy without horizontal indentation. Structured collections keep
    list semantics; only explicit witness-step fields become ordered sequences.
    No evidence is summarized away, reordered within a sequence, or hidden.
    """

    def label(key: str) -> str:
        words = key.replace("_", " ").split()
        acronyms = {"id": "ID", "ip": "IP", "sha256": "SHA-256", "tcp": "TCP", "utc": "UTC"}
        text = " ".join(acronyms.get(word, word) for word in words)
        return text[:1].upper() + text[1:]

    def structured(item: object) -> bool:
        return isinstance(item, (dict, list, tuple)) and bool(item)

    def render(item: object, field: str, depth: int) -> str:
        if isinstance(item, dict) and item:
            parts: list[str] = []
            fields: list[str] = []

            def flush() -> None:
                if fields:
                    parts.append('<dl class="compact-fields">' + "".join(fields) + "</dl>")
                    fields.clear()

            entries = sorted(item.items()) if sort_keys else item.items()
            for key, child in entries:
                key = str(key)
                if structured(child):
                    flush()
                    heading = "h3" if depth == 0 else "h4"
                    parts.append(
                        '<section class="evidence-group" aria-label="'
                        + escape(label(key))
                        + '">'
                        + f'<{heading} class="evidence-heading">'
                        + escape(label(key))
                        + f"</{heading}>"
                        + render(child, key, depth + 1)
                        + "</section>"
                    )
                else:
                    wide = " compact-wide" if isinstance(child, str) and len(child) > 120 else ""
                    fields.append(
                        '<div class="compact-field'
                        + wide
                        + '"><dt>'
                        + escape(label(key))
                        + ": </dt><dd>"
                        + render(child, key, depth + 1)
                        + "</dd></div>"
                    )
            flush()
            return "".join(parts)
        if isinstance(item, (list, tuple)) and item:
            if any(structured(child) for child in item):
                ordered = field in {"steps", "permitted_steps"}
                tag, name = ("ol", "Step") if ordered else ("ul", "Record")
                return (
                    f'<{tag} class="evidence-records" role="list">'
                    + "".join(
                        '<li><h4 class="evidence-heading">'
                        + f"{name} {index}</h4>"
                        + render(child, field, depth + 1)
                        + "</li>"
                        for index, child in enumerate(item, 1)
                    )
                    + f"</{tag}>"
                )
            return (
                '<ul class="evidence-values">'
                + "".join("<li>" + render(child, field, depth + 1) + "</li>" for child in item)
                + "</ul>"
            )
        if isinstance(item, dict):
            return "<code>{}</code>"
        if isinstance(item, (list, tuple)):
            return "<code>[]</code>"
        return leaf(item, field)

    return '<div class="compact-evidence">' + render(value, "", 0) + "</div>"


def identity_details(label: str, value: str) -> str:
    """Short display only; exact identities remain keyboard-accessible text."""
    short = re.sub(r"[a-f0-9]{64}", lambda match: match[0][:12] + "…", value)
    return (
        '<details class="identity"><summary>'
        + escape(label)
        + ": <code>"
        + escape(short)
        + "</code> · Full values</summary><p><code>"
        + escape(value)
        + "</code></p></details>"
    )


LEGEND = (
    '<aside class="legend" aria-label="Trust legend"><h2>Trust legend</h2>'
    "<p>Documentary evidence is not permission. Analytical results apply only to the declared "
    "model and exact evaluated query; not evaluated does not mean denied.</p>"
    "<details><summary>Full trust and interpretation limits</summary><ul>"
    "<li>Documentary evidence · dashed line · Documented only. Unknown from documentary "
    "evidence alone; drawings do not authorize communication.</li>"
    "<li>Owner-confirmed architecture · solid line · Declared only. Validation establishes "
    "model consistency, not physical network truth or permission on every edge.</li>"
    "<li>Analytical result · double or heavy line · Specific evaluated query. Only the exact "
    "model, direction, transport and ports shown were evaluated.</li></ul>"
    "<p>Not evaluated differs from a negative result. Not modeled paths remain unassessed. "
    "Unsupported input is an error. Layout proximity and missing drawing edges establish "
    "neither reachability nor isolation.</p></details></aside>"
)


def document(
    title: str,
    body: str,
    model_hash: str,
    navigation: tuple[tuple[str, str], ...] | None = None,
    model_context: str | None = None,
) -> bytes:
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta http-equiv="Content-Security-Policy" content="default-src &#39;none&#39;; '
        "style-src &#39;self&#39;; script-src &#39;none&#39;; img-src &#39;none&#39;; "
        "connect-src &#39;none&#39;; base-uri &#39;none&#39;; form-action &#39;none&#39;; "
        'object-src &#39;none&#39;">'
        '<link rel="stylesheet" href="assets.css"><title>'
        + escape(title)
        + ' · Architecture Explorer</title></head><body><a class="skip" href="#main">'
        "Skip to main content</a><header><p>OT-ArchGuard · Offline Architecture Explorer</p><h1>"
        + escape(title)
        + "</h1>"
        + identity_details(
            "Baseline and proposed model identities" if model_context else "Model SHA-256",
            model_context or model_hash,
        )
        + '</header><nav aria-label="Explorer"><ul>'
        + "".join(
            f"<li>{link(path, label)}</li>"
            for path, label in (
                navigation
                if navigation is not None
                else (
                    ("index.html", "Architecture overview"),
                    ("zones.html", "Zones"),
                    ("assets.html", "Assets"),
                    ("interfaces.html", "Interfaces"),
                    ("declarations.html", "Native declarations"),
                    ("evidence.html", "Source evidence"),
                    ("analysis.html", "Analytical results"),
                )
            )
        )
        + '</ul></nav><main id="main">'
        + body
        + LEGEND
        + "</main><footer><p>Local engineering report; review sensitive details before sharing.</p>"
        "<details><summary>Sharing and identity limits</summary><p>"
        "Local full-detail engineering report. Review before sharing: "
        "asset names, addresses and selected evidence may be sensitive. Original documents "
        "are not included. Hashes detect changes; they do not authenticate authorship. "
        "Explorer contract 2; native schema 1. No JavaScript required.</p></details>"
        "</footer></body></html>\n"
    ).encode("utf-8")


class PageAudit(HTMLParser):
    """Independent parser over actual emitted bytes; offline resources and local fragments."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: set[str] = set()
        self.links: list[str] = []
        self.entity_marks = 0
        self.relationship_marks = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag not in _ALLOWED_ELEMENTS:
            raise ValueError("Unexpected or active presentation element")
        if tag == "link" and attributes != {"rel": "stylesheet", "href": "assets.css"}:
            raise ValueError("Only the fixed local stylesheet is permitted")
        if tag == "meta" and "http-equiv" in attributes:
            if attributes["http-equiv"] != "Content-Security-Policy":
                raise ValueError("Unexpected active meta directive")
        if any(
            k in attributes
            for k in (
                "data-asset-id",
                "data-zone-id",
                "data-endpoint",
                "data-native-asset-id",
            )
        ):
            self.entity_marks += 1
        if "data-edge-id" in attributes or "diagram-line" in (attributes.get("class") or ""):
            self.relationship_marks += 1
        for key, value in attrs:
            if key.startswith("on") or key in {"style", "src", "srcdoc", "xlink:href"}:
                raise ValueError("Unsafe presentation attribute")
            if key == "id" and value is not None:
                if value in self.ids:
                    raise ValueError("Duplicate document identifier")
                self.ids.add(value)
            if key == "href" and value is not None:
                if not re.fullmatch(r"[a-z0-9.-]+(?:#[a-z0-9-]+)?|#[a-z0-9-]+", value):
                    raise ValueError("Nonlocal or unsafe link")
                self.links.append(value)
            if value and "url(" in value and not re.fullmatch(r"url\(#[a-z0-9-]+\)", value):
                raise ValueError("External SVG reference")


def audit_site(root: Path) -> dict[str, int]:
    pages: dict[str, PageAudit] = {}
    largest_svg = 0
    # One bounded directory inventory replaces a filesystem stat for every link.
    # A compact site can still contain tens of thousands of cross-references.
    actual_files: set[str] = set()
    for entry in root.iterdir():
        if entry.is_symlink() or entry.is_junction() or not entry.is_file():
            raise ValueError("Nonregular site member")
        actual_files.add(entry.name)
    for path in sorted(root.glob("*.html")):
        text = path.read_text(encoding="utf-8")
        parser = PageAudit()
        parser.feed(text)
        pages[path.name] = parser
        for svg in re.findall(r"<svg\b.*?</svg>", text, re.DOTALL):
            largest_svg = max(largest_svg, len(svg.encode("utf-8")))
    links = 0
    for name, parser in pages.items():
        for target in parser.links:
            file, _, fragment = target.partition("#")
            file = file or name
            if PurePosixPath(file).name != file or file not in actual_files:
                raise ValueError("Broken local file link")
            if fragment and (file not in pages or fragment not in pages[file].ids):
                raise ValueError("Broken local anchor")
            links += 1
    return {
        "html_pages": len(pages),
        "internal_links": links,
        "anchors": sum(len(p.ids) for p in pages.values()),
        "broken_links": 0,
        "largest_svg_bytes": largest_svg,
        "rendered_entity_marks": sum(p.entity_marks for p in pages.values()),
        "rendered_relationship_marks": sum(p.relationship_marks for p in pages.values()),
    }


class SiteWriter:
    def __init__(
        self,
        root: Path,
        model_hash: str,
        navigation: tuple[tuple[str, str], ...] | None = None,
        json_bytes: int = 4 * EXPLORER_LIMITS.page_bytes,
        model_context: str | None = None,
    ) -> None:
        self.root = root
        self.model_hash = model_hash
        self.files: dict[str, str] = {}
        self.total = 0
        self.largest = 0
        self.pending: dict[str, tuple[str, str]] = {}
        self.pending_bytes = 0
        self.locations: dict[str, str] = {}
        self.audit_seconds = 0.0
        self.navigation = navigation
        self.json_bytes = json_bytes
        self.model_context = model_context

    def write(self, name: str, data: bytes) -> None:
        if re.fullmatch(r"[a-z0-9-]+\.(html|css|json)", name) is None or name in self.files:
            fail("EXPLORER_OUTPUT", "$", "Unsafe or duplicate generated filename.")
        check_limit("explorer_files", len(self.files) + 1, EXPLORER_LIMITS.pages)
        maximum = self.json_bytes if name.endswith(".json") else EXPLORER_LIMITS.page_bytes
        check_limit("explorer_page_bytes", len(data), maximum)
        check_limit("explorer_total_bytes", self.total + len(data), EXPLORER_LIMITS.total_bytes)
        (self.root / name).write_bytes(data)
        self.files[name] = hashlib.sha256(data).hexdigest()
        self.total += len(data)
        if name.endswith(".html"):
            self.largest = max(self.largest, len(data))

    def page(self, name: str, title: str, body: str) -> None:
        if re.fullmatch(r"[a-z0-9-]+\.html", name) is None or name in self.pending:
            fail("EXPLORER_OUTPUT", "$", "Unsafe or duplicate generated page identity.")
        size = len(document(title, body, self.model_hash, self.navigation, self.model_context))
        check_limit("explorer_page_bytes", size, EXPLORER_LIMITS.page_bytes)
        check_limit("explorer_total_bytes", self.pending_bytes + size, EXPLORER_LIMITS.total_bytes)
        check_limit("explorer_records", len(self.pending) + 1, EXPLORER_LIMITS.pages)
        self.pending_bytes += size
        self.pending[name] = (title, body)

    def _compact(self) -> None:
        """Pack low-value detail files in stable hash tries; never truncate evidence.

        Keys retain the contract-1 semantic digest. Physical paths are contract-2
        locations, not promises that old bookmarks will continue to resolve.
        """
        families = {
            "candidate",
            "group",
            "decision",
            "node",
            "connector",
            "observation",
            "change",
            "finding",
            "record",
        }
        buckets: dict[tuple[str, str], list[str]] = defaultdict(list)
        grouped: dict[str, list[str]] = {}
        for name in sorted(self.pending):
            family, _, identity = name.removesuffix(".html").partition("-")
            if family in families:
                buckets[family, identity[:1]].append(name)
            else:
                self.locations[name] = name

        def split(family: str, prefix: str, members: list[str]) -> None:
            size = sum(len(self.pending[n][1].encode("utf-8")) + 1024 for n in members)
            if len(members) > 24 or (size > 384 * 1024 and len(members) > 1):
                children: dict[str, list[str]] = defaultdict(list)
                for name in members:
                    identity = name.removesuffix(".html").partition("-")[2]
                    if len(prefix) >= len(identity):
                        fail("EXPLORER_OUTPUT", "$", "Evidence identity collision.")
                    children[identity[: len(prefix) + 1]].append(name)
                for child, values in sorted(children.items()):
                    split(family, child, values)
                return
            destination = family + "-" + prefix + ".html"
            grouped[destination] = members
            for name in members:
                self.locations[name] = destination + "#" + name.removesuffix(".html")

        for (family, prefix), members in sorted(buckets.items()):
            split(family, prefix, members)

        def links(body: str, origin: str, namespace: str = "") -> str:
            def destination(match: re.Match[str]) -> str:
                file, marker, fragment = match[1].partition("#")
                target = self.locations.get(file or origin, file or origin)
                if marker:
                    target += ("-" if "#" in target else "#") + fragment
                return 'href="' + target + '"'

            body = re.sub(r'href="([a-z0-9.-]*(?:#[a-z0-9-]+)?)"', destination, body)
            if namespace:
                body = re.sub(
                    r'id="([a-z0-9-]+)"', lambda m: 'id="' + namespace + "-" + m[1] + '"', body
                )
                body = re.sub(
                    r"url\(#([a-z0-9-]+)\)", lambda m: "url(#" + namespace + "-" + m[1] + ")", body
                )
            return body

        for name, (title, body) in sorted(self.pending.items()):
            if self.locations[name] == name:
                self.write(
                    name,
                    document(
                        title,
                        links(body, name),
                        self.model_hash,
                        self.navigation,
                        self.model_context,
                    ),
                )
        for name, members in sorted(grouped.items()):
            review_records = name.partition("-")[0] in {"change", "finding", "record"}
            body = (
                '<p class="notice">This page contains additional local '
                + ("engineering records" if review_records else "documentary evidence")
                + " and is not a public-safe export.</p>"
            )
            body += table(
                "Records on this page",
                ("Record",),
                [(link("#" + n.removesuffix(".html"), self.pending[n][0]),) for n in members],
            )
            for member in members:
                title, record = self.pending[member]
                anchor = member.removesuffix(".html")
                body += '<section id="' + anchor + '"><h2>' + escape(title) + "</h2>"
                body += links(record, member, anchor) + "</section>"
            self.write(
                name,
                document(
                    "Grouped "
                    + name.partition("-")[0]
                    + (" records" if review_records else " evidence"),
                    body,
                    self.model_hash,
                    self.navigation,
                    self.model_context,
                ),
            )
        self.pending.clear()

    def finish(self, metadata: dict[str, object]) -> dict[str, object]:
        self._compact()
        started = time.perf_counter()
        audit = audit_site(self.root)
        self.audit_seconds = time.perf_counter() - started
        manifest = {
            "explorer_version": 2,
            "location_contract": "semantic digest filename to current relative page/anchor",
            "locations": dict(sorted(self.locations.items())),
            "model_sha256": self.model_hash,
            **metadata,
            **audit,
            "largest_html_bytes": self.largest,
            "content_bytes": self.total,
            "files": dict(sorted(self.files.items())),
        }
        self.write(
            "manifest.json", (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode()
        )
        return {**manifest, "total_bytes": self.total, "file_count": len(self.files)}
