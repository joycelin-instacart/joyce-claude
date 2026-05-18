# Sources queried for daily update draft

## Git
- `git log --all --author="Joyce" --since="14 days ago"` — full picture of recent work areas (Peacock, NYT, GH+ FD, EI FD policy cutover, BMO icon)
- `git log --all --author="Joyce" --since="2026-05-15 14:23:00"` — commits after Friday's standup, to figure out what's new since last update
  - Found: Peacock PM gate work (6 commits today, Sun 5/17), NYT modal images (Sat 5/16), small NYT gating revert (right after Fri standup)

## Slack (channel #team-partnership-experience-internal, C0880QWQ5K3)
- `slack_read_channel` — last ~30 messages to find standup reminders + team norms
- `slack_read_thread` on three most recent standup reminders:
  - Fri 2026-05-15 (TS 1778862621.132169) — Joyce's last update; established her current "Y/T" format
  - Thu 2026-05-14 (TS 1778776230.140999) — context on NYT work + Friday "T" carryover
  - Tue 2026-05-13 (TS 1778689825.074329) — context on Peacock abuse plan + EI FD cutover
- Observation: team uses `Y:` / `T:` (and sometimes `B:`) bullet format. Joyce historically omits `B:` when no blockers. PR/expy links inlined.

## Glean
- `glean_search` for "Joyce Lin Treatment Serving Promos", filter `from: Joyce Lin`, `updated: past_week`
  - Surfaced: NYT review-request DMs (PRs 790675, 790683, 790795, 791195), Peacock abuse tack-plan doc, EI FD discount-policy thread in #commerce-discounting, NYTC user-flow sanity-check DM with Priyanka, Embedded Instacart Incentive Prod Setup doc

## Format conventions inferred
- Y / T / (optional B) headers
- Bullets with sub-bullets via `    ◦`
- Inline links to PRs / Jira / Figma / Roulette expy
- Send to channel C0880QWQ5K3 as Joyce (U0AK8RMGWFR)

## Reasoning about the "yesterday" window
- Today = Sun 2026-05-17. No weekend standups appear in channel history (Slackbot reminder only weekdays).
- Next standup is Mon 5/18. "Yesterday" therefore spans Fri afternoon → Sun, covering whatever has happened since the Fri 5/15 update Joyce already posted.
- Pulled completed items from Fri "T" list that show up in git/Glean as actually done, plus weekend Peacock + NYT work.
