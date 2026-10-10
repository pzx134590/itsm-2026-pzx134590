---
lab3_first_draft:
  source: ai
  tool: "Copilot assistant in VS Code, GPT-6-Luna, 10 October 2026"
  ladder: [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
  verdict: refuted
  evidence: {p99_seconds: 0.187, bucket: [0.1, 0.25], relative_width: 0.802}
lab3_flawed_ladder:
  verdict: refuted
  evidence: {p99_seconds: 0.187, bucket: [0.04, 0.5], relative_width: 2.460}
---
<!-- ai-generated: 100% - assistant drafted the exchange and verdict prose from the measured load results -->

# The assistant's first draft, and two verdicts

## Prompt

For GET /kb/search in a Prometheus-instrumented service, propose histogram bucket boundaries in seconds and one multiwindow alert rule. I have not measured my service's latency distribution yet, so state your assumptions and explain why the ladder is only a first draft that must be checked against a measured p99. Use the metric http_server_request_duration_seconds and route label http_route="/kb/search".

## Answer

Assuming I do not yet know the service's latency distribution, I would start with a conventional general-purpose ladder, in seconds:

[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]

This is only a starting point, not a claim that the buckets resolve your p99. Once you measure the p99, find its bucket (lo, hi] and calculate (hi - lo) / p99. If that is greater than 0.20, or if nearby plausible p99 values fall into a much wider bucket, redesign the ladder around the measured slow mode. Choose the latency SLI threshold from one of the final finite bucket boundaries.

For an illustrative availability objective of 99%, a fast multiwindow burn-rate alert could require the 1-hour and 5-minute error ratios to both exceed 14.4 times the allowed error ratio:

```yaml
- alert: KbSearchErrorsBurnFast
  expr: |
    (
      sum(rate(http_server_request_duration_seconds_count{
        job="svcdesk",
        http_route="/kb/search",
        http_response_status_code=~"5.."
      }[1h]))
      /
      sum(rate(http_server_request_duration_seconds_count{
        job="svcdesk",
        http_route="/kb/search"
      }[1h]))
    ) > 14.4 * (1 - 0.99)
    and
    (
      sum(rate(http_server_request_duration_seconds_count{
        job="svcdesk",
        http_route="/kb/search",
        http_response_status_code=~"5.."
      }[5m]))
      /
      sum(rate(http_server_request_duration_seconds_count{
        job="svcdesk",
        http_route="/kb/search"
      }[5m]))
    ) > 14.4 * (1 - 0.99)
  for: 2m
  labels:
    service: svcdesk
    slo: availability
    severity: P1
```

The objective and alert threshold are illustrative assumptions; use the objective you actually choose in your SLO. This rule is one fast-burn example, not a complete multi-burn-rate alert set. Validate the final thresholds, windows, and firing/reset behavior against the declared SLO and tests.

## Verdict on the draft ladder

The measured p99 was 0.187 s, in the draft ladder's (0.1, 0.25] bucket. Its width is (0.25 - 0.1) / 0.187 = 0.802, or 80.2% of p99, far above the 20% resolution limit. `histogram_quantile` interpolates within that broad bucket and cannot establish the actual p99 more precisely than the bucket permits. In a separate run using the final custom ladder, the checker reported its histogram p99 as 0.1919 s; that result does not improve the first-draft ladder's resolution. The ladder is refuted. The same bucket contains 0.95q, q and 1.05q, so the verdict is not close to the decision boundary.

## The draft alert rule

I kept the route filter, the explicit bad-request ratio, and the conjunction of long and short windows: together they scope the signal to knowledge-base searches and avoid paging on a brief spike alone. The example's 99% objective and one 14.4 burn rate were assumptions, not final policy; the final rules must use the objectives and multiple burn rates declared in `slo.md`, and must pass the checker’s timing, reset, and mutation tests.

## Verdict on the instructor's flawed ladder

The same measured p99, 0.187 s, lands in the instructor ladder's (0.04, 0.5] bucket. Its width is (0.5 - 0.04) / 0.187 = 2.460, or 246.0% of p99. The instructor ladder spends many boundaries below 40 ms, then has a 460 ms gap across the slow mode; `histogram_quantile` can only interpolate within that very broad interval. The verdict is refuted.
