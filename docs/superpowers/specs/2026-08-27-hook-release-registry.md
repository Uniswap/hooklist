# Hooklist v1-lite: Release Overlay

**Status:** Adopted (revision 5 — codehash reframed as review cache (post meta-review))
**Date:** 2026-08-27 (rev 4: 2026-08-31)
**Repository:** Uniswap/hooklist
**History:** descopes the full "Semantic Releases and Safe Factory Enrollment" design, now archived as a gated blueprint at `2026-08-27-hook-release-registry-full.md`. The full design's data model was right; its automation was built for volume the repo does not currently have. Revision 4 integrates the post-implementation adversarial red-team's fixes: release code fingerprints (§3.6), the executable-address matching exception (§3.5), full-tree revalidation, and flags/properties coherence checks (§3.3).

## 1. Summary

Hooklist stays exactly what it is today — one canonical hook file per `(chain, address)` under `hooks/`, the issue-driven analyze→review→approve pipeline, and a generated `hooklist.json` — and gains **one small overlay**:

```
releases/<project>/<release-id>.json    # NEW: one reviewed file per project + release version
hooks/<chain>/<address>.json            # unchanged store; files MAY point at a release
```

A **release** is the reviewed home for family-level knowledge: name, description, the five behavioral properties, warnings, source/audit links, version lifecycle. A hook file that belongs to a family points at its release — and may then be a **thin pointer** carrying only its genuinely per-instance facts. `aggregate.py` denormalizes at build time, so `hooklist.json` entries remain full and byte-shape-identical; consumers see no change.

There is **no second canonical store, no migration, no adapters, no guards, no enrollment engine, no scanners, no candidate ledger**. New instances arrive through the existing submission flow and still cost one human approval each (~2/week at current volume). What the overlay removes is duplicated analysis, reviewer effort, cross-sibling drift, and name-string version chaos.

## 2. Motivation and why the descope

The full design was pressure-tested against measured reality:

- 449 hooks; **46 duplicated-name families covering 141 files** — dozens of excess entries, not thousands.
- In **38 of 46 families the `properties` object is already byte-identical** across members; the real data-quality problem is 8 families where the analyze bot drifted (temporal-vs-other swapAccess, delegatecall-upgradeable inconsistency).
- Post-spike volume is ~2 submissions/week; the July-2026 spike (227 commits) was absorbed by the existing flow at ~one approval click per hook.
- The full design's headline ("routine factory deployments ≈ zero review") was contingent on an unresolved GitHub App ruleset-bypass question; in its sanctioned fallback mode it removed approximately zero clicks while roughly tripling the system's concept count, and its unattended failure modes were noisy (duplicate-PR cursor bug, silent enrollment halts, an unbounded dual-canonicality window).

v1-lite keeps the full design's *semantic* wins — one analysis per family, first-class versions and lifecycle, consistency enforcement, the discriminator/parameter/metadata review discipline — and drops its *logistics* wins (zero-click enrollment, autonomous discovery), which had almost no demonstrated demand. The maintenance surface grows by: one directory, one schema, one CI rule, one prompt rule. Left unattended, the system degrades exactly as today's does: a queue of pending PRs, nothing noisy, nothing silently wrong.

## 3. Design

### 3.1 The release file

`releases/<project>/<release-id>.json` — path segments lowercase (`project`: `[a-z0-9-]+`, `release-id`: `[a-z0-9.-]+`); both immutable once merged. The release reference used by hook files is `"<project>/<release-id>"`.

```json
{
  "project": "zora",
  "id": "creator-hook-2.2.1",
  "version": "2.2.1",
  "name": "Zora Creator Hook v2.2.1",
  "description": "Creator-coin launch hook; per-deployment fee configured at deploy time.",
  "source": {
    "verified": true,
    "repository": "https://...",
    "auditUrl": "",
    "codeHashes": ["sha256:..."]
  },
  "properties": {
    "dynamicFee": true,
    "upgradeable": false,
    "requiresCustomSwapData": false,
    "vanillaSwap": false,
    "swapAccess": "none"
  },
  "warnings": [],
  "factories": [
    { "chain": "base", "address": "0x..." }
  ],
  "lifecycle": { "status": "active", "supersedes": null }
}
```

Notes:

- `name` is free-form display text and is what thin instances inherit verbatim into v0 output.
- `factories` is **informational provenance only** — documentation of where instances come from. It drives no automation.
- `lifecycle.status`: `active | superseded | deprecated | flagged`; `supersedes` is a release reference or null. Deprecating a version is a one-line edit to one file.
- Releases are judgment content: created and changed only through reviewed PRs (AI-drafted, bot-reviewed, human-approved — the existing two-pass pattern).
- A release with exactly one instance is fine. Nothing requires families.

### 3.2 Hook files: full and thin forms

`hook.release` is a new **optional** field (the release reference). Three valid forms:

| Form | When | Contents |
|---|---|---|
| **Full, no pointer** | today's format; hooks with no release | unchanged — everything required as today |
| **Full + pointer** | legacy family members after backfill | all of today's fields, plus `hook.release`; legacy text preserved verbatim so v0 values never move |
| **Thin pointer** | new instances of a known release (the factory case) | only per-instance facts; everything else derived at build |

A thin file:

```json
{
  "hook": {
    "address": "0x...",
    "chain": "base",
    "chainId": 8453,
    "release": "zora/creator-hook-2.2.1",
    "deployer": "0x...",
    "description": "Fee: 35 bps; auction 24h."
  }
}
```

Field ownership for thin files — required: `address`, `chain`, `chainId`, `release`. Optional: `deployer` (submitter-claimed, as today), `description` (instance-specific configuration prose; when omitted, the release description is used). **Not permitted on thin files:** `name`, `verifiedSource`, `auditUrl`, top-level `flags`, top-level `properties` — all release-derived or address-derived. This is what keeps a factory's Nth instance a six-line file instead of a duplicated analysis.

### 3.3 Consistency rules (CI)

Enforced by `validate.py` (form logic lives in code; `schema.json` is relaxed only structurally):

1. A file with no `release` pointer must be **full** (today's exact requirements). Nothing about existing files changes.
2. A `release` pointer must resolve to an existing release file.
3. A **full + pointer** file's `properties` must equal the release's `properties` exactly. (This permanently fixes the drifted-siblings bug class. `name`/`description`/`verifiedSource`/`auditUrl` are *not* equality-checked — legacy per-address text is preserved deliberately.)
4. A **thin** file must not carry the not-permitted fields above.
5. Release files: schema-valid; file path matches `project`/`id`; lowercase path rule; `supersedes` (when set) resolves; `codeHashes` (when present) sorted and unique.
6. `verify_flags.py` skips files without a `flags` object (thin files' flags are derived from the address at build time, correct by construction).
7. **Coherence:** properties must not contradict the address's flag bits — a swap returns-delta flag forbids `vanillaSwap: true`; no swap flags at all forbids `vanillaSwap: false` or a restricted `swapAccess`. Errors for pointer-carrying and thin files and for all newly assembled output; warnings for legacy pointer-less files.
8. `hook.chain`/`hook.chainId` must agree with `chains.json`.
9. **Full-tree, both sides of the merge:** data PRs are validated as a whole tree (the PR's checkout — so deleting a release fails while members still point at it, and racing edits collide at PR time), and `regenerate.yml` re-runs full validation before publishing (so nothing inconsistent is ever aggregated). PR shape policy: a PR touching `hooks/` or `releases/` may touch nothing else; hooks-only PRs change exactly one file; release-lane PRs may batch releases + member hooks. Infra-only PRs skip data policy entirely.

### 3.4 Build-time join; the v0 freeze

`aggregate.py` resolves every hook file into a full v0 entry:

- Full files (with or without pointer): emitted verbatim, as today.
- Thin files: `name` ← release.name; `description` ← instance description or release.description; `verifiedSource` ← release.source.verified; `auditUrl` ← release.source.auditUrl (or `""`); `deployer` ← instance deployer (or `""`); `properties` ← release.properties; `flags` ← derived from the address bits.
- The `release` pointer itself is **stripped from `hooklist.json` output** — v0 stays shape-frozen with zero new fields. Release-level grouping is exposed, if ever needed, through new versioned artifacts (deferred until a consumer asks; see §4).
- Value stability: backfill adds pointers to legacy files without touching their other fields, so `hooklist.json` is byte-identical before and after backfill. Only genuinely new (thin) entries carry release-derived values.

### 3.5 Analyze-flow discipline (prompt, not machinery)

The full design's field-classification discipline survives as instructions to the existing analyze/review bots:

- **Match first:** if the submitted hook's verified source matches an existing release (same project source; optionally corroborated by exact runtime bytecode match against an already-listed sibling — a cheap `eth_getCode` assist), emit a **thin** file pointing at it. Describe only per-instance configuration in the instance description.
- **Classify before grouping:** a config difference that changes any categorical conclusion (control flow, routing/quoting support, required hookData, settlement, access control, upgrade path, selected implementation/oracle, any warning) means a **different release** — propose a new one rather than pointing at the old. Values that vary freely without changing conclusions (fee within a sane range, timings, recipients) belong in the instance description. **Overriding exception, stated in the prompts verbatim:** an address parameter that selects executed code — a delegatecall/implementation target, oracle, library, module, or router — ALWAYS breaks a match, even when the verified source is byte-identical. Identical source delegating to different targets is different behavior, and source identity cannot see it; the code fingerprint (§3.6) can, because immutables are baked into runtime bytecode.
- **New version detection:** same project, different source → draft a new release file with `lifecycle.supersedes` set, analyzed as a diff against the predecessor where possible.
- The independent review pass checks the pointer choice the same way it checks properties today.

### 3.6 Code fingerprints (`source.codeHashes`) — a review cache, not a matcher

Every release carries `source.codeHashes`: a **machine-maintained cache of runtime-code fingerprints a human has already reviewed as members of this release** — `sha256:<hex>` of the deployed runtime bytecode of each such member (sha256 deliberately, not keccak: the hash is internal to hooklist and never needs to match on-chain values, so no EVM dependency is taken). It is populated and kept current by a post-merge job (`scripts/update_codehash_index.py`), never hand-authored and never trusted from a PR's own copy — the review-time verdict always reads the base branch's cache, never the PR's version, so a PR gains nothing by editing `source.codeHashes` itself.

Families whose instances embed immutables legitimately hold several entries; the list is sorted and unique (CI-enforced — the fixed `maxItems` cap was removed, since an active factory family can legitimately outgrow any fixed number).

The cache exists to make ONE question mechanical: "have we already reviewed bytes exactly like these as a member of this release?" It answers nothing about whether the release's own analysis is still correct, and a hit against an `upgradeable` release answers nothing about the instance's *current* behavior (a storage-dependent implementation can change after review). It is never a substitute for reviewing novel bytes — it only ever narrows the population that needs full scrutiny.

When a PR adds a hook file carrying `hook.release`, the review workflow's deterministic step (which already fetches source) also fetches the address's runtime code (`scripts/fetch_codehash.py`: explorer proxy API first, public-RPC fallback) and emits a verdict the review bot must act on:

- **match** — the hash is in the release's cache, and the release is not `upgradeable`: artifact identity is settled (mechanical). This does not itself validate the release's analysis.
- **match-upgradeable** — the hash is in the cache, but the release IS `upgradeable`: byte-identity says nothing about current behavior for a storage-dependent implementation. Never collapsed into `match` — full scrutiny of the live implementation/delegate configuration is required regardless of the cache hit.
- **no-cached-review** — nothing negative: there is a cache on the base branch but this hash isn't in it (yet). Full per-address scrutiny applies, aided by a best-effort evidence bundle (this instance's code length, the nearest existing member's code length, and a count of contiguous differing byte runs when the two lengths are equal) that helps a reviewer judge whether this reads as an immutables-configuration variant of the same template or as genuinely different code. A variant whose source shows a differing delegatecall/oracle/implementation target is always REQUEST_CHANGES, evidence or not.
- **no-list / fetch-failed** — no mechanical check possible (the cache doesn't exist yet, or explorer/RPC failure — never a hard job failure, this repo's explorers are known-flaky): full per-address scrutiny applies, and the failure is stated, never treated as evidence.

Once a PR merges, the cache is what actually grows: the post-merge job walks every pointer-carrying hook file and appends any live hash not yet present in its release's cache — this is the mechanism by which "a human reviewed this PR" becomes "these bytes are now in the cache." This is deliberately interim: it appends real fingerprints one merge at a time rather than deriving a bytecode-shape matcher that could recognize deployment-time variance (masked immutables) mechanically. The archived full design's masked-bytecode matching remains the documented next step if factory submission volume ever demands it; nothing here forecloses building it.

### 3.7 What "supporting a factory" means in lite

Register nothing. When a factory's first instance is submitted, its release gets created (one reviewed PR). Every subsequent instance is a thin-file submission: the bot matches, the human approves one small diff. For a backlog, a maintainer may batch-submit thin files for known instances in one PR — the release carries the analysis, so a 20-instance backfill PR is 20 six-line files, reviewable at a glance.

## 4. Deliberately absent, and the gated future phase

Absent from v1-lite: instance auto-discovery, enrollment automation, factory adapters, path/output guards, candidate ledgers, scan cursors, parameter schemas with published per-instance values, a `data/v1` store, migration sync, new published artifacts. Per-instance approval clicks remain (~2/week).

The full design (`2026-08-27-hook-release-registry-full.md`) remains the blueprint for the day all three gates hold:

1. Org admins confirm a dedicated GitHub App can bypass the 2-review ruleset (else automation saves no clicks);
2. A named consumer commits to reading enrollment output at sub-day freshness;
3. Sustained submission volume returns to July-2026 levels.

v1-lite is forward-compatible with it: releases are the same conceptual objects; the enrollment machine would bolt on by adding bindings to release files and an instances ledger, without disturbing the overlay. New versioned lookup artifacts (`v1/…`) are similarly deferred until a consumer names a need — the release files themselves are already consumable JSON in the repo.

## 5. Migration

1. **Dedupe the case-collision pairs under `hooks/`** (one reviewed PR; overdue independently of everything else). The tree held two conflicting records for dozens of addresses, resolved by the dedupe commit.
2. Add the release schema, `validate.py` rules, `aggregate.py` join, and `verify_flags.py` skip. No data changes; everything existing still validates.
3. Update the analyze/review prompts and `assemble_hook.py` (emit thin files on release match).
4. **Backfill**: draft release files for the known families (seeded from the richest existing analysis per family, drifted siblings reconciled in review), add pointers to member hook files without touching their other fields. Batched reviewed PRs; `hooklist.json` provably unchanged at every step.

## 6. Invariants

1. `hooks/<chain>/<address>.json` is and remains the single canonical store; `(chainId, hookAddress)` remains the consumer lookup.
2. `hooklist.json` is shape-frozen and, through backfill, value-stable; the release pointer never appears in it.
3. A release is one reviewed record whose analysis is decision-complete for every instance that points at it; a config difference that changes a categorical conclusion is a different release.
4. Thin instances carry only per-instance facts; full instances that point at a release must agree with its properties exactly.
5. Releases, like all judgment content, enter only through reviewed PRs; release and project identifiers are immutable.
6. No automation beyond the existing pipeline: matching guidance lives in prompts, consistency lives in CI, and everything a maintainer must newly understand is one directory, one schema, a handful of CI rules, and one prompt rule.
7. A release's `codeHashes` field is a machine-maintained review cache, not a matcher for novel bytes: a cache hit narrows scrutiny (and still demands full scrutiny again when the release is `upgradeable`), a cache miss routes to full review backed by an evidence bundle, and the cache is grown only by the post-merge index job — never by a PR's own edits. An address parameter that selects executed code always breaks a match.
