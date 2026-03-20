# Hooklist — PR Review Instructions

You are reviewing a PR that adds or modifies a Uniswap v4 hook file. Your job is to verify the hook metadata is correct by fetching the on-chain source code and cross-referencing it.

## Step 1: Identify Changed Hook Files

Find which `hooks/<chain>/<address>.json` files were added or modified in this PR.

## Step 2: For Each Hook File

### 2a: Verify the Address Flags

Decode the lowest 14 bits of the hook address and confirm the `flags` section matches. The `validate.yml` workflow already checks this, but confirm it in your review.

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

### 2b: Fetch and Analyze Source Code

Look up the chain in `chains.json` to get the `chainId`. Fetch verified source:

```bash
curl -s "https://api.etherscan.io/v2/api?chainid=CHAIN_ID&module=contract&action=getsourcecode&address=ADDRESS&apikey=$ETHERSCAN_API_KEY" -o etherscan_response.json
```

For Blockscout chains (zora, ink, soneium) and Routescan chains (avalanche), use the `explorerUrl` from `chains.json` instead (no API key needed).

Parse the response:
```bash
python3 scripts/parse_etherscan.py etherscan_response.json
```

Then use `Grep` to search `.sources/` for relevant patterns.

### 2c: Verify Properties

Cross-reference the `properties` section against the source code:

1. **dynamicFee**: Should be `true` if `beforeSwap` returns a fee override via `lpFeeOverride`, or if the hook calls `poolManager.updateDynamicLPFee()`.

2. **upgradeable**: Should be `true` if the contract uses proxy patterns, `delegatecall`, mutable implementation storage, or `SELFDESTRUCT`.

3. **requiresCustomSwapData**: Should be `true` if a normal swap with empty `hookData` would **fail, revert, or produce materially incorrect behavior** — i.e. the hook requires specific encoded data (signatures, parameters, routing info, etc.) to function. Should be `false` if swaps work correctly without `hookData`, even if the hook optionally inspects it for ancillary features (e.g. an optional trade referrer).

4. **vanillaSwap**: Verify this answers: "Once a swap is allowed to execute, does it behave identically to a standard v4 pool?"

   **Must be `false` if ANY of:** `dynamicFee` is true, `requiresCustomSwapData` is true, `beforeSwapReturnsDelta` or `afterSwapReturnsDelta` is true, the hook executes nested swaps or transfers tokens inside beforeSwap/afterSwap, or the hook modifies pool state that changes swap behavior.

   **Must be `true` if:** the hook has no swap flags at all.

   **Can be `true` if:** the hook has beforeSwap/afterSwap but they only perform access control (revert-based gating), observation (recording prices/ticks/volumes), or event emission — without modifying how the swap executes.

   A hook that *blocks* swaps (reverts) is vanilla. A hook that *changes* how swaps execute is not.

5. **swapAccess**: Verify the classification matches the actual access control mechanism in beforeSwap:
   - `"none"` — beforeSwap has no access control, or the hook has no swap flags
   - `"temporal"` — gates on `block.timestamp` or `block.number` (configurable start/end times)
   - `"allowlist"` — checks caller against an approved address set, registry, or Merkle proof
   - `"governance"` — checks a boolean flag (e.g., `migrated`, `tradingEnabled`) set by an owner/admin
   - `"other"` — any other gating mechanism

   These are orthogonal to `vanillaSwap` — a hook can be vanilla with restricted access.

### 2d: Check Metadata

- `verifiedSource` should be `true` if Etherscan has verified source code
- `name` should match `ContractName` from Etherscan (or be a reasonable override)
- `description` should accurately describe what the hook does
- `chainId` should match the chain in `chains.json`

## Step 3: Output Your Review

Provide your findings as structured JSON. The workflow will post the review for you.

- If everything checks out, set `outcome` to `"APPROVE"` and summarize your verification in `review_body`.
- If there are issues, set `outcome` to `"REQUEST_CHANGES"` and explain in `review_body` what's wrong and what the correct values should be.
