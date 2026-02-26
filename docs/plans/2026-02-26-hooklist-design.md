# Hooklist Design

Public registry of Uniswap v4 hook deployments by chain and address.

## Repository Structure

```
hooklist/
├── hooks/
│   ├── ethereum/
│   │   └── 0xAbC...123.json
│   ├── base/
│   ├── arbitrum/
│   └── ...
├── hooklist.json                # auto-generated aggregate of all hooks
├── README.md                    # auto-generated summary table
├── .github/
│   ├── workflows/
│   │   ├── analyze-hook.yml     # triggered on issue open
│   │   └── regenerate.yml       # rebuilds hooklist.json + README on merge
│   └── ISSUE_TEMPLATE/
│       └── submit-hook.yml      # structured issue form
├── scripts/
│   └── aggregate.py             # builds hooklist.json + README table from hook files
├── CLAUDE.md                    # instructions for Claude in CI
└── schema.json                  # reference schema for hook files
```

Chain directories use lowercase names (ethereum, base, arbitrum, optimism, polygon). All v4 chains supported.

## Hook File Format

Each hook is a JSON file at `hooks/<chain>/<address>.json`:

```json
{
  "hook": {
    "address": "0xAbC...123",
    "chain": "ethereum",
    "chainId": 1,
    "name": "MyHook",
    "description": "Short summary of what the hook does",
    "deployer": "0x...",
    "verifiedSource": true,
    "auditUrl": ""
  },
  "flags": {
    "beforeInitialize": true,
    "afterInitialize": false,
    "beforeAddLiquidity": false,
    "afterAddLiquidity": false,
    "beforeRemoveLiquidity": false,
    "afterRemoveLiquidity": false,
    "beforeSwap": true,
    "afterSwap": true,
    "beforeDonate": false,
    "afterDonate": false
  },
  "properties": {
    "dynamicFee": false,
    "returnsDelta": true,
    "upgradeable": false
  }
}
```

`hooklist.json` is an array of all these objects.

## Submission Flow

1. User opens a GitHub Issue using the "Submit a Hook" template (chain + address required, name/description/deployer/auditUrl optional)
2. GitHub Action triggers on `issues: opened`
3. Claude Code parses the issue, fetches verified source from Etherscan API, analyzes the Solidity
4. Claude creates a branch, commits the hook JSON, opens a PR that closes the issue
5. If source is not verified on Etherscan, Claude comments on the issue and labels it `unverified`
6. Maintainer reviews and merges
7. On merge, regenerate workflow rebuilds `hooklist.json` and README table

## Issue Template

Required fields: chain (dropdown), address (text input).
Optional fields: name, description, deployer, audit URL.

Submitter-provided optional values are used when present. Claude generates missing values from source analysis (contract name, Claude-generated summary, etc.). Flags and properties are always determined by Claude from source code — not submitter-overridable.

## CI Workflows

### analyze-hook.yml (on issue open)

- Triggered by `issues: opened`
- Validates issue matches Submit a Hook template
- Checks for duplicates (`hooks/<chain>/<address>.json` already exists?)
- Runs Claude Code with `CLAUDE_CODE_OAUTH_TOKEN` and `ETHERSCAN_API_KEY` secrets
- Claude fetches source, analyzes, generates JSON, opens PR

### regenerate.yml (on push to main)

- Triggered by `push` to `main` with `paths: ['hooks/**']`
- Runs aggregate script to rebuild `hooklist.json` and README summary table
- Commits and pushes changes using default `GITHUB_TOKEN`
- No recursive trigger: only watches `hooks/**` but only modifies root-level files, and `GITHUB_TOKEN` pushes don't trigger workflows

## CLAUDE.md Analysis Instructions

### Flag Detection (priority order)

1. Check hook address bitmask — v4 encodes permissions in the address
2. Cross-reference with `getHookPermissions()` if present in source
3. Read actual callback implementations as sanity check

### Property Detection

- **dynamicFee**: check if hook implements `beforeSwap` returning a fee override
- **returnsDelta**: check if `beforeSwap`/`afterSwap` return nonzero deltas (BeforeSwapDelta, afterSwapDelta)
- **upgradeable**: check for proxy patterns (ERC-1967, transparent proxy, UUPS), delegatecall, mutable implementation storage

### Output

- Generate hook JSON matching schema
- Use submitter-provided values when given, generate from source otherwise
- Create branch `hooks/<chain>/<address>`, commit file, open PR closing the issue

## Design Decisions

- **One file per hook**: minimizes merge conflicts, easy to review in PRs
- **JSON format**: universal, easy to aggregate programmatically
- **Issue-based submission**: lowest friction for submitters, Claude handles all the work
- **Etherscan-only source**: if not verified, submission is rejected with explanation
- **Repo-only interface**: GitHub is the UI, no static site needed initially
- **Claude Code in CI (Approach A)**: single tool handles fetching, analysis, and PR creation
