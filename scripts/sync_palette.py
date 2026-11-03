#!/usr/bin/env python3
"""Generate default CSS colors or check skill palette consistency (not rendered output)."""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def css_name(role):
    return re.sub(r"[A-Z]", lambda m: "-" + m[0].lower(), role)


def css_text(colors):
    lines = ["/* Generated from report-tokens.json; override once on the report root. */", ":root{"]
    lines += [f"  --tc-{css_name(role)}:{value};" for role, value in colors.items()]
    return "\n".join(lines + ["}", ""])


def check(root=ROOT):
    root = Path(root)
    tokens = json.loads((root / "assets/report-tokens.json").read_text())
    colors = {**tokens["colors"], **tokens.get("functionalColors", {})}
    errors = []
    if any(not re.fullmatch(r"#[0-9A-F]{6}", value) for value in colors.values()):
        errors.append("Default colors must use uppercase six-digit hex")
    if any(role not in colors for role in tokens["colorPolicy"]["chartSeries"]):
        errors.append("Unknown chart series color role")
    generated = root / "assets/html/palette.css"
    if not generated.is_file() or generated.read_text() != css_text(colors):
        errors.append("palette.css differs from tokens; run scripts/sync_palette.py")
    variables = {css_name(k): v for k, v in colors.items()}
    allowed = set(colors.values())
    for path in sorted((root / "assets/html").glob("*")):
        if path.suffix not in (".css", ".js"):
            continue
        text = path.read_text()
        for role in re.findall(r"var\(--tc-([\w-]+)", text):
            if role not in variables:
                errors.append(f"{path.name}: unknown color variable {role}")
        for role, value in re.findall(r"var\(--tc-([\w-]+)\s*,\s*(#[0-9a-fA-F]+)\)", text):
            if variables.get(role) != value.upper():
                errors.append(f"{path.name}: fallback differs for {role}")
        for value in re.findall(r"#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{4}|[0-9a-fA-F]{3})\b", text):
            rgb = value[1:]
            rgb = "".join(c * 2 for c in rgb[:3]) if len(rgb) in (3, 4) else rgb[:6]
            if "#" + rgb.upper() not in allowed:
                errors.append(f"{path.name}: color outside defaults {value}")
    visual = (root / "references/visual-system.md").read_text()
    for role, value in re.findall(r"\| `([A-Za-z]+)` \| `(#[0-9A-F]{6})` \|", visual):
        if colors.get(role) != value:
            errors.append(f"visual-system.md: color differs for {role}")
    metadata = (root / "agents/openai.yaml").read_text()
    brand = re.search(r'brand_color:\s*"(#[0-9a-fA-F]{6})"', metadata)
    if not brand or brand[1].upper() != colors["primary"]:
        errors.append("Skill brand color differs from primary")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if not args.check:
        tokens = json.loads((ROOT / "assets/report-tokens.json").read_text())
        colors = {**tokens["colors"], **tokens.get("functionalColors", {})}
        (ROOT / "assets/html/palette.css").write_text(css_text(colors))
    errors = check()
    for error in errors:
        print("ERROR: " + error)
    if not errors:
        print("PASS: skill default palette is consistent; rendered reports still need review")
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
