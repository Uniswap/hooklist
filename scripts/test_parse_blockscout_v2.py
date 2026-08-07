import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parse_blockscout_v2 import parse


def test_parse_blockscout_v2_verified(tmp_path):
    """Verified response extracts the primary file plus additional sources."""
    response = {
        "name": "TestHook",
        "is_verified": True,
        "file_path": "src/TestHook.sol",
        "source_code": "pragma solidity ^0.8.0; contract TestHook {}",
        "additional_sources": [
            {"file_path": "lib/Base.sol", "source_code": "pragma solidity ^0.8.0; contract Base {}"},
        ],
        "proxy_type": None,
        "implementations": [],
    }
    response_file = tmp_path / "response.json"
    response_file.write_text(json.dumps(response))

    meta = parse(str(response_file), outdir=str(tmp_path / "sources"))

    assert meta["contractName"] == "TestHook"
    assert meta["verified"] is True
    assert meta["proxy"] is False
    assert os.path.exists(tmp_path / "sources" / "src_TestHook.sol")
    assert os.path.exists(tmp_path / "sources" / "lib_Base.sol")


def test_parse_blockscout_v2_not_found(tmp_path):
    """An unverified address returns {"message": "Not found"} and no source keys."""
    response_file = tmp_path / "response.json"
    response_file.write_text(json.dumps({"message": "Not found"}))

    meta = parse(str(response_file), outdir=str(tmp_path / "sources"))

    assert meta["verified"] is False
    assert meta["contractName"] == ""
    assert not os.path.exists(tmp_path / "sources")


def test_parse_blockscout_v2_rate_limited(tmp_path):
    """A throttled response must read as unverified rather than raising.

    This is the case that motivated the parser: the Etherscan-compatible endpoint
    returns {"result": null} when rate limited, which crashes a parser that indexes
    into it. Whatever shape the error takes, absence of `is_verified` is the signal.
    """
    response_file = tmp_path / "response.json"
    response_file.write_text(json.dumps({"message": "Too many requests", "result": None, "status": "0"}))

    meta = parse(str(response_file), outdir=str(tmp_path / "sources"))

    assert meta["verified"] is False
    assert meta["proxy"] is False


def test_parse_blockscout_v2_proxy(tmp_path):
    """proxy_type plus implementations resolves to a proxy with an implementation."""
    response = {
        "name": "ProxyHook",
        "is_verified": True,
        "file_path": "src/ProxyHook.sol",
        "source_code": "contract ProxyHook {}",
        "additional_sources": [],
        "proxy_type": "eip1967",
        "implementations": [{"address": "0xabcdef1234567890abcdef1234567890abcdef12", "name": "Impl"}],
    }
    response_file = tmp_path / "response.json"
    response_file.write_text(json.dumps(response))

    meta = parse(str(response_file), outdir=str(tmp_path / "sources"))

    assert meta["proxy"] is True
    assert meta["implementation"] == "0xabcdef1234567890abcdef1234567890abcdef12"


def test_parse_blockscout_v2_unknown_proxy_type_is_not_a_proxy(tmp_path):
    """Some instances report proxy_type "unknown" for plain contracts."""
    response = {
        "name": "PlainHook",
        "is_verified": True,
        "file_path": "src/PlainHook.sol",
        "source_code": "contract PlainHook {}",
        "proxy_type": "unknown",
        "implementations": [],
    }
    response_file = tmp_path / "response.json"
    response_file.write_text(json.dumps(response))

    meta = parse(str(response_file), outdir=str(tmp_path / "sources"))

    assert meta["proxy"] is False
    assert meta["implementation"] == ""


def test_parse_blockscout_v2_path_traversal_is_sanitized(tmp_path):
    """Source paths are attacker-influenced; they must not escape outdir."""
    response = {
        "name": "EvilHook",
        "is_verified": True,
        "file_path": "../../etc/passwd",
        "source_code": "contract EvilHook {}",
        "additional_sources": [{"file_path": "../../../tmp/evil.sol", "source_code": "evil"}],
    }
    response_file = tmp_path / "response.json"
    response_file.write_text(json.dumps(response))

    outdir = tmp_path / "sources"
    parse(str(response_file), outdir=str(outdir))

    for written in os.listdir(outdir):
        assert os.path.realpath(os.path.join(outdir, written)).startswith(os.path.realpath(outdir))
