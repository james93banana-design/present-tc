#!/usr/bin/env python3
"""Read-only, heuristic checks. Not a renderer, sanitizer or security audit."""
import argparse
import json
import posixpath
import re
import sys
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree as ET

MAX_FILE_BYTES = 100 * 1024 * 1024
MAX_PARTS = 10000
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"


def finding(items, level, code, message):
    items.append({"level": level, "code": code, "message": message})


def resource(items, value, context):
    value = value.strip()
    if not value or value.startswith("#"):
        return
    if value.lower().startswith("data:"):
        if "," not in value:
            finding(items, "error", "data-uri", context + ": malformed data URI")
        return
    finding(items, "error", "offline-resource", context + ": non-embedded resource")


class ReportParser(HTMLParser):
    def __init__(self, items):
        super().__init__(convert_charrefs=True)
        self.items = items
        self.tags = set()
        self.charset = False
        self.styles = []
        self.scripts = []
        self.mode = None

    def handle_starttag(self, tag, attrs):
        self.tags.add(tag)
        values = dict(attrs)
        if tag in ("style", "script"):
            self.mode = tag
        if tag == "meta" and values.get("charset", "").lower() in ("utf-8", "utf8"):
            self.charset = True
        if values.get("style"):
            self.styles.append(values["style"])
        if any(key.lower().startswith("on") for key in values):
            finding(self.items, "warning", "event-handler", "Review inline event handlers")
        for key in ("src", "poster", "background", "action", "formaction"):
            if values.get(key):
                resource(self.items, values[key], tag + "[" + key + "]")
        if tag in ("link", "image", "use"):
            for key in ("href", "xlink:href"):
                if values.get(key):
                    resource(self.items, values[key], tag + "[" + key + "]")
        if tag == "object" and values.get("data"):
            resource(self.items, values["data"], "object[data]")
        if values.get("srcset"):
            finding(self.items, "warning", "srcset", "Review every srcset candidate for offline use")
        if tag in ("iframe", "object", "embed"):
            finding(self.items, "warning", "active-embed", "Review embedded active content: " + tag)
        if tag == "a" and values.get("href"):
            href = values["href"].strip()
            scheme = urlsplit(href).scheme.lower()
            if scheme in ("javascript", "file") or href.startswith(("/Users/", "/home/")):
                finding(self.items, "error", "unsafe-link", "Review local or executable hyperlink")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if self.mode == tag:
            self.mode = None

    def handle_data(self, data):
        if self.mode == "style":
            self.styles.append(data)
        elif self.mode == "script":
            self.scripts.append(data)


def check_html(path, items):
    text = path.read_text(encoding="utf-8-sig")
    parser = ReportParser(items)
    parser.feed(text)
    parser.close()
    for tag in ("html", "head", "title", "body"):
        if tag not in parser.tags:
            finding(items, "error", "html-structure", "Missing element: " + tag)
    if not parser.charset:
        finding(items, "warning", "charset", "No UTF-8 meta charset found")
    for style in parser.styles:
        style = re.sub(r"/\*.*?\*/", "", style, flags=re.S)
        for match in re.finditer(r"url\(\s*(['\"]?)(.*?)\1\s*\)", style, re.I | re.S):
            resource(items, match.group(2), "CSS url()")
        for match in re.finditer(r"@import\s+(['\"])(.*?)\1", style, re.I | re.S):
            resource(items, match.group(2), "CSS @import")
    code = "\n".join(parser.scripts)
    if re.search(r"\b(fetch\s*\(|XMLHttpRequest|WebSocket|sendBeacon|import\s*\()", code):
        finding(items, "warning", "dynamic-network", "Review JS for dynamic network/resource loading")
    finding(items, "info", "visual-unchecked", "Browser, offline execution, layout and print not tested")


def read_xml(data, name, items):
    if b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
        finding(items, "error", "xml-declaration", "DTD/entity declarations are not supported: " + name)
        return None
    try:
        return ET.fromstring(data)
    except ET.ParseError:
        finding(items, "error", "xml-invalid", "Malformed XML: " + name)
        return None


def resolve_target(rels_name, target):
    if rels_name == "_rels/.rels":
        base = ""
    else:
        base = posixpath.dirname(posixpath.dirname(rels_name))
    part = unquote(urlsplit(target).path)
    if part.startswith("/"):
        return posixpath.normpath(part.lstrip("/"))
    return posixpath.normpath(posixpath.join(base, part))


def check_pptx(path, items):
    with zipfile.ZipFile(path) as package:
        infos = package.infolist()
        if len(infos) > MAX_PARTS or sum(item.file_size for item in infos) > MAX_FILE_BYTES:
            finding(items, "error", "size-limit", "PPTX exceeds inspection limits")
            return
        names = {item.filename for item in infos}
        if len(names) != len(infos):
            finding(items, "error", "duplicate-part", "Duplicate ZIP member names")
        for name in names:
            parts = name.replace("\\", "/").split("/")
            if ".." in parts or name.startswith(("/", "\\")):
                finding(items, "error", "part-path", "Suspicious package path")
        required = ("[Content_Types].xml", "_rels/.rels", "ppt/presentation.xml", "ppt/_rels/presentation.xml.rels")
        for name in required:
            if name not in names:
                finding(items, "error", "missing-part", "Missing part: " + name)
        roots = {}
        for name in sorted(names):
            if name.endswith((".xml", ".rels")):
                root = read_xml(package.read(name), name, items)
                if root is not None:
                    roots[name] = root
            lower = name.lower()
            if "vbaproject" in lower or lower.endswith(".vba"):
                finding(items, "error", "macro", "Macro content found; do not execute")
            if lower.startswith("ppt/embeddings/"):
                finding(items, "warning", "embedded-object", "Review embedded data/object: " + name)
        relationship_maps = {}
        for name, root in roots.items():
            if not name.endswith(".rels"):
                continue
            mapping = {}
            for rel in root.findall("{" + REL_NS + "}Relationship"):
                ident, target = rel.get("Id", ""), rel.get("Target", "")
                if not ident or ident in mapping:
                    finding(items, "error", "relationship-id", "Missing or repeated relationship ID: " + name)
                if rel.get("TargetMode") == "External":
                    mapping[ident] = None
                    finding(items, "warning", "external-relationship", "Review external relationship in " + name)
                    continue
                resolved = resolve_target(name, target)
                mapping[ident] = resolved
                if not target or resolved not in names:
                    finding(items, "error", "relationship-target", "Missing internal relationship target in " + name)
            relationship_maps[name] = mapping
        presentation = roots.get("ppt/presentation.xml")
        if presentation is not None:
            slides = presentation.findall("./{" + P_NS + "}sldIdLst/{" + P_NS + "}sldId")
            if not slides:
                finding(items, "error", "slides-empty", "No slides in presentation order")
            mapping = relationship_maps.get("ppt/_rels/presentation.xml.rels", {})
            for slide in slides:
                target = mapping.get(slide.get("{" + R_NS + "}id", ""))
                if target not in names or not re.fullmatch(r"ppt/slides/slide\d+\.xml", target or ""):
                    finding(items, "error", "slide-reference", "Invalid presentation slide reference")
            finding(items, "info", "slide-count", "Slides in presentation order: " + str(len(slides)))
        for name, root in roots.items():
            if re.fullmatch(r"ppt/slides/slide\d+\.xml", name):
                if root.get("show") in ("0", "false"):
                    finding(items, "warning", "hidden-slide", "Review hidden slide: " + name)
                if not any((node.text or "").strip() for node in root.iter("{" + A_NS + "}t")):
                    finding(items, "warning", "no-native-text", "No native text found; review editability: " + name)
            if name.startswith(("ppt/notesSlides/notesSlide", "ppt/comments/")):
                finding(items, "warning", "notes-comments", "Review non-visible content: " + name)
            if name == "docProps/core.xml":
                for node in root.iter():
                    if node.tag.rsplit("}", 1)[-1] in ("creator", "lastModifiedBy") and (node.text or "").strip():
                        finding(items, "warning", "author-metadata", "Review author metadata (value not printed)")
    finding(items, "info", "visual-unchecked", "Rendering, application compatibility and editability not tested")


def inspect(path):
    path = Path(path)
    items = []
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            finding(items, "error", "size-limit", "Input exceeds 100 MiB inspection limit")
        elif path.suffix.lower() in (".html", ".htm"):
            check_html(path, items)
        elif path.suffix.lower() == ".pptx":
            check_pptx(path, items)
        else:
            finding(items, "error", "unsupported", "Expected .html, .htm or .pptx")
    except (OSError, UnicodeError, ValueError, zipfile.BadZipFile, RuntimeError, NotImplementedError) as exc:
        finding(items, "error", "read-failed", "Could not inspect file: " + type(exc).__name__)
    return items


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--json", action="store_true", help="Print structured findings")
    args = parser.parse_args()
    items = inspect(args.path)
    if args.json:
        print(json.dumps(items, ensure_ascii=False, indent=2))
    else:
        for item in items:
            print("[{level}] {code}: {message}".format(**item))
    return 1 if any(item["level"] == "error" for item in items) else 0


if __name__ == "__main__":
    sys.exit(main())
