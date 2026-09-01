# scripts/test_assemble_thin.py
import json
import os
import assemble_hook

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SUBMISSION = {"chain": "celo", "address": "0x" + "a" * 36 + "20c0",
              "deployer": "", "auditUrl": ""}
SOURCE_META = {"verified": True, "contractName": "TestHook"}
FLAGS = {k: False for k in [
    "beforeInitialize", "afterInitialize", "beforeAddLiquidity", "afterAddLiquidity",
    "beforeRemoveLiquidity", "afterRemoveLiquidity", "beforeSwap", "afterSwap",
    "beforeDonate", "afterDonate", "beforeSwapReturnsDelta", "afterSwapReturnsDelta",
    "afterAddLiquidityReturnsDelta", "afterRemoveLiquidityReturnsDelta"]}
FLAGS["beforeInitialize"] = True
FLAGS["beforeSwap"] = True
FLAGS["afterSwap"] = True
CLAUDE_FULL = {"name": "TestHook", "description": "d", "dynamicFee": False,
               "upgradeable": False, "requiresCustomSwapData": False,
               "vanillaSwap": True, "swapAccess": "none", "warnings": []}


def _setup_repo(tmp_path):
    """Copy the schemas + chains.json into an isolated repo root so tests
    never write into the real releases/ directory."""
    for name in ("schema.json", "release.schema.json", "chains.json"):
        (tmp_path / name).write_text(open(os.path.join(ROOT, name)).read())
    return str(tmp_path)


def _make_release(tmp_release_dir):
    release = {
        "project": "testproj", "id": "test-hook-1.0", "version": "1.0",
        "name": "Test Hook v1.0", "description": "release text",
        "source": {"verified": True},
        "properties": {"dynamicFee": False, "upgradeable": False,
                       "requiresCustomSwapData": False, "vanillaSwap": True,
                       "swapAccess": "none"},
        "warnings": [], "lifecycle": {"status": "active", "supersedes": None},
    }
    os.makedirs(tmp_release_dir, exist_ok=True)
    with open(os.path.join(tmp_release_dir, "test-hook-1.0.json"), "w") as f:
        json.dump(release, f)


def test_no_release_field_keeps_full_form(tmp_path):
    repo_root = _setup_repo(tmp_path)
    hook = assemble_hook.assemble(SUBMISSION, SOURCE_META, FLAGS, dict(CLAUDE_FULL),
                                   repo_root=repo_root)
    assert hook["hook"]["name"] == "TestHook"
    assert "release" not in hook["hook"]
    assert hook["properties"]["vanillaSwap"] is True


def test_release_match_emits_thin_file(tmp_path):
    repo_root = _setup_repo(tmp_path)
    rel_dir = os.path.join(repo_root, "releases", "testproj")
    _make_release(rel_dir)
    claude = dict(CLAUDE_FULL, release="testproj/test-hook-1.0",
                  description="Fee: 35 bps.")
    hook = assemble_hook.assemble(SUBMISSION, SOURCE_META, FLAGS, claude,
                                   repo_root=repo_root)
    assert hook == {"hook": {
        "address": SUBMISSION["address"], "chain": "celo", "chainId": 42220,
        "release": "testproj/test-hook-1.0", "description": "Fee: 35 bps."}}


def test_dangling_release_ref_raises(tmp_path):
    repo_root = _setup_repo(tmp_path)
    claude = dict(CLAUDE_FULL, release="testproj/does-not-exist-9.9")
    try:
        assemble_hook.assemble(SUBMISSION, SOURCE_META, FLAGS, claude, repo_root=repo_root)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_release_properties_match_emits_thin_file(tmp_path):
    repo_root = _setup_repo(tmp_path)
    rel_dir = os.path.join(repo_root, "releases", "testproj")
    _make_release(rel_dir)
    claude = dict(CLAUDE_FULL, release="testproj/test-hook-1.0",
                  description="Fee: 35 bps.")
    hook = assemble_hook.assemble(SUBMISSION, SOURCE_META, FLAGS, claude,
                                   repo_root=repo_root)
    assert hook["hook"]["release"] == "testproj/test-hook-1.0"
    assert "properties" not in hook


def test_release_properties_mismatch_raises_naming_field(tmp_path):
    repo_root = _setup_repo(tmp_path)
    rel_dir = os.path.join(repo_root, "releases", "testproj")
    _make_release(rel_dir)
    claude = dict(CLAUDE_FULL, release="testproj/test-hook-1.0",
                  dynamicFee=True)
    try:
        assemble_hook.assemble(SUBMISSION, SOURCE_META, FLAGS, claude, repo_root=repo_root)
        assert False, "expected ValueError"
    except ValueError as e:
        assert "dynamicFee" in str(e)
