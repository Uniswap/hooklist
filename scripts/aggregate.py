#!/usr/bin/env python3
"""Aggregate individual hook JSON files into hooklist.json."""
import json
import glob
import os
import sys

import jsonschema


def aggregate_hooks(hooks_dir: str, schema: dict | None = None) -> list[dict]:
    """Read all hook JSON files, optionally validate, and return sorted list."""
    hooks = []
    errors = []
    pattern = os.path.join(hooks_dir, "**", "*.json")
    for filepath in glob.glob(pattern, recursive=True):
        with open(filepath) as f:
            hook = json.load(f)
        if schema:
            try:
                jsonschema.validate(hook, schema)
            except jsonschema.ValidationError as e:
                errors.append(f"{filepath}: {e.message}")
        hooks.append(hook)

    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        raise ValueError(f"Schema validation failed with {len(errors)} error(s)")

    hooks.sort(key=lambda h: (h["hook"]["chain"], h["hook"]["address"].lower()))
    return hooks


def filter_vanilla_swap(hooks: list[dict]) -> list[dict]:
    """Return hooks whose vanillaSwap property is true."""
    return [h for h in hooks if h["properties"]["vanillaSwap"]]


def main():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hooks_dir = os.path.join(repo_root, "hooks")
    schema_path = os.path.join(repo_root, "schema.json")
    hooklist_path = os.path.join(repo_root, "hooklist.json")
    vanilla_path = os.path.join(repo_root, "hooklist-vanilla-swap.json")

    with open(schema_path) as f:
        schema = json.load(f)

    hooks = aggregate_hooks(hooks_dir, schema)

    with open(hooklist_path, "w") as f:
        json.dump(hooks, f, indent=2)
        f.write("\n")

    vanilla = filter_vanilla_swap(hooks)
    with open(vanilla_path, "w") as f:
        json.dump(vanilla, f, indent=2)
        f.write("\n")

    print(f"Aggregated {len(hooks)} hooks into hooklist.json")
    print(f"Filtered {len(vanilla)} vanilla-swap hooks into hooklist-vanilla-swap.json")


if __name__ == "__main__":
    main()
