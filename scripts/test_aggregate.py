import json
import os
import tempfile
import pytest
from aggregate import aggregate_hooks


@pytest.fixture
def hook_dir():
    """Create a temp directory with sample hook files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        eth_dir = os.path.join(tmpdir, "hooks", "ethereum")
        base_dir = os.path.join(tmpdir, "hooks", "base")
        os.makedirs(eth_dir)
        os.makedirs(base_dir)

        hook1 = {
            "hook": {
                "address": "0x0000000000000000000000000000000000002080",
                "chain": "ethereum",
                "chainId": 1,
                "name": "TestHook",
                "description": "A test hook",
                "deployer": "",
                "verifiedSource": True,
                "auditUrl": ""
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
                "afterRemoveLiquidityReturnsDelta": False
            },
            "properties": {
                "dynamicFee": False,
                "upgradeable": False,
                "requiresCustomSwapData": False
            }
        }

        hook2 = {
            "hook": {
                "address": "0x00000000000000000000000000000000000000C0",
                "chain": "base",
                "chainId": 8453,
                "name": "SwapHook",
                "description": "A swap hook",
                "deployer": "",
                "verifiedSource": True,
                "auditUrl": ""
            },
            "flags": {
                "beforeInitialize": False,
                "afterInitialize": False,
                "beforeAddLiquidity": False,
                "afterAddLiquidity": False,
                "beforeRemoveLiquidity": False,
                "afterRemoveLiquidity": False,
                "beforeSwap": True,
                "afterSwap": True,
                "beforeDonate": False,
                "afterDonate": False,
                "beforeSwapReturnsDelta": False,
                "afterSwapReturnsDelta": False,
                "afterAddLiquidityReturnsDelta": False,
                "afterRemoveLiquidityReturnsDelta": False
            },
            "properties": {
                "dynamicFee": False,
                "upgradeable": False,
                "requiresCustomSwapData": False
            }
        }

        with open(os.path.join(eth_dir, "0x0000000000000000000000000000000000002080.json"), "w") as f:
            json.dump(hook1, f)
        with open(os.path.join(base_dir, "0x00000000000000000000000000000000000000C0.json"), "w") as f:
            json.dump(hook2, f)

        yield tmpdir


def test_aggregate_hooks(hook_dir):
    hooks = aggregate_hooks(os.path.join(hook_dir, "hooks"))
    assert len(hooks) == 2
    chains = {h["hook"]["chain"] for h in hooks}
    assert chains == {"ethereum", "base"}


def test_aggregate_hooks_sorted_by_chain_then_address(hook_dir):
    hooks = aggregate_hooks(os.path.join(hook_dir, "hooks"))
    assert hooks[0]["hook"]["chain"] == "base"
    assert hooks[1]["hook"]["chain"] == "ethereum"


def test_aggregate_hooks_empty():
    with tempfile.TemporaryDirectory() as tmpdir:
        hooks = aggregate_hooks(tmpdir)
        assert hooks == []


