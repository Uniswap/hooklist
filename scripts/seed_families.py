#!/usr/bin/env python3
"""One-time migration: derive families/ and index/ from existing hooks/ files.

Usage: python3 scripts/seed_families.py [--chains celo,base] [--repo-root PATH]
Requires RPC access (fetches each hook's codehash). Idempotent: skips
addresses already in the index and families that already have files.

Known-address tracking: rather than re-reading each chain's index file from
disk on every hook (which the original sketch did, and which is O(n^2) but
still correct), we load each chain's `latest_by_address` map once and update
it in memory as we append new lines. This also transparently dedupes the
repo's known macOS case-collision hook paths (e.g. `0xAbC....json` and
`0xabc....json` both existing under `hooks/<chain>/`): whichever path is
visited first for a given lowercased address wins, and the second is skipped
via the in-memory `known` map without needing a second disk read.
"""
import argparse
import datetime
import glob
import json
import os
import sys
import time

import assemble_family
import evm
import index_ledger
import rpc
from verify_flags import FLAG_BITS

# Canonical flag order comes from verify_flags.FLAG_BITS (single source).
FLAG_NAMES = list(FLAG_BITS)

RPC_SLEEP_SECONDS = 0.1


def family_from_hooks(family_id: str, members: list[tuple]) -> dict:
    """members: [(chain, address, hook_json)] sharing one codehash."""
    chain, address, best = max(members, key=lambda m: len(m[2]["hook"].get("description", "")))
    h = best["hook"]
    if not h["verifiedSource"]:
        return assemble_family.build_stub(family_id, contract_name=h["name"])
    props = dict(best["properties"])
    upgradeable = props.pop("upgradeable")
    return {
        "family": {
            "id": family_id,
            "kind": "delegating" if upgradeable else "self-contained",
            "name": h["name"],
            "description": h.get("description", ""),
            "sourceStatus": "verified",
            "repoUrl": "",
            "auditUrl": h.get("auditUrl", ""),
            "analyzedAt": datetime.date.today().isoformat(),
        },
        "implementedPermissions": dict(best["flags"]),
        "properties": props,
        "warnings": [
            f"seeded from per-address analysis of {address} on {chain}; "
            "implementedPermissions approximated from address flags"
        ],
    }


def _get_code_with_retry(client: rpc.RpcClient, address: str, chain: str) -> str | None:
    """Fetch code for one address, retrying once on RPC failure.

    Returns None (and logs to stderr) if both attempts fail, so a single
    down chain doesn't abort the whole run -- the caller just skips this
    address and the script can be re-run later (idempotent) once the RPC
    is healthy again.
    """
    for attempt in (1, 2):
        try:
            return client.get_code(address)
        except rpc.RpcError as e:
            print(f"  RPC error on {chain}/{address} (attempt {attempt}): {e}",
                  file=sys.stderr)
            if attempt == 1:
                time.sleep(RPC_SLEEP_SECONDS)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--chains", default="")
    args = ap.parse_args()
    root = args.repo_root
    only = set(args.chains.split(",")) - {""} or None

    with open(os.path.join(root, "chains.json")) as f:
        chains = json.load(f)

    by_family: dict[str, list[tuple]] = {}
    known_by_chain: dict[str, dict[str, dict]] = {}
    clients_by_chain: dict[str, rpc.RpcClient] = {}

    for path in sorted(glob.glob(os.path.join(root, "hooks", "*", "*.json"))):
        chain = os.path.basename(os.path.dirname(path))
        if only and chain not in only:
            continue
        cfg = chains.get(chain, {})
        if "rpcUrls" not in cfg:
            print(f"skip {path}: chain {chain} not RPC-configured", file=sys.stderr)
            continue
        with open(path) as f:
            hook = json.load(f)
        address = hook["hook"]["address"].lower()

        index_path = os.path.join(root, "index", f"{chain}.jsonl")
        if chain not in known_by_chain:
            known_by_chain[chain] = index_ledger.latest_by_address(
                index_ledger.read_lines(index_path))
        known = known_by_chain[chain]
        if address in known:
            continue

        if chain not in clients_by_chain:
            clients_by_chain[chain] = rpc.RpcClient(cfg["rpcUrls"])
        client = clients_by_chain[chain]

        code = _get_code_with_retry(client, address, chain)
        if code is None:
            print(f"  {chain}/{address} -> SKIPPED (RPC unavailable)", file=sys.stderr)
            time.sleep(RPC_SLEEP_SECONDS)
            continue

        family = evm.codehash(code) or "empty-code"
        line = index_ledger.make_line(address, family, 0)
        index_ledger.append_lines(index_path, [line])
        known[address] = line  # in-memory update; avoids re-reading the file
        if family != "empty-code":
            by_family.setdefault(family, []).append((chain, address, hook))
        print(f"  {chain}/{address} -> {family[:14]}…")
        time.sleep(RPC_SLEEP_SECONDS)

    for family_id, members in by_family.items():
        out_path = os.path.join(root, "families", f"{family_id}.json")
        if os.path.exists(out_path):
            continue
        fam = family_from_hooks(family_id, members)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(fam, f, indent=2)
            f.write("\n")

    print(f"Seeded {len(by_family)} families")


if __name__ == "__main__":
    main()
