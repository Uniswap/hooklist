import json
import os
import evm
import ingest


class FakeClient:
    def __init__(self, head, logs=None, code=None, fail=False):
        self.head, self.logs, self.code, self.fail = head, logs or [], code or {}, fail

    def block_number(self):
        if self.fail:
            raise ConnectionError("rpc down")
        return self.head

    def get_logs(self, address, topic0, from_block, to_block):
        return [l for l in self.logs if from_block <= int(l["blockNumber"], 16) <= to_block]

    def get_code(self, address):
        return self.code.get(address.lower(), "0x")


HOOK = "0x00000000000000000000000000000000000020c0"


def log_for(hook, block):
    data = "0x" + "0" * 64 + "0" * 64 + hook[2:].rjust(64, "0") + "0" * 64 + "0" * 64
    return {"data": data, "topics": [evm.INITIALIZE_TOPIC], "blockNumber": hex(block)}


def setup_repo(tmp_path):
    (tmp_path / "chains.json").write_text(json.dumps({
        "celo": {"chainId": 42220, "rpcUrls": ["http://x"], "poolManager": "0xpm",
                 "deployBlock": 0, "confirmations": 10},
        "zora": {"chainId": 7777777}  # not configured for ingestion -> skipped
    }))
    return str(tmp_path)


def test_ingest_appends_and_writes_outputs(tmp_path):
    root = setup_repo(tmp_path)
    clients = {"celo": FakeClient(1010, logs=[log_for(HOOK, 500)], code={HOOK: "0x6001"})}
    rc = ingest.run(root, client_factory=lambda name, cfg: clients[name])
    assert rc == 0
    lines = open(os.path.join(root, "index", "celo.jsonl")).read().strip().split("\n")
    assert json.loads(lines[0])["address"] == HOOK
    cursors = json.loads(open(os.path.join(root, "index", "cursors.json")).read())
    assert cursors["celo"]["block"] == 1000
    # No new_families.json side artifact: analysis candidates are derived
    # from the index by select_analyses.py (retry-by-absence).
    assert not os.path.exists(os.path.join(root, "new_families.json"))


def test_ingest_idempotent_second_run(tmp_path):
    root = setup_repo(tmp_path)
    client = FakeClient(1010, logs=[log_for(HOOK, 500)], code={HOOK: "0x6001"})
    ingest.run(root, client_factory=lambda n, c: client)
    ingest.run(root, client_factory=lambda n, c: client)
    lines = open(os.path.join(root, "index", "celo.jsonl")).read().strip().split("\n")
    assert len(lines) == 1  # known address not re-appended


def test_chain_failure_isolated(tmp_path):
    root = setup_repo(tmp_path)
    rc = ingest.run(root, client_factory=lambda n, c: FakeClient(0, fail=True))
    assert rc == 2  # all configured chains failed
    assert not os.path.exists(os.path.join(root, "index", "celo.jsonl"))


# ---- cursor-persistence gate (no noise commits on idle cron ticks) ----

def cursors_path(root):
    return os.path.join(root, "index", "cursors.json")


def test_idle_small_advance_does_not_write_cursors(tmp_path):
    """No new lines and a sub-threshold cursor advance: cursors.json is not
    written, so the workflow's diff gate sees no change (no noise commit)."""
    root = setup_repo(tmp_path)
    # head 1010, confirmations 10 -> cursor 1000; advance 1000 < threshold
    assert 1000 < ingest.CURSOR_PERSIST_MIN_ADVANCE
    ingest.run(root, client_factory=lambda n, c: FakeClient(1010))
    assert not os.path.exists(cursors_path(root))


def test_idle_large_advance_writes_cursors(tmp_path):
    """No new lines but a threshold-sized advance: persisted, so the
    unscanned window cannot grow without bound."""
    root = setup_repo(tmp_path)
    # head 6010 -> cursor 6000; advance 6000 >= threshold
    ingest.run(root, client_factory=lambda n, c: FakeClient(6010))
    cursors = json.loads(open(cursors_path(root)).read())
    assert cursors["celo"]["block"] == 6000


def test_new_lines_force_cursor_persist_below_threshold(tmp_path):
    """New index lines always persist the cursor, even for a small advance."""
    root = setup_repo(tmp_path)
    client = FakeClient(1010, logs=[log_for(HOOK, 500)], code={HOOK: "0x6001"})
    ingest.run(root, client_factory=lambda n, c: client)
    cursors = json.loads(open(cursors_path(root)).read())
    assert cursors["celo"]["block"] == 1000


def test_small_advance_leaves_persisted_cursor_untouched(tmp_path):
    """A later idle run with a sub-threshold advance past the persisted
    cursor leaves the file at the old value (rescanning that small window
    next run is safe: known-address dedup absorbs re-seen instances)."""
    root = setup_repo(tmp_path)
    ingest.run(root, client_factory=lambda n, c: FakeClient(6010))  # persists 6000
    ingest.run(root, client_factory=lambda n, c: FakeClient(7010))  # +1000 < threshold
    cursors = json.loads(open(cursors_path(root)).read())
    assert cursors["celo"]["block"] == 6000
