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

The capture uses `OpenAIInstrumentor` with the pinned instrumentation and SDK versions. The OpenAI SDK sent a chat completion request to the local Ollama OpenAI-compatible API at `127.0.0.1:11434`, which ran the `qwen3:1.7b` model; no external provider was contacted. The instrumentation emitted nine `gen_ai.*` attributes, all defined in the selected registry with development stability. The OTLP JSON records the request and response model, operation, provider, temperature, finish reason, response id, and token counts, along with the local server address and port. The response and token usage came from Ollama's actual model inference, not a test responder.

For a dashboard, the model, operation and provider attributes can group spans by request type and configured backend; response finish reasons and token counts can help explain behavior and cost. They are experimental development conventions, so dashboards should tolerate missing attributes and be reviewed when the conventions or instrumentation version changes.
