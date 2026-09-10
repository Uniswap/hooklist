import json
import os

import check_release_lane as crl


def write(root, rel, obj):
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        json.dump(obj, f)
    return p


RELEASE = {
    "project": "zora", "id": "creator-hook-2.2.1", "version": "2.2.1",
    "name": "Zora Creator Hook v2.2.1", "description": "d",
    "source": {"verified": True, "codeHashes": []},
    "properties": {"dynamicFee": True, "upgradeable": False,
                   "requiresCustomSwapData": False, "vanillaSwap": False,
                   "swapAccess": "none"},
    "warnings": [],
    "lifecycle": {"status": "active", "supersedes": None},
}

THIN = {"hook": {"address": "0x" + "a" * 40, "chain": "base", "chainId": 8453,
                  "release": "zora/creator-hook-2.2.1"}}


def test_case_a_pointer_names_release_changed_in_same_pr(tmp_path):
    pr_root = tmp_path / "pr"
    trusted_root = tmp_path / "trusted"
    write(str(pr_root), "hooks/base/0x" + "a" * 40 + ".json", THIN)
    write(str(pr_root), "releases/zora/creator-hook-2.2.1.json", RELEASE)

    violations = crl.check(
        changed_hooks=["hooks/base/0x" + "a" * 40 + ".json"],
        changed_releases=["releases/zora/creator-hook-2.2.1.json"],
        pr_root=str(pr_root),
        trusted_root=str(trusted_root),
    )
    assert violations == []


def test_case_a_passes_with_enrichment_fields_alongside_pointer(tmp_path):
    # A hook file that's more than a bare pointer (carries deployer/description
    # enrichment) still passes case (a) as long as the release it points at
    # was changed in this same PR — it need not be a "pure pointer addition".
    pr_root = tmp_path / "pr"
    trusted_root = tmp_path / "trusted"
    enriched = {"hook": dict(THIN["hook"], deployer="0x" + "b" * 40, description="enriched")}
    write(str(pr_root), "hooks/base/0x" + "a" * 40 + ".json", enriched)
    write(str(pr_root), "releases/zora/creator-hook-2.2.1.json", RELEASE)

    violations = crl.check(
        changed_hooks=["hooks/base/0x" + "a" * 40 + ".json"],
        changed_releases=["releases/zora/creator-hook-2.2.1.json"],
        pr_root=str(pr_root),
        trusted_root=str(trusted_root),
    )
    assert violations == []


def test_case_b_pure_pointer_addition_over_trusted(tmp_path):
    # Release already exists on trusted and is untouched by this PR; the
    # hook file only gains the hook.release key relative to trusted.
    pr_root = tmp_path / "pr"
    trusted_root = tmp_path / "trusted"
    path = "hooks/base/0x" + "a" * 40 + ".json"
    trusted_hook = {"hook": {k: v for k, v in THIN["hook"].items() if k != "release"}}
    write(str(trusted_root), path, trusted_hook)
    write(str(pr_root), path, THIN)

    violations = crl.check(
        changed_hooks=[path],
        changed_releases=[],
        pr_root=str(pr_root),
        trusted_root=str(trusted_root),
    )
    assert violations == []


def test_modified_pointerless_hook_with_semantic_edit_fails(tmp_path):
    pr_root = tmp_path / "pr"
    trusted_root = tmp_path / "trusted"
    path = "hooks/base/0x" + "a" * 40 + ".json"
    trusted_hook = {"hook": {"address": "0x" + "a" * 40, "chain": "base", "chainId": 8453,
                              "name": "Old Name", "verifiedSource": True},
                     "flags": {}, "properties": RELEASE["properties"]}
    edited_hook = json.loads(json.dumps(trusted_hook))
    edited_hook["hook"]["name"] = "New Name"
    write(str(trusted_root), path, trusted_hook)
    write(str(pr_root), path, edited_hook)

    violations = crl.check(
        changed_hooks=[path],
        changed_releases=[],
        pr_root=str(pr_root),
        trusted_root=str(trusted_root),
    )
    assert len(violations) == 1
    assert path in violations[0]


def test_new_file_with_no_pointer_and_no_trusted_counterpart_fails(tmp_path):
    pr_root = tmp_path / "pr"
    trusted_root = tmp_path / "trusted"
    path = "hooks/base/0x" + "c" * 40 + ".json"
    write(str(pr_root), path, {"hook": {"address": "0x" + "c" * 40, "chain": "base",
                                          "chainId": 8453, "name": "New", "verifiedSource": True},
                                 "flags": {}, "properties": RELEASE["properties"]})

    violations = crl.check(
        changed_hooks=[path],
        changed_releases=[],
        pr_root=str(pr_root),
        trusted_root=str(trusted_root),
    )
    assert len(violations) == 1


def test_pointer_addition_plus_other_field_change_is_not_case_b(tmp_path):
    # Adding the pointer AND changing something else at the same time is not
    # a "pure" pointer addition, and the release wasn't touched by this PR
    # (case a), so this must fail.
    pr_root = tmp_path / "pr"
    trusted_root = tmp_path / "trusted"
    path = "hooks/base/0x" + "a" * 40 + ".json"
    trusted_hook = {"hook": {k: v for k, v in THIN["hook"].items() if k != "release"}}
    write(str(trusted_root), path, trusted_hook)
    pr_hook = dict(THIN["hook"], deployer="0x" + "d" * 40)
    write(str(pr_root), path, {"hook": pr_hook})

    violations = crl.check(
        changed_hooks=[path],
        changed_releases=[],
        pr_root=str(pr_root),
        trusted_root=str(trusted_root),
    )
    assert len(violations) == 1
