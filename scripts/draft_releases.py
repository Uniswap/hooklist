#!/usr/bin/env python3
"""Draft release files for duplicated-name hook families (backfill assist).

Usage:
  python3 scripts/draft_releases.py                    # report families
  python3 scripts/draft_releases.py --family "Spot"    # report one family
  python3 scripts/draft_releases.py --write            # apply READY drafts
"""
import argparse
import collections
import glob
import json
import os
import re


def slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9.]+", "-", text.lower()).strip("-")
    return re.sub(r"-+", "-", s)


def group_families(hooks) -> dict:
    groups = collections.defaultdict(list)
    for path, data in hooks:
        groups[data["hook"]["name"]].append((path, data))
    return {name: members for name, members in groups.items() if len(members) >= 2}


def draft_family(name: str, members) -> dict:
    props = [json.dumps(d["properties"], sort_keys=True) for _, d in members]
    if len(set(props)) > 1:
        diffs = {}
        base = members[0][1]["properties"]
        for path, d in members[1:]:
            for k, v in d["properties"].items():
                if base.get(k) != v:
                    diffs.setdefault(k, []).append(f"{path}: {base.get(k)} vs {v}")
        return {"status": "NEEDS-RECONCILIATION", "name": name, "diffs": diffs,
                "members": [p for p, _ in members]}
    richest = max(members, key=lambda m: len(m[1]["hook"].get("description", "")))[1]
    sid = slug(name)
    project = sid.split("-")[0]
    release = {
        "project": project,
        "id": sid,
        "version": "1",
        "name": name,
        "description": richest["hook"].get("description", ""),
        "source": {"verified": all(d["hook"].get("verifiedSource", False)
                                   for _, d in members)},
        "properties": richest["properties"],
        "warnings": [],
        "lifecycle": {"status": "active", "supersedes": None},
    }
    # NOTE: source.auditUrl is intentionally never auto-promoted from a
    # single member hook file here. A member's auditUrl is submitter-supplied
    # per-deployment data — promoting it to release-level claims the audit
    # covers every instance of the release, which is not something a single
    # member's field can establish (Important I5). If every member agrees on
    # the same auditUrl, that's a signal worth a human adding it deliberately.
    return {"status": "READY", "name": name, "release": release,
            "members": [p for p, _ in members]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--family", default=None)
    args = ap.parse_args()
    root = args.repo_root

    hooks = []
    for path in sorted(glob.glob(os.path.join(root, "hooks", "**", "*.json"),
                                 recursive=True)):
        with open(path) as f:
            data = json.load(f)
        if "release" in data.get("hook", {}):
            continue  # already backfilled
        hooks.append((path, data))

    for name, members in sorted(group_families(hooks).items()):
        if args.family and name != args.family:
            continue
        result = draft_family(name, members)
        print(f"[{result['status']}] {name} ({len(members)} members)")
        if result["status"] == "NEEDS-RECONCILIATION":
            for field, lines in result["diffs"].items():
                for line in lines:
                    print(f"    {field}: {line}")
            continue
        if args.write:
            rel = result["release"]
            rel_path = os.path.join(root, "releases", rel["project"],
                                    rel["id"] + ".json")
            os.makedirs(os.path.dirname(rel_path), exist_ok=True)
            with open(rel_path, "w") as f:
                json.dump(rel, f, indent=2)
                f.write("\n")
            ref = f"{rel['project']}/{rel['id']}"
            for path, data in members:
                data["hook"]["release"] = ref
                with open(path, "w") as f:
                    json.dump(data, f, indent=2)
                    f.write("\n")
            print(f"    wrote {rel_path} + {len(members)} pointers")


if __name__ == "__main__":
    main()
