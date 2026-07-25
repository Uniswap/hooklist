import sys

import pytest

import evm
import validate_index as vi


class FakeClient:
    def __init__(self, code_map, head=10_000):
        self.code_map, self.head = code_map, head

    def get_code(self, address):
        return self.code_map.get(address.lower(), "0x")

    def block_number(self):
        return self.head


ADDR = "0x" + "1" * 40


def test_valid_line_passes():
    client = FakeClient({ADDR: "0x6001"})
    line = {"address": ADDR, "block": 5, "family": evm.codehash("0x6001")}
    assert vi.validate_line(line, client) == []


def test_wrong_family_fails():
    client = FakeClient({ADDR: "0x6001"})
    line = {"address": ADDR, "block": 5, "family": "0x" + "0" * 64}
    assert vi.validate_line(line, client) != []


def test_uppercase_address_fails():
    client = FakeClient({})
    line = {"address": ADDR.upper(), "block": 5, "family": "empty-code"}
    assert vi.validate_line(line, client) != []


def test_empty_code_sentinel_ok_when_no_code():
    client = FakeClient({})
    line = {"address": ADDR, "block": 5, "family": "empty-code"}
    assert vi.validate_line(line, client) == []


def test_stale_family_tolerated_when_code_changed_note():
    # code appeared since the line was written: line records empty-code but
    # code exists now -> tolerated (a correction line is the fix, not a reject)
    client = FakeClient({ADDR: "0x6001"})
    line = {"address": ADDR, "block": 5, "family": "empty-code"}
    assert vi.validate_line(line, client) == []


def test_block_exceeds_chain_head_fails():
    client = FakeClient({ADDR: "0x6001"}, head=100)
    line = {"address": ADDR, "block": 200, "family": evm.codehash("0x6001")}
    assert vi.validate_line(line, client) != []


def test_negative_block_fails():
    client = FakeClient({ADDR: "0x6001"})
    line = {"address": ADDR, "block": -1, "family": evm.codehash("0x6001")}
    assert vi.validate_line(line, client) != []


def test_non_int_block_fails():
    client = FakeClient({ADDR: "0x6001"})
    line = {"address": ADDR, "block": "5", "family": evm.codehash("0x6001")}
    assert vi.validate_line(line, client) != []


def test_file_mode_empty_file_short_circuits(tmp_path, monkeypatch):
    """An empty --file must exit 0 without ever constructing an RpcClient
    (no chain lookup, no network) -- this is the short-circuit the CI step
    relies on when a changed index/ file has no added lines."""
    added = tmp_path / "added_lines.txt"
    added.write_text("")

    def boom(*args, **kwargs):
        raise AssertionError("RpcClient must not be constructed for an empty --file")

    monkeypatch.setattr(vi.rpc, "RpcClient", boom)
    monkeypatch.setattr(sys, "argv", ["validate_index.py", "celo", "--file", str(added)])

    with pytest.raises(SystemExit) as exc:
        vi.main()
    assert exc.value.code == 0


def test_file_mode_validates_each_line(tmp_path, monkeypatch):
    good = {"address": ADDR, "block": 5, "family": evm.codehash("0x6001")}
    bad_addr = "0x" + "2" * 40
    bad = {"address": bad_addr, "block": 5, "family": "0x" + "0" * 64}
    added = tmp_path / "added_lines.txt"
    added.write_text(
        __import__("json").dumps(good) + "\n" + __import__("json").dumps(bad) + "\n"
    )

    fake = FakeClient({ADDR: "0x6001", bad_addr: "0x6002"})
    monkeypatch.setattr(vi.rpc, "RpcClient", lambda urls: fake)
    monkeypatch.setattr(sys, "argv", ["validate_index.py", "celo", "--file", str(added)])

    with pytest.raises(SystemExit) as exc:
        vi.main()
    assert exc.value.code == 1


def test_no_lines_no_file_exits_zero(monkeypatch):
    """Positional-args mode with zero lines is also a no-op short-circuit."""
    def boom(*args, **kwargs):
        raise AssertionError("RpcClient must not be constructed with no lines")

    monkeypatch.setattr(vi.rpc, "RpcClient", boom)
    monkeypatch.setattr(sys, "argv", ["validate_index.py", "celo"])

    with pytest.raises(SystemExit) as exc:
        vi.main()
    assert exc.value.code == 0
