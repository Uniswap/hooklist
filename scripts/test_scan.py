import evm
import scan


class FakeClient:
    def __init__(self, head, logs_by_range=None, code=None):
        self.head = head
        self.logs = logs_by_range or {}
        self.code = code or {}
        self.get_code_calls = {}

    def block_number(self):
        return self.head

    def get_logs(self, address, topic0, from_block, to_block):
        return self.logs.get((from_block, to_block), [])

    def get_code(self, address):
        key = address.lower()
        self.get_code_calls[key] = self.get_code_calls.get(key, 0) + 1
        return self.code.get(key, "0x")


def log_for(hook):
    data = "0x" + "0" * 64 + "0" * 64 + hook[2:].rjust(64, "0") + "0" * 64 + "0" * 64
    return {"data": data, "topics": [evm.INITIALIZE_TOPIC]}


CFG = {"poolManager": "0xpm", "confirmations": 10}
HOOK = "0x00000000000000000000000000000000000020c0"


def test_scans_to_head_minus_confirmations_and_records_hook():
    client = FakeClient(head=1010, logs_by_range={(1, 1000): [log_for(HOOK)]},
                        code={HOOK: "0x6001"})
    r = scan.scan_chain(client, CFG, cursor=0, pending={}, known=set())
    assert r.cursor == 1000
    assert len(r.new_lines) == 1
    line = r.new_lines[0]
    assert line["address"] == HOOK
    assert line["family"] == evm.codehash("0x6001")
    assert line["block"] == 1000  # to_block of the chunk containing it? NO — see impl: block from log
    assert r.new_families == [evm.codehash("0x6001")]


def test_skips_zero_hook():
    client = FakeClient(head=1010, logs_by_range={(1, 1000): [log_for(scan.ZERO)]})
    r = scan.scan_chain(client, CFG, cursor=0, pending={}, known=set())
    assert r.new_lines == [] and r.pending == {}


def test_known_addresses_not_reprocessed():
    client = FakeClient(head=1010, logs_by_range={(1, 1000): [log_for(HOOK)]})
    r = scan.scan_chain(client, CFG, cursor=0, pending={}, known={HOOK})
    assert r.new_lines == []


def test_empty_code_goes_to_pending_then_sentinel():
    client = FakeClient(head=1010, logs_by_range={(1, 1000): [log_for(HOOK)]})
    r = scan.scan_chain(client, CFG, cursor=0, pending={}, known=set())
    assert r.new_lines == [] and r.pending == {HOOK: 1}
    # after MAX_PENDING_RUNS runs without code, sentinel line is written
    r2 = scan.scan_chain(client, CFG, cursor=1000, pending={HOOK: scan.MAX_PENDING_RUNS},
                         known=set())
    assert r2.pending == {}
    assert r2.new_lines[0]["family"] == scan.EMPTY_CODE_FAMILY


def test_pending_resolves_when_code_appears():
    client = FakeClient(head=1010, code={HOOK: "0x6001"})
    r = scan.scan_chain(client, CFG, cursor=1000, pending={HOOK: 2}, known=set())
    assert r.pending == {}
    assert r.new_lines[0]["family"] == evm.codehash("0x6001")


def test_chunking_bounded_by_max_chunks():
    client = FakeClient(head=100_000)
    r = scan.scan_chain(client, CFG, cursor=0, pending={}, known=set(),
                        chunk_size=100, max_chunks=3)
    assert r.cursor == 300  # 3 chunks * 100 blocks, far short of head


def test_new_family_deduped_within_run():
    h2 = "0x00000000000000000000000000000000000120c0"
    client = FakeClient(head=1010,
                        logs_by_range={(1, 1000): [log_for(HOOK), log_for(h2)]},
                        code={HOOK: "0x6001", h2: "0x6001"})
    r = scan.scan_chain(client, CFG, cursor=0, pending={}, known=set())
    assert len(r.new_lines) == 2
    assert r.new_families == [evm.codehash("0x6001")]  # one family, two instances


def test_pending_address_reappearing_in_log_not_double_processed():
    """A pending address that also shows up in a fresh Initialize log this
    run must be resolved only once (via the recheck loop), not reprocessed
    (and reset) by the main log loop."""
    client = FakeClient(head=1011, logs_by_range={(1001, 1001): [log_for(HOOK)]})
    r = scan.scan_chain(client, CFG, cursor=1000, pending={HOOK: 3}, known=set())
    assert client.get_code_calls[HOOK.lower()] == 1
    assert r.pending == {HOOK: 4}
    assert r.new_lines == []


def test_pending_address_reappearing_in_log_resolves_once_when_code_appears():
    """Same scenario, but code has appeared: exactly one index line is
    produced, not two."""
    client = FakeClient(head=1011, logs_by_range={(1001, 1001): [log_for(HOOK)]},
                        code={HOOK: "0x6001"})
    r = scan.scan_chain(client, CFG, cursor=1000, pending={HOOK: 3}, known=set())
    assert client.get_code_calls[HOOK.lower()] == 1
    assert r.pending == {}
    assert len(r.new_lines) == 1
    assert r.new_lines[0]["family"] == evm.codehash("0x6001")


def test_pending_argument_not_mutated():
    """scan_chain must not mutate the caller's pending dict."""
    client = FakeClient(head=1010, logs_by_range={(1, 1000): [log_for(HOOK)]})
    original = {HOOK: 3}
    snapshot = dict(original)
    scan.scan_chain(client, CFG, cursor=0, pending=original, known=set())
    assert original == snapshot
