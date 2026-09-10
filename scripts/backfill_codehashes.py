#!/usr/bin/env python3
"""One-off backfill: populate releases/<project>/<id>.json source.codeHashes
from live on-chain runtime bytecode.

For every release, finds its member hook files (any hooks/**/*.json whose
hook.release == "<project>/<id>"), fetches each member's runtime code live
(scripts/fetch_codehash.fetch_code: explorer proxy first, public RPC
fallback second), dedupes the sha256 fingerprints, and writes the sorted
list into the release's source.codeHashes.

Per-address failures are recorded and skipped — fetch_code already retries
via the other strategy internally, so no further retry happens here. A
release where every member fetch failed gets NO codeHashes field written
(absence means "no mechanical check was possible", not "zero reviewed
variants"). EMPTY code (e.g. a selfdestructed contract) is recorded in the
report but contributes no hash.

Usage:
  python3 scripts/backfill_codehashes.py                 # dry run, prints report
  python3 scripts/backfill_codehashes.py --write          # apply to release files
  python3 scripts/backfill_codehashes.py --project spot --write   # one project
"""
import argparse
import glob
import json
import os
import time

import fetch_codehash

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SLEEP_SECONDS = 0.25


def find_members(root: str) -> dict:
    """release ref ('project/id') -> list of (chain, address, hook_path) members."""
    members: dict[str, list] = {}
    for path in sorted(glob.glob(os.path.join(root, "hooks", "**", "*.json"), recursive=True)):
        with open(path) as f:
            data = json.load(f)
        ref = data.get("hook", {}).get("release")
        if not ref:
            continue
        chain = data["hook"]["chain"]
        address = data["hook"]["address"]
        members.setdefault(ref, []).append((chain, address, path))
    return members


def all_release_refs(root: str) -> list:
    refs = []
    for path in sorted(glob.glob(os.path.join(root, "releases", "*", "*.json"))):
        with open(path) as f:
            data = json.load(f)
        refs.append(f"{data['project']}/{data['id']}")
    return sorted(set(refs))


def backfill_release(ref: str, member_list: list) -> dict:
    """Fetch codehashes for one release's members. Returns a report dict."""
    hashes = set()
    failures = []
    empties = []
    ok = 0

    for chain, address, _path in member_list:
        try:
            code = fetch_codehash.fetch_code(chain, address)
        except Exception as e:
            failures.append(f"{chain}:{address} ({e})")
            time.sleep(SLEEP_SECONDS)
            continue
        h = fetch_codehash.codehash_of(code)
        if h is None:
            empties.append(f"{chain}:{address}")
        else:
            hashes.add(h)
            ok += 1
        time.sleep(SLEEP_SECONDS)

    return {
        "ref": ref,
        "total": len(member_list),
        "ok": ok,
        "failures": failures,
        "empties": empties,
        "hashes": sorted(hashes),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=REPO_ROOT)
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--project", default=None, help="limit to one release's project")
    args = ap.parse_args()
    root = args.repo_root

    members = find_members(root)
    refs = all_release_refs(root)
    if args.project:
        refs = [r for r in refs if r.startswith(args.project + "/")]

    full = partial = none = 0
    multi_hash_families = []
    reports = []

    for ref in refs:
        member_list = members.get(ref, [])
        report = backfill_release(ref, member_list)
        reports.append(report)

        if report["hashes"] and not report["failures"] and not report["empties"]:
            status = "FULL"
            full += 1
        elif report["hashes"]:
            status = "PARTIAL"
            partial += 1
        else:
            status = "NONE"
            none += 1
        if len(report["hashes"]) > 1:
            multi_hash_families.append(ref)

        print(f"[{status}] {ref}: {report['ok']}/{report['total']} fetched, "
              f"{len(report['hashes'])} distinct hash(es)")
        for f in report["failures"]:
            print(f"    FAILED: {f}")
        for e in report["empties"]:
            print(f"    EMPTY: {e}")

        if args.write and report["hashes"]:
            project, rid = ref.split("/", 1)
            release_path = os.path.join(root, "releases", project, rid + ".json")
            with open(release_path) as fh:
                data = json.load(fh)
            data.setdefault("source", {})["codeHashes"] = report["hashes"]
            with open(release_path, "w") as fh:
                json.dump(data, fh, indent=2)
                fh.write("\n")

    print(f"\nSummary: {full} fully hashed, {partial} partial, {none} none (of {len(refs)} releases).")
    if multi_hash_families:
        print(f"Multi-hash (immutables) families: {', '.join(multi_hash_families)}")


if __name__ == "__main__":
    main()
