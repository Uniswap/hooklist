import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parse_sourcify import parse


def test_parse_sourcify_verified(tmp_path):
    """Verified Sourcify response extracts sources and metadata."""
    response = {
        "match": "exact_match",
        "chainId": "4217",
        "address": "0x1234567890abcdef1234567890abcdef12345678",
        "name": "TestHook",
        "sources": {
            "src/TestHook.sol": {"content": "pragma solidity ^0.8.0; contract TestHook {}"},
            "lib/Base.sol": {"content": "pragma solidity ^0.8.0; contract Base {}"},
        },
    }
    response_file = tmp_path / "response.json"
    response_file.write_text(json.dumps(response))

    meta = parse(str(response_file), outdir=str(tmp_path / "sources"))

    assert meta["contractName"] == "TestHook"
    assert meta["verified"] is True
    assert meta["proxy"] is False
    assert os.path.exists(tmp_path / "sources" / "src_TestHook.sol")
    assert os.path.exists(tmp_path / "sources" / "lib_Base.sol")


def test_parse_sourcify_partial_match(tmp_path):
    """Partial match is still considered verified."""
    response = {
        "match": "partial_match",
        "chainId": "4217",
        "address": "0x1234567890abcdef1234567890abcdef12345678",
        "name": "PartialHook",
        "sources": {
            "Contract.sol": {"content": "contract PartialHook {}"},
        },
    }
    response_file = tmp_path / "response.json"
    response_file.write_text(json.dumps(response))

    meta = parse(str(response_file), outdir=str(tmp_path / "sources"))

    assert meta["verified"] is True
    assert meta["contractName"] == "PartialHook"


def test_parse_sourcify_not_verified(tmp_path):
    """Error response returns verified=False."""
    response = {"error": "not found"}
    response_file = tmp_path / "response.json"
    response_file.write_text(json.dumps(response))

    meta = parse(str(response_file), outdir=str(tmp_path / "sources"))

    assert meta["verified"] is False
    assert meta["contractName"] == ""


def test_parse_sourcify_proxy(tmp_path):
    """Proxy resolution is detected."""
    response = {
        "match": "exact_match",
        "chainId": "4217",
        "address": "0x1234567890abcdef1234567890abcdef12345678",
        "name": "ProxyHook",
        "sources": {"Proxy.sol": {"content": "contract Proxy {}"}},
        "proxyResolution": {
            "implementations": [
                {"address": "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"}
            ]
        },
    }
    response_file = tmp_path / "response.json"
    response_file.write_text(json.dumps(response))

    meta = parse(str(response_file), outdir=str(tmp_path / "sources"))

    assert meta["proxy"] is True
    assert meta["implementation"] == "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"


def test_parse_sourcify_no_proxy_resolution(tmp_path):
    """No proxyResolution field means not a proxy."""
    response = {
        "match": "exact_match",
        "chainId": "4217",
        "address": "0x1234567890abcdef1234567890abcdef12345678",
        "name": "SimpleHook",
        "sources": {"Hook.sol": {"content": "contract SimpleHook {}"}},
    }
    response_file = tmp_path / "response.json"
    response_file.write_text(json.dumps(response))

    meta = parse(str(response_file), outdir=str(tmp_path / "sources"))

    assert meta["proxy"] is False
    assert meta["implementation"] == ""


def test_parse_sourcify_path_sanitization(tmp_path):
    """Suspicious paths are sanitized."""
    response = {
        "match": "exact_match",
        "name": "Hook",
        "sources": {
            "../../etc/passwd": {"content": "malicious"},
            "normal.sol": {"content": "safe"},
        },
    }
    response_file = tmp_path / "response.json"
    response_file.write_text(json.dumps(response))

    meta = parse(str(response_file), outdir=str(tmp_path / "sources"))

    assert meta["verified"] is True
    assert os.path.exists(tmp_path / "sources" / "normal.sol")
    # The traversal path should be sanitized to just the basename
    source_files = os.listdir(tmp_path / "sources")
    for f in source_files:
        assert not f.startswith(".")
