from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT_DIR = Path(__file__).resolve().parents[1]


class SmokeFailure(Exception):
    pass


def request_json(base_url: str, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(f"{base_url}{path}", data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=10) as response:
            text = response.read().decode("utf-8")
            return json.loads(text) if text else {}
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise SmokeFailure(f"{method} {path} failed with HTTP {exc.code}: {details}") from exc
    except URLError as exc:
        raise SmokeFailure(f"{method} {path} failed: {exc}") from exc


def request_text(base_url: str, path: str) -> str:
    try:
        with urlopen(f"{base_url}{path}", timeout=10) as response:
            return response.read().decode("utf-8", errors="replace")
    except URLError as exc:
        raise SmokeFailure(f"GET {path} failed: {exc}") from exc


def expect_json_error(
    base_url: str,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    expected_statuses: set[int] | None = None,
) -> None:
    expected_statuses = expected_statuses or {400}
    body = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(f"{base_url}{path}", data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=10) as response:
            text = response.read().decode("utf-8", errors="replace")
            raise SmokeFailure(f"{method} {path} unexpectedly succeeded with HTTP {response.status}: {text}")
    except HTTPError as exc:
        if exc.code not in expected_statuses:
            details = exc.read().decode("utf-8", errors="replace")
            raise SmokeFailure(
                f"{method} {path} failed with HTTP {exc.code}, expected {sorted(expected_statuses)}: {details}"
            ) from exc
    except URLError as exc:
        raise SmokeFailure(f"{method} {path} failed: {exc}") from exc


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeFailure(message)


def wait_for_server(base_url: str, deadline_seconds: int = 15) -> None:
    deadline = time.time() + deadline_seconds
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            request_json(base_url, "GET", "/api/health")
            return
        except Exception as exc:  # noqa: BLE001 - keep polling while the dev server warms up.
            last_error = exc
            time.sleep(0.5)
    raise SmokeFailure(f"server did not become ready: {last_error}")


def start_demo_server(port: int) -> subprocess.Popen[Any]:
    env = os.environ.copy()
    env["FCQA_DEMO_MODE"] = "1"
    env["FCQA_PORT"] = str(port)
    return subprocess.Popen(
        [sys.executable, "-u", str(ROOT_DIR / "backend" / "app.py")],
        cwd=ROOT_DIR,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def run_smoke(base_url: str) -> list[str]:
    passed: list[str] = []
    created_activity_id: int | None = None
    created_facility_id: int | None = None
    created_building_id: int | None = None

    health = request_json(base_url, "GET", "/api/health")
    assert_true(health.get("service") == "ok", "health check did not return service=ok")
    passed.append("health")

    index_html = request_text(base_url, "/")
    assert_true("复旦校园百事通" in index_html, "frontend index page did not render expected title")
    assert_true("近期活动" in index_html, "user frontend did not render activity area")
    assert_true("我的行程" in index_html, "user frontend did not render reservation area")
    admin_html = request_text(base_url, "/admin.html")
    assert_true("查询工作台" in admin_html, "admin frontend did not render query workspace")
    assert_true("数据维护" in admin_html, "admin frontend did not render maintenance area")
    passed.append("frontend")

    campuses = request_json(base_url, "GET", "/api/campuses")["items"]
    assert_true(len(campuses) >= 1, "campus query returned no rows")
    passed.append("campus query")

    buildings = request_json(base_url, "GET", "/api/buildings")["items"]
    assert_true(len(buildings) >= 1, "building query returned no rows")
    empty_buildings = request_json(base_url, "GET", "/api/buildings?q=__no_such_building__")["items"]
    assert_true(empty_buildings == [], "empty building search should return an empty list")
    passed.append("building query")

    created_building = request_json(
        base_url,
        "POST",
        "/api/buildings",
        {"name": "Smoke Test Building", "type": "教学楼", "campus_id": campuses[0]["campus_id"]},
    )["item"]
    created_building_id = int(created_building["building_id"])
    expect_json_error(
        base_url,
        "POST",
        "/api/buildings",
        {"name": "Smoke Test Building", "type": "教学楼", "campus_id": campuses[0]["campus_id"]},
    )
    expect_json_error(
        base_url,
        "POST",
        "/api/buildings",
        {"name": "Smoke Test Bad Campus", "type": "教学楼", "campus_id": 999999},
        {400, 404},
    )
    updated_building = request_json(
        base_url,
        "PUT",
        f"/api/buildings/{created_building_id}",
        {"name": "Smoke Test Building Updated", "type": "综合楼", "campus_id": campuses[0]["campus_id"]},
    )["item"]
    assert_true(updated_building["name"] == "Smoke Test Building Updated", "building update did not persist")
    passed.append("building create/update")

    created_facility = request_json(
        base_url,
        "POST",
        "/api/facilities",
        {
            "name": "Smoke Test Room",
            "type": "教室",
            "open_time": "09:00-18:00",
            "building_id": created_building_id,
        },
    )["item"]
    created_facility_id = int(created_facility["facility_id"])
    expect_json_error(
        base_url,
        "POST",
        "/api/facilities",
        {
            "name": "Smoke Test Room",
            "type": "教室",
            "open_time": "09:00-18:00",
            "building_id": created_building_id,
        },
    )
    expect_json_error(
        base_url,
        "POST",
        "/api/facilities",
        {
            "name": "Smoke Test Bad Room",
            "type": "教室",
            "open_time": "09:00-18:00",
            "building_id": 999999,
        },
        {400, 404},
    )
    updated_facility = request_json(
        base_url,
        "PUT",
        f"/api/facilities/{created_facility_id}",
        {
            "name": "Smoke Test Room Updated",
            "type": "自习室",
            "open_time": "08:00-22:00",
            "building_id": created_building_id,
        },
    )["item"]
    assert_true(updated_facility["name"] == "Smoke Test Room Updated", "facility update did not persist")
    passed.append("facility create/update")

    created_activity = request_json(
        base_url,
        "POST",
        "/api/activities",
        {
            "name": "Smoke Test Activity",
            "description": "Smoke test activity description",
            "start_time": "2026-05-30T10:00",
            "end_time": "2026-05-30T11:00",
            "organizer": "Smoke Test",
            "facility_id": created_facility_id,
        },
    )["item"]
    created_activity_id = int(created_activity["activity_id"])
    expect_json_error(
        base_url,
        "POST",
        "/api/activities",
        {
            "name": "Smoke Test Activity",
            "description": "Smoke test activity description",
            "start_time": "2026-05-30T10:00",
            "end_time": "2026-05-30T11:00",
            "organizer": "Smoke Test",
            "facility_id": created_facility_id,
        },
    )
    expect_json_error(
        base_url,
        "POST",
        "/api/activities",
        {
            "name": "Smoke Test Bad Activity",
            "description": "Bad foreign key",
            "start_time": "2026-05-30T10:00",
            "end_time": "2026-05-30T11:00",
            "organizer": "Smoke Test",
            "facility_id": 999999,
        },
        {400, 404},
    )
    expect_json_error(
        base_url,
        "POST",
        "/api/activities",
        {
            "name": "Smoke Test Bad Time",
            "description": "Bad time range",
            "start_time": "2026-05-30T12:00",
            "end_time": "2026-05-30T11:00",
            "organizer": "Smoke Test",
            "facility_id": created_facility_id,
        },
    )
    updated_activity = request_json(
        base_url,
        "PUT",
        f"/api/activities/{created_activity_id}",
        {
            "name": "Smoke Test Activity Updated",
            "description": "Smoke test activity description updated",
            "start_time": "2026-05-30T10:30",
            "end_time": "2026-05-30T11:30",
            "organizer": "Smoke Test",
            "facility_id": created_facility_id,
        },
    )["item"]
    assert_true(updated_activity["name"] == "Smoke Test Activity Updated", "activity update did not persist")
    passed.append("activity create/update")

    courses = request_json(base_url, "GET", "/api/courses")["items"]
    assert_true(len(courses) >= 1, "course query returned no rows")
    passed.append("course join query")

    nl_cases = [
        ("邯郸校区有哪些教学楼？", "campus_buildings"),
        ("第二教学楼有哪些自习室？", "building_facilities"),
        ("李芳老师教什么课？", "teacher_courses"),
        ("数据库系统原理周几上课？", "course_schedule"),
        ("近期有哪些校园活动？", "recent_activities"),
        ("热门活动有哪些？", "hot_activities"),
    ]
    for question, expected_intent in nl_cases:
        nl_result = request_json(base_url, "POST", "/api/nl-query", {"question": question, "user_id": 4})
        assert_true(
            nl_result.get("intent") == expected_intent,
            f"natural language query intent mismatch for {question}: {nl_result.get('intent')}",
        )
        assert_true(nl_result.get("row_count", 0) >= 1, f"natural language query returned no rows for {question}")
        assert_true("SELECT" in nl_result.get("sql", ""), "natural language query did not expose SQL")
    passed.append("natural language query")

    sql_examples = request_json(base_url, "GET", "/api/sql-examples")["items"]
    assert_true(len(sql_examples) >= 7, "sql examples endpoint returned too few examples")
    assert_true(all("sql" in item and "rows" in item for item in sql_examples), "sql examples missing sql or rows")
    passed.append("sql examples")

    log = request_json(
        base_url,
        "POST",
        "/api/query-log",
        {"user_id": 4, "query_category": "其他", "query_content": "Smoke test query"},
    )["item"]
    assert_true("log_id" in log, "query log insert did not return log_id")
    expect_json_error(
        base_url,
        "POST",
        "/api/query-log",
        {"user_id": 4, "query_category": "不存在", "query_content": "Smoke test bad category"},
    )
    passed.append("query log insert")

    history = request_json(base_url, "GET", "/api/query-logs")["items"]
    popular_queries = request_json(base_url, "GET", "/api/insights/popular-queries")["items"]
    popular_activities = request_json(base_url, "GET", "/api/insights/popular-activities")["items"]
    assert_true(len(history) >= 1, "query history returned no rows")
    assert_true(len(popular_queries) >= 1, "popular query categories returned no rows")
    assert_true(len(popular_activities) >= 1, "popular activities returned no rows")
    passed.append("browse insights")

    users = request_json(base_url, "GET", "/api/users")["items"]
    assert_true(len(users) >= 1, "users endpoint returned no rows")
    reservation = request_json(
        base_url,
        "POST",
        f"/api/activities/{created_activity_id}/reserve",
        {"user_id": 4},
    )["item"]
    assert_true(reservation["activity_id"] == created_activity_id, "reservation returned unexpected activity_id")
    request_json(base_url, "POST", f"/api/activities/{created_activity_id}/reserve", {"user_id": 4})
    my_reservations = request_json(base_url, "GET", "/api/users/4/reservations")["items"]
    assert_true(
        any(item["activity_id"] == created_activity_id for item in my_reservations),
        "created reservation was not listed in user reservations",
    )
    assert_true(
        sum(1 for item in my_reservations if item["activity_id"] == created_activity_id) == 1,
        "duplicate reservation should not create duplicate rows",
    )
    request_json(base_url, "DELETE", f"/api/activities/{created_activity_id}/reserve/4")
    expect_json_error(base_url, "DELETE", f"/api/activities/{created_activity_id}/reserve/4", expected_statuses={404})
    passed.append("activity reservation")

    passed.append("boundary error handling")

    request_json(base_url, "DELETE", f"/api/activities/{created_activity_id}")
    created_activity_id = None
    request_json(base_url, "DELETE", f"/api/facilities/{created_facility_id}")
    created_facility_id = None
    request_json(base_url, "DELETE", f"/api/buildings/{created_building_id}")
    created_building_id = None
    passed.append("cleanup delete")

    return passed


def main() -> int:
    parser = argparse.ArgumentParser(description="Run smoke tests against the campus QA demo API.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="running backend base URL")
    parser.add_argument("--start-demo", action="store_true", help="start backend/app.py with FCQA_DEMO_MODE=1")
    parser.add_argument("--port", type=int, default=8899, help="port used with --start-demo")
    args = parser.parse_args()

    process: subprocess.Popen[Any] | None = None
    base_url = args.base_url
    if args.start_demo:
        base_url = f"http://127.0.0.1:{args.port}"
        process = start_demo_server(args.port)

    try:
        wait_for_server(base_url)
        passed = run_smoke(base_url)
    except SmokeFailure as exc:
        print(f"SMOKE TEST FAILED: {exc}", file=sys.stderr)
        return 1
    finally:
        if process is not None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

    print("SMOKE TEST PASSED")
    for item in passed:
        print(f"- {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
