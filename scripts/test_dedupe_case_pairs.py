import dedupe_case_pairs as d


def test_find_pairs_groups_case_insensitive_duplicates():
    lines = [
        "hooks/base/0xAbC.json",
        "hooks/base/0xabc.json",
        "hooks/base/0xdef.json",
        "hooks/celo/0xabc.json",  # different chain dir: not a pair
    ]
    assert d.find_pairs(lines) == [("hooks/base/0xAbC.json", "hooks/base/0xabc.json")]


def test_choose_keeper_identical_prefers_lowercase_name():
    c = {"hook": {"name": "X"}}
    assert d.choose_keeper("hooks/base/0xAbC.json", "hooks/base/0xabc.json", c, c, 1, 2) \
        == "hooks/base/0xabc.json"


def test_choose_keeper_conflicting_prefers_newer():
    a = {"hook": {"name": "A"}}
    b = {"hook": {"name": "B"}}
    assert d.choose_keeper("hooks/base/0xAbC.json", "hooks/base/0xabc.json", a, b,
                           mtime_a=100, mtime_b=200) == "hooks/base/0xabc.json"
    assert d.choose_keeper("hooks/base/0xAbC.json", "hooks/base/0xabc.json", a, b,
                           mtime_a=300, mtime_b=200) == "hooks/base/0xAbC.json"
