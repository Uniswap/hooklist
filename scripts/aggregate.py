#!/usr/bin/env python3
"""Aggregate individual hook JSON files into hooklist.json."""
import json
import glob
import os


def aggregate_hooks(hooks_dir: str) -> list[dict]:
    """Read all hook JSON files and return sorted list."""
    hooks = []
    pattern = os.path.join(hooks_dir, "**", "*.json")
    for filepath in glob.glob(pattern, recursive=True):
        with open(filepath) as f:
            hooks.append(json.load(f))
    hooks.sort(key=lambda h: (h["hook"]["chain"], h["hook"]["address"].lower()))
    return hooks


def main():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hooks_dir = os.path.join(repo_root, "hooks")
    hooklist_path = os.path.join(repo_root, "hooklist.json")

    hooks = aggregate_hooks(hooks_dir)

    with open(hooklist_path, "w") as f:
        json.dump(hooks, f, indent=2)
        f.write("\n")

    print(f"Aggregated {len(hooks)} hooks into hooklist.json")


if __name__ == "__main__":
    main()
