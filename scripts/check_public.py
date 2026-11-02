#!/usr/bin/env python3
"""Check the complete Git candidate tree, including the presentation bundle."""
import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from validate_repo import ROOT, validate

PUBLIC_ROOTS = {".github", "agents", "assets", "docs", "examples", "references", "scripts", "tests"}
PUBLIC_FILES = {".gitignore", "README.md", "SKILL.md", "requirements.txt", "LICENSE"}


def candidates(root):
    root = Path(root).resolve()
    top = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "--show-toplevel"], text=True
    ).strip()
    if Path(top).resolve() != root:
        raise ValueError("Run against the present-tc repository root, not its parent.")
    names = subprocess.check_output([
        "git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard", "-z"
    ]).decode("utf-8").split("\0")
    return sorted({name for name in names if name})


def check_public(root, require_license=False):
    root = Path(root).resolve()
    errors = []
    names = candidates(root)
    with tempfile.TemporaryDirectory(prefix="present-tc-public-") as temp:
        export = Path(temp) / "present-tc"
        export.mkdir()
        for name in names:
            relative = Path(name)
            source = root / relative
            # Include tracked ignored files in review: .gitignore cannot hide them.
            allowed = name in PUBLIC_FILES or relative.parts[0] in PUBLIC_ROOTS
            if relative.parts[0] == "assets":
                allowed = name == "assets/report-tokens.json" or relative.parts[:2] in (("assets", "html"), ("assets", "present-tc"))
            if relative.is_absolute() or ".." in relative.parts or not allowed:
                errors.append("Unexpected public file: " + name)
                continue
            if source.is_symlink() or not source.resolve().is_relative_to(root):
                errors.append("Symlink or out-of-repository file: " + name)
                continue
            if not source.is_file():
                errors.append("Tracked file missing; commit its deletion or restore it: " + name)
                continue
            target = export / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        structural, count = validate(export, release=require_license)
        errors.extend(structural)
    return errors, count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-license", action="store_true", help="Also require a non-empty LICENSE for an open-source release")
    args = parser.parse_args()
    try:
        errors, count = check_public(ROOT, args.require_license)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 1
    for error in errors:
        print("ERROR: " + error)
    if errors:
        return 1
    print("PASS: isolated public tree ({0} files); full template bundle verified".format(count))
    return 0


if __name__ == "__main__":
    sys.exit(main())
