#!/usr/bin/env python3
"""Append-only JSONL instance ledger, one file per chain."""
import json
import os

REQUIRED_KEYS = {"address", "block", "family"}


def make_line(address: str, family: str, block: int) -> dict:
    return {"address": address.lower(), "block": block, "family": family.lower()}


def read_lines(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def latest_by_address(lines: list[dict]) -> dict[str, dict]:
    latest = {}
    for line in lines:
        latest[line["address"]] = line
    return latest


def append_lines(path: str, new_lines: list[dict]) -> int:
    for line in new_lines:
        if set(line) != REQUIRED_KEYS:
            raise ValueError(f"index line must have exactly {REQUIRED_KEYS}: {line}")
        if line["address"] != line["address"].lower():
            raise ValueError(f"index address must be lowercase: {line['address']}")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a") as f:
        for line in new_lines:
            f.write(json.dumps(line, sort_keys=True, separators=(",", ":")) + "\n")
    return len(new_lines)
