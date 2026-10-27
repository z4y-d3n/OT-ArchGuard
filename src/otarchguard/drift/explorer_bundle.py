"""Bounded offline publication and portable integrity, never analytical authority.

The completion manifest is published last into an exclusively reserved directory.
An interrupted publication has no valid completion manifest and is not a bundle.
Hashes detect corruption; an attacker able to rewrite all files can mint a new
internally consistent bundle. Source-dependent reproduction remains separate.
"""

import hashlib
import json
import os
import re
import stat
import tempfile
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from otarchguard.diagnostics import check_limit, fail
from otarchguard.drift.reports import _structure
from otarchguard.evidence.paths import _check_read_path
from otarchguard.evidence.workspace import _file_identity

MANIFEST = "explorer-manifest.json"
RENDERER = "otarchguard.historical-explorer.1"
_NAME = re.compile(r"[a-z0-9-]+\.(?:html|css|json)\Z")
_TARGET = re.compile(r"(?:[a-z0-9-]+\.(?:html|css|json))?(?:#[a-z0-9-]+)?\Z")
_HEX = re.compile(r"[0-9a-f]{64}\Z")
_REQUIRED = {"index.html", "style.css", "report.json", "verification.json"}


@dataclass(frozen=True, slots=True)
class BundleLimits:
    files: int = 4096
    page_bytes: int = 2 * 1024 * 1024
    json_bytes: int = 32 * 1024 * 1024
    manifest_bytes: int = 4 * 1024 * 1024
    total_bytes: int = 256 * 1024 * 1024
    links: int = 1_000_000
    svg_bytes: int = 128 * 1024
    svg_nodes: int = 256
    json_nodes: int = 2_000_000
    json_depth: int = 64


BUNDLE_LIMITS = BundleLimits()
_TAGS = frozenset(
    "html head title meta link body header nav main footer section article aside "
    "h1 h2 h3 h4 p div span a ul ol li dl dt dd table caption thead tbody tfoot tr th td "
    "details summary code pre strong em small b i br hr figure figcaption abbr time "
    "svg title desc defs marker path rect circle ellipse line polyline polygon text tspan g".split()
)
_VOID = {"meta", "link", "br", "hr"}
_ATTRS = frozenset(
    "id class lang dir title role tabindex href rel charset name content http-equiv "
    "scope colspan rowspan datetime open width height viewbox preserveaspectratio "
    "x y x1 x2 y1 y2 cx cy r rx ry d points fill stroke stroke-width stroke-dasharray "
    "marker-end marker-start markerwidth markerheight refx refy orient text-anchor "
    "xmlns focusable version aria-label aria-labelledby aria-describedby aria-current "
    "aria-hidden font-size dominant-baseline transform".split()
)


def canonical(value: object) -> bytes:
    try:
        return (
            json.dumps(
                value, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False
            ).encode("ascii")
            + b"\n"
        )
    except (TypeError, ValueError, RecursionError):
        fail("HISTORICAL_BUNDLE", "$", "Unsupported bundle metadata.")


def _json(data: bytes) -> dict[str, Any]:
    check_limit("historical_json_bytes", len(data), BUNDLE_LIMITS.json_bytes)

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                fail("HISTORICAL_BUNDLE", "$", "Duplicate JSON keys are forbidden.")
            result[key] = value
        return result

    def invalid(value: str) -> None:
        fail("HISTORICAL_BUNDLE", "$", "Nonstandard JSON constants are forbidden.")

    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=pairs, parse_constant=invalid)
    except (ValueError, UnicodeError, RecursionError):
        fail("HISTORICAL_BUNDLE", "$", "Malformed bundle JSON.")
    if type(value) is not dict:
        fail("HISTORICAL_BUNDLE", "$", "Bundle JSON root must be an object.")
    stack: list[tuple[object, int]] = [(value, 0)]
    count = 0
    while stack:
        item, depth = stack.pop()
        count += 1
        check_limit("historical_json_nodes", count, BUNDLE_LIMITS.json_nodes)
        check_limit("historical_json_depth", depth, BUNDLE_LIMITS.json_depth)
        if isinstance(item, dict):
            stack.extend((child, depth + 1) for child in item.values())
        elif isinstance(item, list):
            stack.extend((child, depth + 1) for child in item)
    return value


class _Page(HTMLParser):
    """Independent validation over emitted HTML, with no browser execution."""

    def __init__(self, text: str) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: set[str] = set()
        self.links: list[str] = []
        self.stack: list[str] = []
        self.counts: dict[str, int] = {}
        self.lang = self.csp = self.css = self.skip = False
        self.svg_nodes = 0
        self.svg_depth = 0
        try:
            self.feed(text)
            self.close()
        except (ValueError, RecursionError):
            fail("HISTORICAL_HTML", "$", "Malformed or unsafe generated HTML.")
        if self.stack or not all((self.lang, self.csp, self.css, self.skip)):
            fail("HISTORICAL_HTML", "$", "Incomplete accessible offline document structure.")
        if any(
            self.counts.get(tag) != 1 for tag in ("html", "head", "title", "body", "main", "h1")
        ):
            fail("HISTORICAL_HTML", "$", "Expected one document, title, main and first heading.")
        if "main" not in self.ids:
            fail("HISTORICAL_HTML", "$", "Missing skip-to-content destination.")

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in _TAGS or len({key for key, _ in attrs}) != len(attrs):
            raise ValueError("Unsupported tag or duplicate attribute")
        attributes = dict(attrs)
        for key, value in attrs:
            if key not in _ATTRS or key.startswith("on"):
                raise ValueError("Unsafe attribute")
            if value is not None and any(
                unicodedata.category(c) in {"Cc", "Cf", "Cs"} and c not in "\t\n\r" for c in value
            ):
                raise ValueError("Invisible attribute controls")
            if key == "id":
                if value is None or not re.fullmatch(r"[a-z0-9-]+", value) or value in self.ids:
                    raise ValueError("Invalid or duplicate document identifier")
                self.ids.add(value)
            if key == "href":
                if tag not in {"a", "link"} or not value or not _TARGET.fullmatch(value):
                    raise ValueError("Unsafe link")
                self.links.append(value)
                self.skip |= value == "#main"
            if value and "\\" in value and key not in {"title", "aria-label"}:
                raise ValueError("Escaped presentation attribute")
            if value and re.search(r"url\s*\(", value, re.IGNORECASE):
                if not re.fullmatch(r"url\(#[a-z0-9-]+\)", value):
                    raise ValueError("External SVG resource")
                self.links.append(value[4:-1])
        if tag == "html":
            self.lang = bool(attributes.get("lang"))
        if tag == "link":
            if attributes != {"rel": "stylesheet", "href": "style.css"}:
                raise ValueError("Only one fixed local stylesheet is supported")
            self.css = True
        if tag == "meta" and "http-equiv" in attributes:
            if (attributes.get("http-equiv") or "").lower() != "content-security-policy":
                raise ValueError("Active meta directive")
            directives = {
                item.strip()
                for item in (attributes.get("content") or "").split(";")
                if item.strip()
            }
            required = {
                "default-src 'none'",
                "script-src 'none'",
                "style-src 'self'",
                "base-uri 'none'",
                "form-action 'none'",
            }
            if not required <= directives or directives - required - {
                "img-src 'none'",
                "object-src 'none'",
                "connect-src 'none'",
                "font-src 'none'",
                "frame-src 'none'",
            }:
                raise ValueError("Insufficient content security policy")
            self.csp = True
        if tag == "svg":
            if "viewbox" not in attributes or not (
                attributes.get("aria-label") or attributes.get("aria-labelledby")
            ):
                raise ValueError("Unlabelled or unbounded SVG")
            self.svg_depth += 1
        if self.svg_depth:
            self.svg_nodes += 1
            check_limit("historical_svg_nodes", self.svg_nodes, BUNDLE_LIMITS.svg_nodes)
        if not self.svg_depth:
            self.counts[tag] = self.counts.get(tag, 0) + 1
        if tag not in _VOID:
            self.stack.append(tag)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in _VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if not self.stack or self.stack.pop() != tag:
            raise ValueError("Unbalanced HTML")
        if tag == "svg":
            self.svg_depth -= 1

    def handle_data(self, data: str) -> None:
        if any(unicodedata.category(c) in {"Cc", "Cf", "Cs"} and c not in "\t\n\r" for c in data):
            raise ValueError("Invisible display controls")


def audit_files(files: dict[str, bytes]) -> dict[str, int]:
    """Audit all actual emitted bytes and local links, including fragments."""
    if not _REQUIRED <= files.keys() or MANIFEST in files:
        fail("HISTORICAL_BUNDLE", "$", "Required members missing or reserved manifest supplied.")
    check_limit("historical_files", len(files) + 1, BUNDLE_LIMITS.files)
    pages: dict[str, _Page] = {}
    total = largest = largest_svg = 0
    for name, data in sorted(files.items()):
        if not _NAME.fullmatch(name) or type(data) is not bytes:
            fail("HISTORICAL_BUNDLE", "$", "Unsafe bundle member name or bytes.")
        maximum = BUNDLE_LIMITS.json_bytes if name.endswith(".json") else BUNDLE_LIMITS.page_bytes
        check_limit("historical_file_bytes", len(data), maximum)
        total += len(data)
        check_limit("historical_total_bytes", total, BUNDLE_LIMITS.total_bytes)
        if name.endswith(".json"):
            _json(data)
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeError:
            fail("HISTORICAL_HTML", "$", "Invalid Unicode in generated presentation.")
        if name.endswith(".css"):
            if name != "style.css" or re.search(
                r"url\s*\(|@(?!media\b)|expression\s*\(|[\\<\"']|/\*", text, re.IGNORECASE
            ):
                fail("HISTORICAL_HTML", "$", "Unsafe or unexpected stylesheet.")
            continue
        pages[name] = _Page(text)
        largest = max(largest, len(data))
        for svg in re.findall(r"<svg\b.*?</svg>", text, flags=re.DOTALL):
            size = len(svg.encode("utf-8"))
            largest_svg = max(largest_svg, size)
            check_limit("historical_svg_bytes", size, BUNDLE_LIMITS.svg_bytes)
    links = 0
    for name, page in pages.items():
        for target in page.links:
            file, _, fragment = target.partition("#")
            file = file or name
            if file not in files:
                fail("HISTORICAL_LINK", "$", "Broken local file link.")
            if fragment and (file not in pages or fragment not in pages[file].ids):
                fail("HISTORICAL_LINK", "$", "Broken local fragment link.")
            links += 1
            check_limit("historical_links", links, BUNDLE_LIMITS.links)
        for attrs in re.findall(r'aria-labelledby="([^"]+)"', files[name].decode("utf-8")):
            if any(target not in page.ids for target in attrs.split()):
                fail("HISTORICAL_HTML", "$", "Broken accessible label reference.")
    return {
        "html_pages": len(pages),
        "internal_links": links,
        "anchors": sum(len(page.ids) for page in pages.values()),
        "broken_links": 0,
        "largest_page_bytes": largest,
        "largest_svg_bytes": largest_svg,
        "content_bytes": total,
    }


def _bundle_id(body: dict[str, Any]) -> str:
    return (
        "historical-explorer-"
        + hashlib.sha256(b"otarchguard.historical-explorer.v1\x00" + canonical(body)).hexdigest()
    )


def _identity(files: dict[str, bytes], identity: dict[str, Any]) -> None:
    """Bind portable claims structurally; this does not authenticate their author."""
    names = {
        "historical_explorer_version",
        "renderer_version",
        "renderer_sha256",
        "report_sha256",
        "report_bytes",
        "drift_id",
        "drift_version",
        "engine_version",
        "comparability_policy_version",
        "baseline_id",
        "recorded_approval_id",
        "workspace_inventory_sha256",
        "generation_verification",
        "options",
    }
    if type(identity) is not dict or set(identity) != names:
        fail("HISTORICAL_IDENTITY", "$", "Unsupported Explorer source identity.")
    for key in ("historical_explorer_version", "drift_version", "comparability_policy_version"):
        if type(identity[key]) is not int or identity[key] != 1:
            fail("HISTORICAL_IDENTITY", "$", "Unsupported source version.")
    for key in ("renderer_sha256", "report_sha256", "workspace_inventory_sha256"):
        if type(identity[key]) is not str or not _HEX.fullmatch(identity[key]):
            fail("HISTORICAL_IDENTITY", "$", "Malformed source digest.")
    if (
        identity["renderer_version"] != "1.4.0-historical-explorer.1"
        or identity["report_sha256"] != hashlib.sha256(files["report.json"]).hexdigest()
        or type(identity["report_bytes"]) is not int
        or identity["report_bytes"] != len(files["report.json"])
    ):
        fail("HISTORICAL_IDENTITY", "$", "Source identity does not bind exact report bytes.")
    options = identity["options"]
    if (
        type(options) is not dict
        or set(options) != {"page_size"}
        or type(options["page_size"]) is not int
        or not 5 <= options["page_size"] <= 200
    ):
        fail("HISTORICAL_IDENTITY", "$", "Unsupported display options.")
    report = _structure(_json(files["report.json"]))
    receipt = _json(files["verification.json"])
    receipt_keys = {
        "status",
        "drift_id",
        "structure_valid",
        "source_dependencies_available",
        "canonical_reproduction",
        "recorded_baseline_status",
        "current_baseline_status",
        "currently_approved_reference",
        "review_graph_changed",
        "authority",
    }
    if set(receipt) != receipt_keys or receipt != identity["generation_verification"]:
        fail("HISTORICAL_IDENTITY", "$", "Generation receipt differs from source identity.")
    if any(
        type(receipt[key]) is not str
        for key in (
            "status",
            "drift_id",
            "recorded_baseline_status",
            "current_baseline_status",
            "authority",
        )
    ):
        fail("HISTORICAL_IDENTITY", "$", "Malformed generation receipt text.")
    if (
        receipt["status"] != "REPRODUCIBLE_HISTORICAL_REPORT"
        or receipt["recorded_baseline_status"] != "APPROVED"
        or receipt["current_baseline_status"] not in {"APPROVED", "REVOKED", "SUPERSEDED"}
        or any(
            receipt[key] is not True
            for key in (
                "structure_valid",
                "source_dependencies_available",
                "canonical_reproduction",
            )
        )
        or type(receipt["review_graph_changed"]) is not bool
        or type(receipt["currently_approved_reference"]) is not bool
        or receipt["currently_approved_reference"]
        != (receipt["current_baseline_status"] == "APPROVED")
        or receipt["authority"]
        != (
            "Review graph is an unauthenticated local assertion; "
            "report creation time is not attested."
        )
    ):
        fail("HISTORICAL_IDENTITY", "$", "Malformed historical generation assertion.")
    try:
        selected = {
            "drift_id": report["drift_id"],
            "drift_version": report["drift_version"],
            "engine_version": report["engine_version"],
            "comparability_policy_version": report["comparability_policy_version"],
            "baseline_id": report["inputs"]["baseline"]["baseline_id"],
            "recorded_approval_id": report["inputs"]["approval"]["review_id"],
        }
    except (KeyError, TypeError, AttributeError):
        fail("HISTORICAL_IDENTITY", "$", "Malformed report identity dependencies.")
    if any(identity[key] != value for key, value in selected.items()) or (
        receipt["drift_id"] != report["drift_id"]
    ):
        fail("HISTORICAL_IDENTITY", "$", "Source identity does not match retained report.")


def _manifest(files: dict[str, bytes], identity: dict[str, Any]) -> dict[str, Any]:
    audit = audit_files(files)
    _identity(files, identity)
    body = {
        "historical_explorer_version": 1,
        "renderer": RENDERER,
        "identity": identity,
        "files": [
            {"name": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
            for name, data in sorted(files.items())
        ],
        "audit": audit,
    }
    return body | {"bundle_id": _bundle_id(body)}


def _read_file(path: Path, maximum: int) -> bytes:
    _check_read_path(path)
    try:
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode):
            fail("HISTORICAL_PATH", "$", "Bundle members must be regular local files.")
        check_limit("historical_file_bytes", before.st_size, maximum)
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        with os.fdopen(os.open(path, flags), "rb") as stream:
            opened = os.fstat(stream.fileno())
            if _file_identity(before) != _file_identity(opened):
                fail("HISTORICAL_CHANGED", "$", "Bundle changed during opening.")
            data = stream.read(maximum + 1)
            after = os.fstat(stream.fileno())
        _check_read_path(path)
        if (
            _file_identity(opened) != _file_identity(after)
            or opened.st_ctime_ns != after.st_ctime_ns
            or _file_identity(after) != _file_identity(path.lstat())
        ):
            fail("HISTORICAL_CHANGED", "$", "Bundle changed during reading.")
    except OSError:
        fail("HISTORICAL_READ", "$", "Cannot read the complete local bundle.")
    check_limit("historical_file_bytes", len(data), maximum)
    return data


def _result(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "PORTABLE_INTEGRITY_VALID",
        "bundle_id": manifest["bundle_id"],
        "historical_explorer_version": 1,
        "identity": manifest["identity"],
        "files": len(manifest["files"]) + 1,
        **manifest["audit"],
        "analytical_reproduction": False,
        "authority": (
            "Internal integrity only; source-dependent analytical reproduction is separate."
        ),
    }


def verify_bundle(output: Path) -> dict[str, Any]:
    """Verify portable integrity without rewriting, acquiring sources or granting trust."""
    _check_read_path(output)
    try:
        if not output.is_dir():
            fail("HISTORICAL_PATH", "$", "Select a complete local Explorer directory.")
        names: set[str] = set()
        for entry in output.iterdir():
            names.add(entry.name)
            check_limit("historical_files", len(names), BUNDLE_LIMITS.files)
            _check_read_path(entry)
            if not _NAME.fullmatch(entry.name) or not stat.S_ISREG(entry.lstat().st_mode):
                fail("HISTORICAL_PATH", "$", "Unexpected or nonregular bundle member.")
        raw = _read_file(output / MANIFEST, BUNDLE_LIMITS.manifest_bytes)
        manifest = _json(raw)
        if (
            set(manifest)
            != {
                "historical_explorer_version",
                "renderer",
                "identity",
                "files",
                "audit",
                "bundle_id",
            }
            or manifest["historical_explorer_version"] != 1
            or type(manifest["historical_explorer_version"]) is not int
            or manifest["renderer"] != RENDERER
            or type(manifest["identity"]) is not dict
        ):
            fail("HISTORICAL_BUNDLE", "$", "Unsupported Explorer publication contract.")
        inventory = manifest["files"]
        if type(inventory) is not list:
            fail("HISTORICAL_BUNDLE", "$", "Malformed bundle inventory.")
        expected: set[str] = set()
        files: dict[str, bytes] = {}
        total = 0
        for item in inventory:
            if type(item) is not dict or set(item) != {"name", "bytes", "sha256"}:
                fail("HISTORICAL_BUNDLE", "$", "Malformed inventory member.")
            name, size, digest = item["name"], item["bytes"], item["sha256"]
            if (
                type(name) is not str
                or not _NAME.fullmatch(name)
                or name == MANIFEST
                or name in expected
                or type(size) is not int
                or size < 0
                or type(digest) is not str
                or not _HEX.fullmatch(digest)
            ):
                fail("HISTORICAL_BUNDLE", "$", "Unsafe or duplicate inventory identity.")
            expected.add(name)
            total += size
            check_limit("historical_total_bytes", total + len(raw), BUNDLE_LIMITS.total_bytes)
            maximum = (
                BUNDLE_LIMITS.json_bytes if name.endswith(".json") else BUNDLE_LIMITS.page_bytes
            )
            check_limit("historical_file_bytes", size, maximum)
            data = _read_file(output / name, maximum)
            if len(data) != size or hashlib.sha256(data).hexdigest() != digest:
                fail("HISTORICAL_INTEGRITY", "$", "Bundle member bytes do not match the manifest.")
            files[name] = data
        if names != expected | {MANIFEST}:
            fail("HISTORICAL_INTEGRITY", "$", "Bundle inventory is not exact.")
        expected_manifest = _manifest(files, manifest["identity"])
        if manifest != expected_manifest or raw != canonical(expected_manifest):
            fail("HISTORICAL_INTEGRITY", "$", "Bundle manifest or presentation audit mismatch.")
    except OSError:
        fail("HISTORICAL_READ", "$", "Cannot read the complete local bundle.")
    return _result(manifest)


def publish(
    files: dict[str, bytes],
    identity: dict[str, Any],
    output: Path,
    *,
    before_publish: Callable[[], None],
) -> dict[str, Any]:
    """Stage and audit all files; exclusively reserve output; publish completion last.

    A failure after reservation intentionally leaves an incomplete directory for
    inspection. It cannot verify as complete and is never silently overwritten.
    """
    _check_read_path(output)
    if output.exists() or output.is_symlink() or not output.parent.is_dir():
        fail("HISTORICAL_PATH", "$", "Use a fresh directory under an existing local parent.")
    manifest = _manifest(files, identity)
    raw = canonical(manifest)
    check_limit("historical_manifest_bytes", len(raw), BUNDLE_LIMITS.manifest_bytes)
    check_limit(
        "historical_total_bytes",
        manifest["audit"]["content_bytes"] + len(raw),
        BUNDLE_LIMITS.total_bytes,
    )
    try:
        with tempfile.TemporaryDirectory(dir=output.parent, prefix=".historical-explorer-") as root:
            stage = Path(root)
            for name, data in sorted(files.items()):
                (stage / name).write_bytes(data)
            _check_read_path(output)
            output.mkdir()
            for name in sorted(files):
                _check_read_path(output)
                with (output / name).open("xb") as stream:
                    stream.write((stage / name).read_bytes())
            actual: dict[str, bytes] = {}
            for name, expected in files.items():
                maximum = (
                    BUNDLE_LIMITS.json_bytes if name.endswith(".json") else BUNDLE_LIMITS.page_bytes
                )
                actual[name] = _read_file(output / name, maximum)
                if actual[name] != expected:
                    fail("HISTORICAL_CHANGED", "$", "Published member differs from staged bytes.")
            if _manifest(actual, identity) != manifest:
                fail("HISTORICAL_CHANGED", "$", "Emitted site differs from its staged audit.")
            before_publish()
            _check_read_path(output)
            with (output / MANIFEST).open("xb") as stream:
                stream.write(raw)
    except OSError:
        fail(
            "HISTORICAL_PUBLISH",
            "$",
            "Publication failed; incomplete output has no valid manifest.",
        )
    return _result(manifest) | {"status": "PUBLISHED", "output": str(output.absolute())}
