---
lab2_edge_cases:
  E1: {rule: R-08, count: 3}
  E2: {rule: R-06, count: 2}
  E3: {rule: R-09, count: 4}
  E4: {rule: R-10, count: 4}
  E5: {rule: R-12, count: 1}
  E6: {rule: R-13, count: 11}
---
<!-- ai-generated: 100% - written by Copilot -->

# Edge cases in the practice event log

This file records the six published traps in the practice log. The counts below equal the values reported by the running service for the practice fixture.

## E1 - clock skew produces a negative lead time

- What the log contains: A production deployment shipped a commit whose timestamp is later than the deployment, which creates a negative lead time when measured as deployment time minus commit time. This is a clock-skew anomaly, and the service records it as a clamped pair.
- What a default definition would have done: A naive implementation would have dropped the pair or reported a negative median value, which would have hidden the real delivery behavior and underestimated lead time.
- Why the rule is defensible: R-08 says negative lead times are clamped to zero and counted, and the service exposes the count as anomalies.negative_lead_time_pairs so the skew is visible instead of silently lost.

## E2 - a revert of a revert

- What the log contains: The log contains revert commits whose `reverts` field points to another revert, so the change identity is inherited transitively rather than treated as a brand-new change.
- What a default definition would have done: A conventional approach would have counted each revert as its own distinct change and would have overreported the change volume in the log.
- Why the rule is defensible: R-06 defines a change by `change_id` and says a revert of a revert resolves to the original change, collapsing the chain into one change and counting the intermediate revert commit as an anomaly.

## E3 - a hotfix that never touched `main`

- What the log contains: Some production deployments carry commits whose `branch` is not `main`, which can happen with hotfixes shipped directly to production.
- What a default definition would have done: A naive implementation would have filtered these commits out because it assumed all production work came from `main`, which would miscount delivery and hide hotfix reality.
- Why the rule is defensible: R-09 explicitly says the branch is irrelevant; any commit carried by a production deployment contributes as normal, and the distinct off-main shas are reported in anomalies.commits_never_on_main.

## E4 - a deployment with zero linked commits

- What the log contains: Several production deployments have an empty `commits` list, which means they are still in scope for deployment counts but do not contribute lead-time pairs.
- What a default definition would have done: A naive implementation would have excluded them, divided by zero, or miscounted the denominator, underestimating deployment volume and instability.
- Why the rule is defensible: R-10 says empty deployments contribute no lead-time pairs but remain counted in frequency, change fail rate and rework rate, and the anomaly count is tracked separately.

## E5 - a deployment that failed and never recovered

- What the log contains: One failed production deployment has no covering resolved incident, so it remains an open failure in the window and is excluded from the recovery-time median.
- What a default definition would have done: A naive implementation would have invented a recovery time or incorrectly treated an unresolved incident as a resolved one.
- Why the rule is defensible: R-12 says the recovery time is computed from the covering incident and open failures are excluded from the median while still counted in counts.open_failures.

## E6 - overlapping incidents

- What the log contains: Some incidents overlap in time, which means their intervals intersect instead of being treated as mutually exclusive.
- What a default definition would have done: A simplistic implementation would merge overlapping incidents or sum wall-clock durations, which changes the mapping of failed deployments to recovery events.
- Why the rule is defensible: R-13 requires per-deployment recovery, and anomalies.overlapping_incident_pairs counts unordered intersecting incident pairs without collapsing them.

## Gaming demonstration

The service improves deployment_frequency_per_day by adding extra production deployments within the practice window while leaving the base work intact. The effect is captured in gaming.json, which names the metric as deployment_frequency_per_day and the rule as R-11. In a real team this incentive would reward shipping more frequent releases even when the underlying work remains the same, which is exactly the pattern Goodhart?s law warns about. The team that optimizes for the metric rather than delivery quality would be rewarded for churn that hides slower real change.
