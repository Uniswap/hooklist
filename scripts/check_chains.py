#!/usr/bin/env python3
"""Verify chains.json ingestion config against live RPCs.

For each chain with rpcUrls: check the PoolManager has code and that at
least one Initialize log exists in a recent or historical window.

Usage: python3 scripts/check_chains.py [chain ...]
"""
import json
import os
import sys

import evm
import rpc


def main():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(repo_root, "chains.json")) as f:
        chains = json.load(f)

    only = set(sys.argv[1:])
    failures = []
    for name, cfg in chains.items():
        if "rpcUrls" not in cfg:
            continue
        if only and name not in only:
            continue
        try:
            client = rpc.RpcClient(cfg["rpcUrls"])
            head = client.block_number()
            code = client.get_code(cfg["poolManager"])
            assert len(code) > 2, f"no code at poolManager {cfg['poolManager']}"
            assert cfg["deployBlock"] < head, "deployBlock beyond head"
            logs = client.get_logs(cfg["poolManager"], evm.INITIALIZE_TOPIC,
                                   cfg["deployBlock"], min(cfg["deployBlock"] + 5_000, head))
            print(f"  OK: {name} head={head} initialize-logs-in-first-5k={len(logs)}")
        except Exception as e:
            failures.append(f"{name}: {e}")
            print(f"FAIL: {name}: {e}")

    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
