#!/usr/bin/env python3
"""Compute the codehash verdict for a single hook file's release pointer.

Extracted from the "Verify release codehashes" step of
.github/workflows/review-hook.yml (was previously inlined Python in the
workflow YAML) so the logic is unit-testable and carries an explicit ref
guard against path traversal via a malicious hook.release value.

Usage:
  python3 scripts/release_verdict.py --hook-file <path-in-pr-checkout> \\
      --trusted-root trusted --pr-root . --out <verdict.json> [--sleep 0.3]

For each changed hook file that carries hook.release, this fetches the
hook's live runtime bytecode fingerprint and compares it against the
pointed-to release's source.codeHashes REVIEW CACHE — a machine-maintained
allowlist of bytes a human has already reviewed as members of the release —
AS IT EXISTS ON THE TRUSTED (base-branch) CHECKOUT, never the PR's own
version of the release (a PR could otherwise append its own hash to the
cache and manufacture a "match").

The cache is a matcher for "have we reviewed this exact artifact before", not
a validator of the release's own analysis — a cache hit for an `upgradeable`
release says nothing about current behavior (see match-upgradeable below).

Verdicts:
  match             — the runtime bytecode matches a reviewed member hash,
                       and the release is NOT upgradeable. Artifact identity
                       is settled; this does not itself validate the
                       release's analysis.
  match-upgradeable — the runtime bytecode matches a reviewed member hash,
                       but the release IS upgradeable — byte-identity says
                       nothing about current behavior for a storage-
                       dependent implementation. Never collapsed into
                       `match`.
  no-cached-review  — nothing negative: there is a codeHashes cache on
                       trusted but this hash isn't in it. Carries a
                       best-effort evidence bundle (codeLen, nearestMemberLen,
                       diffRuns) to help a human reviewer judge whether this
                       looks like an immutables-configuration variant of the
                       same template or genuinely different code.
  no-list           — the release has no codeHashes yet on trusted (e.g.
                       it's being created by this same PR) — no mechanical
                       check possible.
  fetch-failed      — the codehash fetch failed (both strategies) — never
                       treated as evidence either way (documented explorer
                       flakiness).
  invalid-ref       — hook.release failed the ref-pattern guard, or the
                       release path it names would resolve outside
                       <root>/releases/ (path traversal). Treated the same
                       as no-cached-review by the review prompt:
                       REQUEST_CHANGES, always.

A fetch failure never raises — it's recorded as fetch-failed (or as a null
evidence field) for the reviewer to weigh, same as before.
"""
import argparse
import json
import os
import re
import time

import fetch_codehash

# Release ref must be exactly "<project>/<id>", both lowercase, before ANY
# path construction happens. This is the primary path-traversal guard: a
# ref like "../../x/y" or "/etc/passwd" or an uppercase segment never
# matches and is rejected as invalid-ref without ever touching the
# filesystem.
REF_PATTERN = re.compile(r"^[a-z0-9-]+/[a-z0-9.-]+$")

# Output schema is uniform across all verdicts (evidence fields are
# populated, best-effort, only for no-cached-review; null elsewhere).
_EMPTY_EVIDENCE = {"codeLen": None, "nearestMemberLen": None, "diffRuns": None}


def _invalid_ref_verdict(address, chain, ref) -> dict:
    return {
        "address": address, "chain": chain, "release": ref,
        "verdict": "invalid-ref", "codeHash": None,
        "knownHashes": 0, **_EMPTY_EVIDENCE,
    }


def _release_path_within_root(root: str, project: str, rid: str) -> str | None:
    """Join <root>/releases/<project>/<id>.json and confirm the resolved
    path is actually contained within <root>. Returns the resolved
    (realpath'd) path, or None if it would escape root.

    Belt-and-braces beyond the REF_PATTERN guard above — catches anything
    the regex alone might miss (e.g. a symlink planted inside the
    checkout).
    """
    root_real = os.path.realpath(root)
    candidate = os.path.join(root, "releases", project, rid + ".json")
    candidate_real = os.path.realpath(candidate)
    if os.path.commonpath([candidate_real, root_real]) != root_real:
        return None
    return candidate_real


def _load_release(path: str) -> dict | None:
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def _default_fetch(chain: str, address: str) -> str | None:
    """Default fetch: live bytecode fingerprint via fetch_codehash's library
    functions. Returns None on any failure (including EMPTY code) — never
    raises."""
    try:
        code = fetch_codehash.fetch_code(chain, address)
    except Exception:
        return None
    return fetch_codehash.codehash_of(code)


def _default_fetch_code(chain: str, address: str) -> str | None:
    """Default raw-code fetch (hex '0x...'), used only to build the
    no-cached-review evidence bundle. Returns None on any failure — never
    raises."""
    try:
        return fetch_codehash.fetch_code(chain, address)
    except Exception:
        return None


def _byte_len(code_hex: str | None) -> int | None:
    if not code_hex:
        return None
    hexpart = code_hex[2:] if code_hex.startswith(("0x", "0X")) else code_hex
    if hexpart == "":
        return 0
    try:
        return len(hexpart) // 2
    except Exception:
        return None


def _diff_runs(a_hex: str, b_hex: str) -> int | None:
    """Count contiguous differing byte runs between two same-length '0x...'
    code hex strings. Returns None if lengths differ or parsing fails —
    caller only invokes this when lengths are already known equal, but this
    stays defensive regardless."""
    try:
        a = bytes.fromhex(a_hex[2:] if a_hex.startswith(("0x", "0X")) else a_hex)
        b = bytes.fromhex(b_hex[2:] if b_hex.startswith(("0x", "0X")) else b_hex)
    except Exception:
        return None
    if len(a) != len(b):
        return None
    runs = 0
    in_run = False
    for x, y in zip(a, b):
        if x != y:
            if not in_run:
                runs += 1
            in_run = True
        else:
            in_run = False
    return runs


def _find_first_other_member(pr_root: str, ref: str, exclude_chain, exclude_address):
    """Walk <pr_root>/hooks/ (sorted, deterministic) for the first hook file
    other than (exclude_chain, exclude_address) whose hook.release equals
    ref. Returns (chain, address) or None. Best-effort: any unreadable/
    malformed file is silently skipped."""
    hooks_dir = os.path.join(pr_root, "hooks")
    if not os.path.isdir(hooks_dir):
        return None
    matches = []
    for root, dirs, files in os.walk(hooks_dir):
        dirs.sort()
        for fname in sorted(files):
            if not fname.endswith(".json"):
                continue
            path = os.path.join(root, fname)
            try:
                with open(path) as f:
                    data = json.load(f)
            except Exception:
                continue
            hook = data.get("hook", {})
            if hook.get("release") != ref:
                continue
            addr = str(hook.get("address", "")).lower()
            chain = hook.get("chain")
            if chain == exclude_chain and addr == exclude_address:
                continue
            matches.append((path, chain, addr))
    if not matches:
        return None
    matches.sort(key=lambda m: m[0])
    _, chain, addr = matches[0]
    return chain, addr


def compute_verdict(hook_data: dict, trusted_root: str, pr_root: str, fetch=None, fetch_code=None) -> dict:
    """Compute the codehash verdict for one hook file's release pointer.

    `hook_data` is the parsed hook JSON (caller is expected to have already
    filtered out files with no hook.release — see main()).
    `fetch(chain, address) -> "sha256:..." | None` is injectable for tests;
    production defaults to a live bytecode fetch via fetch_codehash.
    `fetch_code(chain, address) -> "0x..." | None` is a separate injectable
    used only to build the no-cached-review evidence bundle (codeLen /
    nearestMemberLen / diffRuns); production defaults to the same live
    bytecode fetch.
    """
    if fetch is None:
        fetch = _default_fetch
    if fetch_code is None:
        fetch_code = _default_fetch_code

    hook = hook_data.get("hook", {})
    ref = hook.get("release")
    chain = hook.get("chain")
    address = hook.get("address")

    if not ref or not REF_PATTERN.fullmatch(ref):
        return _invalid_ref_verdict(address, chain, ref)

    project, rid = ref.split("/", 1)

    trusted_path = _release_path_within_root(trusted_root, project, rid)
    if trusted_path is None:
        return _invalid_ref_verdict(address, chain, ref)

    # Verdict is always computed against the TRUSTED (base-branch) release's
    # codeHashes review cache, never the PR's own version — see module
    # docstring.
    trusted_release = _load_release(trusted_path)
    known = trusted_release.get("source", {}).get("codeHashes") if trusted_release else None
    upgradeable = bool((trusted_release or {}).get("properties", {}).get("upgradeable"))

    try:
        code_hash = fetch(chain, address)
    except Exception:
        code_hash = None

    if code_hash is None:
        verdict = "fetch-failed"
    elif known is None:
        verdict = "no-list"
    elif code_hash in known:
        verdict = "match-upgradeable" if upgradeable else "match"
    else:
        verdict = "no-cached-review"

    evidence = dict(_EMPTY_EVIDENCE)
    if verdict == "no-cached-review":
        try:
            cur_code_hex = fetch_code(chain, address)
        except Exception:
            cur_code_hex = None
        evidence["codeLen"] = _byte_len(cur_code_hex)

        if cur_code_hex:
            member = _find_first_other_member(pr_root, ref, chain,
                                               str(address or "").lower())
            if member is not None:
                m_chain, m_address = member
                try:
                    member_code_hex = fetch_code(m_chain, m_address)
                except Exception:
                    member_code_hex = None
                evidence["nearestMemberLen"] = _byte_len(member_code_hex)
                if member_code_hex and evidence["codeLen"] == evidence["nearestMemberLen"]:
                    evidence["diffRuns"] = _diff_runs(cur_code_hex, member_code_hex)

    return {
        "address": address,
        "chain": chain,
        "release": ref,
        "verdict": verdict,
        "codeHash": code_hash,
        "knownHashes": len(known) if known else 0,
        **evidence,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hook-file", required=True, help="path to the hook JSON file, in the PR checkout")
    ap.add_argument("--trusted-root", required=True, help="root of the trusted (base branch) checkout")
    ap.add_argument("--pr-root", required=True, help="root of the PR (head) checkout")
    ap.add_argument("--out", required=True, help="path to write the verdict JSON to")
    ap.add_argument("--sleep", type=float, default=0.0,
                     help="politeness delay (seconds) after writing the verdict — a workflow "
                          "loop calling this once per changed hook passes e.g. --sleep 0.3 to "
                          "space out explorer/RPC calls across hooks in the same PR")
    args = ap.parse_args()

    with open(args.hook_file) as f:
        hook_data = json.load(f)

    verdict = compute_verdict(hook_data, args.trusted_root, args.pr_root)

    with open(args.out, "w") as f:
        json.dump(verdict, f, indent=2)
        f.write("\n")

    print(f"{verdict['address']}: {verdict['verdict']}")

    if args.sleep:
        time.sleep(args.sleep)


if __name__ == "__main__":
    main()
