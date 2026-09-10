#!/usr/bin/env python3
"""Find and resolve case-collision duplicate hook files.

Reads the committed tree via git plumbing (never the working tree — macOS
checkouts materialize only one case variant per pair).

Usage:
  python3 scripts/dedupe_case_pairs.py            # report only
  python3 scripts/dedupe_case_pairs.py --apply    # print `git rm --cached` lines,
                                                  # write docs/dedupe-report.md
"""
import argparse
import collections
import json
import os
import subprocess


def _git(repo_root: str, *args: str) -> str:
    return subprocess.run(["git", "-C", repo_root, *args],
                          capture_output=True, text=True, check=True).stdout


def find_pairs(paths: list[str]) -> list[tuple[str, str]]:
    groups = collections.defaultdict(list)
    for path in paths:
        groups[path.lower()].append(path)
    return [tuple(sorted(v)) for v in groups.values() if len(v) == 2]


def choose_keeper(path_a, path_b, content_a, content_b, mtime_a, mtime_b) -> str:
    if content_a == content_b:
        base_a = os.path.basename(path_a)
        return path_a if base_a == base_a.lower() else path_b
    return path_a if mtime_a > mtime_b else path_b


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    root = args.repo_root

    paths = [l for l in
             _git(root, "ls-tree", "-r", "--name-only", "HEAD", "hooks/").splitlines() if l]
    pairs = find_pairs(paths)
    report, rm_lines = [], []
    for a, b in pairs:
        ca = json.loads(_git(root, "cat-file", "-p", f"HEAD:{a}"))
        cb = json.loads(_git(root, "cat-file", "-p", f"HEAD:{b}"))
        ma = int(_git(root, "log", "-1", "--format=%ct", "--", a).strip() or 0)
        mb = int(_git(root, "log", "-1", "--format=%ct", "--", b).strip() or 0)
        keeper = choose_keeper(a, b, ca, cb, ma, mb)
        loser = b if keeper == a else a
        keeper_content = ca if keeper == a else cb
        loser_content = cb if keeper == a else ca
        status = "identical" if ca == cb else "NEEDS-REVIEW (conflicting content)"
        keeper_name = keeper_content.get("hook", {}).get("name")
        loser_name = loser_content.get("hook", {}).get("name")
        report.append(
            f"- keep `{keeper}` (name: \"{keeper_name}\"), "
            f"drop `{loser}` (name: \"{loser_name}\") — {status}")
        rm_lines.append(loser)

    print(f"{len(pairs)} case-collision pairs found")
    for line in report:
        print(line)
    if args.apply:
        os.makedirs(os.path.join(root, "docs"), exist_ok=True)
        with open(os.path.join(root, "docs", "dedupe-report.md"), "w") as f:
            f.write(f"# Case-collision dedupe report\n\n{len(pairs)} pairs\n\n")
            f.write("\n".join(report) + "\n")
        for loser in rm_lines:
            print(f"git rm --cached '{loser}'")


if __name__ == "__main__":
    main()
