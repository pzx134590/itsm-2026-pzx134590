---
lab6_blast_radius:
  postmortem_action: {bug: ITSM-43, commit: 8c6e238da1c22701d75bff33877cca4046370816}
---
<!-- ai-generated: 100% - AI wrote this analysis from the accepted SLO and saved practice measurements -->

# Blast radius

## Gate

The accepted Lab 3 student SLO uses a 28-day window, 99% availability and 95% of searches within 0.1 s.
The release uses burn 20 for availability and burn 4 for latency: 20 x (1 - 0.99) = 0.20 and
4 x (1 - 0.95) = 0.20. Both limits are 20% bad searches, below the minimum 30% sabotage rate.
The separate 60-second baseline sample at 40 searches/s had 7 HTTP 502s among 2,399 HTTP responses,
p95 43.4 ms and p99 178.6 ms; six further requests were aborted at the end of the run. The four most
recent saved warm-ups had 0 to 3 stable 5xx among approximately 1,200 requests each. These samples do not prove
the 28-day objective, but the latency measurements are consistent with retaining the student baseline.

The shadow phase routes users to stable and mirrors their searches to canary. It waits for at least 200
stable searches and 200 completed canary searches before evaluating the 20% shares; at 40 searches/s
this is at least five seconds plus scrape and polling delays. Unlike the weighted phase it uses only one
final share decision, limiting repeated-look false alarms. During a weighted step the gate looks every 5 s
and can reject from 20 requests and five bad observations; repeated looks increase the chance of a false
rollback, even though the honest floor is much lower than 20%. After disabling shadow the script allows
10 seconds for in-flight copies to finish and appear in a scrape before taking the weighted baseline.
At 10% the expected rate is four searches/s:
150 completed searches take about 37.5 s, and the step lasts at least 45 s. The next 50% step lasts at
least 20 s and also needs 150 searches. Counter samples in each look share a Prometheus timestamp.

A missing monitoring response, reset or inconsistent counter fails closed. Zero observed errors alone is
not proof of health: after ingress has continued, ten seconds without completed candidate searches triggers
rollback. This catches the hang, whose unfinished searches never increment its histogram. A genuine outage
in monitoring can therefore cause a safe rollback rather than an unsubstantiated promotion.

For the optional flag strategy, the candidate first serves traffic with `svcdesk-2-1` off, then the flag
ramps through 10% and 50%; only the `on` variant enters the gate. The same 20% SLI limits and no-progress
watchdog apply. In the saved practice flag runs the honest candidate was promoted with radius 0, and the
hang was rolled back with radius 91. Unlike shadow, this variant exposes a small portion of user traffic
to the candidate, so the 150 Core/flag ceiling rather than the shadow ceiling of 5 applies.

## Blast radius

The table gives the most recent saved practice run for each slot, from the runner's user-observed records.
The first three bad builds received no user traffic, while the honest build went on to weighted canary.

| Slot | Behaviour | Decision | Measured blast radius | Script time |
|---|---|---|---:|---:|
| rc.1 | hang | rolled back | 1 | 23.9 s |
| rc.2 | honest | promoted | 2 | 102.5 s |
| rc.3 | slow | rolled back | 0 | 22.7 s |
| rc.4 | errors | rolled back | 0 | 16.8 s |

For bad builds the lecture approximation `c + R x w x q x D` describes failures in user traffic.
Here R = 40/s and the candidate's user-facing weight w = 0 throughout the rejected shadow phase, so the
candidate-caused term and user-visible evidence cost c are both zero regardless of q and detection delay D.
This predicts zero candidate failures, not zero unrelated proxy failures: rc.1 had one headerless connection
failure during the run, giving a measured radius of 1. rc.3 and rc.4 measured zero. These observations
do not establish a bound for every future seed or machine. The honest rc.2's radius of 2 consisted of one
headerless failure and four candidate 5xx minus the runner's estimated stable floor of three.
If a bad build escaped shadow, w = 0.1 in the first step, rising to 0.5 in the second: the delay term would
grow proportionally, and a long window or slow response could push the result above the 150 Core ceiling.
The stricter shadow target is at most 5 per bad run.

## Change classification

The record calls this a standard, low-risk change only within the documented and pre-authorised course
procedure. That classification depends on a tested release pattern, a continuously running stable build,
shadow isolation, measured SLO-derived gates and automatic rollback; it is not a blanket claim that any
unattended release is safe. A changed dependency profile, SLO, routing mechanism or untested candidate
requires reassessment and potentially a normal change with approval before execution.

Starting the candidate, changing weights, rolling back and promoting are closed-loop actions because the
automation chooses and executes them. Reading Prometheus and checking stable health are read-only actions.
No person is asked to approve during the run. In a real service an owner should approve the procedure and
its thresholds in advance, review failed recovery evidence, and decide incident closure independently.

## Postmortem action

Lab 4 action ITSM-43 asks the incident commander to record rollback ownership and recovery evidence, close
the incident ticket after recovery, and keep root-cause work open. Commit
`8c6e238da1c22701d75bff33877cca4046370816` makes the release automation explicitly record its ownership
of rollback and records the result of a stable health check after routing is restored. In the latest
rc.1 practice record, the weight restoration and successful health check appear as separate closed-loop
and read-only actions. The runner's subsequent stable answers provide additional independent evidence.
This is only a partial implementation: `/health` is not proof that search and its dependency are healthy,
and this script neither closes an incident ticket nor maintains a separate problem record. Those decisions
remain with the incident commander after checking the actual user-facing service.
