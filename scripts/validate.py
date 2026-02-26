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

    errors = []
    for filepath in files:
        with open(filepath) as f:
            hook = json.load(f)
        try:
            jsonschema.validate(hook, schema)
            print(f"  OK: {filepath}")
        except jsonschema.ValidationError as e:
            errors.append(f"{filepath}: {e.message}")
            print(f"FAIL: {filepath}: {e.message}")

    if errors:
        print(f"\n{len(errors)} validation error(s)")
        sys.exit(1)
    else:
        print(f"\nAll {len(files)} file(s) valid.")


if __name__ == "__main__":
    main()
