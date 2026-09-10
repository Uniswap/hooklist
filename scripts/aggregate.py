#!/usr/bin/env python3
"""Aggregate individual hook JSON files into hooklist.json."""
import json
import glob
import os
import sys

import validate
import verify_flags


def load_releases(repo_root: str) -> dict[str, dict]:
    releases = {}
    for path in glob.glob(os.path.join(repo_root, "releases", "*", "*.json")):
        with open(path) as f:
            r = json.load(f)
        releases[f"{r['project']}/{r['id']}"] = r
    return releases


MAX_DESCRIPTION_LEN = 500


def _compose_description(release_description: str, fragment: str,
                          max_len: int = MAX_DESCRIPTION_LEN) -> str:
    """Published thin-instance description: release text plus per-instance fragment.

    - Missing or empty-string fragment: release_description alone.
    - Non-empty fragment: f"{release_description} {fragment}", trimmed to
      max_len — the RELEASE part is truncated at a word boundary with "…" if
      needed; the fragment is NEVER truncated.
    """
    fragment = (fragment or "").strip()
    if not fragment:
        return release_description
    combined = f"{release_description} {fragment}"
    if len(combined) <= max_len:
        return combined
    ellipsis = "…"
    budget = max(max_len - len(fragment) - len(ellipsis) - 1, 0)  # -1 for the space before fragment
    truncated = release_description[:budget].rstrip()
    if " " in truncated:
        truncated = truncated.rsplit(" ", 1)[0]
    return f"{truncated}{ellipsis} {fragment}"


def resolve_entry(hook_file: dict, releases: dict, label: str = "<data>") -> dict:
    hook = hook_file["hook"]
    ref = hook.get("release")
    if ref is None:
        return hook_file
    if "properties" in hook_file:
        # full + pointer: pass through, stripping the pointer from v0 output
        out_hook = {k: v for k, v in hook.items() if k != "release"}
        return {"hook": out_hook, "flags": hook_file["flags"],
                "properties": hook_file["properties"]}
    release = releases.get(ref)
    if release is None:
        raise ValueError(f"{label}: unresolved release ref {ref}")
    source = release.get("source", {})
    out_hook = {
        "address": hook["address"],
        "chain": hook["chain"],
        "chainId": hook["chainId"],
        "name": release["name"],
        "description": _compose_description(release["description"], hook.get("description", "")),
        "deployer": hook.get("deployer", ""),
        "verifiedSource": source.get("verified", False),
        "auditUrl": source.get("auditUrl", ""),
    }
    return {"hook": out_hook,
            "flags": verify_flags.decode_flags(hook["address"]),
            "properties": release["properties"]}


def aggregate_hooks(hooks_dir: str, schema: dict | None = None, releases: dict | None = None,
                     repo_root: str | None = None) -> list[dict]:
    """Read all hook JSON files, optionally validate, and return sorted list."""
    if repo_root is None:
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hooks = []
    errors = []
    pattern = os.path.join(hooks_dir, "**", "*.json")
    for filepath in glob.glob(pattern, recursive=True):
        with open(filepath) as f:
            hook = json.load(f)
        if schema:
            errs = validate.check_hook_data(hook, repo_root, label=filepath)
            if errs:
                errors.extend(errs)
        hook = resolve_entry(hook, releases or {}, label=filepath)
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

    releases = load_releases(repo_root)
    hooks = aggregate_hooks(hooks_dir, schema, releases, repo_root=repo_root)

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
