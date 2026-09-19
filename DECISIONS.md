---
svcdesk_decisions:
  C1: business
  C2: reopen
  C3: matrix
---
# ai-generated: 85% - AI drafted the first version and I revised the wording to match the running service and lab requirements.

# Decisions

## C1 - SLA clock for P1

**Decision:** The service uses the business-hours clock for P1 targets as well as for P2 to P4. This keeps the SLA aligned with operating hours and prevents a Friday evening incident from being due at 15 minutes past the next Monday start.

**Rejected alternative:** Wall-clock timing would count time outside office hours, so a P1 created on Friday evening would become late at 15 minutes on the same day even though the desk is closed for the weekend.

**Reason:** The business-hours algorithm measures only the time from 08:00 to 16:00 on weekdays in Europe/Warsaw, which matches the requirement that desk work pauses outside working hours and that backlog reporting is produced on the business clock.

**Service owner:** The service desk operations lead is accountable because they own the recovery targets and staffing windows for every priority and they are the role that signs off on SLA commitments to the business.

**Customer outcome:** Reporters receive a realistic target that reflects when the team is actually working, so a critical issue raised at the end of Friday is not treated as late before Monday support hours resume.

## C2 - Closed tickets and reopening

**Decision:** Closed tickets may be reopened within 7 days, and reopening returns the issue to in_progress without resetting the original resolution clock. This preserves the evidence trail and allows a fix that was incomplete to be revisited quickly.

**Rejected alternative:** Making closed tickets immutable would force the desk to create a new ticket for every failed fix, which would lose the reporting history and would not match the requirement that a customer may report the same failed repair within the reopening window.

**Reason:** The reopened ticket remains a continuation of the same issue, so the service keeps the original due target and expresses the rework as the same ticket transitioning back to active work. The model accepts a reopened closed ticket only within the 7-day window.

**Service owner:** The service desk quality owner is the correct signer because this rule affects how incident records are maintained and when a closed defect is considered a fresh issue instead of the same one being re-opened.

**Customer outcome:** An organisation can repair a failed fix without losing the original ticket history, while still preventing stale issues from reopening indefinitely after the seven-day window.

## C3 - VIP reporters and the priority matrix

**Decision:** The matrix remains authoritative; VIP status is recorded but does not increase the priority above the computed value. This produces a consistent score from impact and urgency and keeps the matrix predictable for analysts and automation.

**Rejected alternative:** The VIP override would raise low-priority incidents to P2, which would distort the priority picture and create false urgency for tickets that are not operationally critical.

**Reason:** The priority matrix is the rule used to calculate urgency from impact and urgency, and the service must not let a reporter request a priority or override the calculated classification. The VIP flag is kept for reporting but does not change the matrix result.

**Service owner:** The incident manager is the sign-off role because they are responsible for prioritisation consistency across teams and for ensuring that executive issues do not distort the workload queue for everyone else.

**Customer outcome:** Staff can trust that the queue reflects operational impact, not reporter status, while still recording VIP participation for visibility and escalation reporting.
