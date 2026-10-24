---
lab4_postmortem:
  ticket: "1224ad8d-06a8-4ae3-865a-da2015a4ddb5"
  detecting_alert: ShopCheckoutErrors
  onset: 2026-10-12T07:05:45Z
  detection: 2026-10-12T07:09:19Z
  acknowledgement: 2026-10-12T07:10:07Z
  recovery: 2026-10-12T07:12:19Z
  mttd_seconds: 214
  mtta_seconds: 48
  mttr_seconds: 394
  identified_flags: [productCatalogFailure, adManualGc]
---
<!-- ai-generated: 75% - AI drafted from the assigned transcript and snapshot; the on-call re-ran PromQL and preserved the source ticket unchanged -->

# Postmortem: Checkout errors during the recorded shop incident

## Date

The incident occurred on 2026-10-12 in the assigned `lab4-rec-3` recording; this postmortem was written after re-running the recording's queries.

## Authors

The on-call responder prepared this report and checked the recorded investigator's claims against the assigned Prometheus snapshot.

## Status

The `ShopCheckoutErrors` alert recovered at 07:12:19Z. The supplied ticket export remains acknowledged, with no resolution or closure timestamp; it is preserved unchanged as required for this recording. Follow-up problem work remains open.

## Summary

Checkout server errors crossed the P1 symptom threshold. Matching failed `GetProduct` spans at checkout and ProductCatalog point to a downstream error path; an independent ad latency spike was also visible. The snapshot does not prove the underlying code-level trigger or a remediation action.

## Impact

At 07:09:19Z, checkout server-span errors were about 0.00673/s out of 0.13174 server spans/s, a 5.11% error ratio. The measured PromQL was:

```promql
(sum(rate(traces_span_metrics_calls_total{service_name="checkout",span_kind="SPAN_KIND_SERVER",status_code="STATUS_CODE_ERROR"}[5m])) or vector(0))
/
sum(rate(traces_span_metrics_calls_total{service_name="checkout",span_kind="SPAN_KIND_SERVER"}[5m]))
```

At the healthy comparison time 07:00:45Z, the same query returned 0% (0 errors/s). The matching ProductCatalog server-span `GetProduct` error rate was about 0.104/s at detection and absent at baseline:

```promql
sum(rate(traces_span_metrics_calls_total{service_name="product-catalog",span_kind="SPAN_KIND_SERVER",span_name="oteldemo.ProductCatalogService/GetProduct",status_code="STATUS_CODE_ERROR"}[5m]))
```

Ad server-span p99 latency rose from 4.86 ms at baseline to about 908 ms at detection:

```promql
histogram_quantile(0.99,sum by(le)(rate(traces_span_metrics_duration_milliseconds_bucket{service_name="ad",span_kind="SPAN_KIND_SERVER"}[5m])))
```

Checkout p99 stayed about 49.6 ms at detection. Users were affected by failed checkout requests, not by elevated checkout latency in this snapshot.

## Root Causes

The clearest failure path was ProductCatalog `GetProduct`: failed server spans in ProductCatalog coincided with failed checkout client spans for that RPC and failed checkout `PlaceOrder` spans. This is consistent with the pool's `productCatalogFailure` signature, but the snapshot cannot establish the exact application-level trigger or prove every failed order followed this path. Separately, ad p99 increased by nearly two orders of magnitude without an observed ad server-error rate, matching the `adManualGc` latency-spike signature. These are evidence-based fault identifications; neither implicates an individual responder.

## Trigger

The incident calculator places the seeded-fault onset at 07:05:45Z. The error alert fired later, at 07:09:19Z; the on-call did not know the specific failing flags from the P1 page alone.

## Resolution

The P1 alert's recorded firing run ended at 07:12:19Z. The assigned files do not record which flags were switched off, who switched them, or in what order. The `seeded_fault_active` metric was still 1 at the recovery marker and remained active in a later sample, so alert recovery is not evidence that the injected conditions had all been removed. The supplied ticket is still acknowledged. The actions that restored the alert and closed neither the incident ticket nor the problem record cannot be inferred from this recording.

## Detection

`ShopCheckoutErrors` first fired at 07:09:19Z, 214 seconds after the onset (MTTD). To quantify the checkout symptom at detection, the on-call used the five-minute server-span error ratio in Impact; it was 5.11%, against 0% at the healthy comparison. Prometheus stores alert samples on a 15-second grid, so the first sampled firing value is 07:09:30Z even though the incident calculator derives the transition at 07:09:19Z. The P1 ticket was created at 07:09:37Z and acknowledged at 07:10:07Z, 48 seconds after detection (MTTA). Without the page, the on-call would have needed to notice failed orders in the checkout dashboard or trace search; the alert did not identify ProductCatalog as the likely downstream failure path.

## Action Items

The ProductCatalog owner owns **ITSM-42**: add a regression test for failed `GetProduct` responses, preserve the failing request context in traces, and alert on the dependency error rate so the next responder can distinguish a downstream failure from the checkout symptom.

The incident commander owns **ITSM-43**: update the incident checklist to record who changes each flag, verify a recovery query, resolve and close the incident ticket after service recovery, and keep the separate problem record open until the cause and workaround are verified.

| Action Item | Type | Owner | Bug |
|---|---|---|---|
| Add a ProductCatalog `GetProduct` failure regression test and dependency-specific error alert. | prevent | ProductCatalog owner | ITSM-42 |
| Record rollback ownership and recovery evidence; close the incident ticket after recovery while keeping root-cause work open. | process | Incident commander | ITSM-43 |

## Lessons Learned

### What went well

The P1 alert identified an error symptom, and the snapshot retained enough trace labels to connect failed checkout calls with ProductCatalog `GetProduct`.

### What went wrong

The supplied ticket was not resolved or closed in the recorded export, and alert recovery occurred while `seeded_fault_active` was still 1. The record therefore cannot establish which action restored the symptom or that the injected condition had ended.

### Where we got lucky

The alert recovered before the snapshot ended, leaving a post-recovery window for checking whether the injected condition and alert state agreed. That check exposed that alert recovery alone was not proof of full fault removal.

## Timeline

- 07:05:45Z — **Onset:** `itsmlab incident 4` places the start of the seeded fault here. No P1 page had fired yet.
- 07:09:19Z — **Detection:** `ShopCheckoutErrors` transitioned to firing. The checkout server-span error ratio query in Impact measured 5.11%; the alert named the checkout symptom, not its cause.
- 07:09:37Z — The supplied P1 ticket was created. The responder had a record of the checkout incident, but no confirmed root cause.
- 07:10:07Z — **Acknowledgement:** the ticket was acknowledged, 48 seconds after detection. The on-call had the page and an elevated checkout error ratio; the matching ProductCatalog path still required investigation.
- During the recorded investigation — Ledger entry **H1** in `ai-rca-eval.json` tested PlaceOrder server errors with `(sum(increase(traces_span_metrics_calls_total{service_name="checkout",status_code="STATUS_CODE_ERROR",span_kind="SPAN_KIND_SERVER",span_name="oteldemo.CheckoutService/PlaceOrder"}[5m])) or vector(0)) > 0`. It was false at 07:00:45Z and true at 07:09:19Z (about 2.02 calls over five minutes). This supports the checkout symptom but not its underlying cause.
- During the recorded investigation — Ledger entry **H2** tested checkout's failed `ProductCatalogService/GetProduct` client spans with `(sum(rate(traces_span_metrics_calls_total{service_name="checkout",status_code="STATUS_CODE_ERROR",span_kind="SPAN_KIND_CLIENT",span_name="oteldemo.ProductCatalogService/GetProduct"}[5m])) or vector(0)) > 0`. It was false at baseline and true at detection; the matching ProductCatalog server error rate was about 0.104/s. The query supports a downstream failure path, not causal certainty.
- During the recorded investigation — Ledger entry **H3** tested checkout's `PaymentService/Charge` errors with `(sum(rate(traces_span_metrics_calls_total{service_name="checkout",status_code="STATUS_CODE_ERROR",span_name="oteldemo.PaymentService/Charge"}[5m])) or vector(0)) > 0`. It was false at detection; payment failure was unsupported.
- During the recorded investigation — Ledger entry **H4** tested `sum(rate(traces_span_metrics_calls_total{status_code="STATUS_CODE_ERROR"}[5m])) > 1`. It was false at baseline (about 0.192 errors/s) and true at detection (about 1.054 errors/s). This supports an error spike, not the transcript's proposed high-load cause; the original `query_range(...)` tool call was not PromQL.
- 07:12:19Z — **Recovery:** the detecting alert's firing run ended. The fault-active metric still read 1, so the responder could not infer that all injected conditions had been removed from alert recovery alone.
- 07:14:49Z — The assigned snapshot ended after the additional recovery observation. The provided ticket export remained acknowledged with no later resolution or closure event.

## Supporting information

The original assigned artifacts are preserved unchanged: `incident/tsdb-snapshot.tar.gz`, `incident/ticket.json`, and `ai-rca/transcript-recorded.md`. The transcript with the re-executed PromQL is `ai-rca/transcript.md`; the four recorded-agent hypotheses and their verdicts are in `ai-rca-eval.json`. The independent investigation is recorded in `ai-rca/transcript-2.md` and scored in `ai-rca-eval-2.json`. `itsmlab incident 4` recomputed onset 07:05:45Z, detection 07:09:19Z, acknowledgement 07:10:07Z, recovery 07:12:19Z, MTTD 214 s, MTTA 48 s and MTTR 394 s.

## Problem record

- Incident record: P1 ticket `1224ad8d-06a8-4ae3-865a-da2015a4ddb5`, created 07:09:37Z and acknowledged 07:10:07Z; the supplied export has no resolution or closure timestamp.
- Root cause: ProductCatalog `GetProduct` server errors are the leading evidenced failure path, but the recording does not identify the application-level trigger.
- Known error: Checkout `PlaceOrder` can fail when its downstream ProductCatalog `GetProduct` call returns an error; ad latency was also abnormal during the same incident window.
- Workaround: No verified workaround is recorded; investigate the ProductCatalog errors and confirm the fault is removed before closing incident work.
