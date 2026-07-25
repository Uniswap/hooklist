#!/usr/bin/env python3
"""Scan a chain's PoolManager Initialize events for new hook instances."""
from dataclasses import dataclass, field

import evm
import index_ledger

ZERO = "0x" + "0" * 40
MAX_PENDING_RUNS = 6
EMPTY_CODE_FAMILY = "empty-code"


@dataclass
class ScanResult:
    new_lines: list = field(default_factory=list)
    cursor: int = 0
    pending: dict = field(default_factory=dict)
    new_families: list = field(default_factory=list)


def _resolve(client, address, block, result, seen_families, existing_runs=None):
    """getCode an address; append an index line or park/advance it in pending.

    existing_runs is the pending count already on record for this address at
    the start of this run (None if this is the address's first sighting).
    """
    code = client.get_code(address)
    family = evm.codehash(code)

    if family is not None:
        result.pending.pop(address, None)
        result.new_lines.append(index_ledger.make_line(address, family, block))
        if family not in seen_families:
            seen_families.add(family)
            result.new_families.append(family)
        return

    # Still no code.
    if existing_runs is None:
        # First sighting with empty code: enter pending at count 1.
        result.pending[address] = 1
    elif existing_runs >= MAX_PENDING_RUNS:
        # Already exhausted its rechecks coming into this run and still
        # empty: give up, emit the sentinel line, and drop it from pending.
        del result.pending[address]
        result.new_lines.append(index_ledger.make_line(address, EMPTY_CODE_FAMILY, block))
    else:
        result.pending[address] = existing_runs + 1


def scan_chain(client, cfg: dict, cursor: int, pending: dict, known: set,
               chunk_size: int = 5000, max_chunks: int = 100) -> ScanResult:
    head = client.block_number()
    safe_head = head - cfg["confirmations"]
    result = ScanResult(cursor=cursor, pending=dict(pending))
    seen_families: set = set()
    # Addresses already pending must not be treated as first-sightings if a
    # fresh log for them shows up later in this same run (they're resolved
    # via the recheck loop below; re-resolving them from the log loop would
    # reset their pending count via the existing_runs=None branch).
    seen_addresses: set = set(known) | set(pending.keys())

    # Recheck previously pending (empty-code) addresses first, at the
    # current cursor block (no new chunk has been scanned yet this run).
    for address, runs in pending.items():
        _resolve(client, address, cursor, result, seen_families, existing_runs=runs)

    chunks = 0
    while result.cursor < safe_head and chunks < max_chunks:
        from_block = result.cursor + 1
        to_block = min(result.cursor + chunk_size, safe_head)
        logs = client.get_logs(cfg["poolManager"], evm.INITIALIZE_TOPIC, from_block, to_block)
        for log in logs:
            hook = evm.hook_from_initialize_log(log)
            if hook == ZERO or hook in seen_addresses:
                continue
            seen_addresses.add(hook)
            block = int(log["blockNumber"], 16) if "blockNumber" in log else to_block
            _resolve(client, hook, block, result, seen_families)
        result.cursor = to_block
        chunks += 1

    return result
