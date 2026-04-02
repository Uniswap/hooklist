#!/usr/bin/env python3
"""Verify chain consistency across chains.json, schema.json, and the issue template.

Usage: python3 scripts/sync_chains.py [--fix]

Without --fix, reports mismatches and exits non-zero if any.
With --fix, updates schema.json and submit-hook.yml to match chains.json.
"""
import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_chains():
    with open(os.path.join(REPO_ROOT, "chains.json")) as f:
        return set(json.load(f).keys())


def load_schema_chains():
    with open(os.path.join(REPO_ROOT, "schema.json")) as f:
        schema = json.load(f)
    return set(schema["properties"]["hook"]["properties"]["chain"].get("enum", []))


def load_template_chains():
    path = os.path.join(REPO_ROOT, ".github", "ISSUE_TEMPLATE", "submit-hook.yml")
    with open(path) as f:
        content = f.read()
    in_options = False
    chains = []
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped == "options:":
            in_options = True
            continue
        if in_options:
            if stripped.startswith("- "):
                chains.append(stripped[2:].strip())
            elif stripped and not stripped.startswith("#"):
                break
    return set(chains)


def main():
    fix = "--fix" in sys.argv
    chains = load_chains()
    schema_chains = load_schema_chains()
    template_chains = load_template_chains()

    errors = []

    if schema_chains != chains:
        extra = schema_chains - chains
        missing = chains - schema_chains
        if extra:
            errors.append(f"schema.json has extra chains: {sorted(extra)}")
        if missing:
            errors.append(f"schema.json is missing chains: {sorted(missing)}")

    if template_chains != chains:
        extra = template_chains - chains
        missing = chains - template_chains
        if extra:
            errors.append(f"submit-hook.yml has extra chains: {sorted(extra)}")
        if missing:
            errors.append(f"submit-hook.yml is missing chains: {sorted(missing)}")

    if not errors:
        print("All chain lists are in sync.")
        return

    for e in errors:
        print(f"MISMATCH: {e}")

    if not fix:
        print("\nRun with --fix to update schema.json and submit-hook.yml to match chains.json.")
        sys.exit(1)

    # Fix schema.json
    schema_path = os.path.join(REPO_ROOT, "schema.json")
    with open(schema_path) as f:
        schema = json.load(f)
    schema["properties"]["hook"]["properties"]["chain"]["enum"] = sorted(chains)
    with open(schema_path, "w") as f:
        json.dump(schema, f, indent=2)
        f.write("\n")
    print("Updated schema.json chain enum.")

    # Fix submit-hook.yml
    template_path = os.path.join(REPO_ROOT, ".github", "ISSUE_TEMPLATE", "submit-hook.yml")
    with open(template_path) as f:
        content = f.read()
    options_str = "      options:\n" + "".join(f"        - {c}\n" for c in sorted(chains))
    content = re.sub(
        r"      options:\n(?:        - .+\n)+",
        options_str,
        content,
    )
    with open(template_path, "w") as f:
        f.write(content)
    print("Updated submit-hook.yml chain options.")


if __name__ == "__main__":
    main()
