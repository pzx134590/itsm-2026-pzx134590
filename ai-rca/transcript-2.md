<!-- ai-generated: 100% - recorded from an independent read-only investigator and re-executed queries on the assigned snapshot -->
# Independent investigation of lab4-rec-3

Investigator: independent Copilot SDK subagent (the host does not expose the backing model name). The investigator was given read-only access to the assigned Prometheus snapshot at `http://127.0.0.1:19091` and was asked not to read the course-recorded transcript, repository scorecards or other recording folders. Evaluation points were the five-minute pre-onset baseline, 2026-10-12T07:00:45Z, the P1 page at 07:09:19Z, acknowledgement at 07:10:07Z and alert recovery at 07:12:19Z.

## H1 — the checkout-page period brought a user-visible HTTP 500 burst

```promql
(sum(increase(http_server_request_duration_seconds_count{service_name="frontend",http_response_status_code="500"}[2m])) or vector(0)) > 0
```

The comparison was false at baseline and true at page time: the two-minute increase was 16 HTTP 500 responses. The frontend HTTP metric has no `http_route` label, so the investigator could not attribute all those failures specifically to checkout.

## H2 — ProductCatalog errors explain the checkout failures

```promql
(sum(increase(rpc_server_call_duration_seconds_count{service_name="product-catalog",rpc_method="oteldemo.ProductCatalogService/GetProduct",rpc_response_status_code="INTERNAL"}[2m])) or vector(0)) > 0
```

The comparison was false at baseline and true at page time: the two-minute increase was 12 ProductCatalog `INTERNAL` responses. A separate checkout-client query did not show an increase in the same short windows, so the server-side errors establish a failing service symptom but not that ProductCatalog caused every checkout or frontend error.

## H3 — payment failure or service latency drove the incident

```promql
(sum(increase(rpc_client_call_duration_seconds_count{service_name="checkout",rpc_method="oteldemo.PaymentService/Charge",rpc_response_status_code!="OK"}[2m])) or vector(0)) > 0
```

The payment-error comparison was false at both baseline and page time. Checkout's PaymentService `Charge` p95 was 4.75 ms at both points; the checked checkout and ProductCatalog p95 values likewise showed no rise. This does not support payment failure or anomalous latency as the incident explanation.

## Additional observations and limits

The investigator observed the alert-state transitions in the snapshot: five alerts were pending at 07:09:19Z, three alerts were firing at 07:10:07Z, and five were firing at 07:12:19Z. The alert's firing samples cleared later than the incident calculator's recovery marker. Error counters in short windows had returned to zero at the recovery marker, but firing alerts remained; therefore the first error-free window and the end of an alert run are different signals. All queries are symptoms with bounded labels and windows; none proves causal direction or the specific seeded flag.
