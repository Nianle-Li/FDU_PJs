from __future__ import annotations

from http import HTTPStatus
from typing import Any

from psycopg.errors import ForeignKeyViolation

from ..config import LlmConfig
from ..constants import BUILDING_TYPES, FACILITY_TYPES, QUERY_CATEGORIES
from ..errors import ApiError
from ..llm_query import LlmQueryError, build_llm_query
from ..nl_query import build_nl_query
from ..privacy import is_activity_participant_roster_question
from ..sql_examples import SQL_EXAMPLES
from ..validation import clean_int, clean_text, parse_datetime_text
from .base import BaseRepository


class PostgresRepository(BaseRepository):
    mode = "postgres"

    def __init__(self, dsn: str, llm_config: LlmConfig | None = None):
        self.dsn = dsn
        self.llm_config = llm_config

    def _connect(self):
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise ApiError(
                HTTPStatus.SERVICE_UNAVAILABLE,
                "缺少 psycopg 驱动，请先执行：python -m pip install -r backend/requirements.txt",
            ) from exc
        return psycopg.connect(self.dsn, row_factory=dict_row, connect_timeout=1)

    def fetch_all(self, sql: str, params: dict[str, Any] | tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, params)
                    return list(cur.fetchall())
        except ApiError:
            raise
        except Exception as exc:
            raise ApiError(HTTPStatus.INTERNAL_SERVER_ERROR, f"数据库查询失败：{exc}") from exc

    def fetch_one(self, sql: str, params: dict[str, Any] | tuple[Any, ...] = ()) -> dict[str, Any] | None:
        rows = self.fetch_all(sql, params)
        return rows[0] if rows else None

    def fetch_readonly_llm_sql(self, sql: str, params: dict[str, Any] | tuple[Any, ...]) -> list[dict[str, Any]]:
        timeout_ms = max(1000, (self.llm_config.timeout_seconds if self.llm_config else 30) * 1000)
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("SET TRANSACTION READ ONLY")
                    cur.execute(f"SET LOCAL statement_timeout = '{timeout_ms}ms'")
                    cur.execute(sql, params)
                    return list(cur.fetchall())
        except Exception as exc:
            raise ApiError(HTTPStatus.BAD_REQUEST, f"LLM SQL 执行失败：{exc}") from exc

    def execute_returning(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any]:
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, params)
                    row = cur.fetchone()
                    conn.commit()
                    if row is None:
                        raise ApiError(HTTPStatus.NOT_FOUND, "目标记录不存在")
                    return dict(row)
        except ApiError:
            raise
        except Exception as exc:
            raise ApiError(HTTPStatus.BAD_REQUEST, f"数据库写入失败：{exc}") from exc

    def execute_count(self, sql: str, params: tuple[Any, ...] = ()) -> int:
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, params)
                    affected = cur.rowcount
                    conn.commit()
                    return affected
        except ApiError:
            raise
        except ForeignKeyViolation as exc:
            raise ApiError(HTTPStatus.BAD_REQUEST, "该记录仍被其他数据引用，不能直接删除；请先删除或迁移关联数据。") from exc
        except Exception as exc:
            raise ApiError(HTTPStatus.BAD_REQUEST, f"数据库写入失败：{exc}") from exc

    def ping(self) -> bool:
        self.fetch_one("SELECT 1 AS ok")
        return True

    def _limit(self, query: dict[str, str], default: int = 20, maximum: int = 100) -> int:
        raw_value = query.get("limit", str(default))
        try:
            value = int(raw_value)
        except ValueError as exc:
            raise ApiError(HTTPStatus.BAD_REQUEST, "limit 必须是整数") from exc
        return max(1, min(value, maximum))

    def users(self, query: dict[str, str]) -> list[dict[str, Any]]:
        conditions: list[str] = []
        params: list[Any] = []
        if query.get("q"):
            q = f"%{query['q'].strip()}%"
            conditions.append("(u.name ILIKE %s OR u.department ILIKE %s)")
            params.extend([q, q])
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        return self.fetch_all(
            f"""
            SELECT u.user_id, u.name, u.department,
                   CASE
                     WHEN t.user_id IS NOT NULL THEN '教师'
                     WHEN s.user_id IS NOT NULL THEN '学生'
                     ELSE '用户'
                   END AS role
            FROM users u
            LEFT JOIN teacher t ON t.user_id = u.user_id
            LEFT JOIN student s ON s.user_id = u.user_id
            {where}
            ORDER BY u.user_id
            """,
            tuple(params),
        )

    def campuses(self, query: dict[str, str]) -> list[dict[str, Any]]:
        q = query.get("q", "").strip()
        where = ""
        params: list[Any] = []
        if q:
            where = "WHERE name ILIKE %s OR address ILIKE %s"
            params = [f"%{q}%", f"%{q}%"]
        return self.fetch_all(
            f"""
            SELECT campus_id, name, address
            FROM campus
            {where}
            ORDER BY campus_id
            """,
            tuple(params),
        )

    def buildings(self, query: dict[str, str]) -> list[dict[str, Any]]:
        conditions: list[str] = []
        params: list[Any] = []
        if query.get("campus_id"):
            conditions.append("b.campus_id = %s")
            params.append(int(query["campus_id"]))
        if query.get("type"):
            conditions.append("b.type = %s")
            params.append(query["type"].strip())
        if query.get("q"):
            q = f"%{query['q'].strip()}%"
            conditions.append("(b.name ILIKE %s OR b.type ILIKE %s OR c.name ILIKE %s)")
            params.extend([q, q, q])
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        return self.fetch_all(
            f"""
            SELECT b.building_id, b.name, b.type, b.campus_id, c.name AS campus_name
            FROM building b
            JOIN campus c ON c.campus_id = b.campus_id
            {where}
            ORDER BY c.campus_id, b.building_id
            """,
            tuple(params),
        )

    def create_building(self, payload: dict[str, Any]) -> dict[str, Any]:
        name = clean_text(payload, "name")
        building_type = clean_text(payload, "type", default="其他")
        campus_id = clean_int(payload, "campus_id")
        if building_type not in BUILDING_TYPES:
            raise ApiError(HTTPStatus.BAD_REQUEST, "建筑类型不在允许范围内")
        return self.execute_returning(
            """
            WITH saved AS (
              INSERT INTO building (name, type, campus_id)
              VALUES (%s, %s, %s)
              RETURNING *
            )
            SELECT saved.building_id, saved.name, saved.type, saved.campus_id, c.name AS campus_name
            FROM saved
            JOIN campus c ON c.campus_id = saved.campus_id
            """,
            (name, building_type, campus_id),
        )

    def update_building(self, building_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        name = clean_text(payload, "name")
        building_type = clean_text(payload, "type", default="其他")
        campus_id = clean_int(payload, "campus_id")
        if building_type not in BUILDING_TYPES:
            raise ApiError(HTTPStatus.BAD_REQUEST, "建筑类型不在允许范围内")
        return self.execute_returning(
            """
            WITH saved AS (
              UPDATE building
              SET name = %s, type = %s, campus_id = %s
              WHERE building_id = %s
              RETURNING *
            )
            SELECT saved.building_id, saved.name, saved.type, saved.campus_id, c.name AS campus_name
            FROM saved
            JOIN campus c ON c.campus_id = saved.campus_id
            """,
            (name, building_type, campus_id, building_id),
        )

    def delete_building(self, building_id: int) -> dict[str, Any]:
        dependency = self.fetch_one(
            """
            SELECT count(*) AS facility_count
            FROM facility
            WHERE building_id = %s
            """,
            (building_id,),
        )
        facility_count = int(dependency["facility_count"]) if dependency else 0
        if facility_count:
            raise ApiError(
                HTTPStatus.BAD_REQUEST,
                f"该建筑下仍有 {facility_count} 个设施，不能删除。请先删除或迁移这些设施，再删除建筑。",
            )
        affected = self.execute_count("DELETE FROM building WHERE building_id = %s", (building_id,))
        if affected == 0:
            raise ApiError(HTTPStatus.NOT_FOUND, "建筑不存在")
        return {"deleted": affected}

    def facilities(self, query: dict[str, str]) -> list[dict[str, Any]]:
        conditions: list[str] = []
        params: list[Any] = []
        if query.get("building_id"):
            conditions.append("f.building_id = %s")
            params.append(int(query["building_id"]))
        if query.get("campus_id"):
            conditions.append("c.campus_id = %s")
            params.append(int(query["campus_id"]))
        if query.get("type"):
            conditions.append("f.type = %s")
            params.append(query["type"].strip())
        if query.get("q"):
            q = f"%{query['q'].strip()}%"
            conditions.append("(f.name ILIKE %s OR f.type ILIKE %s OR b.name ILIKE %s)")
            params.extend([q, q, q])
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        return self.fetch_all(
            f"""
            SELECT f.facility_id, f.name, f.type, f.open_time, f.building_id,
                   b.name AS building_name, c.name AS campus_name
            FROM facility f
            JOIN building b ON b.building_id = f.building_id
            JOIN campus c ON c.campus_id = b.campus_id
            {where}
            ORDER BY c.campus_id, b.building_id, f.facility_id
            """,
            tuple(params),
        )

    def create_facility(self, payload: dict[str, Any]) -> dict[str, Any]:
        name = clean_text(payload, "name")
        facility_type = clean_text(payload, "type", default="其他")
        open_time = clean_text(payload, "open_time", default="以现场公告为准")
        building_id = clean_int(payload, "building_id")
        if facility_type not in FACILITY_TYPES:
            raise ApiError(HTTPStatus.BAD_REQUEST, "设施类型不在允许范围内")
        return self.execute_returning(
            """
            WITH saved AS (
              INSERT INTO facility (name, type, open_time, building_id)
              VALUES (%s, %s, %s, %s)
              RETURNING *
            )
            SELECT saved.facility_id, saved.name, saved.type, saved.open_time, saved.building_id,
                   b.name AS building_name, c.name AS campus_name
            FROM saved
            JOIN building b ON b.building_id = saved.building_id
            JOIN campus c ON c.campus_id = b.campus_id
            """,
            (name, facility_type, open_time, building_id),
        )

    def update_facility(self, facility_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        name = clean_text(payload, "name")
        facility_type = clean_text(payload, "type", default="其他")
        open_time = clean_text(payload, "open_time", default="以现场公告为准")
        building_id = clean_int(payload, "building_id")
        if facility_type not in FACILITY_TYPES:
            raise ApiError(HTTPStatus.BAD_REQUEST, "设施类型不在允许范围内")
        return self.execute_returning(
            """
            WITH saved AS (
              UPDATE facility
              SET name = %s, type = %s, open_time = %s, building_id = %s
              WHERE facility_id = %s
              RETURNING *
            )
            SELECT saved.facility_id, saved.name, saved.type, saved.open_time, saved.building_id,
                   b.name AS building_name, c.name AS campus_name
            FROM saved
            JOIN building b ON b.building_id = saved.building_id
            JOIN campus c ON c.campus_id = b.campus_id
            """,
            (name, facility_type, open_time, building_id, facility_id),
        )

    def delete_facility(self, facility_id: int) -> dict[str, Any]:
        dependency = self.fetch_one(
            """
            SELECT
              (SELECT count(*) FROM activity WHERE facility_id = %s) AS activity_count,
              (SELECT count(*) FROM course_offering_schedule WHERE facility_id = %s) AS schedule_count
            """,
            (facility_id, facility_id),
        )
        activity_count = int(dependency["activity_count"]) if dependency else 0
        schedule_count = int(dependency["schedule_count"]) if dependency else 0
        if activity_count or schedule_count:
            details = []
            if activity_count:
                details.append(f"{activity_count} 个活动")
            if schedule_count:
                details.append(f"{schedule_count} 条排课")
            raise ApiError(
                HTTPStatus.BAD_REQUEST,
                f"该设施仍被{'、'.join(details)}引用，不能删除。请先删除或迁移关联数据，再删除设施。",
            )
        affected = self.execute_count("DELETE FROM facility WHERE facility_id = %s", (facility_id,))
        if affected == 0:
            raise ApiError(HTTPStatus.NOT_FOUND, "设施不存在")
        return {"deleted": affected}

    def courses(self, query: dict[str, str]) -> list[dict[str, Any]]:
        conditions: list[str] = []
        params: list[Any] = []
        if query.get("q"):
            q = f"%{query['q'].strip()}%"
            conditions.append("(c.name ILIKE %s OR co.course_code ILIKE %s OR u.name ILIKE %s OR u.department ILIKE %s)")
            params.extend([q, q, q, q])
        if query.get("course_name"):
            conditions.append("c.name ILIKE %s")
            params.append(f"%{query['course_name'].strip()}%")
        if query.get("course_code"):
            conditions.append("co.course_code ILIKE %s")
            params.append(f"%{query['course_code'].strip()}%")
        if query.get("teacher"):
            conditions.append("u.name ILIKE %s")
            params.append(f"%{query['teacher'].strip()}%")
        if query.get("department"):
            conditions.append("u.department = %s")
            params.append(query["department"].strip())
        if query.get("semester"):
            conditions.append("co.semester ILIKE %s")
            params.append(f"%{query['semester'].strip()}%")
        if query.get("day_of_week"):
            conditions.append("cos.day_of_week = %s")
            params.append(query["day_of_week"].strip())
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        return self.fetch_all(
            f"""
            SELECT co.offering_id, co.course_code, co.semester,
                   c.course_master_code, c.name AS course_name,
                   string_agg(DISTINCT u.name, '、' ORDER BY u.name) AS teachers,
                   string_agg(DISTINCT u.department, '、' ORDER BY u.department) AS departments,
                   string_agg(DISTINCT t.title, '、' ORDER BY t.title) AS teacher_titles,
                   string_agg(
                     DISTINCT cos.day_of_week || ' ' || cos.start_period || '-' || cos.end_period
                       || '节 ' || cos.week_type || ' @ ' || f.name,
                     '；' ORDER BY cos.day_of_week || ' ' || cos.start_period || '-' || cos.end_period
                       || '节 ' || cos.week_type || ' @ ' || f.name
                   ) AS schedules
            FROM course_offering co
            JOIN course_section cs ON cs.course_code = co.course_code
            JOIN course c ON c.course_master_code = cs.course_master_code
            LEFT JOIN course_offering_teacher cot ON cot.offering_id = co.offering_id
            LEFT JOIN teacher t ON t.user_id = cot.teacher_id
            LEFT JOIN users u ON u.user_id = t.user_id
            LEFT JOIN course_offering_schedule cos ON cos.offering_id = co.offering_id
            LEFT JOIN facility f ON f.facility_id = cos.facility_id
            {where}
            GROUP BY co.offering_id, co.course_code, co.semester, c.course_master_code, c.name
            ORDER BY c.name, co.course_code, co.offering_id
            """,
            tuple(params),
        )

    def activities(self, query: dict[str, str]) -> list[dict[str, Any]]:
        conditions: list[str] = []
        params: list[Any] = []
        if query.get("q"):
            q = f"%{query['q'].strip()}%"
            conditions.append(
                "(a.name ILIKE %s OR a.description ILIKE %s OR a.organizer ILIKE %s "
                "OR f.name ILIKE %s OR b.name ILIKE %s OR c.name ILIKE %s)"
            )
            params.extend([q, q, q, q, q, q])
        if query.get("organizer"):
            conditions.append("a.organizer ILIKE %s")
            params.append(f"%{query['organizer'].strip()}%")
        if query.get("facility_id"):
            conditions.append("a.facility_id = %s")
            params.append(int(query["facility_id"]))
        if query.get("campus_id"):
            conditions.append("c.campus_id = %s")
            params.append(int(query["campus_id"]))
        if query.get("start_from"):
            conditions.append("a.start_time >= %s")
            params.append(parse_datetime_text(query["start_from"]))
        if query.get("start_to"):
            conditions.append("a.start_time <= %s")
            params.append(parse_datetime_text(query["start_to"]))
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        return self.fetch_all(
            f"""
            SELECT a.activity_id, a.name, a.description, a.start_time, a.end_time, a.organizer,
                   a.facility_id, f.name AS facility_name, b.name AS building_name, c.name AS campus_name,
                   count(ua.user_id) AS participant_count
            FROM activity a
            JOIN facility f ON f.facility_id = a.facility_id
            JOIN building b ON b.building_id = f.building_id
            JOIN campus c ON c.campus_id = b.campus_id
            LEFT JOIN user_activity ua ON ua.activity_id = a.activity_id
            {where}
            GROUP BY a.activity_id, f.name, b.name, c.name
            ORDER BY a.start_time, a.activity_id
            """,
            tuple(params),
        )

    def create_activity(self, payload: dict[str, Any]) -> dict[str, Any]:
        name = clean_text(payload, "name")
        description = clean_text(payload, "description", default="暂无简介")
        start_time = parse_datetime_text(clean_text(payload, "start_time"))
        end_time = parse_datetime_text(clean_text(payload, "end_time", required=False, default=""))
        organizer = clean_text(payload, "organizer", default="未填写")
        facility_id = clean_int(payload, "facility_id")
        return self.execute_returning(
            """
            INSERT INTO activity (name, description, start_time, end_time, organizer, facility_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING activity_id, name, description, start_time, end_time, organizer, facility_id
            """,
            (name, description, start_time, end_time, organizer, facility_id),
        )

    def update_activity(self, activity_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        name = clean_text(payload, "name")
        description = clean_text(payload, "description", default="暂无简介")
        start_time = parse_datetime_text(clean_text(payload, "start_time"))
        end_time = parse_datetime_text(clean_text(payload, "end_time", required=False, default=""))
        organizer = clean_text(payload, "organizer", default="未填写")
        facility_id = clean_int(payload, "facility_id")
        return self.execute_returning(
            """
            UPDATE activity
            SET name = %s, description = %s, start_time = %s, end_time = %s, organizer = %s, facility_id = %s
            WHERE activity_id = %s
            RETURNING activity_id, name, description, start_time, end_time, organizer, facility_id
            """,
            (name, description, start_time, end_time, organizer, facility_id, activity_id),
        )

    def delete_activity(self, activity_id: int) -> dict[str, Any]:
        affected = self.execute_count("DELETE FROM activity WHERE activity_id = %s", (activity_id,))
        if affected == 0:
            raise ApiError(HTTPStatus.NOT_FOUND, "活动不存在")
        return {"deleted": affected}

    def create_query_log(self, payload: dict[str, Any]) -> dict[str, Any]:
        user_id = clean_int(payload, "user_id")
        category = clean_text(payload, "query_category", default="其他")
        content = clean_text(payload, "query_content")
        if category not in QUERY_CATEGORIES:
            raise ApiError(HTTPStatus.BAD_REQUEST, "查询类别不在允许范围内")
        return self.execute_returning(
            """
            INSERT INTO query_log (user_id, query_category, query_content)
            VALUES (%s, %s, %s)
            RETURNING log_id, user_id, query_category, query_content, query_time
            """,
            (user_id, category, content),
        )

    def query_logs(self, query: dict[str, str]) -> list[dict[str, Any]]:
        conditions: list[str] = []
        params: list[Any] = []
        if query.get("query_category"):
            conditions.append("ql.query_category = %s")
            params.append(query["query_category"].strip())
        if query.get("user_id"):
            conditions.append("ql.user_id = %s")
            params.append(int(query["user_id"]))
        if query.get("q"):
            q = f"%{query['q'].strip()}%"
            conditions.append("(ql.query_content ILIKE %s OR ql.query_category ILIKE %s OR u.name ILIKE %s)")
            params.extend([q, q, q])
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.append(self._limit(query))
        return self.fetch_all(
            f"""
            SELECT ql.log_id, ql.user_id, u.name AS user_name, ql.query_category,
                   ql.query_content, ql.query_time
            FROM query_log ql
            JOIN users u ON u.user_id = ql.user_id
            {where}
            ORDER BY ql.query_time DESC, ql.log_id DESC
            LIMIT %s
            """,
            tuple(params),
        )

    def popular_queries(self, query: dict[str, str]) -> list[dict[str, Any]]:
        conditions: list[str] = []
        params: list[Any] = []
        if query.get("user_id"):
            conditions.append("user_id = %s")
            params.append(int(query["user_id"]))
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.append(self._limit(query, default=10))
        return self.fetch_all(
            f"""
            SELECT query_category, count(*) AS query_count,
                   (array_agg(query_content ORDER BY query_time DESC))[1] AS latest_query,
                   max(query_time) AS latest_query_time
            FROM query_log
            {where}
            GROUP BY query_category
            ORDER BY query_count DESC, query_category
            LIMIT %s
            """,
            tuple(params),
        )

    def popular_activities(self, query: dict[str, str]) -> list[dict[str, Any]]:
        return self.fetch_all(
            """
            SELECT a.activity_id, a.name AS activity_name, a.start_time, a.organizer,
                   f.name AS facility_name, b.name AS building_name, c.name AS campus_name,
                   count(ua.user_id) AS participant_count
            FROM activity a
            JOIN facility f ON f.facility_id = a.facility_id
            JOIN building b ON b.building_id = f.building_id
            JOIN campus c ON c.campus_id = b.campus_id
            LEFT JOIN user_activity ua ON ua.activity_id = a.activity_id
            GROUP BY a.activity_id, f.name, b.name, c.name
            ORDER BY participant_count DESC, a.start_time, a.activity_id
            LIMIT %s
            """,
            (self._limit(query, default=10),),
        )

    def activity_participants(self, activity_id: int, query: dict[str, str]) -> list[dict[str, Any]]:
        if self.fetch_one("SELECT activity_id FROM activity WHERE activity_id = %s", (activity_id,)) is None:
            raise ApiError(HTTPStatus.NOT_FOUND, "活动不存在")

        conditions = ["ua.activity_id = %s"]
        params: list[Any] = [activity_id]
        if query.get("status"):
            conditions.append("ua.status = %s")
            params.append(query["status"].strip())
        if query.get("q"):
            q = f"%{query['q'].strip()}%"
            conditions.append("(u.name ILIKE %s OR u.department ILIKE %s)")
            params.extend([q, q])
        params.append(self._limit(query, default=50, maximum=200))
        where = " AND ".join(conditions)
        return self.fetch_all(
            f"""
            SELECT ua.activity_id, a.name AS activity_name,
                   ua.user_id, u.name AS user_name, u.department,
                   CASE
                     WHEN t.user_id IS NOT NULL THEN '教师'
                     WHEN s.user_id IS NOT NULL THEN '学生'
                     ELSE '用户'
                   END AS role,
                   ua.status
            FROM user_activity ua
            JOIN activity a ON a.activity_id = ua.activity_id
            JOIN users u ON u.user_id = ua.user_id
            LEFT JOIN teacher t ON t.user_id = u.user_id
            LEFT JOIN student s ON s.user_id = u.user_id
            WHERE {where}
            ORDER BY ua.status, u.user_id
            LIMIT %s
            """,
            tuple(params),
        )

    def _scope_query_log_plan(self, plan: dict[str, Any], user_id: int) -> dict[str, Any]:
        sql = str(plan.get("sql", ""))
        if "query_log" not in sql.lower():
            return plan
        if "count(" in sql.lower() or "group by" in sql.lower():
            return {
                **plan,
                "intent": "query_category_stats",
                "title": "统计我的热门查询类别",
                "category": "统计",
                "sql": """
SELECT query_category, count(*) AS query_count
FROM query_log
WHERE user_id = %s
GROUP BY query_category
ORDER BY query_count DESC, query_category
""".strip(),
                "params": (user_id,),
            }
        return {
            **plan,
            "intent": "query_log_history",
            "title": "查询我的 AI 查询记录",
            "category": "其他",
            "sql": """
SELECT query_category, query_content, query_time
FROM query_log
WHERE user_id = %s
ORDER BY query_time DESC, log_id DESC
LIMIT 20
""".strip(),
            "params": (user_id,),
        }

    def user_reservations(self, user_id: int) -> list[dict[str, Any]]:
        return self.fetch_all(
            """
            SELECT ua.user_id, u.name AS user_name, ua.activity_id, ua.status,
                   a.name AS activity_name, a.description, a.start_time, a.end_time, a.organizer,
                   a.facility_id, f.name AS facility_name, b.name AS building_name, c.name AS campus_name
            FROM user_activity ua
            JOIN users u ON u.user_id = ua.user_id
            JOIN activity a ON a.activity_id = ua.activity_id
            JOIN facility f ON f.facility_id = a.facility_id
            JOIN building b ON b.building_id = f.building_id
            JOIN campus c ON c.campus_id = b.campus_id
            WHERE ua.user_id = %s
            ORDER BY a.start_time, a.activity_id
            """,
            (user_id,),
        )

    def reserve_activity(self, activity_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        user_id = clean_int(payload, "user_id")
        return self.execute_returning(
            """
            WITH saved AS (
              INSERT INTO user_activity (user_id, activity_id, status)
              VALUES (%s, %s, '待参加')
              ON CONFLICT (user_id, activity_id) DO UPDATE SET status = '待参加'
              RETURNING user_id, activity_id, status
            )
            SELECT saved.user_id, u.name AS user_name, saved.activity_id, saved.status,
                   a.name AS activity_name, a.start_time, a.end_time, a.organizer,
                   f.name AS facility_name, b.name AS building_name, c.name AS campus_name
            FROM saved
            JOIN users u ON u.user_id = saved.user_id
            JOIN activity a ON a.activity_id = saved.activity_id
            JOIN facility f ON f.facility_id = a.facility_id
            JOIN building b ON b.building_id = f.building_id
            JOIN campus c ON c.campus_id = b.campus_id
            """,
            (user_id, activity_id),
        )

    def cancel_activity_reservation(self, activity_id: int, user_id: int) -> dict[str, Any]:
        affected = self.execute_count(
            "DELETE FROM user_activity WHERE activity_id = %s AND user_id = %s",
            (activity_id, user_id),
        )
        if affected == 0:
            raise ApiError(HTTPStatus.NOT_FOUND, "预约记录不存在")
        return {"deleted": affected}

    def sql_examples(self) -> list[dict[str, Any]]:
        examples = []
        for item in SQL_EXAMPLES:
            examples.append({**item, "rows": self.fetch_all(item["sql"])})
        return examples

    def natural_language_query(self, payload: dict[str, Any]) -> dict[str, Any]:
        question = clean_text(payload, "question")
        user_id = payload.get("user_id", 4)
        try:
            user_id = int(user_id)
        except (TypeError, ValueError) as exc:
            raise ApiError(HTTPStatus.BAD_REQUEST, "user_id 必须是整数") from exc
        role = str(payload.get("role", "user")).strip().lower()
        if role != "admin" and is_activity_participant_roster_question(question):
            raise ApiError(HTTPStatus.FORBIDDEN, "用户端不能查看活动参与者名单，请使用管理员端查看。")

        local_plan = build_nl_query(question)
        engine = "rules"
        llm_error = ""
        if local_plan["intent"] == "course_schedule":
            plan = self._scope_query_log_plan(local_plan, user_id)
            rows = self.fetch_all(plan["sql"], plan["params"])
        elif self.llm_config and self.llm_config.enabled:
            try:
                plan = build_llm_query(question, self.llm_config, current_user_id=user_id)
                plan = self._scope_query_log_plan(plan, user_id)
                rows = self.fetch_readonly_llm_sql(plan["sql"], plan["params"])
                engine = "llm"
            except (ApiError, LlmQueryError) as exc:
                llm_error = getattr(exc, "message", str(exc))
                plan = self._scope_query_log_plan(local_plan, user_id)
                rows = self.fetch_all(plan["sql"], plan["params"])
        else:
            plan = self._scope_query_log_plan(local_plan, user_id)
            rows = self.fetch_all(plan["sql"], plan["params"])
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
            "params": plan["params"] if isinstance(plan["params"], dict) else list(plan["params"]),
            "rows": rows,
            "row_count": len(rows),
            "answer": self.summarize_answer(plan, rows),
            "engine": engine,
            "llm_error": llm_error,
        }
