#!/usr/bin/env python3
"""Ingest new hook instances across all configured chains.

Usage: python3 scripts/ingest.py [--repo-root PATH] [--chains a,b,c]
Writes: index/<chain>.jsonl, index/cursors.json, new_families.json
"""
import argparse
import json
import os
import sys

import index_ledger
import rpc
import scan


def _default_client(name: str, cfg: dict) -> rpc.RpcClient:
    return rpc.RpcClient(cfg["rpcUrls"])


def run(repo_root: str, client_factory=_default_client, only_chains=None) -> int:
    with open(os.path.join(repo_root, "chains.json")) as f:
        chains = json.load(f)

    cursors_path = os.path.join(repo_root, "index", "cursors.json")
    cursors = {}
    if os.path.exists(cursors_path):
        with open(cursors_path) as f:
            cursors = json.load(f)

    new_families = []
    attempted, failed = 0, 0
    for name, cfg in sorted(chains.items()):
        if "rpcUrls" not in cfg:
            continue
        if only_chains and name not in only_chains:
            continue
        attempted += 1
        index_path = os.path.join(repo_root, "index", f"{name}.jsonl")
        state = cursors.get(name, {"block": cfg["deployBlock"], "pending": {}})
        existing = index_ledger.read_lines(index_path)
        known = set(index_ledger.latest_by_address(existing))
        try:
            client = client_factory(name, cfg)
            result = scan.scan_chain(client, cfg, state["block"], state["pending"], known)
        except Exception as e:
            failed += 1
            print(f"ERROR: {name}: {e}", file=sys.stderr)
            continue
        if result.new_lines:
            index_ledger.append_lines(index_path, result.new_lines)
        # Map each new family to a representative line. If multiple new
        # instances share a family, the LAST one encountered in new_lines
        # wins; any instance address of that family is an acceptable
        # representative for new_families.json (dispatch just needs one
        # address to fetch source for), so this is intentional, not a bug.
        # Every family in result.new_families is guaranteed (by scan.py's
        # construction) to have at least one line with that family in
        # new_lines, so this dict comprehension can never leave a family
        # unmapped and the lookup below can never KeyError.
        by_family = {l["family"]: l for l in result.new_lines
                     if l["family"] in result.new_families}
        for fam in result.new_families:
            new_families.append({"family": fam, "chain": name,
                                 "address": by_family[fam]["address"]})
        cursors[name] = {"block": result.cursor, "pending": result.pending}

    os.makedirs(os.path.join(repo_root, "index"), exist_ok=True)
    with open(cursors_path, "w") as f:
        json.dump(cursors, f, indent=2, sort_keys=True)
        f.write("\n")
    with open(os.path.join(repo_root, "new_families.json"), "w") as f:
        json.dump(new_families, f, indent=2)
        f.write("\n")

    print(f"Scanned {attempted - failed}/{attempted} chains; "
          f"{len(new_families)} new families")
    return 2 if attempted and failed == attempted else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--chains", default="")
    args = ap.parse_args()
    only = set(args.chains.split(",")) - {""} or None
    sys.exit(run(args.repo_root, only_chains=only))


if __name__ == "__main__":
    main()
