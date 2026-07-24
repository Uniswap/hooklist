import json
import os
import validate


def repo_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def write(tmp_path, rel, obj):
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj))
    return str(p)


STUB = {"family": {"id": "0x" + "a" * 64, "kind": "unknown",
                   "name": "Unknown 0xaaaa", "sourceStatus": "unverified"}}

ANALYZED = {
    "family": {"id": "0x" + "b" * 64, "kind": "self-contained", "name": "TestHook",
               "description": "d", "sourceStatus": "verified", "analyzedAt": "2026-07-24"},
    "implementedPermissions": {k: False for k in [
        "beforeInitialize", "afterInitialize", "beforeAddLiquidity", "afterAddLiquidity",
        "beforeRemoveLiquidity", "afterRemoveLiquidity", "beforeSwap", "afterSwap",
        "beforeDonate", "afterDonate", "beforeSwapReturnsDelta", "afterSwapReturnsDelta",
        "afterAddLiquidityReturnsDelta", "afterRemoveLiquidityReturnsDelta"]},
    "properties": {"dynamicFee": False, "requiresCustomSwapData": False,
                   "vanillaSwap": True, "swapAccess": "none"},
    "warnings": [],
}


def test_stub_valid(tmp_path):
    p = write(tmp_path, "families/0x%s.json" % ("a" * 64), STUB)
    assert validate.validate_file(p, repo_root()) == []


def test_analyzed_valid(tmp_path):
    p = write(tmp_path, "families/0x%s.json" % ("b" * 64), ANALYZED)
    assert validate.validate_file(p, repo_root()) == []


def test_stub_with_properties_invalid(tmp_path):
    bad = dict(STUB, properties=ANALYZED["properties"])
    p = write(tmp_path, "families/bad.json", bad)
    assert validate.validate_file(p, repo_root()) != []


def test_verified_without_properties_invalid(tmp_path):
    bad = {"family": dict(ANALYZED["family"])}
    p = write(tmp_path, "families/bad2.json", bad)
    assert validate.validate_file(p, repo_root()) != []


def test_hook_file_still_routed_to_hook_schema(tmp_path):
    with open(os.path.join(repo_root(), "hooks", "celo",
                           os.listdir(os.path.join(repo_root(), "hooks", "celo"))[0])) as f:
        hook = json.load(f)
    hook["hook"]["analyzedAtBlock"] = 123  # new optional field accepted
    p = write(tmp_path, "hooks/celo/x.json", hook)
    assert validate.validate_file(p, repo_root()) == []
