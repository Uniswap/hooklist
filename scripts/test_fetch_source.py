import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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


# --- fetch_with_retry ---

from fetch_source import fetch_with_retry


def _fake_curl(script, monkeypatch):
    """Fake subprocess.run for curl. script is a list of (http_code, body);
    http_code None simulates a curl-level failure (nonzero exit)."""
    import fetch_source as fs
    calls = []
    sleeps = []

    def fake_run(cmd, capture_output=True, text=True):
        idx = min(len(calls), len(script) - 1)
        calls.append(list(cmd))
        code, body = script[idx]
        out_path = cmd[cmd.index("-o") + 1]

        class Result:
            pass

        r = Result()
        if code is None:
            r.returncode = 56
            r.stdout = ""
            r.stderr = "curl: (56) connection reset"
            return r
        with open(out_path, "w") as f:
            f.write(body)
        r.returncode = 0
        r.stdout = str(code)
        r.stderr = ""
        return r

    monkeypatch.setattr(fs.subprocess, "run", fake_run)
    monkeypatch.setattr(fs.time, "sleep", lambda s: sleeps.append(s))
    return calls, sleeps


def test_fetch_with_retry_success_first_try(tmp_path, monkeypatch):
    calls, sleeps = _fake_curl([(200, '{"message":"OK"}')], monkeypatch)
    out = str(tmp_path / "resp.json")
    code = fetch_with_retry("http://example/api", out)
    assert code == "200"
    assert len(calls) == 1
    assert sleeps == []


def test_fetch_with_retry_transient_500_then_success(tmp_path, monkeypatch):
    """Blockscout intermittent 500s are retried until a good response."""
    calls, sleeps = _fake_curl(
        [(500, '{"message":"Something went wrong.","result":null,"status":"0"}'),
         (500, '{"message":"Something went wrong.","result":null,"status":"0"}'),
         (200, '{"message":"OK","result":[{}]}')],
        monkeypatch,
    )
    out = str(tmp_path / "resp.json")
    code = fetch_with_retry("http://example/api", out)
    assert code == "200"
    assert len(calls) == 3
    assert len(sleeps) == 2
    assert json.load(open(out))["message"] == "OK"


def test_fetch_with_retry_rate_limit_429(tmp_path, monkeypatch):
    calls, _ = _fake_curl([(429, "rate limited"), (200, '{"ok":1}')], monkeypatch)
    code = fetch_with_retry("http://example/api", str(tmp_path / "r.json"))
    assert code == "200"
    assert len(calls) == 2


def test_fetch_with_retry_curl_failure_retried(tmp_path, monkeypatch):
    calls, _ = _fake_curl([(None, ""), (200, '{"ok":1}')], monkeypatch)
    code = fetch_with_retry("http://example/api", str(tmp_path / "r.json"))
    assert code == "200"
    assert len(calls) == 2


def test_fetch_with_retry_empty_body_retried(tmp_path, monkeypatch):
    """An empty 200 response (observed from Robinhood Blockscout) is transient."""
    calls, _ = _fake_curl([(200, ""), (200, '{"ok":1}')], monkeypatch)
    code = fetch_with_retry("http://example/api", str(tmp_path / "r.json"))
    assert code == "200"
    assert len(calls) == 2


def test_fetch_with_retry_gives_up_after_max_attempts(tmp_path, monkeypatch):
    calls, sleeps = _fake_curl([(500, '{"message":"Something went wrong."}')], monkeypatch)
    code = fetch_with_retry("http://example/api", str(tmp_path / "r.json"), max_attempts=5)
    assert code == "500"
    assert len(calls) == 5
    assert len(sleeps) == 4


def test_fetch_with_retry_404_not_retried(tmp_path, monkeypatch):
    """404 (e.g. Sourcify not-found) is a definitive answer, not transient."""
    calls, _ = _fake_curl([(404, '{"error":"not found"}')], monkeypatch)
    code = fetch_with_retry("http://example/api", str(tmp_path / "r.json"))
    assert code == "404"
    assert len(calls) == 1
