# Hooklist v1: Semantic Releases and Safe Factory Enrollment

**Status:** ARCHIVED BLUEPRINT — gated future phase, not scheduled for implementation.
**Gates (all must hold before building):** (1) the §7.4 App-bypass question is answered YES by org admins; (2) a named consumer commits to reading enrollment output at sub-day freshness; (3) sustained submission volume returns to July-2026 levels. Known fixes required if built: scan cursors must not advance inside unmerged PRs (PR-spam bug); path-guard halts and candidate-ledger growth need an alerting channel; the enrollment cron should be daily, not 30 min.
**Superseded by:** `2026-08-27-hook-release-registry.md` (v1-lite), adopted after an adversarial maintainability review.
**Date:** 2026-08-27
**Repository:** Uniswap/hooklist
**History:** supersedes the initial "Hook Release Registry" proposal of the same date; revised through external architecture review, then a fresh-eyes implementability review (revision 2 resolutions are integrated below, not annotated).

## 1. Summary

Hooklist is a public, neutral source of truth for Uniswap v4 hooks. Its primary lookup is:

> (chainId, hookAddress) → what is this hook, and how can I support it?

V1 keeps Git and static JSON, while adding three concepts:

**Project → Release → Instance**

- A **Project** is the builder or maintainer, such as Clanker or Zora.
- A **Release** is Hooklist's reusable unit of reviewed knowledge.
- An **Instance** is one deployed hook address with its exact configuration and provenance.

The central definition is:

> **A Hooklist release is one reviewed hook behavior model for which a single decision-complete analysis applies to every member after substituting the member's published parameter values.**

This avoids both unsafe code-based grouping and one release per deployment. Every deployment input is classified as one of:

- **Discriminator** — selects a release; a different value means a different release.
- **Parameter** — may vary within a reviewed domain; its exact value is published on the instance.
- **Metadata** — may vary because it cannot affect Hooklist's behavioral conclusions.

Routine factory deployments are enrolled by reviewed Python adapters. Automatic enrollment requires complete field classification, an exact release match, in-domain parameters, a valid factory/path guard, and a mandatory deployed-output guard. Bytecode is therefore used as a postcondition on what the factory produced, not as proof that two contracts behave the same.

AI drafts analysis, field policies, adapters, tests, and release diffs. Humans approve those durable decisions once. Known deployments then enroll mechanically without per-instance AI or human review.

### 1.1 Relationship to the automated-ingestion design

The approved ingestion design (`docs/superpowers/specs/2026-07-24-hook-ingestion-design.md`, committed alongside this spec) predates v1 and is **partially superseded**:

- **Superseded:** its storage vocabulary — `families/<codehash>.json`, family identity by raw codehash, `index/<chain>.jsonl` as the family carrier, and the Pages-published `families.json` / `lookup/<chain>.json` artifacts. Codehash-keyed families fragment on Solidity immutables (verified empirically on `GovernedLBPStrategy`); v1 releases with parameterized enrollment replace them. Unverified/unknown code becomes an *unresolved instance stub* (§4.3), not a family stub.
- **Survives, retargeted:** its discovery machinery — the PoolManager `Initialize` scanner, per-chain cursors and isolation, the minimal JSON-RPC client, chunked `eth_getLogs`, reorg buffers, and its mechanical-lane governance analysis. When built, the scanner emits unresolved instance stubs and feeds the same enrollment path as factory discovery (§8).

## 2. Goals

V1 should:

- Preserve `(chainId, hookAddress)` as the consumer lookup.
- Add first-class project, release, deployment, lifecycle, and configuration data.
- Make routine factory deployments approximately zero-review work.
- Handle continuous launch parameters without hiding meaningful differences.
- Preserve Hooklist's distinction between mechanically re-derived facts and reviewed judgment.
- Keep Git and versioned static JSON as the canonical store and public interface.
- Freeze the existing v0 output **shape** (see §10 for the precise freeze semantics).
- Avoid a universal bytecode-equivalence, factory-predicate, or proxy taxonomy.

## 3. Non-goals

V1 does not attempt to:

- Prove behavioral equivalence from bytecode.
- Model every mutable runtime state.
- Automatically understand arbitrary proxy or delegation systems.
- Fully solve autonomous discovery before the data model ships.
- Require a hosted API, database, API key, lens contract, or per-lookup RPC call.
- Decide whether a particular configuration is economically advisable for a pool.

Hooklist publishes facts and conservative guidance. Consumers decide policy.

## 4. Core model

### 4.1 Project

A project identifies the team or protocol that built and maintains a hook design. Project identity is curated — it is not inferred solely from who deployed a contract.

A project record contains an immutable ID, display information, links, verified publisher information, and **factory registrations** (the store for factory identity — bindings and instances reference factories by `factoryId` defined here):

```json
{
  "schemaVersion": "1.0",
  "id": "clanker",
  "name": "Clanker",
  "links": { "website": "https://...", "repository": "https://..." },
  "factories": [
    {
      "id": "clanker-base-main",
      "chainId": 8453,
      "address": "0x...",
      "discovery": true
    }
  ]
}
```

`discovery: true` marks the factory as a watched discovery source (§6.1). Factory `id`s are globally unique and immutable.

### 4.2 Release

A release is Hooklist's unit of reusable semantic knowledge. It contains:

- Project and upstream version metadata.
- Source, audit, and lifecycle information.
- Conservative integration properties, a description, and warnings.
- A schema for values published on each instance.
- One or more reviewed enrollment bindings.

A Hooklist release is not necessarily the same as a project's marketing version. One upstream version may produce several Hooklist releases when it has materially different modes, dependencies, or integration behavior.

A release may span chains only when the same analysis and parameter schema are accurate on every chain. Chain-specific factories, source artifacts, and output checks live in chain-specific bindings. A chain-specific semantic difference creates a separate release.

A release may be a singleton. Reuse is an optimization, not a correctness requirement.

**Release invariant.** For every instance assigned to a release:

> release analysis + exact instance parameter values

must be accurate and decision-complete. A consumer should not need to inspect raw constructor arguments or source code to discover an unmodeled semantic difference.

Instances never carry semantic overrides. If an instance requires a different property, warning, integration path, or qualitative description, it belongs to a different release.

### 4.3 Instance

An instance is one deployed hook: `(chainId, hookAddress)`. A **resolved** instance contains:

- A release reference (`releaseRef`, the composite `<projectId>/<releaseId>`) and binding reference.
- Exact parameter values and approved metadata.
- Deployment transaction and block.
- Factory, immediate deployer, and deployment initiator.
- Mechanical enrollment evidence, including observed runtime codehash and the block at which configuration values were read.
- Optionally, a `v0` legacy block carrying per-address judgment fields inherited from the pre-v1 registry (§10).

Instances do **not** store the 14 hook flags: flags are a pure function of the address and are expanded into published artifacts at build time (the same rule the ingestion design adopted for index lines). Enrollment still checks the address bits against the binding's `expectedFlags`.

An **unresolved instance stub** is the same file with no release attached — recorded existence plus mechanical facts only: address, chainId, discovery provenance (how it was observed), and first-seen block. Stubs have no analysis, no parameters, and are **excluded from the v0 artifact** (which requires judgment fields a stub cannot honestly carry); in `v1/chains/<chainId>.json` they appear with `"resolved": false` and address-derived flags. A stub is resolved later by enrollment or by per-address analysis into a singleton release.

### 4.4 Builder, factory, deployer, and initiator

V1 keeps four identities separate:

- **Project:** who built or maintains the hook design.
- **Factory:** a registered deployment contract or system (§4.1).
- **Deployer:** the immediate EVM creator of the hook address.
- **Initiator:** the account or contract that requested the deployment, when determinable.

Deployment through an official factory is provenance, not endorsement. A permissionless project factory may produce unusual user-selected configurations.

Note: the legacy v0 `deployer` field is submitter-claimed and usually an EOA; v1's `deployment.deployer` is the mechanically observed EVM creator (usually the factory). They are distinct fields with distinct semantics; the legacy value, where present, lives in the instance's `v0` block.

## 5. Configuration model

Every behavior-relevant deployment input must be assigned exactly one role. Unknown or unclassified inputs disable automatic enrollment.

### 5.1 Discriminators

A discriminator selects the release. A different value does not enroll into that release.

Use a discriminator when the value can change a categorical Hooklist conclusion, including:

- Hook control flow or callback return behavior.
- Router, quoter, or exact-input/exact-output support.
- Required hookData or caller interfaces.
- Settlement mechanism or token flow.
- Access-control mechanism.
- Upgrade or delegation path.
- Selected executable implementation, library, or oracle.
- Any release-level warning or integration recommendation.

Typical examples are curve mode, auction type, settlement mode, implementation address, and enabled feature set.

**Address-valued discriminators inherit mutability.** A discriminator that references an external contract — an oracle, library, or implementation address — pins *which* address is used, not *what that address does*. The binding review must establish that the referenced contract is immutable, or the release analysis must conservatively describe its mutability envelope, the same treatment §6.5 gives the hook itself. An external dependency whose behavior can change without a new deployment cannot silently sit behind a discriminator.

### 5.2 Parameters

A parameter may vary within one release only when:

- Its value is deterministically extractable during enrollment.
- **Its value is provably fixed after deployment** — an immutable variable, or storage with no reachable write path. A value that can change after deployment is not a parameter: either the release describes its mutability envelope qualitatively ("owner-adjustable fee, capped in code at X bps") or the deployment fails to automation.
- Its allowed domain is explicit and reviewed.
- Its exact value is published on every instance.
- The release explains what the parameter changes.
- The release analysis covers the full domain, including boundary and adversarial values and interactions between parameters.
- The same categorical properties, warnings, and integration path remain valid across the domain.
- It does not select arbitrary executable behavior.

Out-of-domain values fail enrollment.

Typical parameters may include fee rate, auction timing, curve coefficients, or price bounds. A parameterized release does not claim that 1 bp and 100 bp are economically equivalent. It claims that one release record can describe both accurately when the concrete feeBps value is included.

V1 does not add a general conditional-property engine. If a parameter changes vanillaSwap, swapAccess, exact-output support, required data, or another categorical conclusion, it must become a discriminator or its domain must be split across releases.

### 5.3 Metadata

Metadata may vary only when it cannot affect any Hooklist property, warning, capability, or integration decision.

A fee recipient may qualify when it changes only where an already determined fee goes. A human-readable deployment label is another example.

An authority address is not automatically metadata. It may be a parameter only when the release already publishes a conservative description of the authority's powers and the exact address is surfaced on the instance.

### 5.4 Exhaustive, fail-closed classification

The adapter and binding must account for every relevant input derived from:

- Factory events.
- Transaction calldata.
- Constructor and initializer arguments.
- Factory state used during deployment.
- Selected external contracts.
- Other values that affect the deployed hook.

CI verifies that every field returned by the adapter has a declared role and that no required field is absent. Unknown, omitted, or unresolved fields become review candidates.

The irreducible human-review obligation is explicit:

> Reviewers approve that the adapter found every semantic input, classified it correctly, and chose parameter domains broad enough for useful automation but narrow enough for one release analysis to remain valid.

AI should assemble and challenge this inventory, but it cannot approve the completeness claim.

## 6. Factory enrollment

### 6.1 Discovery registration

A project may register a factory (§4.1) as a high-signal discovery source. This means: *watch this deployment path and attribute its outputs to this project as candidates.* Discovery registration alone never confers release membership.

### 6.2 Enrollment binding

A release contains one or more chain-specific enrollment bindings. Binding `id`s are unique within their release and referenced from instances alongside `releaseRef`. Each binding includes:

- Chain and factory identity (`factoryId`, resolved through the project's factory registry).
- Pinned adapter reference: `adapter` (module id) + `adapterVersion`, resolving to `factory_adapters/<adapter>/v<adapterVersion>.py` (§6.3).
- **Factory path guard:** a pinned factory runtime codehash or implementation reference, checked on every enrollment run, plus an optional epoch (block range). An open-ended epoch alone guards nothing; the code pin is what detects a factory upgrade. When the code-pin check fails, automatic enrollment halts for the binding immediately; a human then closes the epoch (`toBlock`) and reviews the new factory code in a judgment-lane PR — usually producing a new binding or release.
- Exact discriminator values, including expected address flag bits.
- Allowed parameter domains.
- Accepted metadata fields.
- Mandatory deployed-output guard (§6.4).

An instance auto-enrolls only when:

1. The factory path guard is valid.
2. The adapter fully decodes the deployment.
3. Every decoded field is classified.
4. Discriminators match the release exactly.
5. Parameters satisfy their reviewed domains.
6. Address-derived flags match the binding's expected bits.
7. The deployed-output guard passes.
8. No unresolved mutable dependency requires review.

Any failure creates a **review candidate**. Candidates are recorded in an append-only ledger, `data/v1/candidates/<chainId>.jsonl`, one line per observed deployment, and are **deduplicated by configuration key**: the SHA-256 of the canonical JSON of `{factoryId, discriminators, out-of-domain and unknown fields}`. Review tooling groups candidate lines by key, so a popular unapproved configuration is one review item with a member count, not one per deployment.

### 6.3 Python adapters

Adapters are small, versioned Python modules (the existing repository tooling is Python; RPC uses a minimal stdlib JSON-RPC client — the same design the ingestion plan specifies — with no new heavyweight dependencies).

Layout and versioning: `factory_adapters/<adapter>/v<N>.py`. Every version is a separate committed file; old versions remain in the working tree, not merely in git history, so CI can re-run the exact pinned version referenced by any binding or instance.

**Adapter contract.** Each adapter module exposes:

```python
def decode(ctx: DeploymentContext) -> AdapterResult: ...
def verify_output(ctx: DeploymentContext, result: AdapterResult) -> GuardResult: ...
```

- `DeploymentContext` provides the deployment log/tx (hash, receipt, calldata), an injected RPC client, and the binding under evaluation. Adapters must be deterministic given the context; wall-clock and environment access are prohibited.
- `AdapterResult` carries: hook address; deployment provenance (tx, block, deployer, initiator); the **complete decoded field map**, each field tagged `discriminator | parameter | metadata`; and any fields the adapter observed but cannot classify (which fail enrollment closed).
- `GuardResult` carries pass/fail plus the observed runtime codehash and the verification block.
- Failure semantics: any exception or partial decode aborts enrollment for that deployment and writes a review candidate. There is no partial enrollment.

The exact dataclass shapes are defined by the implementation plan and frozen by tests; the spec-level contract is the two entry points and fail-closed semantics.

### 6.4 Mandatory deployed-output guard

Trusting only the factory path leaves the actual deployed contract unchecked. Every auto-enrolled instance must therefore pass a deterministic output guard.

The guard is specific to the adapter and may use:

- Exact runtime codehash for a fixed artifact.
- Reconstruction from decoded deployment inputs followed by exact runtime comparison.
- A narrowly reviewed runtime template check.
- A fixed proxy shell plus a pinned immutable implementation.
- Another deterministic assertion appropriate to that deployment path.

**Every discriminator and parameter value must be verified against the deployed contract itself**, not only decoded from what the factory claimed: values carried in runtime bytecode are checked by reconstruction or template comparison; values held in storage are checked by deterministic state reads (`eth_getStorageAt` / `eth_call`) at enrollment. Combined with §5.2's immutability requirement, the at-enrollment read is a permanent fact, not a snapshot.

**Guard inputs are pinned in-repo.** The expected runtime template (or its hash plus immutable patch map) and the storage-read recipe are committed as part of the binding review, so guards run from the repository plus an RPC endpoint — independent of block-explorer availability or honesty. The pinned template's provenance (which compilation, which reviewed source) is recorded in the binding's `sourceArtifact`; explorer verification is consulted once during binding review, never at enrollment or re-verification time.

**Re-verification semantics (stated honestly).** Enrollment records at-enrollment evidence (adapter version, observed runtime codehash, verification block). What CI can re-derive later from a full node splits in two:

- **Always re-derivable at latest:** runtime code checks (`eth_getCode` is available for current state), storage/parameter re-reads *under the reviewed §5.2 immutability claims*, and address-flag bits.
- **Archive-dependent:** replaying a historical enrollment exactly — factory code *at the deployment block*, factory state read *at the deployment block*, and old log ranges on pruning endpoints. Adapters should therefore prefer inputs retrievable by transaction hash (receipts, logs, calldata — served by full nodes indefinitely) over historical state reads; an adapter that requires historical state must declare it, and full replay for that factory is best-effort against archive endpoints, not a CI invariant.

The guard cannot assign a release by itself. It only confirms that the reviewed deployment path produced an expected artifact after the discriminator and parameter checks have already matched. Consumers do not need to call `eth_getCode`; the enrollment pipeline performs the check once per new instance. If a reliable output guard cannot be written, the factory remains discovery-only for that release.

### 6.5 Mutable delegation

V1 does not create an enum for every proxy mechanism. A delegating pattern receives automatic enrollment only when its complete behavior path and invalidation condition are deterministically understood by its adapter and conservatively described by the release. Otherwise the hook is marked upgradeable or delegating, automatic enrollment is disabled, and the deployment receives reviewed treatment — usually as a singleton release.

## 7. Automation and review

### 7.1 Mechanical lane

GitHub Actions may automatically:

- Discover deployments from approved factory or PoolManager scanners.
- Derive address flags.
- Run a pinned adapter.
- Validate exhaustive field classification.
- Check discriminators and parameter domains.
- Run factory-path and deployed-output guards.
- Enroll an instance into an existing release.
- Record provenance, values, and enrollment evidence.
- Append review candidates to the candidate ledger.
- Regenerate and validate static artifacts.

No AI is needed for a routine matching deployment.

### 7.2 AI lane

AI may:

- Analyze verified source and deployment code paths.
- Inventory constructor, initializer, event, storage, delegation, and external-call inputs.
- Propose field roles and parameter domains.
- Reason about boundary and adversarial parameter values (fork simulation is aspirational for v1, not required).
- Draft adapters and deterministic tests.
- Compare a candidate with predecessor releases.
- Draft properties, warnings, descriptions, and lifecycle metadata.
- Perform an independent review of a release PR.

AI-generated judgment never auto-merges.

### 7.3 Human approval

Human review is concentrated on four durable decisions:

1. A new or changed release analysis.
2. Completeness and classification of deployment inputs.
3. Parameter domains and their behavioral envelope.
4. Factory identity, adapter, path guard, and output guard.

Routine instances matching these approved rules require no human review.

### 7.4 Mechanical-lane governance

A dedicated GitHub App may bypass human review only for changes to:

```
data/v1/instances/
data/v1/candidates/
generated v0/v1 artifacts (repo-root hooklist.json, hooklist-vanilla-swap.json, v1/)
scanner cursors
```

Enforcement has two layers, both required:

1. **Pre-push, in the trusted job:** the mechanical workflow runs from default-branch code, validates its own diff against the allowed-path list and re-derives every fact it is about to commit, and refuses to push otherwise.
2. **Post-push verifier:** a push-triggered workflow on `main` re-validates any commit authored by the mechanical App and fails loudly (issue + red X) on violation. As in the ingestion design, this is detection, not prevention — the blast radius of allowed paths is data, not code, and `regenerate.yml` refuses to publish when validation fails.

CI rejects changes to projects, releases, adapters, schemas, prompts, workflows, validators, or any undeclared path. Semantic authority therefore always enters through the reviewed judgment lane; the mechanical lane may only execute previously approved rules.

**Open operational question (carried from the ingestion design, unresolved):** whether the repo ruleset's 2-review requirement binds GitHub Apps at all, and whether a ruleset bypass actor for the dedicated App is grantable in this org — this repo has a history of protection-layer drift breaking automation. **Fallback if bypass is unacceptable:** the mechanical lane opens auto-merge PRs that wait for review; this costs enrollment freshness only, and no current consumer requires sub-hour freshness.

## 8. Workflow

```
new deployment observed or submitted
                │
                ▼
known factory adapter?
       ┌────────┴────────┐
       │                 │
      no                yes
       │                 │
AI drafts normal      decode all inputs
review/singleton PR          │
(or unresolved stub)         ▼
                   complete classification?
                        │
                 factory/path guard valid?
                        │
                 discriminator match?
                        │
                 parameters in domain?
                        │
                  output guard passes?
                  ┌─────┴─────┐
                  │           │
                 no          yes
                  │           │
        candidate ledger      mechanical enrollment
        (deduped by key)
```

Intake paths, in rollout order: (1) the existing issue-driven submission flow; (2) manually dispatched ingestion of a specific deployment (`workflow_dispatch` with chain + tx hash or address); (3) a scheduled factory scanner over registered factories' deploy events — cheap, high-signal `eth_getLogs` on a handful of addresses; (4) eventually the PoolManager `Initialize` scanner from the ingestion design, emitting unresolved stubs. All four converge on the flow above.

## 9. Canonical data layout

```
data/v1/projects/<project-id>.json
data/v1/releases/<project-id>/<release-id>.json
data/v1/instances/<chainId>/<address>.json
data/v1/candidates/<chainId>.jsonl
factory_adapters/<adapter>/v<N>.py
schemas/v1/*.schema.json
```

**Address casing:** all addresses in `data/v1/**` — file names and JSON values — are lowercase. CI rejects any uppercase hex in `data/v1` paths or address-typed fields. (This retires the case-collision failure mode that produced 37 duplicate pairs under `hooks/`.)

Project and release IDs are immutable once published. Display names and upstream version labels may be corrected, but an ID is never renamed or reused for a different semantic release. A material semantic change creates a new release linked through lifecycle metadata. Cross-file references use `releaseRef` = `<projectId>/<releaseId>`; binding references use the binding `id`, scoped to its release.

### 9.1 Release sketch

```json
{
  "schemaVersion": "1.0",
  "id": "stable-hook-v1",
  "projectId": "clanker",
  "name": "Clanker Stable Hook",
  "upstreamVersion": "1.0.0",
  "source": {
    "status": "verified",
    "repository": "https://...",
    "commit": "...",
    "auditUrl": "https://..."
  },
  "analysis": {
    "description": "Static-fee launch hook; fee configured per deployment within a reviewed range.",
    "properties": {
      "dynamicFee": true,
      "upgradeable": false,
      "requiresCustomSwapData": false,
      "vanillaSwap": false,
      "swapAccess": "none"
    },
    "warnings": [],
    "parameterDescriptions": {
      "feeBps": "Per-deployment fee; changes trade cost but not the integration path."
    }
  },
  "bindings": [
    {
      "id": "clanker-base-main-v1",
      "chainId": 8453,
      "factoryId": "clanker-base-main",
      "adapter": "clanker_base_main",
      "adapterVersion": 1,
      "pathGuard": {
        "factoryCodeHash": "0x...",
        "epoch": { "fromBlock": 12345678, "toBlock": null }
      },
      "sourceArtifact": {
        "provenance": "compiled from source.commit during binding review",
        "runtimeTemplateHash": "0x...",
        "immutablePatchMap": [{ "start": 340, "length": 32, "input": "oracleImplementation" }]
      },
      "fieldPolicy": {
        "expectedFlags": "0x00c0",
        "discriminators": {
          "hookType": "stable",
          "curveMode": "stable",
          "oracleImplementation": "0x..."
        },
        "parameters": {
          "feeBps": { "type": "uint24", "min": 1, "max": 100 },
          "auctionDuration": { "type": "uint40", "min": 3600, "max": 604800 }
        },
        "metadata": {
          "feeRecipient": { "type": "address" }
        }
      },
      "outputGuard": {
        "adapterMethod": "verify_output",
        "description": "Reconstructs the expected runtime from decoded inputs and compares it with deployed code; storage-configured values verified by state reads."
      }
    }
  ],
  "lifecycle": {
    "status": "active",
    "supersedes": null
  }
}
```

`source.status` is `verified | unverified | analysis-failed` and is what the v0 `verifiedSource` boolean is generated from.

### 9.2 Resolved instance sketch

```json
{
  "schemaVersion": "1.0",
  "chainId": 8453,
  "address": "0x...",
  "resolved": true,
  "releaseRef": "clanker/stable-hook-v1",
  "bindingId": "clanker-base-main-v1",
  "parameters": {
    "feeBps": 35,
    "auctionDuration": 86400
  },
  "metadata": {
    "feeRecipient": "0x..."
  },
  "deployment": {
    "transactionHash": "0x...",
    "blockNumber": 12345678,
    "deployer": "0xfactory...",
    "factoryId": "clanker-base-main",
    "initiator": "0xuser..."
  },
  "enrollmentEvidence": {
    "adapter": "clanker_base_main",
    "adapterVersion": 1,
    "runtimeCodeHash": "0x...",
    "verifiedAtBlock": 12345690
  },
  "v0": {
    "name": "Clanker Stable Fee Hook (Base)",
    "description": "…legacy per-address description…",
    "deployer": "0xsubmitterclaimed...",
    "auditUrl": ""
  }
}
```

The optional `v0` block preserves legacy per-address judgment fields (name, description, submitter-claimed deployer, auditUrl) for v0 artifact regeneration (§10). It is populated by migration, never by new enrollment. Note there is no `flags` object — flags are derived from the address at build time.

### 9.3 Unresolved instance stub sketch

```json
{
  "schemaVersion": "1.0",
  "chainId": 8453,
  "address": "0x...",
  "resolved": false,
  "discovery": {
    "source": "factory-scan | poolmanager-scan | manual",
    "factoryId": "clanker-base-main",
    "transactionHash": "0x...",
    "firstSeenBlock": 12345678
  }
}
```

Stubs are excluded from the v0 artifact and appear in `v1/chains/<chainId>.json` with `"resolved": false` and address-derived flags only.

## 10. Published artifacts and versioning

**v0 freeze semantics (precise).** The existing root `hooklist.json` remains **shape-frozen**: its schema — entry structure, field names, types, required fields — never changes, and it continues to be generated. Its *values* are preserved as follows:

- At migration time, per-address judgment fields are carried into instance `v0` blocks, so the regenerated artifact is value-identical to the pre-migration one (modulo the pre-migration dedup in §11 step 0).
- After migration, v0 values change only through reviewed judgment-lane PRs — e.g., a consolidation PR that deliberately replaces preserved per-address text with release-level text, with the value diff visible in the PR.
- v0 generation rules: `name`/`description`/`deployer`/`auditUrl` come from the instance's `v0` block when present, else from the release (`name`, `analysis.description`) and mechanical provenance; `verifiedSource` = (`release.source.status == "verified"`); `flags` expanded from the address; `properties` from the release. Unresolved stubs are excluded.

New consumers use explicitly versioned, **committed, generated** files at the repo root (same serving mechanism as today's `hooklist.json` — raw git / jsDelivr; the ingestion design's GitHub Pages publishing is superseded for these artifacts):

```
v1/manifest.json
v1/chains/<chainId>.json
v1/projects.json
v1/releases.json
```

`v1/chains/<chainId>.json` is an address-keyed, denormalized lookup containing the release analysis, exact instance parameters, expanded flags, and deployment provenance. Ordinary consumers need no joins and no per-hook RPC calls. (Note the deliberate distinction: `data/v1/` is the canonical hand-and-machine-written store; root `v1/` is generated output.)

The manifest contains schema version, generation timestamp, source Git commit, available chain files, and optional content hashes.

Within v1, optional fields may be added, but existing meanings and types do not change. Breaking changes publish under `v2/`.

A lens contract is deferred: it adds onchain update authority and per-lookup RPC dependence without removing the semantic-review problem. An optional cache-miss resolver may later run the same approved rules, while static JSON remains canonical.

## 11. Migration

0. **Dedupe the 37 case-collision pairs under `hooks/`** (one reviewed PR: pick the canonical analysis per address, delete the duplicate file, regenerate v0). The v0 contract cannot be frozen while the tree contains two conflicting records for one address.
1. Freeze and test the v0 output contract (canonicalized-JSON equality, since today's duplicate-pair ordering is glob-dependent; after step 0, byte-stable ordering is achievable).
2. Add v1 schemas, validators, and the CI policy matrix for the new stores.
3. Create singleton V1 releases + instances for existing analyzed hooks via a deterministic migration script (per-address judgment fields → instance `v0` blocks; lowercase all addresses). During the transition window, **`hooks/` remains canonical**: the migration script re-runs on merge so `data/v1/` tracks it, and CI proves v0-regenerated-from-v1 equals v0-generated-from-hooks.
4. Add `rpcUrls[]` to `chains.json` for chains with bindings (public endpoints, committed, with fallbacks).
5. Onboard high-volume factories one at a time: scout the factory (events, volume, config surface), then review its adapter, exhaustive field policy, parameter domains, path guard, and output guard.
6. Consolidate singleton releases only when one decision-complete release record genuinely covers them (reviewed PRs; visible v0 value diffs).
7. **Cut over canonicality:** retarget the issue-driven analyze flow to emit v1 singleton releases + instances directly; `hooks/` becomes frozen legacy input (retained, no longer written); v0 artifacts generate from `data/v1/` only.
8. Add scheduled factory discovery, then PoolManager discovery, incrementally (§8 intake paths 3–4).

## 12. Tradeoffs

**Parameterization is a bounded escape hatch.** It prevents continuous-parameter factories from degenerating into one release per instance. The cost is a stronger one-time review: the domain and its complete behavioral envelope must be understood. Difficult fields remain discriminators.

**Output guards add a narrow bytecode dependency.** This is intentional. Factory provenance alone does not verify what was deployed. The output guard restores public re-verifiability without treating bytecode as the semantic identity.

**Factory adapters require maintenance.** The cost is one small adapter per important deployment path. Low-volume or unusual hooks can continue using singleton releases and the existing manual path.

**Static data has enrollment latency.** Known addresses require no consumer RPC. New instances appear after the scanner and publication cadence. Optional cache-miss resolution can be added later without changing the model.

**Historical replay is best-effort.** At-enrollment evidence plus latest-state re-checks are the CI invariant; exact historical replay can require archive endpoints (§6.4) and is not guaranteed.

**Some hooks remain unresolved or singleton.** Mutable delegation, arbitrary executable dependencies, incomplete source, or incomplete configuration evidence may prevent safe automation. V1 fails closed rather than forcing every deployment into a reusable group.

## 13. Decision

Adopt **Project → Release → Instance** with these invariants:

1. A release is one decision-complete behavior model, optionally parameterized over reviewed domains.
2. Every exact parameter value is published per instance, and parameters are provably fixed after deployment.
3. A field that changes a categorical property, warning, or integration path is a discriminator; address-valued discriminators require their referenced contracts to be immutable or conservatively described.
4. Instances never carry semantic overrides (the migration-only `v0` block preserves legacy text; it is not analysis).
5. Adapter outputs are exhaustively classified; unknown fields fail closed.
6. Factory provenance is necessary but insufficient for automatic enrollment.
7. Every enrollment binding requires both a path guard (pinned factory code) and a deployed-output guard, with guard inputs pinned in-repo.
8. Every discriminator and parameter value is verified against the deployed contract — bytecode for immutables, state reads for storage.
9. Bytecode verifies output structure; it never independently proves semantic equivalence.
10. AI drafts and challenges semantic work; humans approve completeness, field policy, domains, guards, and identity.
11. A constrained mechanical lane may enroll instances and append candidates, but cannot create semantic authority.
12. A release may span chains only when the same analysis and parameter schema apply.
13. Git and versioned static JSON remain the canonical source of truth and public interface; v0 stays shape-frozen and generated.

This keeps Hooklist simple at the system level: a small reviewed release registry, deterministic factory adapters, appendable instance records, and generated static lookup files. Complexity is concentrated in the one-time review of how a factory's deployment inputs map to a release, rather than repeated for every deployment.
