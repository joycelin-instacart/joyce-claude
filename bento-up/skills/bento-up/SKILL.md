---
name: bento-up
description: Use when the user wants to check that all bento services are healthy, bring the local dev env back up, restart failing services, or invokes /bento-up. Trigger on prompts like "are my services up", "is bento healthy", "reboot anything failing", "make sure everything's running".
---

# Bento Up

Check `bento status`, identify unhealthy services, and restart them.

## Workflow

1. Run `bento status` and parse the table. Columns of interest: `TIER`, `ID`, `HEALTH`, `SERVICE`.

2. Classify each row:
   - **Healthy** — skip:
     - `tool` or `app` tier with `HEALTH = success` and `SERVICE = running`
     - `daemon` row (always blank HEALTH by design)
     - `task` tier with `SERVICE = stopped` — these are one-shots (e.g. `db-setup`, `migrations`); stopped is the expected resting state
   - **Needs restart** — `SERVICE = running` but `HEALTH` is `timeout`, `failure`, or anything non-success → `bento restart <id>`
   - **Needs start** — `tool` or `app` tier with `SERVICE = stopped` → `bento start <id>`

3. If everything is healthy, tell the user and stop.

4. Otherwise, list the unhealthy services and the action you're about to take, then run the `bento restart`/`bento start` commands in parallel (they're independent). Use `run_in_background: true` if they're slow — heavy apps like `customers-backend/web` take a while to come back up.

5. After the restarts finish, run `bento status` again and confirm everything is now healthy. Report the final state and call out anything still unhealthy.

## Notes

- `HEALTH = timeout` on a heavy web app (e.g. `customers-backend/web`) often just means a slow healthcheck on a running process — a restart usually clears it. Still restart per the policy above.
- High CPU% right after a restart (e.g. 150%+) is normal warm-up, not a problem.
- Never restart `daemon` — its blank HEALTH is by design.
- Never `bento start` a `task`-tier service — they're one-shots and finishing is success.
