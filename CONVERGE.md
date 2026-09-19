# Converge report

This report captures the specification decisions that converged during implementation.

The service satisfies R-03, R-04, R-12, R-13, R-14, and R-16. It validates ticket data, computes priority from impact and urgency only, enforces the state machine, and tracks time using the business-hours clock for the lab decision C1=business. The ticket model records the due instants so a Monday report can be produced from one call per ticket.
