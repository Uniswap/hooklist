#!/usr/bin/env python3
"""Fetch verified source code from a block explorer API.

Usage: python3 scripts/fetch_source.py <chain> <address> [--api-key <key>] [--output <meta.json>] [--outdir <.sources>]

Fetches the Etherscan/Blockscout/Sourcify API response, parses source files to --outdir,
and writes metadata to --output. Exits non-zero if source is not verified.
"""
import json
import os
import subprocess
import sys
import time

from parse_etherscan import parse as parse_etherscan
from parse_okx import parse as parse_okx
from parse_sourcify import parse as parse_sourcify
from parse_blockscout_v2 import parse as parse_blockscout_v2

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Explorer instances (notably Blockscout ones) intermittently return 5xx,
# 429 rate limits, or empty bodies for contracts that are verified. A single
# failed attempt must not be read as "source not verified".
TRANSIENT_HTTP_CODES = {"429", "500", "502", "503", "504"}
RETRY_BACKOFF_SECONDS = 2


def fetch_with_retry(url: str, response_file: str, max_attempts: int = 5) -> str:
    """Fetch url to response_file with curl, retrying transient failures.

    Retries on curl-level failure, transient HTTP codes, and empty response
    bodies, with exponential backoff. Returns the final HTTP status code as a
    string ("000" if curl itself never succeeded).
    """
    http_code = "000"
    for attempt in range(1, max_attempts + 1):
        result = subprocess.run(
            ["curl", "-s", "-o", response_file, "-w", "%{http_code}", url],
            capture_output=True, text=True
        )
        http_code = result.stdout.strip() if result.returncode == 0 else "000"
        transient = (
            result.returncode != 0
            or http_code in TRANSIENT_HTTP_CODES
            or not os.path.exists(response_file)
            or os.path.getsize(response_file) == 0
        )
        if not transient:
            return http_code
        if attempt < max_attempts:
            delay = RETRY_BACKOFF_SECONDS * (2 ** (attempt - 1))
            print(
                f"Explorer fetch attempt {attempt}/{max_attempts} failed "
                f"(HTTP {http_code}); retrying in {delay}s...",
                file=sys.stderr,
            )
            time.sleep(delay)
    return http_code


def get_explorer_url(chain: str) -> str:
    """Look up the explorer API URL for a chain from chains.json."""
    with open(os.path.join(REPO_ROOT, "chains.json")) as f:
        chains = json.load(f)
    return chains[chain]["explorerUrl"]


def fetch_and_parse(response_path: str, outdir: str = ".sources", explorer_type: str = "etherscan") -> dict:
    """Parse an already-fetched explorer API response. Returns metadata dict."""
    if explorer_type == "sourcify":
        return parse_sourcify(response_path, outdir)
    if explorer_type == "okx":
        return parse_okx(response_path, outdir)
    if explorer_type == "blockscout-v2":
        return parse_blockscout_v2(response_path, outdir)
    return parse_etherscan(response_path, outdir)


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
    chain_id = chain_info["chainId"]

    # Build the API URL and select parser
    response_file = "explorer_response.json"

    if explorer_type == "sourcify":
        # Sourcify v2 API: GET /v2/contract/{chainId}/{address}?fields=sources,proxyResolution
        url = f"{explorer_url}/v2/contract/{chain_id}/{address}?fields=sources,proxyResolution"
        parser = parse_sourcify
    elif explorer_type == "etherscan":
        url = f"{explorer_url}&module=contract&action=getsourcecode&address={address}&apikey={api_key}"
        parser = parse_etherscan
    elif explorer_type == "okx":
        url = f"{explorer_url}&contractAddress={address}"
        parser = parse_okx
    elif explorer_type == "blockscout-v2":
        # Blockscout's native API. Same host as the Etherscan-compatible endpoint, but not
        # subject to the same rate limit, and a throttled reply cannot be mistaken for an
        # unverified contract. explorerUrl already ends in /api.
        url = f"{explorer_url}/v2/smart-contracts/{address}"
        parser = parse_blockscout_v2
    else:
        # Blockscout / Routescan — no API key
        url = f"{explorer_url}?module=contract&action=getsourcecode&address={address}"
        parser = parse_etherscan

    # Fetch
    http_code = fetch_with_retry(url, response_file)
    if http_code == "000" or http_code in TRANSIENT_HTTP_CODES:
        print(
            f"Explorer error (HTTP {http_code}) after retries — transient explorer "
            "failure, NOT a verification verdict. Try again later.",
            file=sys.stderr,
        )
        sys.exit(1)

    # For Sourcify, a 404 means not verified — write an empty error response
    if explorer_type == "sourcify" and http_code == "404":
        with open(response_file, "w") as f:
            json.dump({"error": "not found"}, f)

    # Parse
    meta = parser(response_file, outdir)

    if not meta["verified"]:
        print("Source code is NOT verified on the block explorer.", file=sys.stderr)
        with open(output_path, "w") as f:
            json.dump(meta, f, indent=2)
            f.write("\n")
        sys.exit(1)

    # Handle proxy: fetch implementation source too
    if meta["proxy"] and meta["implementation"]:
        impl_address = meta["implementation"]
        if explorer_type == "sourcify":
            impl_url = f"{explorer_url}/v2/contract/{chain_id}/{impl_address}?fields=sources"
        elif explorer_type == "etherscan":
            impl_url = f"{explorer_url}&module=contract&action=getsourcecode&address={impl_address}&apikey={api_key}"
        elif explorer_type == "okx":
            impl_url = f"{explorer_url}&contractAddress={impl_address}"
        else:
            impl_url = f"{explorer_url}?module=contract&action=getsourcecode&address={impl_address}"

        impl_response_file = "explorer_impl_response.json"
        impl_http_code = fetch_with_retry(impl_url, impl_response_file)
        if explorer_type == "sourcify" and impl_http_code == "404":
            with open(impl_response_file, "w") as f:
                json.dump({"error": "not found"}, f)

        impl_meta = parser(impl_response_file, outdir)
        if impl_meta["contractName"]:
            meta["contractName"] = impl_meta["contractName"]

    # Write metadata
    with open(output_path, "w") as f:
        json.dump(meta, f, indent=2)
        f.write("\n")

    print(f"Source fetched and parsed: {meta['contractName']} (verified={meta['verified']}, proxy={meta['proxy']})")


if __name__ == "__main__":
    main()
