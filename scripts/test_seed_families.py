import json
import os
import seed_families as sf


def make_hook(name, desc, upgradeable=False, verified=True):
    return {
        "hook": {"address": "0x" + "1" * 40, "chain": "celo", "chainId": 42220,
                 "name": name, "description": desc, "deployer": "",
                 "verifiedSource": verified, "auditUrl": ""},
        "flags": {k: (k == "beforeSwap") for k in sf.FLAG_NAMES},
        "properties": {"dynamicFee": False, "upgradeable": upgradeable,
                       "requiresCustomSwapData": False, "vanillaSwap": True,
                       "swapAccess": "none"},
    }


def test_group_picks_richest_description():
    a = ("celo", "0x" + "1" * 40, make_hook("A", "short"))
    b = ("celo", "0x" + "2" * 40, make_hook("B", "a much longer description wins"))
    fam = sf.family_from_hooks("0x" + "f" * 64, [a, b])
    assert fam["family"]["name"] == "B"
    assert fam["family"]["kind"] == "self-contained"
    assert fam["family"]["sourceStatus"] == "verified"
    assert fam["implementedPermissions"]["beforeSwap"] is True
    assert "upgradeable" not in fam["properties"]
    assert any("approximated" in w for w in fam["warnings"])


def test_upgradeable_becomes_delegating():
    a = ("celo", "0x" + "1" * 40, make_hook("A", "d", upgradeable=True))
    fam = sf.family_from_hooks("0x" + "f" * 64, [a])
    assert fam["family"]["kind"] == "delegating"


def test_unverified_becomes_stub():
    a = ("celo", "0x" + "1" * 40, make_hook("A", "d", verified=False))
    fam = sf.family_from_hooks("0x" + "f" * 64, [a])
    assert fam["family"]["sourceStatus"] == "unverified"
    assert "properties" not in fam and "implementedPermissions" not in fam


def test_seed_validates_output(tmp_path):
    import validate
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    a = ("celo", "0x" + "1" * 40, make_hook("A", "d"))
    fam = sf.family_from_hooks("0x" + "f" * 64, [a])
    p = tmp_path / "families" / "x.json"
    p.parent.mkdir()
    p.write_text(json.dumps(fam))
    assert validate.validate_file(str(p), repo_root) == []
