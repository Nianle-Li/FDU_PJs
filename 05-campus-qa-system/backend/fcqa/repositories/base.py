from __future__ import annotations

from http import HTTPStatus
from typing import Any, Protocol

from ..errors import ApiError


class CampusRepository(Protocol):
    mode: str

    def ping(self) -> bool: ...

    def users(self, query: dict[str, str]) -> list[dict[str, Any]]: ...

    def campuses(self, query: dict[str, str]) -> list[dict[str, Any]]: ...

    def buildings(self, query: dict[str, str]) -> list[dict[str, Any]]: ...

    def create_building(self, payload: dict[str, Any]) -> dict[str, Any]: ...

    def update_building(self, building_id: int, payload: dict[str, Any]) -> dict[str, Any]: ...

    def delete_building(self, building_id: int) -> dict[str, Any]: ...

    def facilities(self, query: dict[str, str]) -> list[dict[str, Any]]: ...

    def create_facility(self, payload: dict[str, Any]) -> dict[str, Any]: ...

    def update_facility(self, facility_id: int, payload: dict[str, Any]) -> dict[str, Any]: ...

    def delete_facility(self, facility_id: int) -> dict[str, Any]: ...

    def courses(self, query: dict[str, str]) -> list[dict[str, Any]]: ...

    def activities(self, query: dict[str, str]) -> list[dict[str, Any]]: ...

    def create_activity(self, payload: dict[str, Any]) -> dict[str, Any]: ...

    def update_activity(self, activity_id: int, payload: dict[str, Any]) -> dict[str, Any]: ...

    def delete_activity(self, activity_id: int) -> dict[str, Any]: ...

    def create_query_log(self, payload: dict[str, Any]) -> dict[str, Any]: ...

    def query_logs(self, query: dict[str, str]) -> list[dict[str, Any]]: ...

    def popular_queries(self, query: dict[str, str]) -> list[dict[str, Any]]: ...

    def popular_activities(self, query: dict[str, str]) -> list[dict[str, Any]]: ...

    def activity_participants(self, activity_id: int, query: dict[str, str]) -> list[dict[str, Any]]: ...

    def user_reservations(self, user_id: int) -> list[dict[str, Any]]: ...

    def reserve_activity(self, activity_id: int, payload: dict[str, Any]) -> dict[str, Any]: ...

    def cancel_activity_reservation(self, activity_id: int, user_id: int) -> dict[str, Any]: ...

    def sql_examples(self) -> list[dict[str, Any]]: ...

    def natural_language_query(self, payload: dict[str, Any]) -> dict[str, Any]: ...

    def import_rows(self, payload: dict[str, Any]) -> dict[str, Any]: ...


class BaseRepository:
    def import_rows(self, payload: dict[str, Any]) -> dict[str, Any]:
        entity_aliases = {
            "building": "buildings",
            "buildings": "buildings",
            "facility": "facilities",
            "facilities": "facilities",
            "activity": "activities",
            "activities": "activities",
            "query_log": "query_logs",
            "query_logs": "query_logs",
        }
        creator_names = {
            "buildings": "create_building",
            "facilities": "create_facility",
            "activities": "create_activity",
            "query_logs": "create_query_log",
        }
        raw_entity = str(payload.get("entity", "")).strip()
        entity = entity_aliases.get(raw_entity)
        if entity is None:
            raise ApiError(HTTPStatus.BAD_REQUEST, "导入对象只支持 buildings、facilities、activities、query_logs")
        rows = payload.get("rows")
        if not isinstance(rows, list):
            raise ApiError(HTTPStatus.BAD_REQUEST, "rows 必须是数组")
        if len(rows) > 200:
            raise ApiError(HTTPStatus.BAD_REQUEST, "单次最多导入 200 行")

        creator = getattr(self, creator_names[entity])
        items: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []
        for index, row in enumerate(rows, start=1):
            if not isinstance(row, dict):
                errors.append({"row": index, "error": "该行不是对象"})
                continue
            cleaned = {str(key).strip(): value for key, value in row.items() if str(key).strip()}
            try:
                items.append(creator(cleaned))
            except ApiError as exc:
                errors.append({"row": index, "error": exc.message})
            except Exception as exc:  # noqa: BLE001 - keep importing later CSV rows.
                errors.append({"row": index, "error": str(exc)})
        return {
            "entity": entity,
            "created_count": len(items),
            "failed_count": len(errors),
            "items": items,
            "errors": errors,
        }

    def summarize_answer(self, plan: dict[str, Any], rows: list[dict[str, Any]]) -> str:
        if not rows:
            return f"没有找到与“{plan['title']}”匹配的数据。"
        intent = plan["intent"]
        detail_intents = {
            "campus_buildings",
            "building_facilities",
            "teacher_courses",
            "course_schedule",
            "recent_activities",
            "global_search",
        }
        if intent in detail_intents:
            return f"已识别为“{plan['title']}”，共返回 {len(rows)} 条结果。"
        if intent in {"building_stats", "query_category_stats", "hot_activities"}:
            return f"已完成“{plan['title']}”统计，共返回 {len(rows)} 条聚合结果。"
        return f"查询完成，共返回 {len(rows)} 条结果。"
