#!/usr/bin/env python3
"""Parse an OKX X Layer verified contract API response."""
import json
import os
import sys


def parse(response_path: str, outdir: str = ".sources") -> dict:
    """Parse OKX API response, extract sources, return metadata."""
    with open(response_path) as f:
        data = json.load(f)

    results = data.get("data") or []
    r = results[0] if results else {}
    src = r.get("sourceCode", "")
    meta = {
        "contractName": r.get("contractName", ""),
        "proxy": r.get("proxy", "0") == "1",
        "implementation": r.get("implementation", ""),
        "verified": bool(src),
    }

    print(f"ContractName: {meta['contractName']}")
    print(f"Proxy: {meta['proxy']}")
    print(f"Implementation: {meta['implementation']}")
    print(f"Verified: {meta['verified']}")

    if not src:
        return meta

    os.makedirs(outdir, exist_ok=True)

    if src.startswith("{{"):
        inner = json.loads(src[1:-1])
        for name, content in inner["sources"].items():
            safe_name = os.path.basename(name.replace("/", "_").replace("\\", "_"))
            if not safe_name or safe_name.startswith("."):
                safe_name = f"source_{hash(name) & 0xFFFFFFFF:08x}.sol"
            path = os.path.join(outdir, safe_name)
            if not os.path.realpath(path).startswith(os.path.realpath(outdir)):
                print(f"  Skipping suspicious path: {name}")
                continue
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
