from __future__ import annotations

from datetime import datetime
from http import HTTPStatus
from typing import Any

from ..constants import BUILDING_TYPES, FACILITY_TYPES, QUERY_CATEGORIES
from ..errors import ApiError
from ..nl_query import build_nl_query
from ..privacy import is_activity_participant_roster_question
from ..sql_examples import SQL_EXAMPLES
from ..validation import clean_int, clean_text, parse_datetime_text
from .base import BaseRepository


class DemoRepository(BaseRepository):
    mode = "demo"

    def __init__(self):
        self.user_rows = [
            {"user_id": 1, "name": "张明", "department": "信息科学与工程学院", "role": "教师"},
            {"user_id": 2, "name": "李芳", "department": "计算机科学技术学院", "role": "教师"},
            {"user_id": 3, "name": "王强", "department": "新闻学院", "role": "教师"},
            {"user_id": 4, "name": "陈晨", "department": "计算机科学技术学院", "role": "学生"},
            {"user_id": 5, "name": "赵敏", "department": "新闻学院", "role": "学生"},
            {"user_id": 6, "name": "刘洋", "department": "数学科学学院", "role": "学生"},
            {"user_id": 7, "name": "周宁", "department": "基础医学院", "role": "学生"},
            {"user_id": 8, "name": "孙洁", "department": "体育教学部", "role": "教师"},
        ]
        self.campus_rows = [
            {"campus_id": 1, "name": "邯郸校区", "address": "上海市杨浦区邯郸路220号"},
            {"campus_id": 2, "name": "江湾校区", "address": "上海市杨浦区淞沪路2005号"},
            {"campus_id": 3, "name": "枫林校区", "address": "上海市徐汇区医学院路138号"},
            {"campus_id": 4, "name": "张江校区", "address": "上海市浦东新区张衡路825号"},
        ]
        self.building_rows = [
            {"building_id": 1, "name": "光华楼", "type": "综合楼", "campus_id": 1},
            {"building_id": 2, "name": "第二教学楼", "type": "教学楼", "campus_id": 1},
            {"building_id": 3, "name": "文科图书馆", "type": "图书馆", "campus_id": 1},
            {"building_id": 4, "name": "江湾体育馆", "type": "体育场馆", "campus_id": 2},
            {"building_id": 5, "name": "枫林图书馆", "type": "图书馆", "campus_id": 3},
            {"building_id": 6, "name": "张江实验楼", "type": "实验楼", "campus_id": 4},
        ]
        self.facility_rows = [
            {"facility_id": 1, "name": "光华楼东辅楼102", "type": "教室", "open_time": "每日 08:00-22:00", "building_id": 1},
            {"facility_id": 2, "name": "光华楼报告厅", "type": "报告厅", "open_time": "工作日 09:00-21:00", "building_id": 1},
            {"facility_id": 3, "name": "H2201", "type": "教室", "open_time": "每日 07:30-22:30", "building_id": 2},
            {"facility_id": 4, "name": "H2303自习室", "type": "自习室", "open_time": "每日 08:00-23:00", "building_id": 2},
            {"facility_id": 5, "name": "文科图书馆阅览室", "type": "图书阅览室", "open_time": "周一至周日 08:00-22:00", "building_id": 3},
            {"facility_id": 6, "name": "江湾篮球馆", "type": "体育设施", "open_time": "周一至周日 09:00-21:00", "building_id": 4},
            {"facility_id": 8, "name": "张江AI实验室", "type": "实验室", "open_time": "工作日 09:00-18:00", "building_id": 6},
        ]
        self.activity_rows = [
            {"activity_id": 1, "name": "新生数据库实践讲座", "description": "介绍数据库建模和查询优化。", "start_time": "2026-05-20 14:00:00", "end_time": "2026-05-20 16:00:00", "organizer": "计算机科学技术学院", "facility_id": 2},
            {"activity_id": 2, "name": "校园开放日导览", "description": "邯郸校区建筑与学习空间导览。", "start_time": "2026-05-18 09:00:00", "end_time": "2026-05-18 11:00:00", "organizer": "招生办公室", "facility_id": 1},
            {"activity_id": 3, "name": "江湾篮球友谊赛", "description": "校内篮球社团交流赛。", "start_time": "2026-05-24 18:00:00", "end_time": "2026-05-24 20:00:00", "organizer": "体育教学部", "facility_id": 6},
        ]
        self.user_activity_rows = [
            {"user_id": 4, "activity_id": 1, "status": "待参加"},
            {"user_id": 5, "activity_id": 1, "status": "待参加"},
            {"user_id": 6, "activity_id": 1, "status": "已签到"},
            {"user_id": 4, "activity_id": 2, "status": "已完成"},
            {"user_id": 5, "activity_id": 2, "status": "已完成"},
            {"user_id": 6, "activity_id": 3, "status": "待参加"},
        ]
        self.query_log_rows = [
            {"log_id": 1, "user_id": 4, "user_name": "陈晨", "query_category": "建筑", "query_content": "邯郸校区有哪些教学楼", "query_time": "2026-05-10 09:10:00"},
            {"log_id": 2, "user_id": 4, "user_name": "陈晨", "query_category": "设施", "query_content": "第二教学楼哪里可以自习", "query_time": "2026-05-10 09:12:00"},
            {"log_id": 3, "user_id": 5, "user_name": "赵敏", "query_category": "课程", "query_content": "数据库系统原理周几上课", "query_time": "2026-05-10 10:20:00"},
            {"log_id": 4, "user_id": 6, "user_name": "刘洋", "query_category": "教师", "query_content": "李芳老师这学期教什么课", "query_time": "2026-05-10 11:05:00"},
            {"log_id": 5, "user_id": 7, "user_name": "周宁", "query_category": "活动", "query_content": "近期有哪些校园活动", "query_time": "2026-05-10 13:30:00"},
            {"log_id": 6, "user_id": 5, "user_name": "赵敏", "query_category": "统计", "query_content": "统计每个校区建筑数量", "query_time": "2026-05-10 14:00:00"},
            {"log_id": 7, "user_id": 4, "user_name": "陈晨", "query_category": "活动", "query_content": "数据库实践讲座在哪里", "query_time": "2026-05-10 15:18:00"},
            {"log_id": 8, "user_id": 6, "user_name": "刘洋", "query_category": "设施", "query_content": "江湾篮球馆开放时间", "query_time": "2026-05-10 16:40:00"},
            {"log_id": 9, "user_id": 7, "user_name": "周宁", "query_category": "课程", "query_content": "医学统计学上课地点", "query_time": "2026-05-10 17:00:00"},
            {"log_id": 10, "user_id": 4, "user_name": "陈晨", "query_category": "用户", "query_content": "查看我的账户信息", "query_time": "2026-05-10 18:15:00"},
        ]
        self.next_building_id = 7
        self.next_facility_id = 9
        self.next_activity_id = 4
        self.next_log_id = 11

    def ping(self) -> bool:
        return True

    def _campus_name(self, campus_id: int) -> str:
        return next((c["name"] for c in self.campus_rows if c["campus_id"] == campus_id), "")

    def _campus(self, campus_id: int) -> dict[str, Any] | None:
        return next((c for c in self.campus_rows if c["campus_id"] == campus_id), None)

    def _building(self, building_id: int) -> dict[str, Any] | None:
        return next((b for b in self.building_rows if b["building_id"] == building_id), None)

    def _facility(self, facility_id: int) -> dict[str, Any] | None:
        return next((f for f in self.facility_rows if f["facility_id"] == facility_id), None)

    def _user(self, user_id: int) -> dict[str, Any] | None:
        return next((u for u in self.user_rows if u["user_id"] == user_id), None)

    def _activity(self, activity_id: int) -> dict[str, Any] | None:
        return next((a for a in self.activity_rows if a["activity_id"] == activity_id), None)

    def _activity_participant_count(self, activity_id: int) -> int:
        return sum(1 for row in self.user_activity_rows if row["activity_id"] == activity_id)

    def _require_campus(self, campus_id: int) -> None:
        if self._campus(campus_id) is None:
            raise ApiError(HTTPStatus.NOT_FOUND, "校区不存在")

    def _require_building(self, building_id: int) -> None:
        if self._building(building_id) is None:
            raise ApiError(HTTPStatus.NOT_FOUND, "建筑不存在")

    def _require_facility(self, facility_id: int) -> None:
        if self._facility(facility_id) is None:
            raise ApiError(HTTPStatus.NOT_FOUND, "设施不存在")

    def _require_building_unique(self, campus_id: int, name: str, *, exclude_id: int | None = None) -> None:
        if any(
            row["campus_id"] == campus_id and row["name"] == name and row["building_id"] != exclude_id
            for row in self.building_rows
        ):
            raise ApiError(HTTPStatus.BAD_REQUEST, "同一校区下建筑名称不能重复")

    def _require_facility_unique(self, building_id: int, name: str, *, exclude_id: int | None = None) -> None:
        if any(
            row["building_id"] == building_id and row["name"] == name and row["facility_id"] != exclude_id
            for row in self.facility_rows
        ):
            raise ApiError(HTTPStatus.BAD_REQUEST, "同一建筑下设施名称不能重复")

    def _require_activity_unique(
        self,
        facility_id: int,
        name: str,
        start_time: str | None,
        *,
        exclude_id: int | None = None,
    ) -> None:
        if any(
            row["facility_id"] == facility_id
            and row["name"] == name
            and row["start_time"] == start_time
            and row["activity_id"] != exclude_id
            for row in self.activity_rows
        ):
            raise ApiError(HTTPStatus.BAD_REQUEST, "同一设施同一时间的活动名称不能重复")

    def _require_activity_time_range(self, start_time: str | None, end_time: str | None) -> None:
        if end_time and start_time and datetime.fromisoformat(end_time) < datetime.fromisoformat(start_time):
            raise ApiError(HTTPStatus.BAD_REQUEST, "活动结束时间不能早于开始时间")

    def _decorate_building(self, row: dict[str, Any]) -> dict[str, Any]:
        return {**row, "campus_name": self._campus_name(row["campus_id"])}

    def _decorate_facility(self, row: dict[str, Any]) -> dict[str, Any]:
        building = self._building(row["building_id"]) or {}
        return {
            **row,
            "building_name": building.get("name", ""),
            "campus_name": self._campus_name(building.get("campus_id", 0)),
        }

    def _decorate_activity(self, row: dict[str, Any]) -> dict[str, Any]:
        facility = self._facility(row["facility_id"]) or {}
        building = self._building(facility.get("building_id", 0)) or {}
        return {
            **row,
            "facility_name": facility.get("name", ""),
            "building_name": building.get("name", ""),
            "campus_name": self._campus_name(building.get("campus_id", 0)),
            "participant_count": self._activity_participant_count(row["activity_id"]),
        }

    def _filter(self, rows: list[dict[str, Any]], q: str, keys: list[str]) -> list[dict[str, Any]]:
        if not q:
            return rows
        return [row for row in rows if any(q in str(row.get(key, "")) for key in keys)]

    def _limit(self, query: dict[str, str], default: int = 20, maximum: int = 100) -> int:
        try:
            value = int(query.get("limit", default))
        except ValueError as exc:
            raise ApiError(HTTPStatus.BAD_REQUEST, "limit 必须是整数") from exc
        return max(1, min(value, maximum))

    def campuses(self, query: dict[str, str]) -> list[dict[str, Any]]:
        return self._filter(self.campus_rows, query.get("q", "").strip(), ["name", "address"])

    def users(self, query: dict[str, str]) -> list[dict[str, Any]]:
        return self._filter(self.user_rows, query.get("q", "").strip(), ["name", "department", "role"])

    def buildings(self, query: dict[str, str]) -> list[dict[str, Any]]:
        rows = [self._decorate_building(row) for row in self.building_rows]
        if query.get("campus_id"):
            rows = [row for row in rows if row["campus_id"] == int(query["campus_id"])]
        if query.get("type"):
            rows = [row for row in rows if row["type"] == query["type"].strip()]
        return self._filter(rows, query.get("q", "").strip(), ["name", "type", "campus_name"])

    def create_building(self, payload: dict[str, Any]) -> dict[str, Any]:
        name = clean_text(payload, "name")
        building_type = clean_text(payload, "type", default="其他")
        campus_id = clean_int(payload, "campus_id")
        if building_type not in BUILDING_TYPES:
            raise ApiError(HTTPStatus.BAD_REQUEST, "建筑类型不在允许范围内")
        self._require_campus(campus_id)
        self._require_building_unique(campus_id, name)
        row = {
            "building_id": self.next_building_id,
            "name": name,
            "type": building_type,
            "campus_id": campus_id,
        }
        self.next_building_id += 1
        self.building_rows.append(row)
        return self._decorate_building(row)

    def update_building(self, building_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        row = self._building(building_id)
        if row is None:
            raise ApiError(HTTPStatus.NOT_FOUND, "建筑不存在")
        name = clean_text(payload, "name")
        building_type = clean_text(payload, "type")
        campus_id = clean_int(payload, "campus_id")
        if building_type not in BUILDING_TYPES:
            raise ApiError(HTTPStatus.BAD_REQUEST, "建筑类型不在允许范围内")
        self._require_campus(campus_id)
        self._require_building_unique(campus_id, name, exclude_id=building_id)
        row.update({"name": name, "type": building_type, "campus_id": campus_id})
        return self._decorate_building(row)

    def delete_building(self, building_id: int) -> dict[str, Any]:
        if any(f["building_id"] == building_id for f in self.facility_rows):
            raise ApiError(HTTPStatus.BAD_REQUEST, "该建筑下仍有设施，演示约束模拟为禁止删除")
        before = len(self.building_rows)
        self.building_rows = [row for row in self.building_rows if row["building_id"] != building_id]
        if len(self.building_rows) == before:
            raise ApiError(HTTPStatus.NOT_FOUND, "建筑不存在")
        return {"deleted": 1}

    def facilities(self, query: dict[str, str]) -> list[dict[str, Any]]:
        rows = [self._decorate_facility(row) for row in self.facility_rows]
        if query.get("building_id"):
            rows = [row for row in rows if row["building_id"] == int(query["building_id"])]
        if query.get("campus_id"):
            rows = [row for row in rows if row["campus_name"] == self._campus_name(int(query["campus_id"]))]
        if query.get("type"):
            rows = [row for row in rows if row["type"] == query["type"].strip()]
        return self._filter(rows, query.get("q", "").strip(), ["name", "type", "building_name", "campus_name"])

    def create_facility(self, payload: dict[str, Any]) -> dict[str, Any]:
        name = clean_text(payload, "name")
        facility_type = clean_text(payload, "type", default="其他")
        open_time = clean_text(payload, "open_time", default="以现场公告为准")
        building_id = clean_int(payload, "building_id")
        if facility_type not in FACILITY_TYPES:
            raise ApiError(HTTPStatus.BAD_REQUEST, "设施类型不在允许范围内")
        self._require_building(building_id)
        self._require_facility_unique(building_id, name)
        row = {
            "facility_id": self.next_facility_id,
            "name": name,
            "type": facility_type,
            "open_time": open_time,
            "building_id": building_id,
        }
        self.next_facility_id += 1
        self.facility_rows.append(row)
        return self._decorate_facility(row)

    def update_facility(self, facility_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        row = self._facility(facility_id)
        if row is None:
            raise ApiError(HTTPStatus.NOT_FOUND, "设施不存在")
        name = clean_text(payload, "name")
        facility_type = clean_text(payload, "type")
        open_time = clean_text(payload, "open_time")
        building_id = clean_int(payload, "building_id")
        if facility_type not in FACILITY_TYPES:
            raise ApiError(HTTPStatus.BAD_REQUEST, "设施类型不在允许范围内")
        self._require_building(building_id)
        self._require_facility_unique(building_id, name, exclude_id=facility_id)
        row.update({
            "name": name,
            "type": facility_type,
            "open_time": open_time,
            "building_id": building_id,
        })
        return self._decorate_facility(row)

    def delete_facility(self, facility_id: int) -> dict[str, Any]:
        if any(activity["facility_id"] == facility_id for activity in self.activity_rows):
            raise ApiError(HTTPStatus.BAD_REQUEST, "该设施仍被活动引用，演示约束模拟为禁止删除")
        before = len(self.facility_rows)
        self.facility_rows = [row for row in self.facility_rows if row["facility_id"] != facility_id]
        if len(self.facility_rows) == before:
            raise ApiError(HTTPStatus.NOT_FOUND, "设施不存在")
        return {"deleted": 1}

    def courses(self, query: dict[str, str]) -> list[dict[str, Any]]:
        rows = [
            {"offering_id": 1, "course_code": "COMP130015.01", "semester": "2025-2026 春季学期", "course_master_code": "COMP130015", "course_name": "数据库系统原理", "teachers": "李芳", "departments": "计算与智能创新学院", "teacher_titles": "教授", "schedules": "周一 3-4节 每周 @ H2201；周三 3-4节 双周 @ 张江AI实验室"},
            {"offering_id": 3, "course_code": "COMP130136.01", "semester": "2025-2026 春季学期", "course_master_code": "COMP130136", "course_name": "人工智能导论", "teachers": "李芳", "departments": "计算与智能创新学院", "teacher_titles": "教授", "schedules": "周四 7-8节 每周 @ 张江AI实验室"},
            {"offering_id": 5, "course_code": "JOUR110001.01", "semester": "2025-2026 春季学期", "course_master_code": "JOUR110001", "course_name": "新闻传播导论", "teachers": "王强", "departments": "新闻学院", "teacher_titles": "副教授", "schedules": "周二 3-4节 每周 @ 文科图书馆阅览室"},
        ]
        if query.get("course_name"):
            term = query["course_name"].strip()
            rows = [row for row in rows if term in row["course_name"]]
        if query.get("course_code"):
            term = query["course_code"].strip()
            rows = [row for row in rows if term in row["course_code"]]
        if query.get("teacher"):
            term = query["teacher"].strip()
            rows = [row for row in rows if term in row["teachers"]]
        if query.get("department"):
            term = query["department"].strip()
            rows = [row for row in rows if term in row["departments"]]
        if query.get("semester"):
            term = query["semester"].strip()
            rows = [row for row in rows if term in row["semester"]]
        if query.get("day_of_week"):
            term = query["day_of_week"].strip()
            rows = [row for row in rows if term in row["schedules"]]
        return self._filter(rows, query.get("q", "").strip(), ["course_name", "course_code", "teachers", "departments"])

    def activities(self, query: dict[str, str]) -> list[dict[str, Any]]:
        rows = [self._decorate_activity(row) for row in self.activity_rows]
        if query.get("organizer"):
            term = query["organizer"].strip()
            rows = [row for row in rows if term in row["organizer"]]
        if query.get("facility_id"):
            rows = [row for row in rows if row["facility_id"] == int(query["facility_id"])]
        if query.get("campus_id"):
            rows = [row for row in rows if row["campus_name"] == self._campus_name(int(query["campus_id"]))]
        if query.get("start_from"):
            start_from = parse_datetime_text(query["start_from"]) or ""
            rows = [row for row in rows if str(row["start_time"]) >= start_from]
        if query.get("start_to"):
            start_to = parse_datetime_text(query["start_to"]) or ""
            rows = [row for row in rows if str(row["start_time"]) <= start_to]
        return self._filter(rows, query.get("q", "").strip(), ["name", "description", "organizer", "facility_name"])

    def create_activity(self, payload: dict[str, Any]) -> dict[str, Any]:
        name = clean_text(payload, "name")
        description = clean_text(payload, "description", default="暂无简介")
        start_time = parse_datetime_text(clean_text(payload, "start_time"))
        end_time = parse_datetime_text(clean_text(payload, "end_time", required=False, default=""))
        organizer = clean_text(payload, "organizer", default="未填写")
        facility_id = clean_int(payload, "facility_id")
        self._require_facility(facility_id)
        self._require_activity_time_range(start_time, end_time)
        self._require_activity_unique(facility_id, name, start_time)
        row = {
            "activity_id": self.next_activity_id,
            "name": name,
            "description": description,
            "start_time": start_time,
            "end_time": end_time,
            "organizer": organizer,
            "facility_id": facility_id,
        }
        self.next_activity_id += 1
        self.activity_rows.append(row)
        return self._decorate_activity(row)

    def update_activity(self, activity_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        row = next((item for item in self.activity_rows if item["activity_id"] == activity_id), None)
        if row is None:
            raise ApiError(HTTPStatus.NOT_FOUND, "活动不存在")
        name = clean_text(payload, "name")
        description = clean_text(payload, "description")
        start_time = parse_datetime_text(clean_text(payload, "start_time"))
        end_time = parse_datetime_text(clean_text(payload, "end_time", required=False, default=""))
        organizer = clean_text(payload, "organizer")
        facility_id = clean_int(payload, "facility_id")
        self._require_facility(facility_id)
        self._require_activity_time_range(start_time, end_time)
        self._require_activity_unique(facility_id, name, start_time, exclude_id=activity_id)
        row.update({
            "name": name,
            "description": description,
            "start_time": start_time,
            "end_time": end_time,
            "organizer": organizer,
            "facility_id": facility_id,
        })
        return self._decorate_activity(row)

    def delete_activity(self, activity_id: int) -> dict[str, Any]:
        before = len(self.activity_rows)
        self.activity_rows = [row for row in self.activity_rows if row["activity_id"] != activity_id]
        if len(self.activity_rows) == before:
            raise ApiError(HTTPStatus.NOT_FOUND, "活动不存在")
        return {"deleted": 1}

    def create_query_log(self, payload: dict[str, Any]) -> dict[str, Any]:
        user_id = clean_int(payload, "user_id")
        if self._user(user_id) is None:
            raise ApiError(HTTPStatus.NOT_FOUND, "用户不存在")
        category = clean_text(payload, "query_category", default="其他")
        if category not in QUERY_CATEGORIES:
            raise ApiError(HTTPStatus.BAD_REQUEST, "查询类别不在允许范围内")
        row = {
            "log_id": self.next_log_id,
            "user_id": user_id,
            "user_name": f"用户{payload.get('user_id', '')}",
            "query_category": category,
            "query_content": clean_text(payload, "query_content"),
            "query_time": datetime.now().isoformat(sep=" ", timespec="seconds"),
        }
        self.next_log_id += 1
        self.query_log_rows.append(row)
        return row

    def query_logs(self, query: dict[str, str]) -> list[dict[str, Any]]:
        rows = list(self.query_log_rows)
        if query.get("query_category"):
            rows = [row for row in rows if row["query_category"] == query["query_category"].strip()]
        if query.get("user_id"):
            rows = [row for row in rows if row["user_id"] == int(query["user_id"])]
        rows = self._filter(rows, query.get("q", "").strip(), ["query_category", "query_content", "user_name"])
        rows.sort(key=lambda row: (str(row["query_time"]), int(row["log_id"])), reverse=True)
        return rows[: self._limit(query)]

    def popular_queries(self, query: dict[str, str]) -> list[dict[str, Any]]:
        rows = list(self.query_log_rows)
        if query.get("user_id"):
            rows = [row for row in rows if row["user_id"] == int(query["user_id"])]
        grouped: dict[str, dict[str, Any]] = {}
        for row in rows:
            category = row["query_category"]
            current = grouped.setdefault(
                category,
                {
                    "query_category": category,
                    "query_count": 0,
                    "latest_query": row["query_content"],
                    "latest_query_time": row["query_time"],
                },
            )
            current["query_count"] += 1
            if str(row["query_time"]) >= str(current["latest_query_time"]):
                current["latest_query"] = row["query_content"]
                current["latest_query_time"] = row["query_time"]
        rows = sorted(grouped.values(), key=lambda row: (-int(row["query_count"]), row["query_category"]))
        return rows[: self._limit(query, default=10)]

    def popular_activities(self, query: dict[str, str]) -> list[dict[str, Any]]:
        rows = sorted(self.activities({}), key=lambda row: (-int(row.get("participant_count", 0)), str(row["start_time"])))
        return [
            {
                "activity_id": row["activity_id"],
                "activity_name": row["name"],
                "start_time": row["start_time"],
                "organizer": row["organizer"],
                "facility_name": row["facility_name"],
                "building_name": row["building_name"],
                "campus_name": row["campus_name"],
                "participant_count": row["participant_count"],
            }
            for row in rows[: self._limit(query, default=10)]
        ]

    def activity_participants(self, activity_id: int, query: dict[str, str]) -> list[dict[str, Any]]:
        if self._activity(activity_id) is None:
            raise ApiError(HTTPStatus.NOT_FOUND, "活动不存在")
        rows = [row for row in self.user_activity_rows if row["activity_id"] == activity_id]
        if query.get("status"):
            rows = [row for row in rows if row["status"] == query["status"].strip()]
        q = query.get("q", "").strip()
        items = []
        for row in rows:
            user = self._user(row["user_id"]) or {}
            activity = self._activity(row["activity_id"]) or {}
            item = {
                "activity_id": row["activity_id"],
                "activity_name": activity.get("name", ""),
                "user_id": row["user_id"],
                "user_name": user.get("name", f"用户{row['user_id']}"),
                "department": user.get("department", ""),
                "role": user.get("role", "用户"),
                "status": row["status"],
            }
            if q and q not in item["user_name"] and q not in item["department"]:
                continue
            items.append(item)
        return items[: self._limit(query, default=50, maximum=200)]

    def _decorate_reservation(self, row: dict[str, Any]) -> dict[str, Any]:
        user = self._user(row["user_id"]) or {}
        activity = self._activity(row["activity_id"])
        if activity is None:
            raise ApiError(HTTPStatus.NOT_FOUND, "活动不存在")
        decorated = self._decorate_activity(activity)
        return {
            "user_id": row["user_id"],
            "user_name": user.get("name", f"用户{row['user_id']}"),
            "status": row["status"],
            "activity_id": row["activity_id"],
            "activity_name": decorated["name"],
            "description": decorated["description"],
            "start_time": decorated["start_time"],
            "end_time": decorated["end_time"],
            "organizer": decorated["organizer"],
            "facility_id": decorated["facility_id"],
            "facility_name": decorated["facility_name"],
            "building_name": decorated["building_name"],
            "campus_name": decorated["campus_name"],
        }

    def user_reservations(self, user_id: int) -> list[dict[str, Any]]:
        rows = [row for row in self.user_activity_rows if row["user_id"] == user_id]
        return [self._decorate_reservation(row) for row in rows if self._activity(row["activity_id"]) is not None]

    def reserve_activity(self, activity_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        user_id = clean_int(payload, "user_id")
        if self._user(user_id) is None:
            raise ApiError(HTTPStatus.NOT_FOUND, "用户不存在")
        if self._activity(activity_id) is None:
            raise ApiError(HTTPStatus.NOT_FOUND, "活动不存在")
        row = next((item for item in self.user_activity_rows if item["user_id"] == user_id and item["activity_id"] == activity_id), None)
        if row is None:
            row = {"user_id": user_id, "activity_id": activity_id, "status": "待参加"}
            self.user_activity_rows.append(row)
        else:
            row["status"] = "待参加"
        return self._decorate_reservation(row)

    def cancel_activity_reservation(self, activity_id: int, user_id: int) -> dict[str, Any]:
        before = len(self.user_activity_rows)
        self.user_activity_rows = [
            row for row in self.user_activity_rows if not (row["activity_id"] == activity_id and row["user_id"] == user_id)
        ]
        if len(self.user_activity_rows) == before:
            raise ApiError(HTTPStatus.NOT_FOUND, "预约记录不存在")
        return {"deleted": 1}

    def sql_examples(self) -> list[dict[str, Any]]:
        return [
            {**SQL_EXAMPLES[0], "rows": [{"campus_name": "邯郸校区", "building_name": "光华楼", "type": "综合楼"}, {"campus_name": "邯郸校区", "building_name": "第二教学楼", "type": "教学楼"}]},
            {**SQL_EXAMPLES[1], "rows": [{"building_name": "第二教学楼", "facility_name": "H2201", "type": "教室", "open_time": "每日 07:30-22:30"}, {"building_name": "第二教学楼", "facility_name": "H2303自习室", "type": "自习室", "open_time": "每日 08:00-23:00"}]},
            {**SQL_EXAMPLES[2], "rows": [{"teacher_name": "李芳", "course_name": "数据库系统原理", "course_code": "COMP130015.01", "semester": "2025-2026 春季学期"}, {"teacher_name": "李芳", "course_name": "人工智能导论", "course_code": "COMP130136.01", "semester": "2025-2026 春季学期"}]},
            {**SQL_EXAMPLES[3], "rows": [{"activity_name": "校园开放日导览", "start_time": "2026-05-18 09:00:00", "campus_name": "邯郸校区", "building_name": "光华楼", "facility_name": "光华楼东辅楼102"}]},
            {**SQL_EXAMPLES[4], "rows": [{"campus_name": "邯郸校区", "type": "教学楼", "building_count": 1}, {"campus_name": "邯郸校区", "type": "图书馆", "building_count": 1}]},
            {**SQL_EXAMPLES[5], "rows": [{"query_category": "活动", "query_count": 2}, {"query_category": "设施", "query_count": 2}]},
            {**SQL_EXAMPLES[6], "rows": [{"activity_name": "新生数据库实践讲座", "participant_count": 3}, {"activity_name": "校园开放日导览", "participant_count": 2}]},
        ]

    def natural_language_query(self, payload: dict[str, Any]) -> dict[str, Any]:
        question = clean_text(payload, "question")
        user_id = payload.get("user_id", 4)
        role = str(payload.get("role", "user")).strip().lower()
        if role != "admin" and is_activity_participant_roster_question(question):
            raise ApiError(HTTPStatus.FORBIDDEN, "用户端不能查看活动参与者名单，请使用管理员端查看。")
        plan = build_nl_query(question)
        if plan["intent"] == "query_category_stats":
            rows = self.popular_queries({"user_id": str(user_id), "limit": "10"})
        else:
            rows = self.demo_nl_rows(plan)
        try:
            self.create_query_log(
                {
                    "user_id": user_id,
                    "query_category": plan["category"],
                    "query_content": question,
                }
            )
        except ApiError:
            pass
        return {
            "question": question,
            "intent": plan["intent"],
            "title": plan["title"],
            "category": plan["category"],
            "sql": plan["sql"],
            "params": list(plan["params"]),
            "rows": rows,
            "row_count": len(rows),
            "answer": self.summarize_answer(plan, rows),
        }

    def demo_nl_rows(self, plan: dict[str, Any]) -> list[dict[str, Any]]:
        intent = plan["intent"]
        params = list(plan["params"])
        if intent == "campus_buildings":
            campus = params[0].strip("%") if params else ""
            rows = [row for row in self.buildings({}) if not campus or campus in row["campus_name"]]
            if len(params) > 1:
                rows = [row for row in rows if row["type"] == params[1]]
            return [{"campus_name": row["campus_name"], "building_name": row["name"], "type": row["type"]} for row in rows]
        if intent == "building_facilities":
            building = params[0].strip("%") if params else ""
            rows = [row for row in self.facilities({}) if not building or building in row["building_name"]]
            if len(params) > 1:
                rows = [row for row in rows if row["type"] == params[1]]
            return [{"building_name": row["building_name"], "facility_name": row["name"], "type": row["type"], "open_time": row["open_time"]} for row in rows]
        if intent == "teacher_courses":
            teacher = params[0].strip("%") if params else ""
            return [row for row in self.courses({}) if teacher in row["teachers"]]
        if intent == "course_schedule":
            term = params[0].strip("%") if params else ""
            return [row for row in self.courses({}) if term in row["course_name"] or term in row["course_code"]]
        if intent == "recent_activities":
            return self.activities({})
        if intent == "building_stats":
            counts: dict[tuple[str, str], int] = {}
            for row in self.buildings({}):
                key = (row["campus_name"], row["type"])
                counts[key] = counts.get(key, 0) + 1
            return [{"campus_name": campus, "type": building_type, "building_count": count} for (campus, building_type), count in sorted(counts.items())]
        if intent == "query_category_stats":
            return [{"query_category": "活动", "query_count": 2}, {"query_category": "设施", "query_count": 2}, {"query_category": "课程", "query_count": 2}]
        if intent == "hot_activities":
            rows = sorted(self.activities({}), key=lambda row: (-int(row.get("participant_count", 0)), row["name"]))
            return [{"activity_name": row["name"], "participant_count": row["participant_count"]} for row in rows]
        term = params[0].strip("%") if params else ""
        combined: list[dict[str, Any]] = []
        combined.extend({"source": "建筑", "title": row["name"], "detail": f"{row['type']}，{row['campus_name']}"} for row in self.buildings({"q": term}))
        combined.extend({"source": "设施", "title": row["name"], "detail": f"{row['type']}，{row['building_name']}，开放时间：{row['open_time']}"} for row in self.facilities({"q": term}))
        combined.extend({"source": "课程", "title": row["course_name"], "detail": f"{row['course_code']}，{row['semester']}"} for row in self.courses({"q": term}))
        combined.extend({"source": "活动", "title": row["name"], "detail": f"{row['organizer']}，{row['start_time']}"} for row in self.activities({"q": term}))
        return combined[:30]
