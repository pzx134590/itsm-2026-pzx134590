---
lab3_genai_diff:
  instrumentation: "opentelemetry-instrumentation-genai-openai==1.2b0; OpenAI SDK 3.19.2; opentelemetry-sdk==1.45.0; opentelemetry-exporter-otlp-json-file==0.66b0"
  spec_ref: "semantic-conventions-genai@e57c543b4889619eb2a05702471937db5119165d"
  attributes:
    - {name: gen_ai.operation.name, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.provider.name, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.request.model, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.request.temperature, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.response.finish_reasons, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.response.model, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.response.id, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.usage.input_tokens, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.usage.output_tokens, emitted: true, in_spec: true, stability: development}
---
<!-- ai-generated: 100% - AI recorded and compared the emitted spans with the pinned GenAI semantic conventions registry -->

# What the library emits, against the spec

The capture uses `OpenAIInstrumentor` with the pinned instrumentation and SDK versions. To avoid sending data to an external provider or requiring an API key, the OpenAI SDK request was sent to a local OpenAI-compatible test responder that returned a chat-completion-shaped response with usage data. The instrumentation emitted nine `gen_ai.*` attributes; all nine are defined in the selected registry and have development stability. The request and response model, operation, provider, temperature, finish reason, response id, and token counts are therefore directly inspectable in the OTLP JSON. This validates the instrumentation and exporter path, but it is not evidence of inference by a hosted or local language model.

For a dashboard, the model, operation and provider attributes can group spans by request type and configured backend; response finish reasons and token counts can help explain behavior and cost. They are experimental development conventions, so dashboards should tolerate missing attributes and be reviewed when the conventions or instrumentation version changes.
