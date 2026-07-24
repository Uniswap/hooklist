import evm


def test_keccak256_empty_vector():
    # Canonical keccak-256 of empty input (NOT sha3-256)
    assert evm.keccak256(b"") == (
        "0xc5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470"
    )


def test_initialize_topic_matches_signature():
    sig = b"Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)"
    assert evm.INITIALIZE_TOPIC == evm.keccak256(sig)


def test_hook_from_initialize_log():
    # Data words: fee, tickSpacing, hooks, sqrtPriceX96, tick
    hook = "0x2f9354bbb0edef5c2a5c4b78d0c59d73412a28cc"
    data = (
        "0x"
        + hex(3000)[2:].rjust(64, "0")          # fee
        + hex(60)[2:].rjust(64, "0")             # tickSpacing
        + hook[2:].rjust(64, "0")                # hooks (left-padded address)
        + "01" .rjust(64, "0")                   # sqrtPriceX96
        + "00" .rjust(64, "0")                   # tick
    )
    log = {"data": data, "topics": [evm.INITIALIZE_TOPIC, "0x" + "00" * 32,
                                    "0x" + "00" * 32, "0x" + "00" * 32]}
    assert evm.hook_from_initialize_log(log) == hook


def test_hook_from_initialize_log_lowercases():
    hook = "0x2F9354BBB0EDEF5C2A5C4B78D0C59D73412A28CC"
    data = "0x" + "0" * 64 + "0" * 64 + hook[2:].rjust(64, "0") + "0" * 64 + "0" * 64
    log = {"data": data, "topics": []}
    assert evm.hook_from_initialize_log(log) == hook.lower()


def test_codehash_of_code_and_empty():
    assert evm.codehash("0x6001") == evm.keccak256(bytes.fromhex("6001"))
    assert evm.codehash("0x") is None
    assert evm.codehash("") is None
