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

For Blockscout chains (zora, ink, soneium), use the `explorerUrl` from `chains.json` instead:

```bash
curl -s "BLOCKSCOUT_URL?module=contract&action=getsourcecode&address=ADDRESS"
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

If the script prints `Verified: False`, the source is NOT verified. Comment on the issue explaining the source is not verified, add the `unverified` label, and stop.

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
