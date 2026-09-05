#!/usr/bin/env python3
"""Validate hook files and release files.

Usage:
  python3 scripts/validate.py                       # validate all hooks + releases
  python3 scripts/validate.py <file> [<file> ...]   # validate specific files
"""
import json
import glob
import os
import sys

import jsonschema

_SCHEMAS: dict[tuple[str, str], dict] = {}
_CHAINS: dict[str, dict] = {}
THIN_FORBIDDEN_HOOK_FIELDS = ("name", "verifiedSource", "auditUrl")
FULL_HOOK_REQUIRED = ("address", "chain", "chainId", "name", "verifiedSource")
SWAP_FLAG_NAMES = ("beforeSwap", "afterSwap", "beforeSwapReturnsDelta", "afterSwapReturnsDelta")


def _schema(repo_root: str, name: str, fallback_root: str | None = None) -> dict:
    key = (repo_root, name)
    if key not in _SCHEMAS:
        path = os.path.join(repo_root, name)
        # The fallback to a sibling (e.g. PR) checkout only applies during
        # the bootstrap window before a schema file has landed on the trusted
        # base branch yet. Gated behind an explicit env var so a merged
        # branch can't silently mask a genuinely missing schema at repo_root.
        if not os.path.exists(path) and fallback_root and os.environ.get("HOOKLIST_SCHEMA_FALLBACK"):
            path = os.path.join(fallback_root, name)
        with open(path) as f:
            _SCHEMAS[key] = json.load(f)
    return _SCHEMAS[key]


def _load_chains(root: str) -> dict:
    if root not in _CHAINS:
        with open(os.path.join(root, "chains.json")) as f:
            _CHAINS[root] = json.load(f)
    return _CHAINS[root]


def _load_chains_with_root(repo_root: str, file_root: str | None) -> dict:
    """Resolve chains.json against file_root first (if given), then repo_root."""
    if file_root is not None and os.path.exists(os.path.join(file_root, "chains.json")):
        return _load_chains(file_root)
    return _load_chains(repo_root)


def coherence_issues(address: str, properties: dict) -> list[str]:
    """Flags derive from the address; properties must not contradict them."""
    import verify_flags
    flags = verify_flags.decode_flags(address)
    issues = []
    if (flags["beforeSwapReturnsDelta"] or flags["afterSwapReturnsDelta"]) \
            and properties.get("vanillaSwap") is True:
        issues.append("vanillaSwap true but a swap returns-delta flag is set")
    if not any(flags[n] for n in SWAP_FLAG_NAMES):
        if properties.get("vanillaSwap") is False:
            issues.append("vanillaSwap false but no swap flags are set")
        if properties.get("swapAccess") not in (None, "none"):
            issues.append("swapAccess restricted but no swap flags are set")
    return issues


def chain_issues(chain, chain_id, repo_root: str, file_root: str | None = None) -> list[str]:
    """Cross-check hook.chain/hook.chainId against chains.json."""
    chains = _load_chains_with_root(repo_root, file_root)
    if chain not in chains:
        return [f"unknown chain: {chain!r}"]
    expected = chains[chain]["chainId"]
    if chain_id != expected:
        return [f"chainId {chain_id!r} does not match chains.json ({expected!r}) for chain {chain!r}"]
    return []


def _filename_address_mismatch(filepath: str, address: str) -> str | None:
    """Filename stem (without .json) must equal `address` case-insensitively.

    Returns a human-readable issue string, or None if filepath doesn't look
    like a real path (e.g. a test label) or the stem matches.
    """
    if not filepath or not filepath.endswith(".json"):
        return None
    stem = os.path.splitext(os.path.basename(filepath))[0]
    if stem.lower() == address.lower():
        return None
    return f"filename must match hook.address case-insensitively: filename stem {stem!r} vs address {address!r}"


def legacy_semantic_warnings(data: dict, repo_root: str, file_root: str | None = None,
                              filepath: str | None = None) -> list[str]:
    """Coherence + chain/chainId + filename checks for legacy pointer-less full hook files.

    These rules post-date a number of already-published hook files, so
    violations here are surfaced as non-fatal warnings (see main()) rather
    than validation failures. Pointer-carrying files (thin or full+pointer)
    are NOT covered here — their coherence/chain/filename issues are
    enforced as hard errors inside check_hook_data.
    """
    hook = data.get("hook", {})
    if hook.get("release") is not None:
        return []
    if "properties" not in data:
        return []
    issues = []
    if "address" in hook:
        issues.extend(coherence_issues(hook["address"], data["properties"]))
        mismatch = _filename_address_mismatch(filepath, hook["address"])
        if mismatch:
            issues.append(mismatch)
    chain = hook.get("chain")
    chain_id = hook.get("chainId")
    if chain is not None and chain_id is not None:
        issues.extend(chain_issues(chain, chain_id, repo_root, file_root))
    return issues


def checkout_root(filepath: str) -> str | None:
    """Find the checkout root that contains the given file.

    Walks up from filepath's directory looking for the nearest ancestor that
    has a hooks/ or releases/ directory. Returns None if none is found.

    This lets CI resolve release refs and schemas against the PR checkout
    that the file actually lives in, rather than only the trusted (base
    branch) checkout the validation scripts run from — see validate_file.
    """
    d = os.path.dirname(os.path.abspath(filepath))
    while True:
        if os.path.isdir(os.path.join(d, "hooks")) or os.path.isdir(os.path.join(d, "releases")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def load_release(repo_root: str, ref: str) -> dict | None:
    try:
        project, rid = ref.split("/", 1)
    except ValueError:
        return None
    path = os.path.join(repo_root, "releases", project, rid + ".json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def _load_release_with_root(repo_root: str, ref: str, file_root: str | None) -> dict | None:
    """Resolve a release ref against the file's own checkout, if one resolves.

    When `file_root` is given (checkout_root found a hooks/ or releases/
    ancestor for this file), that checkout is AUTHORITATIVE — no fallback to
    repo_root. A release ref that doesn't resolve within the file's own
    checkout is an error even when the release happens to exist at
    repo_root (e.g. a PR that deletes a release file while some other file
    in that same PR tree still points at it must fail here, not silently
    resolve against the trusted base-branch checkout).

    Only when file_root is None (no ancestor checkout could be found at all)
    do we fall back to resolving against repo_root.
    """
    if file_root is not None:
        return load_release(file_root, ref)
    return load_release(repo_root, ref)


def _check_release_data(filepath: str, data: dict, repo_root: str, file_root: str | None = None) -> list[str]:
    errors = []
    try:
        jsonschema.validate(data, _schema(repo_root, "release.schema.json", fallback_root=file_root))
    except jsonschema.ValidationError as e:
        path = ".".join(str(p) for p in e.path) or "<root>"
        return [f"{filepath}: {path}: {e.message}"]
    expected = os.path.join("releases", data["project"], data["id"] + ".json")
    if not filepath.replace(os.sep, "/").endswith(expected.replace(os.sep, "/")):
        errors.append(f"{filepath}: path must be {expected} (project/id mismatch)")
    sup = data["lifecycle"]["supersedes"]
    if sup and _load_release_with_root(repo_root, sup, file_root) is None:
        errors.append(f"{filepath}: lifecycle.supersedes does not resolve: {sup}")

    code_hashes = data.get("source", {}).get("codeHashes")
    if code_hashes is not None:
        if code_hashes != sorted(code_hashes):
            errors.append(f"{filepath}: source.codeHashes must be sorted")
        elif len(code_hashes) != len(set(code_hashes)):
            errors.append(f"{filepath}: source.codeHashes must be unique")

    return errors


def check_hook_data(data: dict, repo_root: str, label: str = "<data>", file_root: str | None = None) -> list[str]:
    """Schema + form rules for a hook file's contents."""
    try:
        jsonschema.validate(data, _schema(repo_root, "schema.json", fallback_root=file_root))
    except jsonschema.ValidationError as e:
        path = ".".join(str(p) for p in e.path) or "<root>"
        return [f"{label}: {path}: {e.message}"]

    errors = []
    hook = data.get("hook", {})
    ref = hook.get("release")

    if ref is None:
        for field in FULL_HOOK_REQUIRED:
            if field not in hook:
                errors.append(f"{label}: hook.{field} required without a release pointer")
        for section in ("flags", "properties"):
            if section not in data:
                errors.append(f"{label}: {section} required without a release pointer")
        # Legacy pointer-less full files: coherence + chain/chainId issues
        # are non-fatal here — see legacy_semantic_warnings(), surfaced by
        # main() as WARN: lines. Many pre-existing files predate these rules
        # and need human review, not a CI break.
        return errors

    release = _load_release_with_root(repo_root, ref, file_root)
    if release is None:
        errors.append(f"{label}: hook.release does not resolve: {ref}")
        return errors

    if "address" in hook:
        mismatch = _filename_address_mismatch(label, hook["address"])
        if mismatch:
            errors.append(f"{label}: {mismatch}")

    if "properties" in data:
        # full + pointer: complete file whose properties must agree with the release
        for field in FULL_HOOK_REQUIRED:
            if field not in hook:
                errors.append(f"{label}: hook.{field} required on full files")
        if "flags" not in data:
            errors.append(f"{label}: flags required on full files")
        if data["properties"] != release["properties"]:
            errors.append(f"{label}: properties differ from release {ref}")
        if "address" in hook:
            for issue in coherence_issues(hook["address"], data["properties"]):
                errors.append(f"{label}: {issue}")
    else:
        # thin: only per-instance facts allowed
        for field in THIN_FORBIDDEN_HOOK_FIELDS:
            if field in hook:
                errors.append(f"{label}: hook.{field} not permitted on thin files")
        if "flags" in data:
            errors.append(f"{label}: flags not permitted on thin files")
        if "address" in hook:
            for issue in coherence_issues(hook["address"], release["properties"]):
                errors.append(f"{label}: {issue}")

    chain = hook.get("chain")
    chain_id = hook.get("chainId")
    if chain is not None and chain_id is not None:
        for issue in chain_issues(chain, chain_id, repo_root, file_root):
            errors.append(f"{label}: {issue}")

    return errors


def _is_release_path(filepath: str) -> bool:
    """True when filepath's parent-of-parent directory is exactly 'releases'.

    Routes on path segments rather than repo_root-relativity or a naive
    substring check, since CI validates files from a sibling checkout (e.g.
    trusted/scripts/validate.py operating on pr/releases/<project>/<id>.json)
    where repo_root and the file don't share a root, and some checkout paths
    (e.g. a worktree directory literally named "...-releases") contain
    "releases" as a substring without being a releases/ directory.
    """
    parts = [p for p in filepath.replace(os.sep, "/").split("/") if p]
    return len(parts) >= 3 and parts[-3] == "releases"


def validate_file(filepath: str, repo_root: str) -> list[str]:
    with open(filepath) as f:
        data = json.load(f)
    file_root = checkout_root(filepath)
    if _is_release_path(filepath):
        return _check_release_data(filepath, data, repo_root, file_root=file_root)
    return check_hook_data(data, repo_root, label=filepath, file_root=file_root)


def main():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if len(sys.argv) > 1:
        files = sys.argv[1:]
    else:
        files = glob.glob(os.path.join(repo_root, "hooks", "**", "*.json"), recursive=True)
        files += glob.glob(os.path.join(repo_root, "releases", "*", "*.json"))

    if not files:
        print("No files to validate.")
        return

    errors = []
    warnings = []
    for filepath in files:
        errs = validate_file(filepath, repo_root)
        if errs:
            errors.extend(errs)
            print(f"FAIL: {filepath}")
            for e in errs:
                print(f"  {e}")
        else:
            print(f"  OK: {filepath}")

        if not errs and not _is_release_path(filepath):
            with open(filepath) as f:
                data = json.load(f)
            file_root = checkout_root(filepath)
            for w in legacy_semantic_warnings(data, repo_root, file_root, filepath=filepath):
                warnings.append(f"{filepath}: {w}")

    if warnings:
        print(f"\n{len(warnings)} legacy coherence warning(s) (non-fatal):")
        for w in warnings:
            print(f"WARN: {w}")

    if errors:
        print(f"\n{len(errors)} validation error(s)")
        sys.exit(1)
    print(f"\nAll {len(files)} file(s) valid.")


if __name__ == "__main__":
    main()
