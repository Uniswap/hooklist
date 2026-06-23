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

from parse_etherscan import parse as parse_etherscan
from parse_okx import parse as parse_okx
from parse_sourcify import parse as parse_sourcify

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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
    return parse_etherscan(response_path, outdir)


def okx_curl_args(url: str, request_path: str) -> list[str]:
    """Build OKX-authenticated curl arguments for the verified contract API."""
    import base64
    import datetime
    import hashlib
    import hmac

    access_key = os.environ.get("OKX_ACCESS_KEY", "")
    secret_key = os.environ.get("OKX_SECRET_KEY", "")
    passphrase = os.environ.get("OKX_PASSPHRASE", "")
    if not (access_key and secret_key and passphrase):
        raise RuntimeError("OKX_ACCESS_KEY, OKX_SECRET_KEY, and OKX_PASSPHRASE are required for X Layer source fetches.")

    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    prehash = f"{timestamp}GET{request_path}"
    signature = base64.b64encode(
        hmac.new(secret_key.encode(), prehash.encode(), hashlib.sha256).digest()
    ).decode()

    return [
        "-H", f"OK-ACCESS-KEY: {access_key}",
        "-H", f"OK-ACCESS-SIGN: {signature}",
        "-H", f"OK-ACCESS-PASSPHRASE: {passphrase}",
        "-H", f"OK-ACCESS-TIMESTAMP: {timestamp}",
        url,
    ]


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
        request_path = url.removeprefix("https://web3.okx.com")
        parser = parse_okx
    else:
        # Blockscout / Routescan — no API key
        url = f"{explorer_url}?module=contract&action=getsourcecode&address={address}"
        parser = parse_etherscan

    # Fetch
    try:
        curl_args = okx_curl_args(url, request_path) if explorer_type == "okx" else [url]
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    result = subprocess.run(
        ["curl", "-s", "-o", response_file, "-w", "%{http_code}", *curl_args],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"Failed to fetch from explorer: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    # For Sourcify, a 404 means not verified — write an empty error response
    http_code = result.stdout.strip()
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
            request_path = impl_url.removeprefix("https://web3.okx.com")
        else:
            impl_url = f"{explorer_url}?module=contract&action=getsourcecode&address={impl_address}"

        impl_response_file = "explorer_impl_response.json"
        impl_curl_args = okx_curl_args(impl_url, request_path) if explorer_type == "okx" else [impl_url]
        impl_result = subprocess.run(
            ["curl", "-s", "-o", impl_response_file, "-w", "%{http_code}", *impl_curl_args],
            capture_output=True, text=True
        )
        if explorer_type == "sourcify" and impl_result.stdout.strip() == "404":
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
