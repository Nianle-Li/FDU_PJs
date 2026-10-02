from __future__ import annotations

import re
from http import HTTPStatus
from typing import Any, Callable

from .constants import BUILDING_TYPES, FACILITY_TYPES, QUERY_CATEGORIES
from .errors import ApiError
from .repositories import CampusRepository

PayloadReader = Callable[[], dict[str, Any]]


def _empty_payload() -> dict[str, Any]:
    return {}


class ApiRouter:
    def __init__(self, repository: CampusRepository):
        self.repository = repository

    def route(
        self,
        method: str,
        path: str,
        query: dict[str, str] | None = None,
        read_payload: PayloadReader = _empty_payload,
    ) -> Any:
        query = query or {}
        repository = self.repository

        if method == "GET" and path == "/api/health":
            return self.health()
        if method == "GET" and path == "/api/meta":
            return {"building_types": BUILDING_TYPES, "facility_types": FACILITY_TYPES, "query_categories": QUERY_CATEGORIES}
        if method == "GET" and path == "/api/users":
            return {"items": repository.users(query)}
        if method == "GET" and path == "/api/campuses":
            return {"items": repository.campuses(query)}
        if method == "GET" and path == "/api/buildings":
            return {"items": repository.buildings(query)}
        if method == "POST" and path == "/api/buildings":
            return {"item": repository.create_building(read_payload())}
        if method == "GET" and path == "/api/facilities":
            return {"items": repository.facilities(query)}
        if method == "POST" and path == "/api/facilities":
            return {"item": repository.create_facility(read_payload())}
        if method == "GET" and path == "/api/courses":
            return {"items": repository.courses(query)}
        if method == "GET" and path == "/api/activities":
            return {"items": repository.activities(query)}
        if method == "POST" and path == "/api/activities":
            return {"item": repository.create_activity(read_payload())}
        if method == "POST" and path == "/api/query-log":
            return {"item": repository.create_query_log(read_payload())}
        if method == "GET" and path == "/api/query-logs":
            return {"items": repository.query_logs(query)}
        if method == "GET" and path == "/api/insights/popular-queries":
            return {"items": repository.popular_queries(query)}
        if method == "GET" and path == "/api/insights/popular-activities":
            return {"items": repository.popular_activities(query)}
        if method == "POST" and path == "/api/nl-query":
            return repository.natural_language_query(read_payload())
        if method == "GET" and path == "/api/sql-examples":
            return {"items": repository.sql_examples()}
        if method == "POST" and path == "/api/import":
            return repository.import_rows(read_payload())

        user_reservations_match = re.fullmatch(r"/api/users/(\d+)/reservations", path)
        if user_reservations_match and method == "GET":
            return {"items": repository.user_reservations(int(user_reservations_match.group(1)))}

        activity_participants_match = re.fullmatch(r"/api/admin/activities/(\d+)/participants", path)
        if activity_participants_match and method == "GET":
            return {"items": repository.activity_participants(int(activity_participants_match.group(1)), query)}

        building_match = re.fullmatch(r"/api/buildings/(\d+)", path)
        if building_match:
            building_id = int(building_match.group(1))
            if method == "PUT":
                return {"item": repository.update_building(building_id, read_payload())}
            if method == "DELETE":
                return repository.delete_building(building_id)

        facility_match = re.fullmatch(r"/api/facilities/(\d+)", path)
        if facility_match:
            facility_id = int(facility_match.group(1))
            if method == "PUT":
                return {"item": repository.update_facility(facility_id, read_payload())}
            if method == "DELETE":
                return repository.delete_facility(facility_id)

        activity_match = re.fullmatch(r"/api/activities/(\d+)", path)
        if activity_match:
            activity_id = int(activity_match.group(1))
            if method == "PUT":
                return {"item": repository.update_activity(activity_id, read_payload())}
            if method == "DELETE":
                return repository.delete_activity(activity_id)

        activity_reserve_match = re.fullmatch(r"/api/activities/(\d+)/reserve", path)
        if activity_reserve_match and method == "POST":
            return {"item": repository.reserve_activity(int(activity_reserve_match.group(1)), read_payload())}

        activity_cancel_match = re.fullmatch(r"/api/activities/(\d+)/reserve/(\d+)", path)
        if activity_cancel_match and method == "DELETE":
            return repository.cancel_activity_reservation(
                int(activity_cancel_match.group(1)),
                int(activity_cancel_match.group(2)),
            )

        raise ApiError(HTTPStatus.NOT_FOUND, "接口不存在")

    def health(self) -> dict[str, Any]:
        try:
            self.repository.ping()
            database = {"connected": True, "mode": self.repository.mode}
        except ApiError as exc:
            database = {"connected": False, "mode": self.repository.mode, "error": exc.message}
        return {"service": "ok", "database": database}
