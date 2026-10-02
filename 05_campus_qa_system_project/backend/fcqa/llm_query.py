from __future__ import annotations

import json
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import LlmConfig
from .constants import QUERY_CATEGORIES


class LlmQueryError(Exception):
    pass


SCHEMA_CONTEXT = """
PostgreSQL schema:

campus(campus_id SERIAL PRIMARY KEY, name, address)
building(building_id SERIAL PRIMARY KEY, name, type, campus_id)
facility(facility_id SERIAL PRIMARY KEY, name, type, open_time, building_id)
users(user_id SERIAL PRIMARY KEY, name, department)
teacher(user_id PRIMARY KEY, title)
student(user_id PRIMARY KEY, major)
course(course_master_code PRIMARY KEY, name)
course_section(course_code PRIMARY KEY, course_master_code)
course_offering(offering_id SERIAL PRIMARY KEY, course_code, semester)
course_offering_schedule(offering_id, day_of_week, start_period, end_period, week_type, facility_id)
course_offering_teacher(offering_id, teacher_id)
activity(activity_id SERIAL PRIMARY KEY, name, description, start_time, end_time, organizer, facility_id)
user_activity(user_id, activity_id, status)
query_log(log_id SERIAL PRIMARY KEY, user_id, query_category, query_content, query_time)

Foreign-key relationships:
- building.campus_id -> campus.campus_id
- facility.building_id -> building.building_id
- teacher.user_id -> users.user_id
- student.user_id -> users.user_id
- course_section.course_master_code -> course.course_master_code
- course_offering.course_code -> course_section.course_code
- course_offering_schedule.offering_id -> course_offering.offering_id
- course_offering_schedule.facility_id -> facility.facility_id
- course_offering_teacher.offering_id -> course_offering.offering_id
- course_offering_teacher.teacher_id -> teacher.user_id
- activity.facility_id -> facility.facility_id
- user_activity.user_id -> users.user_id
- user_activity.activity_id -> activity.activity_id
- query_log.user_id -> users.user_id

Useful join paths:
- course -> course_section -> course_offering -> course_offering_schedule -> facility -> building -> campus
- course_offering -> course_offering_teacher -> teacher -> users
- activity -> facility -> building -> campus
- user_activity -> users and activity

Allowed enum values:
- building.type: 教学楼, 图书馆, 宿舍, 食堂, 体育场馆, 办公楼, 实验楼, 医院, 综合楼, 其他
- facility.type: 教室, 自习室, 会议室, 实验室, 报告厅, 图书阅览室, 体育设施, 餐饮服务, 办公服务, 其他
- query_log.query_category: 校区, 建筑, 设施, 课程, 教师, 活动, 用户, 统计, 其他
- user_activity.status: 待参加, 已签到, 已完成, 已取消, 已缺席
""".strip()


SYSTEM_PROMPT = """
You convert Chinese campus information questions into one PostgreSQL read-only query.

Rules:
- Return JSON only. No Markdown. No explanation.
- Generate exactly one SELECT query. WITH is allowed only when it leads to a SELECT.
- Never generate INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE, COPY, GRANT, REVOKE, CALL, DO, VACUUM, ANALYZE, LOCK, SET, RESET, or multiple statements.
- Use psycopg named parameters such as %(course_name)s when filtering by user-provided values.
- Put all user-provided values in the params object. Use ILIKE with wildcard params for fuzzy Chinese name matching.
- Add clear column aliases that the frontend can display.
- Prefer LIMIT 50 or less.
- If the question uses first-person words such as "我", "我的", "自己", or "当前用户", use the provided current_user_id parameter. Never guess user_id=1.
- For "我参与了哪些活动", "我的预约", or similar questions, query user_activity joined with activity and filter by ua.user_id = %(user_id)s.
- For "近期活动" or "最近活动" in this demo database, do not hard-code today's date. Return activities ordered by start_time, or filter only if the user gives an explicit date/range.
- Choose category from: 校区, 建筑, 设施, 课程, 教师, 活动, 用户, 统计, 其他.

Return shape:
{
  "title": "short Chinese title",
  "category": "课程",
  "sql": "SELECT ... WHERE c.name ILIKE %(course_name)s LIMIT 50",
  "params": {"course_name": "%数据库系统%"}
}
""".strip()


FORBIDDEN_SQL_RE = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|create|copy|grant|revoke|call|do|vacuum|analyze|lock|set|reset|merge|execute)\b",
    re.IGNORECASE,
)


def build_llm_query(question: str, config: LlmConfig, current_user_id: int | None = None) -> dict[str, Any]:
    if not config.api_key:
        raise LlmQueryError("未配置 DEEPSEEK_API_KEY")
    max_rows = max(1, min(config.max_rows, 200))
    user_context = f"Current logged-in user_id: {current_user_id}" if current_user_id is not None else "Current user_id is unknown."
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"{SCHEMA_CONTEXT}\n\n{user_context}\n\nUser question:\n{question.strip()}\n\nReturn the JSON query plan now.",
        },
    ]
    response_text = call_deepseek(config, messages)
    raw_plan = parse_json_object(response_text)
    plan = normalize_query_plan(raw_plan, max_rows)
    if current_user_id is not None:
        plan = apply_current_user_context(plan, question, current_user_id)
    return plan


def call_deepseek(config: LlmConfig, messages: list[dict[str, str]]) -> str:
    payload = {
        "model": config.model or "deepseek-chat",
        "messages": messages,
        "temperature": 0,
        "stream": False,
    }
    request = Request(
        chat_completions_url(config.base_url),
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=max(1, config.timeout_seconds)) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise LlmQueryError(f"DeepSeek HTTP {exc.code}: {details[:300]}") from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise LlmQueryError(f"DeepSeek 调用失败：{exc}") from exc

    try:
        return str(data["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError) as exc:
        raise LlmQueryError("DeepSeek 响应缺少 message.content") from exc


def chat_completions_url(base_url: str) -> str:
    base = (base_url or "https://api.deepseek.com").strip().rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    return f"{base}/chat/completions"


def parse_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.IGNORECASE)
        stripped = re.sub(r"\s*```$", "", stripped)
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise LlmQueryError("LLM 未返回 JSON 对象")
    try:
        parsed = json.loads(stripped[start : end + 1])
    except json.JSONDecodeError as exc:
        raise LlmQueryError(f"LLM 返回的 JSON 无法解析：{exc}") from exc
    if not isinstance(parsed, dict):
        raise LlmQueryError("LLM 返回值不是 JSON 对象")
    return parsed


def normalize_query_plan(raw_plan: dict[str, Any], max_rows: int) -> dict[str, Any]:
    title = str(raw_plan.get("title") or "自然语言 SQL 查询").strip()
    category = str(raw_plan.get("category") or "其他").strip()
    if category not in QUERY_CATEGORIES:
        category = "其他"
    sql = prepare_readonly_sql(str(raw_plan.get("sql") or ""), max_rows)
    params = normalize_params(raw_plan.get("params", {}))
    return {
        "intent": "llm_sql",
        "title": title,
        "category": category,
        "sql": sql,
        "params": params,
    }


def normalize_params(raw_params: Any) -> dict[str, Any] | tuple[Any, ...]:
    if raw_params in (None, ""):
        return {}
    if isinstance(raw_params, dict):
        return {str(key): normalize_param_value(value) for key, value in raw_params.items()}
    if isinstance(raw_params, list):
        return tuple(normalize_param_value(value) for value in raw_params)
    raise LlmQueryError("params 必须是对象或数组")


def normalize_param_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def apply_current_user_context(plan: dict[str, Any], question: str, current_user_id: int) -> dict[str, Any]:
    if not is_first_person_query(question):
        return plan
    params = plan.get("params", {})
    if isinstance(params, dict):
        params = {**params, "user_id": current_user_id}
    elif isinstance(params, tuple):
        params = tuple(current_user_id if value == 1 else value for value in params)
    plan["params"] = params
    return plan


def is_first_person_query(question: str) -> bool:
    compact = re.sub(r"\s+", "", question)
    return any(token in compact for token in ["我", "我的", "自己", "当前用户"])


def prepare_readonly_sql(sql: str, max_rows: int) -> str:
    cleaned = sql.strip()
    if not cleaned:
        raise LlmQueryError("SQL 为空")
    if ";" in cleaned:
        raise LlmQueryError("SQL 不能包含分号或多语句")
    if "--" in cleaned or "/*" in cleaned or "*/" in cleaned:
        raise LlmQueryError("SQL 不能包含注释")
    if not re.match(r"^(select|with)\b", cleaned, flags=re.IGNORECASE):
        raise LlmQueryError("SQL 必须以 SELECT 或 WITH 开头")
    if FORBIDDEN_SQL_RE.search(cleaned):
        raise LlmQueryError("SQL 包含禁止的写入或管理语句")
    if re.search(r"\bfor\s+(update|share|no\s+key\s+update|key\s+share)\b", cleaned, flags=re.IGNORECASE):
        raise LlmQueryError("SQL 不能包含行锁")
    if re.search(r"\bpg_sleep\s*\(", cleaned, flags=re.IGNORECASE):
        raise LlmQueryError("SQL 不能调用 pg_sleep")
    return f"SELECT * FROM (\n{cleaned}\n) AS llm_query_result LIMIT {max_rows}"
