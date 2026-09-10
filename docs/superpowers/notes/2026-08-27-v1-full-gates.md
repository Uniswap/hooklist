# Gates for the full v1 design (archived blueprint)

Blueprint: docs/superpowers/specs/2026-08-27-hook-release-registry-full.md
Build it only when ALL hold:

- [ ] Org admins confirm a dedicated GitHub App can bypass the 2-review ruleset
      (else the enrollment automation saves zero clicks). One afternoon to answer.
- [ ] A named consumer (e.g. Uniswap/backend#10753) commits to reading enrollment
      output at sub-day freshness.
- [ ] Sustained submission volume at July-2026 levels (~50+/week) for a month.

Known fixes required if built: scan cursors must not advance inside unmerged PRs
(duplicate-PR spam bug); path-guard halts and candidate-ledger growth need an
alert channel; enrollment cron daily, not 30 minutes; bound the migration window.
Cheap interim assist available any time: exact-runtime-codehash match note in the
review bot to make family approvals one-glance.
