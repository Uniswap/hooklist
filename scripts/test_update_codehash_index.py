import json

import fetch_codehash
import update_codehash_index as uci


def write(tmp_path, rel, obj):
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj))
    return p


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


def hook(address, ref="zora/creator-hook-2.2.1", chain="base"):
    return {"hook": {"address": address, "chain": chain, "chainId": 8453, "release": ref}}


def no_sleep(seconds):
    pass


# --- find_pointer_members ----------------------------------------------------

def test_find_pointer_members_skips_hooks_without_release(tmp_path):
    write(tmp_path, "hooks/base/0xabc.json", hook("0xabc"))
    write(tmp_path, "hooks/base/0xdef.json", {"hook": {"address": "0xdef", "chain": "base", "chainId": 8453}})
    members = uci.find_pointer_members(str(tmp_path))
    assert members == [("base", "0xabc", "zora/creator-hook-2.2.1")]


def test_find_pointer_members_skips_malformed_json(tmp_path):
    p = tmp_path / "hooks" / "base" / "broken.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("{not json")
    members = uci.find_pointer_members(str(tmp_path))
    assert members == []


# --- update_index: core append behavior --------------------------------------

def test_appends_new_hash_and_writes_sorted_unique(tmp_path):
    write(tmp_path, "hooks/base/0xabc.json", hook("0xabc"))
    release_path = write(tmp_path, "releases/zora/creator-hook-2.2.1.json", RELEASE)

    code_hex = "0x" + "11" * 10
    expected_hash = fetch_codehash.codehash_of(code_hex)

    report = uci.update_index(str(tmp_path), fetch_code=lambda c, a: code_hex, sleep=no_sleep)
    assert report["updated"] == [f"base:0xabc -> zora/creator-hook-2.2.1: +{expected_hash}"]
    assert report["changed_refs"] == ["zora/creator-hook-2.2.1"]

    data = json.loads(release_path.read_text())
    assert data["source"]["codeHashes"] == sorted([RELEASE["source"]["codeHashes"][0], expected_hash])


def test_unchanged_when_fetched_hash_matches_existing(tmp_path):
    write(tmp_path, "hooks/base/0xabc.json", hook("0xabc"))
    release_path = write(tmp_path, "releases/zora/creator-hook-2.2.1.json", RELEASE)

    # A code hex whose sha256 equals RELEASE's existing (arbitrary) hash
    # can't be reverse-engineered, so instead seed the release's hash from
    # a real codehash_of() computation over a fixed code hex.
    code_hex = "0x" + "ab" * 20
    real_hash = fetch_codehash.codehash_of(code_hex)
    release_with_hash = dict(RELEASE, source={"verified": True, "codeHashes": [real_hash]})
    release_path.write_text(json.dumps(release_with_hash))

    report = uci.update_index(str(tmp_path), fetch_code=lambda c, a: code_hex, sleep=no_sleep)
    assert report["updated"] == []
    assert report["unchanged"] == 1
    assert json.loads(release_path.read_text())["source"]["codeHashes"] == [real_hash]


def test_creates_codehashes_key_when_release_has_none(tmp_path):
    release_no_hashes = dict(RELEASE, source={"verified": True})
    write(tmp_path, "hooks/base/0xabc.json", hook("0xabc"))
    release_path = write(tmp_path, "releases/zora/creator-hook-2.2.1.json", release_no_hashes)

    code_hex = "0x" + "cd" * 20
    expected_hash = fetch_codehash.codehash_of(code_hex)

    report = uci.update_index(str(tmp_path), fetch_code=lambda c, a: code_hex, sleep=no_sleep)
    assert report["changed_refs"] == ["zora/creator-hook-2.2.1"]
    data = json.loads(release_path.read_text())
    assert data["source"]["codeHashes"] == [expected_hash]


def test_multiple_members_one_new_one_known(tmp_path):
    code_hex_known = "0x" + "aa" * 5
    known_hash = fetch_codehash.codehash_of(code_hex_known)
    code_hex_new = "0x" + "bb" * 5
    new_hash = fetch_codehash.codehash_of(code_hex_new)

    release_with_hash = dict(RELEASE, source={"verified": True, "codeHashes": [known_hash]})
    write(tmp_path, "hooks/base/0xabc.json", hook("0xabc"))
    write(tmp_path, "hooks/base/0xdef.json", hook("0xdef"))
    release_path = write(tmp_path, "releases/zora/creator-hook-2.2.1.json", release_with_hash)

    codes = {"0xabc": code_hex_known, "0xdef": code_hex_new}
    report = uci.update_index(str(tmp_path), fetch_code=lambda c, a: codes[a], sleep=no_sleep)
    assert report["unchanged"] == 1
    assert len(report["updated"]) == 1
    data = json.loads(release_path.read_text())
    assert data["source"]["codeHashes"] == sorted([known_hash, new_hash])


# --- fetch failures never raise ----------------------------------------------

def test_fetch_exception_is_recorded_and_skipped(tmp_path):
    write(tmp_path, "hooks/base/0xabc.json", hook("0xabc"))
    release_path = write(tmp_path, "releases/zora/creator-hook-2.2.1.json", RELEASE)
    original_text = release_path.read_text()

    def boom(chain, address):
        raise RuntimeError("explorer down")

    report = uci.update_index(str(tmp_path), fetch_code=boom, sleep=no_sleep)
    assert len(report["failed"]) == 1
    assert "explorer down" in report["failed"][0]
    assert release_path.read_text() == original_text


def test_empty_code_is_recorded_as_failure(tmp_path):
    write(tmp_path, "hooks/base/0xabc.json", hook("0xabc"))
    release_path = write(tmp_path, "releases/zora/creator-hook-2.2.1.json", RELEASE)
    original_text = release_path.read_text()

    report = uci.update_index(str(tmp_path), fetch_code=lambda c, a: "0x", sleep=no_sleep)
    assert len(report["failed"]) == 1
    assert "empty code" in report["failed"][0]
    assert release_path.read_text() == original_text


def test_dangling_pointer_release_missing_is_skipped_not_raised(tmp_path):
    write(tmp_path, "hooks/base/0xabc.json", hook("0xabc", ref="ghost/does-not-exist"))
    report = uci.update_index(str(tmp_path), fetch_code=lambda c, a: "0x" + "11" * 5, sleep=no_sleep)
    assert report["updated"] == []
    assert report["failed"] == []
    assert report["unchanged"] == 0


# --- dry-run ------------------------------------------------------------

def test_dry_run_never_writes(tmp_path):
    write(tmp_path, "hooks/base/0xabc.json", hook("0xabc"))
    release_path = write(tmp_path, "releases/zora/creator-hook-2.2.1.json", RELEASE)
    original_text = release_path.read_text()

    code_hex = "0x" + "ee" * 8
    report = uci.update_index(str(tmp_path), fetch_code=lambda c, a: code_hex, sleep=no_sleep, dry_run=True)
    assert report["updated"]
    assert release_path.read_text() == original_text


# --- CLI never raises even on total failure ----------------------------------

def test_main_returns_zero_even_when_everything_fails(tmp_path, monkeypatch, capsys):
    write(tmp_path, "hooks/base/0xabc.json", hook("0xabc"))
    write(tmp_path, "releases/zora/creator-hook-2.2.1.json", RELEASE)

    monkeypatch.setattr("sys.argv", ["update_codehash_index.py", "--repo-root", str(tmp_path), "--sleep", "0"])
    monkeypatch.setattr(uci.fetch_codehash, "fetch_code",
                         lambda chain, address: (_ for _ in ()).throw(RuntimeError("down")))
    rc = uci.main()
    assert rc == 0
    out = capsys.readouterr().out
    assert "fetch failure" in out
