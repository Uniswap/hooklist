#!/usr/bin/env python3
"""Verify hook flags match the address bitmask.

Usage:
  python3 scripts/verify_flags.py                     # verify all hooks
  python3 scripts/verify_flags.py hooks/base/0x...json # verify specific files
"""
import json
import glob
import os
import sys

# Bit positions for each flag (from the Uniswap v4 address bitmask)
FLAG_BITS = {
    "beforeInitialize": 13,
    "afterInitialize": 12,
    "beforeAddLiquidity": 11,
    "afterAddLiquidity": 10,
    "beforeRemoveLiquidity": 9,
    "afterRemoveLiquidity": 8,
    "beforeSwap": 7,
    "afterSwap": 6,
    "beforeDonate": 5,
    "afterDonate": 4,
    "beforeSwapReturnsDelta": 3,
    "afterSwapReturnsDelta": 2,
    "afterAddLiquidityReturnsDelta": 1,
    "afterRemoveLiquidityReturnsDelta": 0,
}


def decode_flags(address: str) -> dict[str, bool]:
    """Decode hook permission flags from a hex address."""
    addr_int = int(address, 16)
    return {name: bool(addr_int & (1 << bit)) for name, bit in FLAG_BITS.items()}


def verify_hook(filepath: str) -> list[str]:
    """Verify a hook file's flags match its address. Returns list of errors."""
    with open(filepath) as f:
        hook = json.load(f)

    address = hook["hook"]["address"]
    expected = decode_flags(address)
    actual = hook["flags"]
    errors = []

    for flag, expected_val in expected.items():
        actual_val = actual.get(flag)
        if actual_val is None:
            errors.append(f"{filepath}: missing flag '{flag}'")
        elif actual_val != expected_val:
            errors.append(
                f"{filepath}: flag '{flag}' is {actual_val} but address says {expected_val}"
            )

    return errors


def main():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    if len(sys.argv) > 1:
        files = sys.argv[1:]
    else:
        files = glob.glob(os.path.join(repo_root, "hooks", "**", "*.json"), recursive=True)

    if not files:
        print("No hook files to verify.")
        return

    all_errors = []
    for filepath in files:
        errors = verify_hook(filepath)
        if errors:
            for e in errors:
                print(f"FAIL: {e}")
            all_errors.extend(errors)
        else:
            print(f"  OK: {filepath}")

    if all_errors:
        print(f"\n{len(all_errors)} flag verification error(s)")
        sys.exit(1)
    else:
        print(f"\nAll {len(files)} file(s) passed flag verification.")


if __name__ == "__main__":
    main()
