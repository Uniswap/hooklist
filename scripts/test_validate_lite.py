# scripts/test_validate_lite.py
import json
import os
import validate
import verify_flags


def repo_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def write(tmp_path, rel, obj):
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj))
    return str(p)


RELEASE = {
    "project": "zora", "id": "creator-hook-2.2.1", "version": "2.2.1",
    "name": "Zora Creator Hook v2.2.1", "description": "d",
    "source": {"verified": True},
    "properties": {"dynamicFee": True, "upgradeable": False,
                   "requiresCustomSwapData": False, "vanillaSwap": False,
                   "swapAccess": "none"},
    "warnings": [],
    "lifecycle": {"status": "active", "supersedes": None},
}

THIN = {"hook": {"address": "0x" + "a" * 36 + "20c0", "chain": "base",
                 "chainId": 8453, "release": "zora/creator-hook-2.2.1",
                 "description": "Fee: 35 bps."}}

FULL = {
    "hook": {"address": "0x" + "b" * 36 + "20c0", "chain": "base", "chainId": 8453,
             "name": "Zora Creator Hook v2.2.1 (Base)", "description": "legacy text",
             "deployer": "", "verifiedSource": True, "auditUrl": ""},
    "flags": verify_flags.decode_flags("0x" + "b" * 36 + "20c0"),
    "properties": RELEASE["properties"],
}


def setup_repo(tmp_path):
    write(tmp_path, "releases/zora/creator-hook-2.2.1.json", RELEASE)
    for name in ("schema.json", "release.schema.json", "chains.json"):
        (tmp_path / name).write_text(open(os.path.join(repo_root(), name)).read())
    return str(tmp_path)


def test_release_file_valid(tmp_path):
    root = setup_repo(tmp_path)
    p = os.path.join(root, "releases", "zora", "creator-hook-2.2.1.json")
    assert validate.validate_file(p, root) == []


def test_release_path_must_match_ids(tmp_path):
    root = setup_repo(tmp_path)
    p = write(tmp_path, "releases/zora/wrong-name.json", RELEASE)
    assert any("path" in e for e in validate.validate_file(p, root))


def test_thin_instance_valid(tmp_path):
    root = setup_repo(tmp_path)
    p = write(tmp_path, f"hooks/base/{THIN['hook']['address']}.json", THIN)
    assert validate.validate_file(p, root) == []


def test_thin_with_forbidden_field_invalid(tmp_path):
    root = setup_repo(tmp_path)
    bad = {"hook": dict(THIN["hook"], name="Nope")}
    p = write(tmp_path, "hooks/base/bad.json", bad)
    assert any("thin" in e for e in validate.validate_file(p, root))


def test_thin_with_verified_source_field_invalid(tmp_path):
    root = setup_repo(tmp_path)
    bad = {"hook": dict(THIN["hook"], verifiedSource=True)}
    p = write(tmp_path, "hooks/base/bad_thin_vs.json", bad)
    errs = validate.validate_file(p, root)
    assert any("thin" in e for e in errs), errs


def test_thin_with_audit_url_field_invalid(tmp_path):
    root = setup_repo(tmp_path)
    bad = {"hook": dict(THIN["hook"], auditUrl="https://example.com/audit")}
    p = write(tmp_path, "hooks/base/bad_thin_audit.json", bad)
    errs = validate.validate_file(p, root)
    assert any("thin" in e for e in errs), errs


def test_thin_with_top_level_flags_invalid(tmp_path):
    root = setup_repo(tmp_path)
    bad = {"hook": dict(THIN["hook"]),
           "flags": verify_flags.decode_flags(THIN["hook"]["address"])}
    p = write(tmp_path, "hooks/base/bad_thin_flags.json", bad)
    errs = validate.validate_file(p, root)
    assert any("thin" in e for e in errs), errs


def test_pointer_must_resolve(tmp_path):
    root = setup_repo(tmp_path)
    bad = {"hook": dict(THIN["hook"], release="zora/nope-1.0")}
    p = write(tmp_path, "hooks/base/bad2.json", bad)
    assert any("resolve" in e for e in validate.validate_file(p, root))


def test_full_plus_pointer_properties_must_match(tmp_path):
    root = setup_repo(tmp_path)
    ok = {"hook": dict(FULL["hook"], release="zora/creator-hook-2.2.1"),
          "flags": FULL["flags"], "properties": dict(FULL["properties"])}
    p = write(tmp_path, f"hooks/base/{FULL['hook']['address']}.json", ok)
    assert validate.validate_file(p, root) == []
    bad = {"hook": dict(FULL["hook"], release="zora/creator-hook-2.2.1"),
           "flags": FULL["flags"],
           "properties": dict(FULL["properties"], dynamicFee=False)}
    p2 = write(tmp_path, "hooks/base/fullptr2.json", bad)
    assert any("properties" in e for e in validate.validate_file(p2, root))


def test_full_plus_pointer_missing_name_is_error(tmp_path):
    root = setup_repo(tmp_path)
    hook = dict(FULL["hook"], release="zora/creator-hook-2.2.1")
    del hook["name"]
    bad = {"hook": hook, "flags": FULL["flags"], "properties": dict(FULL["properties"])}
    p = write(tmp_path, "hooks/base/fullptr_missing_name.json", bad)
    errs = validate.validate_file(p, root)
    assert any("hook.name required" in e for e in errs), errs


def test_full_plus_pointer_missing_verified_source_is_error(tmp_path):
    root = setup_repo(tmp_path)
    hook = dict(FULL["hook"], release="zora/creator-hook-2.2.1")
    del hook["verifiedSource"]
    bad = {"hook": hook, "flags": FULL["flags"], "properties": dict(FULL["properties"])}
    p = write(tmp_path, "hooks/base/fullptr_missing_verifiedsource.json", bad)
    errs = validate.validate_file(p, root)
    assert any("hook.verifiedSource required" in e for e in errs), errs


def test_full_plus_pointer_missing_flags_is_error(tmp_path):
    root = setup_repo(tmp_path)
    hook = dict(FULL["hook"], release="zora/creator-hook-2.2.1")
    bad = {"hook": hook, "properties": dict(FULL["properties"])}
    p = write(tmp_path, "hooks/base/fullptr_missing_flags.json", bad)
    errs = validate.validate_file(p, root)
    assert any("flags required on full files" in e for e in errs), errs


def test_no_pointer_requires_full_form(tmp_path):
    root = setup_repo(tmp_path)
    bad = {"hook": {"address": "0x" + "c" * 40, "chain": "base", "chainId": 8453}}
    p = write(tmp_path, "hooks/base/bad3.json", bad)
    assert validate.validate_file(p, root) != []


def test_legacy_full_file_still_valid(tmp_path):
    # A synthetic fixture, not a live repo file: hooks/**/*.json get
    # backfilled with release pointers over time (see draft_releases.py),
    # so pinning this to "whatever the first real hooks/celo file happens
    # to be today" is not durable.
    root = setup_repo(tmp_path)
    hook = {
        "hook": {"address": "0x" + "d" * 40, "chain": "celo", "chainId": 42220,
                 "name": "Legacy Hook", "description": "d", "deployer": "",
                 "verifiedSource": True, "auditUrl": ""},
        "flags": verify_flags.decode_flags("0x" + "d" * 40),
        "properties": {"dynamicFee": False, "upgradeable": False,
                       "requiresCustomSwapData": False, "vanillaSwap": True,
                       "swapAccess": "none"},
    }
    p = write(tmp_path, "hooks/celo/x.json", hook)
    assert validate.validate_file(p, root) == []


def test_verify_flags_skips_thin(tmp_path):
    p = write(tmp_path, "hooks/base/thin2.json", THIN)
    assert verify_flags.verify_hook(p) == []


def test_release_routes_by_path_segments_across_checkouts(tmp_path):
    # Mirrors CI's dual-checkout: scripts run from a "trusted" checkout
    # (repo_root) while the file being validated lives in a sibling "pr"
    # checkout, so repo_root and filepath don't share a common root.
    trusted = tmp_path / "trusted"
    trusted.mkdir()
    for name in ("schema.json", "release.schema.json"):
        (trusted / name).write_text(open(os.path.join(repo_root(), name)).read())
    pr = tmp_path / "pr"
    p = write(pr, "releases/zora/creator-hook-2.2.1.json", RELEASE)
    assert validate.validate_file(p, str(trusted)) == []


def test_hook_path_containing_releases_substring_not_misrouted(tmp_path):
    # A directory literally named "...-releases" must not be mistaken for a
    # releases/ directory (this bit a worktree named "hooklist-v1-releases").
    # Uses a pointer-less full hook (not THIN) so the test isolates path-
    # segment routing (_is_release_path) rather than release-ref resolution:
    # "my-releases/hooks/..." makes checkout_root() find "my-releases" itself
    # as the file's own checkout (it has a hooks/ child), which is a
    # different root than `root` — a pointer would need to resolve there,
    # which is not what this test is about.
    root = setup_repo(tmp_path)
    p = write(tmp_path, f"my-releases/hooks/base/{FULL['hook']['address']}.json", FULL)
    assert validate.validate_file(p, root) == []


def test_checkout_root_finds_hooks_or_releases_ancestor(tmp_path):
    pr = tmp_path / "pr"
    write(pr, "releases/zora/creator-hook-2.2.1.json", RELEASE)
    write(pr, "hooks/base/thin.json", THIN)
    assert validate.checkout_root(str(pr / "releases" / "zora" / "creator-hook-2.2.1.json")) == str(pr)
    assert validate.checkout_root(str(pr / "hooks" / "base" / "thin.json")) == str(pr)
    assert validate.checkout_root(str(tmp_path / "nowhere" / "x.json")) is None


def test_dual_checkout_release_added_in_same_pr(tmp_path):
    # CI's dual-checkout with a release added in the same PR: trusted/ (base
    # branch, where the validation scripts run from) has never heard of the
    # release; it lives only in the PR checkout alongside the thin hook
    # instance that points at it. Both must still resolve against the file's
    # own checkout root, not just repo_root.
    trusted = tmp_path / "trusted"
    trusted.mkdir()
    for name in ("schema.json", "release.schema.json", "chains.json"):
        (trusted / name).write_text(open(os.path.join(repo_root(), name)).read())
    pr = tmp_path / "pr"
    release_path = write(pr, "releases/zora/creator-hook-2.2.1.json", RELEASE)
    thin_path = write(pr, f"hooks/base/{THIN['hook']['address']}.json", THIN)
    assert validate.validate_file(release_path, str(trusted)) == []
    assert validate.validate_file(thin_path, str(trusted)) == []


def test_release_deleted_in_pr_but_present_in_trusted_does_not_resolve(tmp_path):
    # Must-fix 2: a release ref must resolve within the file's OWN checkout.
    # A PR that deletes a release file while a member hook elsewhere in that
    # same PR tree still points at it must fail here — even though the
    # release still exists in the trusted (base branch) checkout — since
    # falling back to trusted would silently paper over the deletion.
    trusted = tmp_path / "trusted"
    trusted.mkdir()
    for name in ("schema.json", "release.schema.json", "chains.json"):
        (trusted / name).write_text(open(os.path.join(repo_root(), name)).read())
    write(trusted, "releases/zora/creator-hook-2.2.1.json", RELEASE)

    pr = tmp_path / "pr"
    # release file NOT present in pr/ — deleted by this PR
    thin_path = write(pr, f"hooks/base/{THIN['hook']['address']}.json", THIN)
    errs = validate.validate_file(thin_path, str(trusted))
    assert any("resolve" in e for e in errs), errs


def test_bootstrap_missing_release_schema_falls_back_to_pr_checkout(tmp_path, monkeypatch):
    # Before this branch merges, release.schema.json doesn't exist on the
    # base branch yet. A release file added in this same PR still validates
    # by falling back to the schema copy carried in its own checkout — but
    # only when CI opts in via HOOKLIST_SCHEMA_FALLBACK (see Fix A2/A7-M2);
    # outside that bootstrap window a missing schema at repo_root is a hard
    # error, not a silent fallback.
    monkeypatch.setenv("HOOKLIST_SCHEMA_FALLBACK", "1")
    trusted2 = tmp_path / "trusted2"
    trusted2.mkdir()
    (trusted2 / "schema.json").write_text(open(os.path.join(repo_root(), "schema.json")).read())
    pr = tmp_path / "pr"
    pr.mkdir()
    (pr / "release.schema.json").write_text(
        open(os.path.join(repo_root(), "release.schema.json")).read())
    release_path = write(pr, "releases/zora/creator-hook-2.2.1.json", RELEASE)
    assert validate.validate_file(release_path, str(trusted2)) == []


def test_bootstrap_missing_release_schema_without_fallback_env_is_hard_error(tmp_path):
    # Same setup as above, but without HOOKLIST_SCHEMA_FALLBACK set: a
    # missing schema at repo_root must be a hard error, not silently
    # resolved from the PR checkout.
    trusted2 = tmp_path / "trusted2"
    trusted2.mkdir()
    (trusted2 / "schema.json").write_text(open(os.path.join(repo_root(), "schema.json")).read())
    pr = tmp_path / "pr"
    pr.mkdir()
    (pr / "release.schema.json").write_text(
        open(os.path.join(repo_root(), "release.schema.json")).read())
    release_path = write(pr, "releases/zora/creator-hook-2.2.1.json", RELEASE)
    try:
        validate.validate_file(release_path, str(trusted2))
        assert False, "expected FileNotFoundError"
    except FileNotFoundError:
        pass


# --- Fix A5: flags/properties coherence -----------------------------------

RELEASE_VANILLA_RETURNS_DELTA = dict(
    RELEASE, id="vanilla-returns-delta-1.0",
    properties={"dynamicFee": False, "upgradeable": False,
                "requiresCustomSwapData": False, "vanillaSwap": True,
                "swapAccess": "none"},
)

RELEASE_RESTRICTED_NO_SWAP_FLAGS = dict(
    RELEASE, id="restricted-no-swap-1.0",
    properties={"dynamicFee": False, "upgradeable": False,
                "requiresCustomSwapData": False, "vanillaSwap": True,
                "swapAccess": "temporal"},
)


def test_coherence_returns_delta_with_vanilla_swap_is_error(tmp_path):
    root = setup_repo(tmp_path)
    write(tmp_path, "releases/zora/vanilla-returns-delta-1.0.json", RELEASE_VANILLA_RETURNS_DELTA)
    # suffix 0008 sets only bit 3 (beforeSwapReturnsDelta)
    thin = {"hook": {"address": "0x" + "e" * 36 + "0008", "chain": "base",
                     "chainId": 8453, "release": "zora/vanilla-returns-delta-1.0"}}
    p = write(tmp_path, "hooks/base/thin_returns_delta.json", thin)
    errs = validate.validate_file(p, root)
    assert any("returns-delta" in e for e in errs), errs


def test_coherence_restricted_swap_access_with_no_swap_flags_is_error(tmp_path):
    root = setup_repo(tmp_path)
    write(tmp_path, "releases/zora/restricted-no-swap-1.0.json", RELEASE_RESTRICTED_NO_SWAP_FLAGS)
    # suffix 0000 sets no bits at all: no swap flags
    thin = {"hook": {"address": "0x" + "f" * 36 + "0000", "chain": "base",
                     "chainId": 8453, "release": "zora/restricted-no-swap-1.0"}}
    p = write(tmp_path, "hooks/base/thin_restricted.json", thin)
    errs = validate.validate_file(p, root)
    assert any("swapAccess restricted" in e for e in errs), errs


RELEASE_VANILLA_FALSE_NO_SWAP_FLAGS = dict(
    RELEASE, id="vanilla-false-no-swap-1.0",
    properties={"dynamicFee": False, "upgradeable": False,
                "requiresCustomSwapData": False, "vanillaSwap": False,
                "swapAccess": "none"},
)


def test_coherence_vanilla_false_with_no_swap_flags_is_hard_error_on_pointer_file(tmp_path):
    # Mirrors test_coherence_restricted_swap_access_with_no_swap_flags_is_error
    # but for the OTHER half of coherence rule 2: vanillaSwap:false with no
    # swap flags set at all must also be a hard error on a pointer-carrying
    # file (it's only a non-fatal warning on legacy pointer-less files — see
    # test_legacy_pointerless_coherence_violation_is_warning_not_error).
    root = setup_repo(tmp_path)
    write(tmp_path, "releases/zora/vanilla-false-no-swap-1.0.json", RELEASE_VANILLA_FALSE_NO_SWAP_FLAGS)
    # suffix 2000 sets only bit 13 (beforeInitialize): no swap flags at all
    thin = {"hook": {"address": "0x" + "9" * 36 + "2000", "chain": "base",
                     "chainId": 8453, "release": "zora/vanilla-false-no-swap-1.0"}}
    p = write(tmp_path, "hooks/base/thin_vanilla_false_no_swap.json", thin)
    errs = validate.validate_file(p, root)
    assert any("vanillaSwap false but no swap flags are set" in e for e in errs), errs


def test_coherence_full_plus_pointer_checked_against_own_properties(tmp_path):
    root = setup_repo(tmp_path)
    write(tmp_path, "releases/zora/vanilla-returns-delta-1.0.json", RELEASE_VANILLA_RETURNS_DELTA)
    full = {
        "hook": {"address": "0x" + "e" * 36 + "0008", "chain": "base", "chainId": 8453,
                 "name": "N", "description": "d", "deployer": "", "verifiedSource": True,
                 "auditUrl": "", "release": "zora/vanilla-returns-delta-1.0"},
        "flags": verify_flags.decode_flags("0x" + "e" * 36 + "0008"),
        "properties": RELEASE_VANILLA_RETURNS_DELTA["properties"],
    }
    p = write(tmp_path, "hooks/base/fullptr_returns_delta.json", full)
    errs = validate.validate_file(p, root)
    assert any("returns-delta" in e for e in errs), errs


def test_legacy_pointerless_coherence_violation_is_warning_not_error(tmp_path):
    root = setup_repo(tmp_path)
    address = "0x" + "1" * 36 + "0000"  # no swap flags at all
    hook = {
        "hook": {"address": address, "chain": "celo", "chainId": 42220,
                 "name": "Legacy Bad Hook", "description": "d", "deployer": "",
                 "verifiedSource": True, "auditUrl": ""},
        "flags": verify_flags.decode_flags(address),
        "properties": {"dynamicFee": False, "upgradeable": False,
                       "requiresCustomSwapData": False, "vanillaSwap": False,
                       "swapAccess": "none"},
    }
    p = write(tmp_path, "hooks/celo/legacybad.json", hook)
    # non-fatal: validate_file does not fail the legacy pointer-less file
    assert validate.validate_file(p, root) == []
    warnings = validate.legacy_semantic_warnings(hook, root, file_root=validate.checkout_root(p))
    assert any("vanillaSwap false but no swap flags are set" in w for w in warnings), warnings


# --- Fix A7 M4: chain/chainId cross-check against chains.json -------------

def test_chain_mismatch_on_pointer_file_is_error(tmp_path):
    root = setup_repo(tmp_path)
    bad = {"hook": dict(THIN["hook"], chainId=1)}  # base is 8453, not 1
    p = write(tmp_path, "hooks/base/bad_chainid.json", bad)
    errs = validate.validate_file(p, root)
    assert any("chainId" in e for e in errs), errs


def test_unknown_chain_issues_directly():
    # schema.json's "chain" enum already blocks an unrecognized chain name
    # before check_hook_data's own chain_issues() runs (see
    # test_chain_mismatch_on_pointer_file_is_error for the schema-passes,
    # chains.json-disagrees case) — so exercise the "unknown chain" branch
    # of chain_issues() directly rather than through validate_file/schema.
    root = repo_root()
    issues = validate.chain_issues("nonexistent-chain", 1, root)
    assert any("unknown chain" in i for i in issues), issues


def test_chain_mismatch_on_legacy_pointerless_file_is_warning_not_error(tmp_path):
    root = setup_repo(tmp_path)
    address = "0x" + "2" * 40
    hook = {
        "hook": {"address": address, "chain": "base", "chainId": 1,  # wrong: base is 8453
                 "name": "Legacy Wrong Chain", "description": "d", "deployer": "",
                 "verifiedSource": True, "auditUrl": ""},
        "flags": verify_flags.decode_flags(address),
        "properties": {"dynamicFee": False, "upgradeable": False,
                       "requiresCustomSwapData": False, "vanillaSwap": False,
                       "swapAccess": "none"},
    }
    p = write(tmp_path, "hooks/base/legacy_wrong_chain.json", hook)
    assert validate.validate_file(p, root) == []
    warnings = validate.legacy_semantic_warnings(hook, root, file_root=validate.checkout_root(p))
    assert any("chainId" in w for w in warnings), warnings


# --- Should-fix A: filename stem must match hook.address -------------------

def test_filename_mismatch_pointer_carrying_is_error(tmp_path):
    root = setup_repo(tmp_path)
    p = write(tmp_path, "hooks/base/not-the-address.json", THIN)
    errs = validate.validate_file(p, root)
    assert any("filename" in e for e in errs), errs


def test_filename_match_pointer_carrying_is_valid(tmp_path):
    root = setup_repo(tmp_path)
    p = write(tmp_path, f"hooks/base/{THIN['hook']['address']}.json", THIN)
    assert validate.validate_file(p, root) == []


def test_filename_mismatch_legacy_pointerless_is_warning_not_error(tmp_path):
    root = setup_repo(tmp_path)
    address = "0x" + "3" * 40
    hook = {
        "hook": {"address": address, "chain": "celo", "chainId": 42220,
                 "name": "Legacy Mismatch", "description": "d", "deployer": "",
                 "verifiedSource": True, "auditUrl": ""},
        "flags": verify_flags.decode_flags(address),
        "properties": {"dynamicFee": False, "upgradeable": False,
                       "requiresCustomSwapData": False, "vanillaSwap": True,
                       "swapAccess": "none"},
    }
    p = write(tmp_path, "hooks/celo/totally-wrong-name.json", hook)
    # non-fatal: validate_file does not fail the legacy pointer-less file
    assert validate.validate_file(p, root) == []
    warnings = validate.legacy_semantic_warnings(hook, root, file_root=validate.checkout_root(p), filepath=p)
    assert any("filename" in w for w in warnings), warnings


# --- Fix B5: source.codeHashes must be sorted + unique ---------------------

HASH_A = "sha256:" + "a" * 64
HASH_B = "sha256:" + "b" * 64
HASH_C = "sha256:" + "c" * 64


def test_code_hashes_sorted_unique_is_valid(tmp_path):
    root = setup_repo(tmp_path)
    release = dict(RELEASE, source={"verified": True, "codeHashes": [HASH_A, HASH_B, HASH_C]})
    p = write(tmp_path, "releases/zora/creator-hook-2.2.1.json", release)
    assert validate.validate_file(p, root) == []


def test_code_hashes_unsorted_is_error(tmp_path):
    root = setup_repo(tmp_path)
    release = dict(RELEASE, source={"verified": True, "codeHashes": [HASH_B, HASH_A]})
    p = write(tmp_path, "releases/zora/creator-hook-2.2.1.json", release)
    errs = validate.validate_file(p, root)
    assert any("sorted" in e for e in errs), errs


def test_code_hashes_duplicate_is_error(tmp_path):
    root = setup_repo(tmp_path)
    release = dict(RELEASE, source={"verified": True, "codeHashes": [HASH_A, HASH_A, HASH_B]})
    p = write(tmp_path, "releases/zora/creator-hook-2.2.1.json", release)
    errs = validate.validate_file(p, root)
    assert any("unique" in e for e in errs), errs


def test_code_hashes_absent_is_valid(tmp_path):
    root = setup_repo(tmp_path)
    # RELEASE already has no source.codeHashes — absence is a valid "no
    # mechanical check available" state, not an error.
    p = os.path.join(root, "releases", "zora", "creator-hook-2.2.1.json")
    assert validate.validate_file(p, root) == []


def test_code_hashes_bad_pattern_caught_by_schema(tmp_path):
    root = setup_repo(tmp_path)
    release = dict(RELEASE, source={"verified": True, "codeHashes": ["not-a-hash"]})
    p = write(tmp_path, "releases/zora/creator-hook-2.2.1.json", release)
    errs = validate.validate_file(p, root)
    assert errs, "malformed codeHashes entry must fail schema validation"
