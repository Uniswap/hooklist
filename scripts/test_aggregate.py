import json
import os
import tempfile
import pytest
from aggregate import aggregate_hooks


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
            "required": ["dynamicFee", "upgradeable", "requiresCustomSwapData"],
            "properties": {
                "dynamicFee": {"type": "boolean"},
                "upgradeable": {"type": "boolean"},
                "requiresCustomSwapData": {"type": "boolean"},
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


def test_aggregate_with_schema_wrong_type():
    with tempfile.TemporaryDirectory() as tmpdir:
        hook = _valid_hook()
        hook["flags"]["beforeSwap"] = "yes"  # should be boolean
        os.makedirs(os.path.join(tmpdir, "ethereum"))
        with open(os.path.join(tmpdir, "ethereum", "bad.json"), "w") as f:
            json.dump(hook, f)
        with pytest.raises(ValueError, match="Schema validation failed"):
            aggregate_hooks(tmpdir, schema=SCHEMA)
