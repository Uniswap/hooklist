#!/usr/bin/env python3
"""Validate hook JSON files against schema.json.

Usage:
  python3 scripts/validate.py                     # validate all hooks
  python3 scripts/validate.py hooks/base/0x...json # validate specific files
"""
import json
import glob
import os
import sys

import jsonschema


def check_filename_casing(files):
    """Enforce lowercase hook filenames and reject case-collisions.

    Hook files must be named with the lowercased address. Two files in one
    chain directory whose names differ only by letter case collide on a
    case-insensitive filesystem (default macOS/Windows) and produce a
    duplicate entry in hooklist.json, so both are rejected here. Runs against
    the files under review, so it gates every PR at review/approval time.
    """
    errors = []
    for filepath in files:
        base = os.path.basename(filepath)
        if base != base.lower():
            errors.append(
                f"{filepath}: filename must be lowercase (got '{base}'); "
                f"name the file with the lowercased address"
            )
        directory = os.path.dirname(filepath)
        try:
            siblings = os.listdir(directory)
        except OSError:
            siblings = []
        twins = sorted(s for s in siblings if s.lower() == base.lower() and s != base)
        if twins:
            errors.append(
                f"{filepath}: case-collision with existing file(s) {twins} in {directory}; "
                f"a hook address may appear only once per chain"
            )
    return errors


def main():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    schema_path = os.path.join(repo_root, "schema.json")

    with open(schema_path) as f:
        schema = json.load(f)

    # Validate specific files or all hooks
    if len(sys.argv) > 1:
        files = sys.argv[1:]
    else:
        files = glob.glob(os.path.join(repo_root, "hooks", "**", "*.json"), recursive=True)

    if not files:
        print("No hook files to validate.")
        return

    errors = list(check_filename_casing(files))
    for e in errors:
        print(f"FAIL: {e}")
    for filepath in files:
        with open(filepath) as f:
            hook = json.load(f)
        try:
            jsonschema.validate(hook, schema)
            print(f"  OK: {filepath}")
        except jsonschema.ValidationError as e:
            path = ".".join(str(p) for p in e.path) or "<root>"
            errors.append(f"{filepath}: {path}: {e.message}")
            print(f"FAIL: {filepath}")
            print(f"  field: {path}")
            print(f"  value: {e.instance!r}")
            print(f"  error: {e.message}")

    if errors:
        print(f"\n{len(errors)} validation error(s)")
        sys.exit(1)
    else:
        print(f"\nAll {len(files)} file(s) valid.")


if __name__ == "__main__":
    main()
