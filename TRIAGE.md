---
lab5_triage:
  image: ghcr.io/pzx134590/itsm-2026-pzx134590@sha256:f176b04229fcaf439cc5b359cfad03da80810cae64767b8574e9a0dc344b79d2
  sarif_receipt: 0
---
<!-- ai-generated: 100% - Copilot documented the observed pipeline findings and fixes. -->
# Triage

The receipt number and bake-off discussion remain pending until the SARIF receipt
is submitted and the course reveals the labels.

| Tool | Rule | Decision | Reason |
|---|---|---|---|
| trivy | CVE-2026-76844 | fix | Updated the Python base image and upgraded Debian packages in the Dockerfile; the next image gate passed. |
| trivy | CVE-2026-85091 | fix | Updated the Python base image and upgraded Debian packages in the Dockerfile; the next image gate passed. |
| trivy | CVE-2025-47273 | fix | Removed pip after installing runtime dependencies, eliminating its vendored setuptools from the image. |
| trivy | CVE-2026-114613 | fix | Removed pip after installing runtime dependencies, eliminating its vendored msgpack from the image. |
| trivy | GHSA-6v7p-g79w-8964 | fix | Removed pip after installing runtime dependencies, eliminating its vendored msgpack from the image. |
| trivy | CVE-2026-97687 | fix | Removed pip after installing runtime dependencies, eliminating its vendored urllib3 from the image. |
| trivy | CVE-2026-97689 | fix | Removed pip after installing runtime dependencies, eliminating its vendored urllib3 from the image. |
| gitleaks | generic-api-key | false-positive | The Grafana pod annotation in k8s/evidence.json is a rollout checksum, not a credential; its exact fingerprint is ignored. |
| semgrep | dockerfile.security.missing-user.missing-user | accept | The service container runs as root; retain this existing configuration for now and assess a non-root runtime separately. |
| semgrep | python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected | accept | The knowledge-base URL comes from deployment configuration, while the query is URL-encoded; restrict deployment configuration to trusted operators. |

## Bake-off

Pending the course's revealed labels and the corresponding computed matrix.
