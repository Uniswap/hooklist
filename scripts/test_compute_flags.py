import json
import subprocess
import sys


def test_compute_flags_basic():
    """Address ending in 0x2080 has bits 13 and 7 set: beforeInitialize and beforeSwap."""
    result = subprocess.run(
        [sys.executable, "compute_flags.py", "0x0000000000000000000000000000000000002080"],
        capture_output=True, text=True, cwd="scripts"
    )
    assert result.returncode == 0
    flags = json.loads(result.stdout)
    assert flags["beforeInitialize"] is True
    assert flags["beforeSwap"] is True
    assert flags["afterSwap"] is False
    assert flags["afterInitialize"] is False


def test_compute_flags_all_false():
    """Address ending in 0x0000 has no flags set."""
    result = subprocess.run(
        [sys.executable, "compute_flags.py", "0x0000000000000000000000000000000000000000"],
        capture_output=True, text=True, cwd="scripts"
    )
    assert result.returncode == 0
    flags = json.loads(result.stdout)
    assert all(v is False for v in flags.values())
    assert len(flags) == 14


def test_compute_flags_all_true():
    """Address ending in 0x3FFF has all 14 bits set."""
    result = subprocess.run(
        [sys.executable, "compute_flags.py", "0x0000000000000000000000000000000000003FFF"],
        capture_output=True, text=True, cwd="scripts"
    )
    assert result.returncode == 0
    flags = json.loads(result.stdout)
    assert all(v is True for v in flags.values())


def test_compute_flags_writes_file():
    """With --output flag, writes JSON to file."""
    import tempfile
    import os
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        outpath = f.name
    try:
        result = subprocess.run(
            [sys.executable, "compute_flags.py", "0x0000000000000000000000000000000000002080", "--output", outpath],
            capture_output=True, text=True, cwd="scripts"
        )
        assert result.returncode == 0
        with open(outpath) as f:
            flags = json.load(f)
        assert flags["beforeInitialize"] is True
        assert flags["beforeSwap"] is True
    finally:
        os.unlink(outpath)


def test_compute_flags_invalid_address():
    """Invalid address exits non-zero."""
    result = subprocess.run(
        [sys.executable, "compute_flags.py", "not-an-address"],
        capture_output=True, text=True, cwd="scripts"
    )
    assert result.returncode != 0
