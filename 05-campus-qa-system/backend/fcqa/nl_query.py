from __future__ import annotations

import re
from typing import Any

from .constants import (
    BUILDING_TYPES,
    FACILITY_TYPES,
    KNOWN_BUILDING_NAMES,
    KNOWN_CAMPUS_NAMES,
    KNOWN_COURSE_NAMES,
    KNOWN_TEACHER_NAMES,
)


def first_known(text: str, candidates: list[str]) -> str | None:
    return next((candidate for candidate in candidates if candidate in text), None)


def extract_teacher_name(question: str) -> str | None:
    known = first_known(question, KNOWN_TEACHER_NAMES)
    if known:
        return known
    match = re.search(r"([\u4e00-\u9fa5A-Za-z0-9]{2,10})(?:老师|教师)", question)
    return match.group(1) if match else None


def extract_search_term(question: str) -> str:
    text = re.sub(r"[？?，,。.!！\s]", "", question)
    for token in [
        "请问",
        "帮我",
        "查询",
        "查一下",
        "告诉我",
        "有哪些",
        "哪里",
        "什么",
        "怎么",
        "近期",
        "最近",
        "的",
        "吗",
    ]:
        text = text.replace(token, "")
    return text[:30] or question.strip()[:30]


def build_nl_query(question: str) -> dict[str, Any]:
    q = question.strip()
    compact = re.sub(r"\s+", "", q)
    campus_name = first_known(compact, KNOWN_CAMPUS_NAMES)
    building_name = first_known(compact, KNOWN_BUILDING_NAMES)
    course_name = first_known(compact, KNOWN_COURSE_NAMES)
    teacher_name = extract_teacher_name(compact)
    building_type = first_known(compact, BUILDING_TYPES)
    facility_type = first_known(compact, FACILITY_TYPES)
    if "自习" in compact:
        facility_type = "自习室"
    elif "篮球" in compact and "活动" not in compact and "课程" not in compact:
        facility_type = "体育设施"

    if "热门活动" in compact or ("活动" in compact and any(word in compact for word in ["热门", "最多人", "参加人数"])):
        return {
            "intent": "hot_activities",
            "title": "统计热门活动",
            "category": "统计",
            "sql": """
SELECT a.name AS activity_name, count(ua.user_id) AS participant_count
FROM activity a
LEFT JOIN user_activity ua ON ua.activity_id = a.activity_id
GROUP BY a.activity_id, a.name
ORDER BY participant_count DESC, a.name
LIMIT 10
""".strip(),
            "params": (),
        }

    if "热门查询" in compact or ("查询" in compact and any(word in compact for word in ["类别", "统计", "最多", "热门"])):
        return {
            "intent": "query_category_stats",
            "title": "统计热门查询类别",
            "category": "统计",
            "sql": """
SELECT query_category, count(*) AS query_count
FROM query_log
GROUP BY query_category
ORDER BY query_count DESC, query_category
""".strip(),
            "params": (),
        }

    if "统计" in compact and "校区" in compact and "建筑" in compact:
        return {
            "intent": "building_stats",
            "title": "统计每个校区各类建筑数量",
            "category": "统计",
            "sql": """
SELECT c.name AS campus_name, b.type, count(*) AS building_count
FROM campus c
JOIN building b ON b.campus_id = c.campus_id
GROUP BY c.name, b.type
ORDER BY c.name, b.type
""".strip(),
            "params": (),
        }

    if teacher_name and any(word in compact for word in ["教", "授课", "课程", "老师", "教师"]):
        return {
            "intent": "teacher_courses",
            "title": f"查询{teacher_name}老师授课列表",
            "category": "教师",
            "sql": """
SELECT u.name AS teacher_name, c.name AS course_name, co.course_code, co.semester
FROM users u
JOIN teacher t ON t.user_id = u.user_id
JOIN course_offering_teacher cot ON cot.teacher_id = t.user_id
JOIN course_offering co ON co.offering_id = cot.offering_id
JOIN course_section cs ON cs.course_code = co.course_code
JOIN course c ON c.course_master_code = cs.course_master_code
WHERE u.name ILIKE %s
ORDER BY c.name, co.course_code
""".strip(),
            "params": (f"%{teacher_name}%",),
        }

    if course_name or ("课" in compact and any(word in compact for word in ["周几", "上课", "地点", "教室", "安排", "哪里"])):
        term = course_name or extract_search_term(compact)
        return {
            "intent": "course_schedule",
            "title": f"查询课程排课：{term}",
            "category": "课程",
            "sql": """
SELECT c.name AS course_name, co.course_code, co.semester,
       string_agg(DISTINCT u.name, '、' ORDER BY u.name) AS teachers,
       cos.day_of_week, cos.start_period, cos.end_period, cos.week_type,
       f.name AS facility_name, b.name AS building_name, cp.name AS campus_name
FROM course_offering co
JOIN course_section cs ON cs.course_code = co.course_code
JOIN course c ON c.course_master_code = cs.course_master_code
LEFT JOIN course_offering_teacher cot ON cot.offering_id = co.offering_id
LEFT JOIN teacher t ON t.user_id = cot.teacher_id
LEFT JOIN users u ON u.user_id = t.user_id
LEFT JOIN course_offering_schedule cos ON cos.offering_id = co.offering_id
LEFT JOIN facility f ON f.facility_id = cos.facility_id
LEFT JOIN building b ON b.building_id = f.building_id
LEFT JOIN campus cp ON cp.campus_id = b.campus_id
WHERE c.name ILIKE %s OR %s ILIKE ('%%' || c.name || '%%') OR co.course_code ILIKE %s
GROUP BY c.name, co.course_code, co.semester, cos.day_of_week, cos.start_period,
         cos.end_period, cos.week_type, f.name, b.name, cp.name
ORDER BY c.name, co.course_code, cos.day_of_week, cos.start_period
""".strip(),
            "params": (f"%{term}%", term, f"%{term}%"),
        }

    if building_name and any(word in compact for word in ["设施", "自习", "教室", "阅览", "开放", "哪里"]):
        conditions = ["b.name ILIKE %s"]
        params: list[Any] = [f"%{building_name}%"]
        if facility_type:
            conditions.append("f.type = %s")
            params.append(facility_type)
        return {
            "intent": "building_facilities",
            "title": f"查询{building_name}设施",
            "category": "设施",
            "sql": f"""
SELECT b.name AS building_name, f.name AS facility_name, f.type, f.open_time
FROM building b
JOIN facility f ON f.building_id = b.building_id
WHERE {' AND '.join(conditions)}
ORDER BY f.name
""".strip(),
            "params": tuple(params),
        }

    if campus_name and any(word in compact for word in ["建筑", "楼", "馆", "食堂"]):
        conditions = ["c.name ILIKE %s"]
        params = [f"%{campus_name}%"]
        if building_type:
            conditions.append("b.type = %s")
            params.append(building_type)
        return {
            "intent": "campus_buildings",
            "title": f"查询{campus_name}建筑列表",
            "category": "建筑",
            "sql": f"""
SELECT c.name AS campus_name, b.name AS building_name, b.type
FROM campus c
JOIN building b ON b.campus_id = c.campus_id
WHERE {' AND '.join(conditions)}
ORDER BY b.name
""".strip(),
            "params": tuple(params),
        }

    if "活动" in compact or "讲座" in compact or "比赛" in compact or "工作坊" in compact:
        extracted_term = extract_search_term(compact)
        generic_activity_query = (
            "近期" in compact
            or "最近" in compact
            or ("有哪些" in compact and "活动" in compact)
            or extracted_term in {"活动", "校园活动", "校内活动"}
        )
        term = "" if generic_activity_query else extracted_term
        if term:
            where = "WHERE a.name ILIKE %s OR a.description ILIKE %s OR a.organizer ILIKE %s"
            params = (f"%{term}%", f"%{term}%", f"%{term}%")
            title = f"查询活动：{term}"
        else:
            where = ""
            params = ()
            title = "查询近期校园活动"
        return {
            "intent": "recent_activities",
            "title": title,
            "category": "活动",
            "sql": f"""
SELECT a.name AS activity_name, a.start_time, a.end_time, a.organizer,
       c.name AS campus_name, b.name AS building_name, f.name AS facility_name
FROM activity a
JOIN facility f ON f.facility_id = a.facility_id
JOIN building b ON b.building_id = f.building_id
JOIN campus c ON c.campus_id = b.campus_id
{where}
ORDER BY a.start_time
""".strip(),
            "params": params,
        }

    term = extract_search_term(compact)
    pattern = f"%{term}%"
    return {
        "intent": "global_search",
        "title": f"综合搜索：{term}",
        "category": "其他",
        "sql": """
SELECT '建筑' AS source, b.name AS title, b.type || '，' || c.name AS detail
FROM building b
JOIN campus c ON c.campus_id = b.campus_id
WHERE b.name ILIKE %s OR b.type ILIKE %s OR c.name ILIKE %s
UNION ALL
SELECT '设施' AS source, f.name AS title, f.type || '，' || b.name || '，开放时间：' || f.open_time AS detail
FROM facility f
JOIN building b ON b.building_id = f.building_id
WHERE f.name ILIKE %s OR f.type ILIKE %s OR b.name ILIKE %s
UNION ALL
SELECT '课程' AS source, c.name AS title, co.course_code || '，' || co.semester AS detail
FROM course c
JOIN course_section cs ON cs.course_master_code = c.course_master_code
JOIN course_offering co ON co.course_code = cs.course_code
WHERE c.name ILIKE %s OR co.course_code ILIKE %s
UNION ALL
SELECT '活动' AS source, a.name AS title, a.organizer || '，' || to_char(a.start_time, 'YYYY-MM-DD HH24:MI') AS detail
FROM activity a
WHERE a.name ILIKE %s OR a.description ILIKE %s OR a.organizer ILIKE %s
LIMIT 30
""".strip(),
        "params": (pattern, pattern, pattern, pattern, pattern, pattern, pattern, pattern, pattern, pattern, pattern),
    }
