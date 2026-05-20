---
name: triage-prs
description: Walk the open PR queue on Uniswap/hooklist, verify bot reviews, approve+rebase-merge the canonical bot-authored PRs, manual-review the external-contributor PRs that the bot can't process, and detect/fix `aggregate.py` breakage of main. Use when the user says "triage PRs", "go through the open PRs", "merge what's mergeable", or after a batch of hook submissions has accumulated.
---

# Triage the hooklist PR queue

This repo's merge flow has more structural baggage than it looks. This skill encodes the rules so a triage pass takes minutes, not an hour of rediscovery.

## Background that drives every decision

- **Merge ruleset**: rebase-only, 2 approving reviews, required status checks `validate` + `review`. No merge commits, no squashes.
- **Author identities**:
  - `app/hooklist-generator` (bot) — opens hook PRs that originate from accepted GitHub issues. Has write perms, so the `review-hook` workflow runs cleanly and the Claude bot posts an APPROVED review.
  - External humans (read-only repo perms) — the `anthropics/claude-code-action` refuses to run for them and the `review` status check goes FAILURE. The PR is structurally unmergeable until either (a) a maintainer-authored equivalent PR replaces it, (b) the workflow is patched to skip-SUCCESS for read-only actors, or (c) admin override.
  - `dgilmanuni` and other Uniswap employees — write perms, bot runs normally.
- **Schema gotcha that has historically broken main**: `hook.description` has `maxLength: 500`. The PR-time `validate.py` walks only changed files, but the merge-time `aggregate.py` re-validates the entire repo against the same schema. A "refine description" follow-up PR can pass per-file validation and then break `regenerate.yml` on merge. Always precheck description length before approving.
- **Self-approval block**: GitHub forbids approving your own PR. For a maintainer-authored PR (e.g., a hotfix), the bot's approval is one slot and you can't fill the second; use `gh pr merge --admin --rebase --delete-branch` to bypass.
- **`/Users/mark.toda/.claude/CLAUDE.md`** memory entry: "bot reviews count toward ruleset's 2-reviewer rule, so AI approval + 1 human = mergeable" — this is what makes the fast-track path work.

## The flow

Spend less than 30 seconds per PR on the fast path. Most of the value of this skill is *not* rediscovering the rules each time.

1. **Snapshot the queue**:
   ```sh
   gh pr list --state open --json number,title,author,headRefName,reviewDecision,mergeStateStatus,statusCheckRollup --limit 50
   ```

2. **For each open PR, classify by author + check state**:

   | Class | How to detect | Action |
   |---|---|---|
   | A. Bot-authored, all checks SUCCESS, bot APPROVED | `author.login == "app/hooklist-generator"` and the github-actions bot has posted an APPROVED review | **Fast-track**: precheck description length, post a one-line approving review, rebase-merge. |
   | B. Bot-authored, bot REQUESTED_CHANGES or `review = FAILURE` | Bot review is REQUEST_CHANGES, or the workflow itself failed | Read the bot review, decide if the issue is real, and either close the PR (have the issue re-opened) or escalate to the user. Do not approve. |
   | C. External-author hook PR, `review = FAILURE` from permission check | PR `author.is_bot == false`, status `review` is FAILURE, the failure log says "Actor does not have write permissions" | **Manual verification path** (below). Do not approve; post a maintainer-review comment with verified findings. The `review` status will stay failing — that's the structural blocker. |
   | D. Maintainer-authored hotfix (e.g., schema fix, description trim) | `author.login` is a Uniswap employee | Get the bot review, then **admin-merge** with `gh pr merge N --admin --rebase --delete-branch` (you can't self-approve). |
   | E. Other (workflow PRs, anything not touching `hooks/`) | No hook files in `gh pr view --json files` | Read the diff yourself; if good, approve. Do not admin-bypass for non-urgent changes. |

3. **Always precheck description length** before approving any hook PR:
   ```sh
   curl -sL "https://raw.githubusercontent.com/Uniswap/hooklist/$(gh pr view N --json headRefOid -q .headRefOid)/<hook-file-path>" \
     | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d['hook']['description']))"
   ```
   If >500, refuse to approve until the description is trimmed — even if `validate.yml` passed, because that workflow only walks changed files and may have been bypassed.

4. **Merge** (Class A):
   ```sh
   gh pr review N --approve --body "..."
   gh pr merge N --rebase --delete-branch
   ```

5. **Merge** (Class D — self-authored):
   ```sh
   gh pr merge N --admin --rebase --delete-branch
   ```

6. **After all merges, sanity-check main** still aggregates:
   ```sh
   git pull origin main --ff-only
   nix-shell -p python312Packages.jsonschema --run "python scripts/aggregate.py" 2>&1 | tail -3
   ```
   If `aggregate.py` fails on main, identify the failing file, draft a fix PR, run the validators locally, push, approve via the bot, then admin-merge (Class D path).

## Manual verification path (Class C)

When the bot can't run, the maintainer becomes the reviewer. Verify against on-chain source — *do not approve*, only comment.

1. Read the hook file and confirm the address-bitmask matches the claimed `flags` (the `validate` workflow already checks this, but re-confirming costs nothing).
2. Look up the verified source on the chain's block explorer (BaseScan for chainId 8453, Etherscan v2 for the rest — `chains.json` has the API URL for each chain). Use `WebFetch` against the `#code` URL on the explorer if no API key is available. For deep verification, dispatch a `general-purpose` agent with the explicit list of properties to check (`dynamicFee`, `upgradeable`, `requiresCustomSwapData`, `vanillaSwap`, `swapAccess`) — past sessions have proven this is the fastest way to get a thorough source read.
3. Verify each of the 5 properties against the actual Solidity logic (see `.claude/prompts/review-hook.md` for the definitions and the property-classification decision tree).
4. Post a comment (not a review) on the PR with the per-property verdict. Explicitly note that the `review` status check is structurally blocking the merge and that this is a maintainer verification, not an approval.
5. Update the user that the PR is verified but blocked.

## Approval body template (Class A)

Keep it short. Acknowledge what the bot covered and add anything you double-checked:

```
Bot review verified. [Hook name + brief identity]. Bitmask 0x<lower14> → <flag list>. LGTM.
```

If anything notable in the data (e.g., description close to the 500 limit, or a property that's debatable per the spec), note it briefly so the audit trail captures the human signal.

## Things to deliberately *not* do

- **Don't push to the bot's branch** to "fix" description prose or formatting. Either merge as-is or ask the original issue author to resubmit. The bot's branch is an artifact of the workflow, not a maintainer worktree.
- **Don't approve the same PR twice**. If you've already approved as `marktoda`, GitHub will silently no-op a re-approval but the audit trail looks weird.
- **Don't `--admin` your way past a failing required check** unless main is broken or the failure is the structural read-only-actor case on a Class C PR (and even then, prefer the manual-comment-only path — admin-bypassing an external PR could land unverified code).
- **Don't run `python scripts/aggregate.py` and commit the regenerated `hooklist.json`** as part of any non-`regenerate.yml` workflow. That's the dedicated workflow's job; if you commit a regenerated `hooklist.json` in your PR, you'll race the workflow and create churn.

## What "done" looks like

A clean end-of-pass summary back to the user:

- N Class-A PRs merged (list numbers).
- N Class-C PRs commented (list numbers + the structural-blocker note).
- N Class-D hotfixes admin-merged (if any).
- Open PRs remaining + why they're not actionable (typically: Class B awaiting upstream resubmit, or Class C awaiting another maintainer's eyes, or Class E waiting on a 2nd human reviewer that isn't `marktoda`).
- Sanity check: `aggregate.py` on main passes.
