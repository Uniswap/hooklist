# hooklist

A public registry of known [Uniswap v4](https://docs.uniswap.org/contracts/v4/overview) hook deployments across all supported chains.

## Browse Hooks

All registered hooks are in [`hooklist.json`](hooklist.json) and as individual files under [`hooks/`](hooks/), organized by chain:

```
hooks/
  ethereum/
    0xAbC...123.json
  base/
    0xDef...456.json
```

Each hook file contains:
- **Address, chain, and chain ID**
- **Hook flags** — all 14 Uniswap v4 permission bits (beforeSwap, afterSwap, etc.)
- **Properties** — dynamic fee, upgradeability, custom swap data requirements
- **Metadata** — name, description, deployer, audit URL

See [`schema.json`](schema.json) for the full schema.

## Data model

The registry is built from three stores:

- **`index/<chain>.jsonl`** — mechanical append-only ledger of every hook instance ever seen on a chain, one JSON object per line: `{"address", "block", "family"}`. Written by the scheduled [`ingest`](.github/workflows/ingest.yml) workflow, which scans `PoolManager` `Initialize` events.
- **`families/<id>.json`** — one code-family analysis per distinct hook bytecode, produced by the [`analyze-family`](.github/workflows/analyze-family.yml) workflow (or seeded from existing `hooks/` entries by `scripts/seed_families.py`). See [`family.schema.json`](family.schema.json).
- **`hooks/<chain>/<address>.json`** — the per-address entries described above, still the source for `hooklist.json`.

**Family identity.** A family's `id` is the keccak256 hash of the deployed bytecode (`scripts/evm.py`'s `codehash`); every address sharing that hash is the same family, regardless of chain or deployer. Two exceptions:
- **`empty-code`** — sentinel family used when `eth_getCode` still returns no code after the scanner has rechecked an address across 6 separate ingest runs (e.g. a `CREATE2` address referenced before deployment). It is not a real family and is never dispatched for analysis.
- **Dated observations** — an index line records what was true as of `block`, not a permanent guarantee. `scripts/validate_index.py` tolerates an `empty-code` line even if the address now has code (a later line is the correction, not a reason to reject the old one), and tolerates a line whose codehash no longer matches current on-chain code (pre-Cancun `SELFDESTRUCT` can empty a contract afterward).

**Flag derivation.** The 14 Uniswap v4 hook permission flags are the low 14 bits of the hook's address: `int(address, 16) & 0x3FFF`. Bit → flag (see `scripts/verify_flags.py`):

| Bit | Flag | Bit | Flag |
|---|---|---|---|
| 13 | beforeInitialize | 6 | afterSwap |
| 12 | afterInitialize | 5 | beforeDonate |
| 11 | beforeAddLiquidity | 4 | afterDonate |
| 10 | afterAddLiquidity | 3 | beforeSwapReturnsDelta |
| 9 | beforeRemoveLiquidity | 2 | afterSwapReturnsDelta |
| 8 | afterRemoveLiquidity | 1 | afterAddLiquidityReturnsDelta |
| 7 | beforeSwap | 0 | afterRemoveLiquidityReturnsDelta |

These address-derived flags are what an address *permits*; a family's `implementedPermissions` is what its code *actually implements*. The two can diverge — `scripts/build_artifacts.py` reports any mismatch as `flagDivergence` in `lookup/<chain>.json`.

## Consuming the registry

- **Pages artifacts** (rebuilt by [`regenerate`](.github/workflows/regenerate.yml) on every merge to main):
  - `https://uniswap.github.io/hooklist/families.json` — every family analysis, each with an `instanceCounts` breakdown per chain.
  - `https://uniswap.github.io/hooklist/lookup/<chain>.json` — every known hook instance on `<chain>`, joined with its family's analysis and flag divergence.
  - Both carry a `builtAt` stamp (UTC timestamp of the build); `lookup/<chain>.json` also carries `scannedToBlock` (the chain height the mechanical ledger had scanned to as of that build) — data about later blocks isn't reflected yet.
- **Committed files**, for consumers who don't use Pages, e.g. via jsDelivr:
  - `https://cdn.jsdelivr.net/gh/Uniswap/hooklist@main/hooklist.json`
  - `https://cdn.jsdelivr.net/gh/Uniswap/hooklist@main/hooklist-vanilla-swap.json`
  - Individual `hooks/<chain>/<address>.json` and `families/<id>.json` files are fetchable the same way.
- **`hooklist.json` remains the stable legacy artifact** — its shape is unchanged by this pipeline; it is still generated solely from `hooks/` by `scripts/aggregate.py`.

## Submit a Hook

[Open an issue](../../issues/new?template=submit-hook.yml) with the chain and hook address. Claude will automatically:

1. Fetch the verified source code from Etherscan
2. Decode the hook flags from the address bitmask
3. Analyze the source for dynamic fees, upgradeability, and custom swap data
4. Open a PR with the generated hook file

Optional fields (name, description, deployer, audit URL) can be provided in the issue — otherwise Claude generates them from the source code.

## Supported Chains

Ethereum, Unichain, Base, Arbitrum, Optimism, Polygon, Blast, Worldchain, Avalanche, BNB, Celo, Zora, Ink, Soneium, Linea, Monad, Robinhood Chain, MegaETH, Tempo, X Layer, zkSync

See [`chains.json`](chains.json) for chain IDs and block explorer mappings.

## How It Works

1. **Submission** — user opens an issue via the [Submit a Hook](../../issues/new?template=submit-hook.yml) template
2. **Analysis** — the [`analyze-hook`](.github/workflows/analyze-hook.yml) workflow runs Claude Code to fetch and analyze the hook
3. **Review** — Claude opens a PR with the hook JSON file; a maintainer reviews and merges
4. **Aggregation** — the [`regenerate`](.github/workflows/regenerate.yml) workflow rebuilds [`hooklist.json`](hooklist.json) from all individual hook files

## Uniswap Routing Allowlisting

Submitting your hook to this repository **DOES NOT** automatically cause your hook to be allowlisted for routing by Uniswap's routing algorithm. This is just a public registry of hooks. If you are looking to get your hook allowlisted for routing by Uniswap's routing algorithm, please visit https://share.hsforms.com/15fMHwt6NTzuKuQdxw6nHwws8pgg.