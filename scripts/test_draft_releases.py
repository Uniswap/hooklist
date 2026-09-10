import json
import draft_releases as dr


def test_slug():
    assert dr.slug("Zora Creator Hook v2.2.1") == "zora-creator-hook-v2.2.1"
    assert dr.slug("Flaunch POSM v3 (Base)") == "flaunch-posm-v3-base"


def test_group_families_by_exact_name():
    a = ("hooks/base/a.json", {"hook": {"name": "Spot"}})
    b = ("hooks/celo/b.json", {"hook": {"name": "Spot"}})
    c = ("hooks/base/c.json", {"hook": {"name": "Solo"}})
    fams = dr.group_families([a, b, c])
    assert set(fams) == {"Spot"}
    assert len(fams["Spot"]) == 2


def test_ready_vs_needs_reconciliation(tmp_path):
    props = {"dynamicFee": False, "upgradeable": False, "requiresCustomSwapData": False,
             "vanillaSwap": True, "swapAccess": "none"}
    def hookfile(name, desc, p):
        return {"hook": {"address": "0x" + "1" * 40, "chain": "base", "chainId": 8453,
                         "name": name, "description": desc, "deployer": "",
                         "verifiedSource": True, "auditUrl": ""},
                "flags": {}, "properties": p}
    same = [("p1", hookfile("X", "short", props)),
            ("p2", hookfile("X", "a much longer canonical description", props))]
    ready = dr.draft_family("X", same)
    assert ready["status"] == "READY"
    assert ready["release"]["description"] == "a much longer canonical description"
    assert ready["release"]["properties"] == props
    diverged = [("p1", hookfile("Y", "d", props)),
                ("p2", hookfile("Y", "d", dict(props, vanillaSwap=False)))]
    rec = dr.draft_family("Y", diverged)
    assert rec["status"] == "NEEDS-RECONCILIATION"
    assert "vanillaSwap" in json.dumps(rec["diffs"])
