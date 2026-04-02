#!/usr/bin/env python3
"""Fetch verified source code from a block explorer API.

Usage: python3 scripts/fetch_source.py <chain> <address> [--api-key <key>] [--output <meta.json>] [--outdir <.sources>]

Fetches the Etherscan/Blockscout API response, parses source files to --outdir,
and writes metadata to --output. Exits non-zero if source is not verified.
"""
import json
import os
import subprocess
import sys

from parse_etherscan import parse

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_explorer_url(chain: str) -> str:
    """Look up the explorer API URL for a chain from chains.json."""
    with open(os.path.join(REPO_ROOT, "chains.json")) as f:
        chains = json.load(f)
    return chains[chain]["explorerUrl"]


def fetch_and_parse(response_path: str, outdir: str = ".sources") -> dict:
    """Parse an already-fetched explorer API response. Returns metadata dict."""
    return parse(response_path, outdir)


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <chain> <address> [--api-key <key>] [--output <path>] [--outdir <dir>]", file=sys.stderr)
        sys.exit(1)

    chain = sys.argv[1]
    address = sys.argv[2]

    api_key = ""
    if "--api-key" in sys.argv:
        api_key = sys.argv[sys.argv.index("--api-key") + 1]

    outdir = ".sources"
    if "--outdir" in sys.argv:
        outdir = sys.argv[sys.argv.index("--outdir") + 1]

    output_path = "source_meta.json"
    if "--output" in sys.argv:
        output_path = sys.argv[sys.argv.index("--output") + 1]

    # Look up explorer URL
    with open(os.path.join(REPO_ROOT, "chains.json")) as f:
        chains = json.load(f)

    chain_info = chains[chain]
    explorer_url = chain_info["explorerUrl"]
    explorer_type = chain_info["explorer"]

    # Build the API URL
    if explorer_type == "etherscan":
        url = f"{explorer_url}&module=contract&action=getsourcecode&address={address}&apikey={api_key}"
    else:
        # Blockscout / Routescan — no API key
        url = f"{explorer_url}?module=contract&action=getsourcecode&address={address}"

    # Fetch
    response_file = "etherscan_response.json"
    result = subprocess.run(
        ["curl", "-s", "-o", response_file, url],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"Failed to fetch from explorer: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    # Parse
    meta = parse(response_file, outdir)

    if not meta["verified"]:
        print("Source code is NOT verified on the block explorer.", file=sys.stderr)
        with open(output_path, "w") as f:
            json.dump(meta, f, indent=2)
            f.write("\n")
        sys.exit(1)

    # Handle proxy: fetch implementation source too
    if meta["proxy"] and meta["implementation"]:
        impl_address = meta["implementation"]
        if explorer_type == "etherscan":
            impl_url = f"{explorer_url}&module=contract&action=getsourcecode&address={impl_address}&apikey={api_key}"
        else:
            impl_url = f"{explorer_url}?module=contract&action=getsourcecode&address={impl_address}"

        impl_response_file = "etherscan_impl_response.json"
        subprocess.run(["curl", "-s", "-o", impl_response_file, impl_url], capture_output=True)
        impl_meta = parse(impl_response_file, outdir)
        if impl_meta["contractName"]:
            meta["contractName"] = impl_meta["contractName"]

    # Write metadata
    with open(output_path, "w") as f:
        json.dump(meta, f, indent=2)
        f.write("\n")

    print(f"Source fetched and parsed: {meta['contractName']} (verified={meta['verified']}, proxy={meta['proxy']})")


if __name__ == "__main__":
    main()
