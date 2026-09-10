#!/usr/bin/env python3
"""Enforce the release-lane pointer policy on hook file edits.

A PR that touches releases/ (the "release lane") is allowed to touch any
number of hooks/ files, unlike a plain hooks-only PR (capped at one file by
the diff-policy step in validate.yml). That wider blast radius needs its own
guard: every hooks/ file the PR ADDS or MODIFIES (deletions are exempt) must
be a release-pointer edit, not an arbitrary semantic edit smuggled in
alongside a release change.

A changed hook file passes when either:

  (a) it carries a hook.release ref, and the release file that ref names
      (releases/<project>/<id>.json) is itself among the files this PR
      changed; or

  (b) it is a "pure pointer addition" relative to the trusted (base-branch)
      checkout: the file already exists there, and the only difference
      between the PR's version and the trusted version is the addition of
      the hook.release key (any other field changing, added, or removed
      fails this case, even a same-value rewrite of an existing field).

Case (b) is what lets a hook file be pointed at a release that already
exists on trusted and is NOT touched by this PR (e.g. a backfill PR that
only adds `"release": "..."` to pre-existing hook files and touches no
releases/ files at all). Case (a) is what lets a brand-new hook file be
added in the same PR that creates the release it points to, including one
that also carries per-instance enrichment (deployer, description, ...)
alongside the pointer — that enrichment is exactly what makes it not a
"pure pointer addition" over trusted (there is no trusted version at all,
or the diff is more than just the release key), so it must satisfy (a).

This check is deliberately narrow: it does not re-validate schema, resolve
release refs against the filesystem, or otherwise duplicate validate.py. It
only asks "was this edit shaped like a release-pointer edit". A malformed
`hook.release` value can never cause a filesystem access here — case (a) is
a pure string/set-membership comparison against the PR's own declared
changed-files list, and case (b) only ever opens paths GitHub itself
reported as changed (never anything derived from the ref).
"""
import argparse
import copy
import json
import os
import sys


def _release_path_for_ref(ref: str) -> str:
    return f"releases/{ref}.json"


def _pure_pointer_addition(pr_data: dict, trusted_data: dict) -> bool:
    """True iff pr_data equals trusted_data except for an added hook.release."""
    pr_copy = copy.deepcopy(pr_data)
    pr_hook = pr_copy.get("hook")
    if isinstance(pr_hook, dict) and "release" in pr_hook:
        del pr_hook["release"]
    return pr_copy == trusted_data


def check(changed_hooks: list, changed_releases: list, pr_root: str, trusted_root: str) -> list[str]:
    """Return a list of violation strings; empty means the lane policy passed.

    `changed_hooks` — hooks/ paths this PR added or modified (deletions
    already excluded by the caller). `changed_releases` — releases/ paths
    that appear anywhere in this PR's changed-files list (any status).
    """
    changed_releases_set = set(changed_releases)
    violations = []

    for hook_path in changed_hooks:
        pr_full = os.path.join(pr_root, hook_path)
        try:
            with open(pr_full) as f:
                pr_data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            violations.append(f"{hook_path}: could not read PR file: {e}")
            continue

        hook = pr_data.get("hook") if isinstance(pr_data, dict) else None
        ref = hook.get("release") if isinstance(hook, dict) else None

        case_a = bool(ref) and _release_path_for_ref(ref) in changed_releases_set

        case_b = False
        trusted_full = os.path.join(trusted_root, hook_path)
        if os.path.exists(trusted_full):
            try:
                with open(trusted_full) as f:
                    trusted_data = json.load(f)
            except (OSError, json.JSONDecodeError):
                trusted_data = None
            if trusted_data is not None:
                case_b = _pure_pointer_addition(pr_data, trusted_data)

        if not (case_a or case_b):
            if ref:
                violations.append(
                    f"{hook_path}: hook.release={ref!r} does not name a release changed in "
                    "this PR, and this file is not a pure pointer addition over the trusted "
                    "checkout"
                )
            else:
                violations.append(
                    f"{hook_path}: added/modified in a release-lane PR without a hook.release "
                    "pointer, and is not a pure pointer addition over the trusted checkout"
                )

    return violations


def _read_lines(path: str) -> list:
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [line.strip() for line in f if line.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pr-root", required=True)
    ap.add_argument("--trusted-root", required=True)
    ap.add_argument("--changed-hooks-file", required=True,
                     help="newline-separated hooks/ paths added or modified by this PR")
    ap.add_argument("--changed-releases-file", required=True,
                     help="newline-separated releases/ paths appearing anywhere in this PR's diff")
    args = ap.parse_args()

    changed_hooks = _read_lines(args.changed_hooks_file)
    changed_releases = _read_lines(args.changed_releases_file)

    violations = check(changed_hooks, changed_releases, args.pr_root, args.trusted_root)

    if violations:
        for v in violations:
            print(f"::error::{v}")
        sys.exit(1)

    print(f"Release-lane pointer policy OK for {len(changed_hooks)} changed hook file(s).")


if __name__ == "__main__":
    main()
