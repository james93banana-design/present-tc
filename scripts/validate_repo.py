#!/usr/bin/env python3
"""Validate this repository's structure and basic publication hygiene."""
import argparse
import hashlib
import json
import re
import sys
import zipfile
from xml.etree import ElementTree as ET
from pathlib import Path
from sync_palette import check as check_palette

ROOT = Path(__file__).resolve().parents[1]
IGNORED = {".git", "__pycache__", ".venv", "outputs", ".qa", "dist", "local-work"}
ALLOWED_SUFFIXES = {".md", ".py", ".yaml", ".yml", ".txt", ".js", ".css", ".json"}
REQUIRED = (
    "SKILL.md", "README.md", "agents/openai.yaml", "requirements.txt",
    "references/html-report.md", "references/ppt-report.md",
    "references/visual-system.md", "references/layout-routing.md",
    "references/delivery-qa.md", "references/public-boundaries.md",
    "scripts/check_delivery.py", "tests/test_checks.py", "tests/scenarios.md",
    "examples/brief.md", "docs/RELEASING.md", ".github/workflows/validate.yml",
    "scripts/check_public.py", "assets/report-tokens.json",
    "assets/html/content-modules.js", "assets/html/countdown.js",
    "assets/html/module-layout-editor.js", "assets/html/page-numbers.js",
    "assets/html/countdown.css", "assets/html/editor.css", "assets/html/shell.css",
    "assets/html/palette.css", "scripts/sync_palette.py",
    "references/html-features.md", "references/layout-contract.md",
    "assets/present-tc/selection-guide.md", "assets/present-tc/templates.json",
    "assets/present-tc/page-mapping.csv",
    "assets/present-tc/assets/fonts/Tencent-W3.woff2",
    "assets/present-tc/assets/fonts/Tencent-W7.woff2",
)


def validate_bundle(root):
    bundle = Path(root) / "assets/present-tc"
    errors = []

    def resource(name):
        path = (bundle / name).resolve()
        if not path.is_relative_to(bundle.resolve()) or not path.is_file():
            raise ValueError("Missing or invalid bundle resource: " + name)
        return path

    try:
        index = json.loads(resource("templates.json").read_text(encoding="utf-8"))
        pages = index["pages"]
        count = index["source"]["slide_count"]
        if len(pages) != count or sorted(p["source_slide"] for p in pages) != list(range(1, count + 1)):
            errors.append("Bundle index page count/order mismatch")
        if len({p["id"] for p in pages}) != len(pages):
            errors.append("Bundle index contains duplicate IDs")
        deck = resource(index["source"]["asset_path"])
        if hashlib.sha256(deck.read_bytes()).hexdigest() != index["source"]["sha256"]:
            errors.append("Bundle PPTX hash differs from index")
        for page in pages:
            resource(page["thumbnail"])
            resource(page["source_asset"])
        resource(index["source"]["mapping_file"])
        with zipfile.ZipFile(deck) as archive:
            if archive.testzip() is not None:
                errors.append("Bundle PPTX contains a corrupt member")
            presentation = ET.fromstring(archive.read("ppt/presentation.xml"))
            ids = presentation.findall("{http://schemas.openxmlformats.org/presentationml/2006/main}sldIdLst/{http://schemas.openxmlformats.org/presentationml/2006/main}sldId")
            if len(ids) != count:
                errors.append("Bundle PPTX slide count differs from index")
        for weight in ("W3", "W7"):
            font = resource("assets/fonts/Tencent-" + weight + ".woff2")
            with font.open("rb") as stream:
                if stream.read(4) != b"wOF2":
                    errors.append("Invalid WOFF2 header: " + font.name)
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile, ET.ParseError) as exc:
        errors.append("Bundle validation failed: " + str(exc))
    return errors


def validate(root, release=False):
    root = Path(root).resolve()
    errors = []
    for name in REQUIRED:
        if not (root / name).is_file():
            errors.append("Missing required file: " + name)
    skill = root / "SKILL.md"
    if skill.is_file():
        text = skill.read_text(encoding="utf-8")
        match = re.match(r'\A---\nname: ([a-z0-9-]+)\ndescription: ("[^\n]+")\n---\n', text)
        if not match:
            errors.append("Expected name and quoted description in SKILL.md frontmatter")
        else:
            if match.group(1) != "present-tc" or not (root.name == match.group(1) or root.name.startswith("skill-")):
                errors.append("Skill name must be present-tc; directory must be present-tc or its registered skill-* identity")
            try:
                description = json.loads(match.group(2))
                if not 1 <= len(description) <= 1024 or any(c in description for c in "<>"):
                    errors.append("Description must be 1-1024 characters without angle brackets")
            except ValueError:
                errors.append("Description must use a valid JSON-compatible YAML quoted string")
        if len(text.splitlines()) > 500:
            errors.append("Keep SKILL.md below 500 lines")
    count = 0
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in IGNORED for part in relative.parts):
            continue
        if path.is_symlink():
            errors.append("Symlink requires manual review: " + relative.as_posix())
            continue
        if not path.is_file():
            continue
        count += 1
        if relative.parts[:2] == ("assets", "present-tc"):
            if path.suffix not in {".md", ".tsv", ".json", ".csv", ".jpg", ".css", ".pptx", ".woff2"}:
                errors.append("Unexpected bundle artifact: " + relative.as_posix())
            if path.stat().st_size >= 100 * 1024 * 1024:
                errors.append("Bundle file exceeds 100 MiB: " + relative.as_posix())
            continue
        if path.name not in (".gitignore", "LICENSE") and path.suffix not in ALLOWED_SUFFIXES:
            errors.append("Unexpected public artifact: " + relative.as_posix())
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeError, OSError):
            errors.append("Expected readable UTF-8 text: " + relative.as_posix())
            continue
        if path.suffix == ".md":
            for link in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
                if re.match(r"^[a-z]+:", link, flags=re.I) or link.startswith("#"):
                    continue
                target = (path.parent / link.split("#", 1)[0]).resolve()
                if not target.is_relative_to(root) or not target.exists():
                    errors.append("Broken or out-of-repo link in " + relative.as_posix() + ": " + link)
        runtime = relative.parts[0] in ("references", "agents", "examples") or path.name == "SKILL.md"
        if runtime:
            if re.search(r"jun-(?:report|ppt|template|interview)|[a-z0-9.-]+\.woa\.com|/Users/[^/\s]+/|/home/[^/\s]+/|[A-Z]:\\\\Users\\\\", text, flags=re.I):
                errors.append("Private dependency/path requires review: " + relative.as_posix())
            if "TODO" in text or "[待填写]" in text:
                errors.append("Unfinished runtime instruction: " + relative.as_posix())
        if re.search(r"gh[pousr]_[A-Za-z0-9]{30,}", text):
            errors.append("Possible credential detected (value withheld): " + relative.as_posix())
    errors.extend(validate_bundle(root))
    try:
        errors.extend(check_palette(root))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append("Palette validation failed: " + str(exc))
    if release and (not (root / "LICENSE").is_file() or not (root / "LICENSE").read_text(encoding="utf-8").strip()):
        errors.append("Release blocked: choose an approved license and add complete LICENSE text")
    return errors, count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", action="store_true", help="Also require LICENSE; does not verify rights/approval")
    args = parser.parse_args()
    errors, count = validate(ROOT, args.release)
    for error in errors:
        print("ERROR: " + error)
    if errors:
        return 1
    print("PASS: structure, links and full template bundle ({0} files)".format(count))
    print("Manual rights, branding, data review and end-to-end artifact QA are still required.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
