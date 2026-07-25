#!/usr/bin/env python3
"""Build published artifacts (dist/) from index + families + hooks stores.

Usage: python3 scripts/build_artifacts.py [--repo-root PATH]
"""
import argparse
import datetime
import glob
import json
import os

import index_ledger
from verify_flags import FLAG_BITS, decode_flags

# Canonical flag order comes from verify_flags.FLAG_BITS (single source).
FLAG_NAMES = list(FLAG_BITS)


def _load_families(repo_root: str) -> dict[str, dict]:
    fams = {}
    for path in glob.glob(os.path.join(repo_root, "families", "*.json")):
        with open(path) as f:
            fam = json.load(f)
        fams[fam["family"]["id"]] = fam
    return fams


def _hook_file(repo_root: str, chain: str, address: str) -> dict | None:
    for candidate in glob.glob(os.path.join(repo_root, "hooks", chain, "*.json")):
        if os.path.basename(candidate).lower() == f"{address}.json":
            with open(candidate) as f:
                return json.load(f)
    return None


def _divergence(flags: dict, implemented: dict) -> list[str]:
    out = []
    for name in FLAG_NAMES:
        if flags[name] and not implemented[name]:
            out.append(f"unimplemented:{name}")
        elif implemented[name] and not flags[name]:
            out.append(f"dormant:{name}")
    return out


def build(repo_root: str, built_at: str | None = None):
    built_at = built_at or datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    families = _load_families(repo_root)
    cursors = {}
    cursors_path = os.path.join(repo_root, "index", "cursors.json")
    if os.path.exists(cursors_path):
        with open(cursors_path) as f:
            cursors = json.load(f)

    counts: dict[str, dict[str, int]] = {}
    os.makedirs(os.path.join(repo_root, "dist", "lookup"), exist_ok=True)

    for index_path in sorted(glob.glob(os.path.join(repo_root, "index", "*.jsonl"))):
        chain = os.path.basename(index_path)[:-6]
        latest = index_ledger.latest_by_address(index_ledger.read_lines(index_path))
        hooks_out = {}
        for address, line in sorted(latest.items()):
            fam = families.get(line["family"])
            fam_meta = fam["family"] if fam else None
            flags = decode_flags(address)
            implemented = fam.get("implementedPermissions") if fam else None
            kind = fam_meta["kind"] if fam_meta else None
            hook_file = _hook_file(repo_root, chain, address)
            if kind == "delegating" or (hook_file and hook_file["properties"]["upgradeable"]):
                upgradeable = True
            elif kind == "self-contained":
                upgradeable = False
            else:
                upgradeable = None
            hooks_out[address] = {
                "family": line["family"],
                "block": line["block"],
                "name": fam_meta["name"] if fam_meta else None,
                "kind": kind,
                "sourceStatus": fam_meta["sourceStatus"] if fam_meta else None,
                "flags": flags,
                "properties": fam.get("properties") if fam else None,
                "upgradeable": upgradeable,
                "flagDivergence": _divergence(flags, implemented) if implemented else [],
            }
            counts.setdefault(line["family"], {})
            counts[line["family"]][chain] = counts[line["family"]].get(chain, 0) + 1
        out = {
            "builtAt": built_at,
            "scannedToBlock": cursors.get(chain, {}).get("block"),
            "hooks": hooks_out,
        }
        with open(os.path.join(repo_root, "dist", "lookup", f"{chain}.json"), "w") as f:
            json.dump(out, f, indent=2)
            f.write("\n")

    fam_list = []
    for fam_id in sorted(families):
        entry = dict(families[fam_id])
        entry["instanceCounts"] = counts.get(fam_id, {})
        fam_list.append(entry)
    with open(os.path.join(repo_root, "dist", "families.json"), "w") as f:
        json.dump({"builtAt": built_at, "families": fam_list}, f, indent=2)
        f.write("\n")
    print(f"Built dist/: {len(fam_list)} families, "
          f"{len(glob.glob(os.path.join(repo_root, 'dist', 'lookup', '*.json')))} lookup files")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))))
    args = ap.parse_args()
    build(args.repo_root)


if __name__ == "__main__":
    main()
