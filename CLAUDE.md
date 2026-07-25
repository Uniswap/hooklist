# hooklist

Public registry of Uniswap v4 hook deployments across all supported chains.

## Project Structure

- `hooks/<chain>/<address>.json` — individual hook files, one per deployed hook
- `index/<chain>.jsonl` — append-only mechanical ledger of every hook instance seen on-chain (`{address, block, family}` per line), written by `ingest.yml`
- `families/<id>.json` — code-family analyses, one per distinct hook codehash
- `hooklist.json` — auto-generated aggregate of all hook files (built by CI on merge)
- `chains.json` — chain name → chain ID + block explorer API + RPC/PoolManager scan config
- `schema.json` — JSON Schema for hook files
- `family.schema.json` — JSON Schema for family files
- `scripts/aggregate.py` — reads all hook files, validates against schema, outputs `hooklist.json`
- `scripts/validate.py` — validates hook and family JSON files against `schema.json` / `family.schema.json`
- `scripts/verify_flags.py` — verifies hook flags match the address bitmask
- `scripts/parse_etherscan.py` — parses Etherscan API responses, extracts source files to `.sources/`
- `scripts/evm.py` — EVM primitives: keccak256, `Initialize` event parsing, codehash
- `scripts/rpc.py` — minimal JSON-RPC client used by the scanner and ledger re-derivation
- `scripts/scan.py` — scans a chain's `PoolManager` `Initialize` events for new hook instances
- `scripts/ingest.py` — CLI entrypoint: scans configured chains, appends new index lines
- `scripts/index_ledger.py` — read/write helpers for the append-only `index/<chain>.jsonl` ledger
- `scripts/select_analyses.py` — selects which new families to dispatch for analysis (caps, dedupes in-flight/failed)
- `scripts/validate_index.py` — re-derives index lines from live chain state (mechanical-lane backstop)
- `scripts/assemble_family.py` — builds a `families/<id>.json` file from Claude's classification output, or as an unverified stub
- `scripts/build_artifacts.py` — builds published `dist/` artifacts (`families.json`, `lookup/<chain>.json`) from `index/` + `families/` + `hooks/`
- `scripts/seed_families.py` — one-time migration: derives `families/` and `index/` from existing `hooks/` files
- `scripts/check_chains.py` — verifies `chains.json` RPC config against live RPCs
- `.github/workflows/analyze-hook.yml` — CI: on issue open, Claude analyzes the hook and opens a PR
- `.github/workflows/validate.yml` — CI: on PR, validates schema + flag bitmask
- `.github/workflows/review-hook.yml` — CI: on PR, Claude reviews hook data against on-chain source
- `.github/workflows/regenerate.yml` — CI: on merge to main, rebuilds `hooklist.json` + `dist/` and publishes to Pages
- `.github/workflows/ingest.yml` — CI: scheduled (~30 min), scans chains and dispatches family analyses
- `.github/workflows/analyze-family.yml` — CI: dispatched per new family, Claude classifies it (or writes an unverified stub) and opens a PR
- `.claude/prompts/analyze-hook.md` — prompt for the analyze-hook workflow
- `.claude/prompts/review-hook.md` — prompt for the review-hook workflow
- `.claude/prompts/classify-family.md` — prompt for the analyze-family workflow

## Hook File Format

Each hook file has three sections: `hook` (identity + metadata), `flags` (14 Uniswap v4 permission bits from the address bitmask), and `properties` (dynamicFee, upgradeable, requiresCustomSwapData). See `schema.json` for the full spec.

## Running Tests

```
nix-shell -p python312Packages.pytest python312Packages.jsonschema python312Packages.pycryptodome --run "cd scripts && python -m pytest test_aggregate.py -v"
```

## Git & PRs

This repository only allows **rebase merges** (no merge commits, no squash). Use `gh pr merge <number> --rebase --delete-branch` to merge PRs.

## Regenerating hooklist.json

```
python scripts/aggregate.py
```
