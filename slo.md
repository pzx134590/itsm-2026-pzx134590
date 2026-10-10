---
lab3_slo:
  service: svcdesk
  route: /kb/search
  window: 28d
  slis:
    availability:
      objective: 0.99
      good: 'sum(rate(http_server_request_duration_seconds_count{job="svcdesk", http_route="/kb/search", http_response_status_code!~"5.."}[5m]))'
      valid: 'sum(rate(http_server_request_duration_seconds_count{job="svcdesk", http_route="/kb/search"}[5m]))'
      error_budget: {fraction: 0.01, minutes: 403.2}
    latency:
      objective: 0.95
      threshold_seconds: 0.1
      good: 'sum(rate(http_server_request_duration_seconds_bucket{job="svcdesk", http_route="/kb/search", le="0.1"}[5m]))'
      valid: 'sum(rate(http_server_request_duration_seconds_count{job="svcdesk", http_route="/kb/search"}[5m]))'
      error_budget: {fraction: 0.05, minutes: 2016}
  alerts:
    - {alert: KbSearchErrorsBurnFast, sli: availability, burn_rate: 14.4, long_window: 1h, short_window: 5m}
    - {alert: KbSearchErrorsBurnSlow, sli: availability, burn_rate: 6, long_window: 2h, short_window: 20m}
---
<!-- ai-generated: 100% - AI drafted SLO values and rationale from measured Lab 3 latency data -->

# SLO for `GET /kb/search`

## Availability

The availability SLI is the share of `/kb/search` responses that are not 5xx; client validation errors do not count against availability because they are rejected inputs, not service failures. The objective is 99% over 28 days, with an error budget of 1% or 403.2 minutes. `kb-index` has its own small failure probability and is outside svcdesk's control, so 99% leaves operational room for those upstream errors while still limiting prolonged outages.

## Latency

The latency SLI is the share of valid `/kb/search` requests completed within 100 ms. Its objective is 95% over 28 days, with a 5% error budget (2,016 minutes). In my open-loop measurement, p50 was 26.6 ms, p95 was 58.3 ms, p99 was 187.0 ms, and p99.9 was 222.6 ms. The 100 ms threshold is above the measured p95 but below the p99 slow mode, so it distinguishes ordinary searches from the slow tail instead of treating the whole distribution as equally good. It is also an explicit histogram boundary, so the SLI counts requests rather than interpolating.

## Alerts

| alert | SLI | burn rate | long / short window | budget spent when it fires | severity: page or chat |
|---|---|---:|---|---|---|
| KbSearchErrorsBurnFast | availability | 14.4 | 1h / 5m | about 2.14% over the 1h long window | P1 page |
| KbSearchErrorsBurnSlow | availability | 6 | 2h / 20m | about 1.79% over the 2h long window | P2 chat |

The fast alert pages because a sustained 14.4x burn would exhaust the 28-day budget in about 46.7 hours, making a delay until morning costly to users. The slower alert goes to chat: at 6x burn the budget lasts about 112 hours, so an immediate night-time interruption is less valuable than a prompt daytime investigation.

## Buckets

The ladder is `[0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.16, 0.17, 0.18, 0.19, 0.20, 0.21, 0.25, 0.5, 1, 2.5, 5, 10]` seconds. The measured p99 of 187 ms falls in `(0.18, 0.19]`, a 10 ms bucket that is 5.3% of p99. The ladder resolves the full ±10% band from 168.3 ms to 205.7 ms: each bucket in that band is 10 ms wide, less than 20% of the band's lower end. The denser boundaries are spent around the measured slow mode; the remaining boundaries retain coverage of fast requests and longer outliers. This measured ladder is more informative for this login's profile than either the assistant's broad draft bucket or the instructor's 460 ms gap.
