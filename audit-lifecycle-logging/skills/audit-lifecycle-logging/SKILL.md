---
name: audit-lifecycle-logging
description: Audit logging and metrics coverage for a user lifecycle (feature, flow, or project) in the customers-backend repo. Use whenever the user wants to trace what's observable across a feature, find logging gaps before launch, debug a production incident with thin observability, prepare a flow for rollout, add structured logs or ICMetrics to an orchestrator/consumer/service, or check that lifecycle steps follow docs/observability-conventions.md (METRIC_PREFIX, 12-char hex log_id, PII safety). Always reports gaps first; only applies edits on explicit go-ahead. Trigger on phrases like "audit logging for X", "what's logged in this flow", "add logging to track this lifecycle", "is this feature observable enough", "find logging gaps in Y", "we got paged and there's nothing in datadog".
---

# Audit Lifecycle Logging

Audit the logging and metrics coverage of a user lifecycle in `customers-backend` and produce a per-step gap report. This is a read-only audit by default. Only modify code after the user explicitly tells you to apply specific recommendations.

The contract this skill enforces lives in [`docs/observability-conventions.md`](../../../carrot/customers/customers-backend/docs/observability-conventions.md) — it's the canonical source for what counts as compliant. Read it before forming opinions; conventions evolve and your memory of them may be stale.

## When to use

Run this skill when:
- A feature is about to roll out and you want to confirm the on-call can actually see what's happening.
- You're debugging an incident and the existing logs/metrics aren't enough.
- A teammate asks "is this flow observable?" or "what gets logged when a user does X?".
- You're adding a new orchestrator/consumer/service and want to make sure it ships with the right hooks.

Do **not** use this skill to:
- Add tracing spans / Datadog APM instrumentation (that's a different layer, handled at the framework level).
- Add product-analytics events to the data warehouse (talk to the team that owns `Domain::Tracking`).
- Audit branding, layering, or other non-observability concerns.

## Step 1 — Establish the lifecycle

The user specifies the lifecycle in one of three shapes. Detect which from their message; if ambiguous, ask one short question.

### Shape A — Entry point + walk the code

User points at a file or class (orchestrator, resolver, consumer, service). Walk from there:

```bash
# Find every downstream Api/Service/Orchestrator/Job call from the entry file.
grep -nE '(::Api\.new|::Orchestrator\.new|Service[^a-z]|perform_later|publish)' <entry_file>
```

For each downstream class, follow one hop further if it's another orchestrator or service — but stop at domain APIs (their internals are owned by the domain, not by this lifecycle). The audit's scope is the **caller's responsibility for logging the response** of each downstream call, not the downstream's internals.

### Shape B — Named steps list

User gives an explicit list ("eligibility check → treatment assigned → exposure logged → conversion fired"). For each named step:

```bash
# Map each step to candidate call sites.
rg -n --type ruby '<step_keyword_or_class>' --glob '!spec/' --glob '!sorbet/'
```

If a step has zero matches, flag it in the report as **unmapped** — the user either named it wrong or the code doesn't reflect their mental model. Don't silently invent a match.

### Shape C — Spec / ticket / design doc

User points at a Linear or Jira ticket, a Confluence page, or a markdown design doc. Extract the user-visible steps from the spec, then fall back to Shape B (map each step to code).

For Linear/Jira, prefer the Glean MCP if available (`mcp__glean_default__search`). Otherwise ask the user to paste the relevant section — don't speculate from the title.

### Always: confirm the step list before auditing

Before running the audit, restate the step list back to the user in 5-10 lines so they can correct your map of "what the lifecycle is." A wrong premise here wastes the entire report.

## Step 2 — Audit each step

For every step, examine the call site and the branches that follow it. Score it against the five dimensions below. **Skip dimensions that genuinely don't apply** — note in the report that you skipped them and why. Don't fabricate findings to pad the audit.

### 2.1 Metrics coverage

Per `docs/observability-conventions.md`, services / APIs / orchestrators / resolvers / mutations / consumers define a `METRIC_PREFIX` constant and emit `ICMetrics.increment` on each success / error branch of external calls.

For each call site, check:

- Is `METRIC_PREFIX` declared at the top of the class? (`grep -n 'METRIC_PREFIX' <file>`)
- Does every success branch emit a metric? (`*.success`)
- Does every error branch emit a metric with a discriminating dimension? (`*.error`, `error_source: "..."`)
- For wrapping operations whose latency matters (downstream API calls, cache lookups), is there an `ICMetrics.timing(...)`?

A branch that silently returns `nil` / `false` / an empty array on failure is a finding — the on-call has no way to tell that path fired.

### 2.2 Structured logs

Per the same conventions doc, every `Rails.logger` call MUST include:

- `message:` — short human-readable description
- `log_id:` — a 12-character hex fingerprint **unique to this call site** (literal string baked into the source)

And SHOULD include `user_id:` and layer-relevant operational identifiers (`business_id`, `member_id`, `order_id`, etc.).

For each error branch, check:

- Is there a `Rails.logger.warn/error` call before the return?
- Does it have a `log_id`? Is the hex literal a valid 12-char hex (`^[0-9a-f]{12}$`)?
- Generate new log_ids with `openssl rand -hex 6` — never with `SecureRandom.hex(6)` at runtime, and never reuse an existing log_id across call sites (`LogFingerprintCop` enforces uniqueness).
- Are the relevant identifiers (`user_id`, etc.) attached as structured fields?

For success branches in user-facing flows, a single info-level log at the "happy path completed" point is usually enough — don't recommend logging every internal step.

### 2.3 PII safety (this is the dangerous one)

Per the root `AGENTS.md`, do **not** log direct PII: names, emails, phone numbers, addresses, SSNs, raw IPs, payment credentials. Also do not log unfiltered `parameters.serialize` / job args when the parameters object could contain any of the above.

For every existing `Rails.logger` call in the lifecycle, check:

```bash
# Find suspicious patterns.
rg -n 'parameters\.serialize|\.email\b|\.phone\b|\.address\b|request_ip|raw_ip' <files>
```

If a call logs `parameters.serialize` (or any nested object that *could* contain PII), flag it as a **PII risk** in the report — even if the current parameter shape is benign, future additions to the Parameters class will silently start leaking. The fix is to log specific fields explicitly.

Internal identifiers (`user_id`, `order_id`, `transaction_id`, `log_id`, `member_id`, `business_id`) are operational data and are expected to be logged as structured fields.

### 2.4 Silent failures

Walk every branch in each step's code. For each branch, ask: "If this branch fires in production, can someone tell?"

A branch is a **silent failure** if it:
- Returns `nil` / `false` / `[]` / a generic error response on a downstream failure with **no log AND no metric**.
- Catches an exception and returns gracefully with no log AND no metric.
- Falls through a feature-variant disabled path without recording that the gate was hit.

For early-return guard clauses (e.g. "guest user, bail"), a single metric increment is usually sufficient — you don't need both a log and a metric.

### 2.5 Lifecycle-level coverage

After auditing individual steps, zoom out:

- **Funnel visibility**: Can you reconstruct, from logs and metrics alone, how a user moved through the lifecycle? If the steps share no correlating identifier (no `user_id`, no `request_id`, no `log_id` lineage), the audit should flag it.
- **Terminal states**: For each terminal state in the lifecycle (success, each distinct failure mode), is there at least one metric the on-call dashboard could chart?
- **Domain events**: For state-change steps (subscription created, code redeemed, eligibility granted), check whether a domain event is published. Lifecycles that mutate state without emitting a domain event are usually a coverage gap, but the fix is policy-loaded — flag it for the user, don't prescribe.

## Step 3 — Produce the report

Use this exact template. The structure matters because it's how the user scans the report and decides what to apply.

```markdown
# Lifecycle observability audit — <lifecycle name>

**Scope:** <list of files audited>
**Steps:** <N>
**Conventions reference:** docs/observability-conventions.md

## Summary

| Step | Metrics | Logs | PII | Silent failures | Verdict |
|---|---|---|---|---|---|
| 1. <step name> | ✓ / partial / ✗ | ✓ / partial / ✗ | ✓ / risk | 0 / N | ok / needs work |
| 2. ... | | | | | |

## Findings

### Step 1 — <step name> (`<file>:<line>`)

**What's there now:**
- <existing metrics / logs in this step, with line numbers>

**Gaps:**
- 🔴 **<short label>** — <one-sentence problem> (`<file>:<line>`)
  - Why it matters: <one sentence — what on-call loses, or what risk it introduces>
  - Suggested change: <concrete code snippet, including suggested log_id from `openssl rand -hex 6`>

### Step 2 — ...

## Cross-cutting findings

- <funnel-level issues that don't belong to a single step>

## Suggested follow-ups (optional, lower priority)

- <things worth doing but not blocking>
```

Use the 🔴 emoji **only** if the user has emoji output enabled (check the conversation tone — if they use emojis, mirror them; otherwise drop the icon and use `**[high]**` / `**[med]**` / `**[low]**` prefixes instead). Severity hierarchy: PII risk > silent failure on an error branch > missing metric on a critical-path branch > missing log on a non-critical branch > stylistic deviations from convention.

After producing the report, ask: "Want me to apply specific findings? Tell me which ones and I'll edit the files. Otherwise this is read-only."

## Step 4 — Apply edits (only on explicit go-ahead)

When the user picks findings to apply, follow these rules:

1. **One file at a time, in order.** Don't batch edits across multiple files without showing each file's diff first for files with >3 changes.
2. **Generate fresh log_ids.** For each new `Rails.logger` call, run `openssl rand -hex 6` and use the output. Never reuse an existing log_id from elsewhere in the codebase.
3. **Match local style.** If the surrounding code uses `Rails.logger.warn` for non-success branches, do the same; don't switch to `error` unless the user asked.
4. **Don't add comments for the change.** Per the repo's [code-commenting guide](../../../carrot/customers/customers-backend/docs/code-commenting.md), the code should be self-explanatory; don't write `# Added per logging audit` or similar.
5. **Run the linter on touched files** when done: `script/lint <changed files>`. `LogFingerprintCop` will catch duplicated log_ids if you accidentally reuse one.
6. **Report tests that should be re-run.** If you added metrics or logs, the spec for the touched file likely uses `expect(ICMetrics).to receive(:increment).with(...)` or `expect(Rails.logger).to receive(:info)`. Surface this so the user can run the relevant spec — don't run it yourself unless asked.

After applying, summarize: which files changed, which findings are now resolved, which were intentionally skipped (and why).

## Things this skill should NOT do

- **Don't make the audit feel mechanical.** A 30-finding report on a 50-line file is noise. Aggressively cut findings that are not actionable in the current context.
- **Don't reformat unrelated code.** Edits should be additive (new log lines, new metric calls). Resist the urge to refactor the surrounding code.
- **Don't second-guess existing log_ids.** If a log_id is already present and valid (12-char hex), leave it alone — even if the message wording could be better.
- **Don't audit the downstream domain.** If the lifecycle calls `CouponsDomain::Api::GetProxyCouponFromCouponCodeString`, audit how the caller handles its response, not the API's internals.
- **Don't recommend Datadog dashboards or alerts.** That's a different skill. Stop at "this metric now exists; the dashboard team can chart it."

## Bundled reference

- [`references/quick-patterns.md`](./references/quick-patterns.md) — copy-pasteable grep snippets for finding common gaps, and example before/after diffs from real customers-backend files.
