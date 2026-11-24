---
lab6_change:
  id: CHG-20261124T102139Z
  candidate: "itsmlab.local/lab6-candidate:59dff1a6c3ed"
  stable: "ghcr.io/swasik/svcdesk-v2-seeded:2.0.0"
  strategy: flag
  change_type: standard
  risk: low
  rollback_plan: "Disable the feature flag, then restore Caddy weights to 100/0/0; stable stays running."
  started: 2026-11-24T10:21:39Z
  finished: 2026-11-24T10:22:13Z
  outcome: rolled-back
  reason: "canary produced no completed search for 10s at weight 10%; treating absent observations as a hang"
  actions:
    - {at: 2026-11-24T10:21:39Z, action: "set weights 100/0/0 before candidate startup", autonomy: closed-loop}
    - {at: 2026-11-24T10:21:41Z, action: "set feature flag to 0 percent before candidate startup", autonomy: closed-loop}
    - {at: 2026-11-24T10:21:43Z, action: "start svcdesk-canary with the candidate at weight 0", autonomy: closed-loop}
    - {at: 2026-11-24T10:21:43Z, action: "route traffic to candidate with feature flag disabled", autonomy: closed-loop}
    - {at: 2026-11-24T10:21:45Z, action: "set feature flag to 10 percent", autonomy: closed-loop}
    - {at: 2026-11-24T10:21:45Z, action: "read canary counters at weight 10%", autonomy: read-only}
    - {at: 2026-11-24T10:21:50Z, action: "read canary counters at weight 10%", autonomy: read-only}
    - {at: 2026-11-24T10:21:56Z, action: "read canary counters at weight 10%", autonomy: read-only}
    - {at: 2026-11-24T10:22:01Z, action: "read canary counters at weight 10%", autonomy: read-only}
    - {at: 2026-11-24T10:22:06Z, action: "read canary counters at weight 10%", autonomy: read-only}
    - {at: 2026-11-24T10:22:11Z, action: "read canary counters at weight 10%", autonomy: read-only}
    - {at: 2026-11-24T10:22:13Z, action: "set feature flag to 0 percent to roll back", autonomy: closed-loop}
    - {at: 2026-11-24T10:22:13Z, action: "release automation owns rollback and set weights 100/0/0: canary produced no completed search for 10s at weight 10%; treating absent observations as a hang", autonomy: closed-loop}
    - {at: 2026-11-24T10:22:13Z, action: "recovery evidence: stable health endpoint answered successfully after rollback", autonomy: read-only}
---
# Change record

## Why this change type

This is a standard change only within the documented, pre-authorised feature-flag procedure. The candidate starts
dark and is exposed in configured stages, with Prometheus observations and automatic rollback. A new service,
changed SLO or untested procedure needs normal change assessment instead.

## Risk and what bounds it

The flag starts off, then enables candidate behaviour for 10% and 50% of searches. The gate reads only the on
variant and requires the configured observation minimum before passing; a stopped counter is treated as a hang.
Rollback disables the flag and restores stable routing. The runner independently measures the actual blast radius.
