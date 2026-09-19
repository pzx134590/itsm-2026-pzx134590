# Service Desk API Specification

## Purpose

The SvcDesk service provides a simple ticket management API for an IT service desk. It allows users to create, update, view, close, and reopen support tickets. The service will be implemented as a REST API and deployed using Docker Compose.

## Functional Requirements

### Ticket Creation

Users can create a ticket by providing:

- title
- description
- reporter name
- reporter email

The system assigns:

- unique ticket identifier
- creation timestamp
- initial status OPEN
- ticket priority

### Priority Matrix

Tickets are assigned one of four priorities:

- P1 - Critical
- P2 - High
- P3 - Medium
- P4 - Low

Priority depends on business impact and urgency.

### Ticket Lifecycle

Supported ticket states:

- OPEN
- IN_PROGRESS
- RESOLVED
- CLOSED

State transitions:

OPEN → IN_PROGRESS

IN_PROGRESS → RESOLVED

RESOLVED → CLOSED

Under defined conditions a CLOSED ticket may be reopened.

### Ticket Queries

The API allows:

- retrieving a ticket by ID
- listing all tickets
- filtering by status
- filtering by priority

### Health Endpoint

The service exposes:

GET /health

Response:

{
  "status": "ok"
}

This endpoint is used for health checks and automated verification.

## SLA Requirements

The system tracks SLA deadlines based on ticket priority.

Example targets:

| Priority | Response Time |
|-----------|--------------|
| P1 | 1 hour |
| P2 | 4 hours |
| P3 | 8 hours |
| P4 | 24 hours |

The system must be able to determine whether a ticket breached its SLA.

## Validation Rules

- title cannot be empty
- description cannot be empty
- email must be valid
- priority must be one of P1-P4
- status must be one of the allowed states

## Non-Functional Requirements

- RESTful API design
- JSON request and response bodies
- Docker Compose deployment
- Python 3.13 implementation
- FastAPI framework
- Automated tests using pytest

## Decision Documentation

Any ambiguities or contradictions discovered during implementation must be documented in DECISIONS.md. The selected behavior must match the running implementation.