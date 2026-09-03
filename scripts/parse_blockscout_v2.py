#!/usr/bin/env python3
"""Parse a Blockscout v2 API response.

Usage: python3 scripts/parse_blockscout_v2.py response.json [--outdir .sources]

Prints contract metadata to stdout and writes individual source files
to the output directory for grep-based analysis.

Why this exists alongside parse_etherscan.py: Blockscout instances also expose an
Etherscan-compatible endpoint (`?module=contract&action=getsourcecode`), but that
endpoint is rate limited far more aggressively on some instances, and a throttled
response is indistinguishable from an unverified contract — it returns
`{"message":"Too many requests","result":null,"status":"0"}`, which reads as "no
source". The native v2 endpoint is not subject to the same limit and returns richer
metadata, so a chain whose Etherscan-compatible endpoint is unreliable can be pointed
at `blockscout-v2` instead.

Blockscout v2 response format (GET /api/v2/smart-contracts/{address}):
{
  "name": "ContractName",
  "is_verified": true,
  "file_path": "src/Contract.sol",
  "source_code": "pragma solidity ...",
  "additional_sources": [
    {"file_path": "lib/Base.sol", "source_code": "pragma solidity ..."},
    ...
  ],
  "proxy_type": null | "eip1167" | ...,
  "implementations": [{"address": "0x...", "name": "Impl"}]
}

An unverified or unknown address returns {"message": "Not found"} with no source keys.
"""
import json
import os
import sys


def _unverified() -> dict:
    meta = {"contractName": "", "proxy": False, "implementation": "", "verified": False}
    print(f"ContractName: {meta['contractName']}")
    print(f"Proxy: {meta['proxy']}")
    print(f"Implementation: {meta['implementation']}")
    print(f"Verified: {meta['verified']}")
    return meta


def parse(response_path: str, outdir: str = ".sources") -> dict:
    """Parse Blockscout v2 API response, extract sources, return metadata."""
    with open(response_path) as f:
        body = f.read()
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        # A bot-challenge or error page, not an API answer: say so instead of
        # crashing, and never call the contract unverified on its account.
        raise RuntimeError(
            "Explorer returned a non-JSON body (a bot challenge or error page?) — "
            "transient explorer failure, not an unverified contract"
        ) from None

    # Not-found, error, and rate-limited shapes all lack `is_verified`. Treat anything
    # without it as unverified rather than indexing into keys that may not be there.
    if not isinstance(data, dict) or not data.get("is_verified"):
        return _unverified()

    impls = data.get("implementations") or []
    implementation = ""
    if impls and isinstance(impls, list) and isinstance(impls[0], dict):
        implementation = impls[0].get("address", "") or ""

    meta = {
        "contractName": data.get("name", "") or "",
        # proxy_type is null for a plain contract; some instances report "unknown"
        "proxy": bool(data.get("proxy_type")) and data.get("proxy_type") != "unknown",
        "implementation": implementation,
        "verified": True,
    }

    print(f"ContractName: {meta['contractName']}")
    print(f"Proxy: {meta['proxy']}")
    print(f"Implementation: {meta['implementation']}")
    print(f"Verified: {meta['verified']}")

    # The primary file comes back as source_code/file_path; the rest as additional_sources.
    sources = {}
    if data.get("source_code"):
        sources[data.get("file_path") or "main.sol"] = data["source_code"]
    for extra in data.get("additional_sources") or []:
        if not isinstance(extra, dict):
            continue
        path = extra.get("file_path")
        content = extra.get("source_code")
        if path and content:
            sources[path] = content

    if not sources:
        return meta

    os.makedirs(outdir, exist_ok=True)

    for name, content in sources.items():
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

    outdir = ".sources"
    if "--outdir" in sys.argv:
        outdir = sys.argv[sys.argv.index("--outdir") + 1]

    parse(sys.argv[1], outdir)


if __name__ == "__main__":
    main()
