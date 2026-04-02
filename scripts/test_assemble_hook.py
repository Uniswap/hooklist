import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from assemble_hook import assemble, sanitize_name, generate_pr_body


def _make_inputs():
    submission = {
        "chain": "base",
        "address": "0x0000000000000000000000000000000000002080",
        "name": "TestHook",
        "description": "A test hook",
        "deployer": "0x1234567890abcdef1234567890abcdef12345678",
        "auditUrl": "https://example.com/audit",
    }
    source_meta = {
        "contractName": "TestHookContract",
        "verified": True,
        "proxy": False,
        "implementation": "",
    }
    flags = {
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
    }
    claude_output = {
        "name": "TestHook",
        "description": "A hook that tests things",
        "dynamicFee": False,
        "upgradeable": False,
        "requiresCustomSwapData": False,
        "vanillaSwap": True,
        "swapAccess": "none",
    }
    return submission, source_meta, flags, claude_output


def test_assemble_basic():
    submission, source_meta, flags, claude_output = _make_inputs()
    hook = assemble(submission, source_meta, flags, claude_output, issue_number=42)
    assert hook["hook"]["address"] == "0x0000000000000000000000000000000000002080"
    assert hook["hook"]["chain"] == "base"
    assert hook["hook"]["chainId"] == 8453
    assert hook["hook"]["name"] == "TestHook"
    assert hook["hook"]["verifiedSource"] is True
    assert hook["flags"]["beforeInitialize"] is True
    assert hook["flags"]["afterSwap"] is False
    assert hook["properties"]["vanillaSwap"] is True
    assert hook["properties"]["swapAccess"] == "none"


def test_assemble_uses_submitter_name_over_claude():
    submission, source_meta, flags, claude_output = _make_inputs()
    submission["name"] = "SubmitterName"
    claude_output["name"] = "ClaudeName"
    hook = assemble(submission, source_meta, flags, claude_output, issue_number=1)
    assert hook["hook"]["name"] == "SubmitterName"


def test_assemble_falls_back_to_claude_name():
    submission, source_meta, flags, claude_output = _make_inputs()
    submission["name"] = ""
    claude_output["name"] = "ClaudeName"
    hook = assemble(submission, source_meta, flags, claude_output, issue_number=1)
    assert hook["hook"]["name"] == "ClaudeName"


def test_assemble_falls_back_to_contract_name():
    submission, source_meta, flags, claude_output = _make_inputs()
    submission["name"] = ""
    claude_output["name"] = ""
    source_meta["contractName"] = "OnChainName"
    hook = assemble(submission, source_meta, flags, claude_output, issue_number=1)
    assert hook["hook"]["name"] == "OnChainName"


def test_assemble_uses_submitter_description_over_claude():
    submission, source_meta, flags, claude_output = _make_inputs()
    submission["description"] = "User desc"
    claude_output["description"] = "Claude desc"
    hook = assemble(submission, source_meta, flags, claude_output, issue_number=1)
    assert hook["hook"]["description"] == "User desc"


def test_assemble_deployer_non_address_discarded():
    submission, source_meta, flags, claude_output = _make_inputs()
    submission["deployer"] = "Uniswap Labs"
    hook = assemble(submission, source_meta, flags, claude_output, issue_number=1)
    assert hook["hook"]["deployer"] == ""


def test_sanitize_name():
    assert sanitize_name("MyHook (v2.1)") == "MyHook (v2.1)"
    assert sanitize_name("Normal_Hook-Name.sol") == "Normal_Hook-Name.sol"
    assert sanitize_name('Hook"; rm -rf /') == "Hook rm -rf"
    assert sanitize_name("") == "UnnamedHook"
    assert sanitize_name("a" * 200) == "a" * 100


def test_generate_pr_body():
    _, source_meta, flags, claude_output = _make_inputs()
    body = generate_pr_body(flags, claude_output, "A test hook", issue_number=42)
    assert "beforeInitialize" in body
    assert "true" in body.lower()
    assert "Closes #42" in body
