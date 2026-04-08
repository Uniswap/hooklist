#!/usr/bin/env python3
"""Parse a Sourcify v2 API response.

Usage: python3 scripts/parse_sourcify.py response.json [--outdir .sources]

Prints contract metadata to stdout and writes individual source files
to the output directory for grep-based analysis.

Sourcify v2 response format (with ?fields=sources,proxyResolution):
{
  "match": "exact_match",
  "chainId": "4217",
  "address": "0x...",
  "name": "ContractName",
  "sources": {
    "src/Contract.sol": { "content": "pragma solidity ..." },
    ...
  },
  "proxyResolution": { ... } | null
}
"""
import json
import os
import sys


def parse(response_path: str, outdir: str = ".sources") -> dict:
    """Parse Sourcify v2 API response, extract sources, return metadata."""
    with open(response_path) as f:
        data = json.load(f)

    # Sourcify returns 404 as {"error": "..."} or the response might be empty
    if "error" in data or not data.get("match"):
        meta = {
            "contractName": "",
            "proxy": False,
            "implementation": "",
            "verified": False,
        }
        print(f"ContractName: {meta['contractName']}")
        print(f"Proxy: {meta['proxy']}")
        print(f"Implementation: {meta['implementation']}")
        print(f"Verified: {meta['verified']}")
        return meta

    # Check proxy resolution if available
    proxy_info = data.get("proxyResolution") or {}
    proxy = bool(proxy_info.get("implementations"))
    implementation = ""
    if proxy and proxy_info.get("implementations"):
        # Take the first implementation address
        impls = proxy_info["implementations"]
        if isinstance(impls, list) and impls:
            implementation = impls[0].get("address", "")
        elif isinstance(impls, dict):
            # Some formats use dict with named implementations
            first = next(iter(impls.values()), {})
            implementation = first.get("address", "") if isinstance(first, dict) else ""

    meta = {
        "contractName": data.get("name", ""),
        "proxy": proxy,
        "implementation": implementation,
        "verified": data.get("match") in ("exact_match", "partial_match"),
    }

    print(f"ContractName: {meta['contractName']}")
    print(f"Proxy: {meta['proxy']}")
    print(f"Implementation: {meta['implementation']}")
    print(f"Verified: {meta['verified']}")

    sources = data.get("sources", {})
    if not sources:
        return meta

    os.makedirs(outdir, exist_ok=True)

    for name, content_obj in sources.items():
        # Sourcify sources are {"content": "..."} objects
        if isinstance(content_obj, dict):
            content = content_obj.get("content", "")
        else:
            content = str(content_obj)

        # Sanitize filename (same logic as parse_etherscan.py)
        safe_name = os.path.basename(name.replace("/", "_").replace("\\", "_"))
        if not safe_name or safe_name.startswith("."):
            safe_name = f"source_{hash(name) & 0xFFFFFFFF:08x}.sol"
        path = os.path.join(outdir, safe_name)
        # Verify resolved path stays within outdir
        if not os.path.realpath(path).startswith(os.path.realpath(outdir)):
            print(f"  Skipping suspicious path: {name}")
            continue
        with open(path, "w") as out:
            out.write(content)
        print(f"  Source file: {name} ({len(content)} chars)")

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
