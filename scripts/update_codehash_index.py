#!/usr/bin/env python3
"""Post-merge machine maintenance job: keep each release's source.codeHashes
review cache current with its members' live runtime bytecode.

For every pointer-carrying hook file (`hooks/**/*.json` with `hook.release`
set), fetch that member's live runtime bytecode fingerprint (throttled, with
fetch_codehash's built-in explorer+RPC retry/backoff) and, if it is not
already present in the pointed release's `source.codeHashes`, append it
(sorted, deduped). `codeHashes` is entirely machine-maintained — the human
review gate is the PR that adds or changes the hook/release file
(.github/workflows/review-hook.yml, mechanically checked by
scripts/release_verdict.py); once that PR is merged, THIS job is what
actually records the reviewed bytes into the cache (this is why it runs
post-merge, in regenerate.yml, and never in the PR-time review workflow
itself). It only ever appends — it never removes a hash and never
overwrites the whole list, so a hand-curated addition (e.g. from
backfill_codehashes.py) is preserved.

Best-effort and non-blocking by design: this runs unattended in CI after
every merge to main, so it must never fail the workflow because an explorer
had a bad day (this repo has documented explorer flakiness, e.g. transient
robinhood blockscout 500s). Any fetch failure for any single member is
recorded as a warning and skipped; the script's `main()` always returns 0.

Usage:
  python3 scripts/update_codehash_index.py [--repo-root .] [--sleep 0.25] [--dry-run]
"""
import argparse
import glob
import json
import os
import time

import fetch_codehash

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SLEEP = 0.25


def find_pointer_members(root: str) -> list:
    """Every hooks/**/*.json with hook.release set, as (chain, address, ref)
    tuples, sorted by path for determinism. Unreadable/malformed files are
    silently skipped — scripts/validate.py's schema pass is what's supposed
    to catch those, not this job."""
    members = []
    for path in sorted(glob.glob(os.path.join(root, "hooks", "**", "*.json"), recursive=True)):
        try:
            with open(path) as f:
                data = json.load(f)
        except Exception:
            continue
        hook = data.get("hook", {})
        ref = hook.get("release")
        if not ref:
            continue
        chain = hook.get("chain")
        address = hook.get("address")
        if not chain or not address:
            continue
        members.append((chain, address, ref))
    return members


def _release_path(root: str, ref: str) -> str | None:
    if "/" not in ref:
        return None
    project, rid = ref.split("/", 1)
    return os.path.join(root, "releases", project, rid + ".json")


def update_index(root: str, fetch_code=None, sleep=None,
                  sleep_seconds: float = DEFAULT_SLEEP, dry_run: bool = False) -> dict:
    """Run the whole job against the checkout at `root`.

    `fetch_code(chain, address) -> "0x..." | None` is injectable for tests;
    production defaults to fetch_codehash.fetch_code (raises on failure,
    caught here). `sleep(seconds) -> None` is injectable for tests;
    production defaults to time.sleep.

    Returns a report dict: {"updated": [str, ...], "failed": [str, ...],
    "unchanged": int, "changed_refs": [str, ...]}.
    """
    if fetch_code is None:
        fetch_code = fetch_codehash.fetch_code
    if sleep is None:
        sleep = time.sleep

    members = find_pointer_members(root)

    # Load each distinct release once, mutate in memory, write once per
    # changed release at the end (a release can have many members).
    releases: dict[str, dict] = {}
    release_paths: dict[str, str] = {}
    for _, _, ref in members:
        if ref in releases:
            continue
        path = _release_path(root, ref)
        if path is None or not os.path.exists(path):
            continue
        with open(path) as f:
            releases[ref] = json.load(f)
        release_paths[ref] = path

    updated = []
    failed = []
    changed_refs = set()
    unchanged = 0

    for chain, address, ref in members:
        release = releases.get(ref)
        if release is None:
            # Release file doesn't exist on this checkout (e.g. a dangling
            # pointer) — nothing to index. validate.py's tree-wide pass is
            # what catches dangling pointers; this job just skips them.
            continue

        known = set(release.get("source", {}).get("codeHashes") or [])

        try:
            code = fetch_code(chain, address)
            code_hash = fetch_codehash.codehash_of(code)
        except Exception as e:
            failed.append(f"{chain}:{address} -> {ref}: {e}")
            sleep(sleep_seconds)
            continue

        if code_hash is None:
            failed.append(f"{chain}:{address} -> {ref}: empty code")
            sleep(sleep_seconds)
            continue

        if code_hash in known:
            unchanged += 1
            sleep(sleep_seconds)
            continue

        known.add(code_hash)
        release.setdefault("source", {})["codeHashes"] = sorted(known)
        changed_refs.add(ref)
        updated.append(f"{chain}:{address} -> {ref}: +{code_hash}")
        sleep(sleep_seconds)

    if not dry_run:
        for ref in changed_refs:
            path = release_paths[ref]
            with open(path, "w") as f:
                json.dump(releases[ref], f, indent=2)
                f.write("\n")

    return {
        "updated": updated,
        "failed": failed,
        "unchanged": unchanged,
        "changed_refs": sorted(changed_refs),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=REPO_ROOT)
    ap.add_argument("--sleep", type=float, default=DEFAULT_SLEEP,
                     help="politeness delay between live fetches (seconds)")
    ap.add_argument("--dry-run", action="store_true",
                     help="report only, do not write release files")
    args = ap.parse_args()

    report = update_index(args.repo_root, sleep_seconds=args.sleep, dry_run=args.dry_run)

    for line in report["updated"]:
        print(f"UPDATED: {line}")
    for line in report["failed"]:
        print(f"::warning::codehash index fetch failed for {line}")
    print(f"Summary: {len(report['updated'])} hash(es) added across {len(report['changed_refs'])} "
          f"release(s), {report['unchanged']} already current, {len(report['failed'])} fetch failure(s).")

    # Best-effort job: never fail the workflow, even if every fetch failed.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
