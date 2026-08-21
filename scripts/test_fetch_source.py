import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fetch_source
from fetch_source import get_explorer_url, fetch_and_parse


def test_get_explorer_url_etherscan_chain():
    url = get_explorer_url("ethereum")
    assert "etherscan" in url or "chainid=1" in url


def test_get_explorer_url_blockscout_chain():
    url = get_explorer_url("zora")
    assert "blockscout" in url or "zora" in url


def test_get_explorer_url_okx_chain():
    url = get_explorer_url("xlayer")
    assert "web3.okx.com" in url and "chainShortName=xlayer" in url


def test_get_explorer_url_new_chains():
    assert get_explorer_url("linea") == "https://api.etherscan.io/v2/api?chainid=59144"
    assert get_explorer_url("megaeth") == "https://api.etherscan.io/v2/api?chainid=4326"
    assert get_explorer_url("zksync") == "https://block-explorer-api.mainnet.zksync.io/api"


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


def test_fetch_and_parse_okx(tmp_path):
    """OKX responses use the OKX parser."""
    mock_response = {
        "data": [{
            "contractName": "OkxHook",
            "sourceCode": "contract OkxHook {}",
            "proxy": "0",
            "implementation": "",
        }]
    }
    response_file = tmp_path / "response.json"
    response_file.write_text(json.dumps(mock_response))

    meta = fetch_and_parse(str(response_file), outdir=str(tmp_path / "sources"), explorer_type="okx")

    assert meta["contractName"] == "OkxHook"
    assert meta["verified"] is True


def test_blockscout_v2_proxy_implementation_uses_native_v2_endpoint(tmp_path, monkeypatch):
    """Proxy resolution keeps both Blockscout requests on the native v2 API."""
    proxy_address = "0x1111111111111111111111111111111111111111"
    implementation_address = "0x2222222222222222222222222222222222222222"
    responses = [
        {
            "name": "ProxyHook",
            "is_verified": True,
            "file_path": "src/ProxyHook.sol",
            "source_code": "contract ProxyHook {}",
            "additional_sources": [],
            "proxy_type": "eip1967",
            "implementations": [{"address": implementation_address, "name": "ImplHook"}],
        },
        {
            "name": "ImplHook",
            "is_verified": True,
            "file_path": "src/ImplHook.sol",
            "source_code": "contract ImplHook {}",
            "additional_sources": [],
            "proxy_type": None,
            "implementations": [],
        },
    ]
    requested_urls = []

    def fake_curl(args, capture_output, text):
        requested_urls.append(args[-1])
        output_path = Path(args[args.index("-o") + 1])
        output_path.write_text(json.dumps(responses[len(requested_urls) - 1]))
        return subprocess.CompletedProcess(args, 0, stdout="200", stderr="")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(fetch_source.subprocess, "run", fake_curl)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "fetch_source.py",
            "robinhood",
            proxy_address,
            "--output",
            "source_meta.json",
            "--outdir",
            ".sources",
        ],
    )

    fetch_source.main()

    assert requested_urls == [
        f"https://robinhoodchain.blockscout.com/api/v2/smart-contracts/{proxy_address}",
        f"https://robinhoodchain.blockscout.com/api/v2/smart-contracts/{implementation_address}",
    ]
    assert json.loads(Path("source_meta.json").read_text())["contractName"] == "ImplHook"
    assert Path(".sources/src_ImplHook.sol").exists()
