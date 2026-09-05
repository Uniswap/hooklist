#!/usr/bin/env python3
"""Fetch a deployed hook's runtime bytecode and print its sha256 fingerprint.

Usage: python3 scripts/fetch_codehash.py <chain> <address>
  prints "sha256:<hex>" and exits 0 on success
  prints "EMPTY" and exits 3 if the address has no code
  prints an error to stderr and exits 1 on failure

The hash is sha256 (NOT keccak) of the raw bytes decoded from eth_getCode's
hex result. It is internal to hooklist and never needs to match on-chain
keccak-derived values (e.g. EXTCODEHASH) — it exists only to fingerprint
"have we seen this exact runtime bytecode before" across a release's members.

Code retrieval tries two strategies in order:
  1. Explorer proxy module (etherscan/blockscout/routescan explorer types
     from chains.json): GET .../api?...&module=proxy&action=eth_getCode
     &address=<addr>&tag=latest. The module=proxy... query segment is
     joined with "&" if explorerUrl already has a "?" (etherscan-style
     URLs, which embed "?chainid=...") or "?" otherwise (blockscout/
     routescan URLs, which have no query string). &apikey=$ETHERSCAN_API_KEY
     is appended only when the chain's explorer type is exactly
     "etherscan" — blockscout/routescan/zora hosts don't need it and
     shouldn't receive it.
  2. Public RPC fallback (PUBLIC_RPC below): POST eth_getCode via JSON-RPC.
     Used for chains whose explorer type isn't proxy-module-compatible
     (okx, sourcify, zksync) and as a fallback when the explorer call fails
     (this repo has documented explorer flakiness, e.g. transient robinhood
     blockscout 500s — a fetch failure is not evidence of anything).

Fetch failures never hard-block anything upstream (validate.py, CI) — a
failure here should be treated as "no mechanical check available", not
evidence of anything wrong with the hook.
"""
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Hard charset guard: an address is used to build explorer query URLs below,
# so anything outside this shape (e.g. "0xVICTIM&address=0xLEGIT") must be
# rejected before any URL is constructed or any network call is made — never
# just relied on being "probably fine" because it came from validated JSON
# upstream. quote(..., safe='') on top of this is belt-and-braces.
_ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")


def _validate_address(address: str) -> str:
    """Validate `address` against the strict hex-address charset and return
    it lowercased. Raises ValueError on anything else (wrong length, non-hex
    characters, extra query-string-shaped content, etc.)."""
    if not isinstance(address, str) or not _ADDRESS_RE.match(address):
        raise ValueError(f"invalid address: {address!r} (expected ^0x[0-9a-fA-F]{{40}}$)")
    return address.lower()

# Public RPC endpoints for every chain that currently has hook files under
# hooks/ (derived from chains.json entries actually used there — chains.json
# lists a few chains with no hook files yet, e.g. tempo/zksync/ink/linea/
# megaeth, which have no verified entry here since there was nothing to
# backfill against them).
#
# Each URL below was live-verified with eth_chainId against the chainId in
# chains.json as of 2026-08-31. Two commonly listed public endpoints were
# dead and were substituted with a working canonical endpoint:
#   - polygon: https://polygon-rpc.com returned a hard "API key
#     disabled/tenant disabled" 403 — substituted publicnode's endpoint.
#   - worldchain: https://rpc.worldchain.network does not resolve (DNS
#     failure) — substituted Alchemy's public World Chain endpoint.
PUBLIC_RPC = {
    "ethereum": "https://ethereum-rpc.publicnode.com",
    "unichain": "https://mainnet.unichain.org",
    "base": "https://mainnet.base.org",
    "arbitrum": "https://arb1.arbitrum.io/rpc",
    "optimism": "https://mainnet.optimism.io",
    "polygon": "https://polygon-bor-rpc.publicnode.com",
    "blast": "https://rpc.blast.io",
    "bnb": "https://bsc-rpc.publicnode.com",
    "celo": "https://forno.celo.org",
    "zora": "https://rpc.zora.energy",
    "soneium": "https://rpc.soneium.org",
    "avalanche": "https://avalanche-c-chain-rpc.publicnode.com",
    "worldchain": "https://worldchain-mainnet.g.alchemy.com/public",
    "xlayer": "https://rpc.xlayer.tech",
    "monad": "https://rpc.monad.xyz",
    "robinhood": "https://rpc.mainnet.chain.robinhood.com",
    # No verified public endpoint yet (no hook files under these chains):
    # ink, linea, megaeth, tempo, zksync.
}

# chains.json "explorer" values whose API exposes an Etherscan-compatible
# module=proxy&action=eth_getCode endpoint.
EXPLORER_PROXY_TYPES = ("etherscan", "blockscout", "routescan")

# Retry/backoff for each strategy's HTTP call — this repo has documented
# explorer flakiness (transient 500s), and a single failed attempt should
# not be treated the same as "this strategy doesn't work". 3 attempts total,
# sleeping 1s then 3s between attempts (no sleep after the final attempt).
RETRY_ATTEMPTS = 3
RETRY_DELAYS = (1, 3)


def _call_with_retries(get, url: str, payload: dict | None, sleep):
    """Call `get(url, payload)`, retrying on any exception up to RETRY_ATTEMPTS
    times with RETRY_DELAYS backoff. Re-raises the last exception if every
    attempt fails; callers already wrap this in their own try/except."""
    last_exc = None
    for attempt in range(RETRY_ATTEMPTS):
        try:
            return get(url, payload)
        except Exception as e:
            last_exc = e
            if attempt < RETRY_ATTEMPTS - 1:
                sleep(RETRY_DELAYS[attempt])
    raise last_exc


def _default_get(url: str, payload: dict | None):
    """Default network transport: plain GET (payload=None) or JSON POST."""
    headers = {"User-Agent": "hooklist-fetch-codehash/1.0"}
    if payload is None:
        req = urllib.request.Request(url, headers=headers)
    else:
        headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def _load_chains() -> dict:
    with open(os.path.join(REPO_ROOT, "chains.json")) as f:
        return json.load(f)


def _is_code_hex(value) -> bool:
    if not isinstance(value, str) or not value.startswith("0x"):
        return False
    hexpart = value[2:]
    return all(c in "0123456789abcdefABCDEF" for c in hexpart)


def _fetch_via_explorer(chain_info: dict, address: str, get, sleep=None) -> str | None:
    """Strategy 1. Returns the '0x...' code hex, or None on any failure."""
    if chain_info["explorer"] not in EXPLORER_PROXY_TYPES:
        return None
    sleep = sleep or time.sleep
    explorer_url = chain_info["explorerUrl"]
    # Etherscan explorerUrls already carry a query string (e.g. "...?chainid=1");
    # blockscout/routescan ones don't (e.g. "https://soneium.blockscout.com/api").
    # Mirror fetch_source.py's separator handling so we don't produce a dead
    # "...api&module=..." URL for the latter.
    sep = "&" if "?" in explorer_url else "?"
    # Belt-and-braces: address is already charset-validated by fetch_code,
    # but quote(..., safe='') ensures nothing in it can ever be interpreted
    # as an additional query parameter.
    url = f"{explorer_url}{sep}module=proxy&action=eth_getCode&address={urllib.parse.quote(address, safe='')}&tag=latest"
    # Only etherscan actually needs (or accepts) the API key — don't leak it
    # to blockscout/routescan/zora hosts that have no use for it.
    if chain_info["explorer"] == "etherscan":
        api_key = os.environ.get("ETHERSCAN_API_KEY")
        if api_key:
            url += f"&apikey={api_key}"
    try:
        resp = _call_with_retries(get, url, None, sleep)
    except Exception:
        return None
    if not isinstance(resp, dict) or "error" in resp:
        return None
    result = resp.get("result")
    return result if _is_code_hex(result) else None


def _fetch_via_rpc(chain: str, address: str, get, sleep=None) -> str | None:
    """Strategy 2. Returns the '0x...' code hex, or None on any failure."""
    url = PUBLIC_RPC.get(chain)
    if url is None:
        return None
    sleep = sleep or time.sleep
    payload = {"jsonrpc": "2.0", "id": 1, "method": "eth_getCode", "params": [address, "latest"]}
    try:
        resp = _call_with_retries(get, url, payload, sleep)
    except Exception:
        return None
    if not isinstance(resp, dict) or "error" in resp:
        return None
    result = resp.get("result")
    return result if _is_code_hex(result) else None


def fetch_code(chain: str, address: str, get=None, sleep=None) -> str:
    """Fetch runtime bytecode ('0x...' hex) for address on chain.

    Tries the explorer proxy module first, then a public RPC fallback. Each
    strategy retries its HTTP call up to RETRY_ATTEMPTS times with backoff
    before giving up (see _call_with_retries). Raises RuntimeError if both
    strategies fail (or the chain is unknown).
    `get` is an injectable (url, payload_or_None) -> response_dict transport,
    for tests — production calls default to a real urllib request. `sleep`
    is an injectable (seconds) -> None, for tests — production defaults to
    time.sleep.
    """
    address = _validate_address(address)
    if get is None:
        get = _default_get
    chains = _load_chains()
    if chain not in chains:
        raise RuntimeError(f"unknown chain: {chain!r} (not present in chains.json)")
    chain_info = chains[chain]

    code = _fetch_via_explorer(chain_info, address, get, sleep=sleep)
    if code is not None:
        return code

    code = _fetch_via_rpc(chain, address, get, sleep=sleep)
    if code is not None:
        return code

    raise RuntimeError(f"failed to fetch code for {chain}:{address} (explorer + RPC both failed)")


def codehash_of(code_hex: str) -> str | None:
    """sha256 fingerprint ('sha256:<hex>') of the raw bytes in a '0x...' code
    hex string. Returns None for empty code ('0x' / '0X')."""
    if code_hex is None:
        return None
    hexpart = code_hex[2:] if code_hex.startswith(("0x", "0X")) else code_hex
    if hexpart == "":
        return None
    raw = bytes.fromhex(hexpart)
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <chain> <address>", file=sys.stderr)
        sys.exit(1)
    chain, address = sys.argv[1], sys.argv[2]
    try:
        code = fetch_code(chain, address)
    except Exception as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    h = codehash_of(code)
    if h is None:
        print("EMPTY")
        sys.exit(3)
    print(h)
    sys.exit(0)


if __name__ == "__main__":
    main()
