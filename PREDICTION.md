---
feature: "Add a dedicated Lab 2 feature module for DORA metric computation"
predicted_minutes: 20
predicted_at: "2026-09-27T09:00:00Z"
feature_path: "src/svcdesk/dora_metrics.py"
---

I predict this feature will take about 20 minutes because the work is a narrow API update: one dedicated module for the DORA computation, a small integration adjustment, and a proof run against the published practice fixture. The risk is moderate but bounded because the contract is already known and the implementation can be isolated in a new supporting module, which keeps the service stable while preserving the delivery traceability required by the Lab 2 rule set.
