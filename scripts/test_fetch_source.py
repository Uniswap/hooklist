import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fetch_source import get_explorer_url, fetch_and_parse


def test_get_explorer_url_etherscan_chain():
    url = get_explorer_url("ethereum")
    assert "etherscan" in url or "chainid=1" in url


def test_get_explorer_url_blockscout_chain():
    url = get_explorer_url("zora")
    assert "blockscout" in url or "zora" in url


def test_get_explorer_url_unknown_chain():
    import pytest
    with pytest.raises(KeyError):
        get_explorer_url("solana")


def test_fetch_and_parse_verified(tmp_path):
    """Mock a verified single-file Etherscan response."""
    mock_response = {
        "result": [{
            "ContractName": "TestHook",
            "SourceCode": "pragma solidity ^0.8.0; contract TestHook {}",
            "Proxy": "0",
            "Implementation": "",
        }]
    }
    response_file = tmp_path / "response.json"
    response_file.write_text(json.dumps(mock_response))

    meta = fetch_and_parse(str(response_file), outdir=str(tmp_path / "sources"))

    assert meta["contractName"] == "TestHook"
    assert meta["verified"] is True
    assert meta["proxy"] is False
    assert os.path.exists(tmp_path / "sources" / "main.sol")


def test_fetch_and_parse_not_verified(tmp_path):
    """Unverified contract returns verified=False."""
    mock_response = {
        "result": [{
            "ContractName": "",
            "SourceCode": "",
            "Proxy": "0",
            "Implementation": "",
        }]
    }
    response_file = tmp_path / "response.json"
    response_file.write_text(json.dumps(mock_response))

    meta = fetch_and_parse(str(response_file), outdir=str(tmp_path / "sources"))

    assert meta["verified"] is False


def test_fetch_and_parse_proxy(tmp_path):
    """Proxy contract is detected."""
    mock_response = {
        "result": [{
            "ContractName": "ProxyHook",
            "SourceCode": "contract Proxy {}",
            "Proxy": "1",
            "Implementation": "0x1234567890abcdef1234567890abcdef12345678",
        }]
    }
    response_file = tmp_path / "response.json"
    response_file.write_text(json.dumps(mock_response))

    meta = fetch_and_parse(str(response_file), outdir=str(tmp_path / "sources"))

    assert meta["proxy"] is True
    assert meta["implementation"] == "0x1234567890abcdef1234567890abcdef12345678"
