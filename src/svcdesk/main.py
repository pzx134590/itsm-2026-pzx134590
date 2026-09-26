# ai-generated: 85% - Implemented in FastAPI and manually verified against the Lab 1 SLA and state-machine rules.

import os
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
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


def parse_iso8601(value: Optional[str], field_name: str = "timestamp") -> datetime:
    if value is None:
        raise ValueError(f"missing {field_name}")
    candidate = str(value).strip()
    if not candidate:
        raise ValueError(f"missing {field_name}")
    try:
        dt = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"invalid {field_name}") from exc
    if dt.tzinfo is None:
        raise ValueError(f"invalid {field_name}")
    return dt.astimezone(timezone.utc)


def quantize_decimal(value: float | int | Decimal, digits: int) -> Decimal:
    if isinstance(value, Decimal):
        decimal_value = value
    else:
        decimal_value = Decimal(str(value))
    quantum = Decimal("1").scaleb(-digits)
    return decimal_value.quantize(quantum, rounding=ROUND_HALF_UP)


def round_float(value: float | int | Decimal, digits: int) -> float:
    return float(quantize_decimal(value, digits))


def round_duration_seconds(value: int | float | Decimal) -> int:
    if value is None:
        return 0
    decimal_value = Decimal(str(value))
    if decimal_value < 0:
        decimal_value = Decimal(0)
    return int(decimal_value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def median_value(values: list[int | float], digits: int = 0, clamp_negative: bool = False) -> Optional[float | int]:
    if not values:
        return None
    cleaned = []
    for value in values:
        numeric = Decimal(str(value))
        if clamp_negative and numeric < 0:
            numeric = Decimal(0)
        cleaned.append(numeric)
    cleaned.sort()
    n = len(cleaned)
    if n % 2 == 1:
        result = cleaned[n // 2]
    else:
        result = (cleaned[n // 2 - 1] + cleaned[n // 2]) / Decimal(2)
    if digits == 0:
        return int(result.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return float(result.quantize(Decimal("1").scaleb(-digits), rounding=ROUND_HALF_UP))


def valid_event_id(value: Any) -> bool:
    return isinstance(value, str) and 1 <= len(value) <= 64


def validate_and_normalize_event_log(events: list[Any]) -> tuple[list[dict[str, Any]], set[str], set[str], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    deduped: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for raw in events:
        if not isinstance(raw, dict):
            raise ValueError("malformed event")
        event_id = raw.get("event_id")
        if not valid_event_id(event_id):
            raise ValueError("invalid event_id")
        if event_id in seen_ids:
            continue
        seen_ids.add(event_id)
        deduped.append(raw)

    commit_shas: set[str] = set()
    deployment_ids: set[str] = set()
    incident_ids: set[str] = set()
    commits_by_sha: dict[str, dict[str, Any]] = {}
    deployments_by_id: dict[str, dict[str, Any]] = {}
    incidents_by_id: dict[str, dict[str, Any]] = {}
    incident_phase_counts: dict[str, dict[str, int]] = {}

    for raw in deduped:
        event_type = raw.get("type")
        if event_type not in {"commit", "deployment", "incident"}:
            raise ValueError("invalid event type")
        if not isinstance(raw.get("at"), str):
            raise ValueError("invalid event timestamp")
        parse_iso8601(raw.get("at"), "event timestamp")

        if event_type == "commit":
            sha = raw.get("sha")
            if not isinstance(sha, str) or not sha:
                raise ValueError("invalid commit sha")
            if sha in commit_shas:
                raise ValueError("duplicate commit sha")
            commit_shas.add(sha)
            commits_by_sha[sha] = raw
            branch = raw.get("branch")
            if not isinstance(branch, str):
                raise ValueError("invalid commit branch")
            change_id = raw.get("change_id")
            reverts = raw.get("reverts")
            if change_id is None and reverts is None:
                raise ValueError("commit missing change_id or reverts")
            if change_id is not None and reverts is not None:
                raise ValueError("commit has both change_id and reverts")
            if reverts is not None and not isinstance(reverts, str):
                raise ValueError("invalid revert target")
            if change_id is not None and not isinstance(change_id, str):
                raise ValueError("invalid change_id")
        elif event_type == "deployment":
            dep_id = raw.get("deployment_id")
            if not isinstance(dep_id, str) or not dep_id:
                raise ValueError("invalid deployment_id")
            if dep_id in deployment_ids:
                raise ValueError("duplicate deployment_id")
            deployment_ids.add(dep_id)
            deployments_by_id[dep_id] = raw
            environment = raw.get("environment")
            if environment is not None and not isinstance(environment, str):
                raise ValueError("invalid deployment environment")
            outcome = raw.get("outcome")
            if outcome not in {"success", "failure"}:
                raise ValueError("invalid deployment outcome")
            commits = raw.get("commits")
            if not isinstance(commits, list):
                raise ValueError("invalid deployment commits")
            for sha in commits:
                if not isinstance(sha, str):
                    raise ValueError("invalid deployment commit reference")
            if raw.get("unplanned") is not None and not isinstance(raw.get("unplanned"), bool):
                raise ValueError("invalid deployment unplanned")
            caused_by = raw.get("caused_by")
            if caused_by is not None and not isinstance(caused_by, str):
                raise ValueError("invalid deployment caused_by")
        elif event_type == "incident":
            incident_id = raw.get("incident_id")
            if not isinstance(incident_id, str) or not incident_id:
                raise ValueError("invalid incident_id")
            incident_ids.add(incident_id)
            incidents_by_id[incident_id] = raw
            phase = raw.get("phase")
            if phase not in {"opened", "resolved"}:
                raise ValueError("invalid incident phase")
            phase_counts = incident_phase_counts.setdefault(incident_id, {"opened": 0, "resolved": 0})
            phase_counts[phase] += 1
            deployments = raw.get("deployments")
            if not isinstance(deployments, list):
                raise ValueError("invalid incident deployments")
            for dep_id in deployments:
                if not isinstance(dep_id, str):
                    raise ValueError("invalid incident deployment reference")

    for raw in deduped:
        if raw.get("type") == "commit":
            reverts = raw.get("reverts")
            if reverts is not None and reverts not in commit_shas:
                raise ValueError("revert target missing")
            change_id = raw.get("change_id")
            if change_id is not None and not isinstance(change_id, str):
                raise ValueError("invalid change_id")
        elif raw.get("type") == "deployment":
            for sha in raw.get("commits", []):
                if sha not in commit_shas:
                    raise ValueError("deployment commit missing")
            caused_by = raw.get("caused_by")
            if caused_by is not None and caused_by not in incident_ids:
                raise ValueError("deployment caused_by missing")
        elif raw.get("type") == "incident":
            for dep_id in raw.get("deployments", []):
                if dep_id not in deployment_ids:
                    raise ValueError("incident deployment missing")

    for incident_id, counts in incident_phase_counts.items():
        if counts["opened"] > 1 or counts["resolved"] > 1:
            raise ValueError("incident phase repeated")
        if counts["resolved"] and counts["opened"] == 0:
            raise ValueError("resolved incident without open")

    return deduped, commit_shas, deployment_ids, commits_by_sha, deployments_by_id


def resolve_change_id(sha: str, commit_lookup: dict[str, dict[str, Any]], memo: dict[str, str | None] | None = None) -> str | None:
    if memo is None:
        memo = {}
    if sha in memo:
        return memo[sha]
    commit = commit_lookup.get(sha)
    if commit is None:
        return None
    reverts = commit.get("reverts")
    if reverts is None:
        result = commit.get("change_id")
        memo[sha] = result
        return result
    result = resolve_change_id(reverts, commit_lookup, memo)
    memo[sha] = result
    return result


def compute_metrics_for_events(events: list[dict[str, Any]], window_from: datetime, window_to: datetime) -> dict[str, Any]:
    if not events:
        return {
            "spec_version": "1.0.0",
            "window": {"from": window_from.strftime("%Y-%m-%dT%H:%M:%SZ"), "to": window_to.strftime("%Y-%m-%dT%H:%M:%SZ")},
            "deployment_frequency_per_day": 0.0,
            "change_lead_time_seconds_p50": None,
            "failed_deployment_recovery_time_seconds_p50": None,
            "change_fail_rate": None,
            "deployment_rework_rate": None,
            "counts": {
                "deployments": 0,
                "successful_deployments": 0,
                "failed_deployments": 0,
                "recovered_failures": 0,
                "open_failures": 0,
                "rework_deployments": 0,
                "lead_time_pairs": 0,
                "changes": 0,
            },
            "anomalies": {
                "negative_lead_time_pairs": 0,
                "deployments_without_commits": 0,
                "commits_never_on_main": 0,
                "revert_chains_collapsed": 0,
                "overlapping_incident_pairs": 0,
            },
            "ground_truth": {
                "changes_delivered": 0,
                "true_change_lead_time_seconds_p50": None,
            },
        }

    commit_lookup: dict[str, dict[str, Any]] = {}
    incident_opened: dict[str, datetime] = {}
    incident_resolved: dict[str, datetime] = {}
    for event in events:
        if event.get("type") == "commit":
            commit_lookup[event["sha"]] = event
        elif event.get("type") == "incident":
            iid = event["incident_id"]
            ts = parse_iso8601(event.get("at"), "incident timestamp")
            if event.get("phase") == "opened":
                if iid not in incident_opened or ts < incident_opened[iid]:
                    incident_opened[iid] = ts
            elif event.get("phase") == "resolved":
                if iid not in incident_resolved or ts < incident_resolved[iid]:
                    incident_resolved[iid] = ts

    production_deployments = [
        event for event in events
        if event.get("type") == "deployment"
        and event.get("environment") == "production"
        and window_from <= parse_iso8601(event.get("at"), "deployment timestamp") < window_to
    ]

    counts = {
        "deployments": len(production_deployments),
        "successful_deployments": sum(1 for ev in production_deployments if ev.get("outcome") == "success"),
        "failed_deployments": sum(1 for ev in production_deployments if ev.get("outcome") == "failure"),
        "recovered_failures": 0,
        "open_failures": 0,
        "rework_deployments": sum(1 for ev in production_deployments if bool(ev.get("unplanned")) and ev.get("caused_by") is not None),
        "lead_time_pairs": 0,
        "changes": 0,
    }

    anomaly_counts = {
        "negative_lead_time_pairs": 0,
        "deployments_without_commits": sum(1 for ev in production_deployments if not ev.get("commits")),
        "commits_never_on_main": 0,
        "revert_chains_collapsed": sum(1 for ev in events if ev.get("type") == "commit" and ev.get("reverts") is not None),
        "overlapping_incident_pairs": 0,
    }

    change_first_commit: dict[str, datetime] = {}
    for event in events:
        if event.get("type") != "commit":
            continue
        change_id = resolve_change_id(event["sha"], commit_lookup)
        if change_id is None:
            continue
        commit_dt = parse_iso8601(event.get("at"), "commit timestamp")
        if change_id not in change_first_commit or commit_dt < change_first_commit[change_id]:
            change_first_commit[change_id] = commit_dt
    counts["changes"] = len(change_first_commit)

    off_main_shas: set[str] = set()
    for dep in production_deployments:
        for sha in dep.get("commits", []):
            commit_event = commit_lookup.get(sha)
            if commit_event is not None and commit_event.get("branch") != "main":
                off_main_shas.add(sha)
    anomaly_counts["commits_never_on_main"] = len(off_main_shas)

    incident_intervals: list[tuple[datetime, datetime, str]] = []
    for iid, opened in incident_opened.items():
        end = incident_resolved.get(iid, window_to)
        incident_intervals.append((opened, end, iid))
    for i, (opened_a, end_a, iid_a) in enumerate(incident_intervals):
        for opened_b, end_b, iid_b in incident_intervals[i + 1 :]:
            if opened_a < end_b and opened_b < end_a:
                anomaly_counts["overlapping_incident_pairs"] += 1

    first_successful_deployment_by_sha: dict[str, datetime] = {}
    for dep in sorted(production_deployments, key=lambda ev: parse_iso8601(ev.get("at"), "deployment timestamp")):
        if dep.get("outcome") != "success":
            continue
        dep_at = parse_iso8601(dep.get("at"), "deployment timestamp")
        for sha in dep.get("commits", []):
            if sha not in first_successful_deployment_by_sha:
                first_successful_deployment_by_sha[sha] = dep_at

    lead_durations: list[int] = []
    for sha, dep_at in first_successful_deployment_by_sha.items():
        commit_event = commit_lookup.get(sha)
        if commit_event is None:
            continue
        commit_at = parse_iso8601(commit_event.get("at"), "commit timestamp")
        lead = int((dep_at - commit_at).total_seconds())
        if lead < 0:
            anomaly_counts["negative_lead_time_pairs"] += 1
            lead = 0
        lead_durations.append(lead)
    counts["lead_time_pairs"] = len(lead_durations)

    failed_prod = [ev for ev in production_deployments if ev.get("outcome") == "failure"]
    recovered_times: list[int] = []
    for dep in failed_prod:
        dep_id = dep["deployment_id"]
        candidates: list[tuple[datetime, str]] = []
        for event in events:
            if event.get("type") != "incident":
                continue
            deployments = event.get("deployments") or []
            if dep_id not in deployments:
                continue
            opened = None
            resolved = None
            for other in events:
                if other.get("type") != "incident" or other.get("incident_id") != event["incident_id"]:
                    continue
                ts = parse_iso8601(other.get("at"), "incident timestamp")
                if other.get("phase") == "opened":
                    opened = ts if opened is None or ts < opened else opened
                elif other.get("phase") == "resolved":
                    resolved = ts if resolved is None or ts < resolved else resolved
            if opened is None:
                continue
            if resolved is not None:
                candidates.append((opened, event["incident_id"]))
        if not candidates:
            counts["open_failures"] += 1
            continue
        best = min(candidates, key=lambda item: (item[0], item[1]))
        if best[0] is None:
            counts["open_failures"] += 1
            continue
        incident_id = best[1]
        resolved_time = None
        for event in events:
            if event.get("type") == "incident" and event.get("incident_id") == incident_id and event.get("phase") == "resolved":
                candidate = parse_iso8601(event.get("at"), "incident timestamp")
                if resolved_time is None or candidate < resolved_time:
                    resolved_time = candidate
        if resolved_time is None:
            counts["open_failures"] += 1
            continue
        counts["recovered_failures"] += 1
        recovered_times.append(int((resolved_time - parse_iso8601(dep.get("at"), "deployment timestamp")).total_seconds()))

    for dep in failed_prod:
        dep_id = dep["deployment_id"]
        has_cover = False
        has_resolved = False
        for event in events:
            if event.get("type") != "incident":
                continue
            if dep_id not in (event.get("deployments") or []):
                continue
            has_cover = True
            for other in events:
                if other.get("type") == "incident" and other.get("incident_id") == event["incident_id"] and other.get("phase") == "resolved":
                    has_resolved = True
                    break
            if has_resolved:
                break
        if has_cover and not has_resolved:
            counts["open_failures"] += 1

    counts["recovered_failures"] = sum(1 for dep in failed_prod if any(
        dep["deployment_id"] in (evt.get("deployments") or [])
        and any(other.get("type") == "incident" and other.get("incident_id") == evt.get("incident_id") and other.get("phase") == "resolved" for other in events)
        for evt in events if evt.get("type") == "incident"
    ))
    counts["open_failures"] = counts["failed_deployments"] - counts["recovered_failures"]

    if counts["deployments"] == 0:
        deployment_frequency = 0.0
    else:
        total_seconds = Decimal((window_to - window_from).total_seconds())
        deployment_frequency = float(quantize_decimal(Decimal(counts["deployments"]) / (total_seconds / Decimal(86400)), 6))

    failure_rate = None if counts["deployments"] == 0 else float(quantize_decimal(Decimal(counts["failed_deployments"]) / Decimal(counts["deployments"]), 6))
    rework_rate = None if counts["deployments"] == 0 else float(quantize_decimal(Decimal(counts["rework_deployments"]) / Decimal(counts["deployments"]), 6))

    change_lead_time_p50 = median_value(lead_durations, digits=0, clamp_negative=True) if lead_durations else None
    recovery_time_p50 = median_value(recovered_times, digits=0, clamp_negative=True) if recovered_times else None

    change_ids_delivered: set[str] = set()
    first_successful_window: dict[str, datetime] = {}
    for dep in production_deployments:
        if dep.get("outcome") != "success":
            continue
        dep_at = parse_iso8601(dep.get("at"), "deployment timestamp")
        for sha in dep.get("commits", []):
            change_id = resolve_change_id(sha, commit_lookup)
            if change_id is None:
                continue
            if change_id not in first_successful_window or dep_at < first_successful_window[change_id]:
                first_successful_window[change_id] = dep_at
            change_ids_delivered.add(change_id)

    true_change_deltas: list[int] = []
    for change_id in sorted(change_ids_delivered):
        if change_id not in change_first_commit:
            continue
        delta = int((first_successful_window[change_id] - change_first_commit[change_id]).total_seconds())
        if delta < 0:
            delta = 0
        true_change_deltas.append(delta)
    true_change_p50 = median_value(true_change_deltas, digits=0, clamp_negative=True) if true_change_deltas else None

    result = {
        "spec_version": "1.0.0",
        "window": {"from": window_from.strftime("%Y-%m-%dT%H:%M:%SZ"), "to": window_to.strftime("%Y-%m-%dT%H:%M:%SZ")},
        "deployment_frequency_per_day": round_float(deployment_frequency, 6),
        "change_lead_time_seconds_p50": change_lead_time_p50,
        "failed_deployment_recovery_time_seconds_p50": recovery_time_p50,
        "change_fail_rate": failure_rate,
        "deployment_rework_rate": rework_rate,
        "counts": counts,
        "anomalies": anomaly_counts,
        "ground_truth": {
            "changes_delivered": len(change_ids_delivered),
            "true_change_lead_time_seconds_p50": true_change_p50,
        },
    }
    return result


@app.get("/health")
def health():
    return {"status": "ok", "service": "svcdesk"}


@app.post("/dora/metrics")
def dora_metrics(body: dict):
    if not isinstance(body, dict):
        return error_response(400, "validation", "request body must be an object")
    window = body.get("window")
    if not isinstance(window, dict):
        return error_response(400, "validation", "window is required")
    try:
        from_dt = parse_iso8601(window.get("from"), "window.from")
        to_dt = parse_iso8601(window.get("to"), "window.to")
    except ValueError as exc:
        return error_response(400, "validation", str(exc))
    if to_dt <= from_dt:
        return error_response(400, "validation", "window.to must be after window.from")
    events = body.get("events")
    if not isinstance(events, list):
        return error_response(400, "validation", "events must be an array")
    try:
        valid_events, _, _, _, _ = validate_and_normalize_event_log(events)
    except ValueError as exc:
        return error_response(400, "validation", str(exc))
    result = compute_metrics_for_events(valid_events, from_dt, to_dt)
    return result


@app.get("/dora/ticket-events")
def ticket_events():
    rows = []
    for ticket in tickets.values():
        for phase, field_name, state_name in [
            ("created", "created_at", "new"),
            ("acknowledged", "acknowledged_at", "acknowledged"),
            ("resolved", "resolved_at", "resolved"),
            ("closed", "closed_at", "closed"),
        ]:
            ts = ticket.get(field_name)
            if ts is None:
                continue
            rows.append({
                "ticket_id": ticket["id"],
                "at": ts,
                "phase": phase,
                "priority": ticket["priority"],
                "state": state_name if phase == "created" else phase,
            })
    rows.sort(key=lambda item: (item["at"], item["ticket_id"]))
    return rows


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