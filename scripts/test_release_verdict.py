import json
import os

import release_verdict as rv


def write(tmp_path, rel, obj):
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj))
    return str(p)


RELEASE = {
    "project": "zora", "id": "creator-hook-2.2.1", "version": "2.2.1",
    "name": "Zora Creator Hook v2.2.1", "description": "d",
    "source": {"verified": True, "codeHashes": ["sha256:" + "a" * 64]},
    "properties": {"dynamicFee": True, "upgradeable": False,
                   "requiresCustomSwapData": False, "vanillaSwap": False,
                   "swapAccess": "none"},
    "warnings": [],
    "lifecycle": {"status": "active", "supersedes": None},
}

UPGRADEABLE_RELEASE = dict(RELEASE, properties=dict(RELEASE["properties"], upgradeable=True))


def hook_data(ref="zora/creator-hook-2.2.1", chain="base", address="0xabc"):
    return {"hook": {"address": address, "chain": chain, "chainId": 8453, "release": ref}}


# --- ref guard (path traversal) -------------------------------------------

def test_ref_traversal_dotdot_is_invalid_ref(tmp_path):
    result = rv.compute_verdict(hook_data(ref="../../etc/passwd"), str(tmp_path), str(tmp_path))
    assert result["verdict"] == "invalid-ref"


def test_ref_absolute_path_is_invalid_ref(tmp_path):
    result = rv.compute_verdict(hook_data(ref="/etc/passwd"), str(tmp_path), str(tmp_path))
    assert result["verdict"] == "invalid-ref"


def test_ref_uppercase_is_invalid_ref(tmp_path):
    result = rv.compute_verdict(hook_data(ref="Zora/Creator-Hook-2.2.1"), str(tmp_path), str(tmp_path))
    assert result["verdict"] == "invalid-ref"


def test_ref_multiple_slashes_is_invalid_ref(tmp_path):
    result = rv.compute_verdict(hook_data(ref="zora/creator/hook"), str(tmp_path), str(tmp_path))
    assert result["verdict"] == "invalid-ref"


def test_ref_trailing_newline_is_invalid_ref(tmp_path):
    # $-anchored regex .match() would accept "zora/x\n" (a bare newline sneaks
    # in past `$`); fullmatch() must reject it.
    result = rv.compute_verdict(hook_data(ref="zora/x\n"), str(tmp_path), str(tmp_path))
    assert result["verdict"] == "invalid-ref"


def test_ref_missing_is_invalid_ref(tmp_path):
    data = {"hook": {"address": "0xabc", "chain": "base", "chainId": 8453}}
    result = rv.compute_verdict(data, str(tmp_path), str(tmp_path))
    assert result["verdict"] == "invalid-ref"


def test_invalid_ref_never_touches_filesystem(tmp_path, monkeypatch):
    # Belt-and-braces: even if somehow a bad ref got past the regex, no
    # release file should ever be opened for a ref this contract rejects.
    opened = []
    real_open = open

    def spy_open(path, *a, **kw):
        opened.append(path)
        return real_open(path, *a, **kw)

    monkeypatch.setattr("builtins.open", spy_open)
    rv.compute_verdict(hook_data(ref="../../secret"), str(tmp_path), str(tmp_path))
    assert opened == []


# --- trusted-only resolution ----------------------------------------------

def test_no_list_when_release_absent_in_trusted(tmp_path):
    trusted = tmp_path / "trusted"
    pr = tmp_path / "pr"
    write(pr, "releases/zora/creator-hook-2.2.1.json", RELEASE)
    result = rv.compute_verdict(hook_data(), str(trusted), str(pr),
                                 fetch=lambda c, a: "sha256:" + "z" * 64)
    assert result["verdict"] == "no-list"
    assert result["knownHashes"] == 0


def test_match_when_hash_in_trusted_allowlist(tmp_path):
    trusted = tmp_path / "trusted"
    pr = tmp_path / "pr"
    write(trusted, "releases/zora/creator-hook-2.2.1.json", RELEASE)
    known_hash = RELEASE["source"]["codeHashes"][0]
    result = rv.compute_verdict(hook_data(), str(trusted), str(pr),
                                 fetch=lambda c, a: known_hash)
    assert result["verdict"] == "match"
    assert result["knownHashes"] == 1


def test_match_upgradeable_when_release_is_upgradeable(tmp_path):
    # Byte-identical hash + an upgradeable release must NEVER collapse to
    # plain "match" — behavior is storage-dependent, so the cache hit alone
    # doesn't settle anything.
    trusted = tmp_path / "trusted"
    pr = tmp_path / "pr"
    write(trusted, "releases/zora/creator-hook-2.2.1.json", UPGRADEABLE_RELEASE)
    known_hash = UPGRADEABLE_RELEASE["source"]["codeHashes"][0]
    result = rv.compute_verdict(hook_data(), str(trusted), str(pr),
                                 fetch=lambda c, a: known_hash)
    assert result["verdict"] == "match-upgradeable"
    assert result["codeHash"] == known_hash
    assert result["knownHashes"] == 1


def test_no_cached_review_when_hash_absent_from_trusted_allowlist(tmp_path):
    trusted = tmp_path / "trusted"
    pr = tmp_path / "pr"
    write(trusted, "releases/zora/creator-hook-2.2.1.json", RELEASE)
    result = rv.compute_verdict(hook_data(), str(trusted), str(pr),
                                 fetch=lambda c, a: "sha256:" + "9" * 64,
                                 fetch_code=lambda c, a: None)
    assert result["verdict"] == "no-cached-review"


def test_pr_side_release_never_consulted_for_the_cache(tmp_path):
    # If the PR appends its own hash to its copy of the release, and this
    # hook's live bytecode matches ONLY the PR-added hash (not present in
    # trusted), the verdict must still be no-cached-review — the cache is
    # always read from trusted, and the PR's own release copy is never even
    # opened for this purpose.
    trusted = tmp_path / "trusted"
    pr = tmp_path / "pr"
    write(trusted, "releases/zora/creator-hook-2.2.1.json", RELEASE)
    pr_hash = "sha256:" + "9" * 64
    pr_release = dict(RELEASE, source={"verified": True,
                                        "codeHashes": sorted(RELEASE["source"]["codeHashes"] + [pr_hash])})
    write(pr, "releases/zora/creator-hook-2.2.1.json", pr_release)
    result = rv.compute_verdict(hook_data(), str(trusted), str(pr),
                                 fetch=lambda c, a: pr_hash,
                                 fetch_code=lambda c, a: None)
    assert result["verdict"] == "no-cached-review"


# --- fetch-failed -----------------------------------------------------------

def test_fetch_failed_when_fetch_returns_none(tmp_path):
    trusted = tmp_path / "trusted"
    pr = tmp_path / "pr"
    write(trusted, "releases/zora/creator-hook-2.2.1.json", RELEASE)
    result = rv.compute_verdict(hook_data(), str(trusted), str(pr), fetch=lambda c, a: None)
    assert result["verdict"] == "fetch-failed"


def test_fetch_failed_when_fetch_raises(tmp_path):
    trusted = tmp_path / "trusted"
    pr = tmp_path / "pr"
    write(trusted, "releases/zora/creator-hook-2.2.1.json", RELEASE)

    def boom(chain, address):
        raise RuntimeError("explorer down")

    result = rv.compute_verdict(hook_data(), str(trusted), str(pr), fetch=boom)
    assert result["verdict"] == "fetch-failed"


# --- no-cached-review evidence bundle ---------------------------------------

CODE_A = "0x" + "11" * 100  # 100-byte "current hook" bytecode
CODE_A_ONE_BYTE_DIFF = "0x" + "11" * 40 + "22" + "11" * 59  # same length, 1-byte diff run
CODE_A_TWO_RUNS_DIFF = "0x" + "11" * 10 + "22" * 3 + "11" * 30 + "22" * 2 + "11" * 55  # same length, 2 diff runs
CODE_SHORTER = "0x" + "33" * 40  # different length


def test_no_cached_review_evidence_codelen_from_current_hook(tmp_path):
    trusted = tmp_path / "trusted"
    pr = tmp_path / "pr"
    write(trusted, "releases/zora/creator-hook-2.2.1.json", RELEASE)
    result = rv.compute_verdict(
        hook_data(), str(trusted), str(pr),
        fetch=lambda c, a: "sha256:" + "9" * 64,
        fetch_code=lambda c, a: CODE_A,
    )
    assert result["verdict"] == "no-cached-review"
    assert result["codeLen"] == 100
    # No other member hook file exists in the PR checkout's hooks/ tree.
    assert result["nearestMemberLen"] is None
    assert result["diffRuns"] is None


def test_no_cached_review_evidence_nearest_member_equal_length_counts_diff_runs(tmp_path):
    trusted = tmp_path / "trusted"
    pr = tmp_path / "pr"
    write(trusted, "releases/zora/creator-hook-2.2.1.json", RELEASE)
    # A sibling member of the same release, elsewhere in the PR tree.
    write(pr, "hooks/base/0xdef.json", {
        "hook": {"address": "0xdef", "chain": "base", "chainId": 8453,
                  "release": "zora/creator-hook-2.2.1"},
    })

    codes = {"0xabc": CODE_A, "0xdef": CODE_A_TWO_RUNS_DIFF}
    result = rv.compute_verdict(
        hook_data(address="0xabc"), str(trusted), str(pr),
        fetch=lambda c, a: "sha256:" + "9" * 64,
        fetch_code=lambda c, a: codes[a],
    )
    assert result["verdict"] == "no-cached-review"
    assert result["codeLen"] == 100
    assert result["nearestMemberLen"] == 100
    assert result["diffRuns"] == 2


def test_no_cached_review_evidence_single_byte_diff_is_one_run(tmp_path):
    trusted = tmp_path / "trusted"
    pr = tmp_path / "pr"
    write(trusted, "releases/zora/creator-hook-2.2.1.json", RELEASE)
    write(pr, "hooks/base/0xdef.json", {
        "hook": {"address": "0xdef", "chain": "base", "chainId": 8453,
                  "release": "zora/creator-hook-2.2.1"},
    })

    codes = {"0xabc": CODE_A, "0xdef": CODE_A_ONE_BYTE_DIFF}
    result = rv.compute_verdict(
        hook_data(address="0xabc"), str(trusted), str(pr),
        fetch=lambda c, a: "sha256:" + "9" * 64,
        fetch_code=lambda c, a: codes[a],
    )
    assert result["diffRuns"] == 1


def test_no_cached_review_evidence_diffruns_null_when_lengths_differ(tmp_path):
    trusted = tmp_path / "trusted"
    pr = tmp_path / "pr"
    write(trusted, "releases/zora/creator-hook-2.2.1.json", RELEASE)
    write(pr, "hooks/base/0xdef.json", {
        "hook": {"address": "0xdef", "chain": "base", "chainId": 8453,
                  "release": "zora/creator-hook-2.2.1"},
    })

    codes = {"0xabc": CODE_A, "0xdef": CODE_SHORTER}
    result = rv.compute_verdict(
        hook_data(address="0xabc"), str(trusted), str(pr),
        fetch=lambda c, a: "sha256:" + "9" * 64,
        fetch_code=lambda c, a: codes[a],
    )
    assert result["codeLen"] == 100
    assert result["nearestMemberLen"] == 40
    assert result["diffRuns"] is None


def test_no_cached_review_evidence_excludes_self_when_scanning_members(tmp_path):
    # The current hook's own file also carries the release ref — the scan
    # must never treat it as its own "nearest member".
    trusted = tmp_path / "trusted"
    pr = tmp_path / "pr"
    write(trusted, "releases/zora/creator-hook-2.2.1.json", RELEASE)
    write(pr, "hooks/base/0xabc.json", hook_data(address="0xabc"))

    result = rv.compute_verdict(
        hook_data(address="0xabc"), str(trusted), str(pr),
        fetch=lambda c, a: "sha256:" + "9" * 64,
        fetch_code=lambda c, a: CODE_A,
    )
    assert result["nearestMemberLen"] is None
    assert result["diffRuns"] is None


def test_no_cached_review_evidence_all_null_on_fetch_failure(tmp_path):
    trusted = tmp_path / "trusted"
    pr = tmp_path / "pr"
    write(trusted, "releases/zora/creator-hook-2.2.1.json", RELEASE)
    write(pr, "hooks/base/0xdef.json", {
        "hook": {"address": "0xdef", "chain": "base", "chainId": 8453,
                  "release": "zora/creator-hook-2.2.1"},
    })
    result = rv.compute_verdict(
        hook_data(), str(trusted), str(pr),
        fetch=lambda c, a: "sha256:" + "9" * 64,
        fetch_code=lambda c, a: None,
    )
    assert result["verdict"] == "no-cached-review"
    assert result["codeLen"] is None
    assert result["nearestMemberLen"] is None
    assert result["diffRuns"] is None


def test_evidence_fields_null_for_match_verdict(tmp_path):
    trusted = tmp_path / "trusted"
    pr = tmp_path / "pr"
    write(trusted, "releases/zora/creator-hook-2.2.1.json", RELEASE)
    known_hash = RELEASE["source"]["codeHashes"][0]
    result = rv.compute_verdict(hook_data(), str(trusted), str(pr), fetch=lambda c, a: known_hash)
    assert result["codeLen"] is None
    assert result["nearestMemberLen"] is None
    assert result["diffRuns"] is None


# --- output fields ----------------------------------------------------------

def test_output_includes_chain_field(tmp_path):
    trusted = tmp_path / "trusted"
    pr = tmp_path / "pr"
    write(trusted, "releases/zora/creator-hook-2.2.1.json", RELEASE)
    known_hash = RELEASE["source"]["codeHashes"][0]
    result = rv.compute_verdict(hook_data(chain="base"), str(trusted), str(pr), fetch=lambda c, a: known_hash)
    assert result["chain"] == "base"
    assert set(result.keys()) == {"address", "chain", "release", "verdict", "codeHash",
                                   "knownHashes", "codeLen", "nearestMemberLen", "diffRuns"}


# --- CLI end-to-end ----------------------------------------------------------

def test_cli_writes_verdict_json(tmp_path, monkeypatch):
    trusted = tmp_path / "trusted"
    pr = tmp_path / "pr"
    write(trusted, "releases/zora/creator-hook-2.2.1.json", RELEASE)
    hook_path = write(pr, "hooks/base/0xabc.json", hook_data())
    out_path = tmp_path / "verdict.json"

    monkeypatch.setattr(rv, "_default_fetch", lambda chain, address: RELEASE["source"]["codeHashes"][0])
    monkeypatch.setattr("sys.argv", [
        "release_verdict.py",
        "--hook-file", hook_path,
        "--trusted-root", str(trusted),
        "--pr-root", str(pr),
        "--out", str(out_path),
    ])
    rv.main()
    result = json.loads(out_path.read_text())
    assert result["verdict"] == "match"
