import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parse_okx import parse


def test_parse_okx_verified(tmp_path):
    """Verified OKX response extracts source and metadata."""
    response = {
        "code": "0",
        "msg": "",
        "data": [
            {
                "sourceCode": "pragma solidity ^0.8.0; contract TestHook {}",
                "contractName": "TestHook",
                "proxy": "0",
                "implementation": "",
            }
        ],
    }
    response_file = tmp_path / "response.json"
    response_file.write_text(json.dumps(response))

    meta = parse(str(response_file), outdir=str(tmp_path / "sources"))

    assert meta["contractName"] == "TestHook"
    assert meta["verified"] is True
    assert meta["proxy"] is False
    assert os.path.exists(tmp_path / "sources" / "main.sol")


def test_parse_okx_proxy(tmp_path):
    """OKX proxy fields are preserved for implementation fetches."""
    response = {
        "code": "0",
        "msg": "",
        "data": [
            {
                "sourceCode": "contract Proxy {}",
                "contractName": "ProxyHook",
                "proxy": "1",
                "implementation": "0x1234567890abcdef1234567890abcdef12345678",
            }
        ],
    }
    response_file = tmp_path / "response.json"
    response_file.write_text(json.dumps(response))

    meta = parse(str(response_file), outdir=str(tmp_path / "sources"))

    assert meta["proxy"] is True
    assert meta["implementation"] == "0x1234567890abcdef1234567890abcdef12345678"


def test_parse_okx_not_verified(tmp_path):
    """Missing OKX source returns verified=False."""
    response = {"code": "0", "msg": "", "data": [{"contractName": "", "sourceCode": ""}]}
    response_file = tmp_path / "response.json"
    response_file.write_text(json.dumps(response))

    meta = parse(str(response_file), outdir=str(tmp_path / "sources"))

    assert meta["verified"] is False
