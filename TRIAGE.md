---
lab5_triage:
  image: ghcr.io/pzx134590/itsm-2026-pzx134590@sha256:f176b04229fcaf439cc5b359cfad03da80810cae64767b8574e9a0dc344b79d2
  sarif_receipt: 358
---
<!-- ai-generated: 100% - Copilot documented the observed pipeline findings and fixes. -->
# Triage

The findings below include the initial image scan and results outside the
canary in the receipted SARIF.

| Tool | Rule | Decision | Reason |
|---|---|---|---|
| trivy | CVE-2026-76844 | fix | Updated the Python base image and upgraded Debian packages in the Dockerfile; the next image gate passed. |
| trivy | CVE-2026-85091 | fix | Updated the Python base image and upgraded Debian packages in the Dockerfile; the next image gate passed. |
| trivy | CVE-2025-47273 | fix | Removed pip after installing runtime dependencies, eliminating its vendored setuptools from the image. |
| trivy | CVE-2026-114613 | fix | Removed pip after installing runtime dependencies, eliminating its vendored msgpack from the image. |
| trivy | GHSA-6v7p-g79w-8964 | fix | Removed pip after installing runtime dependencies, eliminating its vendored msgpack from the image. |
| trivy | CVE-2026-97687 | fix | Removed pip after installing runtime dependencies, eliminating its vendored urllib3 from the image. |
| trivy | CVE-2026-97689 | fix | Removed pip after installing runtime dependencies, eliminating its vendored urllib3 from the image. |
| gitleaks | generic-api-key | ignore | The Grafana pod annotation in k8s/evidence.json is a rollout checksum, not a credential; its exact fingerprint is ignored. |
| semgrep | dockerfile.security.missing-user.missing-user | accept | The service container runs as root; retain this existing configuration for now and assess a non-root runtime separately. |
| semgrep | python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected | accept | The knowledge-base URL comes from deployment configuration, while the query is URL-encoded; restrict deployment configuration to trusted operators. |

## Bake-off

The set contains nine labelled defects. Gitleaks found 3, with no false
positives and 6 missed defects: precision 1.0000, recall 0.3333 and F1 0.5000.
Grype and OSV-Scanner each found 2, with no false positives and 7 missed:
precision 1.0000, recall 0.2222 and F1 0.3636. Semgrep found 4, with 2 false
positives and 5 missed: precision 0.6667, recall 0.4444 and F1 0.5333. Trivy
found 4, with no false positives and 5 missed: precision 1.0000, recall 0.4444
and F1 0.6154.

I would retain Trivy's dependency gate and the gitleaks secret gate, while
using Semgrep as a reviewed report rather than a blocking gate. The zero false
positives for Trivy and gitleaks on this small set make their alerts useful,
but their missed defects show that neither is sufficient alone. Semgrep's two
false positives illustrate the review effort a blocking rule would impose;
its additional code findings still make it valuable. Grype and OSV-Scanner
detected both dependency defects, but their results overlap on this set and
do not establish coverage of the other classes.

These are measurements of deliberately seeded defects, not estimates of
production performance: synthetic defects can be easier to detect, so the
observed recall is an upper-bound warning rather than a guarantee. A finding
can match more than one defect and repeated findings do not increase the
number of defects found; there is no true-negative count in this evaluation.
