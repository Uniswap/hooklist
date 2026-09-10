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
- `.claude/prompts/classify-hook.md` — prompt for the analyze-hook workflow's classification step
- `.claude/prompts/analyze-hook.md` — reference-only walkthrough (not wired to any workflow)
- `.claude/prompts/review-hook.md` — prompt for the review-hook workflow
- `releases/<project>/<release-id>.json` — reviewed per-family release records (spec: docs/superpowers/specs/2026-08-27-hook-release-registry.md)
- `release.schema.json` — JSON Schema for release files
- `scripts/draft_releases.py` — backfill assistant: drafts release files for duplicated-name families
- `scripts/dedupe_case_pairs.py` — case-collision detector (reads git plumbing, not the working tree)
- `scripts/fetch_codehash.py` — sha256 fingerprint of an address's runtime bytecode (explorer proxy API, public-RPC fallback, with retry/backoff)
- `scripts/release_verdict.py` — computes a single hook file's release-codehash verdict (match/match-upgradeable/no-cached-review/no-list/fetch-failed/invalid-ref) with a release-ref path-traversal guard; used by the review-hook workflow
- `scripts/backfill_codehashes.py` — one-off: populates `source.codeHashes` on releases from live member bytecode
- `scripts/update_codehash_index.py` — post-merge machine maintenance: appends any pointer-carrying member's live runtime hash missing from its release's `source.codeHashes` review cache (best-effort, never fails the job); wired into `regenerate.yml` after validation

## Hook File Format

Each hook file has three sections: `hook` (identity + metadata), `flags` (14 Uniswap v4 permission bits from the address bitmask), and `properties` (dynamicFee, upgradeable, requiresCustomSwapData). See `schema.json` for the full spec. A hook file may carry `hook.release` (`"<project>/<release-id>"`). Thin files (pointer + address/chain/chainId + optional deployer/description) are joined against the release at build time; full files that carry a pointer must have `properties` identical to the release's (CI-enforced). Release paths and ids are lowercase and immutable. Releases carry `source.codeHashes` — a sorted, machine-maintained review cache (kept current by `scripts/update_codehash_index.py`, post-merge) of `sha256:` fingerprints of reviewed members' runtime bytecode; the review workflow mechanically checks a pointer-carrying submission's bytecode against it (match / match-upgradeable / no-cached-review / no-list / fetch-failed, resolved against the trusted checkout).

## Running Tests

```
nix-shell -p python312Packages.pytest python312Packages.jsonschema --run "cd scripts && python -m pytest -v"
```

## Git & PRs

This repository only allows **rebase merges** (no merge commits, no squash). Use `gh pr merge <number> --rebase --delete-branch` to merge PRs.

## Regenerating hooklist.json

```
python scripts/aggregate.py
```
