import json
import os
import select_analyses as sa

FAM = "0x" + "a" * 64
CAND = [{"family": FAM, "chain": "celo", "address": "0x" + "1" * 40}]


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


def test_selects_new_family(tmp_path):
    got = sa.select(CAND, str(tmp_path), gh_stub(), cap=5)
    assert got == CAND


def test_skips_existing_family_file(tmp_path):
    fam_dir = tmp_path / "families"
    fam_dir.mkdir()
    (fam_dir / f"{FAM}.json").write_text("{}")
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
    cands = [{"family": "0x" + str(i) * 64, "chain": "celo", "address": "0x" + "1" * 40}
             for i in range(1, 8)] + [{"family": "empty-code", "chain": "celo",
                                       "address": "0x" + "2" * 40}]
    got = sa.select(cands, str(tmp_path), gh_stub(), cap=3)
    assert len(got) == 3
    assert all(c["family"] != "empty-code" for c in got)
