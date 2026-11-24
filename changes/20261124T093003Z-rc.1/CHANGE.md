---
lab6_change:
  id: CHG-20261124T093003Z
  candidate: "itsmlab.local/lab6-candidate:3199915bc315"
  stable: "ghcr.io/swasik/svcdesk-v2-seeded:2.0.0"
  strategy: flag
  change_type: standard
  risk: low
  rollback_plan: "Restore Caddy weights to 100/0/0 through its admin API; stable stays running."
  started: 2026-11-24T09:30:03Z
  finished: 2026-11-24T09:30:44Z
  outcome: rolled-back
  reason: "canary produced no completed search for 10s at weight 10%; treating absent observations as a hang"
  actions:
    - {at: 2026-11-24T09:30:04Z, action: "set weights 100/0/0 before candidate startup", autonomy: closed-loop}
    - {at: 2026-11-24T09:30:06Z, action: "set feature flag to 0 percent before candidate startup", autonomy: closed-loop}
    - {at: 2026-11-24T09:30:08Z, action: "start svcdesk-canary with the candidate at weight 0", autonomy: closed-loop}
    - {at: 2026-11-24T09:30:08Z, action: "route traffic to candidate with feature flag disabled", autonomy: closed-loop}
    - {at: 2026-11-24T09:30:10Z, action: "set feature flag to 10 percent", autonomy: closed-loop}
    - {at: 2026-11-24T09:30:10Z, action: "read canary counters at weight 10%", autonomy: read-only}
    - {at: 2026-11-24T09:30:15Z, action: "read canary counters at weight 10%", autonomy: read-only}
    - {at: 2026-11-24T09:30:21Z, action: "read canary counters at weight 10%", autonomy: read-only}
    - {at: 2026-11-24T09:30:26Z, action: "read canary counters at weight 10%", autonomy: read-only}
    - {at: 2026-11-24T09:30:31Z, action: "read canary counters at weight 10%", autonomy: read-only}
    - {at: 2026-11-24T09:30:36Z, action: "read canary counters at weight 10%", autonomy: read-only}
    - {at: 2026-11-24T09:30:41Z, action: "read canary counters at weight 10%", autonomy: read-only}
    - {at: 2026-11-24T09:30:44Z, action: "set feature flag to 0 percent to roll back", autonomy: closed-loop}
    - {at: 2026-11-24T09:30:44Z, action: "release automation owns rollback and set weights 100/0/0: canary produced no completed search for 10s at weight 10%; treating absent observations as a hang", autonomy: closed-loop}
    - {at: 2026-11-24T09:30:44Z, action: "recovery evidence: stable health endpoint answered successfully after rollback", autonomy: read-only}
---
# Change record

## Why this change type

This is a standard change only within the documented, pre-authorised release procedure: nginx first mirrors live
searches to the candidate while serving users from the stable build, then a weighted canary begins only after the
shadow gate passes. Both phases read the candidate's SLIs from Prometheus, and promotion is automatic only after
the configured observation minimums and SLO-derived limits pass. An unattended release is not automatically low
risk; a new service, changed SLO, untested gate, or candidate outside this procedure needs normal change
assessment instead. The gate's decisions are closed-loop; its Prometheus observations are read-only.

## Risk and what bounds it

Users receive stable answers throughout shadowing: nginx mirrors each search to the candidate and discards its
response. Before routing users to the candidate, the gate requires at least 200 stable-track searches to have
passed through the shadow proxy and 200 completed candidate observations to evaluate error and latency shares.
A hang stops producing completed candidate observations; the 10-second no-progress watchdog rolls back after the
proxy has continued to serve stable traffic. Missing or inconsistent monitoring data also fails closed. Only after
shadow passes does the 10% weighted step begin; the 50% step follows only after that passes. Weighted steps reject
a bad-share above the configured 20% ceiling after five bad observations and require at least 150 requests before
passing. Rollback restores 100/0/0 through the admin API without stopping stable. The actual blast radius is
measured by the runner for each run, not asserted here.
