import json
import os
import tempfile
import pytest
import aggregate
from aggregate import aggregate_hooks, filter_vanilla_swap


SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["hook", "flags", "properties"],
    "additionalProperties": False,
    "properties": {
        "hook": {
            "type": "object",
            "required": ["address", "chain", "chainId", "name", "verifiedSource"],
            "properties": {
                "address": {"type": "string", "pattern": "^0x[a-fA-F0-9]{40}$"},
                "chain": {"type": "string"},
                "chainId": {"type": "integer"},
                "name": {"type": "string"},
                "description": {"type": "string"},
                "deployer": {"type": "string"},
                "verifiedSource": {"type": "boolean"},
                "auditUrl": {"type": "string"},
            },
        },
        "flags": {
            "type": "object",
            "required": [
                "beforeInitialize", "afterInitialize",
                "beforeAddLiquidity", "afterAddLiquidity",
                "beforeRemoveLiquidity", "afterRemoveLiquidity",
                "beforeSwap", "afterSwap",
                "beforeDonate", "afterDonate",
                "beforeSwapReturnsDelta", "afterSwapReturnsDelta",
                "afterAddLiquidityReturnsDelta", "afterRemoveLiquidityReturnsDelta",
            ],
            "properties": {
                "beforeInitialize": {"type": "boolean"},
                "afterInitialize": {"type": "boolean"},
                "beforeAddLiquidity": {"type": "boolean"},
                "afterAddLiquidity": {"type": "boolean"},
                "beforeRemoveLiquidity": {"type": "boolean"},
                "afterRemoveLiquidity": {"type": "boolean"},
                "beforeSwap": {"type": "boolean"},
                "afterSwap": {"type": "boolean"},
                "beforeDonate": {"type": "boolean"},
                "afterDonate": {"type": "boolean"},
                "beforeSwapReturnsDelta": {"type": "boolean"},
                "afterSwapReturnsDelta": {"type": "boolean"},
                "afterAddLiquidityReturnsDelta": {"type": "boolean"},
                "afterRemoveLiquidityReturnsDelta": {"type": "boolean"},
            },
        },
        "properties": {
            "type": "object",
            "required": ["dynamicFee", "upgradeable", "requiresCustomSwapData", "vanillaSwap", "swapAccess"],
            "properties": {
                "dynamicFee": {"type": "boolean"},
                "upgradeable": {"type": "boolean"},
                "requiresCustomSwapData": {"type": "boolean"},
                "vanillaSwap": {"type": "boolean"},
                "swapAccess": {"type": "string", "enum": ["none", "temporal", "allowlist", "governance", "other"]},
            },
        },
    },
}


def _valid_hook(chain="ethereum", address="0x0000000000000000000000000000000000002080", name="TestHook"):
    return {
        "hook": {
            "address": address,
            "chain": chain,
            "chainId": 1,
            "name": name,
            "description": "A test hook",
            "deployer": "",
            "verifiedSource": True,
            "auditUrl": "",
        },
        "flags": {
            "beforeInitialize": True,
            "afterInitialize": False,
            "beforeAddLiquidity": False,
            "afterAddLiquidity": False,
            "beforeRemoveLiquidity": False,
            "afterRemoveLiquidity": False,
            "beforeSwap": True,
            "afterSwap": False,
            "beforeDonate": False,
            "afterDonate": False,
            "beforeSwapReturnsDelta": False,
            "afterSwapReturnsDelta": False,
            "afterAddLiquidityReturnsDelta": False,
            "afterRemoveLiquidityReturnsDelta": False,
        },
        "properties": {
            "dynamicFee": False,
            "upgradeable": False,
            "requiresCustomSwapData": False,
            "vanillaSwap": False,
            "swapAccess": "none",
        },
    }


@pytest.fixture
def hook_dir():
    """Create a temp directory with sample hook files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        eth_dir = os.path.join(tmpdir, "ethereum")
        base_dir = os.path.join(tmpdir, "base")
        os.makedirs(eth_dir)
        os.makedirs(base_dir)

        hook1 = _valid_hook("ethereum", "0x0000000000000000000000000000000000002080", "TestHook")
        hook2 = _valid_hook("base", "0x00000000000000000000000000000000000000C0", "SwapHook")
        hook2["hook"]["chainId"] = 8453
        hook2["flags"]["beforeInitialize"] = False
        hook2["flags"]["beforeSwap"] = True
        hook2["flags"]["afterSwap"] = True

        with open(os.path.join(eth_dir, "0x0000000000000000000000000000000000002080.json"), "w") as f:
            json.dump(hook1, f)
        with open(os.path.join(base_dir, "0x00000000000000000000000000000000000000C0.json"), "w") as f:
            json.dump(hook2, f)

        yield tmpdir


def test_aggregate_hooks(hook_dir):
    hooks = aggregate_hooks(hook_dir)
    assert len(hooks) == 2
    chains = {h["hook"]["chain"] for h in hooks}
    assert chains == {"ethereum", "base"}


def test_aggregate_hooks_sorted_by_chain_then_address(hook_dir):
    hooks = aggregate_hooks(hook_dir)
    assert hooks[0]["hook"]["chain"] == "base"
    assert hooks[1]["hook"]["chain"] == "ethereum"


def test_aggregate_hooks_empty():
    with tempfile.TemporaryDirectory() as tmpdir:
        hooks = aggregate_hooks(tmpdir)
        assert hooks == []


def test_aggregate_with_schema_valid(hook_dir):
    hooks = aggregate_hooks(hook_dir, schema=SCHEMA)
    assert len(hooks) == 2


def test_aggregate_with_schema_missing_section():
    with tempfile.TemporaryDirectory() as tmpdir:
        bad_hook = {"hook": _valid_hook()["hook"], "flags": _valid_hook()["flags"]}
        # missing "properties" section
        os.makedirs(os.path.join(tmpdir, "ethereum"))
        with open(os.path.join(tmpdir, "ethereum", "bad.json"), "w") as f:
            json.dump(bad_hook, f)
        with pytest.raises(ValueError, match="Schema validation failed"):
            aggregate_hooks(tmpdir, schema=SCHEMA)


def test_aggregate_with_schema_missing_flag():
    with tempfile.TemporaryDirectory() as tmpdir:
        hook = _valid_hook()
        del hook["flags"]["beforeSwap"]
        os.makedirs(os.path.join(tmpdir, "ethereum"))
        with open(os.path.join(tmpdir, "ethereum", "bad.json"), "w") as f:
            json.dump(hook, f)
        with pytest.raises(ValueError, match="Schema validation failed"):
            aggregate_hooks(tmpdir, schema=SCHEMA)


def test_filter_vanilla_swap_excludes_swap_hooks():
    swap_hook = _valid_hook()  # has beforeSwap=True, vanillaSwap=False
    vanilla_hook = _valid_hook(address="0x00000000000000000000000000000000000000A0")
    vanilla_hook["properties"]["vanillaSwap"] = True
    result = filter_vanilla_swap([swap_hook, vanilla_hook])
    assert len(result) == 1
    assert result[0]["hook"]["address"] == vanilla_hook["hook"]["address"]


def test_filter_vanilla_swap_excludes_returns_delta():
    hook = _valid_hook()
    hook["flags"]["beforeSwap"] = False
    hook["flags"]["afterSwap"] = False
    hook["flags"]["afterSwapReturnsDelta"] = True
    result = filter_vanilla_swap([hook])
    assert result == []


def test_filter_vanilla_swap_empty():
    assert filter_vanilla_swap([]) == []


def test_aggregate_with_schema_wrong_type():
    with tempfile.TemporaryDirectory() as tmpdir:
        hook = _valid_hook()
        hook["flags"]["beforeSwap"] = "yes"  # should be boolean
        os.makedirs(os.path.join(tmpdir, "ethereum"))
        with open(os.path.join(tmpdir, "ethereum", "bad.json"), "w") as f:
            json.dump(hook, f)
        with pytest.raises(ValueError, match="Schema validation failed"):
            aggregate_hooks(tmpdir, schema=SCHEMA)


def test_filter_vanilla_swap_includes_beforeSwap_with_vanillaSwap():
    """A hook with beforeSwap=True but vanillaSwap=True IS included."""
    hook = _valid_hook()  # has beforeSwap=True by default
    hook["properties"]["vanillaSwap"] = True
    result = filter_vanilla_swap([hook])
    assert len(result) == 1
    assert result[0]["hook"]["address"] == hook["hook"]["address"]


def test_filter_vanilla_swap_includes_governance_access_with_vanillaSwap():
    """Access control doesn't affect vanilla status."""
    hook = _valid_hook()
    hook["properties"]["vanillaSwap"] = True
    hook["properties"]["swapAccess"] = "governance"
    result = filter_vanilla_swap([hook])
    assert len(result) == 1


def test_schema_rejects_invalid_swapAccess():
    """Schema validation rejects an invalid swapAccess value."""
    with tempfile.TemporaryDirectory() as tmpdir:
        hook = _valid_hook()
        hook["properties"]["swapAccess"] = "invalid"
        os.makedirs(os.path.join(tmpdir, "ethereum"))
        with open(os.path.join(tmpdir, "ethereum", "bad.json"), "w") as f:
            json.dump(hook, f)
        with pytest.raises(ValueError, match="Schema validation failed"):
            aggregate_hooks(tmpdir, schema=SCHEMA)


# --- v1-lite join tests (append) ---
import verify_flags

RELEASE_L = {
    "project": "zora", "id": "creator-hook-2.2.1", "version": "2.2.1",
    "name": "Zora Creator Hook v2.2.1", "description": "release text",
    "source": {"verified": True, "auditUrl": "https://audit.example"},
    "properties": {"dynamicFee": True, "upgradeable": False,
                   "requiresCustomSwapData": False, "vanillaSwap": False,
                   "swapAccess": "none"},
    "warnings": [], "lifecycle": {"status": "active", "supersedes": None},
}
RELEASES_L = {"zora/creator-hook-2.2.1": RELEASE_L}
THIN_ADDR = "0x" + "a" * 36 + "20c0"


def test_resolve_thin_entry_joins_release():
    thin = {"hook": {"address": THIN_ADDR, "chain": "base", "chainId": 8453,
                     "release": "zora/creator-hook-2.2.1",
                     "description": "Fee: 35 bps."}}
    entry = aggregate.resolve_entry(thin, RELEASES_L)
    assert entry["hook"] == {
        "address": THIN_ADDR, "chain": "base", "chainId": 8453,
        "name": "Zora Creator Hook v2.2.1", "description": "release text Fee: 35 bps.",
        "deployer": "", "verifiedSource": True, "auditUrl": "https://audit.example",
    }
    assert entry["properties"] == RELEASE_L["properties"]
    assert entry["flags"] == verify_flags.decode_flags(THIN_ADDR)
    assert "release" not in entry["hook"]


def test_resolve_thin_without_description_uses_release_text():
    thin = {"hook": {"address": THIN_ADDR, "chain": "base", "chainId": 8453,
                     "release": "zora/creator-hook-2.2.1"}}
    entry = aggregate.resolve_entry(thin, RELEASES_L)
    assert entry["hook"]["description"] == "release text"


def test_resolve_thin_empty_string_description_uses_release_text_alone():
    thin = {"hook": {"address": THIN_ADDR, "chain": "base", "chainId": 8453,
                     "release": "zora/creator-hook-2.2.1", "description": ""}}
    entry = aggregate.resolve_entry(thin, RELEASES_L)
    assert entry["hook"]["description"] == "release text"


def test_resolve_thin_composed_description_capped_fragment_intact():
    long_release = dict(RELEASE_L, description="R" * 480)
    releases = {"zora/creator-hook-2.2.1": long_release}
    fragment = "Fee: 35 bps, referrer optional."
    thin = {"hook": {"address": THIN_ADDR, "chain": "base", "chainId": 8453,
                     "release": "zora/creator-hook-2.2.1", "description": fragment}}
    entry = aggregate.resolve_entry(thin, releases)
    description = entry["hook"]["description"]
    assert len(description) <= 500
    assert description.endswith(fragment)  # fragment is never truncated
    assert "…" in description  # release part was truncated


def test_resolve_full_with_pointer_strips_pointer_only():
    full = {"hook": {"address": THIN_ADDR, "chain": "base", "chainId": 8453,
                     "name": "Legacy Name", "description": "legacy", "deployer": "",
                     "verifiedSource": True, "auditUrl": "",
                     "release": "zora/creator-hook-2.2.1"},
            "flags": verify_flags.decode_flags(THIN_ADDR),
            "properties": RELEASE_L["properties"]}
    entry = aggregate.resolve_entry(full, RELEASES_L)
    assert entry["hook"]["name"] == "Legacy Name"       # legacy values preserved
    assert "release" not in entry["hook"]                # pointer never reaches v0
    assert entry["flags"] == full["flags"]


def test_resolve_full_without_pointer_is_identity():
    full = {"hook": {"address": THIN_ADDR, "chain": "base", "chainId": 8453,
                     "name": "N", "verifiedSource": True},
            "flags": verify_flags.decode_flags(THIN_ADDR),
            "properties": RELEASE_L["properties"]}
    assert aggregate.resolve_entry(full, RELEASES_L) == full


def test_resolve_unresolvable_pointer_raises():
    thin = {"hook": {"address": THIN_ADDR, "chain": "base", "chainId": 8453,
                     "release": "zora/nope-1.0"}}
    try:
        aggregate.resolve_entry(thin, RELEASES_L, label="hooks/base/x.json")
        assert False, "expected ValueError"
    except ValueError as e:
        assert "hooks/base/x.json" in str(e)
        assert "zora/nope-1.0" in str(e)


def test_aggregate_hooks_dangling_release_pointer_error_includes_filepath():
    # Fix E: aggregate_hooks must surface the offending filepath, not a bare
    # KeyError, when a hook file's release pointer doesn't resolve.
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = os.path.join(tmpdir, "base")
        os.makedirs(base_dir)
        thin_path = os.path.join(base_dir, "thinbad.json")
        with open(thin_path, "w") as f:
            json.dump({"hook": {"address": THIN_ADDR, "chain": "base", "chainId": 8453,
                                 "release": "zora/nope-1.0"}}, f)
        try:
            aggregate_hooks(tmpdir, releases={})
            assert False, "expected ValueError"
        except ValueError as e:
            assert "thinbad.json" in str(e)
            assert "zora/nope-1.0" in str(e)
