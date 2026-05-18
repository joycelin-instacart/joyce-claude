# Daily Update Candidates — drafting standup for Mon 2026-05-18

Today: 2026-05-17 (Sunday)
Yesterday-working-day: 2026-05-15 (Friday)
Prior Monday priority post: 2026-05-11

## Yesterday (Y:) — Friday 5/15

1. [slack 5/15] EI FD discount policy cutover — verified FD still works in Grubhub  *(source: her own Friday standup post Y section)*
2. [slack 5/15] Expy setup for GH+ FD Floating cart message — `<https://roulette.instacart.tools/expy/production/partnerships_grubhub_plus_fd_campaign?...|expy>` *(source: her own Friday standup post Y section)*
3. [git+slack 5/15] NYT new flyout update — merged PR #792206 `<https://github.com/instacart/carrot/pull/792206|PR>` *(source: gh PR list + her Friday standup post)*
4. [slack 5/15] Mandatory Snowflake Continu training *(source: her Friday standup post)*
5. [git 5/14, slack 5/15] Peacock-distributed IC+ benefit suppression — landed code, testing in prod `<https://github.com/instacart/carrot/pull/791828|PR>` `<https://instacart.atlassian.net/browse/CXP-210557|CXP-210557>` *(source: Friday "T:" carryover + Friday PR merge + Rob/Peacock thread)*
6. [claude 5/15] NYT outbound banner copy update gated by `partnerships_nyt_cooking_api_redemption_enabled` roulette *(source: Friday Claude transcript — joycelin-instacart/update-nyt-banner-placement)*

## Today (T:) — Monday 5/18 candidates

1. [carryover from Fri T:] Testing Peacock-distributed IC+ users do not see Peacock offer `<https://github.com/instacart/carrot/pull/791828|PR>` *(source: Friday T section, still in flight per Rob thread)*
2. [carryover from Fri T:] Create EPP placements for NYT storefront banner *(source: Friday T section)*
3. [priority-post 5/11] Add payment gate for Peacock redemption — PR #792845 now up `<https://github.com/instacart/carrot/pull/792845|PR>` `<https://instacart.atlassian.net/browse/CXP-211150|CXP-211150>` *(source: Monday priority post + weekend PR open)*
4. [git 5/16-17] NYT modal image upload + flyout image swap `<https://github.com/instacart/carrot/pull/792812|images PR>` `<https://github.com/instacart/carrot/pull/792815|swap PR>` *(source: weekend PRs)*
5. [priority-post 5/11, slack 5/14 Rob thread] Peacock World Cup readiness — credit-card trial redemption requirement (June 11 deadline) *(source: Monday priority post + Rob thread on 5/14)*
6. [carryover] Mandatory Snowflake Continu training *(source: Friday T section, likely still pending)*

## Blocker (B:) — usually omit

1. None surfaced — no blocker-language Slack messages in past 3 days, no Blocked-status Jira tickets identified, Yoda backtest already resolved (pivoted to payment gating). Recommend omitting B: section per Joyce's habit.

---

## Auto-selected for test mode

Y: 1, 2, 3, 4, 5 (omit 6 — banner copy is part of the broader NYT flyout work already captured in item 3)
T: 1, 2, 3, 4, 5 (omit 6 — Snowflake training is low signal for Monday focus)
B: skip
