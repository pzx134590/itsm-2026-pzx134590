<!-- ai-generated: 100% - drafted from local k8sgpt output and the recorded ReAct diagnostic -->
# k8sgpt and agentic ReAct comparison

## Test setup

The Kubernetes track was exercised on the existing `kind-svcdesk-lab3` cluster to stay within the lab's memory budget. A disposable `lab4-k8sgpt-sim` namespace contained one deliberately broken Deployment referencing `invalid.invalid/lab4/broken:0.1`. The pod reached `ErrImagePull`; its events recorded a DNS lookup failure for the deliberately invalid registry hostname. This is a controlled diagnostic exercise, not the OpenTelemetry Demo incident or its ground truth. The namespace was deleted after evidence collection.

`k8sgpt` v0.4.38 analyzed the namespace without an AI backend and reported two findings: the Deployment had zero available replicas, and the Pod could not resolve the image reference. The raw JSON is in [k8sgpt-analyze.json](./k8sgpt-analyze.json).

## Agentic ReAct trace

The local `qwen3:1.7b` model was given the initial observation: the Pod was `ErrImagePull` and the Deployment had zero available replicas. It chose a read-only `kubectl describe pod` query to investigate the container state and events.

The query showed `Waiting / ErrImagePull`, the exact image reference, and a failed DNS lookup for `invalid.invalid`, followed by `ImagePullBackOff`. Given that evidence, the model reported an invalid image reference as the immediate failure mechanism and selected `kubectl get events -n lab4-k8sgpt-sim --sort-by=.lastTimestamp` as its follow-up. The event query confirmed repeated pull failures and backoff. It did not justify a broader claim about the original service incident.

## Difference

The rule-based analyzers were fast and deterministic: they surfaced both the unavailable Deployment and the Pod's image-pull error in a single pass. The ReAct loop selected a follow-up query based on the first observation, then connected the Pod status to the event's DNS error. That flexibility is useful when the first symptom is ambiguous, but depends on the model choosing a relevant query and interpreting its output faithfully. In this test both approaches agreed on the immediate fault; k8sgpt reported the controller- and Pod-level symptoms separately, while ReAct used the additional query to explain the failure mechanism. Neither result establishes a cause for the separate OpenTelemetry Demo incident.
