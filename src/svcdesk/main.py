# ai-generated: 85% - Implemented in FastAPI and manually verified against the Lab 1 SLA and state-machine rules.

import os
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Optional
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Header, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI()

tickets: dict[str, dict[str, Any]] = {}
WARSAW = ZoneInfo("Europe/Warsaw")
DECISION_C1 = "business"
DECISION_C2 = "reopen"
DECISION_C3 = "matrix"


def error_response(status: int, code: str, message: str):
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message}},
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(_: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return error_response(404, "not_found", "not found")
    if exc.status_code == 405:
        return error_response(405, "method_not_allowed", "method not allowed")
    return error_response(exc.status_code, "http_error", exc.detail or "error")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError):
    return error_response(422, "validation", exc.errors()[0]["msg"] if exc.errors() else "invalid request")


def parse_rfc3339(value: Optional[str]) -> datetime:
    if value is None:
        raise ValueError("missing timestamp")
    candidate = value.strip()
    if not candidate:
        raise ValueError("missing timestamp")
    try:
        dt = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid timestamp") from exc
    if dt.tzinfo is None:
        raise ValueError("invalid timestamp")
    return dt.astimezone(timezone.utc)


def to_utc_string(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_now(x_test_clock: Optional[str]) -> datetime:
    if x_test_clock is not None:
        return parse_rfc3339(x_test_clock)
    return datetime.now(timezone.utc).replace(microsecond=0)


def business_window_for(local_dt: datetime) -> bool:
    return local_dt.weekday() < 5 and time(8, 0) <= local_dt.timetz() < time(16, 0)


def next_business_opening(local_dt: datetime) -> datetime:
    current = local_dt.date()
    for offset in range(0, 12):
        day = current + timedelta(days=offset)
        if day.weekday() < 5:
            return datetime.combine(day, time(8, 0), tzinfo=local_dt.tzinfo)
    raise ValueError("no business day found")


def business_due_at(created_at_utc: datetime, target_hours: int) -> datetime:
    remaining = timedelta(hours=target_hours)
    current = created_at_utc.astimezone(WARSAW)

    while remaining > timedelta(0):
        if current.weekday() < 5:
            window_start = current.replace(hour=8, minute=0, second=0, microsecond=0)
            window_end = current.replace(hour=16, minute=0, second=0, microsecond=0)

            if current < window_start:
                current = window_start
                continue
            if current >= window_end:
                current = (current + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                continue

            available = window_end - current
            if remaining <= available:
                return (current + remaining).astimezone(timezone.utc)
            remaining -= available
            next_day = (current + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            current = next_day
        else:
            current = current.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)

    return created_at_utc


def due_at_for(priority: str, created_at_utc: datetime, kind: str) -> datetime:
    targets = {
        "P1": {"ack": 15, "resolve": 4 * 60},
        "P2": {"ack": 60, "resolve": 8 * 60},
        "P3": {"ack": 4 * 60, "resolve": 24 * 60},
        "P4": {"ack": 8 * 60, "resolve": 72 * 60},
    }

    target_minutes = targets[priority][kind]
    if kind == "ack" and priority == "P1" and DECISION_C1 == "wallclock":
        return created_at_utc + timedelta(minutes=target_minutes)
    if kind == "resolve" and priority == "P1" and DECISION_C1 == "wallclock":
        return created_at_utc + timedelta(minutes=target_minutes)
    return business_due_at(created_at_utc, target_minutes / 60)


def compute_priority(impact: int, urgency: int, vip: bool) -> str:
    matrix = {
        (1, 1): "P1",
        (1, 2): "P2",
        (1, 3): "P3",
        (2, 1): "P2",
        (2, 2): "P3",
        (2, 3): "P4",
        (3, 1): "P3",
        (3, 2): "P4",
        (3, 3): "P4",
    }
    base = matrix[(impact, urgency)]
    if DECISION_C3 == "vip" and vip and base in {"P3", "P4"}:
        return "P2"
    return base


def business_clock_for_priority(priority: str) -> bool:
    return not (priority == "P1" and DECISION_C1 == "wallclock")


def get_ticket_or_404(ticket_id: str):
    return tickets.get(ticket_id)


@app.get("/health")
def health():
    return {"status": "ok", "service": "svcdesk"}


@app.post("/tickets", status_code=201)
def create_ticket(
    body: dict,
    x_test_clock: Optional[str] = Header(default=None, alias="X-Test-Clock"),
):
    if not isinstance(body, dict):
        return error_response(422, "validation", "request body must be an object")

    ticket_clock = datetime.now(timezone.utc).replace(microsecond=0)
    if os.getenv("SVCDESK_TEST_CLOCK", "0").lower() in {"1", "true"} and x_test_clock is not None:
        try:
            ticket_clock = parse_rfc3339(x_test_clock)
        except ValueError:
            return error_response(422, "validation", "invalid X-Test-Clock")

    title = body.get("title")
    if title is None or not isinstance(title, str) or len(title.strip()) == 0:
        return error_response(422, "validation", "title is required")
    if len(title) > 200:
        return error_response(422, "validation", "title too long")

    description = body.get("description", "")
    if description is None:
        description = ""
    if not isinstance(description, str) or len(description) > 4000:
        return error_response(422, "validation", "description too long")

    reporter = body.get("reporter")
    if not isinstance(reporter, dict):
        return error_response(422, "validation", "reporter is required")
    reporter_name = reporter.get("name")
    if not isinstance(reporter_name, str) or len(reporter_name.strip()) == 0 or len(reporter_name) > 100:
        return error_response(422, "validation", "reporter.name is required")

    impact = body.get("impact")
    urgency = body.get("urgency")
    if not isinstance(impact, int) or impact not in {1, 2, 3}:
        return error_response(422, "validation", "invalid impact")
    if not isinstance(urgency, int) or urgency not in {1, 2, 3}:
        return error_response(422, "validation", "invalid urgency")

    vip = bool(reporter.get("vip", False))
    priority = compute_priority(impact, urgency, vip)
    ticket_id = str(uuid4())

    created_at = ticket_clock
    sla = {
        "ack_due_at": to_utc_string(due_at_for(priority, created_at, "ack")),
        "resolve_due_at": to_utc_string(due_at_for(priority, created_at, "resolve")),
    }

    ticket = {
        "id": ticket_id,
        "title": title,
        "description": description,
        "reporter": {"name": reporter_name, "email": reporter.get("email"), "vip": vip},
        "impact": impact,
        "urgency": urgency,
        "priority": priority,
        "state": "new",
        "created_at": to_utc_string(created_at),
        "acknowledged_at": None,
        "resolved_at": None,
        "closed_at": None,
        "related_to": body.get("related_to"),
        "sla": sla,
    }
    tickets[ticket_id] = ticket
    return ticket


@app.get("/tickets")
def list_tickets(
    state: Optional[str] = Query(default=None),
    priority: Optional[str] = Query(default=None),
):
    result = list(tickets.values())
    if state is not None:
        result = [t for t in result if t["state"] == state]
    if priority is not None:
        result = [t for t in result if t["priority"] == priority]
    return result


@app.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: str):
    ticket = get_ticket_or_404(ticket_id)
    if ticket is None:
        return error_response(404, "not_found", "ticket not found")
    return ticket


@app.get("/tickets/{ticket_id}/sla")
def get_ticket_sla(ticket_id: str, x_test_clock: Optional[str] = Header(default=None, alias="X-Test-Clock")):
    ticket = get_ticket_or_404(ticket_id)
    if ticket is None:
        return error_response(404, "not_found", "ticket not found")
    now = parse_now(x_test_clock) if os.getenv("SVCDESK_TEST_CLOCK", "0").lower() in {"1", "true"} and x_test_clock is not None else datetime.now(timezone.utc).replace(microsecond=0)
    ack_due = parse_rfc3339(ticket["sla"]["ack_due_at"])
    resolve_due = parse_rfc3339(ticket["sla"]["resolve_due_at"])
    ack_breached = (
        ticket["acknowledged_at"] is not None and parse_rfc3339(ticket["acknowledged_at"]) > ack_due
    ) or (ticket["acknowledged_at"] is None and now > ack_due)
    resolve_breached = (
        ticket["resolved_at"] is not None and parse_rfc3339(ticket["resolved_at"]) > resolve_due
    ) or (ticket["resolved_at"] is None and now > resolve_due)
    paused = (
        ticket["state"] not in {"resolved", "closed"}
        and business_clock_for_priority(ticket["priority"])
        and not business_window_for(now.astimezone(WARSAW))
    )
    return {
        "priority": ticket["priority"],
        "ack_due_at": ticket["sla"]["ack_due_at"],
        "resolve_due_at": ticket["sla"]["resolve_due_at"],
        "ack_breached": ack_breached,
        "resolve_breached": resolve_breached,
        "paused": paused,
    }


@app.post("/tickets/{ticket_id}/ack")
def ack_ticket(
    ticket_id: str,
    x_test_clock: Optional[str] = Header(default=None, alias="X-Test-Clock"),
):
    ticket = get_ticket_or_404(ticket_id)
    if ticket is None:
        return error_response(404, "not_found", "ticket not found")
    if ticket["state"] != "new":
        return error_response(409, "invalid_transition", "invalid transition")
    now = parse_now(x_test_clock) if os.getenv("SVCDESK_TEST_CLOCK", "0").lower() in {"1", "true"} and x_test_clock is not None else datetime.now(timezone.utc).replace(microsecond=0)
    ticket["state"] = "acknowledged"
    ticket["acknowledged_at"] = to_utc_string(now)
    return ticket


@app.post("/tickets/{ticket_id}/start")
def start_ticket(ticket_id: str):
    ticket = get_ticket_or_404(ticket_id)
    if ticket is None:
        return error_response(404, "not_found", "ticket not found")
    if ticket["state"] != "acknowledged":
        return error_response(409, "invalid_transition", "invalid transition")
    ticket["state"] = "in_progress"
    return ticket


@app.post("/tickets/{ticket_id}/resolve")
def resolve_ticket(
    ticket_id: str,
    x_test_clock: Optional[str] = Header(default=None, alias="X-Test-Clock"),
):
    ticket = get_ticket_or_404(ticket_id)
    if ticket is None:
        return error_response(404, "not_found", "ticket not found")
    if ticket["state"] != "in_progress":
        return error_response(409, "invalid_transition", "invalid transition")
    now = parse_now(x_test_clock) if os.getenv("SVCDESK_TEST_CLOCK", "0").lower() in {"1", "true"} and x_test_clock is not None else datetime.now(timezone.utc).replace(microsecond=0)
    ticket["state"] = "resolved"
    ticket["resolved_at"] = to_utc_string(now)
    return ticket


@app.post("/tickets/{ticket_id}/close")
def close_ticket(
    ticket_id: str,
    x_test_clock: Optional[str] = Header(default=None, alias="X-Test-Clock"),
):
    ticket = get_ticket_or_404(ticket_id)
    if ticket is None:
        return error_response(404, "not_found", "ticket not found")
    if ticket["state"] != "resolved":
        return error_response(409, "invalid_transition", "invalid transition")
    now = parse_now(x_test_clock) if os.getenv("SVCDESK_TEST_CLOCK", "0").lower() in {"1", "true"} and x_test_clock is not None else datetime.now(timezone.utc).replace(microsecond=0)
    ticket["state"] = "closed"
    ticket["closed_at"] = to_utc_string(now)
    return ticket


@app.post("/tickets/{ticket_id}/reopen")
def reopen_ticket(
    ticket_id: str,
    x_test_clock: Optional[str] = Header(default=None, alias="X-Test-Clock"),
):
    ticket = get_ticket_or_404(ticket_id)
    if ticket is None:
        return error_response(404, "not_found", "ticket not found")
    now = parse_now(x_test_clock) if os.getenv("SVCDESK_TEST_CLOCK", "0").lower() in {"1", "true"} and x_test_clock is not None else datetime.now(timezone.utc).replace(microsecond=0)

    if ticket["state"] == "resolved":
        resolved_at = parse_rfc3339(ticket["resolved_at"]) if ticket["resolved_at"] else now
        if now > resolved_at + timedelta(days=7):
            return error_response(409, "reopen_window_expired", "reopen window expired")
        ticket["state"] = "in_progress"
        ticket["resolved_at"] = None
        return ticket

    if ticket["state"] == "closed":
        if DECISION_C2 != "reopen":
            return error_response(409, "ticket_closed", "ticket is closed")
        closed_at = parse_rfc3339(ticket["closed_at"]) if ticket["closed_at"] else now
        if now > closed_at + timedelta(days=7):
            return error_response(409, "reopen_window_expired", "reopen window expired")
        ticket["state"] = "in_progress"
        ticket["closed_at"] = None
        ticket["resolved_at"] = None
        return ticket

    return error_response(409, "invalid_transition", "invalid transition")

    return error_response(409, "invalid transition")