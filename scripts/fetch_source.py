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
# Some explorers (robinhoodchain.blockscout.com since late August 2026) sit
# behind a Cloudflare bot challenge that answers curl's default user agent
# with an HTTP 403 HTML page; the same request with a browser user agent
# gets the JSON. Identify as a browser, and treat a 403 as transient so a
# challenge is retried rather than read as "source not verified".
#
# As of 2026-09-10 the challenge also fires on any user agent containing
# "Chrome" (32/32 robinhood hooks -> 403 + `cf-mitigated: challenge`, from
# CI and locally), while Safari and Firefox strings get JSON for 32/32.
# Keep this string Chrome-free; test_fetch_source guards it.
FETCH_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.6 Safari/605.1.15 hooklist-fetch"
)
CHALLENGE_HTTP_CODES = {"403"}


def fetch_with_retry(url: str, response_file: str, max_attempts: int = 5) -> str:
    """Fetch url to response_file with curl, retrying transient failures.

    Retries on curl-level failure, transient HTTP codes, and empty response
    bodies, with exponential backoff. Returns the final HTTP status code as a
    string ("000" if curl itself never succeeded).
    """
    http_code = "000"
    for attempt in range(1, max_attempts + 1):
        result = subprocess.run(
            [
                "curl", "-s", "-o", response_file, "-w", "%{http_code}",
                "-A", FETCH_USER_AGENT, "-H", "Accept: application/json",
                url,
            ],
            capture_output=True, text=True
        )
        http_code = result.stdout.strip() if result.returncode == 0 else "000"
        transient = (
            result.returncode != 0
            or http_code in TRANSIENT_HTTP_CODES
            or http_code in CHALLENGE_HTTP_CODES
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


# Explorers tried, in order, after the chain's own explorer reports the source as
# unverified. A hook verified on any of them has public source that matches the
# deployed bytecode, so the review can read it. Etherscan v2 is skipped without an
# API key, and on chains it does not index it answers "not verified".
FALLBACK_EXPLORERS = [
    ("sourcify", "https://sourcify.dev/server"),
    ("etherscan", "https://api.etherscan.io/v2/api?chainid={chain_id}"),
]


def build_source_url(explorer_type: str, explorer_url: str, chain_id: int, address: str, api_key: str) -> str:
    """API URL that returns the verified source of address on the given explorer."""
    if explorer_type == "sourcify":
        # Sourcify v2 API: GET /v2/contract/{chainId}/{address}?fields=...
        # `compilation` carries the contract name, which is the fallback assemble_hook.py
        # uses when the classifier returns no name.
        return (
            f"{explorer_url}/v2/contract/{chain_id}/{address}"
            "?fields=sources,compilation,proxyResolution"
        )
    if explorer_type == "etherscan":
        return f"{explorer_url}&module=contract&action=getsourcecode&address={address}&apikey={api_key}"
    if explorer_type == "okx":
        return f"{explorer_url}&contractAddress={address}"
    if explorer_type == "blockscout-v2":
        # Blockscout's native API. Same host as the Etherscan-compatible endpoint, but not
        # subject to the same rate limit, and a throttled reply cannot be mistaken for an
        # unverified contract. explorerUrl already ends in /api.
        return f"{explorer_url}/v2/smart-contracts/{address}"
    # Blockscout / Routescan — no API key
    return f"{explorer_url}?module=contract&action=getsourcecode&address={address}"


def explorer_candidates(chain_info: dict, api_key: str) -> list:
    """The chain's explorer first, then each fallback that is not the same explorer."""
    chain_id = chain_info["chainId"]
    candidates = [(chain_info["explorer"], chain_info["explorerUrl"])]
    for explorer_type, url_template in FALLBACK_EXPLORERS:
        if explorer_type == "etherscan" and not api_key:
            continue
        candidate = (explorer_type, url_template.format(chain_id=chain_id))
        if candidate not in candidates:
            candidates.append(candidate)
    return candidates


def fetch_meta(explorer_type: str, explorer_url: str, chain_id: int, address: str,
               api_key: str, outdir: str, response_file: str):
    """Fetch and parse one explorer's answer. Returns (http_code, meta); meta is None
    when the explorer failed transiently, so no verdict can be read from it."""
    url = build_source_url(explorer_type, explorer_url, chain_id, address, api_key)
    http_code = fetch_with_retry(url, response_file)
    if http_code == "000" or http_code in TRANSIENT_HTTP_CODES:
        return http_code, None
    # For Sourcify, a 404 means not verified — write an empty error response
    if explorer_type == "sourcify" and http_code == "404":
        with open(response_file, "w") as f:
            json.dump({"error": "not found"}, f)
    return http_code, fetch_and_parse(response_file, outdir, explorer_type)


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

    with open(os.path.join(REPO_ROOT, "chains.json")) as f:
        chains = json.load(f)
    chain_info = chains[chain]
    chain_id = chain_info["chainId"]

    response_file = "explorer_response.json"
    meta = None
    primary_meta = None
    transient_codes = []
    verified_on = None
    for index, (explorer_type, explorer_url) in enumerate(explorer_candidates(chain_info, api_key)):
        http_code, candidate_meta = fetch_meta(
            explorer_type, explorer_url, chain_id, address, api_key, outdir, response_file
        )
        if candidate_meta is None:
            transient_codes.append(f"{explorer_type}: HTTP {http_code}")
            continue
        if index == 0:
            primary_meta = candidate_meta
        if candidate_meta["verified"]:
            meta = candidate_meta
            verified_on = (explorer_type, explorer_url)
            break
        if index > 0:
            print(f"Source code is NOT verified on {explorer_type} either.", file=sys.stderr)
        else:
            print(f"Source code is NOT verified on {explorer_type}; trying other explorers.", file=sys.stderr)

    if meta is None:
        if primary_meta is None or transient_codes:
            print(
                f"Explorer error after retries ({', '.join(transient_codes)}) and no explorer "
                "reported the source as verified: transient explorer failure, NOT a "
                "verification verdict. Try again later.",
                file=sys.stderr,
            )
            if primary_meta is None:
                sys.exit(1)
        print("Source code is NOT verified on any supported explorer.", file=sys.stderr)
        with open(output_path, "w") as f:
            json.dump(primary_meta, f, indent=2)
            f.write("\n")
        sys.exit(1)

    explorer_type, explorer_url = verified_on
    meta["verifiedOn"] = explorer_type

    # Handle proxy: fetch implementation source too, from the explorer that verified the proxy
    if meta["proxy"] and meta["implementation"]:
        _, impl_meta = fetch_meta(
            explorer_type, explorer_url, chain_id, meta["implementation"], api_key, outdir,
            "explorer_impl_response.json",
        )
        if impl_meta and impl_meta["contractName"]:
            meta["contractName"] = impl_meta["contractName"]

    # Write metadata
    with open(output_path, "w") as f:
        json.dump(meta, f, indent=2)
        f.write("\n")

    print(
        f"Source fetched and parsed: {meta['contractName']} (verified={meta['verified']}, "
        f"proxy={meta['proxy']}, verifiedOn={meta['verifiedOn']})"
    )


if __name__ == "__main__":
    main()
