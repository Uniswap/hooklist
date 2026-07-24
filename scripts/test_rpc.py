import pytest
import rpc


def make_post(responses):
    """responses: url -> callable(payload)->dict or Exception to raise."""
    calls = []

    def post(url, payload):
        calls.append((url, payload))
        r = responses[url]
        if isinstance(r, Exception):
            raise r
        return r(payload)

    return post, calls


def ok(result):
    return lambda payload: {"jsonrpc": "2.0", "id": payload["id"], "result": result}


def test_call_returns_result():
    post, _ = make_post({"http://a": ok("0x10")})
    client = rpc.RpcClient(["http://a"], post=post)
    assert client.call("eth_blockNumber", []) == "0x10"


def test_fallback_on_transport_error():
    post, calls = make_post({"http://a": ConnectionError("down"), "http://b": ok("0x10")})
    client = rpc.RpcClient(["http://a", "http://b"], post=post)
    assert client.call("eth_blockNumber", []) == "0x10"
    assert [u for u, _ in calls] == ["http://a", "http://b"]


def test_fallback_on_rpc_error_payload():
    err = lambda payload: {"jsonrpc": "2.0", "id": payload["id"],
                           "error": {"code": -32005, "message": "limit exceeded"}}
    post, _ = make_post({"http://a": err, "http://b": ok([])})
    client = rpc.RpcClient(["http://a", "http://b"], post=post)
    assert client.call("eth_getLogs", [{}]) == []


def test_all_urls_fail_raises():
    post, _ = make_post({"http://a": ConnectionError("down")})
    client = rpc.RpcClient(["http://a"], post=post)
    with pytest.raises(rpc.RpcError):
        client.call("eth_blockNumber", [])


def test_helpers_encode_hex():
    seen = {}

    def post(url, payload):
        seen.update(payload)
        return {"jsonrpc": "2.0", "id": payload["id"], "result": "0x1a"}

    client = rpc.RpcClient(["http://a"], post=post)
    assert client.block_number() == 26
    client.get_code("0xAbC")
    assert seen["params"] == ["0xabc", "latest"]
    post_logs_seen = {}

    def post2(url, payload):
        post_logs_seen.update(payload)
        return {"jsonrpc": "2.0", "id": payload["id"], "result": []}

    client2 = rpc.RpcClient(["http://a"], post=post2)
    client2.get_logs("0xPM", "0xT0", 16, 32)
    assert post_logs_seen["params"] == [{
        "address": "0xpm", "topics": ["0xT0"],
        "fromBlock": "0x10", "toBlock": "0x20",
    }]
