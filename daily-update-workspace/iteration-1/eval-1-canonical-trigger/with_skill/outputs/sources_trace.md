# Sources trace

Date math: today = Sunday 2026-05-17. Yesterday (previous working day) = Friday 2026-05-15.

| Source | Query / window | Result |
|---|---|---|
| git log (carrot, Joyce, Fri) | `git log --author="Joyce Lin" --since="2026-05-15" --until="2026-05-16"` | 0 direct commits (PRs merged via squash) |
| gh pr list merged Fri | `--state merged --search "merged:2026-05-15"` | 2 merged PRs: #791828 (Peacock benefit, CXP-210557), #792206 (NYT flyout, CXP-211002) |
| gh pr list open | Joyce's open PRs | 6 open: #792845 (Peacock PM gate CXP-211150), #792815 (NYT modal image), #792812 (NYT 1x/3x images), #791195 (NYT offer card), #785366 (BMO payment switcher), #783432 (NYT placement copy override) |
| Slack: from:joyce after Fri 00:00 ET, before Fri 23:59 ET | 20 messages — own standup post, NYT DM threads with Priyanka, Peacock IC+ thread w/ Rob, self-DM scratchpad ("Peacock attributes, peacock payment, training", "EPP mobile in staging?", "Update offer card image?") | rich signal |
| Slack: from:joyce in #team-partnership-experience-internal | 5 most recent — top hit is Friday standup post 2026-05-15 14:23 (full Y/T) + Thursday Peacock thread w/ Rob | got last standup |
| Slack: from:joyce (blocked OR waiting OR pending OR stuck) last 3d | 0 results | no blockers |
| Slack: #team-partnership-experience-internal Mon 5/11 00:00–23:59 | Slackbot priority reminder, found thread | Joyce's Monday priorities reply: Peacock benefit suppression, Peacock payment gate, GH+ FD Expy, NYT launch placements, Costco VGP Thursday cutover |
| Slack: thread on priority reminder | 6 replies | Joyce's full priority list captured |
| Glean Jira: joyce.lin CXP Done past_week | 50+ Jira hits | Done: CXP-210927 (Peacock hide, 5/15), CXP-211002 (NYT flyout, Done), CXP-210460 (Costco VGP), CXP-211136 (Phase 3 verify), CXP-208634 (NYT duration), CXP-205675 (IC+ trial→paid hook), CXP-205678 (Admin care), CXP-207887 (GH FD floating cart). In Progress: CXP-208674 (NYT placement copy), CXP-207786 (BMO switcher), CXP-211293 (Ideation). New (just-created subtasks under CXP-211150): CXP-211294/295/296/297 (Peacock PM gate breakdown). Acknowledged: CXP-210350 (MC credit copy), CXP-210839 (DDC boku), CXP-211244 (CRM attribute for Peacock) |
| Glean Jira: CXP In Progress from:joyce.lin | overlapping set | confirms in-flight tickets |
| Claude transcripts | 6 jsonl files modified Fri 5/15 | Topics: undo PR #789455, return ineligible for nbcu_free_yearly in peacock_eligibility_service.rb, NYT outbound flyout design update (gated by partnerships_nyt_cooking_api_redemption_enabled), Peacock benefit sunset (don't revoke), BMO payment switcher (CA only), NYT banner placement text update |

Tallies: Slack 3 queries (40+ hits), Slack thread read 1, Slack channel read 2, git/gh 3, Glean Jira 2 (100+ results), Claude transcripts 6 files (~65 user prompts).
