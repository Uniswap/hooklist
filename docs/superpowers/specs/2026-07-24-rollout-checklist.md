# Ingestion rollout checklist (repo-settings + coordination work)

- [ ] Create "hook-ingest-bot" GitHub App (contents:write only); install on repo;
      set INGEST_APP_ID var + INGEST_APP_PRIVATE_KEY secret.
- [ ] Add the ingest App to the ruleset bypass list (mechanical lane direct push).
      Decision recorded in spec §Governance; fallback = auto-merge PRs.
- [ ] Enable GitHub Pages (source: GitHub Actions) in repo settings.
- [ ] Run ClickHouse sizing query (Alex F):
      select chain_id, uniqExact(hooks) from v4_initialize
      where hooks != '0x0000000000000000000000000000000000000000' group by chain_id
      → record expected instance + family counts; sets review-throughput expectations.
- [ ] Run scripts/seed_families.py (post-merge); spot-check the output locally
      (scripts/validate.py + scripts/build_artifacts.py); push directly to main
      with the ingest App credentials (mechanical lane: the seed is derived from
      already-human-reviewed hooks/ entries, and a seed PR would violate our own
      CI policy matrix — ~224 family files plus index/families mixing).
- [ ] Enable ingest on celo + soneium (workflow_dispatch with chains input); watch 3 days.
- [ ] Cross-check celo/soneium index counts vs ClickHouse.
- [ ] Enable unichain + ethereum; watch backfill chunking + RPC rate limits.
- [ ] Enable base (largest); confirm backfill completes (est. 2-3 days).
- [ ] Share registry integration docs with Alex F: index/families as the
      loop's "what's new"/"what's known" reads (spec §Backend integration);
      his PR 10753's RECORD phase should read this repo, not an internal ledger.
- [ ] Announce new artifacts (families.json, lookup/) + jsDelivr URLs.
- [ ] Later (consumer-paced): extend chains.json RPC config beyond the initial five.
