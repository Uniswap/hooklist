#!/usr/bin/env python3
"""Minimal JSON-RPC client with URL fallback (stdlib only)."""
import json
import urllib.request


class RpcError(Exception):
    pass


def _default_post(url: str, payload: dict) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "hooklist-ingest/0.1",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


class RpcClient:
    def __init__(self, urls: list[str], post=None):
        if not urls:
            raise ValueError("at least one RPC URL required")
        self.urls = urls
        self._post = post or _default_post
        self._id = 0

    def call(self, method: str, params: list):
        self._id += 1
        payload = {"jsonrpc": "2.0", "id": self._id, "method": method, "params": params}
        errors = []
        for url in self.urls:
            try:
                resp = self._post(url, payload)
            except Exception as e:  # transport failure -> try next URL
                errors.append(f"{url}: {e}")
                continue
            if "error" in resp:
                errors.append(f"{url}: rpc error {resp['error']}")
                continue
            return resp["result"]
        raise RpcError(f"{method} failed on all URLs: {'; '.join(errors)}")

    def block_number(self) -> int:
        return int(self.call("eth_blockNumber", []), 16)

    def get_code(self, address: str) -> str:
        return self.call("eth_getCode", [address.lower(), "latest"])

    def get_logs(self, address: str, topic0: str, from_block: int, to_block: int) -> list:
        return self.call("eth_getLogs", [{
            "address": address.lower(),
            "topics": [topic0],
            "fromBlock": hex(from_block),
            "toBlock": hex(to_block),
        }])
