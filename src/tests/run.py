# ai-generated: 70% - Small smoke suite written to validate core service behavior and print the required pass summary.

import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Any

BASE_URL = os.getenv("SVCDESK_URL", "http://svcdesk:8080")


def request(method: str, path: str, payload: Any | None = None, clock: str | None = None):
    url = BASE_URL.rstrip("/") + path
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if clock is not None:
        headers["X-Test-Clock"] = clock
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            body = response.read()
            parsed = json.loads(body.decode("utf-8")) if body else None
            return response.status, parsed
    except urllib.error.HTTPError as exc:
        body = exc.read()
        parsed = json.loads(body.decode("utf-8")) if body else None
        return exc.code, parsed


def wait_for_health():
    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            status, body = request("GET", "/health")
            if status == 200 and body.get("status") == "ok":
                return
        except Exception:
            pass
        time.sleep(0.5)
    raise RuntimeError("svcdesk not ready")


passed = 0
failed = 0


def check(name: str, fn):
    global passed, failed
    try:
        fn()
        passed += 1
        print(f"PASS: {name}")
    except Exception as exc:
        failed += 1
        print(f"FAIL: {name}: {exc}")


def test_health():
    status, body = request("GET", "/health")
    assert status == 200
    assert body["status"] == "ok"
    assert body["service"] == "svcdesk"


def test_create_ticket():
    status, body = request(
        "POST",
        "/tickets",
        {
            "title": "Printer down",
            "description": "printer does not work",
            "reporter": {"name": "Anna", "email": "anna@example.com", "vip": False},
            "impact": 2,
            "urgency": 1,
        },
        clock="2026-10-14T10:00:00Z",
    )
    assert status == 201
    assert body["priority"] == "P2"
    assert body["state"] == "new"
    assert body["sla"]["ack_due_at"] == "2026-10-14T11:00:00Z"
    assert body["sla"]["resolve_due_at"] == "2026-10-15T10:00:00Z"


def test_create_invalid_title():
    status, body = request(
        "POST",
        "/tickets",
        {
            "description": "missing title",
            "reporter": {"name": "Anna"},
            "impact": 1,
            "urgency": 1,
        },
        clock="2026-10-14T10:00:00Z",
    )
    assert status in {400, 422}
    assert "error" in body


def test_list_and_get():
    status, body = request("GET", "/tickets")
    assert status == 200
    assert isinstance(body, list)
    ticket = body[0]
    get_status, get_body = request("GET", f"/tickets/{ticket['id']}")
    assert get_status == 200
    assert get_body["id"] == ticket["id"]


def test_ack_start_resolve_close():
    status, ticket = request(
        "POST",
        "/tickets",
        {
            "title": "Laptop issue",
            "reporter": {"name": "Bert"},
            "impact": 1,
            "urgency": 2,
        },
        clock="2026-10-14T10:00:00Z",
    )
    ticket_id = ticket["id"]
    s1, b1 = request("POST", f"/tickets/{ticket_id}/ack", clock="2026-10-14T10:05:00Z")
    assert s1 == 200 and b1["state"] == "acknowledged"
    s2, b2 = request("POST", f"/tickets/{ticket_id}/start")
    assert s2 == 200 and b2["state"] == "in_progress"
    s3, b3 = request("POST", f"/tickets/{ticket_id}/resolve", clock="2026-10-14T10:30:00Z")
    assert s3 == 200 and b3["state"] == "resolved"
    s4, b4 = request("POST", f"/tickets/{ticket_id}/close", clock="2026-10-14T10:40:00Z")
    assert s4 == 200 and b4["state"] == "closed"


def test_reopen_window():
    status, ticket = request(
        "POST",
        "/tickets",
        {
            "title": "Monitor issue",
            "reporter": {"name": "Chris"},
            "impact": 3,
            "urgency": 3,
        },
        clock="2026-10-14T10:00:00Z",
    )
    ticket_id = ticket["id"]
    request("POST", f"/tickets/{ticket_id}/ack", clock="2026-10-14T10:05:00Z")
    request("POST", f"/tickets/{ticket_id}/start")
    request("POST", f"/tickets/{ticket_id}/resolve", clock="2026-10-14T10:30:00Z")
    s, body = request("POST", f"/tickets/{ticket_id}/reopen", clock="2026-10-20T10:00:00Z")
    assert s == 200 and body["state"] == "in_progress"


def test_sla_block():
    status, body = request(
        "POST",
        "/tickets",
        {
            "title": "Backup issue",
            "reporter": {"name": "Dana"},
            "impact": 1,
            "urgency": 1,
        },
        clock="2026-10-16T15:00:00Z",
    )
    ticket_id = body["id"]
    status, sla = request("GET", f"/tickets/{ticket_id}/sla", clock="2026-10-19T09:00:00Z")
    assert status == 200
    assert set(sla.keys()) >= {"priority", "ack_due_at", "resolve_due_at", "ack_breached", "resolve_breached", "paused"}


def test_invalid_clock():
    status, body = request(
        "POST",
        "/tickets",
        {
            "title": "Oops",
            "reporter": {"name": "Zoe"},
            "impact": 1,
            "urgency": 1,
        },
        clock="yesterday",
    )
    assert status in {400, 422}
    assert "error" in body


def test_vip_matrix():
    status, body = request(
        "POST",
        "/tickets",
        {
            "title": "VIP issue",
            "reporter": {"name": "Exec", "vip": True},
            "impact": 3,
            "urgency": 3,
        },
        clock="2026-10-14T10:00:00Z",
    )
    assert status == 201
    assert body["priority"] == "P4"


def test_unknown_ticket():
    status, body = request("GET", "/tickets/does-not-exist-9f3c")
    assert status == 404
    assert "error" in body


wait_for_health()
check("health", test_health)
check("create ticket", test_create_ticket)
check("invalid title", test_create_invalid_title)
check("list and get", test_list_and_get)
check("ack start resolve close", test_ack_start_resolve_close)
check("reopen window", test_reopen_window)
check("sla block", test_sla_block)
check("invalid clock", test_invalid_clock)
check("vip matrix", test_vip_matrix)
check("unknown ticket", test_unknown_ticket)

print(f"ITSMLAB-TESTS: passed={passed} failed={failed}")
if failed:
    sys.exit(1)
