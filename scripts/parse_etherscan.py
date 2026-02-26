#!/usr/bin/env python3
"""Parse an Etherscan getsourcecode API response.

Usage: python3 scripts/parse_etherscan.py response.json [--outdir .sources]

Prints contract metadata to stdout and writes individual source files
to the output directory for grep-based analysis.
"""
import json
import os
import sys


def parse(response_path: str, outdir: str = ".sources") -> dict:
    """Parse Etherscan API response, extract sources, return metadata."""
    with open(response_path) as f:
        data = json.load(f)

    r = data["result"][0]
    meta = {
        "contractName": r["ContractName"],
        "proxy": r.get("Proxy", "0") == "1",
        "implementation": r.get("Implementation", ""),
        "verified": bool(r["SourceCode"]),
    }

    print(f"ContractName: {meta['contractName']}")
    print(f"Proxy: {meta['proxy']}")
    print(f"Implementation: {meta['implementation']}")
    print(f"Verified: {meta['verified']}")

    src = r["SourceCode"]
    if not src:
        return meta

    os.makedirs(outdir, exist_ok=True)

    if src.startswith("{{"):
        # Multi-file source: strip outer braces, parse JSON
        inner = json.loads(src[1:-1])
        for name, content in inner["sources"].items():
            path = os.path.join(outdir, name.replace("/", "_"))
            with open(path, "w") as out:
                out.write(content["content"])
            print(f"  Source file: {name} ({len(content['content'])} chars)")
    else:
        path = os.path.join(outdir, "main.sol")
        with open(path, "w") as out:
            out.write(src)
        print(f"  Single file source ({len(src)} chars)")

    return meta


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <response.json> [--outdir <dir>]", file=sys.stderr)
        sys.exit(1)

    response_path = sys.argv[1]
    outdir = ".sources"
    if "--outdir" in sys.argv:
        outdir = sys.argv[sys.argv.index("--outdir") + 1]

    parse(response_path, outdir)


if __name__ == "__main__":
    main()
