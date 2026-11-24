---
lab6_change:
  id: CHG-20261124T102319Z
  candidate: "itsmlab.local/lab6-candidate:c42933b828e9"
  stable: "ghcr.io/swasik/svcdesk-v2-seeded:2.0.0"
  strategy: flag
  change_type: standard
  risk: low
  rollback_plan: "Disable the feature flag, then restore Caddy weights to 100/0/0; stable stays running."
  started: 2026-11-24T10:23:19Z
  finished: 2026-11-24T10:24:38Z
  outcome: promoted
  reason: "all configured canary steps passed their SLO-derived gates"
  actions:
    - {at: 2026-11-24T10:23:19Z, action: "set weights 100/0/0 before candidate startup", autonomy: closed-loop}
    - {at: 2026-11-24T10:23:21Z, action: "set feature flag to 0 percent before candidate startup", autonomy: closed-loop}
    - {at: 2026-11-24T10:23:23Z, action: "start svcdesk-canary with the candidate at weight 0", autonomy: closed-loop}
    - {at: 2026-11-24T10:23:23Z, action: "route traffic to candidate with feature flag disabled", autonomy: closed-loop}
    - {at: 2026-11-24T10:23:25Z, action: "set feature flag to 10 percent", autonomy: closed-loop}
    - {at: 2026-11-24T10:23:25Z, action: "read canary counters at weight 10%", autonomy: read-only}
    - {at: 2026-11-24T10:23:30Z, action: "read canary counters at weight 10%", autonomy: read-only}
    - {at: 2026-11-24T10:23:36Z, action: "read canary counters at weight 10%", autonomy: read-only}
    - {at: 2026-11-24T10:23:41Z, action: "read canary counters at weight 10%", autonomy: read-only}
    - {at: 2026-11-24T10:23:46Z, action: "read canary counters at weight 10%", autonomy: read-only}
    - {at: 2026-11-24T10:23:51Z, action: "read canary counters at weight 10%", autonomy: read-only}
    - {at: 2026-11-24T10:23:56Z, action: "read canary counters at weight 10%", autonomy: read-only}
    - {at: 2026-11-24T10:24:02Z, action: "read canary counters at weight 10%", autonomy: read-only}
    - {at: 2026-11-24T10:24:07Z, action: "read canary counters at weight 10%", autonomy: read-only}
    - {at: 2026-11-24T10:24:12Z, action: "read canary counters at weight 10%", autonomy: read-only}
    - {at: 2026-11-24T10:24:14Z, action: "set feature flag to 50 percent", autonomy: closed-loop}
    - {at: 2026-11-24T10:24:15Z, action: "read canary counters at weight 50%", autonomy: read-only}
    - {at: 2026-11-24T10:24:20Z, action: "read canary counters at weight 50%", autonomy: read-only}
    - {at: 2026-11-24T10:24:25Z, action: "read canary counters at weight 50%", autonomy: read-only}
    - {at: 2026-11-24T10:24:30Z, action: "read canary counters at weight 50%", autonomy: read-only}
    - {at: 2026-11-24T10:24:35Z, action: "read canary counters at weight 50%", autonomy: read-only}
    - {at: 2026-11-24T10:24:37Z, action: "set feature flag to 100 percent to promote the candidate", autonomy: closed-loop}
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
