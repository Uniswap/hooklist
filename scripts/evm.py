#!/usr/bin/env python3
"""EVM primitives: keccak-256, v4 Initialize event parsing, codehash."""
from Crypto.Hash import keccak as _keccak


def keccak256(data: bytes) -> str:
    h = _keccak.new(digest_bits=256)
    h.update(data)
    return "0x" + h.hexdigest()


# event Initialize(PoolId indexed id, Currency indexed currency0,
#   Currency indexed currency1, uint24 fee, int24 tickSpacing,
#   IHooks hooks, uint160 sqrtPriceX96, int24 tick)
INITIALIZE_TOPIC = keccak256(
    b"Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)"
)


def hook_from_initialize_log(log: dict) -> str:
    """Extract the hooks address from an Initialize log's data field.

    Non-indexed data words: [fee, tickSpacing, hooks, sqrtPriceX96, tick];
    hooks is word 2, address is its low 20 bytes.
    """
    data = log["data"][2:]  # strip 0x
    word = data[64 * 2 : 64 * 3]
    return ("0x" + word[24:]).lower()


def codehash(code_hex: str) -> str | None:
    """keccak of contract code as returned by eth_getCode; None if no code."""
    stripped = code_hex[2:] if code_hex.startswith("0x") else code_hex
    if not stripped:
        return None
    return keccak256(bytes.fromhex(stripped))
