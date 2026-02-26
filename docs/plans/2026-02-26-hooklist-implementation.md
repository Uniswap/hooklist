# Hooklist Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a public registry of Uniswap v4 hook deployments where anyone can submit a hook via GitHub Issue and Claude Code in CI automatically analyzes it, generates metadata, and opens a PR.

**Architecture:** One JSON file per hook at `hooks/<chain>/<address>.json`. Issue-opened triggers a GitHub Actions workflow that runs Claude Code to fetch verified source from Etherscan V2 API, analyze the Solidity for flags/properties, and open a PR. A second workflow on merge regenerates `hooklist.json` and the README summary table.

**Tech Stack:** GitHub Actions, Claude Code CLI, Etherscan V2 API, Python 3 (aggregation script), JSON Schema

---

### Task 1: Create the JSON Schema

**Files:**
- Create: `schema.json`

**Step 1: Create the schema file**

This defines the canonical shape of every hook JSON file. All 14 flags from the v4 address bitmask are included, plus properties detected from source analysis.

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Uniswap v4 Hook",
  "type": "object",
  "required": ["hook", "flags", "properties"],
  "additionalProperties": false,
  "properties": {
    "hook": {
      "type": "object",
      "required": ["address", "chain", "chainId", "name", "verifiedSource"],
      "additionalProperties": false,
      "properties": {
        "address": { "type": "string", "pattern": "^0x[a-fA-F0-9]{40}$" },
        "chain": { "type": "string" },
        "chainId": { "type": "integer" },
        "name": { "type": "string" },
        "description": { "type": "string", "default": "" },
        "deployer": { "type": "string", "pattern": "^0x[a-fA-F0-9]{40}$", "default": "" },
        "verifiedSource": { "type": "boolean" },
        "auditUrl": { "type": "string", "format": "uri", "default": "" }
      }
    },
    "flags": {
      "type": "object",
      "required": [
        "beforeInitialize", "afterInitialize",
        "beforeAddLiquidity", "afterAddLiquidity",
        "beforeRemoveLiquidity", "afterRemoveLiquidity",
        "beforeSwap", "afterSwap",
        "beforeDonate", "afterDonate",
        "beforeSwapReturnsDelta", "afterSwapReturnsDelta",
        "afterAddLiquidityReturnsDelta", "afterRemoveLiquidityReturnsDelta"
      ],
      "additionalProperties": false,
      "properties": {
        "beforeInitialize": { "type": "boolean" },
        "afterInitialize": { "type": "boolean" },
        "beforeAddLiquidity": { "type": "boolean" },
        "afterAddLiquidity": { "type": "boolean" },
        "beforeRemoveLiquidity": { "type": "boolean" },
        "afterRemoveLiquidity": { "type": "boolean" },
        "beforeSwap": { "type": "boolean" },
        "afterSwap": { "type": "boolean" },
        "beforeDonate": { "type": "boolean" },
        "afterDonate": { "type": "boolean" },
        "beforeSwapReturnsDelta": { "type": "boolean" },
        "afterSwapReturnsDelta": { "type": "boolean" },
        "afterAddLiquidityReturnsDelta": { "type": "boolean" },
        "afterRemoveLiquidityReturnsDelta": { "type": "boolean" }
      }
    },
    "properties": {
      "type": "object",
      "required": ["dynamicFee", "upgradeable", "requiresCustomSwapData"],
      "additionalProperties": false,
      "properties": {
        "dynamicFee": { "type": "boolean" },
        "upgradeable": { "type": "boolean" },
        "requiresCustomSwapData": { "type": "boolean" }
      }
    }
  }
}
```

Note: `returnsDelta` was removed as a separate property since the 4 returns-delta flags in `flags` already capture this granularly.

**Step 2: Commit**

```bash
git add schema.json
git commit -m "feat: add JSON schema for hook files"
```

---

### Task 2: Create the GitHub Issue Template

**Files:**
- Create: `.github/ISSUE_TEMPLATE/submit-hook.yml`

**Step 1: Create the issue template**

```yaml
name: Submit a Hook
description: Propose a Uniswap v4 hook for the registry
title: "hook: "
labels: ["submission"]
body:
  - type: markdown
    attributes:
      value: |
        Submit a deployed Uniswap v4 hook to the registry. Provide the chain and address — Claude will automatically analyze the verified source code and generate the metadata.
  - type: dropdown
    id: chain
    attributes:
      label: Chain
      options:
        - ethereum
        - unichain
        - base
        - arbitrum
        - optimism
        - polygon
        - blast
        - worldchain
        - avalanche
        - bnb
        - celo
        - zora
        - ink
        - soneium
    validations:
      required: true
  - type: input
    id: address
    attributes:
      label: Hook Address
      description: The deployed hook contract address
      placeholder: "0x..."
    validations:
      required: true
  - type: input
    id: name
    attributes:
      label: Hook Name
      description: Optional — will be detected from source if not provided
      placeholder: "MyHook"
  - type: textarea
    id: description
    attributes:
      label: Description
      description: Optional — Claude will generate a summary if not provided
      placeholder: "What does this hook do?"
  - type: input
    id: deployer
    attributes:
      label: Deployer Address
      description: Optional
      placeholder: "0x..."
  - type: input
    id: audit_url
    attributes:
      label: Audit URL
      description: Optional — link to a security audit
      placeholder: "https://..."
```

**Step 2: Commit**

```bash
git add .github/ISSUE_TEMPLATE/submit-hook.yml
git commit -m "feat: add GitHub Issue template for hook submissions"
```

---

### Task 3: Create Chain Config

**Files:**
- Create: `chains.json`

**Step 1: Create the chain configuration file**

This maps chain names (used in the issue template dropdown and directory names) to chain IDs and Etherscan API details. Claude reads this in CI to know how to call the right explorer.

```json
{
  "ethereum": { "chainId": 1, "explorer": "etherscan", "explorerUrl": "https://api.etherscan.io/v2/api?chainid=1" },
  "unichain": { "chainId": 130, "explorer": "etherscan", "explorerUrl": "https://api.etherscan.io/v2/api?chainid=130" },
  "base": { "chainId": 8453, "explorer": "etherscan", "explorerUrl": "https://api.etherscan.io/v2/api?chainid=8453" },
  "arbitrum": { "chainId": 42161, "explorer": "etherscan", "explorerUrl": "https://api.etherscan.io/v2/api?chainid=42161" },
  "optimism": { "chainId": 10, "explorer": "etherscan", "explorerUrl": "https://api.etherscan.io/v2/api?chainid=10" },
  "polygon": { "chainId": 137, "explorer": "etherscan", "explorerUrl": "https://api.etherscan.io/v2/api?chainid=137" },
  "blast": { "chainId": 81457, "explorer": "etherscan", "explorerUrl": "https://api.etherscan.io/v2/api?chainid=81457" },
  "worldchain": { "chainId": 480, "explorer": "etherscan", "explorerUrl": "https://api.etherscan.io/v2/api?chainid=480" },
  "avalanche": { "chainId": 43114, "explorer": "etherscan", "explorerUrl": "https://api.etherscan.io/v2/api?chainid=43114" },
  "bnb": { "chainId": 56, "explorer": "etherscan", "explorerUrl": "https://api.etherscan.io/v2/api?chainid=56" },
  "celo": { "chainId": 42220, "explorer": "etherscan", "explorerUrl": "https://api.etherscan.io/v2/api?chainid=42220" },
  "zora": { "chainId": 7777777, "explorer": "blockscout", "explorerUrl": "https://explorer.zora.energy/api" },
  "ink": { "chainId": 57073, "explorer": "blockscout", "explorerUrl": "https://explorer.inkonchain.com/api" },
  "soneium": { "chainId": 1868, "explorer": "blockscout", "explorerUrl": "https://soneium.blockscout.com/api" }
}
```

**Step 2: Commit**

```bash
git add chains.json
git commit -m "feat: add chain configuration with explorer URLs"
```

---

### Task 4: Write the Aggregation Script with Tests

**Files:**
- Create: `scripts/aggregate.py`
- Create: `scripts/test_aggregate.py`

**Step 1: Write the failing test**

```python
# scripts/test_aggregate.py
import json
import os
import tempfile
import pytest
from aggregate import aggregate_hooks, generate_readme_table


@pytest.fixture
def hook_dir():
    """Create a temp directory with sample hook files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        eth_dir = os.path.join(tmpdir, "hooks", "ethereum")
        base_dir = os.path.join(tmpdir, "hooks", "base")
        os.makedirs(eth_dir)
        os.makedirs(base_dir)

        hook1 = {
            "hook": {
                "address": "0x0000000000000000000000000000000000002080",
                "chain": "ethereum",
                "chainId": 1,
                "name": "TestHook",
                "description": "A test hook",
                "deployer": "",
                "verifiedSource": True,
                "auditUrl": ""
            },
            "flags": {
                "beforeInitialize": True,
                "afterInitialize": False,
                "beforeAddLiquidity": False,
                "afterAddLiquidity": False,
                "beforeRemoveLiquidity": False,
                "afterRemoveLiquidity": False,
                "beforeSwap": True,
                "afterSwap": False,
                "beforeDonate": False,
                "afterDonate": False,
                "beforeSwapReturnsDelta": False,
                "afterSwapReturnsDelta": False,
                "afterAddLiquidityReturnsDelta": False,
                "afterRemoveLiquidityReturnsDelta": False
            },
            "properties": {
                "dynamicFee": False,
                "upgradeable": False,
                "requiresCustomSwapData": False
            }
        }

        hook2 = {
            "hook": {
                "address": "0x00000000000000000000000000000000000000C0",
                "chain": "base",
                "chainId": 8453,
                "name": "SwapHook",
                "description": "A swap hook",
                "deployer": "",
                "verifiedSource": True,
                "auditUrl": ""
            },
            "flags": {
                "beforeInitialize": False,
                "afterInitialize": False,
                "beforeAddLiquidity": False,
                "afterAddLiquidity": False,
                "beforeRemoveLiquidity": False,
                "afterRemoveLiquidity": False,
                "beforeSwap": True,
                "afterSwap": True,
                "beforeDonate": False,
                "afterDonate": False,
                "beforeSwapReturnsDelta": False,
                "afterSwapReturnsDelta": False,
                "afterAddLiquidityReturnsDelta": False,
                "afterRemoveLiquidityReturnsDelta": False
            },
            "properties": {
                "dynamicFee": False,
                "upgradeable": False,
                "requiresCustomSwapData": False
            }
        }

        with open(os.path.join(eth_dir, "0x0000000000000000000000000000000000002080.json"), "w") as f:
            json.dump(hook1, f)
        with open(os.path.join(base_dir, "0x00000000000000000000000000000000000000C0.json"), "w") as f:
            json.dump(hook2, f)

        yield tmpdir


def test_aggregate_hooks(hook_dir):
    hooks = aggregate_hooks(os.path.join(hook_dir, "hooks"))
    assert len(hooks) == 2
    chains = {h["hook"]["chain"] for h in hooks}
    assert chains == {"ethereum", "base"}


def test_aggregate_hooks_sorted_by_chain_then_address(hook_dir):
    hooks = aggregate_hooks(os.path.join(hook_dir, "hooks"))
    assert hooks[0]["hook"]["chain"] == "base"
    assert hooks[1]["hook"]["chain"] == "ethereum"


def test_aggregate_hooks_empty():
    with tempfile.TemporaryDirectory() as tmpdir:
        hooks = aggregate_hooks(tmpdir)
        assert hooks == []


def test_generate_readme_table(hook_dir):
    hooks = aggregate_hooks(os.path.join(hook_dir, "hooks"))
    table = generate_readme_table(hooks)
    assert "TestHook" in table
    assert "SwapHook" in table
    assert "ethereum" in table
    assert "base" in table
    assert "| Chain |" in table
```

**Step 2: Run test to verify it fails**

Run: `cd scripts && python -m pytest test_aggregate.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'aggregate'`

**Step 3: Write the aggregation script**

```python
#!/usr/bin/env python3
"""Aggregate individual hook JSON files into hooklist.json and README table."""
import json
import glob
import os
import sys


def aggregate_hooks(hooks_dir: str) -> list[dict]:
    """Read all hook JSON files and return sorted list."""
    hooks = []
    pattern = os.path.join(hooks_dir, "**", "*.json")
    for filepath in glob.glob(pattern, recursive=True):
        with open(filepath) as f:
            hooks.append(json.load(f))
    hooks.sort(key=lambda h: (h["hook"]["chain"], h["hook"]["address"].lower()))
    return hooks


def generate_readme_table(hooks: list[dict]) -> str:
    """Generate a markdown table summarizing all hooks."""
    if not hooks:
        return "_No hooks registered yet._"

    lines = [
        "| Chain | Address | Name | Flags | Dynamic Fee | Returns Delta | Upgradeable |",
        "|-------|---------|------|-------|-------------|---------------|-------------|",
    ]
    for h in hooks:
        hook = h["hook"]
        flags = h["flags"]
        props = h["properties"]

        active_flags = [k for k, v in flags.items() if v]
        flag_str = ", ".join(active_flags) if active_flags else "none"

        returns_delta = any([
            flags.get("beforeSwapReturnsDelta"),
            flags.get("afterSwapReturnsDelta"),
            flags.get("afterAddLiquidityReturnsDelta"),
            flags.get("afterRemoveLiquidityReturnsDelta"),
        ])

        addr_short = f"`{hook['address'][:6]}...{hook['address'][-4:]}`"
        lines.append(
            f"| {hook['chain']} | {addr_short} | {hook['name']} | {flag_str} "
            f"| {'Yes' if props['dynamicFee'] else 'No'} "
            f"| {'Yes' if returns_delta else 'No'} "
            f"| {'Yes' if props['upgradeable'] else 'No'} |"
        )
    return "\n".join(lines)


def main():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hooks_dir = os.path.join(repo_root, "hooks")
    hooklist_path = os.path.join(repo_root, "hooklist.json")
    readme_path = os.path.join(repo_root, "README.md")

    hooks = aggregate_hooks(hooks_dir)

    # Write hooklist.json
    with open(hooklist_path, "w") as f:
        json.dump(hooks, f, indent=2)
        f.write("\n")

    # Write README.md
    table = generate_readme_table(hooks)
    readme_content = f"# hooklist\n\nA public registry of Uniswap v4 hook deployments.\n\n## Registered Hooks\n\n{table}\n"
    with open(readme_path, "w") as f:
        f.write(readme_content)

    print(f"Aggregated {len(hooks)} hooks into hooklist.json")


if __name__ == "__main__":
    main()
```

**Step 4: Run tests to verify they pass**

Run: `cd scripts && python -m pytest test_aggregate.py -v`
Expected: All 4 tests PASS

**Step 5: Commit**

```bash
git add scripts/aggregate.py scripts/test_aggregate.py
git commit -m "feat: add aggregation script with tests"
```

---

### Task 5: Write the CLAUDE.md

**Files:**
- Create: `CLAUDE.md`

**Step 1: Create the CLAUDE.md file**

This is the instruction file Claude Code reads when running in CI. It tells Claude exactly how to analyze a hook.

````markdown
# Hooklist — CI Analysis Instructions

You are running in CI to analyze a Uniswap v4 hook submission. An issue has been opened with a chain and address. Your job is to fetch the verified source code, analyze it, and open a PR adding the hook to the registry.

## Step 1: Parse the Issue

Read the issue body. Extract:
- `chain` (required) — from the Chain dropdown
- `address` (required) — from the Hook Address field
- `name` (optional) — from the Hook Name field
- `description` (optional) — from the Description field
- `deployer` (optional) — from the Deployer Address field
- `auditUrl` (optional) — from the Audit URL field

## Step 2: Check for Duplicates

Check if `hooks/<chain>/<address>.json` already exists. If it does, comment on the issue that the hook is already registered and close the issue.

## Step 3: Decode Flags from Address

Uniswap v4 encodes hook permissions in the lowest 14 bits of the hook address. This is the authoritative source of truth — the PoolManager checks these bits at runtime.

Decode the address as a 160-bit integer and check each bit:

| Bit | Flag |
|-----|------|
| 13 | beforeInitialize |
| 12 | afterInitialize |
| 11 | beforeAddLiquidity |
| 10 | afterAddLiquidity |
| 9 | beforeRemoveLiquidity |
| 8 | afterRemoveLiquidity |
| 7 | beforeSwap |
| 6 | afterSwap |
| 5 | beforeDonate |
| 4 | afterDonate |
| 3 | beforeSwapReturnsDelta |
| 2 | afterSwapReturnsDelta |
| 1 | afterAddLiquidityReturnsDelta |
| 0 | afterRemoveLiquidityReturnsDelta |

Example: address ending in `...2080` → bits 13 and 7 set → `beforeInitialize` and `beforeSwap`.

## Step 4: Fetch Verified Source from Etherscan

Read `chains.json` to get the explorer URL for the chain. Then fetch verified source:

```bash
curl "EXPLORER_URL&module=contract&action=getsourcecode&address=ADDRESS&apikey=$ETHERSCAN_API_KEY"
```

For Etherscan V2 chains, use: `https://api.etherscan.io/v2/api?chainid=CHAIN_ID`
For Blockscout chains (zora, ink, soneium), use the `explorerUrl` from `chains.json` directly.

### Detecting Verification Status

- If `SourceCode` is empty string OR `ABI` equals `"Contract source code not verified"`, the source is NOT verified.
- In that case: comment on the issue explaining the source is not verified, add the `unverified` label, and stop.

### Parsing Multi-File Sources

- If `SourceCode` starts with `{{`, it's Solidity Standard JSON Input. Strip the outer `{` and `}`, parse the inner JSON, and read source files from the `sources` object.
- Otherwise, `SourceCode` is plain Solidity text.

### Proxy Contracts

- If the response has `"Proxy": "1"`, fetch the implementation contract source too using the `Implementation` address. Analyze the implementation, not the proxy.

## Step 5: Analyze the Source Code

Cross-reference the address-derived flags with the source code:

1. **Verify flags match source**: If the hook extends `BaseHook`, find `getHookPermissions()` and confirm it matches the address bits. Flag any discrepancy in the description.

2. **Detect `dynamicFee`**: Check if `beforeSwap` returns a fee override via the `lpFeeOverride` return value, or if the hook calls `poolManager.updateDynamicLPFee()`.

3. **Detect `upgradeable`**: Check for:
   - Proxy patterns (ERC-1967, transparent proxy, UUPS)
   - `delegatecall` usage
   - Mutable storage pointing to an implementation address
   - `SELFDESTRUCT` / `SELFDESTRUC` opcode usage

4. **Detect `requiresCustomSwapData`**: Check if the hook's `beforeSwap` or `afterSwap` reads from `hookData` parameter and requires specific encoded data (signatures, parameters, etc.) that a standard router would not provide. If `hookData` is only used for pass-through or is ignored, this is `false`.

5. **Generate name**: Use `ContractName` from the Etherscan response if the submitter didn't provide one.

6. **Generate description**: Write a 1-2 sentence summary of what the hook does, based on your analysis of the source code.

## Step 6: Generate the Hook JSON

Create `hooks/<chain>/<address>.json` matching the schema in `schema.json`. Use submitter-provided values for `name`, `description`, `deployer`, and `auditUrl` when present. Generate the rest from analysis.

## Step 7: Open a PR

1. Create a branch named `hooks/<chain>/<address>`
2. Commit the hook JSON file
3. Open a PR with:
   - Title: `Add <name> hook on <chain>`
   - Body containing:
     - Hook analysis summary
     - Flag table
     - Properties summary
     - Any warnings or discrepancies found
     - `Closes #<issue_number>`

## Reference: Hook JSON Schema

See `schema.json` for the full schema. See `hooks/` for examples.
````

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "feat: add CLAUDE.md with CI analysis instructions"
```

---

### Task 6: Create the analyze-hook Workflow

**Files:**
- Create: `.github/workflows/analyze-hook.yml`

**Step 1: Create the workflow file**

```yaml
name: Analyze Hook Submission

on:
  issues:
    types: [opened]

jobs:
  analyze:
    if: contains(github.event.issue.labels.*.name, 'submission') || contains(github.event.issue.title, 'hook:')
    runs-on: ubuntu-latest
    permissions:
      contents: write
      issues: write
      pull-requests: write
    steps:
      - uses: actions/checkout@v4

      - name: Install Claude Code
        run: npm install -g @anthropic-ai/claude-code

      - name: Analyze hook and open PR
        env:
          CLAUDE_CODE_OAUTH_TOKEN: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
          ETHERSCAN_API_KEY: ${{ secrets.ETHERSCAN_API_KEY }}
        run: |
          claude --print "Analyze the hook submission in issue #${{ github.event.issue.number }}.

          Issue title: ${{ github.event.issue.title }}
          Issue body:
          ${{ github.event.issue.body }}

          Follow the instructions in CLAUDE.md to:
          1. Parse the issue fields
          2. Check for duplicates
          3. Decode flags from the address
          4. Fetch and analyze verified source from Etherscan
          5. Generate the hook JSON file
          6. Open a PR that closes issue #${{ github.event.issue.number }}"
```

**Step 2: Commit**

```bash
git add .github/workflows/analyze-hook.yml
git commit -m "feat: add analyze-hook CI workflow"
```

---

### Task 7: Create the regenerate Workflow

**Files:**
- Create: `.github/workflows/regenerate.yml`

**Step 1: Create the workflow file**

```yaml
name: Regenerate Registry

on:
  push:
    branches: [main]
    paths: ['hooks/**']

jobs:
  regenerate:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Regenerate hooklist.json and README
        run: python scripts/aggregate.py

      - name: Commit changes
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add hooklist.json README.md
          git diff --staged --quiet || git commit -m "chore: regenerate hooklist.json and README"
          git push
```

**Step 2: Commit**

```bash
git add .github/workflows/regenerate.yml
git commit -m "feat: add regenerate workflow for hooklist.json and README"
```

---

### Task 8: Create Initial hooklist.json and README

**Files:**
- Create: `hooklist.json`
- Modify: `README.md`

**Step 1: Create empty hooklist.json**

```json
[]
```

**Step 2: Update README.md**

```markdown
# hooklist

A public registry of Uniswap v4 hook deployments.

## Registered Hooks

_No hooks registered yet._
```

**Step 3: Commit**

```bash
git add hooklist.json README.md
git commit -m "feat: add initial empty hooklist.json and README"
```

---

### Task 9: Add an Example Hook for Validation

**Files:**
- Create: `hooks/ethereum/0x0000000000000000000000000000000000002080.json`

**Step 1: Create the example hook file**

This serves as a reference example and validates the schema/aggregation pipeline. Use a fake address with known flag bits.

```json
{
  "hook": {
    "address": "0x0000000000000000000000000000000000002080",
    "chain": "ethereum",
    "chainId": 1,
    "name": "ExampleHook",
    "description": "Example hook for testing the registry pipeline. Address bits encode beforeInitialize and beforeSwap.",
    "deployer": "",
    "verifiedSource": false,
    "auditUrl": ""
  },
  "flags": {
    "beforeInitialize": true,
    "afterInitialize": false,
    "beforeAddLiquidity": false,
    "afterAddLiquidity": false,
    "beforeRemoveLiquidity": false,
    "afterRemoveLiquidity": false,
    "beforeSwap": true,
    "afterSwap": false,
    "beforeDonate": false,
    "afterDonate": false,
    "beforeSwapReturnsDelta": false,
    "afterSwapReturnsDelta": false,
    "afterAddLiquidityReturnsDelta": false,
    "afterRemoveLiquidityReturnsDelta": false
  },
  "properties": {
    "dynamicFee": false,
    "upgradeable": false,
    "requiresCustomSwapData": false
  }
}
```

**Step 2: Run aggregation to verify pipeline**

Run: `python scripts/aggregate.py`
Expected: `hooklist.json` updated with the example hook, README table generated.

**Step 3: Run tests**

Run: `cd scripts && python -m pytest test_aggregate.py -v`
Expected: All tests PASS

**Step 4: Commit**

```bash
git add hooks/ethereum/0x0000000000000000000000000000000000002080.json hooklist.json README.md
git commit -m "feat: add example hook and regenerate registry"
```

---

## Summary of Files Created

| File | Purpose |
|------|---------|
| `schema.json` | JSON Schema for hook files |
| `.github/ISSUE_TEMPLATE/submit-hook.yml` | Issue form for hook submissions |
| `chains.json` | Chain name → ID + explorer URL mapping |
| `scripts/aggregate.py` | Builds hooklist.json + README table |
| `scripts/test_aggregate.py` | Tests for aggregation script |
| `CLAUDE.md` | Instructions for Claude Code in CI |
| `.github/workflows/analyze-hook.yml` | CI workflow triggered on issue open |
| `.github/workflows/regenerate.yml` | CI workflow triggered on merge to main |
| `hooklist.json` | Auto-generated aggregate registry |
| `README.md` | Auto-generated summary with hook table |
| `hooks/ethereum/0x...2080.json` | Example hook for pipeline validation |

## Required Repository Secrets

- `CLAUDE_CODE_OAUTH_TOKEN` — already configured
- `ETHERSCAN_API_KEY` — needed for Etherscan V2 API calls
