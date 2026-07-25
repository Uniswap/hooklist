import json
import os
import select_analyses as sa

FAM = "0x" + "a" * 64
FAM2 = "0x" + "b" * 64
ADDR = "0x" + "1" * 40
ADDR2 = "0x" + "2" * 40
CAND = [{"family": FAM, "chain": "celo", "address": ADDR}]


def gh_stub(pr_branches=(), runs=()):
    """runs: list of (displayTitle, status, conclusion)."""
    def gh(args):
        if args[:2] == ["pr", "list"]:
            return json.dumps([{"headRefName": b} for b in pr_branches])
        if args[:2] == ["run", "list"]:
            return json.dumps([
                {"displayTitle": t, "status": s, "conclusion": c} for t, s, c in runs
            ])
        raise AssertionError(f"unexpected gh call: {args}")
    return gh


def write_index(tmp_path, chain, lines):
    d = tmp_path / "index"
    d.mkdir(exist_ok=True)
    with open(d / f"{chain}.jsonl", "w") as f:
        for line in lines:
            f.write(json.dumps(line) + "\n")


def write_family_file(tmp_path, fam):
    d = tmp_path / "families"
    d.mkdir(exist_ok=True)
    (d / f"{fam}.json").write_text("{}")


# ---- candidates_from_index (retry-by-absence) ----

def test_candidates_derived_from_index(tmp_path):
    write_index(tmp_path, "celo", [{"address": ADDR, "block": 5, "family": FAM}])
    got = sa.candidates_from_index(str(tmp_path))
    assert got == [{"family": FAM, "chain": "celo", "address": ADDR}]


def test_candidates_exclude_existing_family_file(tmp_path):
    write_index(tmp_path, "celo", [{"address": ADDR, "block": 5, "family": FAM}])
    write_family_file(tmp_path, FAM)
    assert sa.candidates_from_index(str(tmp_path)) == []


def test_candidates_exclude_empty_code(tmp_path):
    write_index(tmp_path, "celo",
                [{"address": ADDR, "block": 5, "family": "empty-code"}])
    assert sa.candidates_from_index(str(tmp_path)) == []


def test_candidates_representative_deterministic(tmp_path):
    # Same family on two chains and two addresses: representative is the
    # first by sorted chain, then sorted address within that chain.
    write_index(tmp_path, "celo", [{"address": ADDR, "block": 5, "family": FAM}])
    write_index(tmp_path, "base", [
        {"address": ADDR2, "block": 9, "family": FAM},
        {"address": ADDR, "block": 7, "family": FAM},
    ])
    got = sa.candidates_from_index(str(tmp_path))
    assert got == [{"family": FAM, "chain": "base", "address": ADDR}]


def test_overflow_family_picked_up_on_later_run(tmp_path):
    """A family beyond the dispatch cap is not lost: once the first family
    has its file, the next run's index-derived candidates include the
    leftover family."""
    write_index(tmp_path, "celo", [
        {"address": ADDR, "block": 5, "family": FAM},
        {"address": ADDR2, "block": 6, "family": FAM2},
    ])
    first = sa.select(sa.candidates_from_index(str(tmp_path)), str(tmp_path),
                      gh_stub(), cap=1)
    assert [c["family"] for c in first] == [FAM]
    write_family_file(tmp_path, FAM)  # analysis of FAM merged
    second = sa.select(sa.candidates_from_index(str(tmp_path)), str(tmp_path),
                       gh_stub(), cap=1)
    assert [c["family"] for c in second] == [FAM2]


def test_failed_run_family_still_gated_by_failure_cap(tmp_path):
    """A family whose only trace is old index lines (never re-emitted by a
    later scan) is still seen by the failure gate: retried while under the
    cap, dropped at the cap."""
    write_index(tmp_path, "celo", [{"address": ADDR, "block": 5, "family": FAM}])
    fails = [(f"analyze-family {FAM}", "completed", "failure")]
    cands = sa.candidates_from_index(str(tmp_path))
    assert sa.select(cands, str(tmp_path), gh_stub(runs=fails * 2), cap=5) == cands
    assert sa.select(cands, str(tmp_path), gh_stub(runs=fails * 3), cap=5) == []


# ---- select() gh-based filters ----

def test_selects_new_family(tmp_path):
    got = sa.select(CAND, str(tmp_path), gh_stub(), cap=5)
    assert got == CAND


def test_skips_existing_family_file(tmp_path):
    write_family_file(tmp_path, FAM)
    assert sa.select(CAND, str(tmp_path), gh_stub(), cap=5) == []


def test_skips_open_pr_branch(tmp_path):
    gh = gh_stub(pr_branches=[f"families/{FAM}"])
    assert sa.select(CAND, str(tmp_path), gh, cap=5) == []


def test_skips_in_flight_run(tmp_path):
    gh = gh_stub(runs=[(f"analyze-family {FAM}", "in_progress", "")])
    assert sa.select(CAND, str(tmp_path), gh, cap=5) == []


def test_skips_after_three_failures(tmp_path):
    fails = [(f"analyze-family {FAM}", "completed", "failure")] * 3
    assert sa.select(CAND, str(tmp_path), gh_stub(runs=fails), cap=5) == []


def test_two_failures_still_retries(tmp_path):
    fails = [(f"analyze-family {FAM}", "completed", "failure")] * 2
    assert sa.select(CAND, str(tmp_path), gh_stub(runs=fails), cap=5) == CAND


def test_cap_and_empty_code(tmp_path):
    cands = [{"family": "0x" + str(i) * 64, "chain": "celo", "address": ADDR}
             for i in range(1, 8)] + [{"family": "empty-code", "chain": "celo",
                                       "address": ADDR2}]
    got = sa.select(cands, str(tmp_path), gh_stub(), cap=3)
    assert len(got) == 3
    assert all(c["family"] != "empty-code" for c in got)
