#!/usr/bin/env python3
"""Compute hook permission flags from an address bitmask.

Usage: python3 scripts/compute_flags.py <address> [--output <path>]

Prints flags as JSON to stdout. With --output, also writes to a file.
"""
import json
import re
import sys

from verify_flags import decode_flags


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <address> [--output <path>]", file=sys.stderr)
        sys.exit(1)

    address = sys.argv[1]
    if not re.match(r"^0x[a-fA-F0-9]{40}$", address):
        print(f"Invalid address: {address}", file=sys.stderr)
        sys.exit(1)

    flags = decode_flags(address)
    output = json.dumps(flags, indent=2)
    print(output)

    if "--output" in sys.argv:
        outpath = sys.argv[sys.argv.index("--output") + 1]
        with open(outpath, "w") as f:
            f.write(output)
            f.write("\n")


if __name__ == "__main__":
    main()
