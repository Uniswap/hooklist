import json
import os
import build_artifacts as ba

FAM = "0x" + "a" * 64
ADDR = "0x00000000000000000000000000000000000000c0"  # bits 7,6 -> beforeSwap, afterSwap


def setup_repo(tmp_path):
    (tmp_path / "index").mkdir()
    (tmp_path / "families").mkdir()
    (tmp_path / "index" / "celo.jsonl").write_text(
        json.dumps({"address": ADDR, "block": 5, "family": FAM}) + "\n")
    (tmp_path / "index" / "cursors.json").write_text(
        json.dumps({"celo": {"block": 1000, "pending": {}}}))
    perms = {k: (k == "beforeSwap") for k in [
        "beforeInitialize", "afterInitialize", "beforeAddLiquidity", "afterAddLiquidity",
        "beforeRemoveLiquidity", "afterRemoveLiquidity", "beforeSwap", "afterSwap",
        "beforeDonate", "afterDonate", "beforeSwapReturnsDelta", "afterSwapReturnsDelta",
        "afterAddLiquidityReturnsDelta", "afterRemoveLiquidityReturnsDelta"]}
    (tmp_path / "families" / f"{FAM}.json").write_text(json.dumps({
        "family": {"id": FAM, "kind": "self-contained", "name": "T",
                   "description": "", "sourceStatus": "verified",
                   "analyzedAt": "2026-07-24"},
        "implementedPermissions": perms,
        "properties": {"dynamicFee": False, "requiresCustomSwapData": False,
                       "vanillaSwap": True, "swapAccess": "none"},
        "warnings": [],
    }))
    return str(tmp_path)


def test_families_artifact_counts_instances(tmp_path):
    root = setup_repo(tmp_path)
    ba.build(root, built_at="2026-07-24T12:00:00Z")
    fams = json.loads(open(os.path.join(root, "dist", "families.json")).read())
    assert fams["builtAt"] == "2026-07-24T12:00:00Z"
    assert fams["families"][0]["instanceCounts"] == {"celo": 1}


def test_lookup_artifact_denormalizes(tmp_path):
    root = setup_repo(tmp_path)
    ba.build(root, built_at="2026-07-24T12:00:00Z")
    lookup = json.loads(open(os.path.join(root, "dist", "lookup", "celo.json")).read())
    assert lookup["scannedToBlock"] == 1000
    entry = lookup["hooks"][ADDR]
    assert entry["name"] == "T"
    assert entry["flags"]["beforeSwap"] is True and entry["flags"]["afterSwap"] is True
    assert entry["upgradeable"] is False
    # address sets afterSwap bit but code doesn't implement it
    assert "unimplemented:afterSwap" in entry["flagDivergence"]
    assert "dormant:" not in "".join(entry["flagDivergence"])


def test_unknown_family_entry(tmp_path):
    root = setup_repo(tmp_path)
    addr2 = "0x0000000000000000000000000000000000002080"
    fam2 = "0x" + "b" * 64
    with open(os.path.join(root, "index", "celo.jsonl"), "a") as f:
        f.write(json.dumps({"address": addr2, "block": 6, "family": fam2}) + "\n")
    # no family file for fam2 (analysis pending)
    ba.build(root, built_at="x")
    lookup = json.loads(open(os.path.join(root, "dist", "lookup", "celo.json")).read())
    entry = lookup["hooks"][addr2]
    assert entry["family"] == fam2
    assert entry["name"] is None and entry["sourceStatus"] is None
    assert entry["upgradeable"] is None and entry["flagDivergence"] == []


def test_build_with_no_index_or_families_dirs(tmp_path):
    root = str(tmp_path)
    ba.build(root, built_at="2026-07-24T12:00:00Z")
    fams = json.loads(open(os.path.join(root, "dist", "families.json")).read())
    assert fams["families"] == []
    assert os.path.isdir(os.path.join(root, "dist", "lookup"))
