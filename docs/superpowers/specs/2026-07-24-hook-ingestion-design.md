# Automated Hook Ingestion — Design

**Date:** 2026-07-24
**Status:** Approved design, pending implementation plan

## Goal

Make hooklist a responsive, comprehensive, public system-of-record for every Uniswap v4 hook deployed on every supported chain — discovered automatically from `Initialize` events, deduplicated by code family, honest about unverified and mutable contracts, and still consumable as plain JSON over a CDN with zero infrastructure.

It also becomes the shared storage layer for the backend autonomous vetting loop (Uniswap/backend#10753): the loop reads the registry to learn "what's new" and "what's known" instead of keeping an internal ledger.

## Decisions (settled during brainstorming)

1. **Repo role:** shared public system-of-record. Every hook seen on-chain gets an entry, including unverified ones. Ecosystem-wide resource, not just Uniswap's.
2. **Storage root:** git stays canonical. Data is split by trust level, not by entity type.
3. **Neutrality:** the registry stores objective facts and analysis warnings only. No allow/deny verdicts — integrators (including Uniswap's backend) derive their own policy.
4. **Discovery:** repo-native scheduled GitHub Action scanning `Initialize` events via public RPCs. Replayable by anyone; no dependency on internal infra. ClickHouse is only an occasional cross-check.
5. **Pipeline shape:** two-lane — a mechanical lane for provable facts, a reviewed lane for judgment.
6. **The new system wraps the existing one; it does not replace it.** `hooks/`, `schema.json`, the analyze/review workflows, and today's `hooklist.json` all keep working. New capability is additive.

## Core model

### Two trust lanes

Every datum belongs to exactly one lane:

| Lane | Content | Verification | Merge policy |
|---|---|---|---|
| **Mechanical** | Instance observations: address, block, codehash, address-derived flag mask | CI independently re-derives every fact (event log + `eth_getCode` + bit math; flags need no RPC at all) | Auto (see Governance) |
| **Judgment** | Analysis: name, description, implemented permissions, properties, warnings | AI analysis + bot review + human review (existing flow) | Reviewed PR |

### Family identity

**Family id = `keccak(eth_getCode(address))` — the codehash of the code at the hook address.** Uniform for every contract; no proxy-pattern enumeration, no slot reading, no composite keys.

The analysis lane classifies each family's **kind**:

- **`self-contained`** — behavior fully determined by the codehash (the overwhelming majority: mined-address immutable hooks). Analysis is done once per family and never goes stale. All dedup wins live here: 50,000 launchpad instances of one family cost one analysis.
- **`delegating`** — the code forwards behavior elsewhere (ERC-1967, UUPS, beacon, diamond, custom delegatecall — the analysis lane decides from source; "unsure" defaults to `delegating`). The family file states only "proxy shell; behavior not determined by this codehash."

**Instances of delegating families are analyzed per-address into `hooks/<chain>/<address>.json` — today's format and location, unchanged** (plus `family`, `analyzedAtBlock`, `upgradeable: true`). Proxy hooks are rare, so per-address scales. The registry never stores a "current implementation" pointer — it makes an explicitly dated snapshot claim. Consumers who would route through a mutable hook need live monitoring regardless; the backend's decision matrix hard-denies upgradeable hooks, so `upgradeable: true` is decision-complete for Uniswap routing.

EIP-1167 minimal clones: the target address is immutable in the clone bytecode; the analysis follows it once and classifies `self-contained` if the target is immutable.

### Flags are instance-level; implemented permissions are family-level

Hook flags are a function of the **address** bits (the PoolManager consults only these). The **code** independently determines which callbacks are implemented. Effective behavior is the intersection.

- Index lines carry the 14-bit mask derived from the address — pure string math, verifiable from the diff alone.
- Family files carry `implementedPermissions` — what the code supports, from source analysis. Absent for unverified families.
- Divergence is computed at build time and surfaced as a per-instance warning: bit set but not implemented → callbacks fail, pools may be broken (serious); implemented but bit unset → dormant callback (informational).

### Unverified contracts

An unverified family still gets a family file: `sourceStatus: "unverified"`, no `implementedPermissions`, no `properties`, no speculation. Its instances still carry address-derived flags — "we know the flags and say it's unverified, so we don't know anything else."

`repoUrl` lets a maintainer PR in an off-chain source repository for an unverified family; this re-queues analysis, with results clearly marked as analyzed-from-unattested-source.

## Repo layout

Three stores, one per role. Everything else is unchanged.

```
index/<chain>.jsonl             # mechanical: one line per hook instance, append-only
index/cursors.json              # mechanical: per-chain scan state
families/<codehash>.json        # judgment: one file per code family (new)
hooks/<chain>/<address>.json    # judgment: per-address entries — existing format, now
                                #   used for delegating-family instances and curated
                                #   per-address enrichment (deployer, auditUrl, …)
chains.json                     # gains: rpcUrls[], poolManager, deployBlock, confirmations
schema.json                     # unchanged (hooks/); family.schema.json + index line schema added
```

### Family file schema (sketch)

Deliberately shaped like today's hook files with the per-address identity swapped for a codehash — one mental model, two keys:

```json
{
  "family": {
    "id": "0x<codehash>",
    "kind": "self-contained | delegating",
    "name": "DopplerV4Hook",
    "description": "…",
    "sourceStatus": "verified | unverified | analysis-failed",
    "repoUrl": "",
    "auditUrl": "",
    "analyzedAt": "2026-07-24"
  },
  "implementedPermissions": { "beforeSwap": true, "…": false },
  "properties": {
    "dynamicFee": true,
    "requiresCustomSwapData": false,
    "vanillaSwap": false,
    "swapAccess": "none"
  },
  "warnings": ["…"]
}
```

Notes:
- `upgradeable` is not a property of self-contained families; it appears on per-address entries of delegating instances, or as a warning when source shows delegatecall/selfdestruct.
- `warnings` is the existing freeform mechanism from the analyze flow, reused as-is. A controlled machine-readable vocabulary is deferred until a consumer actually needs one.
- No `chains` list on the family — where a family is deployed is mechanical data, derived from the index at build time. Judgment files never need mechanical updates.

### Index line schema (sketch)

```jsonl
{"address":"0x…2080","family":"0xabc…","block":31280045,"flags":"0x2080"}
```

- Chain is implied by the filename. Addresses lowercased (retires the historical case-collision problem).
- Append-only; re-scans dedupe on address; a lost cursor only causes harmless re-scanning.

## Pipeline

### `ingest.yml` — mechanical lane (cron ~30 min)

One run scans **all chains** (sequentially or matrixed), commits **once**, and only when there is something to commit:

1. Per chain: `eth_getLogs(Initialize)` on the PoolManager from `cursor` to `head − confirmations` (reorg buffer), in bounded chunks per run.
2. For each new hook address: `eth_getCode` → codehash; decode flag mask from the address string.
3. Append lines to `index/<chain>.jsonl`; advance cursors.
4. Commit/PR only if new instances were found, or if a chain's unscanned window exceeds a threshold (so quiet chains don't accumulate unbounded re-scan windows).
5. For every new family id with no `families/` file, dispatch `analyze-family.yml`.

Backfill and steady state are the same code path: cursors start at each PoolManager's deploy block, and the first runs simply take more cycles to catch up. The completed backfill is sanity-checked against a ClickHouse `select distinct chain_id, hooks from v4_initialize` count.

Per-chain isolation: a chain's cursor advances only on its success; one chain's RPC issues never block others. Multiple `rpcUrls` per chain as fallbacks.

### Governance for the mechanical lane

The repo ruleset requires 2 reviews (bot + human), which would stall mechanical PRs on human attention ~48×/day. Since every index line is CI-re-derivable, human review adds no safety here. **Recommendation:** grant the existing registry GitHub App bypass on the ruleset and have `ingest.yml` push index-only commits directly to main, with `validate.yml` re-derivation running on push as the backstop; a commit touching anything outside `index/` fails validation loudly. Fallback if bypass is unacceptable: auto-merge PRs and accept the review-latency on index freshness.

### `analyze-family.yml` — judgment lane (dispatched per new family)

1. Pick any one instance address of the new family.
2. Run the **existing** fetch-source → parse → Claude-classify machinery, retargeted at families (adds: classify kind, implementedPermissions).
3. Unverified source → emit the minimal unverified family file (no speculation).
4. Delegating kind → also analyze its instances per-address into `hooks/` (existing analyze flow, nearly verbatim).
5. Open a reviewed PR through the existing bot-review + human-review flow.

**Retry-by-absence:** a missing family file *is* the retry queue. Analysis failure leaves no file; the next ingest run re-dispatches. After 3 failures (tracked by counting prior failed workflow runs, not stored state), write a stub (`sourceStatus: "analysis-failed"`) and open a labeled issue for a human — the escalation channel.

### `regenerate.yml` — build + publish (on merge to main)

Today's artifacts keep building exactly as they do now. New artifacts are added alongside, published to **GitHub Pages** (jsDelivr documented as an alternative):

| Artifact | Contents | Audience | Status |
|---|---|---|---|
| `hooklist.json` | per-address entries from `hooks/` | existing frontends | unchanged |
| `hooklist-vanilla-swap.json` | vanilla-swap subset | existing consumers | unchanged |
| `families.json` | all family files + per-chain instance counts | frontends rendering hook varieties | new |
| `index/<chain>.json` | address → family/flags lookup | integrators resolving a specific hook | new |
| `hooklist-full.json.gz` | index ⋈ families, everything | DB ingesters | new |

Every new artifact carries honesty stamps: `builtAt` plus per-chain `scannedToBlock`. Flag masks are expanded to the familiar 14-boolean object in built artifacts. Once consumers migrate to `families.json`, `hooklist.json` can be deprecated on its own schedule — no forced migration.

### Existing issue-driven flow

Survives as the **enrichment path**: community submissions contribute name/description/auditUrl/repoUrl to a family (or request analysis priority), rather than being the only way into the registry.

## Backend integration (Uniswap/backend#10753)

- **"What's new":** the loop diffs `index/*.jsonl` (or built per-chain indexes) against families it has evaluated.
- **"What's known":** family files provide kind, sourceStatus, properties, warnings.
- **Ledger collapse:** "have I tried this hook?" = does a family file exist and what is its `sourceStatus`; the loop's 7-day pending TTL and separate review-ledger artifact become unnecessary.
- **Verdicts stay in the backend**, derived from properties/warnings + policy (e.g. hard-deny upgradeable). The registry stays neutral.
- Evaluation is per-family, not per-address — the loop's workload shrinks by the dedup factor.

## Error handling summary

- **Reorgs:** scan only to `head − confirmations` (per-chain setting, default 30).
- **RPC failures:** per-chain isolation; cursor advances only on success; fallback RPC URLs; bounded chunk sizes for `getLogs` provider limits.
- **Idempotency:** append-dedupe on address; re-scanning is harmless.
- **Analysis failures:** retry-by-absence; stub + escalation issue after 3 failures.
- **Explorer rate limits:** analyses run serially, dispatched one family at a time.
- **No internal state that can drift:** git + the chain are jointly the entire pipeline state.

## Rollout plan (additive — nothing breaks at any step)

1. Add `families/`, `index/` schemas + scripts + tests. Existing system untouched.
2. One-time enrichment: fetch codehash for the existing 421 hooks (one RPC sweep), group them, generate family files from the richest existing analysis per codehash, seed index lines. `hooks/` files stay exactly where they are.
3. Enable `ingest.yml` per chain progressively: small chains first (soneium, celo), Base last once chunking is proven. Deploy-block backfill doubles as the comprehensiveness pass; cross-check totals against ClickHouse.
4. Add new artifacts + Pages publishing to `regenerate.yml`.
5. Point the backend loop at the registry; retire its internal ledger plan.
6. (Eventually, consumer-paced) migrate frontends to `families.json`; deprecate redundant per-address files for self-contained families.

## Testing

Extend the existing pytest setup (`scripts/test_*.py`):

- Scanner: log parsing, cursor math, chunking, reorg buffer, per-chain isolation (mocked RPC).
- Codehash/family grouping; flag-mask decode (property test against the 14-bit table).
- JSONL append/dedupe idempotency.
- Family/index schema validation.
- Build: artifact generation, flags-mismatch warning computation, honesty stamps, unchanged legacy artifacts.
- Migration: fixture-based test over a sample of real `hooks/` files.
- `validate.yml` gains index-line re-derivation — the property that makes the mechanical lane safe (public RPC endpoints suffice at PR volume).

## Out of scope (explicitly)

- Upgrade tracking for delegating instances (event watching, impl sweeps): deliberately omitted; a dated snapshot + `upgradeable: true` is decision-complete for known consumers. Can be added later, purely additively.
- Machine-readable risk-finding vocabulary: deferred until a consumer needs it; `warnings` suffices.
- Allow/deny verdicts, routing policy, notifications/comms (Slack digests, Linear escalation): backend concerns. The registry's labeled escalation issues are its only human-attention channel.
- Serving infrastructure beyond GitHub Pages/jsDelivr.
