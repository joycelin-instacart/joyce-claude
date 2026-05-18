# Sources Trace — daily-update for Mon 2026-05-18

## Date window
- Today: 2026-05-17 (Sunday)
- Yesterday-working-day: 2026-05-15 (Friday)
- Prior Monday: 2026-05-11
- Epoch ranges computed in America/New_York

## Queries executed

### Git (carrot monorepo)
- `git log --author="Joyce Lin" --since="2026-05-15 00:00" --until="2026-05-16 00:00" --oneline` → no commits returned (empty output)
- `git log --author="Joyce Lin" --since="2026-05-13 00:00" --until="2026-05-16 00:00" --oneline` → no commits returned (likely because commits land via squash-merge under different author)
- `git log --author="Joyce Lin" --since="2026-05-16 00:00" --until="2026-05-18 00:00" --oneline` → no weekend commits

### GitHub PRs
- `gh pr list --author "@me" --state merged --search "merged:2026-05-15" --limit 20` → returned:
  - #792206 [CXP-211002] Update NYT outbound flyout to new design (merged 2026-05-15 14:43)
  - #791828 [CXP-210557] Hide Peacock benefit for users on the Peacock-distributed IC+ plan (merged 2026-05-14 21:01)
- `gh pr list --author "@me" --state all --limit 10` → 10 recent PRs across NYT/Peacock workstreams (including weekend opens: #792845, #792815, #792812)

### Slack
- `slack_search_public_and_private from:<@U0AK8RMGWFR> after:2026-05-15 before:2026-05-16 limit:20 sort:timestamp desc` → No results (search filter behavior — Joyce's posts on 5/15 surfaced only via in:channel query)
- `slack_search_public_and_private from:<@U0AK8RMGWFR> in:#team-partnership-experience-internal limit:10 sort:timestamp desc` → returned 10 results including:
  - Friday 5/15 14:23 EDT standup (Y/T post — load-bearing source)
  - Thursday 5/14 standup
  - Wednesday 5/13 standup
  - Tuesday 5/12 standup
  - Monday 5/11 priority post (load-bearing source for T items)
  - Several thread replies in Rob's 5/14 Peacock workstream thread (provides Peacock context)
- `slack_search_public_and_private from:<@U0AK8RMGWFR> (blocked OR waiting OR pending OR stuck) after:2026-05-14 limit:10` → No results

### Glean (Jira)
- `mcp__glean__search query:"joyce.lin CXP" app:jira updated:past_week num_results:15` → Result oversized (67K chars), file saved but not re-read. Sufficient signal already obtained from PR titles which contain CXP IDs (CXP-211002, CXP-210557, CXP-211150).

### Claude transcripts
- Located 6 jsonl files modified Friday 2026-05-15 in `~/.claude/projects/-home-bento-carrot-customers-customers-backend/`
- Extracted user prompts. Clustered topics:
  - NYT outbound flyout redesign (multiple sessions: update-nyt-outbound-flyout, update-nyt-banner-placement)
  - Peacock IC+ plan benefit suppression (remove-peacock-benefit-offer, modifying HidePeacockForDistributedPlan FV)
  - Checkout payment switcher BMO (CA-only enable, parallel to chase/mastercard US-only)

## Source-to-candidate mapping

| Candidate | Primary source | Corroborating |
|---|---|---|
| Y1 EI FD discount cutover | Friday standup post (Y) | n/a |
| Y2 Expy GH+ FD floating cart | Friday standup post (Y) | n/a |
| Y3 NYT flyout update | GH PR #792206 merged 5/15 | Friday standup post (Y); Claude transcript |
| Y4 Snowflake training | Friday standup post (Y) | n/a |
| Y5 Peacock benefit suppression testing | Friday standup post (T) | PR #791828 merged 5/14; Rob thread 5/14; Claude transcripts |
| Y6 NYT banner copy roulette gating | Claude transcript (update-nyt-banner-placement) | not yet in a PR |
| T1 Peacock testing carryover | Friday T section | PR #791828; Rob's 5/14 thread |
| T2 NYT EPP placements | Friday T section | Monday priority post (NYT launch) |
| T3 Peacock payment gate | Monday priority post 5/11 | Weekend PR #792845, CXP-211150 |
| T4 NYT modal image swap | Weekend PRs #792812, #792815 | n/a |
| T5 Peacock World Cup readiness | Monday priority post 5/11 + Rob's 5/14 thread | June 11 deadline confirmed by Rob |
| T6 Snowflake training | Friday T section | low priority |
| B  No blockers | blocker search returned empty | Yoda issue resolved via pivot to payment gating |

## Gaps / Caveats
- Glean Jira search hit token limit; relied on PR titles for CXP IDs
- `git log --author "Joyce Lin"` returned no rows for the week — likely because merges are squashed under another committer; the PR list compensates
- `slack_search ... from:<@U0AK8RMGWFR>` with after/before filters returned no results; the `in:#channel` variant surfaced her posts including 5/15
