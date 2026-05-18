# Sources Trace — Standup Draft for 2026-05-17 (Joyce Lin)

## User-provided constraints
- Joyce was off yesterday (2026-05-16, Friday) → Y section kept light ("OOO Friday")
- Channel: #team-partnership-experience-internal (C0880QWQ5K3)
- Do not send to Slack; save draft only

## Style reference
Joyce's previous standup in same channel (2026-05-15, msg_ts 1778869382.207349):
- Format: `Y:` / `T:` with hyphen bullets, no `B:` unless blockers
- Plain text, occasional inline link with descriptive anchor

## Today (T) — sources

### 1. Peacock payment-method gate (PR #792845)
- PR created 2026-05-17 21:37 UTC: "[CXP-211150] Add payment-method-required gate to Peacock redemption" (open, updated 2026-05-17 23:51 UTC)
- Joyce's self-DM (D0ALJ960Z7S) on 2026-05-17 14:53–15:27 EDT shows her actively thinking through:
  - "Do we only want to gate for trial users?"
  - Reference file: `domains/view_domain/app/domain/express_view/layouts/express_response_backed/partnership_redemption/peacock.rb`
  - Pattern hint: "use params.is_redemption like in layers/orchestration_layer/orchestrators/partnership_offer_orchestrators/services/custom/bmo/bmo_eligibility_service.rb"
  - Open question: what should `valid_payment_method?` mean (1–4 options listed)
- This is clearly the active in-flight work for today

### 2. NYT modal image PRs (PR #792812, #792815)
- Both opened 2026-05-16 (during her OOO Friday — likely small drop-in cleanup or already queued):
  - #792812 "[NYT] Add modal images at 1x and 3x" — open
  - #792815 "[NYT] Replace API-redemption header image with new modal image" — open
- Listed as T follow-up since they're open and need shepherding to merge

### 3. NYT EPP outbound offer card asset constant (PR #791195)
- Opened 2026-05-14, still open as of 2026-05-15 19:40 UTC
- Joyce posted in #pxp-misc-eng-only on 2026-05-15 15:33 EDT asking for review: "Can I get review for PR to set up NYT placement on EPP"
- Was in her T on 2026-05-15 standup ("Create EPP placements for NYT storefront banner") — likely still pending review/merge

## Yesterday (Y) — intentionally light
- User stated she was OOO on Friday → "OOO Friday" only
- Noted: GitHub shows two NYT PRs opened on 2026-05-16, but per user direction this is treated as OOO and not surfaced as Y work
- No blockers section since none surfaced in DMs/channels

## Items considered and excluded
- Snowflake training (was on 2026-05-15 T) — no signal it's still pending; snowflake_bot DM on 2026-05-16 shows she was trying `create_sandbox_schema` but got "not connected to a Snowflake account" — could be a blocker, but not raised as one by Joyce. Left out to keep the draft tight; could add as a B item if user wants.
- Older merged PRs (NYT DDC, NYT redemption fixes from 2026-05-13) — already in past standups
- Peacock-distributed IC+ users test PR (#791828) — merged 2026-05-15, was T on last standup, complete

## Channels / sources queried
- #team-partnership-experience-internal (C0880QWQ5K3) — last 50 messages
- Last standup thread (msg_ts 1778862621.132169) for style + last Y/T
- Slack search `from:<@U0AK8RMGWFR>` — last 20 messages across all channels/DMs
- `gh search prs --author=joycelin-instacart --limit=10` — recent PR activity
