import json
import pytest
import index_ledger as il


def test_read_missing_file_returns_empty(tmp_path):
    assert il.read_lines(str(tmp_path / "nope.jsonl")) == []


def test_append_and_read_roundtrip(tmp_path):
    p = str(tmp_path / "base.jsonl")
    lines = [il.make_line("0xAbC0000000000000000000000000000000002080", "0x" + "f" * 64, 5)]
    n = il.append_lines(p, lines)
    assert n == 1
    got = il.read_lines(p)
    assert got == [{"address": "0xabc0000000000000000000000000000000002080",
                    "block": 5, "family": "0x" + "f" * 64}]
    # file is one compact JSON object per line
    raw = open(p).read()
    assert raw.endswith("\n") and "\n" not in raw.strip()


def test_latest_by_address_last_wins():
    a = {"address": "0xa", "block": 1, "family": "0x1"}
    b = {"address": "0xa", "block": 9, "family": "0x2"}
    c = {"address": "0xb", "block": 2, "family": "0x3"}
    latest = il.latest_by_address([a, b, c])
    assert latest["0xa"]["family"] == "0x2"
    assert latest["0xb"]["family"] == "0x3"


def test_append_rejects_uppercase_address(tmp_path):
    p = str(tmp_path / "x.jsonl")
    with pytest.raises(ValueError):
        il.append_lines(p, [{"address": "0xABC", "block": 1, "family": "0x1"}])


def test_append_rejects_missing_keys(tmp_path):
    p = str(tmp_path / "x.jsonl")
    with pytest.raises(ValueError):
        il.append_lines(p, [{"address": "0xabc", "block": 1}])


def test_make_line_lowercases():
    line = il.make_line("0xABC", "0xDEF", 7)
    assert line == {"address": "0xabc", "block": 7, "family": "0xdef"}
