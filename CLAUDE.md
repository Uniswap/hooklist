# hooklist

Public registry of Uniswap v4 hook deployments across all supported chains.

## Project Structure

- `hooks/<chain>/<address>.json` — individual hook files, one per deployed hook
- `hooklist.json` — auto-generated aggregate of all hook files (built by CI on merge)
- `chains.json` — chain name → chain ID + block explorer API mapping
- `schema.json` — JSON Schema for hook files
- `scripts/aggregate.py` — reads all hook files, validates against schema, outputs `hooklist.json`
- `scripts/validate.py` — validates hook JSON files against `schema.json`
- `scripts/verify_flags.py` — verifies hook flags match the address bitmask
- `scripts/parse_etherscan.py` — parses Etherscan API responses, extracts source files to `.sources/`
- `.github/workflows/analyze-hook.yml` — CI: on issue open, Claude analyzes the hook and opens a PR
- `.github/workflows/validate.yml` — CI: on PR, validates schema + flag bitmask
- `.github/workflows/review-hook.yml` — CI: on PR, Claude reviews hook data against on-chain source
- `.github/workflows/regenerate.yml` — CI: on merge to main, rebuilds `hooklist.json`
- `.claude/prompts/analyze-hook.md` — prompt for the analyze-hook workflow
- `.claude/prompts/review-hook.md` — prompt for the review-hook workflow

## Hook File Format

Each hook file has three sections: `hook` (identity + metadata), `flags` (14 Uniswap v4 permission bits from the address bitmask), and `properties` (dynamicFee, upgradeable, requiresCustomSwapData). See `schema.json` for the full spec.

## Running Tests

```
nix-shell -p python312Packages.pytest python312Packages.jsonschema --run "cd scripts && python -m pytest test_aggregate.py -v"
```

## Git & PRs

This repository only allows **rebase merges** (no merge commits, no squash). Use `gh pr merge <number> --rebase --delete-branch` to merge PRs.

## Regenerating hooklist.json

```
python scripts/aggregate.py
```
