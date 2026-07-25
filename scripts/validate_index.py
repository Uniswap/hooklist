#!/usr/bin/env python3
"""Re-derive new index lines from chain state (mechanical-lane backstop).

Usage:
  python3 scripts/validate_index.py <chain> <line-json> [<line-json> ...]
  python3 scripts/validate_index.py <chain> --file <path>

The --file form reads one line-JSON object per line (matching the JSONL
index format) and is the primary interface for CI: it avoids the shell
quoting hazards of passing each added line as a separate argv entry.
"""
import argparse
import json
import os
import re
import sys

import evm
import rpc

ADDRESS_RE = re.compile(r"^0x[a-f0-9]{40}$")


def validate_line(line: dict, client) -> list[str]:
    errors = []
    addr = line.get("address", "")
    if not ADDRESS_RE.match(addr):
        errors.append(f"{addr}: address must be lowercase 0x-hex")
        return errors

    block = line.get("block")
    if not isinstance(block, int) or isinstance(block, bool) or block < 0:
        errors.append(f"{addr}: block must be a non-negative integer")
    elif block > client.block_number():
        errors.append(f"{addr}: block {block} exceeds chain head")

    code = client.get_code(addr)
    actual = evm.codehash(code)
    claimed = line.get("family", "")
    if claimed == "empty-code":
        # tolerated even if code exists now (a correction line is the remedy,
        # not a reject of this line)
        return errors
    if actual is None:
        # code vanished (pre-Cancun selfdestruct) -- dated observation, tolerate
        return errors
    if claimed != actual:
        errors.append(f"{addr}: family {claimed} != current codehash {actual}")
    return errors


def _read_line_jsons(args: argparse.Namespace) -> list[str]:
    if args.file:
        with open(args.file) as f:
            return [ln.strip() for ln in f if ln.strip()]
    return args.lines


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("chain")
    parser.add_argument(
        "lines", nargs="*", help="line-json arguments (ignored if --file is given)"
    )
    parser.add_argument(
        "--file", help="path to a file with one line-JSON object per line"
    )
    args = parser.parse_args()

    line_jsons = _read_line_jsons(args)
    if not line_jsons:
        # Nothing to validate -- short-circuit before touching chains.json or
        # constructing an RpcClient (no chain lookup, no network).
        sys.exit(0)

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(repo_root, "chains.json")) as f:
        cfg = json.load(f)[args.chain]
    client = rpc.RpcClient(cfg["rpcUrls"])

    errors = []
    for lj in line_jsons:
        errors.extend(validate_line(json.loads(lj), client))
    for e in errors:
        print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
