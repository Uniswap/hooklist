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

## Releases

A release file captures a reviewed family analysis: name, description, the five hook properties, warnings, and source/audit links. Each release is a separate PR, reviewed and merged once; later instances of the same hook family (factory deployments, forks, or audited variants) may reference the release via a thin pointer file (containing only address, chain, chainId, optional deployer/description, and the release reference). These thin files are expanded at build time to include all properties from their release. The published `hooklist.json` remains unchanged for consumers — they see a flat list of complete hook records regardless of whether a hook's data came from a full file or a thin pointer.

To submit a new release (a family you've reviewed and want to make available for instances), open a PR adding one or more `releases/<project>/<release-id>.json` files, optionally with member hook files that reference them. To submit a new instance of an existing release, use the normal [hook submission process](#submit-a-hook); Claude's bot will automatically detect and match it to the release.

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