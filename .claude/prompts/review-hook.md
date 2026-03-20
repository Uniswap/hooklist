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

4. **vanillaSwap**: Should be `true` if the hook's beforeSwap/afterSwap do not modify swap pricing, amounts, or deltas — only access control, logging, or observation. Should be `true` if the hook has no swap flags. Should be `false` if the hook executes trades, modifies fees, returns deltas, or alters swap mechanics in any way.

5. **swapAccess**: Should accurately classify the hook's swap access control: `"none"` if no restrictions, `"temporal"` for time-based gates, `"allowlist"` for address-based restrictions, `"governance"` for admin-controlled gates, `"other"` for anything else.

### 2d: Check Metadata

- `verifiedSource` should be `true` if Etherscan has verified source code
- `name` should match `ContractName` from Etherscan (or be a reasonable override)
- `description` should accurately describe what the hook does
- `chainId` should match the chain in `chains.json`

## Step 3: Output Your Review

Provide your findings as structured JSON. The workflow will post the review for you.

- If everything checks out, set `outcome` to `"APPROVE"` and summarize your verification in `review_body`.
- If there are issues, set `outcome` to `"REQUEST_CHANGES"` and explain in `review_body` what's wrong and what the correct values should be.
