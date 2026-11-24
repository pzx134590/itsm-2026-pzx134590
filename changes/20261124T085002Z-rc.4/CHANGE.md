---
lab6_change:
  id: CHG-20261124T085002Z
  candidate: "itsmlab.local/lab6-candidate:621f894748a1"
  stable: "ghcr.io/swasik/svcdesk-v2-seeded:2.0.0"
  strategy: canary
  change_type: standard
  risk: low
  rollback_plan: "Restore Caddy weights to 100/0/0 through its admin API; stable stays running."
  started: 2026-11-24T08:50:02Z
  finished: 2026-11-24T08:50:19Z
  outcome: rolled-back
  reason: "shadow availability: 110 of 254 candidate searches failed against a 0.2 bad-share limit"
  actions:
    - {at: 2026-11-24T08:50:03Z, action: "set weights 100/0/0 before candidate startup", autonomy: closed-loop}
    - {at: 2026-11-24T08:50:05Z, action: "start svcdesk-canary with the candidate at weight 0", autonomy: closed-loop}
    - {at: 2026-11-24T08:50:05Z, action: "enable nginx shadow at weights 0/0/100; users continue to receive stable responses", autonomy: closed-loop}
    - {at: 2026-11-24T08:50:05Z, action: "read candidate shadow counters from Prometheus", autonomy: read-only}
    - {at: 2026-11-24T08:50:11Z, action: "read candidate shadow counters from Prometheus", autonomy: read-only}
    - {at: 2026-11-24T08:50:16Z, action: "read candidate shadow counters from Prometheus", autonomy: read-only}
    - {at: 2026-11-24T08:50:19Z, action: "set weights 100/0/0 to roll back: shadow availability: 110 of 254 candidate searches failed against a 0.2 bad-share limit", autonomy: closed-loop}
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
