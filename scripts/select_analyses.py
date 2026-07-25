#!/usr/bin/env python3
"""Select which new families to dispatch for analysis.

Spec rule: dispatch iff no family file, no open families/<id> PR, no
in-flight analyze-family run, and < 3 failed runs (then a human stub-path
takes over). Cap per ingest run, oldest first (candidates arrive in scan
order, which is block order).
"""
import argparse
import json
import os
import subprocess
import sys

MAX_FAILURES = 3


def _default_gh(args: list[str]) -> str:
    return subprocess.run(["gh"] + args, check=True, capture_output=True,
                          text=True).stdout


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
    with open(os.path.join(args.repo_root, "new_families.json")) as f:
        candidates = json.load(f)
    print(json.dumps(select(candidates, args.repo_root, cap=args.cap)))


if __name__ == "__main__":
    main()
