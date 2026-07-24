# Automated Hook Ingestion — Design

**Date:** 2026-07-24
**Status:** Approved design (2 self-review passes + fresh-eyes subagent review), pending implementation plan

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

Every datum belongs to exactly one lane. The lane is determined by *content*, not by which file it lives in:

| Lane | Content | Verification | Merge policy |
|---|---|---|---|
| **Mechanical** | Instance observations (address, block, codehash, address-derived flag mask) **and unverified family stubs** (codehash + `sourceStatus: "unverified"` — zero judgment content) | CI independently re-derives every fact (event log, `eth_getCode`, bit math, explorer verification status) | Auto (see Governance) |
| **Judgment** | Analysis of verified source: name, description, kind, implemented permissions, properties, warnings | AI analysis + bot review + human review (existing flow) | Reviewed PR |

Unverified families are expected to be the *majority* of auto-discovered families; keeping their stubs in the mechanical lane is what keeps human review load proportional to verified, analyzable code.

### Family identity

**Family id = `keccak(eth_getCode(address))` — the codehash of the code at the hook address, recorded as an observation at scan time.** Uniform for every contract; no proxy-pattern enumeration, no slot reading, no composite keys. (Metamorphic CREATE2 redeploys can change code under an address; the index line's `block` dates the observation, and a later re-observation appends a corrected line — same latest-wins semantics as everything else.)

The analysis lane classifies each family's **kind**:

- **`self-contained`** — behavior determined by the codehash (the overwhelming majority: mined-address immutable hooks). Analysis is done once per family and never goes stale. All dedup wins live here: 50,000 launchpad instances of one family cost one analysis. Family claims are **code-capability claims only** ("has an allowlist", "can set dynamic fee") — instance-specific configuration set in storage (owner, fee bps, registry addresses) can differ between siblings and is out of family scope (per-address enrichment in `hooks/` covers it when it matters).
- **`delegating`** — the code forwards behavior elsewhere (ERC-1967, UUPS, beacon, diamond, custom delegatecall — the analysis lane decides from source; "unsure" defaults to `delegating`).
- **`unknown`** — source not available (`sourceStatus != "verified"`). Kind is only decidable with source in hand.

**Instances of delegating families are analyzed per-address into `hooks/<chain>/<address>.json` — today's format and location** (schema gains one optional field: `analyzedAtBlock`). Proxy hooks are rare, so per-address scales. The registry never stores a "current implementation" pointer — it makes an explicitly dated snapshot claim. Consumers who would route through a mutable hook need live monitoring regardless; the backend's decision matrix hard-denies upgradeable hooks, so `upgradeable: true` is decision-complete for Uniswap routing.

`hooks/` files do **not** carry a family reference — the linkage is derivable at build time by joining the index on address, so judgment files never need mechanical updates (same rule as families never listing their chains).

EIP-1167 minimal clones: the target address is immutable in the clone bytecode; the analysis follows it once and classifies `self-contained` if the target is immutable.

### Flags are instance-level; implemented permissions are family-level

Hook flags are a function of the **address** bits (the PoolManager consults only these). The **code** independently determines which callbacks are implemented. Effective behavior is the intersection.

- Index lines carry the 14-bit mask derived from the address — redundant with the address by construction, kept deliberately: it is verifiable from the diff alone and saves every consumer the bit math.
- Family files carry `implementedPermissions` — what the code supports, from source analysis. Absent unless `sourceStatus: "verified"`.
- Divergence is computed at build time and surfaced as per-instance fields in the built lookup artifacts (not stored in git): bit set but not implemented → callbacks fail, pools may be broken (serious); implemented but bit unset → dormant callback (informational).

### Unverified contracts

An unverified family gets a **stub** family file: `sourceStatus: "unverified"`, `kind: "unknown"`, no `implementedPermissions`, no `properties`, no speculation. Its instances still carry address-derived flags — "we know the flags and say it's unverified, so we don't know anything else." The stub is mechanical-lane content (its only claims are CI-checkable).

`repoUrl` lets a maintainer PR in an off-chain source repository for an unverified family; this re-queues analysis, with results clearly marked as analyzed-from-unattested-source.

## Repo layout

Three stores, one per role. Everything else is unchanged.

```
index/<chain>.jsonl             # mechanical: one line per hook instance, append-only
index/cursors.json              # mechanical: per-chain scan state + pending-code recheck list
families/<codehash>.json        # per-codehash entries: stubs (mechanical) or analyses (judgment)
hooks/<chain>/<address>.json    # judgment: per-address entries — existing format, now
                                #   used for delegating-family instances and curated
                                #   per-address enrichment (deployer, auditUrl, …)
chains.json                     # gains: rpcUrls[], poolManager, deployBlock, confirmations
schema.json                     # gains one optional field (analyzedAtBlock); family.schema.json
                                #   + index line schema added
```

Address-case convention: index lines are lowercased (retiring the historical case-collision problem); existing `hooks/` filenames keep their historical mixed case — build-time joins normalize case, so the two conventions never meet.

### Family file schema (sketch)

Deliberately shaped like today's hook files with the per-address identity swapped for a codehash — one mental model, two keys:

```json
{
  "family": {
    "id": "0x<codehash>",
    "kind": "self-contained | delegating | unknown",
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
- `implementedPermissions`, `properties`, `warnings` present only when `sourceStatus: "verified"` (stubs stop at the `family` block).
- `upgradeable` is not a property of self-contained families; it appears on per-address entries of delegating instances, or as a warning when source shows delegatecall/selfdestruct.
- `warnings` persists what the existing analyze flow already produces in its structured output but today only surfaces in PR bodies — this is new registry surface, worth its rent: it is the neutral home for risk observations. A controlled machine-readable vocabulary is deferred until a consumer needs one.

### Index line schema (sketch)

```jsonl
{"address":"0x…2080","family":"0xabc…","block":31280045,"flags":"0x2080"}
```

- Chain is implied by the filename; addresses lowercased.
- Append-only; dedupe on address applies to resolved lines; a lost cursor only causes harmless re-scanning.
- `family` is the codehash observed when the line was written; corrections (metamorphic redeploys, late code) append a new line for the same address — latest wins at build time.

## Pipeline

### `ingest.yml` — mechanical lane (cron ~30 min)

Declares `concurrency: { group: ingest, cancel-in-progress: false }` (every workflow in this repo has a concurrency group; a slow backfill run must not race the next tick). Pushes use fetch-rebase-retry.

One run scans **all chains**, commits **once**, and only when there is something to commit:

1. Per chain: `eth_getLogs(Initialize)` on the PoolManager from `cursor` to `head − confirmations` (reorg buffer), in bounded chunks.
2. **Skip `hooks == address(0)`** (the majority of Initialize events).
3. For each new hook address: `eth_getCode` → codehash; decode flag mask from the address string.
   - **Empty code** (counterfactual deploy where the address has no init flags yet, or pre-observation state): do *not* write an index line; add the address to a `pendingCode` list in `cursors.json`, rechecked each run. After M runs without code, write the line with family `empty-code` (still rechecked on later sightings — it is not dedup-final).
4. Append lines to `index/<chain>.jsonl`; advance cursors; commit only if there are new lines or a chain's unscanned window exceeds a threshold.
5. For each new codehash with **no `families/` file, no open `families/<codehash>` branch/PR, and no in-flight `analyze-family` run** (run-name convention below), dispatch analysis — capped at **N families per run, oldest first**. The queue is the set of missing family files itself; no queue state exists.

Backfill and steady state are the same code path: cursors start at each PoolManager's deploy block. Sizing: at ~5k-block `getLogs` chunks and ~100 calls per chain per run, a run covers ~500k blocks/chain; Base (~2s blocks, ~25M blocks since deploy) backfills in roughly 2–3 days of normal cron cadence. Chains without a dependable public RPC simply stay dark and honest — their `scannedToBlock` stamp shows exactly how far coverage extends. Completed backfills are sanity-checked against ClickHouse (`select distinct chain_id, hooks from v4_initialize`), which should also be run **before implementation** to size the expected family count and review burden.

Per-chain isolation: a chain's cursor advances only on its success; one chain's RPC issues never block others. Multiple `rpcUrls` per chain as fallbacks.

### Governance for the mechanical lane

The repo ruleset requires 2 reviews (bot + human), which would stall mechanical commits on human attention. Since every mechanical fact is CI-re-derivable, human review adds no safety here. Note `regenerate.yml` already direct-pushes to main with the registry App token today — establish during implementation whether the ruleset currently binds Apps at all.

**Recommendation:** a *separate* fine-grained App (or deploy key) used only by `ingest.yml`, granted ruleset bypass — identity-scoped, so the analyze/review workflows that process untrusted contract source never hold bypass power. Honest caveat: validation-on-push is **detection, not prevention** — a bad mechanical commit lands on main and is republished by `regenerate.yml` before a human sees the red X. Mitigations: the ingest job itself validates before pushing; `regenerate.yml` refuses to publish when validation fails; the blast radius of index-only commits is data, not code.

**Fallback** if bypass is unacceptable: auto-merge PRs that wait for human review. This costs index freshness only — and no named consumer currently requires 30-minute freshness (the backend loop is itself a cron), so the fallback is genuinely viable, not a fig leaf.

### `analyze-family.yml` — judgment lane (dispatched per new family)

Declares `concurrency: { group: analyze-family, cancel-in-progress: false }` so analyses actually run serially, and `run-name: analyze-family <codehash>` — the run name is the idempotency key that lets ingest detect in-flight analyses (dispatch inputs are not listable via the API; run names are).

1. Pick any one instance address of the new family.
2. Query the explorer. **Unverified** → emit the stub family file (mechanical lane — auto path, no judgment content).
3. **Verified** → run the existing fetch-source → parse → Claude-classify machinery, retargeted at families (adds: classify kind, implementedPermissions). Open a reviewed PR (branch `families/<codehash>`) through the existing bot-review + human-review flow.
4. Delegating kind → also analyze its instances per-address into `hooks/` (existing analyze flow, nearly verbatim), in the same PR.

**Retry-by-absence:** a missing family file — with no open branch/PR and no in-flight run — *is* the retry queue. Analysis failure leaves no file; a later ingest run re-dispatches. After 3 failed runs for a codehash (counted by run name), write an `analysis-failed` stub and open a labeled issue for a human — the escalation channel.

### CI policy matrix

`validate.yml` today enforces "exactly one file, under `hooks/` only" per PR; that policy extends per store:

| Change shape | Validation | Allowed to co-occur |
|---|---|---|
| `index/**` commit (mechanical) | re-derive every new line (code fetch, hash, bit math); nothing outside `index/` may be touched | cursors.json |
| `families/<codehash>.json` stub | explorer verification status re-checked; no judgment fields present | — |
| `families/<codehash>.json` analysis PR | family schema; codehash exists in index; flags-vs-implementedPermissions sanity | `hooks/` files of the same family (delegating case) |
| `hooks/<chain>/<address>.json` PR | existing schema + flag-bitmask checks (unchanged) | its family file |

`regenerate.yml` triggers extend from `paths: ['hooks/**']` to include `families/**` and `index/**`.

### `regenerate.yml` — build + publish (on merge to main)

Today's artifacts keep building exactly as they do now. New artifacts are added alongside, published to **GitHub Pages** — used rather than raw git URLs because generated artifacts (joins, denormalizations) shouldn't be committed, and Pages adds real CDN cache headers. jsDelivr over the repo documented as an alternative for committed files.

| Artifact | Contents | Audience | Status |
|---|---|---|---|
| `hooklist.json` | per-address entries from `hooks/` | existing frontends | unchanged |
| `hooklist-vanilla-swap.json` | vanilla-swap subset | existing consumers | unchanged |
| `families.json` | all family entries + per-chain instance counts | frontends rendering hook varieties | new |
| `lookup/<chain>.json` | address → **denormalized** family summary (name, kind, sourceStatus, key properties, expanded flags, divergence warnings) | anyone answering "what is hook 0x… on <chain>?" in one fetch, no join | new |

(The earlier `hooklist-full.json.gz` was cut: no named consumer. DB ingesters clone the repo — it is already the full dataset.)

Every new artifact carries honesty stamps: `builtAt` plus per-chain `scannedToBlock`. Once consumers migrate to `families.json`/`lookup/`, `hooklist.json` can be deprecated on its own schedule — no forced migration.

### Existing issue-driven flow

Survives as the **enrichment path**: community submissions contribute name/description/auditUrl/repoUrl to a family (or request analysis priority), rather than being the only way into the registry.

## Backend integration (Uniswap/backend#10753)

- **"What's new":** the loop diffs `lookup/<chain>.json` (or `index/*.jsonl`) against its own evaluated set. (The evaluated set is the backend's verdict store, which it needs anyway — the registry removes the need for a separate *pending/denied hook ledger*, not for verdicts.)
- **"What's known":** family files provide kind, sourceStatus, properties, warnings.
- **Pending-state collapse:** "is this hook still being processed?" = family file absent but branch/PR/run in flight — all publicly visible GitHub state; the loop's 7-day pending TTL and separate review-ledger artifact become unnecessary.
- **Verdicts stay in the backend**, derived from properties/warnings + policy (e.g. hard-deny upgradeable). The registry stays neutral.
- Evaluation is per-family, not per-address — the loop's workload shrinks by the dedup factor.

## Error handling summary

- **Reorgs:** scan only to `head − confirmations` (per-chain setting, default 30).
- **RPC failures:** per-chain isolation; cursor advances only on success; fallback RPC URLs; bounded chunk sizes; chains with no working RPC stay dark with honest stamps.
- **Overlapping runs:** concurrency groups on both workflows; fetch-rebase-retry on push.
- **Idempotency:** append-dedupe on address (resolved lines); re-scanning harmless; empty-code addresses rechecked, not finalized.
- **Analysis failures:** retry-by-absence with in-flight detection via run names; `analysis-failed` stub + escalation issue after 3 failures.
- **Analysis volume:** capped dispatches per ingest run; serial execution via concurrency group; unverified majority handled as stubs without review load.
- **No hidden state:** git + the chain + visible GitHub runs/PRs are jointly the entire pipeline state.

## Rollout plan (additive — nothing breaks at any step)

1. Add schemas + scripts + tests; rework `validate.yml` per the CI policy matrix. Existing system untouched.
2. Run the ClickHouse sizing query; confirm expected family counts and human-review throughput for verified families.
3. One-time enrichment: fetch codehash for the existing ~421 hooks (one RPC sweep), group them, generate family files from the richest existing analysis per codehash, seed index lines. `hooks/` files stay exactly where they are.
4. Enable `ingest.yml` per chain progressively: small chains first (soneium, celo), Base last once chunking is proven. Deploy-block backfill doubles as the comprehensiveness pass; cross-check totals against ClickHouse.
5. Add new artifacts + Pages publishing to `regenerate.yml`.
6. Point the backend loop at the registry; retire its internal ledger plan.
7. (Eventually, consumer-paced) migrate frontends to `families.json`/`lookup/`; deprecate redundant per-address files for self-contained families.

## Testing

Extend the existing pytest setup (`scripts/test_*.py`):

- Scanner: log parsing, `hooks==0x0` skip, empty-code pending list, cursor math, chunking, reorg buffer, per-chain isolation (mocked RPC).
- Codehash/family grouping; flag-mask decode (property test against the 14-bit table).
- JSONL append/dedupe idempotency; correction-line latest-wins semantics.
- Family/index schema validation; stub-vs-analysis field gating on `sourceStatus`.
- Build: artifact generation, denormalized lookup join, divergence-warning computation, honesty stamps, unchanged legacy artifacts.
- Migration: fixture-based test over a sample of real `hooks/` files.
- `validate.yml`: index-line re-derivation and the CI policy matrix (public RPC endpoints suffice at PR volume).

## Out of scope (explicitly)

- Upgrade tracking for delegating instances (event watching, impl sweeps): deliberately omitted; a dated snapshot + `upgradeable: true` is decision-complete for known consumers. Can be added later, purely additively.
- Machine-readable risk-finding vocabulary: deferred until a consumer needs it; `warnings` suffices.
- Allow/deny verdicts, routing policy, notifications/comms (Slack digests, Linear escalation): backend concerns. The registry's labeled escalation issues are its only human-attention channel.
- Serving infrastructure beyond GitHub Pages/jsDelivr.
