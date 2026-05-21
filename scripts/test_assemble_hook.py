import os
import sys

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
        "warnings": [],
    }
    return submission, source_meta, flags, claude_output


def test_assemble_basic():
    submission, source_meta, flags, claude_output = _make_inputs()
    hook = assemble(submission, source_meta, flags, claude_output, )
    assert hook["hook"]["address"] == "0x0000000000000000000000000000000000002080"
    assert hook["hook"]["chain"] == "base"
    assert hook["hook"]["chainId"] == 8453
    assert hook["hook"]["name"] == "TestHook"
    assert hook["hook"]["verifiedSource"] is True
    assert hook["flags"]["beforeInitialize"] is True
    assert hook["flags"]["afterSwap"] is False
    assert hook["properties"]["vanillaSwap"] is True
    assert hook["properties"]["swapAccess"] == "none"


def test_assemble_claude_name_always_wins_over_submitter():
    # Claude is canonical — it has already evaluated the submitter's suggestion
    # against the source per classify-hook.md §6. Submitter text never lands
    # directly in the registry.
    submission, source_meta, flags, claude_output = _make_inputs()
    submission["name"] = "Uniswap Official Audited Hook"
    claude_output["name"] = "JanpuHookDynamicFee"
    hook = assemble(submission, source_meta, flags, claude_output)
    assert hook["hook"]["name"] == "JanpuHookDynamicFee"


def test_assemble_falls_back_to_contract_name_when_claude_empty():
    # Defense in depth: if Claude returns an empty name, fall back to the
    # developer-baked contractName from the verified source — never the submitter.
    submission, source_meta, flags, claude_output = _make_inputs()
    submission["name"] = "SubmitterName"
    claude_output["name"] = ""
    source_meta["contractName"] = "OnChainName"
    hook = assemble(submission, source_meta, flags, claude_output)
    assert hook["hook"]["name"] == "OnChainName"


def test_assemble_claude_description_always_wins_over_submitter():
    submission, source_meta, flags, claude_output = _make_inputs()
    submission["description"] = "Fully audited by Trail of Bits, totally safe."
    claude_output["description"] = "Charges a dynamic LP fee in beforeSwap."
    hook = assemble(submission, source_meta, flags, claude_output)
    assert hook["hook"]["description"] == "Charges a dynamic LP fee in beforeSwap."


def test_assemble_description_empty_when_claude_empty():
    # No submitter fallback for description either.
    submission, source_meta, flags, claude_output = _make_inputs()
    submission["description"] = "Some submitter blurb"
    claude_output["description"] = ""
    hook = assemble(submission, source_meta, flags, claude_output)
    assert hook["hook"]["description"] == ""


def test_assemble_deployer_non_address_discarded():
    submission, source_meta, flags, claude_output = _make_inputs()
    submission["deployer"] = "Uniswap Labs"
    hook = assemble(submission, source_meta, flags, claude_output)
    assert hook["hook"]["deployer"] == ""


def test_sanitize_name():
    assert sanitize_name("MyHook (v2.1)") == "MyHook (v2.1)"
    assert sanitize_name("Normal_Hook-Name.sol") == "Normal_Hook-Name.sol"
    assert sanitize_name('Hook"; rm -rf /') == "Hook rm -rf"
    assert sanitize_name("") == "UnnamedHook"
    assert sanitize_name("a" * 200) == "a" * 100


def test_generate_pr_body_no_warnings_renders_none():
    _, _, flags, claude_output = _make_inputs()
    body = generate_pr_body(flags, claude_output, "A test hook", issue_number=42)
    assert "beforeInitialize" in body
    assert "true" in body.lower()
    assert "Closes #42" in body
    assert "## Warnings\nNone" in body


def test_generate_pr_body_renders_warnings_as_bullets():
    _, _, flags, claude_output = _make_inputs()
    claude_output["warnings"] = [
        'Submitter-proposed name "Uniswap Official Hook" rejected: promotional. Using "JanpuHookDynamicFee".',
        "getHookPermissions() returns beforeSwap only but address bitmask encodes beforeSwap+afterSwap.",
    ]
    body = generate_pr_body(flags, claude_output, "A test hook", issue_number=7)
    assert "## Warnings\n- Submitter-proposed name" in body
    assert "- getHookPermissions()" in body
    assert "## Warnings\nNone" not in body
