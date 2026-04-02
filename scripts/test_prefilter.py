import json
import os
import tempfile
import pytest

sys_path_hack = os.path.dirname(os.path.abspath(__file__))
import sys
sys.path.insert(0, sys_path_hack)

from prefilter import parse_issue_body, validate_submission, CHAINS


def test_parse_issue_body_standard():
    body = (
        "### Chain\n\nethereum\n\n"
        "### Hook Address\n\n0x00bbc6fc07342cf80d14b60695cf0e1aa8de00cc\n\n"
        "### Hook Name\n\nMyHook\n\n"
        "### Description\n\nA cool hook\n\n"
        "### Deployer Address\n\n0x1234567890abcdef1234567890abcdef12345678\n\n"
        "### Audit URL\n\nhttps://example.com/audit\n"
    )
    result = parse_issue_body(body)
    assert result["chain"] == "ethereum"
    assert result["address"] == "0x00bbc6fc07342cf80d14b60695cf0e1aa8de00cc"
    assert result["name"] == "MyHook"
    assert result["description"] == "A cool hook"
    assert result["deployer"] == "0x1234567890abcdef1234567890abcdef12345678"
    assert result["auditUrl"] == "https://example.com/audit"


def test_parse_issue_body_optional_fields_blank():
    body = (
        "### Chain\n\nbase\n\n"
        "### Hook Address\n\n0x167f77c0d015414f65bf3dde7198922c399e2080\n\n"
        "### Hook Name\n\n_No response_\n\n"
        "### Description\n\n_No response_\n\n"
        "### Deployer Address\n\n_No response_\n\n"
        "### Audit URL\n\n_No response_\n"
    )
    result = parse_issue_body(body)
    assert result["chain"] == "base"
    assert result["address"] == "0x167f77c0d015414f65bf3dde7198922c399e2080"
    assert result["name"] == ""
    assert result["description"] == ""
    assert result["deployer"] == ""
    assert result["auditUrl"] == ""


def test_validate_submission_valid():
    submission = {
        "chain": "base",
        "address": "0x0000000000000000000000000000000000002080",
        "name": "TestHook",
        "description": "",
        "deployer": "",
        "auditUrl": "",
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        errors = validate_submission(submission, hooks_dir=tmpdir)
    assert errors == []


def test_validate_submission_bad_address():
    submission = {
        "chain": "base",
        "address": "not-an-address",
        "name": "",
        "description": "",
        "deployer": "",
        "auditUrl": "",
    }
    errors = validate_submission(submission, hooks_dir="/nonexistent")
    assert any("address" in e.lower() for e in errors)


def test_validate_submission_bad_chain():
    submission = {
        "chain": "solana",
        "address": "0x0000000000000000000000000000000000002080",
        "name": "",
        "description": "",
        "deployer": "",
        "auditUrl": "",
    }
    errors = validate_submission(submission, hooks_dir="/nonexistent")
    assert any("chain" in e.lower() for e in errors)


def test_validate_submission_duplicate():
    submission = {
        "chain": "ethereum",
        "address": "0x0000000000000000000000000000000000002080",
        "name": "",
        "description": "",
        "deployer": "",
        "auditUrl": "",
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        chain_dir = os.path.join(tmpdir, "ethereum")
        os.makedirs(chain_dir)
        with open(os.path.join(chain_dir, "0x0000000000000000000000000000000000002080.json"), "w") as f:
            f.write("{}")
        errors = validate_submission(submission, hooks_dir=tmpdir)
    assert any("already" in e.lower() for e in errors)


def test_validate_submission_bad_deployer():
    submission = {
        "chain": "base",
        "address": "0x0000000000000000000000000000000000002080",
        "name": "",
        "description": "",
        "deployer": "Uniswap Labs",
        "auditUrl": "",
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        errors = validate_submission(submission, hooks_dir=tmpdir)
    assert any("deployer" in e.lower() for e in errors)


def test_validate_submission_bad_audit_url():
    submission = {
        "chain": "base",
        "address": "0x0000000000000000000000000000000000002080",
        "name": "",
        "description": "",
        "deployer": "",
        "auditUrl": "ftp://evil.com",
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        errors = validate_submission(submission, hooks_dir=tmpdir)
    assert any("audit" in e.lower() for e in errors)


def test_chains_matches_chains_json():
    """The CHAINS set in prefilter.py must match chains.json."""
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(repo_root, "chains.json")) as f:
        chains_json = json.load(f)
    assert CHAINS == set(chains_json.keys())
