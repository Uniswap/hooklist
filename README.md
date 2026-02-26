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

## Submit a Hook

[Open an issue](../../issues/new?template=submit-hook.yml) with the chain and hook address. Claude will automatically:

1. Fetch the verified source code from Etherscan
2. Decode the hook flags from the address bitmask
3. Analyze the source for dynamic fees, upgradeability, and custom swap data
4. Open a PR with the generated hook file

Optional fields (name, description, deployer, audit URL) can be provided in the issue — otherwise Claude generates them from the source code.

## Supported Chains

Ethereum, Unichain, Base, Arbitrum, Optimism, Polygon, Blast, Worldchain, Avalanche, BNB, Celo, Zora, Ink, Soneium

See [`chains.json`](chains.json) for chain IDs and block explorer mappings.

## How It Works

1. **Submission** — user opens an issue via the [Submit a Hook](../../issues/new?template=submit-hook.yml) template
2. **Analysis** — the [`analyze-hook`](.github/workflows/analyze-hook.yml) workflow runs Claude Code to fetch and analyze the hook
3. **Review** — Claude opens a PR with the hook JSON file; a maintainer reviews and merges
4. **Aggregation** — the [`regenerate`](.github/workflows/regenerate.yml) workflow rebuilds [`hooklist.json`](hooklist.json) from all individual hook files
