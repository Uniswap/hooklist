#!/usr/bin/env python3
"""Validate hook and family JSON files against their schemas.

Usage:
  python3 scripts/validate.py                       # validate all hooks + families
  python3 scripts/validate.py <file> [<file> ...]   # validate specific files
"""
import json
import glob
import os
import sys

import jsonschema

_SCHEMAS = {}


def _schema_for(filepath: str, repo_root: str) -> dict:
    name = "family.schema.json" if "families/" in filepath.replace(os.sep, "/") else "schema.json"
    if name not in _SCHEMAS:
        with open(os.path.join(repo_root, name)) as f:
            _SCHEMAS[name] = json.load(f)
    return _SCHEMAS[name]


def validate_file(filepath: str, repo_root: str) -> list[str]:
    """Return a list of error strings (empty if valid)."""
    schema = _schema_for(filepath, repo_root)
    with open(filepath) as f:
        data = json.load(f)
    try:
        jsonschema.validate(data, schema)
        return []
    except jsonschema.ValidationError as e:
        path = ".".join(str(p) for p in e.path) or "<root>"
        return [f"{filepath}: {path}: {e.message}"]


def main():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    if len(sys.argv) > 1:
        files = sys.argv[1:]
    else:
        files = glob.glob(os.path.join(repo_root, "hooks", "**", "*.json"), recursive=True)
        files += glob.glob(os.path.join(repo_root, "families", "*.json"))

    if not files:
        print("No files to validate.")
        return

    errors = []
    for filepath in files:
        errs = validate_file(filepath, repo_root)
        if errs:
            errors.extend(errs)
            print(f"FAIL: {filepath}")
            for e in errs:
                print(f"  {e}")
        else:
            print(f"  OK: {filepath}")

    if errors:
        print(f"\n{len(errors)} validation error(s)")
        sys.exit(1)
    else:
        print(f"\nAll {len(files)} file(s) valid.")


if __name__ == "__main__":
    main()
