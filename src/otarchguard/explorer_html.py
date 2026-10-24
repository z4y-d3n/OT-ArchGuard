"""Narrow HTML/SVG safety boundary and complete-site link/resource validation."""

import hashlib
import html
import json
import re
import time
from collections import defaultdict
from collections.abc import Sequence
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
@media(max-width:640px){header,nav,main,footer{padding:1rem}h1{font-size:1.5rem}
nav ul{gap:1rem}.cards{display:block}.cards li{margin:.6rem 0}}
@media print{html{background:white;color:black}nav,.skip{display:none}a{color:black}
.scroll{overflow:visible}svg{max-width:100%;height:auto}table{min-width:0}}
"""

_PATH = re.compile(
    r"(?i)(?:file://\S+|[a-z]:[\\/]\S*|\\\\[^\s<>]+|/(?:home|users|tmp|var|private|etc)/[^\s<>]*)"
)
_BIDI = frozenset(range(0x202A, 0x202F)) | frozenset(range(0x2066, 0x206A))
_ALLOWED_ELEMENTS = frozenset(
    "html head meta link title body a header p h1 h2 h3 nav ul li main section dl dt dd div "
    "table caption thead tr th tbody td aside footer figure figcaption pre code br svg "
    "desc defs marker path clippath rect g text circle".split()
)


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


def table(caption: str, headings: tuple[str, ...], rows: Sequence[tuple[str, ...]]) -> str:
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
        + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows)
        + "</tbody></table></div>"
    )


LEGEND = (
    '<aside class="legend" aria-label="Trust legend"><h2>Trust legend</h2><ul>'
    "<li>Documentary evidence · dashed line · Documented only. Unknown from documentary "
    "evidence alone; drawings do not authorize communication.</li>"
    "<li>Owner-confirmed architecture · solid line · Declared only. Validation establishes "
    "model consistency, not physical network truth or permission on every edge.</li>"
    "<li>Analytical result · double or heavy line · Specific evaluated query. Only the exact "
    "model, direction, transport and ports shown were evaluated.</li></ul>"
    "<p>Not evaluated differs from a negative result. Not modeled paths remain unassessed. "
    "Unsupported input is an error. Layout proximity and missing drawing edges establish "
    "neither reachability nor isolation.</p></aside>"
)


def document(
    title: str,
    body: str,
    model_hash: str,
    navigation: tuple[tuple[str, str], ...] | None = None,
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
        + "</h1><p>Model SHA-256: <code>"
        + escape(model_hash)
        + '</code></p></header><nav aria-label="Explorer"><ul>'
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
        + "</main><footer>Local full-detail engineering report. Review before sharing: "
        "asset names, addresses and selected evidence may be sensitive. Original documents "
        "are not included. Hashes detect changes; they do not authenticate authorship. "
        "Explorer contract 2; native schema 1. No JavaScript required.</footer></body></html>\n"
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
        size = len(document(title, body, self.model_hash, self.navigation))
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
                    name, document(title, links(body, name), self.model_hash, self.navigation)
                )
        for name, members in sorted(grouped.items()):
            body = (
                '<p class="notice">This page contains additional local documentary evidence '
                "and is not a public-safe export.</p>"
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
                    "Grouped " + name.partition("-")[0] + " evidence",
                    body,
                    self.model_hash,
                    self.navigation,
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
