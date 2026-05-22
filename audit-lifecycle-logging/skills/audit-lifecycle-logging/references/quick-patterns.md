# Quick patterns — grep snippets and example diffs

Copy-paste these when running the audit. All paths are relative to `customers-backend/`.

## Finding existing observability in a file

```bash
# All metric emissions in a file.
grep -nE 'ICMetrics\.(increment|timing|histogram|gauge)' <file>

# All Rails.logger calls in a file.
grep -nE 'Rails\.logger\.' <file>

# All log_ids in a file (verify each is unique).
grep -oE 'log_id: "[0-9a-f]{12}"' <file> | sort | uniq -c | sort -rn

# Domain events published.
grep -nE 'Domain::Events::.*\.publish|publish_event|DomainEvent\.' <file>
```

## Finding gaps across a directory

```bash
# Classes that should but don't have METRIC_PREFIX.
# (Orchestrators, services, consumers, APIs, resolvers, mutations all should.)
DIR=layers/orchestration_layer/orchestrators/express_orchestrators
rg -L 'METRIC_PREFIX' "$DIR" --type ruby --glob '!spec/' --glob '!*_spec.rb'

# Rails.logger calls missing log_id (likely violation).
rg -n 'Rails\.logger\.\w+\(' <DIR> --type ruby | rg -v 'log_id:'

# PII-risky patterns: logging serialized parameters.
rg -nE 'Rails\.logger.*parameters\.serialize|Rails\.logger.*\.email\b|Rails\.logger.*request_ip' <DIR>

# Duplicate log_ids across the codebase (LogFingerprintCop should catch but worth spot-checking).
rg -hoE 'log_id: "[0-9a-f]{12}"' . --type ruby | sort | uniq -c | sort -rn | awk '$1 > 1'
```

## Generating new log_ids

```bash
# One log_id.
openssl rand -hex 6

# N log_ids at once (if you're adding several in one pass).
for i in $(seq 1 5); do openssl rand -hex 6; done
```

Never use `SecureRandom.hex(6)` at runtime inside the source — `log_id` must be a literal so Datadog searches can pin to a specific call site.

## Example diffs from real audits

### Example 1 — Silent failure on downstream error

**Before:**

```ruby
def api_eligible?(criteria)
  custom_check_response = PartnershipOfferOrchestrators::CheckCustomEligibility::Orchestrator.new(parameters: parameters(criteria)).response
  return false unless custom_check_response.is_a?(PartnershipOfferOrchestrators::CheckCustomEligibility::SuccessResponse)
  custom_check_response.eligibility_status == PartnershipOfferDomain::Api::Types::EligibilityStatus::Eligible
end
```

Gap: when the downstream returns a non-success response, this silently returns `false`. The on-call has no way to distinguish "user actually ineligible" from "downstream broken."

**After:**

```ruby
METRIC_PREFIX = T.let("express_orchestrators.services.eligibility.partnership_custom_check", String)

def api_eligible?(criteria)
  response = PartnershipOfferOrchestrators::CheckCustomEligibility::Orchestrator.new(parameters: parameters(criteria)).response
  case response
  when PartnershipOfferOrchestrators::CheckCustomEligibility::SuccessResponse
    ICMetrics.increment("#{METRIC_PREFIX}.api_eligible.success")
    response.eligibility_status == PartnershipOfferDomain::Api::Types::EligibilityStatus::Eligible
  else
    ICMetrics.increment("#{METRIC_PREFIX}.api_eligible.error", error_source: response.class.name)
    Rails.logger.warn(
      message: "partnership_custom_check downstream eligibility check returned non-success",
      user_id: @_user_id,
      offer_name: criteria.offer_name,
      response_class: response.class.name,
      log_id: "<openssl rand -hex 6>",
    )
    false
  end
end
```

### Example 2 — PII risk from `parameters.serialize`

**Before:**

```ruby
Rails.logger.info(
  message: "coupons_orchestrator.promotion_codes_redemption - PromoCodeCampaignLevelCheck is not enabled",
  parameters: parameters.serialize,
  log_id: "2e0ac2a2551e",
)
```

Gap: `parameters.serialize` dumps the full Parameters object, which includes `request_ip` (raw IP — PII per AGENTS.md). Even if `request_ip` isn't sensitive today, future fields added to `Parameters` will silently leak.

**After:**

```ruby
Rails.logger.info(
  message: "coupons_orchestrator.promotion_codes_redemption - PromoCodeCampaignLevelCheck is not enabled",
  user_id: parameters.user_id,
  code: parameters.code,
  log_id: "2e0ac2a2551e",
)
```

Whitelist the specific operational identifiers you need, instead of dumping the whole serialized payload.

### Example 3 — Skip branch with log but no metric

**Before:**

```ruby
unless feature_variant(event.user_id, request_context).visible?
  Rails.logger.info(message: "#{METRIC_PREFIX}.skipped_feature_disabled", user_id: event.user_id, log_id: "e7c8d2a4f016")
  return
end
```

Gap: when this branch fires (feature flag off), there's a log but no metric. A dashboard counting "how many Chase events did we skip due to gating" has nothing to chart.

**After:**

```ruby
unless feature_variant(event.user_id, request_context).visible?
  ICMetrics.increment("#{METRIC_PREFIX}.skipped", reason: "feature_disabled")
  Rails.logger.info(message: "#{METRIC_PREFIX}.skipped_feature_disabled", user_id: event.user_id, log_id: "e7c8d2a4f016")
  return
end
```

The log gives you searchable per-event detail. The metric gives you an aggregate the on-call dashboard can chart.

## Severity guide for the report

| Severity | Examples |
|---|---|
| **[high]** | PII leak; silent failure on a downstream call to the critical path; missing `log_id` (Cop violation) |
| **[med]** | Missing metric on an error branch; missing METRIC_PREFIX on a class that should have one; downstream error returns nil with no observability |
| **[low]** | Inconsistent log level (info vs warn); missing user_id on an otherwise compliant log; missing `error_source` dimension on an existing error metric |

Don't write findings below **[low]** — they're noise.
