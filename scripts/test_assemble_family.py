import json
import assemble_family as af

FAM = "0x" + "a" * 64

CLAUDE = {
    "name": "TestHook", "description": "Does things.", "kind": "self-contained",
    "implementedPermissions": {k: (k == "beforeSwap") for k in [
        "beforeInitialize", "afterInitialize", "beforeAddLiquidity", "afterAddLiquidity",
        "beforeRemoveLiquidity", "afterRemoveLiquidity", "beforeSwap", "afterSwap",
        "beforeDonate", "afterDonate", "beforeSwapReturnsDelta", "afterSwapReturnsDelta",
        "afterAddLiquidityReturnsDelta", "afterRemoveLiquidityReturnsDelta"]},
    "dynamicFee": False, "requiresCustomSwapData": False,
    "vanillaSwap": True, "swapAccess": "none", "warnings": [],
}


def test_stub_shape():
    out = af.build_stub(FAM, contract_name="")
    assert out == {"family": {
        "id": FAM, "kind": "unknown", "name": f"Unknown {FAM[:10]}",
        "description": "", "sourceStatus": "unverified", "repoUrl": "", "auditUrl": "",
    }}


def test_analyzed_shape(tmp_path):
    out = af.build_analyzed(FAM, CLAUDE, analyzed_at="2026-07-24")
    assert out["family"]["sourceStatus"] == "verified"
    assert out["family"]["name"] == "TestHook"
    assert out["family"]["analyzedAt"] == "2026-07-24"
    assert out["implementedPermissions"]["beforeSwap"] is True
    assert out["properties"] == {"dynamicFee": False, "requiresCustomSwapData": False,
                                 "vanillaSwap": True, "swapAccess": "none"}
    assert out["warnings"] == []


def test_analyzed_validates_against_schema(tmp_path):
    import os, validate
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = af.build_analyzed(FAM, CLAUDE, analyzed_at="2026-07-24")
    p = tmp_path / "families" / f"{FAM}.json"
    p.parent.mkdir()
    p.write_text(json.dumps(out))
    assert validate.validate_file(str(p), repo_root) == []


def test_stub_validates_against_schema(tmp_path):
    import os, validate
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    p = tmp_path / "families" / f"{FAM}.json"
    p.parent.mkdir()
    p.write_text(json.dumps(af.build_stub(FAM, contract_name="MyHook")))
    assert validate.validate_file(str(p), repo_root) == []
