---
lab4_comms:
  awareness: 2026-10-12T07:10:07Z
  detection: 2026-10-12T07:09:19Z
  classification: 2026-10-12T07:10:07Z
  nis2:
    early_warning_due: 2026-10-13T07:10:07Z
    notification_due: 2026-10-15T07:10:07Z
    notification_sent: 2026-10-12T07:30:00Z
    final_report_due: 2026-11-12T07:30:00Z
  ksc:
    early_warning_due: 2026-10-13T07:09:19Z
    notification_due: 2026-10-15T07:09:19Z
    notification_sent: 2026-10-12T07:30:00Z
    final_report_due: 2026-11-12T07:30:00Z
  dora:
    initial_due: 2026-10-12T11:10:07Z
    initial_sent: 2026-10-12T08:00:00Z
    intermediate_due: 2026-10-15T08:00:00Z
    intermediate_sent: 2026-10-15T07:30:00Z
    final_due: 2026-11-15T07:30:00Z
  log:
    - {at: 2026-10-12T07:30:00Z, to: "CSIRT and competent authority", what: "Proposed NIS2 early warning and KSC incident notification, before the calculated deadlines."}
    - {at: 2026-10-12T08:00:00Z, to: "Financial supervisor", what: "Proposed DORA initial notification, before its four-hour deadline from classification."}
    - {at: 2026-10-15T07:30:00Z, to: "Financial supervisor", what: "Proposed DORA intermediate report, before its calculated deadline."}
---
<!-- ai-generated: 70% - AI recalculated reporting clocks from the assigned recording; the responder selected and explained awareness and classification instants -->

# Communications log: the regulators' clocks

## The three instants you defend

For this exercise, the shop is assumed to fall under NIS2, the Polish KSC act and DORA. NIS2 awareness is 07:10:07Z, when the on-call acknowledged the P1 and had confirmed significant checkout impact. KSC detection is 07:09:19Z, the recorded alert transition. DORA classification is set to 07:10:07Z, after the responder acknowledged and classified the multi-service error path for this exercise. These are distinct decision points, not interchangeable timestamps.

The proposed NIS2 and KSC early warning/notification is 07:30Z on 2026-10-12. The DORA initial report is proposed for 08:00Z. The DORA intermediate report is proposed for 07:30Z on 2026-10-15. These are exercise communications, not claims that reports were actually sent.

## The log

| UTC time | Recipient | Communication |
|---|---|---|
| 2026-10-12T07:30:00Z | CSIRT and competent authority | Proposed NIS2 early warning and KSC incident notification. |
| 2026-10-12T08:00:00Z | Financial supervisor | Proposed DORA initial notification. |
| 2026-10-15T07:30:00Z | Financial supervisor | Proposed DORA intermediate report. |

The NIS2 deadlines are awareness plus 24 hours and 72 hours; the final report is one calendar month after the proposed notification. KSC uses the detection instant for its 24-hour and 72-hour deadlines. DORA classification occurred within 24 hours of awareness, so the initial deadline is four hours after classification (11:10:07Z), earlier than awareness plus 24 hours. Its intermediate deadline is 72 hours after the proposed initial submission; the final deadline is one calendar month after the proposed intermediate submission. All instants and calculations are in UTC.
