import hashlib

import pytest

import fetch_codehash as fc

# A well-shaped 40-hex-char address for tests that go through fetch_code()
# (which now charset-validates its address argument). Low-level helper tests
# below (_fetch_via_explorer / _fetch_via_rpc) bypass that validation
# entirely and intentionally keep using the toy "0xabc" address.
VALID_ADDR = "0x" + "ab" * 20


# --- codehash_of ------------------------------------------------------

def test_codehash_of_hashes_raw_bytes():
    expected = "sha256:" + hashlib.sha256(bytes.fromhex("6001")).hexdigest()
    assert fc.codehash_of("0x6001") == expected


def test_codehash_of_none_for_empty_code():
    assert fc.codehash_of("0x") is None
    assert fc.codehash_of("0X") is None


def test_codehash_of_none_for_none_input():
    assert fc.codehash_of(None) is None


def test_codehash_of_case_insensitive_prefix():
    # Same bytes regardless of 0x/0X and hex case; hash matches.
    lower = fc.codehash_of("0x6001")
    upper = fc.codehash_of("0X6001")
    assert lower == upper


# --- explorer-path parsing ---------------------------------------------

def test_fetch_via_explorer_parses_result():
    calls = []

    def fake_get(url, payload):
        calls.append((url, payload))
        return {"status": "1", "message": "OK", "result": "0x6001"}

    chain_info = {"explorer": "etherscan", "explorerUrl": "https://api.etherscan.io/v2/api?chainid=1"}
    code = fc._fetch_via_explorer(chain_info, "0xabc", fake_get)
    assert code == "0x6001"
    # GET call (payload None), correct module/action params, address included.
    url, payload = calls[0]
    assert payload is None
    assert "module=proxy" in url
    assert "action=eth_getCode" in url
    assert "address=0xabc" in url
    assert "tag=latest" in url


def test_fetch_via_explorer_appends_api_key_when_set(monkeypatch):
    monkeypatch.setenv("ETHERSCAN_API_KEY", "mykey")
    captured = {}

    def fake_get(url, payload):
        captured["url"] = url
        return {"result": "0x6001"}

    chain_info = {"explorer": "etherscan", "explorerUrl": "https://api.etherscan.io/v2/api?chainid=1"}
    fc._fetch_via_explorer(chain_info, "0xabc", fake_get)
    assert "apikey=mykey" in captured["url"]


def test_fetch_via_explorer_no_api_key_omits_param(monkeypatch):
    monkeypatch.delenv("ETHERSCAN_API_KEY", raising=False)
    captured = {}

    def fake_get(url, payload):
        captured["url"] = url
        return {"result": "0x6001"}

    chain_info = {"explorer": "etherscan", "explorerUrl": "https://api.etherscan.io/v2/api?chainid=1"}
    fc._fetch_via_explorer(chain_info, "0xabc", fake_get)
    assert "apikey=" not in captured["url"]


def test_fetch_via_explorer_skips_non_proxy_explorer_types():
    def fake_get(url, payload):
        raise AssertionError("should not be called for okx/sourcify explorer types")

    for explorer_type in ("okx", "sourcify", "zksync"):
        chain_info = {"explorer": explorer_type, "explorerUrl": "https://example.com/api"}
        assert fc._fetch_via_explorer(chain_info, "0xabc", fake_get) is None


def test_fetch_via_explorer_rejects_error_response():
    def fake_get(url, payload):
        return {"status": "0", "message": "NOTOK", "result": "Missing/Invalid API Key"}

    chain_info = {"explorer": "etherscan", "explorerUrl": "https://api.etherscan.io/v2/api?chainid=1"}
    assert fc._fetch_via_explorer(chain_info, "0xabc", fake_get) is None


def test_fetch_via_explorer_uses_ampersand_when_url_has_query_string():
    # Etherscan-style explorerUrls already embed "?chainid=..." — the
    # module=proxy... segment must join with "&", not "?".
    captured = {}

    def fake_get(url, payload):
        captured["url"] = url
        return {"result": "0x6001"}

    chain_info = {"explorer": "etherscan", "explorerUrl": "https://api.etherscan.io/v2/api?chainid=1"}
    fc._fetch_via_explorer(chain_info, "0xabc", fake_get)
    assert "api?chainid=1&module=proxy" in captured["url"]
    assert "??" not in captured["url"]


def test_fetch_via_explorer_uses_question_mark_when_url_has_no_query_string():
    # Blockscout/routescan explorerUrls (e.g. soneium/zora/avalanche) have no
    # query string at all — the module=proxy... segment must start with "?",
    # not be dangled onto the bare path with "&" (which produced dead URLs).
    captured = {}

    def fake_get(url, payload):
        captured["url"] = url
        return {"result": "0x6001"}

    chain_info = {"explorer": "blockscout", "explorerUrl": "https://soneium.blockscout.com/api"}
    fc._fetch_via_explorer(chain_info, "0xabc", fake_get)
    assert captured["url"] == (
        "https://soneium.blockscout.com/api?module=proxy&action=eth_getCode"
        "&address=0xabc&tag=latest"
    )


def test_fetch_via_explorer_omits_api_key_for_blockscout(monkeypatch):
    # The API key is only meaningful (and only should be sent) to etherscan —
    # blockscout/routescan/zora hosts don't need it and shouldn't receive it.
    monkeypatch.setenv("ETHERSCAN_API_KEY", "mykey")
    captured = {}

    def fake_get(url, payload):
        captured["url"] = url
        return {"result": "0x6001"}

    chain_info = {"explorer": "blockscout", "explorerUrl": "https://soneium.blockscout.com/api"}
    fc._fetch_via_explorer(chain_info, "0xabc", fake_get)
    assert "apikey" not in captured["url"]


def test_fetch_via_explorer_omits_api_key_for_routescan(monkeypatch):
    monkeypatch.setenv("ETHERSCAN_API_KEY", "mykey")
    captured = {}

    def fake_get(url, payload):
        captured["url"] = url
        return {"result": "0x6001"}

    chain_info = {
        "explorer": "routescan",
        "explorerUrl": "https://api.routescan.io/v2/network/mainnet/evm/43114/etherscan/api",
    }
    fc._fetch_via_explorer(chain_info, "0xabc", fake_get)
    assert "apikey" not in captured["url"]


def test_fetch_via_explorer_rejects_error_key():
    def fake_get(url, payload):
        return {"error": "not found"}

    chain_info = {"explorer": "blockscout", "explorerUrl": "https://example.blockscout.com/api"}
    assert fc._fetch_via_explorer(chain_info, "0xabc", fake_get) is None


def test_fetch_via_explorer_none_on_exception():
    def fake_get(url, payload):
        raise OSError("network down")

    chain_info = {"explorer": "etherscan", "explorerUrl": "https://api.etherscan.io/v2/api?chainid=1"}
    assert fc._fetch_via_explorer(chain_info, "0xabc", fake_get, sleep=lambda s: None) is None


# --- retry/backoff -------------------------------------------------------

def test_fetch_via_explorer_retries_then_succeeds():
    calls = []

    def flaky_get(url, payload):
        calls.append(1)
        if len(calls) < 3:
            raise OSError("transient")
        return {"result": "0x6001"}

    sleeps = []
    chain_info = {"explorer": "etherscan", "explorerUrl": "https://api.etherscan.io/v2/api?chainid=1"}
    code = fc._fetch_via_explorer(chain_info, "0xabc", flaky_get, sleep=sleeps.append)
    assert code == "0x6001"
    assert len(calls) == 3
    assert sleeps == [1, 3]


def test_fetch_via_rpc_retries_then_succeeds():
    calls = []

    def flaky_get(url, payload):
        calls.append(1)
        if len(calls) < 3:
            raise OSError("transient")
        return {"result": "0x6002"}

    sleeps = []
    code = fc._fetch_via_rpc("ethereum", "0xabc", flaky_get, sleep=sleeps.append)
    assert code == "0x6002"
    assert len(calls) == 3
    assert sleeps == [1, 3]


def test_fetch_via_explorer_gives_up_after_max_attempts():
    calls = []

    def always_fails(url, payload):
        calls.append(1)
        raise OSError("down")

    chain_info = {"explorer": "etherscan", "explorerUrl": "https://api.etherscan.io/v2/api?chainid=1"}
    assert fc._fetch_via_explorer(chain_info, "0xabc", always_fails, sleep=lambda s: None) is None
    assert len(calls) == fc.RETRY_ATTEMPTS


# --- RPC fallback --------------------------------------------------------

def test_fetch_via_rpc_parses_result():
    def fake_get(url, payload):
        assert url == fc.PUBLIC_RPC["ethereum"]
        assert payload["method"] == "eth_getCode"
        assert payload["params"] == ["0xabc", "latest"]
        return {"jsonrpc": "2.0", "id": 1, "result": "0x6001"}

    assert fc._fetch_via_rpc("ethereum", "0xabc", fake_get) == "0x6001"


def test_fetch_via_rpc_none_for_unknown_chain():
    def fake_get(url, payload):
        raise AssertionError("should not be called for a chain with no PUBLIC_RPC entry")

    assert fc._fetch_via_rpc("no-such-chain", "0xabc", fake_get) is None


def test_fetch_via_rpc_none_on_rpc_error():
    def fake_get(url, payload):
        return {"jsonrpc": "2.0", "id": 1, "error": {"code": -32000, "message": "boom"}}

    assert fc._fetch_via_rpc("ethereum", "0xabc", fake_get) is None


def test_fetch_via_rpc_none_on_exception():
    def fake_get(url, payload):
        raise TimeoutError("slow")

    assert fc._fetch_via_rpc("ethereum", "0xabc", fake_get, sleep=lambda s: None) is None


# --- fetch_code fallback ordering ----------------------------------------

def test_fetch_code_prefers_explorer_over_rpc():
    calls = []

    def fake_get(url, payload):
        calls.append(url)
        if payload is None:
            return {"result": "0x6001"}
        raise AssertionError("RPC should not be reached when explorer succeeds")

    code = fc.fetch_code("ethereum", VALID_ADDR, get=fake_get)
    assert code == "0x6001"
    assert len(calls) == 1


def test_fetch_code_falls_back_to_rpc_when_explorer_fails():
    stages = []

    def fake_get(url, payload):
        if payload is None:
            stages.append("explorer")
            raise OSError("explorer down")
        stages.append("rpc")
        return {"result": "0x6002"}

    code = fc.fetch_code("ethereum", VALID_ADDR, get=fake_get, sleep=lambda s: None)
    assert code == "0x6002"
    # Explorer is retried RETRY_ATTEMPTS times before falling back to RPC.
    assert stages == ["explorer"] * fc.RETRY_ATTEMPTS + ["rpc"]


def test_fetch_code_falls_back_to_rpc_for_okx_explorer_type():
    # xlayer's explorer type is "okx" — not proxy-module compatible, so the
    # explorer stage is skipped entirely and RPC is used directly.
    def fake_get(url, payload):
        assert payload is not None, "okx explorer type must skip straight to RPC"
        return {"result": "0x6003"}

    code = fc.fetch_code("xlayer", VALID_ADDR, get=fake_get)
    assert code == "0x6003"


def test_fetch_code_raises_when_both_strategies_fail():
    def fake_get(url, payload):
        raise OSError("down")

    with pytest.raises(RuntimeError):
        fc.fetch_code("ethereum", VALID_ADDR, get=fake_get, sleep=lambda s: None)


def test_fetch_code_raises_for_unknown_chain():
    with pytest.raises(RuntimeError):
        fc.fetch_code("no-such-chain", VALID_ADDR, get=lambda url, payload: {"result": "0x6001"})


# --- address charset guard (finding B) -----------------------------------

def test_fetch_code_rejects_malicious_address_before_any_network_call():
    def fail_if_called(url, payload):
        raise AssertionError("no network call should happen for an invalid address")

    with pytest.raises(ValueError):
        fc.fetch_code("ethereum", "0xVICTIM&address=0xLEGIT", get=fail_if_called)


def test_fetch_code_rejects_wrong_length_address():
    def fail_if_called(url, payload):
        raise AssertionError("no network call should happen for an invalid address")

    with pytest.raises(ValueError):
        fc.fetch_code("ethereum", "0xabc", get=fail_if_called)


def test_fetch_code_accepts_mixed_case_address_and_lowercases_it_in_the_url():
    mixed = "0x" + "AbCd" * 10  # 40 hex chars, mixed case
    assert len(mixed) == 42
    captured = {}

    def fake_get(url, payload):
        captured["url"] = url
        captured["address"] = payload["params"][0] if payload else None
        return {"result": "0x6001"}

    # xlayer skips straight to the RPC strategy, whose payload carries the
    # address directly (no explorer URL string to inspect).
    code = fc.fetch_code("xlayer", mixed, get=fake_get)
    assert code == "0x6001"
    assert captured["address"] == mixed.lower()


def test_fetch_code_lowercases_address_in_explorer_url():
    mixed = "0x" + "AbCd" * 10
    captured = {}

    def fake_get(url, payload):
        captured["url"] = url
        return {"result": "0x6001"}

    code = fc.fetch_code("ethereum", mixed, get=fake_get)
    assert code == "0x6001"
    assert f"address={mixed.lower()}" in captured["url"]
    assert mixed[2:] not in captured["url"]  # original mixed-case form never appears


# --- EMPTY exit path (via main(), argv patched) ---------------------------

def test_main_prints_empty_and_exits_3(monkeypatch, capsys):
    monkeypatch.setattr(fc, "fetch_code", lambda chain, address: "0x")
    monkeypatch.setattr("sys.argv", ["fetch_codehash.py", "ethereum", "0xabc"])
    with pytest.raises(SystemExit) as exc:
        fc.main()
    assert exc.value.code == 3
    assert capsys.readouterr().out.strip() == "EMPTY"


def test_main_prints_hash_and_exits_0(monkeypatch, capsys):
    monkeypatch.setattr(fc, "fetch_code", lambda chain, address: "0x6001")
    monkeypatch.setattr("sys.argv", ["fetch_codehash.py", "ethereum", "0xabc"])
    with pytest.raises(SystemExit) as exc:
        fc.main()
    assert exc.value.code == 0
    expected = "sha256:" + hashlib.sha256(bytes.fromhex("6001")).hexdigest()
    assert capsys.readouterr().out.strip() == expected


def test_main_exits_1_on_fetch_failure(monkeypatch, capsys):
    def raise_error(chain, address):
        raise RuntimeError("failed to fetch code for ethereum:0xabc")

    monkeypatch.setattr(fc, "fetch_code", raise_error)
    monkeypatch.setattr("sys.argv", ["fetch_codehash.py", "ethereum", "0xabc"])
    with pytest.raises(SystemExit) as exc:
        fc.main()
    assert exc.value.code == 1
    assert "failed to fetch code" in capsys.readouterr().err
