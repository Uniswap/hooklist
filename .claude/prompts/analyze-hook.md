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

**IMPORTANT: Use the Etherscan API, not the website. Never scrape etherscan.io HTML.**

Look up the chain in `chains.json` to get the `chainId`. Then fetch verified source using the Etherscan V2 API:

```bash
curl -s "https://api.etherscan.io/v2/api?chainid=CHAIN_ID&module=contract&action=getsourcecode&address=ADDRESS&apikey=$ETHERSCAN_API_KEY"
```

For Blockscout chains (zora, ink, soneium) and Routescan chains (avalanche), use the `explorerUrl` from `chains.json` instead (no API key needed):

```bash
curl -s "EXPLORER_URL?module=contract&action=getsourcecode&address=ADDRESS"
```

The `$ETHERSCAN_API_KEY` environment variable is available in CI.

### Fetching and parsing

Save the API response, then use the provided parsing script. Source code can be very large (100K+ chars), so never try to read it all at once.

```bash
# Fetch and save
curl -s "https://api.etherscan.io/v2/api?chainid=CHAIN_ID&module=contract&action=getsourcecode&address=ADDRESS&apikey=$ETHERSCAN_API_KEY" -o etherscan_response.json

# Parse response — prints metadata, writes individual source files to .sources/
python3 scripts/parse_etherscan.py etherscan_response.json
```

The script prints `ContractName`, `Proxy`, `Implementation`, and `Verified` status. If verified, it extracts all source files to `.sources/` within the working directory (handles both single-file and multi-file contracts).

Then use `Grep` to search `.sources/` for relevant patterns (getHookPermissions, beforeSwap, hookData, delegatecall, etc.) rather than trying to read entire files.

### Detecting Verification Status

If the script prints `Verified: False`, the source is NOT verified:

1. Add the `unverified` label:
```bash
gh issue edit <issue_number> --add-label unverified
```

2. Write a comment body to a file and post it (avoids shell escaping issues):
```bash
python3 -c "
with open('comment.md', 'w') as f:
    f.write('The source code for this hook is **not verified** on the block explorer. ')
    f.write('Please verify the contract source and resubmit once verification is complete.')
"
```
```bash
gh issue comment <issue_number> --body-file comment.md
```

3. Stop — do not close the issue or proceed with analysis or PR creation.

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

4. **Detect `requiresCustomSwapData`**: This is `true` if a normal swap (sending empty `hookData`) would **fail, revert, or produce materially incorrect behavior** because the hook requires specific encoded data (signatures, parameters, routing info, etc.) in `hookData`. If the hook merely inspects `hookData` for optional/ancillary features (e.g. an optional trade referrer via `if (hookData.length > 0)`) but swaps work correctly without it, this is `false`. In short: would an unsuspecting router or user sending no `hookData` have a bad experience?

5. **Detect `vanillaSwap`**: Determines whether, once a swap is allowed to execute, it behaves identically to a standard Uniswap v4 pool with no hook. Use this decision process:

   **Always `true` if:** the hook has no swap flags at all (`beforeSwap`, `afterSwap`, `beforeSwapReturnsDelta`, `afterSwapReturnsDelta` are all `false`).

   **Always `false` if ANY of these are true:**
   - `dynamicFee` is `true` (hook modifies fees)
   - `requiresCustomSwapData` is `true` (standard swap with empty hookData would fail)
   - `beforeSwapReturnsDelta` or `afterSwapReturnsDelta` is `true` (hook modifies swap amounts)
   - The hook executes nested swaps, transfers tokens, or calls `poolManager.swap()` inside `beforeSwap`/`afterSwap`
   - The hook modifies pool state in ways that change subsequent swap behavior (e.g., adjusting tick spacing, moving liquidity)

   **`true` if the hook has `beforeSwap`/`afterSwap` but they ONLY do:**
   - Access control: revert if caller/timing/state doesn't meet criteria (allow/deny gating)
   - Observation: recording prices, ticks, volumes, or timestamps for oracle/analytics purposes
   - Event emission: emitting events for off-chain indexing
   - Reading state without modifying it

   **Key distinction:** A hook that *blocks* a swap (reverts in beforeSwap) is vanilla — the swap either doesn't happen or happens normally. A hook that *changes* how the swap executes is NOT vanilla.

6. **Detect `swapAccess`**: Classify the hook's swap access control mechanism by searching the `beforeSwap` implementation:

   - `"none"` — No access control logic in beforeSwap. The hook either has no beforeSwap, or beforeSwap never reverts based on caller identity, timing, or external state. Default for most hooks.
   - `"temporal"` — Swaps gated by time. Look for: `block.timestamp` or `block.number` comparisons, `require(block.timestamp >= startTime)`, configurable start/end times, or phase-based timing logic.
   - `"allowlist"` — Only approved addresses can swap. Look for: `mapping(address => bool)` checks against `tx.origin` or `sender`, calls to external allowlist/registry contracts, Merkle proof verification, or KYC/Predicate authorization checks.
   - `"governance"` — An admin/owner must flip a flag to enable swaps. Look for: boolean storage like `migrated`, `tradingEnabled`, or `launched` that is set by an owner/admin function, with beforeSwap checking `require(migrated)` or similar. Includes single-owner gates, multi-sig gates, and role-based access control.
   - `"other"` — Some other mechanism not covered above (e.g., NFT-gated, token-balance-gated, signature-based).

   **Important:** A hook can be `vanillaSwap: true` with any `swapAccess` value — these are orthogonal. Access control determines *if* you can swap; vanillaSwap determines *how* the swap behaves once allowed. If the hook has no swap flags, `swapAccess` must be `"none"`.

7. **Generate name**: Use `ContractName` from the Etherscan response if the submitter didn't provide one.

8. **Generate description**: Write a 1-2 sentence summary of what the hook does, based on your analysis of the source code.

## Step 6: Generate the Hook JSON

Use the `Write` tool to create `hooks/<chain>/<address>.json` matching the schema in `schema.json`. The Write tool creates parent directories automatically — do not use `mkdir`. Use submitter-provided values for `name`, `description`, `deployer`, and `auditUrl` when present. Generate the rest from analysis.

**IMPORTANT: `deployer` must be a valid Ethereum address (`0x` + 40 hex chars) or an empty string `""`. If the submitter provides a name or organization instead of an address, discard it and use `""`. Never put a human-readable name in the `deployer` field.**

## Step 7: Open a PR

**Important: Run each git/gh command as a separate Bash call. Do not chain commands with `&&`.**

```bash
git checkout -b hooks/<chain>/<address>
```

```bash
git add hooks/<chain>/<address>.json
```

```bash
git commit -m "Add <name> hook on <chain>"
```

```bash
git push -u origin hooks/<chain>/<address>
```

Use the `Write` tool to create `pr_body.md` with the PR description, then create the PR with `--body-file`. This ensures proper markdown formatting.

```bash
gh pr create --title "Add <name> hook on <chain>" --body-file pr_body.md
```

The PR body should contain:

```markdown
## Summary
<1-2 sentence description>

## Flags
| Flag | Value |
|------|-------|
| beforeInitialize | true/false |
| afterInitialize | true/false |
| beforeAddLiquidity | true/false |
| afterAddLiquidity | true/false |
| beforeRemoveLiquidity | true/false |
| afterRemoveLiquidity | true/false |
| beforeSwap | true/false |
| afterSwap | true/false |
| beforeDonate | true/false |
| afterDonate | true/false |
| beforeSwapReturnsDelta | true/false |
| afterSwapReturnsDelta | true/false |
| afterAddLiquidityReturnsDelta | true/false |
| afterRemoveLiquidityReturnsDelta | true/false |

## Properties
| Property | Value |
|----------|-------|
| dynamicFee | true/false |
| upgradeable | true/false |
| requiresCustomSwapData | true/false |
| vanillaSwap | true/false |
| swapAccess | none/temporal/allowlist/governance/other |

## Warnings
<any discrepancies or notes, or "None">

Closes #<issue_number>
```

## Reference: Hook JSON Schema

See `schema.json` for the full schema. See `hooks/` for examples.
