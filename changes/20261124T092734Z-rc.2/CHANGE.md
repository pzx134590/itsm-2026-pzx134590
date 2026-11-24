---
lab6_change:
  id: CHG-20261124T092734Z
  candidate: "itsmlab.local/lab6-candidate:43902aef9de9"
  stable: "ghcr.io/swasik/svcdesk-v2-seeded:2.0.0"
  strategy: flag
  change_type: standard
  risk: low
  rollback_plan: "Restore Caddy weights to 100/0/0 through its admin API; stable stays running."
  started: 2026-11-24T09:27:34Z
  finished: 2026-11-24T09:28:53Z
  outcome: promoted
  reason: "all configured canary steps passed their SLO-derived gates"
  actions:
    - {at: 2026-11-24T09:27:35Z, action: "set weights 100/0/0 before candidate startup", autonomy: closed-loop}
    - {at: 2026-11-24T09:27:37Z, action: "set feature flag to 0 percent before candidate startup", autonomy: closed-loop}
    - {at: 2026-11-24T09:27:38Z, action: "start svcdesk-canary with the candidate at weight 0", autonomy: closed-loop}
    - {at: 2026-11-24T09:27:38Z, action: "route traffic to candidate with feature flag disabled", autonomy: closed-loop}
    - {at: 2026-11-24T09:27:40Z, action: "set feature flag to 10 percent", autonomy: closed-loop}
    - {at: 2026-11-24T09:27:41Z, action: "read canary counters at weight 10%", autonomy: read-only}
    - {at: 2026-11-24T09:27:46Z, action: "read canary counters at weight 10%", autonomy: read-only}
    - {at: 2026-11-24T09:27:51Z, action: "read canary counters at weight 10%", autonomy: read-only}
    - {at: 2026-11-24T09:27:56Z, action: "read canary counters at weight 10%", autonomy: read-only}
    - {at: 2026-11-24T09:28:01Z, action: "read canary counters at weight 10%", autonomy: read-only}
    - {at: 2026-11-24T09:28:07Z, action: "read canary counters at weight 10%", autonomy: read-only}
    - {at: 2026-11-24T09:28:12Z, action: "read canary counters at weight 10%", autonomy: read-only}
    - {at: 2026-11-24T09:28:17Z, action: "read canary counters at weight 10%", autonomy: read-only}
    - {at: 2026-11-24T09:28:22Z, action: "read canary counters at weight 10%", autonomy: read-only}
    - {at: 2026-11-24T09:28:27Z, action: "read canary counters at weight 10%", autonomy: read-only}
    - {at: 2026-11-24T09:28:30Z, action: "set feature flag to 50 percent", autonomy: closed-loop}
    - {at: 2026-11-24T09:28:30Z, action: "read canary counters at weight 50%", autonomy: read-only}
    - {at: 2026-11-24T09:28:35Z, action: "read canary counters at weight 50%", autonomy: read-only}
    - {at: 2026-11-24T09:28:40Z, action: "read canary counters at weight 50%", autonomy: read-only}
    - {at: 2026-11-24T09:28:45Z, action: "read canary counters at weight 50%", autonomy: read-only}
    - {at: 2026-11-24T09:28:51Z, action: "read canary counters at weight 50%", autonomy: read-only}
    - {at: 2026-11-24T09:28:53Z, action: "set feature flag to 100 percent to promote the candidate", autonomy: closed-loop}
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
