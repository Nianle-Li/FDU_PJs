from __future__ import annotations

SQL_EXAMPLES = [
    {
        "key": "campus_buildings",
        "title": "查询邯郸校区建筑列表",
        "group": "基础关联查询",
        "purpose": "验证校区与建筑的一对多关系，确认可以按校区筛选建筑。",
        "business_question": "邯郸校区有哪些建筑？",
        "tables": ["campus", "building"],
        "sql": """
SELECT c.name AS campus_name, b.name AS building_name, b.type
FROM campus c
JOIN building b ON b.campus_id = c.campus_id
WHERE c.name = '邯郸校区'
ORDER BY b.name
""".strip(),
    },
    {
        "key": "building_facilities",
        "title": "查询第二教学楼设施",
        "group": "基础关联查询",
        "purpose": "验证建筑与设施的一对多关系，展示指定建筑内的教室、自习室、报告厅等设施。",
        "business_question": "第二教学楼里有哪些可用设施？",
        "tables": ["building", "facility"],
        "sql": """
SELECT b.name AS building_name, f.name AS facility_name, f.type, f.open_time
FROM building b
JOIN facility f ON f.building_id = b.building_id
WHERE b.name = '第二教学楼'
ORDER BY f.name
""".strip(),
    },
    {
        "key": "teacher_courses",
        "title": "查询李芳老师授课列表",
        "group": "教学业务查询",
        "purpose": "验证教师、开课实例、课程班次和课程主数据之间的多表连接。",
        "business_question": "某位教师这学期教哪些课程？",
        "tables": ["users", "teacher", "course_offering_teacher", "course_offering", "course_section", "course"],
        "sql": """
SELECT u.name AS teacher_name, c.name AS course_name, co.course_code, co.semester
FROM users u
JOIN teacher t ON t.user_id = u.user_id
JOIN course_offering_teacher cot ON cot.teacher_id = t.user_id
JOIN course_offering co ON co.offering_id = cot.offering_id
JOIN course_section cs ON cs.course_code = co.course_code
JOIN course c ON c.course_master_code = cs.course_master_code
WHERE u.name = '李芳'
ORDER BY c.name, co.course_code
""".strip(),
    },
    {
        "key": "recent_activities",
        "title": "查询近期校园活动",
        "group": "活动业务查询",
        "purpose": "验证活动、设施、建筑、校区链路，支撑用户端活动地点展示。",
        "business_question": "近期有哪些校园活动，分别在哪里举办？",
        "tables": ["activity", "facility", "building", "campus"],
        "sql": """
SELECT a.name AS activity_name, a.start_time, c.name AS campus_name, b.name AS building_name, f.name AS facility_name
FROM activity a
JOIN facility f ON f.facility_id = a.facility_id
JOIN building b ON b.building_id = f.building_id
JOIN campus c ON c.campus_id = b.campus_id
WHERE a.start_time >= TIMESTAMP '2026-05-11 00:00:00'
ORDER BY a.start_time
""".strip(),
    },
    {
        "key": "building_stats",
        "title": "统计每个校区各类建筑数量",
        "group": "统计分析查询",
        "purpose": "验证 GROUP BY 聚合能力，展示校区维度下不同建筑类型的数量分布。",
        "business_question": "各校区分别有多少教学楼、图书馆、实验楼等建筑？",
        "tables": ["campus", "building"],
        "sql": """
SELECT c.name AS campus_name, b.type, count(*) AS building_count
FROM campus c
JOIN building b ON b.campus_id = c.campus_id
GROUP BY c.name, b.type
ORDER BY c.name, b.type
""".strip(),
    },
    {
        "key": "query_categories",
        "title": "统计热门查询类别",
        "group": "统计分析查询",
        "purpose": "验证查询日志聚合，帮助管理员了解系统高频查询方向。",
        "business_question": "用户最常查询哪些类别的问题？",
        "tables": ["query_log"],
        "sql": """
SELECT query_category, count(*) AS query_count
FROM query_log
GROUP BY query_category
ORDER BY query_count DESC, query_category
""".strip(),
    },
    {
        "key": "hot_activities",
        "title": "统计热门活动",
        "group": "统计分析查询",
        "purpose": "验证活动报名关系表的聚合能力，展示各活动参与热度。",
        "business_question": "哪些活动报名或参与人数最多？",
        "tables": ["activity", "user_activity"],
        "sql": """
SELECT a.name AS activity_name, count(ua.user_id) AS participant_count
FROM activity a
LEFT JOIN user_activity ua ON ua.activity_id = a.activity_id
GROUP BY a.activity_id, a.name
ORDER BY participant_count DESC, a.name
""".strip(),
    },
]
