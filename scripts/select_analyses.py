#!/usr/bin/env python3
"""Select which families to dispatch for analysis.

Spec rule (retry-by-absence): the candidate set is every family present in
index/ that has no families/<id>.json file — a missing family file, with no
open branch/PR and no in-flight run, IS the retry queue. Deriving candidates
from the index (rather than from a "new this run" list) means overflow
beyond the cap, failed/cancelled analysis runs, and lost dispatches are all
picked up again on the next ingest run. Dispatch iff no family file, no open
families/<id> PR, no in-flight analyze-family run, and < 3 failed runs (then
a human stub-path takes over). Cap per ingest run.
"""
import argparse
import glob
import json
import os
import subprocess
import sys

import index_ledger

MAX_FAILURES = 3


def _default_gh(args: list[str]) -> str:
    return subprocess.run(["gh"] + args, check=True, capture_output=True,
                          text=True).stdout


def candidates_from_index(repo_root: str) -> list[dict]:
    """Families in index/ with no families/<id>.json, each with one
    representative instance (deterministic: first by sorted chain, then by
    sorted address within the chain)."""
    by_family: dict[str, dict] = {}
    for index_path in sorted(glob.glob(os.path.join(repo_root, "index", "*.jsonl"))):
        chain = os.path.basename(index_path)[:-len(".jsonl")]
        latest = index_ledger.latest_by_address(index_ledger.read_lines(index_path))
        for address in sorted(latest):
            fam = latest[address]["family"]
            if fam == "empty-code" or fam in by_family:
                continue
            if os.path.exists(os.path.join(repo_root, "families", f"{fam}.json")):
                continue
            by_family[fam] = {"family": fam, "chain": chain, "address": address}
    return list(by_family.values())


def select(candidates: list[dict], repo_root: str, gh=_default_gh, cap: int = 5) -> list[dict]:
    if not candidates:
        return []
    open_branches = {p["headRefName"] for p in json.loads(
        gh(["pr", "list", "--state", "open", "--json", "headRefName",
            "--limit", "200"]))}
    runs = json.loads(gh(["run", "list", "--workflow", "analyze-family.yml",
                          "--json", "displayTitle,status,conclusion",
                          "--limit", "500"]))
    in_flight = {r["displayTitle"] for r in runs
                 if r["status"] in ("in_progress", "queued", "waiting")}
    failures: dict[str, int] = {}
    for r in runs:
        if r["status"] == "completed" and r["conclusion"] == "failure":
            failures[r["displayTitle"]] = failures.get(r["displayTitle"], 0) + 1

    selected = []
    for cand in candidates:
        fam = cand["family"]
        if fam == "empty-code":
            continue
        if os.path.exists(os.path.join(repo_root, "families", f"{fam}.json")):
            continue
        if f"families/{fam}" in open_branches:
            continue
        title = f"analyze-family {fam}"
        if title in in_flight or failures.get(title, 0) >= MAX_FAILURES:
            continue
        selected.append(cand)
        if len(selected) >= cap:
            break
    return selected


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--cap", type=int, default=5)
    args = ap.parse_args()
    candidates = candidates_from_index(args.repo_root)
    print(json.dumps(select(candidates, args.repo_root, cap=args.cap)))


if __name__ == "__main__":
    main()
