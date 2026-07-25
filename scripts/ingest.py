#!/usr/bin/env python3
"""Ingest new hook instances across all configured chains.

Usage: python3 scripts/ingest.py [--repo-root PATH] [--chains a,b,c]
Writes: index/<chain>.jsonl, index/cursors.json

Analysis candidates are NOT emitted here: select_analyses.py derives them
from the index itself (retry-by-absence), so this script's only job is to
keep the mechanical ledger current.
"""
import argparse
import json
import os
import sys

import index_ledger
import rpc
import scan


# Persist a chain's cursor advance only when the run appended new lines, or
# when the cursor moved at least this many blocks past the last persisted
# value. One getLogs chunk window (scan.py's default chunk_size) is the
# defensible floor: losing a sub-threshold advance means the next run
# re-fetches at most one chunk it already saw — and the known-address dedup
# makes that rescan a no-op — whereas persisting every tiny advance would
# turn each 30-minute cron tick into a noise commit plus a full artifact
# rebuild and Pages deploy (regenerate.yml triggers on index/**).
CURSOR_PERSIST_MIN_ADVANCE = 5000


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

    total_lines = 0
    cursors_changed = False
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
            total_lines += len(result.new_lines)
        # New lines force persistence (pending-state changes that produced
        # them must not replay next run); otherwise only a threshold-sized
        # cursor advance is worth a commit. A dropped sub-threshold advance
        # is safe: the next run rescans a small window and the known-address
        # dedup absorbs any re-seen instances.
        if result.new_lines or result.cursor - state["block"] >= CURSOR_PERSIST_MIN_ADVANCE:
            cursors[name] = {"block": result.cursor, "pending": result.pending}
            cursors_changed = True

    if cursors_changed:
        os.makedirs(os.path.join(repo_root, "index"), exist_ok=True)
        with open(cursors_path, "w") as f:
            json.dump(cursors, f, indent=2, sort_keys=True)
            f.write("\n")

    print(f"Scanned {attempted - failed}/{attempted} chains; "
          f"{total_lines} new index lines")
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
